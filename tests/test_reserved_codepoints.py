"""Pinned Unicode-17 reserved-position tests for legacy converter output."""

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from nepal_ttf2utf import convert
from nepal_ttf2utf.jg_lepcha import convert_jg_lepcha
from nepal_ttf2utf.kiratrai import convert_kiratrai, convert_kiratrai_herald
from nepal_ttf2utf.lepcha import convert_lepcha
from nepal_ttf2utf.limbu import LimbuConverter, convert_limbu
from nepal_ttf2utf.sunuwar import convert_sunuwar
from nepal_ttf2utf.tibetan import convert_tibetanmachine
from nepal_ttf2utf.tirhuta import convert_tirhuta
from nepal_ttf2utf.unicode_span import (
    _ASSIGNED_BLOCK_RANGES,
    _SCRIPT_BLOCK_RANGES,
    _is_assigned_script_codepoint,
)


def _points(*parts):
    values = set()
    for part in parts:
        if isinstance(part, int):
            values.add(part)
        else:
            values.update(part)
    return frozenset(values)


RESERVED_BY_SCRIPT = {
    "Limbu": _points(0x191F, range(0x192C, 0x1930), range(0x193C, 0x1940), range(0x1941, 0x1944)),
    "Kirat Rai": _points(range(0x16D7A, 0x16D80)),
    "Sunuwar": _points(range(0x11BE2, 0x11BF0), range(0x11BFA, 0x11C00)),
    "Lepcha": _points(range(0x1C38, 0x1C3B), range(0x1C4A, 0x1C4D)),
    "Tirhuta": _points(range(0x114C8, 0x114D0), range(0x114DA, 0x114E0)),
    "Tibetan": _points(
        0x0F48,
        range(0x0F6D, 0x0F71),
        0x0F98,
        0x0FBD,
        0x0FCD,
        range(0x0FDB, 0x1000),
    ),
}


@dataclass(frozen=True)
class ReservedRoute:
    script: str
    font: str
    detailed_converter: Callable[[str], object]
    strict_converter: Callable[..., object]
    diagnostic_field: str
    count_field: str
    raw_diagnostics: bool = False


_LIMBU = LimbuConverter.default()

RESERVED_ROUTES = (
    ReservedRoute(
        "Limbu",
        "namdhinggo",
        _LIMBU.convert,
        convert_limbu,
        "unmapped_codepoints",
        "limbu_char_count",
    ),
    ReservedRoute(
        "Kirat Rai",
        "kiratraifontnew",
        convert_kiratrai,
        convert_kiratrai,
        "unmapped_codepoints",
        "kiratrai_char_count",
    ),
    ReservedRoute(
        "Kirat Rai",
        "kiratraifont",
        convert_kiratrai_herald,
        convert_kiratrai_herald,
        "unmapped_codepoints",
        "kiratrai_char_count",
    ),
    ReservedRoute(
        "Sunuwar",
        "sunuwar",
        convert_sunuwar,
        convert_sunuwar,
        "unmapped_bytes",
        "sunuwar_char_count",
        raw_diagnostics=True,
    ),
    ReservedRoute(
        "Lepcha",
        "lepcha-sikkimherald",
        convert_lepcha,
        convert_lepcha,
        "unmapped_bytes",
        "lepcha_char_count",
    ),
    ReservedRoute(
        "Lepcha",
        "jg-lepcha",
        convert_jg_lepcha,
        convert_jg_lepcha,
        "unmapped_codepoints",
        "lepcha_char_count",
    ),
    ReservedRoute(
        "Tirhuta",
        "janaki",
        convert_tirhuta,
        convert_tirhuta,
        "unmapped_codepoints",
        "tirhuta_char_count",
    ),
    ReservedRoute(
        "Tibetan",
        "tibetanmachine",
        convert_tibetanmachine,
        convert_tibetanmachine,
        "unmapped_codepoints",
        "tibetan_char_count",
    ),
)


def _expand(ranges):
    return {codepoint for start, end in ranges for codepoint in range(start, end + 1)}


def test_reserved_inventory_matches_the_pinned_unicode17_tables():
    assert len(set().union(*RESERVED_BY_SCRIPT.values())) == 103
    assert sum(len(RESERVED_BY_SCRIPT[route.script]) for route in RESERVED_ROUTES) == 115

    for script, expected in RESERVED_BY_SCRIPT.items():
        assigned = _expand(_ASSIGNED_BLOCK_RANGES[script])
        block = _expand(_SCRIPT_BLOCK_RANGES[script])
        assert block - assigned == expected
        assert all(_is_assigned_script_codepoint(codepoint, script) for codepoint in assigned)
        assert not any(_is_assigned_script_codepoint(codepoint, script) for codepoint in expected)


@pytest.mark.parametrize("route", RESERVED_ROUTES, ids=lambda route: route.font)
def test_every_reserved_position_is_preserved_diagnosed_and_strictly_rejected(route):
    for codepoint in sorted(RESERVED_BY_SCRIPT[route.script]):
        source = chr(codepoint)
        label = f"U+{codepoint:04X}"
        result = route.detailed_converter(source)

        assert result.unicode_text == source
        assert result.replacement_count == 0
        assert getattr(result, route.count_field) == 1
        expected_diagnostics = [source] if route.raw_diagnostics else [label]
        assert getattr(result, route.diagnostic_field) == expected_diagnostics

        with pytest.raises(ValueError, match=label.replace("+", r"\+")):
            route.strict_converter(source, strict=True)
        with pytest.raises(ValueError, match=label.replace("+", r"\+")):
            convert(source, font=route.font, strict=True)


@pytest.mark.parametrize("route", RESERVED_ROUTES, ids=lambda route: route.font)
def test_every_assigned_position_remains_accepted_by_strict_legacy_routes(route):
    for codepoint in sorted(_expand(_ASSIGNED_BLOCK_RANGES[route.script])):
        source = chr(codepoint)
        result = route.detailed_converter(source)
        assert result.unicode_text == unicodedata.normalize("NFC", source)
        assert getattr(result, route.diagnostic_field) == []
        route.strict_converter(source, strict=True)
        convert(source, font=route.font, strict=True)


def test_legacy_assignment_checks_do_not_depend_on_runtime_unicode_categories(monkeypatch):
    monkeypatch.setattr("nepal_ttf2utf.unicode_span.unicodedata.category", lambda _char: "Lo")
    with pytest.raises(ValueError, match=r"U\+16D7A"):
        convert("\U00016d7a", font="kiratraifontnew", strict=True)

    monkeypatch.setattr("nepal_ttf2utf.unicode_span.unicodedata.category", lambda _char: "Cn")
    assert convert("\U00016d40", font="kiratraifontnew", strict=True) == "\U00016d40"
