"""Sikkim Herald live-text Lepcha (Róng) conversion tests.

Anchors are the shape-identity + round-trip-verified cases from the source
derivation, including the pre-base vowel reordering this font requires.
"""

import unicodedata

import pytest

from nepal_ttf2utf import convert, convert_lepcha
from nepal_ttf2utf.lepcha import LepchaConverter


def test_lepcha_consonant_bytes_map_to_base_series():
    conv = LepchaConverter.default()
    # Uppercase Latin A.. -> the Lepcha base-consonant series in Unicode order.
    assert conv.convert("A").unicode_text == "ᰀ"  # KA
    assert conv.convert("B").unicode_text == "ᰂ"  # KHA
    assert conv.convert("C").unicode_text == "ᰃ"  # GA
    assert conv.convert("Z").unicode_text == "ᰠ"  # SA
    # Lowercase carry the two overflow bases SHA/WA + the independent vowel A.
    assert conv.convert("k").unicode_text == "ᰡ"  # SHA
    assert conv.convert("p").unicode_text == "ᰢ"  # WA
    assert conv.convert("w").unicode_text == "ᰣ"  # independent A


def test_lepcha_digits_map_to_lepcha_digits():
    conv = LepchaConverter.default()
    assert conv.convert("0").unicode_text == "᱀"  # DIGIT ZERO
    assert conv.convert("539").unicode_text == "᱅᱃᱉"  # 5 3 9


def test_lepcha_pre_base_vowel_reorders_after_base():
    conv = LepchaConverter.default()
    # In the legacy stream pre-base vowels I/O/OO are keyed BEFORE the base; Unicode
    # stores them AFTER. byte 'c' = VOWEL SIGN O.
    out = conv.convert("cA")  # O + KA (visual) -> KA + O (logical)
    assert [unicodedata.name(ch) for ch in out.unicode_text] == [
        "LEPCHA LETTER KA",
        "LEPCHA VOWEL SIGN O",
    ]
    # Same syllable typed base-first yields identical output.
    assert conv.convert("Ac").unicode_text == out.unicode_text


def test_lepcha_canonical_cluster_order():
    conv = LepchaConverter.default()
    # base 'A'=KA + post-base vowel 'g'=U + final ':'=SIGN M -> base + vowel + final.
    out = conv.convert("Ag:").unicode_text
    assert [unicodedata.name(ch) for ch in out] == [
        "LEPCHA LETTER KA",
        "LEPCHA VOWEL SIGN U",
        "LEPCHA CONSONANT SIGN M",
    ]


def test_lepcha_two_syllable_word_keeps_pre_vowel_with_its_base():
    conv = LepchaConverter.default()
    # 'Ag' (KA+U) then pre-base 'c' (O) belonging to the NEXT base 'C' (GA): the
    # trailing-sign run must STOP at the pre-base vowel so O attaches to GA, not KA.
    out = conv.convert("AgcC").unicode_text
    assert [unicodedata.name(ch) for ch in out] == [
        "LEPCHA LETTER KA",
        "LEPCHA VOWEL SIGN U",
        "LEPCHA LETTER GA",
        "LEPCHA VOWEL SIGN O",
    ]


def test_lepcha_output_is_nfc_and_in_block():
    res = convert_lepcha("AgC: cA dC")
    non_space = [ch for ch in res.unicode_text if ch != " "]
    assert non_space, "expected Lepcha output"
    assert all(0x1C00 <= ord(ch) <= 0x1C4F for ch in non_space)
    assert res.unicode_text == unicodedata.normalize("NFC", res.unicode_text)


def test_lepcha_remaining_unmapped_bytes_are_flagged_not_silently_dropped():
    res = convert_lepcha("A*()+/")
    assert res.unmapped_bytes == ["0x28", "0x29", "0x2A", "0x2B", "0x2F"]
    with pytest.raises(ValueError):
        convert_lepcha("A*()+/", strict=True)


def test_lepcha_visual_leading_final_k_moves_to_following_base():
    # Legacy ]=FINAL K and d=pre-base I both precede the base T. The final must
    # not attach to the preceding A syllable.
    result = convert_lepcha("A]dT", strict=True)
    assert [unicodedata.name(ch) for ch in result.unicode_text] == [
        "LEPCHA LETTER KA",
        "LEPCHA LETTER DZA",
        "LEPCHA VOWEL SIGN I",
        "LEPCHA CONSONANT SIGN K",
    ]


def test_lepcha_subjoined_ra_and_hyphen_are_resolved():
    result = convert_lepcha(r"C\% -", strict=True)
    assert result.unicode_text == "ᰃ᰷ᰥ -"
    assert not result.unmapped_bytes


def test_lepcha_structural_whitespace_is_not_reported_as_unmapped():
    result = convert_lepcha("A\t\r\n", strict=True)
    assert result.unicode_text == "ᰀ\t\r\n"
    assert result.unmapped_bytes == []


def test_convert_dispatches_to_lepcha():
    out = convert("AgC", font="lepcha-sikkimherald")
    assert any(0x1C00 <= ord(c) <= 0x1C4F for c in out)


def test_lepcha_genuine_unicode_passes_through():
    text = "ᰀᰪ"
    res = convert_lepcha(text, strict=True)
    assert res.unicode_text == text
    assert not res.unmapped_bytes


def test_lepcha_empty_map_rejected():
    with pytest.raises(ValueError):
        LepchaConverter({})


def test_nukta_precedes_subjoined_in_canonical_order():
    # The Unicode Standard ch.13 Table 13-9: encoding order is consonant,
    # nukta, subjoined consonant, vowel sign, final, ran. The spec's worked
    # example: retroflex t = <KA, NUKTA, SUBJOINED RA>. Regression for the
    # 2026-07-14 audit finding (nukta was emitted after subjoined marks).
    from nepal_ttf2utf.lepcha import convert_lepcha

    for raw in ("A\\&", "A&\\"):  # KA+NUKTA+SUBJ-YA in both input orders
        out = convert_lepcha(raw).unicode_text
        assert "ᰀ᰷ᰤ" in out, (raw, out.encode("unicode_escape"))
