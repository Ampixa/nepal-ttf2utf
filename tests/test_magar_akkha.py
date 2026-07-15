"""Standards-aligned Magar Akkha/Brahmi transliteration tests."""

import pytest

from nepal_ttf2utf import convert, transliterate_magar_akkha


@pytest.mark.parametrize(
    "devanagari",
    ["मगर", "मगर ढुट", "नेपाल", "क्षेत्र", "ज्ञान", "नमस्ते", "१२३४५६७८९०"],
)
def test_devanagari_brahmi_roundtrip_is_lossless_by_default(devanagari):
    brahmi = transliterate_magar_akkha(devanagari, strict=True)
    restored = transliterate_magar_akkha(brahmi.unicode_text, target="devanagari", strict=True)
    assert restored.unicode_text == devanagari


def test_forward_output_uses_unicode_brahmi():
    result = transliterate_magar_akkha("क", strict=True)
    assert result.unicode_text == "𑀓"
    assert result.replacement_count == 1


def test_minimal_inventory_folding_is_explicit_and_counted():
    lossless = transliterate_magar_akkha("टश")
    folded = transliterate_magar_akkha("टश", fold_to_minimal_inventory=True)
    assert lossless.unicode_text != folded.unicode_text
    assert folded.folded_count == 2
    assert folded.unicode_text == transliterate_magar_akkha("तस").unicode_text


def test_unmapped_devanagari_is_preserved_and_strictly_reported():
    result = transliterate_magar_akkha("ऋ")
    assert result.unicode_text == "ऋ"
    assert result.unmapped_codepoints == ["U+090B"]
    with pytest.raises(ValueError, match=r"U\+090B"):
        transliterate_magar_akkha("ऋ", strict=True)


def test_already_brahmi_akkha_route_validates_without_retransliteration():
    text = transliterate_magar_akkha("मगर", strict=True).unicode_text
    assert convert(text, font="magar-akkha-brahmi", strict=True) == text
