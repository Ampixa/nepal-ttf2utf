"""Limbu/Sirijonga (Namdhinggo legacy) conversion tests."""

import pytest

from nepal_ttf2utf import convert, convert_limbu
from nepal_ttf2utf.limbu import LimbuConverter


def _has_limbu(s: str) -> bool:
    return any(0x1900 <= ord(c) <= 0x194F for c in s)


def test_namdhinggo_legacy_produces_unicode_limbu():
    # Real Gorkhapatra Limbu/Sirijonga legacy span bytes.
    out = convert_limbu("kfMG g' ;fK;SF[ yf]af]cf")
    assert _has_limbu(out)
    # output is NFC-normalized
    import unicodedata

    assert out == unicodedata.normalize("NFC", out)


def test_convert_dispatches_to_limbu():
    assert _has_limbu(convert("kfMG g'", font="namdhinggo"))
    assert _has_limbu(convert("kfMG g'", font="sirijonga"))


def test_converter_loads_default_map():
    conv = LimbuConverter.default()
    res = conv.convert("kfMG")
    assert res.limbu_char_count >= 1
    assert isinstance(res.unmapped_codepoints, list)


def test_limbu_structural_whitespace_is_not_reported_as_unmapped():
    res = LimbuConverter.default().convert("k\t\r\n")
    assert res.unicode_text == "ᤐ\t\r\n"
    assert res.unmapped_codepoints == []


def test_limbu_unmapped_ascii_is_surfaced_in_strict_mode():
    # The upstream map explicitly leaves '#' unresolved.
    res = LimbuConverter.default().convert("#")
    assert "U+0023" in res.unmapped_codepoints
    with pytest.raises(ValueError):
        convert_limbu("#", strict=True)
    with pytest.raises(ValueError):
        convert("#", font="namdhinggo", strict=True)
