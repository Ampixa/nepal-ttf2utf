"""Sunuwar / Jenticha (Koĩts) legacy display-font conversion tests.

Anchors are the printed-crop / round-trip-verified assignments from the source
derivation (``outputs/sunuwar-map-derivation``). The formerly uncertain ``|`` byte
is confirmed as the Sikkim regional form of U+11BC5 UTTHI.
"""

import unicodedata

import pytest

from nepal_ttf2utf import convert, convert_sunuwar
from nepal_ttf2utf.sunuwar import (
    SUNUWAR_DIGITS,
    SUNUWAR_LETTERS_CONFIRMED,
    SUNUWAR_LETTERS_UNCERTAIN,
    SunuwarConverter,
)


def test_sunuwar_digits_map_in_order_to_block():
    conv = SunuwarConverter()
    for i in range(10):
        assert conv.convert(str(i)).unicode_text == chr(0x11BF0 + i)


def test_sunuwar_confirmed_map_is_one_to_one_in_block():
    cps = [ord(v) for v in list(SUNUWAR_LETTERS_CONFIRMED.values()) + list(SUNUWAR_DIGITS.values())]
    assert all(0x11BC0 <= cp <= 0x11BFF for cp in cps)
    assert len(cps) == len(set(cps)), "confirmed map must be one-to-one"


def test_sunuwar_full_map_including_uncertain_is_one_to_one():
    cps = [
        ord(v)
        for v in list(SUNUWAR_LETTERS_CONFIRMED.values())
        + list(SUNUWAR_DIGITS.values())
        + list(SUNUWAR_LETTERS_UNCERTAIN.values())
    ]
    assert all(0x11BC0 <= cp <= 0x11BFF for cp in cps)
    assert len(cps) == len(set(cps)), "byte->codepoint map must be globally one-to-one"


def test_sunuwar_high_frequency_anchor_letters():
    conv = SunuwarConverter()
    assert conv.convert("{").unicode_text == chr(0x11BC3)  # imar (cross)
    assert conv.convert("}").unicode_text == chr(0x11BC2)  # eko
    assert conv.convert("A").unicode_text == chr(0x11BD6)  # aal (highest-freq byte)
    assert conv.convert("i").unicode_text == chr(0x11BCC)  # carmi
    assert conv.convert("y").unicode_text == chr(0x11BDC)  # shyer


def test_sunuwar_second_pass_resolved_letters_applied_by_default():
    conv = SunuwarConverter()
    resolved = {
        "v": 0x11BC4,  # reu
        "q": 0x11BE0,  # kloko
        "x": 0x11BD3,  # varca
        "r": 0x11BD9,  # phar
        "u": 0x11BD4,  # yat
        "g": 0x11BD5,  # ava
        "h": 0x11BDA,  # ngar
        "j": 0x11BCF,  # jyah
    }
    for byte, cp in resolved.items():
        res = conv.convert(byte)
        assert res.unicode_text == chr(cp), f"{byte!r} should map to U+{cp:05X}"
        assert res.confirmed_byte_count == 1
        assert res.uncertain_bytes == []


def test_sunuwar_no_uncertain_bytes_remain():
    assert SUNUWAR_LETTERS_UNCERTAIN == {}


def test_sunuwar_pipe_is_confirmed_utthi_by_default():
    res = convert_sunuwar("|")
    assert res.unicode_text == chr(0x11BC5)
    assert res.uncertain_bytes == []
    assert res.sunuwar_char_count == 1
    assert res.confirmed_byte_count == 1


def test_sunuwar_apply_uncertain_is_compatibility_noop():
    assert (
        convert_sunuwar("|").unicode_text == convert_sunuwar("|", apply_uncertain=True).unicode_text
    )


def test_sunuwar_strict_mode_accepts_confirmed_utthi():
    assert convert_sunuwar("|", strict=True).unicode_text == chr(0x11BC5)


def test_sunuwar_output_is_nfc_and_block_constrained_for_confirmed():
    res = convert_sunuwar("A{z}tO 18")
    non_ascii = [c for c in res.unicode_text if ord(c) > 0x7F]
    assert non_ascii
    assert all(0x11BC0 <= ord(c) <= 0x11BFF for c in non_ascii)
    assert res.sunuwar_char_count == len(non_ascii)
    assert res.unicode_text == unicodedata.normalize("NFC", res.unicode_text)
    # 6 confirmed letters (A { z } t O) + 2 confirmed digits (1 8) = 8.
    assert res.confirmed_byte_count == 8


def test_sunuwar_spaces_and_punctuation_pass_through():
    res = convert_sunuwar("A, O")
    assert " " in res.unicode_text
    assert "," in res.unicode_text


def test_sunuwar_structural_whitespace_is_not_reported_as_unmapped():
    res = convert_sunuwar("o\t\r\n", strict=True)
    assert res.unicode_text == "𑯀\t\r\n"
    assert res.uncertain_bytes == []
    assert res.unmapped_bytes == []


def test_sunuwar_unmapped_ascii_is_surfaced():
    res = convert_sunuwar("B")
    assert "B" in res.unmapped_bytes
    with pytest.raises(ValueError):
        convert_sunuwar("B", strict=True)


def test_sunuwar_genuine_unicode_passes_through():
    text = chr(0x11BC0)
    res = convert_sunuwar(text, strict=True)
    assert res.unicode_text == text
    assert not res.unmapped_bytes


def test_convert_dispatches_to_sunuwar():
    out = convert("A{z}", font="sunuwar")
    assert any(0x11BC0 <= ord(c) <= 0x11BFF for c in out)
