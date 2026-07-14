"""Janaki / Devanagari-coded Tirhuta conversion tests."""

import unicodedata

import pytest

from nepal_ttf2utf import convert, convert_tirhuta


def test_tirhuta_logical_devanagari_remaps_by_script_semantics():
    result = convert_tirhuta("मैथिली")
    assert result.unicode_text == "𑒧𑒻𑒟𑒱𑒪𑒲"
    assert result.tirhuta_char_count == 6
    assert result.unicode_text == unicodedata.normalize("NFC", result.unicode_text)


def test_tirhuta_visual_prebase_i_is_repaired():
    result = convert_tirhuta("िवदेह")
    assert result.unicode_text == "𑒫𑒱𑒠𑒹𑒯"
    assert result.prebase_i_moves == 1


def test_tirhuta_visual_trailing_reph_is_repaired():
    result = convert_tirhuta("वषर्")
    assert result.unicode_text == "𑒫𑒩𑓂𑒭"
    assert result.reph_moves == 1


def test_tirhuta_logical_reph_order_is_not_changed():
    assert convert_tirhuta("वर्ष").unicode_text == "𑒫𑒩𑓂𑒭"
    assert convert_tirhuta("कर्म").unicode_text == "𑒏𑒩𑓂𑒧"


def test_tirhuta_digits_and_nukta_letters():
    assert convert_tirhuta("०१२३४५६७८९").unicode_text == "𑓐𑓑𑓒𑓓𑓔𑓕𑓖𑓗𑓘𑓙"
    assert convert_tirhuta("क़ ख़").unicode_text == "𑒏𑓃 𑒐𑓃"


def test_tirhuta_unrecoverable_pdf_characters_are_surfaced():
    result = convert_tirhuta("क�")
    assert result.unicode_text.endswith("�")
    assert result.unmapped_codepoints == ["U+FFFD"]
    with pytest.raises(ValueError):
        convert_tirhuta("क�", strict=True)


def test_tirhuta_genuine_unicode_and_punctuation_pass_through():
    result = convert_tirhuta("𑒏।", strict=True)
    assert result.unicode_text == "𑒏।"
    assert not result.unmapped_codepoints


def test_convert_dispatches_to_tirhuta():
    assert convert("मैथिली", font="janaki") == "𑒧𑒻𑒟𑒱𑒪𑒲"


def test_devanagari_lla_maps_to_la_plus_nukta():
    # Pandey L2/11-175R section 4.12: /l./ (Devanagari LLA) = TIRHUTA LA + NUKTA,
    # not NNA + NUKTA (regression for the 2026-07-14 audit finding).
    from nepal_ttf2utf.tirhuta import convert_tirhuta

    result = convert_tirhuta("ळ")
    assert "\U000114AA\U000114C3" in result.unicode_text
    assert "\U0001149D" not in result.unicode_text
