"""Limbu/Sirijonga legacy-font (Namdhinggo SIL) -> Unicode Limbu (U+1900-U+194F).

Ports the SIL TECkit ``Byte_Unicode`` pass from the vendored ``Limbu.map`` and applies
the vowel / subjoined-consonant reordering that Unicode logical order requires. Validated
against real Gorkhapatra Limbu/Sirijonga newspaper pages.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

_BYTE_RULE_RE = re.compile(r"0x([0-9A-Fa-f]{2})")
_UNICODE_RULE_RE = re.compile(r"U\+([0-9A-Fa-f]{4,6})")
_LIMBU_CODEPOINT_RE = re.compile(r"[ᤀ-᥏]")
_VOWEL_RANGE = range(0x1920, 0x1929)
_SUBJOINED_RANGE = range(0x1929, 0x192C)
_KEMPHRENG = "᤺"


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
        rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        in_byte_pass = False
        for raw_line in map_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split(";", 1)[0].strip()
            if not line:
                continue
            if line.startswith("Pass("):
                in_byte_pass = line == "Pass(Byte_Unicode)"
                continue
            if not in_byte_pass or ("<>" not in line and ">" not in line):
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
            # The legacy map has an explicit rule for ASCII space. Preserve the
            # other structural whitespace outside the byte map so multiline
            # boundaries never become unresolved legacy input.
            if text[index] in "\t\r\n":
                output.append(text[index])
                index += 1
                continue
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
            if not (0x1900 <= code <= 0x194F):
                unmapped.append(f"U+{code:04X}")
            index += 1
        converted = _reorder_limbu(("".join(output)))
        converted = unicodedata.normalize("NFC", converted)
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
    With ``strict=True``, any byte absent from the SIL map raises ``ValueError``.
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
