"""SIL JG Lepcha legacy-font conversion tests."""

import hashlib
import re
from importlib import resources

import pytest

from nepal_ttf2utf import convert, convert_jg_lepcha
from nepal_ttf2utf.jg_lepcha import JGLepchaConverter


def test_jg_lepcha_map_matches_the_pinned_sil_source_and_parser_inventory():
    map_resource = resources.files("nepal_ttf2utf.maps") / "JGLepcha.map"
    assert hashlib.sha256(map_resource.read_bytes()).hexdigest() == (
        "179d172b4bd4223f40b1ddc1a0daeb6547b5ad97dc1be7df2b09f2bf45ff6b2d"
    )

    converter = JGLepchaConverter.default()
    assert len(converter._byte_rules) == 160
    assert len(converter._reorder_rules) == 72
    assert len(converter._unicode_classes) == 11
    assert converter._uncertain_source_codepoints == frozenset({0x3C, 0x3D, 0x3E})


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


@pytest.mark.parametrize(
    ("source", "source_label"),
    [("<", "U+003C"), ("=", "U+003D"), (">", "U+003E")],
)
def test_jg_lepcha_upstream_placeholder_mappings_are_uncertain(source, source_label):
    result = convert_jg_lepcha(source)
    assert result.unicode_text == "◌"
    assert result.lepcha_char_count == 0
    assert result.replacement_count == 1
    assert result.unmapped_codepoints == []
    assert result.uncertain_codepoints == [source_label]

    with pytest.raises(ValueError, match=rf"{re.escape(source_label)}.*U\+25CC"):
        convert_jg_lepcha(source, strict=True)
    with pytest.raises(ValueError, match=rf"{re.escape(source_label)}.*U\+25CC"):
        convert(source, font="jg-lepcha", strict=True)


def test_jg_lepcha_placeholder_diagnostics_preserve_all_source_values():
    result = convert_jg_lepcha("<=>")
    assert result.unicode_text == "◌◌◌"
    assert result.replacement_count == 3
    assert result.unmapped_codepoints == []
    assert result.uncertain_codepoints == ["U+003C", "U+003D", "U+003E"]


def test_jg_lepcha_direct_dotted_circle_remains_an_unmapped_value():
    result = convert_jg_lepcha("◌")
    assert result.unicode_text == "◌"
    assert result.replacement_count == 0
    assert result.unmapped_codepoints == ["U+25CC"]
    assert result.uncertain_codepoints == []
    with pytest.raises(ValueError, match=r"U\+25CC"):
        convert_jg_lepcha("◌", strict=True)


def test_jg_lepcha_neighboring_evidenced_rules_remain_strict_clean():
    result = convert_jg_lepcha("./k", strict=True)
    assert result.unicode_text == "᰿ ᰀ"
    assert result.replacement_count == 3
    assert result.unmapped_codepoints == []
    assert result.uncertain_codepoints == []


def test_jg_lepcha_unmapped_ascii_is_surfaced():
    result = convert_jg_lepcha("~")
    assert result.unicode_text == "~"
    assert result.unmapped_codepoints == ["U+007E"]
    with pytest.raises(ValueError, match="unmapped/leftover characters"):
        convert_jg_lepcha("~", strict=True)


def test_jg_lepcha_genuine_unicode_passes_through():
    result = convert_jg_lepcha("ᰀ", strict=True)
    assert result.unicode_text == "ᰀ"
    assert not result.unmapped_codepoints


def test_convert_dispatches_to_jg_lepcha():
    assert convert("k", font="jg-lepcha") == "ᰀ"
