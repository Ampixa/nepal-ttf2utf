"""Validation and normalization for font spans that already contain Unicode.

Some source documents label text with a script-specific font even though the
text layer already stores the intended Unicode characters.  These spans need
normalization and validation, not a legacy byte map.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class UnicodeSpanConversion:
    """Result of validating an already-Unicode font span."""

    source_text: str
    unicode_text: str
    script: str
    script_char_count: int
    invalid_codepoints: list[str]


_SCRIPT_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "Devanagari": (
        (0x0900, 0x097F),
        (0x1CD0, 0x1CFF),
        (0xA8E0, 0xA8FF),
        (0x11B00, 0x11B5F),
    ),
    "Newa": ((0x11400, 0x1147F),),
    "Tibetan": ((0x0F00, 0x0FFF),),
}


def _in_script(codepoint: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)


def validate_unicode_span(
    text: str,
    *,
    script: str,
    strict: bool = False,
) -> UnicodeSpanConversion:
    """Normalize and validate text already encoded for ``script``.

    Common punctuation, whitespace, digits, and embedded Latin text are kept.
    Invalid Unicode replacement characters, surrogates, unassigned values, and
    non-text controls are reported. In strict mode, a nonempty span must also
    contain at least one character from the declared script.
    """
    try:
        ranges = _SCRIPT_RANGES[script]
    except KeyError as error:
        raise ValueError(f"unsupported Unicode span script {script!r}") from error

    normalized = unicodedata.normalize("NFC", text)
    invalid: set[str] = set()
    script_count = 0
    for char in normalized:
        codepoint = ord(char)
        if _in_script(codepoint, ranges):
            script_count += 1
        category = unicodedata.category(char)
        if (
            char == "\ufffd"
            or category in {"Cs", "Cn"}
            or (category == "Cc" and char not in "\t\r\n")
        ):
            invalid.add(f"U+{codepoint:04X}")

    if strict and normalized.strip() and script_count == 0:
        raise ValueError(f"nonempty {script} span contains no {script} characters")
    if strict and invalid:
        raise ValueError(
            f"invalid characters in Unicode {script} span: " + " ".join(sorted(invalid))
        )

    return UnicodeSpanConversion(
        source_text=text,
        unicode_text=normalized,
        script=script,
        script_char_count=script_count,
        invalid_codepoints=sorted(invalid),
    )
