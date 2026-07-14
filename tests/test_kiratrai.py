"""Kirat Rai (legacy ``kiratraifont`` / AKRS) conversion tests.

Anchors are the round-trip-verified cases from the source derivation: SIL's TECkit
``kiratraifontnew.map`` byte-class table + its explicit multi-byte ligature rules.
"""

import unicodedata

import pytest

from nepal_ttf2utf import convert, convert_kiratrai
from nepal_ttf2utf.kiratrai import KiratRaiConverter


def _has_kiratrai(s: str) -> bool:
    return any(0x16D40 <= ord(c) <= 0x16D7F for c in s)


def test_kiratrai_byte_classes_map_positionally():
    conv = KiratRaiConverter.default()
    # cons1 byte class -> U+16D43..; 'a' (0x61) is position 0 -> U+16D43 LETTER A.
    assert conv.convert("a").unicode_text == "\U00016d43"
    # 'k' (0x6b) is position 1 in cons1 -> U+16D44 LETTER KA.
    assert conv.convert("k").unicode_text == "\U00016d44"
    # digits map 0x30..0x39 -> U+16D70..U+16D79.
    assert conv.convert("0").unicode_text == "\U00016d70"
    assert conv.convert("9").unicode_text == "\U00016d79"


def test_kiratrai_multibyte_ligature_rules_take_precedence():
    conv = KiratRaiConverter.default()
    # '//' (0x2f 0x2f) -> U+16D6F DOUBLE DANDA wins over single '/' -> U+16D6E DANDA.
    assert conv.convert("//").unicode_text == "\U00016d6f"
    # 'ee' (0x65 0x65) -> U+16D68 VOWEL SIGN AI.
    assert conv.convert("ee").unicode_text == "\U00016d68"


def test_kiratrai_mapped_bytes_are_in_block_and_nfc():
    res = convert_kiratrai("ebr kueuqb")
    non_ascii = [c for c in res.unicode_text if ord(c) > 0x7F]
    assert non_ascii, "expected Kirat Rai output"
    assert all(0x16D40 <= ord(c) <= 0x16D7F for c in non_ascii)
    assert res.kiratrai_char_count == len(non_ascii)
    assert res.unicode_text == unicodedata.normalize("NFC", res.unicode_text)


def test_convert_dispatches_to_kiratrai():
    assert _has_kiratrai(convert("a", font="kiratrai"))
    assert _has_kiratrai(convert("0", font="kiratrai"))


def test_kiratrai_unmapped_byte_surfaced_not_dropped():
    # 'f' is a real AKRS glyph missing from SIL's class table. Although it is
    # ASCII-shaped in extracted text, it must still be surfaced.
    res = convert_kiratrai("f")
    assert "U+0066" in res.unmapped_codepoints
    assert "f" in res.unicode_text
    with pytest.raises(ValueError):
        convert_kiratrai("f", strict=True)


def test_kiratrai_genuine_unicode_passes_through():
    text = "\U00016d43"
    res = convert_kiratrai(text, strict=True)
    assert res.unicode_text == text
    assert not res.unmapped_codepoints
