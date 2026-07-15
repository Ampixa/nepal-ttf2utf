"""Legacy-font conversion and Unicode span validation for Nepal and Sikkim.

The package converts evidenced Devanagari, Limbu, Kirat Rai, Sunuwar, Lepcha,
Ol Chiki, Tirhuta, and Tibetan legacy layouts. It also provides NFC
normalization and version-stable assigned-repertoire validation for its Unicode
output scripts and Gurung Khema. Specialized APIs provide hash-pinned Janaki
PDF glyph-ID recovery and proposal-aligned Magar Akkha Devanagari/Brahmi
transliteration. Unresolved input is surfaced instead of guessed.

    from nepal_ttf2utf import convert
    convert("g]kfn", font="preeti")       # -> 'नेपाल'   (Devanagari)
    convert("...", font="nayanepal")       # -> Gorkhapatra Devanagari, Unicode
    convert("<namdhinggo bytes>", font="namdhinggo")  # -> Unicode Limbu (Sirijonga)
    convert("<kiratraifont bytes>", font="kiratrai")  # -> Unicode Kirat Rai
    convert("<koits/kirat1 bytes>", font="sunuwar")   # -> Unicode Sunuwar
    convert("<herald bytes>", font="lepcha-sikkimherald")  # -> Unicode Lepcha
    convert("<JG Lepcha bytes>", font="jg-lepcha")  # -> Unicode Lepcha
    convert("<olck optimum bytes>", font="olck-optimum")  # -> Unicode Ol Chiki
    convert("<olck latic bytes>", font="olcklatic-normal")  # -> Unicode Ol Chiki
    convert("<Janaki text>", font="janaki")  # -> Unicode Tirhuta
    convert("<TibetanMachine text>", font="tibetanmachine")  # -> Unicode Tibetan
    convert("<Unicode Newa>", font="noto-sans-newa")  # -> validated Unicode Newa
"""

from __future__ import annotations

import re

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
from .magar_akkha import MagarAkkhaTransliteration, transliterate_magar_akkha
from .olchiki import (
    OLChikiConversion,
    OLChikiConverter,
    OLChikiLaticConverter,
    convert_olchiki,
    convert_olchiki_latic,
)
from .sunuwar import SunuwarConversion, SunuwarConverter, convert_sunuwar
from .tibetan import TibetanMachineConversion, TibetanMachineConverter, convert_tibetanmachine
from .tirhuta import TirhutaConversion, TirhutaConverter, convert_tirhuta
from .unicode_span import (
    UNICODE_REPERTOIRE_VERSION,
    UnicodeSpanConversion,
    supported_unicode_scripts,
    validate_unicode_span,
)
from .videha import (
    VIDEHA_2008_04_15,
    VIDEHA_ISSUE_001,
    UnknownJanakiGlyphError,
    VidehaJanakiRecovery,
    VidehaProfileError,
    janaki_gid_map_sha256,
    recover_videha_janaki_trace,
)

__all__ = [
    "convert",
    "supported_fonts",
    "convert_devanagari",
    "convert_limbu",
    "convert_kiratrai",
    "convert_kiratrai_herald",
    "transliterate_magar_akkha",
    "convert_jg_lepcha",
    "convert_sunuwar",
    "convert_tibetanmachine",
    "convert_lepcha",
    "convert_olchiki",
    "convert_olchiki_latic",
    "convert_tirhuta",
    "validate_unicode_span",
    "supported_unicode_scripts",
    "UNICODE_REPERTOIRE_VERSION",
    "recover_videha_janaki_trace",
    "janaki_gid_map_sha256",
    "DevanagariConversion",
    "LimbuConversion",
    "LimbuConverter",
    "MagarAkkhaTransliteration",
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
    "OLChikiLaticConverter",
    "TirhutaConversion",
    "TirhutaConverter",
    "UnicodeSpanConversion",
    "VidehaJanakiRecovery",
    "VidehaProfileError",
    "UnknownJanakiGlyphError",
    "VIDEHA_ISSUE_001",
    "VIDEHA_2008_04_15",
    "supported_devanagari_fonts",
]

__version__ = "0.3.0"

# Limbu/Sirijonga legacy fonts that share the Namdhinggo SIL byte encoding.
_LIMBU_FONTS = {"namdhinggo", "namdhinggosill", "sirijonga", "limbu"}
# Modern Unicode Limbu fonts. Bare ``namdhinggo`` remains the legacy route for
# compatibility; use an explicit Regular/PostScript or Unicode key for v3.100.
_LIMBU_UNICODE_FONTS = {
    "limbu-unicode",
    "namdhinggo-bold",
    "namdhinggo-extrabold",
    "namdhinggo-medium",
    "namdhinggo regular",
    "namdhinggo-regular",
    "namdhinggo-semibold",
    "namdhinggo-unicode",
    "noto sans limbu",
    "noto-sans-limbu",
    "notosanslimbu",
    "notosanslimbu-regular",
    "unicode-limbu",
}
# Canonical 2021 ``kirat rai font new`` encoding published with SIL's map.
_KIRATRAI_FONTS = {"kiratrai", "kiratrai-new", "kiratraifontnew", "akrs", "akrs-new"}
# Older, globally permuted layout extracted from Sikkim Herald PDF subsets.
_KIRATRAI_HERALD_FONTS = {"kiratrai-herald", "kiratraifont", "sikkimherald-kiratrai"}
_KIRATRAI_UNICODE_FONTS = {
    "kanchenjunga",
    "kanchenjunga-bold",
    "kanchenjunga-regular",
    "kirat-rai-unicode",
    "unicode-kirat-rai",
}
# Sunuwar / Jenticha (Koĩts) legacy display font (koits / kirat1).
_SUNUWAR_FONTS = {"sunuwar", "jenticha", "koits", "kirat1"}
_SUNUWAR_UNICODE_FONTS = {
    "noto sans sunuwar",
    "noto-sans-sunuwar",
    "notosanssunuwar",
    "notosanssunuwar-regular",
    "sunuwar-unicode",
    "unicode-sunuwar",
}
# BDRC/UTFC legacy TibetanMachine encoding (not Unicode Tibetan fonts).
_TIBETAN_MACHINE_FONTS = {"tibetanmachine", "tibetan-machine"}
# Tibetan font families observed with real Unicode text layers.
_TIBETAN_UNICODE_FONTS = {
    "ctrc-ht",
    "jomolhari",
    "jomolhari-id",
    "microsoft himalaya",
    "microsoft-himalaya",
    "monlam unicode",
    "monlam-unicode",
    "monlamuniouchan5",
    "qomolangma",
    "qomolangma-subtitle",
    "qomolangma-title",
    "qomolangma-uchen-suring",
    "tibetan-unicode",
    "unicode-tibetan",
}
# Unicode Devanagari font spans that need identity routing, including the DU
# encoding of Nithya Ranjana (Ranjana glyphs over Devanagari characters) and
# LTK's exact Madan2 family/full/PostScript name.
_DEVANAGARI_UNICODE_FONTS = {
    "annapurna sil nepal",
    "annapurna-sil-nepal",
    "annapurnasilnepal",
    "devanagari-unicode",
    "madan2",
    "nithya ranjana du",
    "nithya-ranjana-du",
    "nithyaranjanadu",
    "nithyaranjanadu-regular",
    "noto sans devanagari",
    "noto serif devanagari",
    "noto-sans-devanagari",
    "noto-serif-devanagari",
    "notosansdevanagari",
    "notosansdevanagari-regular",
    "notoserifdevanagari",
    "notoserifdevanagari-regular",
    "notoserifdevanagari-variablefont-wdth,wght",
    "unicode-devanagari",
}
# Unicode Newa/Prachalit font keys. These normalize and validate; they do not
# apply a legacy-byte mapping.
_NEWA_UNICODE_FONTS = {
    "newa",
    "newa-unicode",
    "noto sans newa",
    "noto-sans-newa",
    "notosansnewa",
    "notosansnewa-regular",
    "nithya ranjana nu",
    "nithya-ranjana-nu",
    "nithyaranjananu",
    "nithyaranjananu-regular",
    "prachalit-unicode",
    "unicode-newa",
}
_BRAHMI_UNICODE_FONTS = {
    "akkha-brahmi",
    "brahmi-unicode",
    "magar-akkha-brahmi",
    "unicode-brahmi",
}
# Sikkim Herald live-text Lepcha body font (TT*O00 named layout).
_LEPCHA_FONTS = {"lepcha-sikkimherald", "lepcha", "sikkimherald-lepcha"}
# Jason Glavy's public legacy Lepcha encoding (different from the Herald layout).
_JG_LEPCHA_FONTS = {"jg-lepcha", "jglepcha", "lepcha-jg"}
_LEPCHA_UNICODE_FONTS = {
    "lepcha-unicode",
    "mingzat",
    "mingzat-regular",
    "noto sans lepcha",
    "noto-sans-lepcha",
    "notosanslepcha",
    "notosanslepcha-regular",
    "unicode-lepcha",
}
# Santali Ol Chiki 'Optimum' legacy display font (OLCKOptimum-Medium/-ExtraBlack).
_OLCHIKI_FONTS = {"olck-optimum", "olchiki-optimum", "olchiki", "aale-chhatka"}
# OLCKLatic shares the semantic letters/digits but has different punctuation.
_OLCHIKI_LATIC_FONTS = {
    "olck-latic",
    "olcklatic",
    "olcklatic-black",
    "olcklatic-bold",
    "olcklatic-extrablack",
    "olcklatic-medium",
    "olcklatic-normal",
    "olcklatic-ultrablack",
    "olchiki-latic",
}
_OLCHIKI_UNICODE_FONTS = {
    "noto sans ol chiki",
    "noto-sans-ol-chiki",
    "notosansolchiki",
    "notosansolchiki-regular",
    "notosansolchiki-variablefont-wght",
    "ol-chiki-unicode",
    "unicode-ol-chiki",
}
# Janaki stores Tirhuta glyphs under semantically corresponding Devanagari codepoints.
_TIRHUTA_FONTS = {"janaki", "tirhuta", "mithilakshar"}
_TIRHUTA_UNICODE_FONTS = {
    "noto sans tirhuta",
    "noto-sans-tirhuta",
    "notosanstirhuta",
    "notosanstirhuta-regular",
    "tirhuta-unicode",
    "unicode-tirhuta",
}
_GURUNG_KHEMA_UNICODE_FONTS = {
    "gurung-khema-unicode",
    "noto sans gurung khema",
    "noto-sans-gurung-khema",
    "notosansgurungkhema",
    "notosansgurungkhema-regular",
    "unicode-gurung-khema",
}


def supported_fonts() -> dict[str, str]:
    """Map of supported font keys -> script."""
    fonts = {f: "Devanagari" for f in supported_devanagari_fonts()}
    fonts.update({f: "Devanagari" for f in sorted(_DEVANAGARI_UNICODE_FONTS)})
    fonts.update({f: "Limbu" for f in sorted(_LIMBU_FONTS)})
    fonts.update({f: "Limbu" for f in sorted(_LIMBU_UNICODE_FONTS)})
    fonts.update({f: "Kirat Rai" for f in sorted(_KIRATRAI_FONTS)})
    fonts.update({f: "Kirat Rai" for f in sorted(_KIRATRAI_HERALD_FONTS)})
    fonts.update({f: "Kirat Rai" for f in sorted(_KIRATRAI_UNICODE_FONTS)})
    fonts.update({f: "Sunuwar" for f in sorted(_SUNUWAR_FONTS)})
    fonts.update({f: "Sunuwar" for f in sorted(_SUNUWAR_UNICODE_FONTS)})
    fonts.update({f: "Tibetan" for f in sorted(_TIBETAN_MACHINE_FONTS)})
    fonts.update({f: "Tibetan" for f in sorted(_TIBETAN_UNICODE_FONTS)})
    fonts.update({f: "Newa" for f in sorted(_NEWA_UNICODE_FONTS)})
    fonts.update({f: "Brahmi" for f in sorted(_BRAHMI_UNICODE_FONTS)})
    fonts.update({f: "Lepcha" for f in sorted(_LEPCHA_FONTS)})
    fonts.update({f: "Lepcha" for f in sorted(_JG_LEPCHA_FONTS)})
    fonts.update({f: "Lepcha" for f in sorted(_LEPCHA_UNICODE_FONTS)})
    fonts.update({f: "Ol Chiki" for f in sorted(_OLCHIKI_FONTS)})
    fonts.update({f: "Ol Chiki" for f in sorted(_OLCHIKI_LATIC_FONTS)})
    fonts.update({f: "Ol Chiki" for f in sorted(_OLCHIKI_UNICODE_FONTS)})
    fonts.update({f: "Tirhuta" for f in sorted(_TIRHUTA_FONTS)})
    fonts.update({f: "Tirhuta" for f in sorted(_TIRHUTA_UNICODE_FONTS)})
    fonts.update({f: "Gurung Khema" for f in sorted(_GURUNG_KHEMA_UNICODE_FONTS)})
    return fonts


def _normalize_font_key(font: str) -> str:
    """Normalize a user/PDF font name while preserving meaningful family text."""
    key = font.strip().lower().replace("_", "-")
    return re.sub(r"^[a-z]{6}\+", "", key)


def convert(text: str, font: str, *, strict: bool = False) -> str:
    """Convert a legacy span or validate an already-Unicode span as NFC.

    ``font`` is case-insensitive. Supported legacy families cover Devanagari,
    Limbu, Kirat Rai, Sunuwar, Lepcha, Ol Chiki Optimum and Latic, Janaki
    Tirhuta, and TibetanMachine. Explicit modern Unicode families for those
    scripts, Newa, Brahmi, and Gurung Khema use assigned-repertoire validation
    without a legacy byte mapping. See :func:`supported_fonts` for exact keys.

    ``strict=True`` raises if any converter leaves an unmapped or uncertain
    character. Lenient mode preserves that input. Use a format-specific
    ``convert_*`` function to inspect its detailed conversion result. Videha
    glyph-ID recovery and Magar Akkha transliteration use their specialized
    APIs rather than this dispatcher.
    """
    key = _normalize_font_key(font)
    if key in _DEVANAGARI_UNICODE_FONTS:
        return validate_unicode_span(text, script="Devanagari", strict=strict).unicode_text
    if key in _LIMBU_UNICODE_FONTS:
        return validate_unicode_span(text, script="Limbu", strict=strict).unicode_text
    if key in _LIMBU_FONTS:
        return convert_limbu(text, strict=strict)
    if key in _KIRATRAI_UNICODE_FONTS:
        return validate_unicode_span(text, script="Kirat Rai", strict=strict).unicode_text
    if key in _KIRATRAI_FONTS:
        return convert_kiratrai(text, strict=strict).unicode_text
    if key in _KIRATRAI_HERALD_FONTS:
        return convert_kiratrai_herald(text, strict=strict).unicode_text
    if key in _SUNUWAR_FONTS:
        return convert_sunuwar(text, strict=strict).unicode_text
    if key in _SUNUWAR_UNICODE_FONTS:
        return validate_unicode_span(text, script="Sunuwar", strict=strict).unicode_text
    if key in _TIBETAN_MACHINE_FONTS:
        return convert_tibetanmachine(text, strict=strict).unicode_text
    if key in _TIBETAN_UNICODE_FONTS:
        return validate_unicode_span(text, script="Tibetan", strict=strict).unicode_text
    if key in _NEWA_UNICODE_FONTS:
        return validate_unicode_span(text, script="Newa", strict=strict).unicode_text
    if key in _BRAHMI_UNICODE_FONTS:
        return validate_unicode_span(text, script="Brahmi", strict=strict).unicode_text
    if key in _LEPCHA_UNICODE_FONTS:
        return validate_unicode_span(text, script="Lepcha", strict=strict).unicode_text
    if key in _LEPCHA_FONTS:
        return convert_lepcha(text, strict=strict).unicode_text
    if key in _JG_LEPCHA_FONTS:
        return convert_jg_lepcha(text, strict=strict).unicode_text
    if key in _OLCHIKI_FONTS:
        return convert_olchiki(text, strict=strict).unicode_text
    if key in _OLCHIKI_LATIC_FONTS:
        return convert_olchiki_latic(text, strict=strict).unicode_text
    if key in _OLCHIKI_UNICODE_FONTS:
        return validate_unicode_span(text, script="Ol Chiki", strict=strict).unicode_text
    if key in _TIRHUTA_UNICODE_FONTS:
        return validate_unicode_span(text, script="Tirhuta", strict=strict).unicode_text
    if key in _TIRHUTA_FONTS:
        return convert_tirhuta(text, strict=strict).unicode_text
    if key in _GURUNG_KHEMA_UNICODE_FONTS:
        return validate_unicode_span(text, script="Gurung Khema", strict=strict).unicode_text
    return convert_devanagari(text, font=key, strict=strict).unicode_text
