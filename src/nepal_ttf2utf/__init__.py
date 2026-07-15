"""Legacy-font conversion and Unicode span validation for Nepal and Sikkim.

The package converts evidenced Devanagari, Limbu, Kirat Rai, Sunuwar, Lepcha,
Ol Chiki, Tirhuta, and Tibetan legacy layouts. It also provides NFC
normalization and version-stable assigned-repertoire validation for its Unicode
output scripts and Gurung Khema. Specialized APIs provide hash-pinned Janaki
PDF glyph-ID recovery and an explicit project Magar Akkha Devanagari/Brahmi
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
from collections.abc import Mapping
from types import MappingProxyType

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
_LIMBU_FONTS = frozenset({"namdhinggo", "namdhinggosill", "sirijonga", "limbu"})
# Modern Unicode Limbu fonts. Bare ``namdhinggo`` remains the legacy route for
# compatibility; use an explicit Regular/PostScript or Unicode key for v3.100.
_LIMBU_UNICODE_FONTS = frozenset(
    {
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
)
if _LIMBU_FONTS & _LIMBU_UNICODE_FONTS:
    raise ValueError("Limbu legacy and Unicode font aliases overlap")
# Canonical 2021 ``kirat rai font new`` encoding published with SIL's map.
_KIRATRAI_FONTS = frozenset({"kiratrai", "kiratrai-new", "kiratraifontnew", "akrs", "akrs-new"})
# Older, globally permuted layout extracted from Sikkim Herald PDF subsets.
_KIRATRAI_HERALD_FONTS = frozenset({"kiratrai-herald", "kiratraifont", "sikkimherald-kiratrai"})
_KIRATRAI_UNICODE_FONTS = frozenset(
    {
        "kanchenjunga",
        "kanchenjunga-bold",
        "kanchenjunga-regular",
        "kirat-rai-unicode",
        "unicode-kirat-rai",
    }
)
if (
    _KIRATRAI_FONTS & _KIRATRAI_HERALD_FONTS
    or _KIRATRAI_FONTS & _KIRATRAI_UNICODE_FONTS
    or _KIRATRAI_HERALD_FONTS & _KIRATRAI_UNICODE_FONTS
):
    raise ValueError("Kirat Rai canonical, Herald, and Unicode font aliases overlap")
# Sunuwar / Jenticha (Koĩts) legacy display font (koits / kirat1).
_SUNUWAR_FONTS = frozenset({"sunuwar", "jenticha", "koits", "kirat1"})
_SUNUWAR_UNICODE_FONTS = frozenset(
    {
        "noto sans sunuwar",
        "noto-sans-sunuwar",
        "notosanssunuwar",
        "notosanssunuwar-regular",
        "sunuwar-unicode",
        "unicode-sunuwar",
    }
)
# BDRC/UTFC legacy TibetanMachine encoding (not Unicode Tibetan fonts).
_TIBETAN_MACHINE_FONTS = frozenset({"tibetanmachine", "tibetan-machine"})
# Tibetan font families observed with real Unicode text layers.
_TIBETAN_UNICODE_FONTS = frozenset(
    {
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
)
# Unicode Devanagari font spans that need identity routing, including the DU
# encoding of Nithya Ranjana (Ranjana glyphs over Devanagari characters) and
# LTK's exact Madan2 family/full/PostScript name.
_DEVANAGARI_UNICODE_FONTS = frozenset(
    {
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
)
# Unicode Newa/Prachalit font keys. These normalize and validate; they do not
# apply a legacy-byte mapping.
_NEWA_UNICODE_FONTS = frozenset(
    {
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
)
_BRAHMI_UNICODE_FONTS = frozenset(
    {
        "akkha-brahmi",
        "brahmi-unicode",
        "magar-akkha-brahmi",
        "unicode-brahmi",
    }
)
# Sikkim Herald live-text Lepcha body font (TT*O00 named layout).
_LEPCHA_FONTS = frozenset({"lepcha-sikkimherald", "lepcha", "sikkimherald-lepcha"})
# Jason Glavy's public legacy Lepcha encoding (different from the Herald layout).
_JG_LEPCHA_FONTS = frozenset({"jg-lepcha", "jglepcha", "lepcha-jg"})
_LEPCHA_UNICODE_FONTS = frozenset(
    {
        "lepcha-unicode",
        "mingzat",
        "mingzat-regular",
        "noto sans lepcha",
        "noto-sans-lepcha",
        "notosanslepcha",
        "notosanslepcha-regular",
        "unicode-lepcha",
    }
)
if (
    _LEPCHA_FONTS & _JG_LEPCHA_FONTS
    or _LEPCHA_FONTS & _LEPCHA_UNICODE_FONTS
    or _JG_LEPCHA_FONTS & _LEPCHA_UNICODE_FONTS
):
    raise ValueError("Lepcha legacy and Unicode font aliases overlap")
# Santali Ol Chiki Optimum legacy display fonts evidenced by embedded outlines.
_OLCHIKI_FONTS = frozenset(
    {
        "aale-chhatka",
        "olck-optimum",
        "olckoptimum-extrablack",
        "olckoptimum-medium",
        "olchiki",
        "olchiki-optimum",
    }
)
# OLCKLatic shares the semantic letters/digits but has different punctuation.
_OLCHIKI_LATIC_FONTS = frozenset(
    {
        "olck-latic",
        "olcklatic",
        "olcklatic-bold",
        "olcklatic-normal",
        "olcklatic-ultrablack",
        "olchiki-latic",
    }
)
_OLCHIKI_UNICODE_FONTS = frozenset(
    {
        "noto sans ol chiki",
        "noto-sans-ol-chiki",
        "notosansolchiki",
        "notosansolchiki-regular",
        "notosansolchiki-variablefont-wght",
        "ol-chiki-unicode",
        "unicode-ol-chiki",
    }
)
# The audited Videha Janaki spans use the project Devanagari-to-Tirhuta crosswalk.
# Generic Tirhuta/Mithilakshar keys are compatibility aliases for that legacy route.
_TIRHUTA_FONTS = frozenset({"janaki", "tirhuta", "mithilakshar"})
_TIRHUTA_UNICODE_FONTS = frozenset(
    {
        "noto sans tirhuta",
        "noto-sans-tirhuta",
        "notosanstirhuta",
        "notosanstirhuta-regular",
        "tirhuta-unicode",
        "unicode-tirhuta",
    }
)
if _TIRHUTA_FONTS & _TIRHUTA_UNICODE_FONTS:
    raise ValueError("Tirhuta legacy and Unicode font aliases overlap")
_GURUNG_KHEMA_UNICODE_FONTS = frozenset(
    {
        "gurung-khema-unicode",
        "noto sans gurung khema",
        "noto-sans-gurung-khema",
        "notosansgurungkhema",
        "notosansgurungkhema-regular",
        "unicode-gurung-khema",
    }
)


def _normalize_font_key(font: str) -> str:
    """Normalize a user/PDF font name while preserving meaningful family text."""
    if not isinstance(font, str):
        raise TypeError("font must be a string")
    key = font.strip().lower().replace("_", "-")
    return re.sub(r"^[a-z]{6}\+", "", key)


_DEVANAGARI_LEGACY_FONTS = frozenset(supported_devanagari_fonts())

# Route inventories are immutable and globally disjoint. The Boolean marks
# already-Unicode routes, which all share the generic span validator.
_FONT_ROUTE_GROUPS: Mapping[str, tuple[str, frozenset[str], bool]] = MappingProxyType(
    {
        "devanagari-legacy": ("Devanagari", _DEVANAGARI_LEGACY_FONTS, False),
        "devanagari-unicode": ("Devanagari", _DEVANAGARI_UNICODE_FONTS, True),
        "limbu-legacy": ("Limbu", _LIMBU_FONTS, False),
        "limbu-unicode": ("Limbu", _LIMBU_UNICODE_FONTS, True),
        "kirat-rai-canonical": ("Kirat Rai", _KIRATRAI_FONTS, False),
        "kirat-rai-herald": ("Kirat Rai", _KIRATRAI_HERALD_FONTS, False),
        "kirat-rai-unicode": ("Kirat Rai", _KIRATRAI_UNICODE_FONTS, True),
        "sunuwar-legacy": ("Sunuwar", _SUNUWAR_FONTS, False),
        "sunuwar-unicode": ("Sunuwar", _SUNUWAR_UNICODE_FONTS, True),
        "tibetan-machine": ("Tibetan", _TIBETAN_MACHINE_FONTS, False),
        "tibetan-unicode": ("Tibetan", _TIBETAN_UNICODE_FONTS, True),
        "newa-unicode": ("Newa", _NEWA_UNICODE_FONTS, True),
        "brahmi-unicode": ("Brahmi", _BRAHMI_UNICODE_FONTS, True),
        "lepcha-herald": ("Lepcha", _LEPCHA_FONTS, False),
        "jg-lepcha": ("Lepcha", _JG_LEPCHA_FONTS, False),
        "lepcha-unicode": ("Lepcha", _LEPCHA_UNICODE_FONTS, True),
        "ol-chiki-optimum": ("Ol Chiki", _OLCHIKI_FONTS, False),
        "ol-chiki-latic": ("Ol Chiki", _OLCHIKI_LATIC_FONTS, False),
        "ol-chiki-unicode": ("Ol Chiki", _OLCHIKI_UNICODE_FONTS, True),
        "tirhuta-legacy": ("Tirhuta", _TIRHUTA_FONTS, False),
        "tirhuta-unicode": ("Tirhuta", _TIRHUTA_UNICODE_FONTS, True),
        "gurung-khema-unicode": (
            "Gurung Khema",
            _GURUNG_KHEMA_UNICODE_FONTS,
            True,
        ),
    }
)


def _build_font_alias_contract(
    route_groups: Mapping[str, tuple[str, frozenset[str], bool]],
) -> tuple[Mapping[str, str], Mapping[str, str], Mapping[str, str]]:
    supported: dict[str, str] = {}
    unicode_routes: dict[str, str] = {}
    owners: dict[str, str] = {}
    supported_scripts = frozenset(supported_unicode_scripts())

    for route_name, (script, aliases, is_unicode) in route_groups.items():
        if not isinstance(aliases, frozenset):
            raise ValueError(f"font route {route_name!r} aliases must be a frozenset")
        if type(is_unicode) is not bool:
            raise ValueError(f"font route {route_name!r} Unicode marker must be Boolean")
        if script not in supported_scripts:
            raise ValueError(f"font route {route_name!r} has unsupported script {script!r}")
        if not aliases:
            raise ValueError(f"font route {route_name!r} has no aliases")
        for alias in sorted(aliases):
            if _normalize_font_key(alias) != alias:
                raise ValueError(f"font route {route_name!r} has unnormalized alias {alias!r}")
            previous_route = owners.get(alias)
            if previous_route is not None:
                raise ValueError(
                    f"font alias {alias!r} overlaps routes {previous_route!r} and {route_name!r}"
                )
            owners[alias] = route_name
            supported[alias] = script
            if is_unicode:
                unicode_routes[alias] = script

    return (
        MappingProxyType(supported),
        MappingProxyType(unicode_routes),
        MappingProxyType(owners),
    )


_SUPPORTED_FONT_SCRIPTS, _UNICODE_FONT_SCRIPTS, _FONT_ALIAS_ROUTES = _build_font_alias_contract(
    _FONT_ROUTE_GROUPS
)


def supported_fonts() -> dict[str, str]:
    """Return a mutable copy of the supported normalized font-key catalog."""
    return dict(_SUPPORTED_FONT_SCRIPTS)


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
    unicode_script = _UNICODE_FONT_SCRIPTS.get(key)
    if unicode_script is not None:
        return validate_unicode_span(text, script=unicode_script, strict=strict).unicode_text
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
    if key in _OLCHIKI_LATIC_FONTS:
        return convert_olchiki_latic(text, strict=strict).unicode_text
    if key in _TIRHUTA_FONTS:
        return convert_tirhuta(text, strict=strict).unicode_text
    if key in _DEVANAGARI_LEGACY_FONTS:
        return convert_devanagari(text, font=key, strict=strict).unicode_text
    raise ValueError(
        f"unsupported font key {key!r}; use supported_fonts() or --list-fonts to list accepted keys"
    )
