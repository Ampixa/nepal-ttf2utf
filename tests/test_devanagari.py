"""Devanagari conversion tests, anchored on real Gorkhapatra / known words."""

import itertools
import re
import unicodedata

import pytest

from nepal_ttf2utf import convert, devanagari
from nepal_ttf2utf.devanagari import convert_devanagari, supported_devanagari_fonts


def test_preeti_known_words():
    assert convert("g]kfn", font="preeti") == "नेपाल"
    assert convert("du/", font="preeti") == "मगर"


def test_nayanepal_gorkhapatra_anchors():
    # Real Gorkhapatra masthead spans (legacy bytes incl. control chars + ƒ extension).
    assert "गोरखापत्र" in convert("uf]\x03ƒvfkqåfƒf", font="nayanepal")
    assert convert("k|sflzt", font="nayanepal") == "प्रकाशित"
    # ƒ -> र extension specifically (would be गोƒखापत्र without it).
    assert "ƒ" not in convert("uf]\x03ƒvfkqåfƒf", font="nayanepal")


def test_nayanepal_output_is_clean_devanagari():
    res = convert_devanagari("clgn a'9fduƒ,", font="nayanepal")
    assert res.clean
    assert res.unicode_text.startswith("अनिल")


def test_devanagari_preserves_structural_whitespace_but_cleans_other_c0_controls():
    res = convert_devanagari("g]kfn\t\r\n\x03du/", font="preeti")
    assert res.unicode_text == "नेपाल\t\r\nमगर"
    assert not res.clean
    assert res.leftover == ["\x03"]
    with pytest.raises(ValueError, match=r"U\+0003"):
        convert_devanagari("g]kfn\t\r\n\x03du/", font="preeti", strict=True)


def test_strict_mode_surfaces_leftovers():
    # An unmapped byte (á / U+00E1) should raise in strict mode rather than pass silently.
    with pytest.raises(ValueError):
        convert_devanagari("áá", font="preeti", strict=True)
    # ... and be reported (not dropped) in lenient mode.
    res = convert_devanagari("áá", font="preeti")
    assert not res.clean and "á" in res.leftover


@pytest.mark.parametrize("font", supported_devanagari_fonts())
def test_strict_mode_reports_dependency_deleting_post_rule(font):
    source = r"\f"
    result = convert_devanagari(source, font=font)
    assert result.unicode_text == ""
    assert result.leftover == ["\\", "f"]
    assert not result.clean

    with pytest.raises(ValueError, match=r"U\+005C.*U\+0066"):
        convert_devanagari(source, font=font, strict=True)
    with pytest.raises(ValueError, match=r"U\+005C.*U\+0066"):
        convert(source, font=font, strict=True)


def test_fontasy_empty_character_map_entry_is_reported():
    result = convert_devanagari("»", font="fontasy-himali")
    assert result.unicode_text == ""
    assert result.leftover == ["»"]
    assert not result.clean
    with pytest.raises(ValueError, match=r"U\+00BB"):
        convert("»", font="fontasy-himali", strict=True)


def test_dependency_empty_mappings_and_fully_consumed_deletions_are_diagnostic():
    mapper = devanagari._font_mapper()
    base_fonts = {
        **devanagari._NPTTF2UTF_FONTS,
        **{font: "Preeti" for font in devanagari._PREETI_FAMILY_EXT},
    }
    for font, base_font in base_fonts.items():
        rules = mapper.all_rules[base_font]["rules"]
        assert rules["pre-rules"] == []
        deleting_patterns = [
            re.compile(pattern) for pattern, replacement in rules["post-rules"] if not replacement
        ]
        assert deleting_patterns

        character_map = rules["character-map"]
        for source, target in character_map.items():
            if target:
                continue
            result = convert_devanagari(source, font=font)
            assert source in result.leftover

        keys = tuple(character_map)
        for length in (1, 2):
            for source_values in itertools.product(keys, repeat=length):
                mapped = "".join(character_map[value] for value in source_values)
                if not any(pattern.search(mapped) for pattern in deleting_patterns):
                    continue
                source = "".join(source_values)
                result = convert_devanagari(source, font=font)
                dependency_output = mapper.map_to_unicode(source, from_font=base_font)
                if dependency_output:
                    assert not set(source) & set(result.leftover)
                else:
                    assert set(source) <= set(result.leftover)


@pytest.mark.parametrize("font", supported_devanagari_fonts())
@pytest.mark.parametrize("source", [r"s\f", r"\fs", r"s\fs"])
def test_fully_consumed_deletion_is_reported_inside_nonempty_word(font, source):
    result = convert_devanagari(source, font=font)
    assert result.unicode_text
    assert result.leftover == ["\\", "f"]
    assert not result.clean

    with pytest.raises(ValueError, match=r"U\+005C.*U\+0066"):
        convert_devanagari(source, font=font, strict=True)
    with pytest.raises(ValueError, match=r"U\+005C.*U\+0066"):
        convert(source, font=font, strict=True)


@pytest.mark.parametrize("font", supported_devanagari_fonts())
@pytest.mark.parametrize("source", ["Sf", "0f"])
def test_deleting_post_rule_remains_clean_when_it_produces_valid_output(font, source):
    result = convert_devanagari(source, font=font, strict=True)
    assert result.unicode_text
    assert result.leftover == []
    assert result.clean
    assert convert(source, font=font, strict=True) == result.unicode_text


@pytest.mark.parametrize("font", supported_devanagari_fonts())
@pytest.mark.parametrize(("source", "expected"), [("lक", "कि"), ("कM", "कः")])
def test_mixed_unicode_devanagari_keeps_dependency_word_context(font, source, expected):
    result = convert_devanagari(source, font=font, strict=True)
    assert result.unicode_text == expected
    assert result.leftover == []
    assert result.clean
    assert convert(source, font=font, strict=True) == expected


def test_legacy_byte_lenient_output_remains_dependency_compatible():
    mapper = devanagari._font_mapper()
    source = "".join(chr(codepoint) for codepoint in range(0x100))
    cleaned = devanagari._CTRL.sub("", source)
    base_fonts = {
        **devanagari._NPTTF2UTF_FONTS,
        **{font: "Preeti" for font in devanagari._PREETI_FAMILY_EXT},
    }
    for font, base_font in base_fonts.items():
        expected = mapper.map_to_unicode(cleaned, from_font=base_font)
        for old, new in devanagari._PREETI_FAMILY_EXT.get(font, {}).items():
            expected = expected.replace(old, new)
        for old, new in devanagari._PUNCT_NORMALIZE.items():
            expected = expected.replace(old, new)
        expected = unicodedata.normalize("NFC", expected)
        assert convert_devanagari(source, font=font).unicode_text == expected


def test_mixed_unicode_devanagari_is_preserved_before_legacy_mapping():
    source = "g]kfn\u0903\u1cd0\ua8e0\U00011b00"
    expected = "नेपाल\u0903\u1cd0\ua8e0\U00011b00"
    result = convert_devanagari(source, font="preeti", strict=True)
    assert result.unicode_text == expected
    assert result.leftover == []
    assert result.clean


def test_unknown_font_raises():
    with pytest.raises(ValueError):
        convert("abc", font="not-a-font")


def test_supported_fonts_listed():
    fonts = supported_devanagari_fonts()
    assert "nayanepal" in fonts and "preeti" in fonts
