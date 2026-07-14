"""SIL JG Lepcha legacy-font conversion tests."""

import pytest

from nepal_ttf2utf import convert, convert_jg_lepcha
from nepal_ttf2utf.jg_lepcha import JGLepchaConverter


def test_jg_lepcha_consonants_and_digits_follow_sil_classes():
    converter = JGLepchaConverter.default()
    assert converter.convert("k").unicode_text == "ᰀ"
    assert converter.convert("W").unicode_text == "ᰁ"
    assert converter.convert("0123456789").unicode_text == "᱀᱁᱂᱃᱄᱅᱆᱇᱈᱉"


def test_jg_lepcha_visual_prebase_vowel_reorders():
    # byte i = vowel sign I, byte k = letter KA
    assert convert_jg_lepcha("ik").unicode_text == "ᰀᰧ"


def test_jg_lepcha_composites_and_conjuncts():
    # '!' is SIL's OO + final K composite. Latin-1 À is byte 0xC0,
    # the precomposed legacy KA+subjoined-YA conjunct.
    assert convert_jg_lepcha("!").unicode_text == "ᰩᰭ"
    assert convert_jg_lepcha("À").unicode_text == "ᰀᰤ"


def test_jg_lepcha_contextual_a_rule_uses_negated_previous_class():
    # Standalone a is independent A. After a dependent-vowel byte it falls
    # through to the regular dependent-vowel class, exactly as SIL specifies.
    assert convert_jg_lepcha("a").unicode_text == "ᰦ"
    assert convert_jg_lepcha("Oa").unicode_text == "ᰨᰨ"


def test_jg_lepcha_unmapped_ascii_is_surfaced():
    result = convert_jg_lepcha("~")
    assert result.unicode_text == "~"
    assert result.unmapped_codepoints == ["U+007E"]
    with pytest.raises(ValueError):
        convert_jg_lepcha("~", strict=True)


def test_jg_lepcha_genuine_unicode_passes_through():
    result = convert_jg_lepcha("ᰀ", strict=True)
    assert result.unicode_text == "ᰀ"
    assert not result.unmapped_codepoints


def test_convert_dispatches_to_jg_lepcha():
    assert convert("k", font="jg-lepcha") == "ᰀ"
