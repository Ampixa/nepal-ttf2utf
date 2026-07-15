"""Canonical-new and Sikkim Herald legacy Kirat Rai conversion tests.

Anchors are the round-trip-verified cases from the source derivation: SIL's TECkit
``kiratraifontnew.map`` byte-class table + its explicit multi-byte ligature rules.
"""

import unicodedata

import pytest

from nepal_ttf2utf import convert, convert_kiratrai, convert_kiratrai_herald
from nepal_ttf2utf.kiratrai import KIRATRAI_HERALD_PREMAP, KiratRaiConverter


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


@pytest.mark.parametrize("converter", [convert_kiratrai, convert_kiratrai_herald])
@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("\U00016d67\U00016d67", "\U00016d68"),
        ("\U00016d63\U00016d67", "\U00016d69"),
        ("\U00016d69\U00016d67", "\U00016d6a"),
        ("\U00016d63\U00016d67\U00016d67", "\U00016d6a"),
    ],
)
def test_kiratrai_unicode16_nfc_is_version_stable(converter, source, expected, monkeypatch):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )

    result = converter(source, strict=True)

    assert result.unicode_text == expected
    assert result.kiratrai_char_count == 1
    assert result.replacement_count == 0
    assert result.unmapped_codepoints == []


@pytest.mark.parametrize(
    ("converter", "source"),
    [
        (convert_kiratrai, "e\U00016d67"),
        (convert_kiratrai_herald, "r\U00016d67"),
    ],
)
def test_kiratrai_unicode16_nfc_composes_across_legacy_unicode_boundary(
    converter, source, monkeypatch
):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )

    result = converter(source, strict=True)

    assert result.unicode_text == "\U00016d68"
    assert result.kiratrai_char_count == 1
    assert result.replacement_count == 1
    assert result.unmapped_codepoints == []


def test_kiratrai_dispatchers_use_version_stable_unicode16_nfc(monkeypatch):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )
    source = "\U00016d67\U00016d67"

    assert convert(source, font="kiratraifontnew", strict=True) == "\U00016d68"
    assert convert(source, font="kiratraifont", strict=True) == "\U00016d68"


def test_convert_dispatches_to_kiratrai():
    assert _has_kiratrai(convert("a", font="kiratrai"))
    assert _has_kiratrai(convert("0", font="kiratrai"))


def test_kiratrai_unmapped_byte_surfaced_not_dropped():
    # Canonical-new byte 'f' is absent from SIL's class table. Herald 'f' belongs
    # to a different layout and is tested separately below.
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


def test_herald_full_observed_letter_premap_matches_exact_unicode_targets():
    expected = {
        "D": 0x16D4E,
        "F": 0x16D46,
        "G": 0x16D58,
        "H": 0x16D4B,
        "I": 0x16D51,
        "J": 0x16D4C,
        "K": 0x16D4F,
        "L": 0x16D6D,
        "O": 0x16D41,
        "R": 0x16D50,
        "S": 0x16D47,
        "U": 0x16D40,
        "a": 0x16D44,
        "b": 0x16D63,
        "c": 0x16D55,
        "d": 0x16D45,
        "e": 0x16D5B,
        "f": 0x16D48,
        "g": 0x16D60,
        "h": 0x16D43,
        "i": 0x16D5F,
        "j": 0x16D59,
        "k": 0x16D5D,
        "l": 0x16D64,
        "m": 0x16D49,
        "n": 0x16D57,
        "o": 0x16D56,
        "p": 0x16D52,
        "q": 0x16D54,
        "r": 0x16D67,
        "s": 0x16D4A,
        "t": 0x16D62,
        "u": 0x16D65,
        "v": 0x16D5A,
        "w": 0x16D5E,
        "x": 0x16D53,
        "y": 0x16D5C,
        "z": 0x16D6B,
    }
    assert set(KIRATRAI_HERALD_PREMAP) == set(expected)
    for byte, codepoint in expected.items():
        assert convert_kiratrai_herald(byte, strict=True).unicode_text == chr(codepoint)


def test_herald_corpus_masthead_regression():
    assert convert_kiratrai_herald("udzdle", strict=True).unicode_text == "".join(
        chr(codepoint) for codepoint in (0x16D65, 0x16D45, 0x16D6B, 0x16D45, 0x16D64, 0x16D5B)
    )


def test_herald_premap_preserves_canonical_multibyte_rules():
    assert convert_kiratrai_herald("rr", strict=True).unicode_text == chr(0x16D68)
    assert convert_kiratrai_herald("br", strict=True).unicode_text == chr(0x16D69)
    assert convert_kiratrai_herald("brr", strict=True).unicode_text == chr(0x16D6A)
    assert convert_kiratrai_herald("//", strict=True).unicode_text == chr(0x16D6F)


@pytest.mark.parametrize("blank", ["\\", "Z"])
def test_herald_blank_glyphs_normalize_to_space(blank):
    result = convert_kiratrai_herald(f"a{blank}a", strict=True)
    assert result.unicode_text == chr(0x16D44) + " " + chr(0x16D44)
    assert not result.unmapped_codepoints


def test_canonical_z_remains_kirat_rai_sang():
    assert convert_kiratrai("Z", strict=True).unicode_text == chr(0x16D6C)


def test_convert_dispatches_old_and_new_kiratrai_layouts_separately():
    assert convert("f", font="kiratraifont", strict=True) == chr(0x16D48)
    assert convert("N", font="kiratraifontnew", strict=True) == chr(0x16D48)
