"""Public package API tests."""

import pytest

from nepal_ttf2utf import __version__, convert, supported_fonts


def test_version_matches_release():
    assert __version__ == "0.3.0"


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
        ("olcklatic-normal", "Ol Chiki"),
        ("janaki", "Tirhuta"),
        ("annapurnasilnepal", "Devanagari"),
        ("nithyaranjanadu", "Devanagari"),
        ("nithyaranjananu", "Newa"),
        ("magar-akkha-brahmi", "Brahmi"),
        ("namdhinggo-regular", "Limbu"),
        ("kanchenjunga-regular", "Kirat Rai"),
        ("notosanssunuwar-regular", "Sunuwar"),
        ("notosansgurungkhema", "Gurung Khema"),
    ],
)
def test_supported_fonts_covers_every_converter_family(font, script):
    assert supported_fonts()[font] == script


def test_font_dispatch_is_case_insensitive_and_trimmed():
    assert convert("k", font="  JG-LEPCHA  ") == "ᰀ"


def test_pdf_subset_font_prefix_is_ignored():
    assert convert("𑑅", font="ABCDEF+NithyaRanjanaNU-Regular", strict=True) == "𑑅"


@pytest.mark.parametrize(
    ("font", "source", "mapped"),
    [
        ("preeti", "g]kfn", "नेपाल"),
        ("namdhinggo", "k", "ᤐ"),
        ("kiratraifontnew", "N", "𖵈"),
        ("kiratraifont", "f", "𖵈"),
        ("sunuwar", "o", "𑯀"),
        ("lepcha-sikkimherald", "A", "ᰀ"),
        ("jg-lepcha", "k", "ᰀ"),
        ("olck-optimum", "a", "ᱟ"),
        ("olcklatic-normal", "a", "ᱟ"),
        ("janaki", "क", "𑒏"),
        ("tibetanmachine", "!", "ཀ"),
    ],
)
def test_every_legacy_route_preserves_structural_whitespace(font, source, mapped):
    separators = " \t\r\n"
    assert convert(source + separators + source, font=font, strict=True) == (
        mapped + separators + mapped
    )


def test_unknown_font_reports_supported_devanagari_keys():
    with pytest.raises(ValueError, match="unsupported Devanagari font"):
        convert("text", font="does-not-exist")
