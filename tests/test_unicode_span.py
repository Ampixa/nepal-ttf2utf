"""Already-Unicode font-span routing tests."""

import unicodedata

import pytest

from nepal_ttf2utf import (
    UNICODE_REPERTOIRE_VERSION,
    convert,
    supported_fonts,
    supported_unicode_scripts,
    validate_unicode_span,
)
from nepal_ttf2utf.limbu import convert_limbu
from nepal_ttf2utf.tirhuta import convert_tirhuta


@pytest.mark.parametrize(
    ("script", "codepoint"),
    [
        ("Brahmi", 0x11013),
        ("Devanagari", 0x0915),
        ("Gurung Khema", 0x16100),
        ("Kirat Rai", 0x16D43),
        ("Lepcha", 0x1C00),
        ("Limbu", 0x1900),
        ("Newa", 0x11400),
        ("Ol Chiki", 0x1C5A),
        ("Sunuwar", 0x11BC0),
        ("Tibetan", 0x0F40),
        ("Tirhuta", 0x11480),
    ],
)
def test_every_package_output_script_has_a_unicode_validator(script, codepoint):
    text = chr(codepoint)
    result = validate_unicode_span(text, script=script.lower(), strict=True)
    assert result.unicode_text == text
    assert result.script == script
    assert result.script_char_count == 1
    assert result.invalid_codepoints == []
    assert result.unexpected_script_codepoints == []


def test_unicode_repertoire_is_version_pinned_and_discoverable():
    assert UNICODE_REPERTOIRE_VERSION == "17.0.0"
    assert supported_unicode_scripts() == (
        "Brahmi",
        "Devanagari",
        "Gurung Khema",
        "Kirat Rai",
        "Lepcha",
        "Limbu",
        "Newa",
        "Ol Chiki",
        "Sunuwar",
        "Tibetan",
        "Tirhuta",
    )


def test_new_unicode_scripts_do_not_depend_on_the_python_unicode_database(monkeypatch):
    original_category = unicodedata.category
    newer_codepoints = {0x11B00, 0x11BC0, 0x16100, 0x16D40}

    def old_runtime_category(char):
        if ord(char) in newer_codepoints:
            return "Cn"
        return original_category(char)

    monkeypatch.setattr("nepal_ttf2utf.unicode_span.unicodedata.category", old_runtime_category)
    for script, codepoint in (
        ("Devanagari", 0x11B00),
        ("Sunuwar", 0x11BC0),
        ("Gurung Khema", 0x16100),
        ("Kirat Rai", 0x16D40),
    ):
        result = validate_unicode_span(chr(codepoint), script=script, strict=True)
        assert result.script_char_count == 1
        assert result.invalid_codepoints == []


@pytest.mark.parametrize(
    ("script", "decomposed", "composed"),
    [
        ("Gurung Khema", "\U0001611e\U0001611e", "\U00016121"),
        ("Gurung Khema", "\U0001611e\U0001611e\U0001611f", "\U00016126"),
        ("Kirat Rai", "\U00016d67\U00016d67", "\U00016d68"),
        ("Kirat Rai", "\U00016d63\U00016d67\U00016d67", "\U00016d6a"),
    ],
)
def test_unicode16_nfc_composition_is_version_stable(script, decomposed, composed, monkeypatch):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )
    assert validate_unicode_span(decomposed, script=script, strict=True).unicode_text == composed


def test_reserved_codepoint_in_a_supported_block_is_rejected():
    source = chr(0x1613A)
    result = validate_unicode_span(source, script="Gurung Khema")
    assert result.invalid_codepoints == ["U+1613A"]
    with pytest.raises(ValueError, match=r"U\+1613A"):
        validate_unicode_span(source, script="Gurung Khema", strict=True)


@pytest.mark.parametrize("codepoint", [0xE000, 0xF0000, 0x100000])
def test_unicode_span_reports_private_use_values(codepoint):
    source = "𑐣" + chr(codepoint)
    result = validate_unicode_span(source, script="Newa")
    assert result.invalid_codepoints == [f"U+{codepoint:04X}"]
    with pytest.raises(ValueError, match=f"U\\+{codepoint:04X}"):
        validate_unicode_span(source, script="Newa", strict=True)


def test_unicode_span_reports_a_supported_but_misrouted_script():
    result = validate_unicode_span("𑐣म", script="Newa")
    assert result.script_char_count == 1
    assert result.unexpected_script_codepoints == ["U+092E"]
    with pytest.raises(ValueError, match=r"U\+092E.*Devanagari"):
        validate_unicode_span("𑐣म", script="Newa", strict=True)


def test_unicode_span_allows_embedded_latin_digits_and_punctuation():
    text = "𑐣 Newa 2026!"
    assert validate_unicode_span(text, script="Newa", strict=True).unicode_text == text


def test_shared_indic_dandas_are_not_attributed_exclusively_to_devanagari():
    tirhuta = convert_tirhuta("क।", strict=True).unicode_text
    assert validate_unicode_span(tirhuta, script="Tirhuta", strict=True).unicode_text == tirhuta

    limbu = convert_limbu("k.", strict=True)
    assert limbu.endswith("॥")
    assert validate_unicode_span(limbu, script="Limbu", strict=True).unicode_text == limbu


def test_common_tibetan_block_symbols_are_not_attributed_to_tibetan_script():
    text = "𑐣\u0fd5"
    assert validate_unicode_span(text, script="Newa", strict=True).unicode_text == text
    assert validate_unicode_span("ཀ\u0fd5", script="Tibetan", strict=True).unicode_text == "ཀ\u0fd5"
    with pytest.raises(ValueError, match="contains no Tibetan"):
        validate_unicode_span("\u0fd5", script="Tibetan", strict=True)


SCX_POLICY_SAMPLES = "\u02bc\u0300\u0951\u0952\u0965\u1cd1\u20f0\u3008\u300b"


def test_script_extensions_are_not_a_negative_script_allowlist():
    # U+1CD1 has the singleton Script_Extensions value Deva; other samples have
    # target-omitting or multi-script associations. None is exclusive ownership.
    for script, base in (("Newa", "𑐣"), ("Tibetan", "ཀ")):
        result = validate_unicode_span(base + SCX_POLICY_SAMPLES, script=script, strict=True)
        assert result.script_char_count == 1
        assert result.unexpected_script_codepoints == []


def test_script_extensions_do_not_anchor_native_script_presence():
    result = validate_unicode_span(SCX_POLICY_SAMPLES, script="Newa")
    assert result.script_char_count == 0
    with pytest.raises(ValueError, match="contains no Newa"):
        validate_unicode_span(SCX_POLICY_SAMPLES, script="Newa", strict=True)


def test_runtime_unassigned_detection_remains_strict_outside_pinned_blocks():
    source = "𑐣\u0378"
    result = validate_unicode_span(source, script="Newa")
    assert result.invalid_codepoints == ["U+0378"]
    with pytest.raises(ValueError, match=r"U\+0378"):
        validate_unicode_span(source, script="Newa", strict=True)


@pytest.mark.parametrize("codepoint", [0xFDD0, 0xFFFE, 0x1FFFE, 0x10FFFF])
def test_unicode_noncharacters_are_always_invalid(codepoint):
    source = "𑐣" + chr(codepoint)
    result = validate_unicode_span(source, script="Newa")
    assert result.invalid_codepoints == [f"U+{codepoint:04X}"]
    with pytest.raises(ValueError, match=f"U\\+{codepoint:04X}"):
        validate_unicode_span(source, script="Newa", strict=True)


def test_unicode_tibetan_font_families_are_normalized_without_legacy_mapping():
    text = "བོད་ཡིག"
    for font in (
        "monlam-unicode",
        "MonlamUniOuChan5",
        "microsoft-himalaya",
        "qomolangma-title",
        "jomolhari",
        "Jomolhari-ID",
        "Qomolangma-Uchen-Suring",
        "CTRC-HT",
    ):
        assert convert(text, font=font, strict=True) == text


def test_unicode_newa_font_families_are_normalized_without_legacy_mapping():
    text = "𑐣𑐾𑐥𑐵𑐮"
    assert convert(text, font="newa-unicode", strict=True) == text
    assert convert(text, font="Noto Sans Newa", strict=True) == text
    assert convert(text, font="Nithya Ranjana NU", strict=True) == text


@pytest.mark.parametrize(
    ("font", "text"),
    [
        ("Namdhinggo-Regular", "ᤀ"),
        ("NotoSansLimbu-Regular", "ᤀ"),
        ("Kanchenjunga-Regular", "𖵃"),
        ("NotoSansSunuwar-Regular", "𑯀"),
        ("Mingzat-Regular", "ᰀ"),
        ("NotoSansLepcha-Regular", "ᰀ"),
        ("NotoSansOlChiki-Regular", "ᱚ"),
        ("NotoSansTirhuta-Regular", "𑒀"),
        ("NotoSansGurungKhema", "𖄀"),
        ("NotoSansDevanagari-Regular", "म"),
        ("NotoSerifDevanagari-Regular", "म"),
        ("NotoSansNewa-Regular", "𑐣"),
    ],
)
def test_modern_native_unicode_font_families_are_identity_routed(font, text):
    assert convert(text, font=font, strict=True) == text


def test_modern_namdhinggo_route_is_distinct_from_legacy_namdhinggo():
    assert convert("k", font="namdhinggo") != "k"
    with pytest.raises(ValueError, match="contains no Limbu"):
        convert("k", font="namdhinggo-unicode", strict=True)


def test_unicode_devanagari_and_ranjana_du_fonts_are_identity_routed():
    text = "मगर नेपाल"
    assert convert(text, font="AnnapurnaSILNepal", strict=True) == text
    assert convert(text, font="Nithya Ranjana DU", strict=True) == text


def test_madan2_exact_name_routes_unicode_devanagari_without_a_legacy_pass():
    source = "नेपाल क्षेत्र e\u0301 २०८३।"
    expected = unicodedata.normalize("NFC", source)
    assert convert(source, font="Madan2", strict=True) == expected
    assert convert(source, font="  mAdAn2  ", strict=True) == expected
    assert convert(source, font="ABCDEF+Madan2", strict=True) == expected
    assert convert("g]kfn", font="Madan2") == "g]kfn"


def test_madan2_strict_route_rejects_unanchored_invalid_and_misrouted_text():
    with pytest.raises(ValueError, match="contains no Devanagari"):
        convert("g]kfn", font="Madan2", strict=True)
    with pytest.raises(ValueError, match=r"U\+11400.*Newa"):
        convert("म𑐀", font="Madan2", strict=True)
    with pytest.raises(ValueError, match=r"U\+11480.*Tirhuta"):
        convert("म𑒀", font="Madan2", strict=True)
    with pytest.raises(ValueError, match=r"U\+FFFD"):
        convert("म�", font="Madan2", strict=True)
    with pytest.raises(ValueError, match=r"U\+11B0A"):
        convert("म\U00011b0a", font="Madan2", strict=True)


@pytest.mark.parametrize(
    "font",
    ["madan", "madan.ttf", "madan2-regular", "Madan2 Regular", "ABCDE+Madan2"],
)
def test_madan2_route_does_not_infer_unsupported_names(font):
    with pytest.raises(ValueError, match="unsupported font key"):
        convert("नेपाल", font=font, strict=True)


def test_pdf_subset_prefix_is_removed_before_font_routing():
    assert convert("བོད", font="ABCDEF+Jomolhari-ID", strict=True) == "བོད"
    assert convert("नेपाल", font="ABCDEF+AnnapurnaSILNepal", strict=True) == "नेपाल"


def test_unicode_span_reports_replacement_characters():
    result = validate_unicode_span("བ�", script="Tibetan")
    assert result.invalid_codepoints == ["U+FFFD"]
    with pytest.raises(ValueError, match=r"U\+FFFD"):
        validate_unicode_span("བ�", script="Tibetan", strict=True)


def test_strict_unicode_span_rejects_a_misrouted_nonempty_span():
    with pytest.raises(ValueError, match="contains no Newa"):
        convert("legacy ASCII", font="newa", strict=True)


def test_unicode_fonts_are_discoverable():
    fonts = supported_fonts()
    assert fonts["monlam-unicode"] == "Tibetan"
    assert fonts["microsoft-himalaya"] == "Tibetan"
    assert fonts["newa-unicode"] == "Newa"
    assert fonts["annapurnasilnepal"] == "Devanagari"
    assert fonts["madan2"] == "Devanagari"
    assert "madan" not in fonts
    assert "madan2-regular" not in fonts
    assert fonts["nithyaranjanadu"] == "Devanagari"
    assert fonts["nithyaranjananu"] == "Newa"
    assert fonts["namdhinggo-regular"] == "Limbu"
    assert fonts["kanchenjunga-regular"] == "Kirat Rai"
    assert fonts["notosanssunuwar-regular"] == "Sunuwar"
    assert fonts["notosanslepcha-regular"] == "Lepcha"
    assert fonts["notosansolchiki-regular"] == "Ol Chiki"
    assert fonts["notosanstirhuta-regular"] == "Tirhuta"
    assert fonts["notosansgurungkhema"] == "Gurung Khema"
