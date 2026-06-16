"""Limbu/Sirijonga (Namdhinggo legacy) conversion tests."""

from lipantar import convert, convert_limbu
from lipantar.limbu import LimbuConverter


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
