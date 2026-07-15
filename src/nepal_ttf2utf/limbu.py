"""Limbu/Sirijonga legacy-font (Namdhinggo SIL) -> Unicode Limbu (U+1900-U+194F).

Applies the forward explicit assignments from the SIL TECkit ``Byte_Unicode`` pass,
including positional class rules, in the vendored ``Limbu.map``. It also applies the
vowel / subjoined-consonant reordering that Unicode logical order requires, limited to
scalars emitted by the legacy byte pass. Pre-existing Unicode Limbu and mixed-provenance
windows are not custom reordered.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from ._controls import STRUCTURAL_C0, diagnostic_c0_codepoints
from .unicode_span import _is_assigned_script_codepoint

_BYTE_RULE_RE = re.compile(r"0x([0-9A-Fa-f]{2})")
_UNICODE_RULE_RE = re.compile(r"U\+([0-9A-Fa-f]{4,6})")
_BYTECLASS_RE = re.compile(r"^ByteClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_UNICLASS_RE = re.compile(r"^UniClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_CLASS_RULE_RE = re.compile(r"^\[([^\]]+)\]\s*<?>\s*\[([^\]]+)\]\s*$")
_PASS_RE = re.compile(r"^Pass\(\s*(Byte_Unicode|Unicode)\s*\)$", re.IGNORECASE)
_PASS_PREFIX_RE = re.compile(r"^Pass\b", re.IGNORECASE)
_BYTE_DEFAULT_RE = re.compile(r"^ByteDefault\s+0x[0-9A-Fa-f]{2}$", re.IGNORECASE)
_UNI_DEFAULT_RE = re.compile(r"^UniDefault\s+replacement_character$", re.IGNORECASE)
_DEFAULT_PREFIX_RE = re.compile(r"^(?:ByteDefault|UniDefault)\b", re.IGNORECASE)
_EXPLICIT_RULE_RE = re.compile(
    r"^(?P<source>0x[0-9A-Fa-f]{2}(?:\s+0x[0-9A-Fa-f]{2})*)\s*"
    r"(?:<>|>)\s*"
    r"(?P<target>U\+[0-9A-Fa-f]{4,6}(?:\s+U\+[0-9A-Fa-f]{4,6})*)$"
)
_LIMBU_CODEPOINT_RE = re.compile(r"[ᤀ-᥏]")
_VOWELS = frozenset(range(0x1920, 0x1929))
_SUBJOINED = frozenset(range(0x1929, 0x192C))
_KEMPHRENG = 0x193A


def _tokens(body: str) -> list[str]:
    body = re.sub(r"\s*\.\.\s*", " .. ", body)
    return [token for token in body.split() if token]


def _validate_unicode_scalar(codepoint: int) -> int:
    if (
        isinstance(codepoint, bool)
        or not isinstance(codepoint, int)
        or not (0 <= codepoint <= 0x10FFFF)
        or 0xD800 <= codepoint <= 0xDFFF
    ):
        raise ValueError(f"invalid Unicode scalar in Limbu map: {codepoint!r}")
    return codepoint


def _expand_byte_tokens(body: str) -> tuple[int, ...]:
    values: list[int] = []
    tokens = _tokens(body)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start_match = _BYTE_RULE_RE.fullmatch(token)
            end_match = _BYTE_RULE_RE.fullmatch(tokens[index + 2])
            if start_match is None or end_match is None:
                raise ValueError(f"invalid byte range in Limbu map: {token}..{tokens[index + 2]}")
            start = int(start_match.group(1), 16)
            end = int(end_match.group(1), 16)
            if end < start:
                raise ValueError(f"invalid byte range in Limbu map: {token}..{tokens[index + 2]}")
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _BYTE_RULE_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable byte token in Limbu map: {token!r}")
        values.append(int(match.group(1), 16))
        index += 1
    if not values:
        raise ValueError("empty byte class in Limbu map")
    return tuple(values)


def _expand_unicode_tokens(body: str) -> tuple[int, ...]:
    values: list[int] = []
    tokens = _tokens(body)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start_match = _UNICODE_RULE_RE.fullmatch(token)
            end_match = _UNICODE_RULE_RE.fullmatch(tokens[index + 2])
            if start_match is None or end_match is None:
                raise ValueError(
                    f"invalid Unicode range in Limbu map: {token}..{tokens[index + 2]}"
                )
            start = _validate_unicode_scalar(int(start_match.group(1), 16))
            end = _validate_unicode_scalar(int(end_match.group(1), 16))
            if end < start:
                raise ValueError(
                    f"invalid Unicode range in Limbu map: {token}..{tokens[index + 2]}"
                )
            if start <= 0xDFFF and end >= 0xD800:
                raise ValueError(
                    f"invalid Unicode scalar range in Limbu map: {token}..{tokens[index + 2]}"
                )
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _UNICODE_RULE_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable Unicode token in Limbu map: {token!r}")
        values.append(_validate_unicode_scalar(int(match.group(1), 16)))
        index += 1
    if not values:
        raise ValueError("empty Unicode class in Limbu map")
    return tuple(values)


def _parse_explicit_rule(line: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    match = _EXPLICIT_RULE_RE.fullmatch(line)
    if match is None:
        raise ValueError(f"invalid explicit Limbu rule: {line!r}")
    source = tuple(int(value, 16) for value in _BYTE_RULE_RE.findall(match.group("source")))
    target = tuple(
        _validate_unicode_scalar(int(value, 16))
        for value in _UNICODE_RULE_RE.findall(match.group("target"))
    )
    return source, target


@dataclass(frozen=True)
class LimbuConversion:
    legacy_text: str
    unicode_text: str
    limbu_char_count: int
    replacement_count: int
    unmapped_codepoints: list[str]


@dataclass(frozen=True)
class _LimbuReorderContract:
    vowels: frozenset[int]
    subjoined: frozenset[int]
    kemphreng: int
    provenance: str


_DEFAULT_REORDER_CONTRACT = _LimbuReorderContract(
    vowels=_VOWELS,
    subjoined=_SUBJOINED,
    kemphreng=_KEMPHRENG,
    provenance="legacy-byte-derived-only",
)


@dataclass(frozen=True)
class _LimbuContract:
    rules: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]
    reorder: _LimbuReorderContract


class LimbuConverter:
    """Forward ``Byte_Unicode`` reader for the SIL Namdhinggo Limbu legacy map."""

    def __init__(self, rules: Iterable[tuple[Iterable[int], Iterable[int]]]) -> None:
        normalized_rules = [(tuple(source), tuple(target)) for source, target in rules]
        if not normalized_rules:
            raise ValueError("LimbuConverter requires at least one mapping rule")
        seen: set[tuple[int, ...]] = set()
        for source, target in normalized_rules:
            if not source or any(
                isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= 0xFF)
                for value in source
            ):
                raise ValueError(f"invalid Limbu source rule: {source!r}")
            if not target:
                raise ValueError(f"empty Limbu target rule for source: {source!r}")
            for codepoint in target:
                _validate_unicode_scalar(codepoint)
            if source in seen:
                label = " ".join(f"0x{value:02X}" for value in source)
                raise ValueError(f"duplicate Limbu source rule: {label}")
            seen.add(source)
        # Longest source sequences first so multi-byte rules win.
        self._contract = _LimbuContract(
            rules=tuple(sorted(normalized_rules, key=lambda item: len(item[0]), reverse=True)),
            reorder=_DEFAULT_REORDER_CONTRACT,
        )

    @property
    def _rules(self) -> tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]:
        return self._contract.rules

    @classmethod
    def from_map_file(cls, path: str | Path) -> "LimbuConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"Limbu legacy map does not exist: {map_path}")
        byte_classes: dict[str, tuple[int, ...]] = {}
        unicode_classes: dict[str, tuple[int, ...]] = {}
        rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        in_byte_pass = False
        seen_passes: set[str] = set()
        seen_defaults: set[str] = set()
        rule_lines: list[str] = []
        for raw_line in map_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.split(";", 1)[0].strip()
            if not line:
                continue
            if _PASS_PREFIX_RE.match(line):
                pass_match = _PASS_RE.fullmatch(line)
                if pass_match is None:
                    raise ValueError(f"invalid Limbu pass declaration: {line!r}")
                pass_name = pass_match.group(1).casefold()
                if pass_name in seen_passes:
                    raise ValueError(f"duplicate Limbu pass declaration: {line!r}")
                seen_passes.add(pass_name)
                in_byte_pass = pass_name == "byte_unicode"
                continue
            if not in_byte_pass:
                continue
            if _DEFAULT_PREFIX_RE.match(line):
                if _BYTE_DEFAULT_RE.fullmatch(line) or _UNI_DEFAULT_RE.fullmatch(line):
                    default_name = line.split(None, 1)[0].casefold()
                    if default_name in seen_defaults:
                        raise ValueError(f"duplicate Limbu default declaration: {line!r}")
                    seen_defaults.add(default_name)
                    continue
                raise ValueError(f"invalid Limbu default declaration: {line!r}")
            byte_match = _BYTECLASS_RE.match(line)
            if byte_match:
                name = byte_match.group(1).strip()
                if not name:
                    raise ValueError("empty Limbu byte class name")
                if name in byte_classes:
                    raise ValueError(f"duplicate Limbu byte class: {name!r}")
                byte_classes[name] = _expand_byte_tokens(byte_match.group(2))
                continue
            unicode_match = _UNICLASS_RE.match(line)
            if unicode_match:
                name = unicode_match.group(1).strip()
                if not name:
                    raise ValueError("empty Limbu Unicode class name")
                if name in unicode_classes:
                    raise ValueError(f"duplicate Limbu Unicode class: {name!r}")
                unicode_classes[name] = _expand_unicode_tokens(unicode_match.group(2))
                continue
            rule_lines.append(line)

        for line in rule_lines:
            class_match = _CLASS_RULE_RE.match(line)
            if class_match:
                byte_name, unicode_name = (name.strip() for name in class_match.groups())
                if not byte_name or not unicode_name:
                    raise ValueError(f"empty Limbu class reference: {line!r}")
                byte_values = byte_classes.get(byte_name)
                unicode_values = unicode_classes.get(unicode_name)
                if byte_values is None:
                    raise ValueError(
                        f"Limbu class rule references unknown byte class: {byte_name!r}"
                    )
                if unicode_values is None:
                    raise ValueError(
                        f"Limbu class rule references unknown Unicode class: {unicode_name!r}"
                    )
                if len(byte_values) != len(unicode_values):
                    raise ValueError(
                        f"Limbu class rule length mismatch for [{byte_name}]>[{unicode_name}]: "
                        f"{len(byte_values)} bytes vs {len(unicode_values)} codepoints"
                    )
                rules.extend(
                    ((byte_value,), (codepoint,))
                    for byte_value, codepoint in zip(byte_values, unicode_values)
                )
                continue
            rules.append(_parse_explicit_rule(line))
        return cls(rules)

    @classmethod
    def default(cls) -> "LimbuConverter":
        with resources.as_file(resources.files("nepal_ttf2utf.maps") / "Limbu.map") as p:
            return cls.from_map_file(p)

    def _byte_pass_with_provenance(self, text: str) -> tuple[str, tuple[bool, ...], int, list[str]]:
        output: list[str] = []
        derived: list[bool] = []
        unmapped: list[str] = []
        replacements = 0
        index = 0
        while index < len(text):
            code = ord(text[index])
            matched = False
            for source, target in self._rules:
                if self._matches(text, index, source):
                    output.extend(chr(value) for value in target)
                    derived.extend([True] * len(target))
                    replacements += 1
                    index += len(source)
                    matched = True
                    break
            if matched:
                continue
            output.append(text[index])
            derived.append(False)
            if text[index] not in STRUCTURAL_C0 and not _is_assigned_script_codepoint(
                code, "Limbu"
            ):
                unmapped.append(f"U+{code:04X}")
            index += 1
        return "".join(output), tuple(derived), replacements, unmapped

    def convert(self, text: str) -> LimbuConversion:
        mapped, derived, replacements, unmapped = self._byte_pass_with_provenance(text)
        converted = _reorder_limbu(mapped, derived, contract=self._contract.reorder)
        converted = unicodedata.normalize("NFC", converted)
        # SIL's CTL class preserves every C0 value. Keep that exact lenient
        # mapping/count behavior but diagnose values outside the allowlist.
        unmapped.extend(diagnostic_c0_codepoints(converted))
        return LimbuConversion(
            legacy_text=text,
            unicode_text=converted,
            limbu_char_count=len(_LIMBU_CODEPOINT_RE.findall(converted)),
            replacement_count=replacements,
            unmapped_codepoints=sorted(set(unmapped)),
        )

    @staticmethod
    def _matches(text: str, index: int, source: tuple[int, ...]) -> bool:
        if index + len(source) > len(text):
            return False
        return all(ord(text[index + offset]) == code for offset, code in enumerate(source))


def _reorder_limbu(
    text: str,
    derived: tuple[bool, ...] | None = None,
    *,
    contract: _LimbuReorderContract = _DEFAULT_REORDER_CONTRACT,
) -> str:
    if derived is None:
        derived = (True,) * len(text)
    if (
        type(derived) is not tuple
        or len(derived) != len(text)
        or any(type(value) is not bool for value in derived)
    ):
        raise ValueError("invalid Limbu reorder provenance")
    chars = list(text)
    provenance = list(derived)
    index = 0
    while index < len(chars) - 1:
        current = ord(chars[index])
        nxt = ord(chars[index + 1])
        if current in contract.vowels and nxt in contract.subjoined:
            if provenance[index] and provenance[index + 1]:
                chars[index], chars[index + 1] = chars[index + 1], chars[index]
                provenance[index], provenance[index + 1] = (
                    provenance[index + 1],
                    provenance[index],
                )
            index += 2
            continue
        if (
            index < len(chars) - 2
            and current in contract.vowels
            and ord(chars[index + 1]) == contract.kemphreng
            and ord(chars[index + 2]) in contract.subjoined
        ):
            if all(provenance[index : index + 3]):
                vowel = chars[index]
                subjoined = chars[index + 2]
                chars[index : index + 3] = [subjoined, vowel, chr(contract.kemphreng)]
                vowel_derived = provenance[index]
                subjoined_derived = provenance[index + 2]
                kemphreng_derived = provenance[index + 1]
                provenance[index : index + 3] = [
                    subjoined_derived,
                    vowel_derived,
                    kemphreng_derived,
                ]
            index += 3
            continue
        index += 1
    return "".join(chars)


_DEFAULT: LimbuConverter | None = None


def convert_limbu(text: str, *, strict: bool = False) -> str:
    """Convert Namdhinggo-legacy Limbu text to Unicode Limbu (NFC).

    The string return type is retained for compatibility. Use
    :meth:`LimbuConverter.convert` for counts and the unmapped-codepoint list.
    With ``strict=True``, input absent from the SIL map or the pinned assigned
    Limbu repertoire raises ``ValueError``.
    """
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = LimbuConverter.default()
    result = _DEFAULT.convert(text)
    if strict and result.unmapped_codepoints:
        raise ValueError(
            "unmapped/leftover characters after Limbu conversion: "
            + " ".join(result.unmapped_codepoints)
        )
    return result.unicode_text
