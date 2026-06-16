"""Devanagari conversion tests, anchored on real Gorkhapatra / known words."""

import pytest

from lipantar import convert
from lipantar.devanagari import convert_devanagari, supported_devanagari_fonts


def test_preeti_known_words():
    assert convert("g]kfn", font="preeti") == "नेपाल"
    assert convert("du/", font="preeti") == "मगर"


def test_nayanepal_gorkhapatra_anchors():
    # Real Gorkhapatra masthead spans (legacy bytes incl. control chars + ƒ extension).
    assert "गोरखापत्र" in convert("uf]\x03ƒvfkqåfƒf", font="nayanepal")
    assert convert("k|sflzt", font="nayanepal") == "प्रकाशित"
    # ƒ -> र extension specifically (would be गोƒखापत्र without it).
    assert "ƒ" not in convert("uf]\x03ƒvfkqåfƒf", font="nayanepal")


def test_nayanepal_output_is_clean_devanagari():
    res = convert_devanagari("clgn a'9fduƒ,", font="nayanepal")
    assert res.clean
    assert res.unicode_text.startswith("अनिल")


def test_strict_mode_surfaces_leftovers():
    # An unmapped byte (á / U+00E1) should raise in strict mode rather than pass silently.
    with pytest.raises(ValueError):
        convert_devanagari("áá", font="preeti", strict=True)
    # ... and be reported (not dropped) in lenient mode.
    res = convert_devanagari("áá", font="preeti")
    assert not res.clean and "á" in res.leftover


def test_unknown_font_raises():
    with pytest.raises(ValueError):
        convert("abc", font="not-a-font")


def test_supported_fonts_listed():
    fonts = supported_devanagari_fonts()
    assert "nayanepal" in fonts and "preeti" in fonts
