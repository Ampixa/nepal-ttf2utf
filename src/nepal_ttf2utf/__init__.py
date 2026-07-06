"""nepal_ttf2utf — legacy ASCII-font -> Unicode for the scripts of Nepal and its diaspora.

Fills the gap left by Nepali-only converters (e.g. npttf2utf, which covers a few
Devanagari ASCII fonts): one library covering Devanagari legacy fonts *including
newspaper fonts like nayanepal/Gorkhapatra*, the Limbu/Sirijonga script, and the
minority-language fonts of the Sikkim Herald (Kirat Rai, Sunuwar, Lepcha) and the
Santali Ol Chiki 'Optimum' legacy font, with correct handling of the special
characters most converters silently drop.

    from nepal_ttf2utf import convert
    convert("g]kfn", font="preeti")       # -> 'नेपाल'   (Devanagari)
    convert("...", font="nayanepal")       # -> Gorkhapatra Devanagari, Unicode
    convert("<namdhinggo bytes>", font="namdhinggo")  # -> Unicode Limbu (Sirijonga)
    convert("<kiratraifont bytes>", font="kiratrai")  # -> Unicode Kirat Rai
    convert("<koits/kirat1 bytes>", font="sunuwar")   # -> Unicode Sunuwar
    convert("<herald bytes>", font="lepcha-sikkimherald")  # -> Unicode Lepcha
    convert("<olck optimum bytes>", font="olck-optimum")  # -> Unicode Ol Chiki
"""

from __future__ import annotations

from .devanagari import (
    DevanagariConversion,
    convert_devanagari,
    supported_devanagari_fonts,
)
from .kiratrai import KiratRaiConversion, KiratRaiConverter, convert_kiratrai
from .lepcha import LepchaConversion, LepchaConverter, convert_lepcha
from .limbu import LimbuConversion, LimbuConverter, convert_limbu
from .olchiki import OLChikiConversion, OLChikiConverter, convert_olchiki
from .sunuwar import SunuwarConversion, SunuwarConverter, convert_sunuwar

__all__ = [
    "convert",
    "supported_fonts",
    "convert_devanagari",
    "convert_limbu",
    "convert_kiratrai",
    "convert_sunuwar",
    "convert_lepcha",
    "convert_olchiki",
    "DevanagariConversion",
    "LimbuConversion",
    "LimbuConverter",
    "KiratRaiConversion",
    "KiratRaiConverter",
    "SunuwarConversion",
    "SunuwarConverter",
    "LepchaConversion",
    "LepchaConverter",
    "OLChikiConversion",
    "OLChikiConverter",
    "supported_devanagari_fonts",
]

__version__ = "0.1.0"

# Limbu/Sirijonga legacy fonts that share the Namdhinggo SIL byte encoding.
_LIMBU_FONTS = {"namdhinggo", "namdhinggosill", "sirijonga", "limbu"}
# Kirat Rai legacy ``kiratraifont`` (AKRS) byte encoding.
_KIRATRAI_FONTS = {"kiratrai", "kiratraifont", "akrs"}
# Sunuwar / Jenticha (Koĩts) legacy display font (koits / kirat1).
_SUNUWAR_FONTS = {"sunuwar", "jenticha", "koits", "kirat1"}
# Sikkim Herald live-text Lepcha body font (TT*O00 named layout).
_LEPCHA_FONTS = {"lepcha-sikkimherald", "lepcha", "sikkimherald-lepcha"}
# Santali Ol Chiki 'Optimum' legacy display font (OLCKOptimum-Medium/-ExtraBlack).
_OLCHIKI_FONTS = {"olck-optimum", "olchiki-optimum", "olchiki", "aale-chhatka"}


def supported_fonts() -> dict[str, str]:
    """Map of supported font keys -> script."""
    fonts = {f: "Devanagari" for f in supported_devanagari_fonts()}
    fonts.update({f: "Limbu" for f in sorted(_LIMBU_FONTS)})
    fonts.update({f: "Kirat Rai" for f in sorted(_KIRATRAI_FONTS)})
    fonts.update({f: "Sunuwar" for f in sorted(_SUNUWAR_FONTS)})
    fonts.update({f: "Lepcha" for f in sorted(_LEPCHA_FONTS)})
    fonts.update({f: "Ol Chiki" for f in sorted(_OLCHIKI_FONTS)})
    return fonts


def convert(text: str, font: str, *, strict: bool = False) -> str:
    """Convert ``text`` rendered in a legacy ``font`` to proper Unicode (NFC).

    ``font`` is case-insensitive. Devanagari fonts: preeti, kantipur, sagarmatha,
    pcs-nepali, fontasy-himali, nayanepal, gorkhapatra. Limbu fonts: namdhinggo,
    sirijonga, limbu. Kirat Rai: kiratrai. Sunuwar: sunuwar.
    Lepcha (Sikkim Herald live-text font): lepcha-sikkimherald.
    Ol Chiki (Santali 'Optimum' legacy font): olck-optimum.

    For the Kirat Rai / Sunuwar / Lepcha / Ol Chiki converters, ``strict=True``
    raises if any byte is unmapped or uncertain; in lenient mode such bytes are
    passed through unchanged. Use the ``convert_kiratrai`` / ``convert_sunuwar`` /
    ``convert_lepcha`` / ``convert_olchiki`` functions directly to inspect the
    flagged bytes.
    """
    key = font.strip().lower()
    if key in _LIMBU_FONTS:
        return convert_limbu(text)
    if key in _KIRATRAI_FONTS:
        return convert_kiratrai(text, strict=strict).unicode_text
    if key in _SUNUWAR_FONTS:
        return convert_sunuwar(text, strict=strict).unicode_text
    if key in _LEPCHA_FONTS:
        return convert_lepcha(text, strict=strict).unicode_text
    if key in _OLCHIKI_FONTS:
        return convert_olchiki(text, strict=strict).unicode_text
    return convert_devanagari(text, font=key, strict=strict).unicode_text
