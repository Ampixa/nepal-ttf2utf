"""Public package API tests."""

import pytest

from nepal_ttf2utf import __version__, convert, supported_fonts


def test_version_matches_release():
    assert __version__ == "0.2.0"


@pytest.mark.parametrize(
    ("font", "script"),
    [
        ("preeti", "Devanagari"),
        ("namdhinggo", "Limbu"),
        ("kiratraifont", "Kirat Rai"),
        ("kiratraifontnew", "Kirat Rai"),
        ("koits", "Sunuwar"),
        ("tibetanmachine", "Tibetan"),
        ("lepcha-sikkimherald", "Lepcha"),
        ("jg-lepcha", "Lepcha"),
        ("olck-optimum", "Ol Chiki"),
        ("janaki", "Tirhuta"),
    ],
)
def test_supported_fonts_covers_every_converter_family(font, script):
    assert supported_fonts()[font] == script


def test_font_dispatch_is_case_insensitive_and_trimmed():
    assert convert("k", font="  JG-LEPCHA  ") == "ᰀ"


def test_unknown_font_reports_supported_devanagari_keys():
    with pytest.raises(ValueError, match="unsupported Devanagari font"):
        convert("text", font="does-not-exist")
