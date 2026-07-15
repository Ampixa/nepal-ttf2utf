"""BDRC TibetanMachine legacy-table conversion tests."""

import unicodedata

import pytest

from nepal_ttf2utf import convert, convert_tibetanmachine
from nepal_ttf2utf.tibetan import TibetanMachineConverter


def test_tibetanmachine_basic_consonants_follow_bdrc_table():
    result = convert_tibetanmachine('!"#$')
    assert result.unicode_text == "ཀཁགང"
    assert result.tibetan_char_count == 4
    assert result.replacement_count == 4


def test_tibetanmachine_clusters_and_punctuation():
    assert convert_tibetanmachine("?@A", strict=True).unicode_text == "རྐརྒརྔ"
    assert convert_tibetanmachine(chr(201), strict=True).unicode_text == "༆༅"


def test_tibetanmachine_digits_map_in_order():
    assert convert_tibetanmachine("".join(chr(cp) for cp in range(190, 200))).unicode_text == (
        "༠༡༢༣༤༥༦༧༨༩"
    )


def test_tibetanmachine_cp1252_and_raw_byte_aliases_match():
    converter = TibetanMachineConverter.default()
    assert converter.convert("€").unicode_text == "སྒྱ"
    assert converter.convert(chr(0x80)).unicode_text == "སྒྱ"


def test_tibetanmachine_defined_empty_entry_is_reported():
    result = convert_tibetanmachine("-")
    assert result.unicode_text == ""
    assert result.empty_codepoints == ["U+002D"]
    with pytest.raises(ValueError):
        convert_tibetanmachine("-", strict=True)


def test_tibetanmachine_nbsp_matches_upstream_space_normalization():
    result = convert_tibetanmachine("\u00a0", strict=True)
    assert result.unicode_text == " "
    assert result.empty_codepoints == []


def test_tibetanmachine_unknown_and_unicode_passthrough():
    result = convert_tibetanmachine("☃")
    assert result.unicode_text == "☃"
    assert result.unmapped_codepoints == ["U+2603"]
    with pytest.raises(ValueError):
        convert_tibetanmachine("☃", strict=True)

    unicode_text = "བོད"
    result = convert_tibetanmachine(unicode_text, strict=True)
    assert result.unicode_text == unicode_text
    assert not result.unmapped_codepoints


@pytest.mark.parametrize("codepoint", [0xE010, 0xE013])
def test_tibetanmachine_notdef_pua_is_reported_as_missing_glyph(codepoint):
    source = chr(codepoint)
    result = convert_tibetanmachine(source)
    assert result.unicode_text == source
    assert result.missing_glyph_codepoints == [f"U+{codepoint:04X}"]
    assert result.unmapped_codepoints == []
    with pytest.raises(ValueError, match="missing"):
        convert_tibetanmachine(source, strict=True)


def test_tibetanmachine_map_targets_are_tibetan_and_output_is_nfc():
    converter = TibetanMachineConverter.default()
    result = converter.convert("!@A€¾")
    assert all(0x0F00 <= ord(char) <= 0x0FFF for char in result.unicode_text)
    assert result.unicode_text == unicodedata.normalize("NFC", result.unicode_text)


def test_convert_dispatches_to_tibetanmachine():
    assert convert("!", font="tibetanmachine", strict=True) == "ཀ"
