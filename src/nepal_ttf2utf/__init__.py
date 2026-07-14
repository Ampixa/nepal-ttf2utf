"""nepal_ttf2utf — legacy ASCII-font -> Unicode for the scripts of Nepal and its diaspora.

Fills the gap left by Nepali-only converters (e.g. npttf2utf, which covers a few
Devanagari ASCII fonts): one library covering Devanagari legacy fonts *including
newspaper fonts like nayanepal/Gorkhapatra*, the Limbu/Sirijonga script, and the
minority-language fonts of the Sikkim Herald (Kirat Rai, Sunuwar, Lepcha), Jason
Glavy's JG Lepcha font, the Santali Ol Chiki 'Optimum' font, and Janaki's
Devanagari-coded Tirhuta glyphs, plus TibetanMachine. Unresolved input is
surfaced instead of guessed.

    from nepal_ttf2utf import convert
    convert("g]kfn", font="preeti")       # -> 'नेपाल'   (Devanagari)
    convert("...", font="nayanepal")       # -> Gorkhapatra Devanagari, Unicode
    convert("<namdhinggo bytes>", font="namdhinggo")  # -> Unicode Limbu (Sirijonga)
    convert("<kiratraifont bytes>", font="kiratrai")  # -> Unicode Kirat Rai
    convert("<koits/kirat1 bytes>", font="sunuwar")   # -> Unicode Sunuwar
    convert("<herald bytes>", font="lepcha-sikkimherald")  # -> Unicode Lepcha
    convert("<JG Lepcha bytes>", font="jg-lepcha")  # -> Unicode Lepcha
    convert("<olck optimum bytes>", font="olck-optimum")  # -> Unicode Ol Chiki
    convert("<Janaki text>", font="janaki")  # -> Unicode Tirhuta
    convert("<TibetanMachine text>", font="tibetanmachine")  # -> Unicode Tibetan
"""

from __future__ import annotations

from .devanagari import (
    DevanagariConversion,
    convert_devanagari,
    supported_devanagari_fonts,
)
from .jg_lepcha import JGLepchaConversion, JGLepchaConverter, convert_jg_lepcha
from .kiratrai import (
    KiratRaiConversion,
    KiratRaiConverter,
    KiratRaiHeraldConverter,
    convert_kiratrai,
    convert_kiratrai_herald,
)
from .lepcha import LepchaConversion, LepchaConverter, convert_lepcha
from .limbu import LimbuConversion, LimbuConverter, convert_limbu
from .olchiki import OLChikiConversion, OLChikiConverter, convert_olchiki
from .sunuwar import SunuwarConversion, SunuwarConverter, convert_sunuwar
from .tibetan import TibetanMachineConversion, TibetanMachineConverter, convert_tibetanmachine
from .tirhuta import TirhutaConversion, TirhutaConverter, convert_tirhuta

__all__ = [
    "convert",
    "supported_fonts",
    "convert_devanagari",
    "convert_limbu",
    "convert_kiratrai",
    "convert_kiratrai_herald",
    "convert_jg_lepcha",
    "convert_sunuwar",
    "convert_tibetanmachine",
    "convert_lepcha",
    "convert_olchiki",
    "convert_tirhuta",
    "DevanagariConversion",
    "LimbuConversion",
    "LimbuConverter",
    "KiratRaiConversion",
    "KiratRaiConverter",
    "KiratRaiHeraldConverter",
    "JGLepchaConversion",
    "JGLepchaConverter",
    "SunuwarConversion",
    "SunuwarConverter",
    "TibetanMachineConversion",
    "TibetanMachineConverter",
    "LepchaConversion",
    "LepchaConverter",
    "OLChikiConversion",
    "OLChikiConverter",
    "TirhutaConversion",
    "TirhutaConverter",
    "supported_devanagari_fonts",
]

__version__ = "0.2.0"

# Limbu/Sirijonga legacy fonts that share the Namdhinggo SIL byte encoding.
_LIMBU_FONTS = {"namdhinggo", "namdhinggosill", "sirijonga", "limbu"}
# Canonical 2021 ``kirat rai font new`` encoding published with SIL's map.
_KIRATRAI_FONTS = {"kiratrai", "kiratrai-new", "kiratraifontnew", "akrs", "akrs-new"}
# Older, globally permuted layout extracted from Sikkim Herald PDF subsets.
_KIRATRAI_HERALD_FONTS = {"kiratrai-herald", "kiratraifont", "sikkimherald-kiratrai"}
# Sunuwar / Jenticha (Koĩts) legacy display font (koits / kirat1).
_SUNUWAR_FONTS = {"sunuwar", "jenticha", "koits", "kirat1"}
# BDRC/UTFC legacy TibetanMachine encoding (not Unicode Tibetan fonts).
_TIBETAN_MACHINE_FONTS = {"tibetanmachine", "tibetan-machine"}
# Sikkim Herald live-text Lepcha body font (TT*O00 named layout).
_LEPCHA_FONTS = {"lepcha-sikkimherald", "lepcha", "sikkimherald-lepcha"}
# Jason Glavy's public legacy Lepcha encoding (different from the Herald layout).
_JG_LEPCHA_FONTS = {"jg-lepcha", "jglepcha", "lepcha-jg"}
# Santali Ol Chiki 'Optimum' legacy display font (OLCKOptimum-Medium/-ExtraBlack).
_OLCHIKI_FONTS = {"olck-optimum", "olchiki-optimum", "olchiki", "aale-chhatka"}
# Janaki stores Tirhuta glyphs under semantically corresponding Devanagari codepoints.
_TIRHUTA_FONTS = {"janaki", "tirhuta", "mithilakshar"}


def supported_fonts() -> dict[str, str]:
    """Map of supported font keys -> script."""
    fonts = {f: "Devanagari" for f in supported_devanagari_fonts()}
    fonts.update({f: "Limbu" for f in sorted(_LIMBU_FONTS)})
    fonts.update({f: "Kirat Rai" for f in sorted(_KIRATRAI_FONTS)})
    fonts.update({f: "Kirat Rai" for f in sorted(_KIRATRAI_HERALD_FONTS)})
    fonts.update({f: "Sunuwar" for f in sorted(_SUNUWAR_FONTS)})
    fonts.update({f: "Tibetan" for f in sorted(_TIBETAN_MACHINE_FONTS)})
    fonts.update({f: "Lepcha" for f in sorted(_LEPCHA_FONTS)})
    fonts.update({f: "Lepcha" for f in sorted(_JG_LEPCHA_FONTS)})
    fonts.update({f: "Ol Chiki" for f in sorted(_OLCHIKI_FONTS)})
    fonts.update({f: "Tirhuta" for f in sorted(_TIRHUTA_FONTS)})
    return fonts


def convert(text: str, font: str, *, strict: bool = False) -> str:
    """Convert ``text`` rendered in a legacy ``font`` to proper Unicode (NFC).

    ``font`` is case-insensitive. Devanagari fonts: preeti, kantipur, sagarmatha,
    pcs-nepali, fontasy-himali, nayanepal, gorkhapatra. Limbu fonts: namdhinggo,
    sirijonga, limbu. Kirat Rai: kiratrai. Sunuwar: sunuwar.
    Lepcha: lepcha-sikkimherald or jg-lepcha. Ol Chiki (Santali 'Optimum'
    legacy font): olck-optimum. Tirhuta (Janaki): janaki. Tibetan:
    tibetanmachine.

    ``strict=True`` raises if any converter leaves an unmapped or uncertain
    character. Lenient mode preserves that input. Use a format-specific
    ``convert_*`` function to inspect its detailed conversion result.
    """
    key = font.strip().lower()
    if key in _LIMBU_FONTS:
        return convert_limbu(text, strict=strict)
    if key in _KIRATRAI_FONTS:
        return convert_kiratrai(text, strict=strict).unicode_text
    if key in _KIRATRAI_HERALD_FONTS:
        return convert_kiratrai_herald(text, strict=strict).unicode_text
    if key in _SUNUWAR_FONTS:
        return convert_sunuwar(text, strict=strict).unicode_text
    if key in _TIBETAN_MACHINE_FONTS:
        return convert_tibetanmachine(text, strict=strict).unicode_text
    if key in _LEPCHA_FONTS:
        return convert_lepcha(text, strict=strict).unicode_text
    if key in _JG_LEPCHA_FONTS:
        return convert_jg_lepcha(text, strict=strict).unicode_text
    if key in _OLCHIKI_FONTS:
        return convert_olchiki(text, strict=strict).unicode_text
    if key in _TIRHUTA_FONTS:
        return convert_tirhuta(text, strict=strict).unicode_text
    return convert_devanagari(text, font=key, strict=strict).unicode_text
