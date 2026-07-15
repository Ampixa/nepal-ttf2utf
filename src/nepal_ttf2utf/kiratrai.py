"""Legacy Kirat Rai fonts -> Unicode Kirat Rai (U+16D40-U+16D7F).

SIL publishes a TECkit map for the canonical 2021 ``kirat rai font new`` encoding;
the vendored copy lives at ``maps/kiratraifontnew.map``. Four audited Sikkim Herald
PDF subsets use a different, older layout hidden behind per-PDF CIDs and ASCII
ToUnicode values. The package's frozen Herald routing snapshot applies the observed
38-entry old-to-new premap before the SIL rules. The source PDFs and intermediate
outline-comparison artifacts are not distributed; ``docs/EVIDENCE.md`` records the
derivation boundary.

That map is expressed with TECkit ``ByteClass`` / ``UniClass`` declarations plus a
handful of explicit multi-byte ligature rules. A ``[class] > [class]`` rule maps the
byte at position *n* of the byte class to the codepoint at position *n* of the paired
Unicode class. This module reads the map natively (no ``teckit_compile`` dependency)
and applies the forward Legacy->Unicode pass, longest-match-first so the multi-byte
ligature rules win over the single-byte class rules.

The two layouts must not be auto-detected from text: even old-layout strings without
the formerly conspicuous ``f R x F I L`` bytes are globally permuted. Callers must
select the canonical-new or Herald alias explicitly. The sole extracted Herald ``Z``
is a blank spacing glyph and is normalized to an ordinary space.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from types import MappingProxyType

from ._controls import diagnostic_c0_codepoints
from .unicode_span import _is_assigned_script_codepoint, _normalize_nfc

_KIRATRAI_CODEPOINT_RE = re.compile(r"[\U00016D40-\U00016D7F]")
_BYTE_TOKEN_RE = re.compile(r"0x([0-9A-Fa-f]{2})")
_UNI_TOKEN_RE = re.compile(r"U\+([0-9A-Fa-f]{4,6})")
_BYTECLASS_RE = re.compile(r"^ByteClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_UNICLASS_RE = re.compile(r"^UniClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_CLASS_RULE_RE = re.compile(r"^\[([^\]]+)\]\s*<?>\s*\[([^\]]+)\]\s*$")
_PASS_RE = re.compile(r"^Pass\(\s*(Byte_Unicode|Unicode)\s*\)$", re.IGNORECASE)
_PASS_PREFIX_RE = re.compile(r"^Pass\b", re.IGNORECASE)
_EXPLICIT_RULE_RE = re.compile(
    r"^(?P<source>0x[0-9A-Fa-f]{2}(?:\s+0x[0-9A-Fa-f]{2})*)\s*"
    r"(?:<>|>)\s*"
    r"(?P<target>U\+[0-9A-Fa-f]{4,6}(?:\s+U\+[0-9A-Fa-f]{4,6})*)$"
)

_KIRATRAI_LO, _KIRATRAI_HI = 0x16D40, 0x16D7F

# Bytes absent from SIL's canonical-new map. Kept as a public compatibility constant;
# in Herald PDFs these ASCII values belong to the separate permuted layout below.
KIRATRAI_UNMAPPED_BYTES: frozenset[str] = frozenset("fRxFIL\\")

# Sikkim Herald extracted ASCII -> canonical ``kiratraifontnew`` byte. The
# project-derived values are the complete distributed premap observed across the
# four audited PDF subsets; they do not claim a universal Herald encoding.
KIRATRAI_HERALD_PREMAP: Mapping[str, str] = MappingProxyType(
    {
        "D": "q",
        "F": "g",
        "G": "P",
        "H": "j",
        "I": "W",
        "J": "J",
        "K": "Q",
        "L": "$",
        "O": "O",
        "R": "w",
        "S": "G",
        "U": "o",
        "a": "k",
        "b": "A",
        "c": "D",
        "d": "K",
        "e": "m",
        "f": "N",
        "g": "s",
        "h": "a",
        "i": "v",
        "j": "b",
        "k": "r",
        "l": "i",
        "m": "c",
        "n": "p",
        "o": "n",
        "p": "t",
        "q": "d",
        "r": "e",
        "s": "C",
        "t": "h",
        "u": "u",
        "v": "B",
        "w": "l",
        "x": "T",
        "y": "y",
        "z": "z",
    }
)

# Values forwarded unchanged to the canonical map. Digits and slash consequently
# become Kirat Rai characters; the remaining values stay literal. Backslash and
# Herald ``Z`` are separate blank glyphs normalized to ordinary spaces. Canonical
# ``kiratraifontnew`` Z remains U+16D6C and is unaffected.
KIRATRAI_HERALD_PASSTHROUGH: frozenset[str] = frozenset(" \t\r\n0123456789(),-/.;")
KIRATRAI_HERALD_BLANKS: frozenset[str] = frozenset("\\Z")


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
        raise ValueError(f"invalid Unicode scalar in Kirat Rai map: {codepoint!r}")
    return codepoint


def _expand_byte_tokens(body: str) -> tuple[int, ...]:
    """Expand a TECkit byte-class body into ordered byte values (``0xNN`` or ``0xNN .. 0xMM``)."""
    values: list[int] = []
    tokens = _tokens(body)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start_match = _BYTE_TOKEN_RE.fullmatch(token)
            end_match = _BYTE_TOKEN_RE.fullmatch(tokens[index + 2])
            if start_match is None or end_match is None:
                raise ValueError(
                    f"invalid byte range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            start = int(start_match.group(1), 16)
            end = int(end_match.group(1), 16)
            if end < start:
                raise ValueError(
                    f"invalid byte range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _BYTE_TOKEN_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable byte token in Kirat Rai map: {token!r}")
        values.append(int(match.group(1), 16))
        index += 1
    if not values:
        raise ValueError("empty byte class in Kirat Rai map")
    return tuple(values)


def _expand_uni_tokens(body: str) -> tuple[int, ...]:
    """Expand a TECkit Unicode-class body into ordered codepoints (``U+NNNN`` or ranges)."""
    values: list[int] = []
    tokens = _tokens(body)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start_match = _UNI_TOKEN_RE.fullmatch(token)
            end_match = _UNI_TOKEN_RE.fullmatch(tokens[index + 2])
            if start_match is None or end_match is None:
                raise ValueError(
                    f"unparseable unicode range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            start = _validate_unicode_scalar(int(start_match.group(1), 16))
            end = _validate_unicode_scalar(int(end_match.group(1), 16))
            if end < start:
                raise ValueError(
                    f"invalid unicode range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            if start <= 0xDFFF and end >= 0xD800:
                raise ValueError(
                    f"invalid Unicode scalar range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _UNI_TOKEN_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable unicode token in Kirat Rai map: {token!r}")
        values.append(_validate_unicode_scalar(int(match.group(1), 16)))
        index += 1
    if not values:
        raise ValueError("empty Unicode class in Kirat Rai map")
    return tuple(values)


def _parse_explicit_rule(line: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    match = _EXPLICIT_RULE_RE.fullmatch(line)
    if match is None:
        raise ValueError(f"invalid explicit Kirat Rai rule: {line!r}")
    source = tuple(int(value, 16) for value in _BYTE_TOKEN_RE.findall(match.group("source")))
    target = tuple(
        _validate_unicode_scalar(int(value, 16))
        for value in _UNI_TOKEN_RE.findall(match.group("target"))
    )
    return source, target


@dataclass(frozen=True)
class KiratRaiConversion:
    legacy_text: str
    unicode_text: str
    kiratrai_char_count: int
    replacement_count: int
    unmapped_codepoints: list[str]


class KiratRaiConverter:
    """Native reader/applier for SIL's ``kiratraifontnew.map`` TECkit mapping.

    Rules are flattened to ``(source_bytes, target_codepoints)`` pairs and applied
    longest-match-first so explicit multi-byte ligature rules (e.g. ``//`` -> double
    danda) take precedence over the single-byte class rules.
    """

    def __init__(self, rules: Iterable[tuple[Iterable[int], Iterable[int]]]) -> None:
        normalized_rules = [(tuple(source), tuple(target)) for source, target in rules]
        if not normalized_rules:
            raise ValueError("KiratRaiConverter requires at least one mapping rule")
        seen: set[tuple[int, ...]] = set()
        for source, target in normalized_rules:
            if not source or any(
                isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= 0xFF)
                for value in source
            ):
                raise ValueError(f"invalid Kirat Rai source rule: {source!r}")
            if not target:
                raise ValueError(f"empty Kirat Rai target rule for source: {source!r}")
            for codepoint in target:
                _validate_unicode_scalar(codepoint)
            if source in seen:
                label = " ".join(f"0x{value:02X}" for value in source)
                raise ValueError(f"duplicate Kirat Rai source rule: {label}")
            seen.add(source)
        self._rules = tuple(sorted(normalized_rules, key=lambda item: len(item[0]), reverse=True))

    @classmethod
    def from_map_file(cls, path: str | Path) -> "KiratRaiConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"Kirat Rai legacy map does not exist: {map_path}")
        byte_classes: dict[str, tuple[int, ...]] = {}
        uni_classes: dict[str, tuple[int, ...]] = {}
        rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        in_byte_pass = False
        # First parse class declarations; collect rule lines for a second pass so class
        # rules can reference classes regardless of declaration order.
        rule_lines: list[str] = []
        for raw_line in map_path.read_text(encoding="utf-8-sig").splitlines():
            line = raw_line.split(";", 1)[0].strip()
            if not line:
                continue
            if _PASS_PREFIX_RE.match(line):
                pass_match = _PASS_RE.fullmatch(line)
                if pass_match is None:
                    raise ValueError(f"invalid Kirat Rai pass declaration: {line!r}")
                in_byte_pass = pass_match.group(1).casefold() == "byte_unicode"
                continue
            if not in_byte_pass:
                continue
            byte_match = _BYTECLASS_RE.match(line)
            if byte_match:
                name = byte_match.group(1).strip()
                if not name:
                    raise ValueError("empty Kirat Rai byte class name")
                if name in byte_classes:
                    raise ValueError(f"duplicate Kirat Rai byte class: {name!r}")
                byte_classes[name] = _expand_byte_tokens(byte_match.group(2))
                continue
            uni_match = _UNICLASS_RE.match(line)
            if uni_match:
                name = uni_match.group(1).strip()
                if not name:
                    raise ValueError("empty Kirat Rai Unicode class name")
                if name in uni_classes:
                    raise ValueError(f"duplicate Kirat Rai Unicode class: {name!r}")
                uni_classes[name] = _expand_uni_tokens(uni_match.group(2))
                continue
            rule_lines.append(line)

        for line in rule_lines:
            class_rule = _CLASS_RULE_RE.match(line)
            if class_rule:
                left_name = class_rule.group(1).strip()
                right_name = class_rule.group(2).strip()
                if not left_name or not right_name:
                    raise ValueError(f"empty Kirat Rai class reference: {line!r}")
                left = byte_classes.get(left_name)
                right = uni_classes.get(right_name)
                if left is None:
                    raise ValueError(
                        f"Kirat Rai class rule references unknown byte class: {left_name!r}"
                    )
                if right is None:
                    raise ValueError(
                        f"Kirat Rai class rule references unknown unicode class: {right_name!r}"
                    )
                if len(left) != len(right):
                    raise ValueError(
                        f"Kirat Rai class rule length mismatch for [{left_name}]>[{right_name}]: "
                        f"{len(left)} bytes vs {len(right)} codepoints"
                    )
                for byte_value, codepoint in zip(left, right):
                    rules.append(((byte_value,), (codepoint,)))
                continue
            rules.append(_parse_explicit_rule(line))
        return cls(rules)

    @classmethod
    def default(cls) -> "KiratRaiConverter":
        with resources.as_file(resources.files("nepal_ttf2utf.maps") / "kiratraifontnew.map") as p:
            return cls.from_map_file(p)

    def convert(self, text: str) -> KiratRaiConversion:
        output: list[str] = []
        unmapped: list[str] = []
        replacements = 0
        index = 0
        length = len(text)
        while index < length:
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
            char = text[index]
            output.append(char)
            code = ord(char)
            if not _is_assigned_script_codepoint(code, "Kirat Rai"):
                unmapped.append(f"U+{code:04X}")
            index += 1
        converted = _normalize_nfc("".join(output))
        # SIL's CTL class preserves every C0 value. Keep that exact lenient
        # mapping/count behavior but diagnose values outside the allowlist.
        unmapped.extend(diagnostic_c0_codepoints(converted))
        return KiratRaiConversion(
            legacy_text=text,
            unicode_text=converted,
            kiratrai_char_count=len(_KIRATRAI_CODEPOINT_RE.findall(converted)),
            replacement_count=replacements,
            unmapped_codepoints=sorted(set(unmapped)),
        )

    @staticmethod
    def _matches(text: str, index: int, source: tuple[int, ...]) -> bool:
        if index + len(source) > len(text):
            return False
        return all(ord(text[index + offset]) == code for offset, code in enumerate(source))


def _freeze_herald_contract() -> tuple[Mapping[str, str], frozenset[str], frozenset[str]]:
    """Validate and snapshot the fixed four-PDF Herald routing contract."""
    if not isinstance(KIRATRAI_HERALD_PREMAP, Mapping):
        raise ValueError("invalid Kirat Rai Herald premap")
    premap = dict(KIRATRAI_HERALD_PREMAP)
    passthrough = frozenset(KIRATRAI_HERALD_PASSTHROUGH)
    blanks = frozenset(KIRATRAI_HERALD_BLANKS)

    if len(premap) != 38:
        raise ValueError("Kirat Rai Herald premap must contain exactly 38 entries")
    if len(passthrough) != 21:
        raise ValueError("Kirat Rai Herald passthrough must contain exactly 21 values")
    if len(blanks) != 2:
        raise ValueError("Kirat Rai Herald blanks must contain exactly two values")

    for source, target in premap.items():
        if (
            type(source) is not str
            or len(source) != 1
            or ord(source) > 0xFF
            or type(target) is not str
            or len(target) != 1
            or ord(target) > 0xFF
        ):
            raise ValueError(f"invalid Kirat Rai Herald premap entry: {source!r}: {target!r}")
    if len(set(premap.values())) != len(premap):
        raise ValueError("Kirat Rai Herald premap targets must be one-to-one")

    for label, values in (("passthrough", passthrough), ("blank", blanks)):
        if any(type(value) is not str or len(value) != 1 or ord(value) > 0xFF for value in values):
            raise ValueError(f"invalid Kirat Rai Herald {label} value")

    source_sets = (set(premap), set(passthrough), set(blanks))
    if any(source_sets[left] & source_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("Kirat Rai Herald routing sources overlap")

    canonical = KiratRaiConverter.default()
    singleton_sources = {source[0] for source, _target in canonical._rules if len(source) == 1}
    unsupported_targets = sorted(
        target for target in premap.values() if ord(target) not in singleton_sources
    )
    if unsupported_targets:
        labels = " ".join(f"U+{ord(target):04X}" for target in unsupported_targets)
        raise ValueError(f"unsupported Kirat Rai Herald canonical target: {labels}")

    for value in set(premap.values()) | set(passthrough) | {" "}:
        result = canonical.convert(value)
        if result.replacement_count != 1 or result.unmapped_codepoints:
            raise ValueError(f"unclean Kirat Rai Herald canonical projection: {value!r}")

    return MappingProxyType(premap), passthrough, blanks


(
    _DEFAULT_HERALD_PREMAP,
    _DEFAULT_HERALD_PASSTHROUGH,
    _DEFAULT_HERALD_BLANKS,
) = _freeze_herald_contract()


class KiratRaiHeraldConverter:
    """Convert the frozen four-PDF Herald layout through a canonical SIL snapshot."""

    def __init__(self, canonical: KiratRaiConverter) -> None:
        if not isinstance(canonical, KiratRaiConverter):
            raise ValueError("KiratRaiHeraldConverter requires a KiratRaiConverter")
        self._canonical = KiratRaiConverter(canonical._rules)
        self._premap = _DEFAULT_HERALD_PREMAP
        self._passthrough = _DEFAULT_HERALD_PASSTHROUGH
        self._blanks = _DEFAULT_HERALD_BLANKS

    @classmethod
    def default(cls) -> "KiratRaiHeraldConverter":
        return cls(KiratRaiConverter.default())

    def convert(self, text: str) -> KiratRaiConversion:
        output: list[str] = []
        canonical_run: list[str] = []
        unmapped: set[str] = set()
        replacements = 0

        def flush() -> None:
            nonlocal replacements
            if not canonical_run:
                return
            result = self._canonical.convert("".join(canonical_run))
            output.append(result.unicode_text)
            replacements += result.replacement_count
            unmapped.update(result.unmapped_codepoints)
            canonical_run.clear()

        for char in text:
            remapped = self._premap.get(char)
            if remapped is not None:
                canonical_run.append(remapped)
                continue
            if char in self._blanks:
                canonical_run.append(" ")
                continue
            if char in self._passthrough:
                canonical_run.append(char)
                continue
            if _is_assigned_script_codepoint(ord(char), "Kirat Rai"):
                flush()
                output.append(char)
                continue
            flush()
            output.append(char)
            unmapped.add(f"U+{ord(char):04X}")
        flush()

        converted = _normalize_nfc("".join(output))
        return KiratRaiConversion(
            legacy_text=text,
            unicode_text=converted,
            kiratrai_char_count=len(_KIRATRAI_CODEPOINT_RE.findall(converted)),
            replacement_count=replacements,
            unmapped_codepoints=sorted(unmapped),
        )


_DEFAULT: KiratRaiConverter | None = None
_HERALD_DEFAULT: KiratRaiHeraldConverter | None = None


def convert_kiratrai(text: str, *, strict: bool = False) -> KiratRaiConversion:
    """Convert canonical ``kiratraifontnew`` text to Unicode Kirat Rai (NFC).

    This function applies SIL's map directly. Use :func:`convert_kiratrai_herald` for
    text extracted from the older/permuted Sikkim Herald PDF font.
    """
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = KiratRaiConverter.default()
    result = _DEFAULT.convert(text)
    if strict and result.unmapped_codepoints:
        raise ValueError(
            "unmapped/leftover characters after Kirat Rai conversion: "
            + " ".join(result.unmapped_codepoints)
        )
    return result


def convert_kiratrai_herald(text: str, *, strict: bool = False) -> KiratRaiConversion:
    """Convert Sikkim Herald's permuted Kirat Rai PDF text to Unicode (NFC)."""
    global _HERALD_DEFAULT
    if _HERALD_DEFAULT is None:
        _HERALD_DEFAULT = KiratRaiHeraldConverter.default()
    result = _HERALD_DEFAULT.convert(text)
    if strict and result.unmapped_codepoints:
        raise ValueError(
            "unmapped/leftover characters after Herald Kirat Rai conversion: "
            + " ".join(result.unmapped_codepoints)
        )
    return result
