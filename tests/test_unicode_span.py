"""Already-Unicode font-span routing tests."""

import pytest

from nepal_ttf2utf import convert, supported_fonts, validate_unicode_span


def test_unicode_tibetan_font_families_are_normalized_without_legacy_mapping():
    text = "བོད་ཡིག"
    for font in (
        "monlam-unicode",
        "MonlamUniOuChan5",
        "microsoft-himalaya",
        "qomolangma-title",
        "jomolhari",
    ):
        assert convert(text, font=font, strict=True) == text


def test_unicode_newa_font_families_are_normalized_without_legacy_mapping():
    text = "𑐣𑐾𑐥𑐵𑐮"
    assert convert(text, font="newa-unicode", strict=True) == text
    assert convert(text, font="Noto Sans Newa", strict=True) == text


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
