"""Limbu/Sirijonga (Namdhinggo legacy) conversion tests."""

import hashlib
import json
import unicodedata
from collections import Counter
from importlib import resources

import pytest

from nepal_ttf2utf import convert, convert_limbu
from nepal_ttf2utf._controls import DIAGNOSTIC_C0
from nepal_ttf2utf.limbu import LimbuConverter


def _has_limbu(s: str) -> bool:
    return any(0x1900 <= ord(c) <= 0x194F for c in s)


def test_limbu_map_matches_the_pinned_sil_source_and_parser_inventory():
    map_resource = resources.files("nepal_ttf2utf.maps") / "Limbu.map"
    map_bytes = map_resource.read_bytes()
    assert len(map_bytes) == 5981
    assert hashlib.sha256(map_bytes).hexdigest() == (
        "2e9f6b8205a7facc0732f54c3dd4cc64f8344c7767acdbc12dd3c11cfb535f58"
    )
    lines = map_bytes.decode("utf-8-sig").splitlines()
    assert len(lines) == 146
    assert sum(line.strip().startswith("ByteClass") for line in lines) == 1
    assert sum(line.strip().startswith("UniClass") for line in lines) == 3

    in_byte_pass = False
    active_lines = []
    for raw_line in lines:
        line = raw_line.split(";", 1)[0].strip()
        if line.casefold() == "pass(byte_unicode)":
            in_byte_pass = True
            continue
        if line.casefold() == "pass(unicode)":
            in_byte_pass = False
            continue
        if in_byte_pass and line:
            active_lines.append(line)
    assert sum(line.startswith("0x") for line in active_lines) == 99

    converter = LimbuConverter.default()
    assert len(converter._rules) == 131
    assert len({source for source, _target in converter._rules}) == 131
    assert Counter(len(source) for source, _target in converter._rules) == {1: 129, 2: 2}
    assert Counter(len(target) for _source, target in converter._rules) == {1: 129, 2: 2}

    functional_payload = json.dumps(
        [[list(source), list(target)] for source, target in sorted(converter._rules)],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(functional_payload) == 1741
    assert hashlib.sha256(functional_payload).hexdigest() == (
        "31c47c252d2c82e9ab0d05619e80e1e0d1897a2b55f581edf8f987897e97956e"
    )


def test_every_limbu_source_rule_has_exact_output_and_counts():
    converter = LimbuConverter.default()
    for source, target in converter._rules:
        source_text = "".join(chr(value) for value in source)
        # Legacy H is the sole individual source whose raw target needs the
        # map's vowel/subjoined logical-order repair. The LJ cross-rule form is
        # pinned independently in test_limbu_multibyte_rules_take_precedence_and_count_per_rule.
        expected_target = (0x192A, 0x1922) if source == (0x48,) else target
        expected = unicodedata.normalize("NFC", "".join(chr(value) for value in expected_target))
        result = converter.convert(source_text)
        label = " ".join(f"0x{value:02X}" for value in source)

        assert result.unicode_text == expected, label
        assert result.replacement_count == 1, label
        assert result.limbu_char_count == sum(0x1900 <= ord(char) <= 0x194F for char in expected), (
            label
        )
        assert result.unmapped_codepoints == sorted(
            f"U+{ord(char):04X}" for char in set(expected) & DIAGNOSTIC_C0
        ), label


@pytest.mark.parametrize(
    ("map_text", "message"),
    [
        (
            "Pass(Byte_Unicode) trailing\n0x41 > U+1901\n",
            "invalid Limbu pass declaration",
        ),
        ("Pass (Byte_Unicode)\n0x41 > U+1901\n", "invalid Limbu pass declaration"),
        (
            "Pass(Byte_Unicode)\nByteDefault 0x15E\n0x41 > U+1901\n",
            "invalid Limbu default declaration",
        ),
        (
            "Pass(Byte_Unicode)\nUniDefault U+FFFD\n0x41 > U+1901\n",
            "invalid Limbu default declaration",
        ),
        (
            "Pass(Byte_Unicode)\nPass(Byte_Unicode)\n0x41 > U+1901\n",
            "duplicate Limbu pass declaration",
        ),
        (
            "Pass(Byte_Unicode)\nByteDefault 0x5E\nByteDefault 0x5F\n0x41 > U+1901\n",
            "duplicate Limbu default declaration",
        ),
        (
            "Pass(Byte_Unicode)\nUniDefault replacement_character\n"
            "UniDefault replacement_character\n0x41 > U+1901\n",
            "duplicate Limbu default declaration",
        ),
        ("Pass(Byte_Unicode)\nByteClass [b] = (41)\n", "unparseable byte token"),
        ("Pass(Byte_Unicode)\nByteClass [b] = (0x141)\n", "unparseable byte token"),
        (
            "Pass(Byte_Unicode)\nByteClass [b] = (0x41 .. 42)\n",
            "invalid byte range",
        ),
        (
            "Pass(Byte_Unicode)\nUniClass [u] = (U+1901junk)\n",
            "unparseable Unicode token",
        ),
        ("Pass(Byte_Unicode)\nUniClass [u] = (U+110000)\n", "invalid Unicode scalar"),
        ("Pass(Byte_Unicode)\nUniClass [u] = (U+D800)\n", "invalid Unicode scalar"),
        (
            "Pass(Byte_Unicode)\nUniClass [u] = (U+D7FF .. U+E000)\n",
            "invalid Unicode scalar range",
        ),
        ("Pass(Byte_Unicode)\nByteClass [b] = ()\n", "empty byte class"),
        ("Pass(Byte_Unicode)\nUniClass [u] = ()\n", "empty Unicode class"),
        (
            "Pass(Byte_Unicode)\nByteClass [ ] = (0x41)\n",
            "empty Limbu byte class name",
        ),
        (
            "Pass(Byte_Unicode)\nUniClass [ ] = (U+1901)\n",
            "empty Limbu Unicode class name",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [b] = (0x41)\nUniClass [u] = (U+1901)\n[ ] > [u]\n",
            "empty Limbu class reference",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [b] = (0x41)\nUniClass [u] = (U+1901)\n[b] > [ ]\n",
            "empty Limbu class reference",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [b] = (0x41)\nByteClass [b] = (0x42)\n",
            "duplicate Limbu byte class",
        ),
        (
            "Pass(Byte_Unicode)\nUniClass [u] = (U+1901)\nUniClass [u] = (U+1902)\n",
            "duplicate Limbu Unicode class",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 0xGG > U+1901 trailing-garbage\n",
            "invalid explicit Limbu rule",
        ),
        ("Pass(Byte_Unicode)\n0x41 >\n", "invalid explicit Limbu rule"),
        ("Pass(Byte_Unicode)\n> U+1901\n", "invalid explicit Limbu rule"),
        ("Pass(Byte_Unicode)\n0x41 U+1901\n", "invalid explicit Limbu rule"),
        ("Pass(Byte_Unicode)\n0x41 > > U+1901\n", "invalid explicit Limbu rule"),
        ("Pass(Byte_Unicode)\nunsupported syntax\n", "invalid explicit Limbu rule"),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1901\n0x41 > U+1902\n",
            "duplicate Limbu source rule",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [b] = (0x41)\n"
            "UniClass [u] = (U+1901)\n[b] > [u]\n0x41 > U+1902\n",
            "duplicate Limbu source rule",
        ),
    ],
)
def test_limbu_parser_rejects_malformed_or_ambiguous_maps(tmp_path, map_text, message):
    map_path = tmp_path / "invalid.map"
    map_path.write_text(map_text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        LimbuConverter.from_map_file(map_path)


def test_limbu_parser_accepts_exact_defaults_and_forward_rules(tmp_path):
    map_path = tmp_path / "valid.map"
    map_path.write_text(
        "Pass(Byte_Unicode)\nByteDefault 0x5E\nUniDefault replacement_character\n"
        "ByteClass [b] = (0x41)\nUniClass [u] = (U+1901)\n"
        "[b] > [u]\n0x42 <> U+1902\nPass(Unicode)\nunsupported reverse syntax\n",
        encoding="utf-8",
    )
    converter = LimbuConverter.from_map_file(map_path)
    assert converter.convert("AB").unicode_text == "ᤁᤂ"


@pytest.mark.parametrize(
    "rules",
    [
        [((True,), (0x1901,))],
        [((0x41,), (True,))],
        [((0x100,), (0x1901,))],
        [((0x41,), ())],
        [((), (0x1901,))],
        [((0x41,), (0x110000,))],
        [((0x41,), (0xD800,))],
        [((0x41,), (0x1901,)), ((0x41,), (0x1902,))],
    ],
)
def test_limbu_constructor_rejects_invalid_or_ambiguous_rules(rules):
    with pytest.raises(ValueError):
        LimbuConverter(rules)


def test_limbu_constructor_freezes_mutable_rule_sequences():
    source = [0x41]
    target = [0x1901]
    converter = LimbuConverter([(source, target)])

    source[0] = 0x42
    target[0] = 0x110000

    assert converter.convert("A").unicode_text == "ᤁ"


def test_limbu_constructor_consumes_one_shot_rules_once():
    rules = iter([((0x41,), (0x1901,))])
    converter = LimbuConverter(rules)

    assert converter.convert("A").unicode_text == "ᤁ"


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
