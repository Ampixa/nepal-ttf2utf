"""Cross-converter control-character safety tests."""

import pytest

from nepal_ttf2utf import convert
from nepal_ttf2utf._controls import DIAGNOSTIC_C0, STRUCTURAL_C0
from nepal_ttf2utf.devanagari import convert_devanagari
from nepal_ttf2utf.jg_lepcha import JGLepchaConverter
from nepal_ttf2utf.kiratrai import KiratRaiConverter
from nepal_ttf2utf.limbu import LimbuConverter, convert_limbu
from nepal_ttf2utf.olchiki import convert_olchiki, convert_olchiki_latic
from nepal_ttf2utf.sunuwar import convert_sunuwar

DIAGNOSTIC_TEXT = "".join(sorted(DIAGNOSTIC_C0, key=ord))
DIAGNOSTIC_LABELS = [f"U+{ord(char):04X}" for char in DIAGNOSTIC_TEXT]
ALL_C0_TEXT = "".join(chr(codepoint) for codepoint in range(0x20))

LEGACY_ROUTES = (
    ("preeti", "g]kfn"),
    ("namdhinggo", "k"),
    ("kiratraifontnew", "N"),
    ("kiratraifont", "f"),
    ("sunuwar", "o"),
    ("lepcha-sikkimherald", "A"),
    ("jg-lepcha", "k"),
    ("olck-optimum", "a"),
    ("olcklatic-normal", "a"),
    ("janaki", "क"),
    ("tibetanmachine", "!"),
)


def test_diagnostic_c0_inventory_is_exact():
    assert len(DIAGNOSTIC_C0) == 29
    assert STRUCTURAL_C0 == frozenset("\t\r\n")
    assert not DIAGNOSTIC_C0 & STRUCTURAL_C0
    assert {ord(char) for char in DIAGNOSTIC_C0} | {9, 10, 13} == set(range(0x20))


@pytest.mark.parametrize(("font", "source"), LEGACY_ROUTES)
def test_every_legacy_route_rejects_and_labels_every_diagnostic_c0(font, source):
    for control in DIAGNOSTIC_TEXT:
        with pytest.raises(ValueError) as error:
            convert(source + control, font=font, strict=True)
        codepoint_label = f"U+{ord(control):04X}"
        byte_label = f"0x{ord(control):02X}"
        assert codepoint_label in str(error.value) or byte_label in str(error.value)


def test_devanagari_retains_lenient_cleanup_but_reports_removed_controls():
    result = convert_devanagari(DIAGNOSTIC_TEXT, font="preeti")
    assert result.unicode_text == ""
    assert not result.clean
    assert result.leftover == list(DIAGNOSTIC_TEXT)
    with pytest.raises(ValueError) as error:
        convert_devanagari(DIAGNOSTIC_TEXT, font="preeti", strict=True)
    assert all(label in str(error.value) for label in DIAGNOSTIC_LABELS)


@pytest.mark.parametrize(
    "converter",
    [LimbuConverter.default(), KiratRaiConverter.default(), JGLepchaConverter.default()],
)
def test_teckit_control_rules_preserve_but_diagnose_c0_outside_allowlist(converter):
    result = converter.convert(DIAGNOSTIC_TEXT)
    assert result.unicode_text == DIAGNOSTIC_TEXT
    assert result.replacement_count == 29
    assert result.unmapped_codepoints == DIAGNOSTIC_LABELS


def test_limbu_direct_strict_error_lists_every_diagnostic_c0():
    with pytest.raises(ValueError) as error:
        convert_limbu(DIAGNOSTIC_TEXT, strict=True)
    assert all(label in str(error.value) for label in DIAGNOSTIC_LABELS)


def test_limbu_complete_ctl_class_counts_all_32_positional_rules():
    result = LimbuConverter.default().convert(ALL_C0_TEXT)
    assert result.unicode_text == ALL_C0_TEXT
    assert result.replacement_count == 32
    assert result.unmapped_codepoints == DIAGNOSTIC_LABELS


@pytest.mark.parametrize("converter", [convert_sunuwar, convert_olchiki, convert_olchiki_latic])
def test_raw_byte_result_apis_use_visible_codepoints_in_strict_errors(converter):
    result = converter(DIAGNOSTIC_TEXT)
    assert result.unicode_text == DIAGNOSTIC_TEXT
    assert result.unmapped_bytes == list(DIAGNOSTIC_TEXT)

    with pytest.raises(ValueError) as error:
        converter(DIAGNOSTIC_TEXT, strict=True)
    message = str(error.value)
    assert all(label in message for label in DIAGNOSTIC_LABELS)
    assert not DIAGNOSTIC_C0 & set(message)


@pytest.mark.parametrize(
    "converter",
    [LimbuConverter.default(), KiratRaiConverter.default(), JGLepchaConverter.default()],
)
def test_teckit_structural_controls_keep_existing_map_counts(converter):
    text = "\t\r\n"
    result = converter.convert(text)
    assert result.unicode_text == text
    assert result.replacement_count == 3
    assert result.unmapped_codepoints == []
