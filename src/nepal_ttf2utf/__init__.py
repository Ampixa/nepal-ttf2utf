"""nepal_ttf2utf — legacy ASCII-font -> Unicode for the scripts of Nepal and its diaspora.

Fills the gap left by Nepali-only converters (e.g. npttf2utf, which covers a few
Devanagari ASCII fonts): one library covering Devanagari legacy fonts *including
newspaper fonts like nayanepal/Gorkhapatra* and the Limbu/Sirijonga script, with
correct handling of the special characters most converters silently drop.

    from nepal_ttf2utf import convert
    convert("g]kfn", font="preeti")       # -> 'नेपाल'   (Devanagari)
    convert("...", font="nayanepal")       # -> Gorkhapatra Devanagari, Unicode
    convert("<namdhinggo bytes>", font="namdhinggo")  # -> Unicode Limbu (Sirijonga)
"""

from __future__ import annotations

from .devanagari import (
    DevanagariConversion,
    convert_devanagari,
    supported_devanagari_fonts,
)
from .limbu import LimbuConversion, LimbuConverter, convert_limbu

__all__ = [
    "convert",
    "supported_fonts",
    "convert_devanagari",
    "convert_limbu",
    "DevanagariConversion",
    "LimbuConversion",
    "LimbuConverter",
    "supported_devanagari_fonts",
]

__version__ = "0.1.0"

# Limbu/Sirijonga legacy fonts that share the Namdhinggo SIL byte encoding.
_LIMBU_FONTS = {"namdhinggo", "namdhinggosill", "sirijonga", "limbu"}


def supported_fonts() -> dict[str, str]:
    """Map of supported font keys -> script."""
    fonts = {f: "Devanagari" for f in supported_devanagari_fonts()}
    fonts.update({f: "Limbu" for f in sorted(_LIMBU_FONTS)})
    return fonts


def convert(text: str, font: str, *, strict: bool = False) -> str:
    """Convert ``text`` rendered in a legacy ``font`` to proper Unicode (NFC).

    ``font`` is case-insensitive. Devanagari fonts: preeti, kantipur, sagarmatha,
    pcs-nepali, fontasy-himali, nayanepal, gorkhapatra. Limbu fonts: namdhinggo,
    sirijonga, limbu.
    """
    key = font.strip().lower()
    if key in _LIMBU_FONTS:
        return convert_limbu(text)
    return convert_devanagari(text, font=key, strict=strict).unicode_text
