"""Public package API tests."""

import pytest

from nepal_ttf2utf import __version__, convert, convert_devanagari, supported_fonts


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


def test_every_advertised_font_key_reaches_a_dispatch_route():
    for font in supported_fonts():
        assert convert("", font=font) == "", font


@pytest.mark.parametrize(
    ("font", "source", "expected"),
    [
        ("  JG-LEPCHA  ", "k", "ᰀ"),
        ("AbCdEf+JG_LEPCHA", "k", "ᰀ"),
        ("ABCDEF+PREETI", "g]kfn", "नेपाल"),
    ],
)
def test_font_key_normalization_preserves_supported_routes(font, source, expected):
    assert convert(source, font=font, strict=True) == expected


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


@pytest.mark.parametrize(
    ("font", "normalized_key"),
    [
        ("does-not-exist", "does-not-exist"),
        ("  Does_Not_Exist  ", "does-not-exist"),
        ("ABCDEF+Unknown_Font", "unknown-font"),
        ("ABCDE+Madan2", "abcde+madan2"),
        ("   ", ""),
    ],
)
def test_unknown_font_reports_normalized_package_key(font, normalized_key):
    with pytest.raises(ValueError) as error:
        convert("text", font=font)

    message = str(error.value)
    assert f"unsupported font key {normalized_key!r}" in message
    assert "supported_fonts()" in message
    assert "--list-fonts" in message
    assert "Devanagari" not in message
    assert "supported: [" not in message


def test_direct_devanagari_api_retains_its_specialized_unknown_font_error():
    with pytest.raises(ValueError, match="unsupported Devanagari font"):
        convert_devanagari("text", font="does-not-exist")


@pytest.mark.parametrize("font", [None, 123, b"preeti"])
def test_non_string_font_key_has_an_explicit_type_error(font):
    with pytest.raises(TypeError, match="font must be a string"):
        convert("text", font=font)
