"""Limbu/Sirijonga legacy-font (Namdhinggo SIL) -> Unicode Limbu (U+1900-U+194F).

Applies the forward explicit assignments from the SIL TECkit ``Byte_Unicode`` pass,
including positional class rules, in the vendored ``Limbu.map``. It also applies the
vowel / subjoined-consonant reordering that Unicode logical order requires. Validated
against real Gorkhapatra Limbu/Sirijonga newspaper pages.
"""

from __future__ import annotations

import re
import unicodedata
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
_LIMBU_CODEPOINT_RE = re.compile(r"[ᤀ-᥏]")
_VOWEL_RANGE = range(0x1920, 0x1929)
_SUBJOINED_RANGE = range(0x1929, 0x192C)
_KEMPHRENG = "᤺"


def _tokens(body: str) -> list[str]:
    body = re.sub(r"\s*\.\.\s*", " .. ", body)
    return [token for token in body.split() if token]


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
            start = int(start_match.group(1), 16)
            end = int(end_match.group(1), 16)
            if end < start:
                raise ValueError(
                    f"invalid Unicode range in Limbu map: {token}..{tokens[index + 2]}"
                )
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _UNICODE_RULE_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable Unicode token in Limbu map: {token!r}")
        values.append(int(match.group(1), 16))
        index += 1
    return tuple(values)


@dataclass(frozen=True)
class LimbuConversion:
    legacy_text: str
    unicode_text: str
    limbu_char_count: int
    replacement_count: int
    unmapped_codepoints: list[str]


class LimbuConverter:
    """Forward ``Byte_Unicode`` reader for the SIL Namdhinggo Limbu legacy map."""

    def __init__(self, rules: list[tuple[tuple[int, ...], tuple[int, ...]]]) -> None:
        if not rules:
            raise ValueError("LimbuConverter requires at least one mapping rule")
        # longest source sequences first so multi-byte rules win.
        self._rules = sorted(rules, key=lambda item: len(item[0]), reverse=True)

    @classmethod
    def from_map_file(cls, path: str | Path) -> "LimbuConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"Limbu legacy map does not exist: {map_path}")
        byte_classes: dict[str, tuple[int, ...]] = {}
        unicode_classes: dict[str, tuple[int, ...]] = {}
        rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        in_byte_pass = False
        rule_lines: list[str] = []
        for raw_line in map_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.split(";", 1)[0].strip()
            if not line:
                continue
            lowered = line.lower()
            if lowered.startswith("pass("):
                in_byte_pass = lowered == "pass(byte_unicode)"
                continue
            if not in_byte_pass:
                continue
            byte_match = _BYTECLASS_RE.match(line)
            if byte_match:
                byte_classes[byte_match.group(1).strip()] = _expand_byte_tokens(byte_match.group(2))
                continue
            unicode_match = _UNICLASS_RE.match(line)
            if unicode_match:
                unicode_classes[unicode_match.group(1).strip()] = _expand_unicode_tokens(
                    unicode_match.group(2)
                )
                continue
            rule_lines.append(line)

        for line in rule_lines:
            class_match = _CLASS_RULE_RE.match(line)
            if class_match:
                byte_name, unicode_name = (name.strip() for name in class_match.groups())
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
            if "<>" not in line and ">" not in line:
                continue
            left, right = line.split("<>", 1) if "<>" in line else line.split(">", 1)
            source = tuple(int(value, 16) for value in _BYTE_RULE_RE.findall(left))
            target = tuple(int(value, 16) for value in _UNICODE_RULE_RE.findall(right))
            if source and target:
                rules.append((source, target))
        return cls(rules)

    @classmethod
    def default(cls) -> "LimbuConverter":
        with resources.as_file(resources.files("nepal_ttf2utf.maps") / "Limbu.map") as p:
            return cls.from_map_file(p)

    def convert(self, text: str) -> LimbuConversion:
        output: list[str] = []
        unmapped: list[str] = []
        replacements = 0
        index = 0
        while index < len(text):
            code = ord(text[index])
            matched = False
            for source, target in self._rules:
                if self._matches(text, index, source):
                    output.extend(chr(value) for value in target)
                    replacements += 1
                    index += len(source)
                    matched = True
                    break
            if matched:
                continue
            output.append(text[index])
            if text[index] not in STRUCTURAL_C0 and not _is_assigned_script_codepoint(
                code, "Limbu"
            ):
                unmapped.append(f"U+{code:04X}")
            index += 1
        converted = _reorder_limbu(("".join(output)))
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


def _reorder_limbu(text: str) -> str:
    chars = list(text)
    index = 0
    while index < len(chars) - 1:
        current = ord(chars[index])
        nxt = ord(chars[index + 1])
        if current in _VOWEL_RANGE and nxt in _SUBJOINED_RANGE:
            chars[index], chars[index + 1] = chars[index + 1], chars[index]
            index += 2
            continue
        if (
            index < len(chars) - 2
            and current in _VOWEL_RANGE
            and chars[index + 1] == _KEMPHRENG
            and ord(chars[index + 2]) in _SUBJOINED_RANGE
        ):
            vowel = chars[index]
            subjoined = chars[index + 2]
            chars[index : index + 3] = [subjoined, vowel, _KEMPHRENG]
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
