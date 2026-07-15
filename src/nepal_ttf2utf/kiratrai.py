"""Legacy Kirat Rai fonts -> Unicode Kirat Rai (U+16D40-U+16D7F).

SIL publishes a TECkit map for the canonical 2021 ``kirat rai font new`` encoding;
the vendored copy lives at ``maps/kiratraifontnew.map``. Sikkim Herald PDFs use a
different, older layout hidden behind per-PDF CID subsets and ASCII ToUnicode values.
Four independently subset Herald PDFs share one stable old->new remap: exact glyph
outline plus advance-width identity covers the observed script characters. The
Herald converter applies that complete premap before the SIL rules.

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
import unicodedata
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

_KIRATRAI_CODEPOINT_RE = re.compile(r"[\U00016D40-\U00016D7F]")
_BYTE_TOKEN_RE = re.compile(r"0x([0-9A-Fa-f]{2})")
_UNI_TOKEN_RE = re.compile(r"U\+([0-9A-Fa-f]{4,6})")
_BYTECLASS_RE = re.compile(r"^ByteClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_UNICLASS_RE = re.compile(r"^UniClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_CLASS_RULE_RE = re.compile(r"^\[([^\]]+)\]\s*<?>\s*\[([^\]]+)\]\s*$")

_KIRATRAI_LO, _KIRATRAI_HI = 0x16D40, 0x16D7F

# Bytes absent from SIL's canonical-new map. Kept as a public compatibility constant;
# in Herald PDFs these ASCII values belong to the separate permuted layout below.
KIRATRAI_UNMAPPED_BYTES: frozenset[str] = frozenset("fRxFIL\\")

# Sikkim Herald extracted ASCII -> canonical ``kiratraifontnew`` byte. Derived by exact
# RecordingPen outline-command and advance-width identity against the font embedded in
# Unicode proposal L2/22-043R. Shared by four PDF subsets and 43,037 exact-match chars.
KIRATRAI_HERALD_PREMAP: dict[str, str] = {
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

# Values confirmed as identity/literal in the audited Herald PDFs. Backslash and
# Herald ``Z`` are separate blank glyphs normalized to ordinary spaces. Canonical
# ``kiratraifontnew`` Z remains U+16D6C and is unaffected.
KIRATRAI_HERALD_PASSTHROUGH: frozenset[str] = frozenset(" \t\r\n0123456789(),-/.;")
KIRATRAI_HERALD_BLANKS: frozenset[str] = frozenset("\\Z")


def _expand_byte_tokens(body: str) -> tuple[int, ...]:
    """Expand a TECkit byte-class body into ordered byte values (``0xNN`` or ``0xNN .. 0xMM``)."""
    values: list[int] = []
    tokens = re.split(r"\s+", body.strip())
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token:
            index += 1
            continue
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start = int(token, 16)
            end = int(tokens[index + 2], 16)
            if end < start:
                raise ValueError(
                    f"invalid byte range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            values.extend(range(start, end + 1))
            index += 3
            continue
        values.append(int(token, 16))
        index += 1
    return tuple(values)


def _expand_uni_tokens(body: str) -> tuple[int, ...]:
    """Expand a TECkit Unicode-class body into ordered codepoints (``U+NNNN`` or ranges)."""
    values: list[int] = []
    tokens = re.split(r"\s+", body.strip())
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not token:
            index += 1
            continue
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start_match = _UNI_TOKEN_RE.match(token)
            end_match = _UNI_TOKEN_RE.match(tokens[index + 2])
            if start_match is None or end_match is None:
                raise ValueError(
                    f"unparseable unicode range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            start = int(start_match.group(1), 16)
            end = int(end_match.group(1), 16)
            if end < start:
                raise ValueError(
                    f"invalid unicode range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _UNI_TOKEN_RE.match(token)
        if match is None:
            raise ValueError(f"unparseable unicode token in Kirat Rai map: {token!r}")
        values.append(int(match.group(1), 16))
        index += 1
    return tuple(values)


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

    def __init__(self, rules: list[tuple[tuple[int, ...], tuple[int, ...]]]) -> None:
        if not rules:
            raise ValueError("KiratRaiConverter requires at least one mapping rule")
        # De-duplicate while preserving longest-source-first ordering.
        seen: set[tuple[int, ...]] = set()
        ordered: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        for source, target in sorted(rules, key=lambda item: len(item[0]), reverse=True):
            if source in seen:
                continue
            seen.add(source)
            ordered.append((source, target))
        self._rules = ordered

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
            uni_match = _UNICLASS_RE.match(line)
            if uni_match:
                uni_classes[uni_match.group(1).strip()] = _expand_uni_tokens(uni_match.group(2))
                continue
            rule_lines.append(line)

        for line in rule_lines:
            class_rule = _CLASS_RULE_RE.match(line)
            if class_rule:
                left_name = class_rule.group(1).strip()
                right_name = class_rule.group(2).strip()
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
            if "<>" in line or ">" in line:
                left_text, right_text = line.split("<>", 1) if "<>" in line else line.split(">", 1)
                source = _BYTE_TOKEN_RE.findall(left_text)
                target = _UNI_TOKEN_RE.findall(right_text)
                if source and target:
                    rules.append(
                        (
                            tuple(int(value, 16) for value in source),
                            tuple(int(value, 16) for value in target),
                        )
                    )
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
            if not (_KIRATRAI_LO <= code <= _KIRATRAI_HI):
                unmapped.append(f"U+{code:04X}")
            index += 1
        converted = unicodedata.normalize("NFC", "".join(output))
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


class KiratRaiHeraldConverter:
    """Convert the permuted Sikkim Herald PDF layout through the canonical SIL map."""

    def __init__(self, canonical: KiratRaiConverter) -> None:
        self._canonical = canonical

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
            remapped = KIRATRAI_HERALD_PREMAP.get(char)
            if remapped is not None:
                canonical_run.append(remapped)
                continue
            if char in KIRATRAI_HERALD_BLANKS:
                canonical_run.append(" ")
                continue
            if char in KIRATRAI_HERALD_PASSTHROUGH:
                canonical_run.append(char)
                continue
            if _KIRATRAI_LO <= ord(char) <= _KIRATRAI_HI:
                flush()
                output.append(char)
                continue
            flush()
            output.append(char)
            unmapped.add(f"U+{ord(char):04X}")
        flush()

        converted = unicodedata.normalize("NFC", "".join(output))
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
