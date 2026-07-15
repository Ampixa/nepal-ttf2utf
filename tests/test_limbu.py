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
    assert res.replacement_count == 4
    assert res.unmapped_codepoints == []


def test_custom_limbu_rules_preserve_unmatched_structural_whitespace_cleanly():
    converter = LimbuConverter([((0x30,), (0x1946,))])
    result = converter.convert("\t\r\n")
    assert result.unicode_text == "\t\r\n"
    assert result.replacement_count == 0
    assert result.unmapped_codepoints == []


def test_limbu_multibyte_rules_take_precedence_and_count_per_rule():
    result = LimbuConverter.default().convert("f]f}H")
    assert result.unicode_text == "ᤥᤦᤪᤢ"
    assert result.replacement_count == 3
    assert result.unmapped_codepoints == []

    kemphreng_result = LimbuConverter.default().convert("LJ")
    assert kemphreng_result.unicode_text == "ᤫᤡ᤺"
    assert kemphreng_result.replacement_count == 2
    assert kemphreng_result.unmapped_codepoints == []


def test_limbu_byte_and_unicode_classes_expand_positionally_in_byte_pass(tmp_path):
    map_path = tmp_path / "class.map"
    map_path.write_text(
        """Pass(Byte_Unicode)
ByteClass [bytes] = (0x30 0x31..0x32)
UniClass [digits] = (U+1946 U+1947 .. U+1948)
[bytes] <> [digits]
Pass(Unicode)
ByteClass [ignored_bytes] = (0x41)
UniClass [ignored_chars] = (U+1901)
[ignored_bytes] <> [ignored_chars]
""",
        encoding="utf-8",
    )

    converter = LimbuConverter.from_map_file(map_path)
    result = converter.convert("012A")
    assert result.unicode_text == "᥆᥇᥈A"
    assert result.replacement_count == 3
    assert result.unmapped_codepoints == ["U+0041"]


@pytest.mark.parametrize(
    ("map_text", "message"),
    [
        (
            "Pass(Byte_Unicode)\nUniClass [chars] = (U+1946)\n[missing] <> [chars]\n",
            "unknown byte class",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [bytes] = (0x30)\n[bytes] <> [missing]\n",
            "unknown Unicode class",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [bytes] = (0xGG)\n",
            "unparseable byte token",
        ),
        (
            "Pass(Byte_Unicode)\nUniClass [chars] = (U+ZZZZ)\n",
            "unparseable Unicode token",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [bytes] = (0x30 0x31)\n"
            "UniClass [chars] = (U+1946)\n[bytes] <> [chars]\n",
            "length mismatch",
        ),
    ],
)
def test_limbu_class_parser_rejects_invalid_definitions(tmp_path, map_text, message):
    map_path = tmp_path / "invalid.map"
    map_path.write_text(map_text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        LimbuConverter.from_map_file(map_path)


def test_limbu_unmapped_ascii_is_surfaced_in_strict_mode():
    # The upstream map explicitly leaves '#' unresolved.
    res = LimbuConverter.default().convert("#")
    assert res.unicode_text == "#"
    assert res.replacement_count == 0
    assert "U+0023" in res.unmapped_codepoints
    with pytest.raises(ValueError):
        convert_limbu("#", strict=True)
    with pytest.raises(ValueError):
        convert("#", font="namdhinggo", strict=True)
