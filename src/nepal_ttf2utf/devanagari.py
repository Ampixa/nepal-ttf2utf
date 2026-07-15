"""Legacy ASCII Devanagari fonts -> Unicode Devanagari (U+0900-U+097F).

Builds on the tested ``npttf2utf`` font maps (Preeti, Kantipur, Sagarmatha, PCS Nepali,
Fontasy Himali) and adds:

- ``nayanepal`` / Gorkhapatra newspaper-font support (Preeti-family + extension glyphs
  ``ƒ``->र and ``†``->्), validated against real Gorkhapatra pages (97-99% clean
  Devanagari output, anchors गोरखापत्रद्वारा / प्रकाशित / नेपाल / मगर correct).
- whitespace + smart-punctuation normalization,
- a strict mode that surfaces leftover non-Devanagari bytes instead of silently dropping
  them (the failure mode of most legacy converters),
- optional Kiranti glottal-stop normalization to U+097D.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field

from ._controls import DIAGNOSTIC_C0

# Strip C0 values outside the package's structural allowlist. TAB, LF, and CR
# are data boundaries for multiline conversion, not font bytes.
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# nayanepal/Gorkhapatra extension glyphs not present in the base Preeti map.
_NAYANEPAL_EXT = {"ƒ": "र", "†": "्"}
# Cosmetic normalizations: narrow-no-break-space, smart quotes/dashes -> plain forms.
_PUNCT_NORMALIZE = {" ": " ", "‘": "'", "’": "'", "–": "-", "—": "-"}

# Fonts handled directly by the bundled npttf2utf maps.
_NPTTF2UTF_FONTS = {
    "preeti": "Preeti",
    "kantipur": "Kantipur",
    "sagarmatha": "Sagarmatha",
    "pcs-nepali": "PCS NEPALI",
    "fontasy-himali": "FONTASY_HIMALI_TT",
}
# Fonts that are Preeti-family with extra extension glyphs.
_PREETI_FAMILY_EXT = {"nayanepal": _NAYANEPAL_EXT, "gorkhapatra": _NAYANEPAL_EXT}

_FONT_MAPPER = None


def _font_mapper():
    global _FONT_MAPPER
    if _FONT_MAPPER is None:
        import npttf2utf  # tested base maps

        path = os.path.join(os.path.dirname(npttf2utf.__file__), "map.json")
        _FONT_MAPPER = npttf2utf.FontMapper(path)
    return _FONT_MAPPER


@dataclass
class DevanagariConversion:
    legacy_text: str
    unicode_text: str
    clean: bool
    leftover: list[str] = field(default_factory=list)


def supported_devanagari_fonts() -> list[str]:
    return sorted(set(_NPTTF2UTF_FONTS) | set(_PREETI_FAMILY_EXT))


def convert_devanagari(
    text: str,
    font: str = "preeti",
    *,
    strict: bool = False,
    normalize_glottal_stop: bool = False,
) -> DevanagariConversion:
    """Convert a legacy Devanagari ASCII-font string to Unicode Devanagari (NFC)."""
    key = font.strip().lower()
    if key in _PREETI_FAMILY_EXT:
        base_font = "Preeti"
        ext = _PREETI_FAMILY_EXT[key]
    elif key in _NPTTF2UTF_FONTS:
        base_font = _NPTTF2UTF_FONTS[key]
        ext = {}
    else:
        raise ValueError(
            f"unsupported Devanagari font {font!r}; supported: {supported_devanagari_fonts()}"
        )

    out = _font_mapper().map_to_unicode(_CTRL.sub("", text), from_font=base_font)
    for src, dst in ext.items():
        out = out.replace(src, dst)
    for src, dst in _PUNCT_NORMALIZE.items():
        out = out.replace(src, dst)
    if normalize_glottal_stop:
        # Kiranti/Rai glottal stop written as a colon-like mark -> DEVANAGARI LETTER
        # GLOTTAL STOP (U+097D). Opt-in: only meaningful for Kiranti orthographies.
        out = out.replace("ʻ", "ॽ")
    out = unicodedata.normalize("NFC", out)

    leftover = sorted(
        (
            {
                c
                for c in out
                if not (0x0900 <= ord(c) <= 0x097F)
                and c not in " \t\r\n।॥,.?!:;'\"()[]-/0123456789"
            }
        )
        | (set(text) & DIAGNOSTIC_C0)
    )
    clean = not leftover
    if strict and not clean:
        raise ValueError(
            f"unmapped/leftover characters after {font} conversion: "
            + " ".join(f"U+{ord(c):04X}" for c in leftover)
        )
    return DevanagariConversion(legacy_text=text, unicode_text=out, clean=clean, leftover=leftover)
