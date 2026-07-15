"""Canonical-new and Sikkim Herald legacy Kirat Rai conversion tests.

Anchors are the round-trip-verified cases from the source derivation: SIL's TECkit
``kiratraifontnew.map`` byte-class table + its explicit multi-byte ligature rules.
"""

import hashlib
import json
import unicodedata
from collections import Counter
from importlib import resources

import pytest

from nepal_ttf2utf import convert, convert_kiratrai, convert_kiratrai_herald
from nepal_ttf2utf._controls import DIAGNOSTIC_C0
from nepal_ttf2utf.kiratrai import KIRATRAI_HERALD_PREMAP, KiratRaiConverter


def _has_kiratrai(s: str) -> bool:
    return any(0x16D40 <= ord(c) <= 0x16D7F for c in s)


def test_kiratrai_map_matches_the_pinned_sil_source_and_parser_inventory():
    map_resource = resources.files("nepal_ttf2utf.maps") / "kiratraifontnew.map"
    map_bytes = map_resource.read_bytes()
    assert len(map_bytes) == 2158
    assert hashlib.sha256(map_bytes).hexdigest() == (
        "1750a51d4c40156ed49a57105d5d83905f263b7c084b7d7539ab7055a931a3c4"
    )

    lines = map_bytes.decode("utf-8-sig").splitlines()
    assert len(lines) == 59
    assert sum(line.strip().startswith("ByteClass") for line in lines) == 8
    assert sum(line.strip().startswith("UniClass") for line in lines) == 8

    converter = KiratRaiConverter.default()
    assert len(converter._rules) == 115
    assert len({source for source, _target in converter._rules}) == 115
    assert Counter(len(source) for source, _target in converter._rules) == {
        1: 110,
        2: 4,
        3: 1,
    }
    functional_payload = json.dumps(
        [[list(source), list(target)] for source, target in sorted(converter._rules)],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(functional_payload) == 1592
    assert hashlib.sha256(functional_payload).hexdigest() == (
        "d83310902ddacc1a04ed11c10d8b8f5ebf3af374745ca2f3c23fe9f1c49c0a8a"
    )


def test_every_kiratrai_source_rule_has_exact_output_and_counts():
    converter = KiratRaiConverter.default()
    for source, target in converter._rules:
        source_text = "".join(chr(value) for value in source)
        expected = unicodedata.normalize("NFC", "".join(chr(value) for value in target))
        result = converter.convert(source_text)
        label = " ".join(f"0x{value:02X}" for value in source)

        assert result.unicode_text == expected, label
        assert result.replacement_count == 1, label
        assert result.kiratrai_char_count == sum(
            0x16D40 <= ord(char) <= 0x16D7F for char in expected
        ), label
        assert result.unmapped_codepoints == sorted(
            f"U+{ord(char):04X}" for char in set(expected) & DIAGNOSTIC_C0
        ), label


@pytest.mark.parametrize(
    ("map_text", "message"),
    [
        (
            "Pass(Byte_Unicode) trailing\n0x41 > U+16D43\n",
            "invalid Kirat Rai pass declaration",
        ),
        ("Pass (Byte_Unicode)\n0x41 > U+16D43\n", "invalid Kirat Rai pass declaration"),
        ("Pass(Byte_Unicode)\nByteClass [b] = (41)\n", "unparseable byte token"),
        ("Pass(Byte_Unicode)\nByteClass [b] = (0x141)\n", "unparseable byte token"),
        (
            "Pass(Byte_Unicode)\nUniClass [u] = (U+16D43junk)\n",
            "unparseable unicode token",
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
            "empty Kirat Rai byte class name",
        ),
        (
            "Pass(Byte_Unicode)\nUniClass [ ] = (U+16D43)\n",
            "empty Kirat Rai Unicode class name",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [b] = (0x41)\nUniClass [u] = (U+16D43)\n[ ] > [u]\n",
            "empty Kirat Rai class reference",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [b] = (0x41)\nUniClass [u] = (U+16D43)\n[b] > [ ]\n",
            "empty Kirat Rai class reference",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [b] = (0x41)\nByteClass [b] = (0x42)\n",
            "duplicate Kirat Rai byte class",
        ),
        (
            "Pass(Byte_Unicode)\nUniClass [u] = (U+16D43)\nUniClass [u] = (U+16D44)\n",
            "duplicate Kirat Rai Unicode class",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 0xGG > U+16D43 trailing-garbage\n",
            "invalid explicit Kirat Rai rule",
        ),
        ("Pass(Byte_Unicode)\n0x41 >\n", "invalid explicit Kirat Rai rule"),
        ("Pass(Byte_Unicode)\n> U+16D43\n", "invalid explicit Kirat Rai rule"),
        ("Pass(Byte_Unicode)\n0x41 U+16D43\n", "invalid explicit Kirat Rai rule"),
        ("Pass(Byte_Unicode)\n0x41 > > U+16D43\n", "invalid explicit Kirat Rai rule"),
        ("Pass(Byte_Unicode)\nunsupported syntax\n", "invalid explicit Kirat Rai rule"),
        (
            "Pass(Byte_Unicode)\n0x41 > U+16D43\n0x41 > U+16D44\n",
            "duplicate Kirat Rai source rule",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [b] = (0x41)\n"
            "UniClass [u] = (U+16D43)\n[b] > [u]\n0x41 > U+16D44\n",
            "duplicate Kirat Rai source rule",
        ),
    ],
)
def test_kiratrai_parser_rejects_malformed_or_ambiguous_maps(tmp_path, map_text, message):
    map_path = tmp_path / "invalid.map"
    map_path.write_text(map_text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        KiratRaiConverter.from_map_file(map_path)


def test_kiratrai_parser_accepts_an_exact_custom_map(tmp_path):
    map_path = tmp_path / "valid.map"
    map_path.write_text(
        "Pass(Byte_Unicode)\nByteClass [b] = (0x41)\n"
        "UniClass [u] = (U+16D43)\n[b] > [u]\n0x42 > U+16D44\n"
        "Pass(Unicode)\n",
        encoding="utf-8",
    )
    converter = KiratRaiConverter.from_map_file(map_path)
    assert converter.convert("AB").unicode_text == "\U00016d43\U00016d44"


@pytest.mark.parametrize(
    "rules",
    [
        [((True,), (0x16D43,))],
        [((0x41,), (True,))],
        [((0x41,), ())],
        [((), (0x16D43,))],
        [((0x41,), (0x110000,))],
    ],
)
def test_kiratrai_constructor_rejects_invalid_rules(rules):
    with pytest.raises(ValueError):
        KiratRaiConverter(rules)


def test_kiratrai_constructor_freezes_mutable_rule_sequences():
    source = [0x41]
    target = [0x16D43]
    converter = KiratRaiConverter([(source, target)])

    source[0] = 0x42
    target[0] = 0x110000

    assert converter.convert("A").unicode_text == "\U00016d43"


def test_kiratrai_constructor_consumes_one_shot_rules_once():
    rules = iter([((0x41,), (0x16D43,))])
    converter = KiratRaiConverter(rules)

    assert converter.convert("A").unicode_text == "\U00016d43"


def test_kiratrai_byte_classes_map_positionally():
    conv = KiratRaiConverter.default()
    # cons1 byte class -> U+16D43..; 'a' (0x61) is position 0 -> U+16D43 LETTER A.
    assert conv.convert("a").unicode_text == "\U00016d43"
    # 'k' (0x6b) is position 1 in cons1 -> U+16D44 LETTER KA.
    assert conv.convert("k").unicode_text == "\U00016d44"
    # digits map 0x30..0x39 -> U+16D70..U+16D79.
    assert conv.convert("0").unicode_text == "\U00016d70"
    assert conv.convert("9").unicode_text == "\U00016d79"


def test_kiratrai_multibyte_ligature_rules_take_precedence():
    conv = KiratRaiConverter.default()
    # '//' (0x2f 0x2f) -> U+16D6F DOUBLE DANDA wins over single '/' -> U+16D6E DANDA.
    assert conv.convert("//").unicode_text == "\U00016d6f"
    # 'ee' (0x65 0x65) -> U+16D68 VOWEL SIGN AI.
    assert conv.convert("ee").unicode_text == "\U00016d68"


def test_kiratrai_mapped_bytes_are_in_block_and_nfc():
    res = convert_kiratrai("ebr kueuqb")
    non_ascii = [c for c in res.unicode_text if ord(c) > 0x7F]
    assert non_ascii, "expected Kirat Rai output"
    assert all(0x16D40 <= ord(c) <= 0x16D7F for c in non_ascii)
    assert res.kiratrai_char_count == len(non_ascii)
    assert res.unicode_text == unicodedata.normalize("NFC", res.unicode_text)


@pytest.mark.parametrize("converter", [convert_kiratrai, convert_kiratrai_herald])
@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("\U00016d67\U00016d67", "\U00016d68"),
        ("\U00016d63\U00016d67", "\U00016d69"),
        ("\U00016d69\U00016d67", "\U00016d6a"),
        ("\U00016d63\U00016d67\U00016d67", "\U00016d6a"),
    ],
)
def test_kiratrai_unicode16_nfc_is_version_stable(converter, source, expected, monkeypatch):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )

    result = converter(source, strict=True)

    assert result.unicode_text == expected
    assert result.kiratrai_char_count == 1
    assert result.replacement_count == 0
    assert result.unmapped_codepoints == []


@pytest.mark.parametrize(
    ("converter", "source"),
    [
        (convert_kiratrai, "e\U00016d67"),
        (convert_kiratrai_herald, "r\U00016d67"),
    ],
)
def test_kiratrai_unicode16_nfc_composes_across_legacy_unicode_boundary(
    converter, source, monkeypatch
):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )

    result = converter(source, strict=True)

    assert result.unicode_text == "\U00016d68"
    assert result.kiratrai_char_count == 1
    assert result.replacement_count == 1
    assert result.unmapped_codepoints == []


def test_kiratrai_dispatchers_use_version_stable_unicode16_nfc(monkeypatch):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )
    source = "\U00016d67\U00016d67"

    assert convert(source, font="kiratraifontnew", strict=True) == "\U00016d68"
    assert convert(source, font="kiratraifont", strict=True) == "\U00016d68"


def test_convert_dispatches_to_kiratrai():
    assert _has_kiratrai(convert("a", font="kiratrai"))
    assert _has_kiratrai(convert("0", font="kiratrai"))


def test_kiratrai_unmapped_byte_surfaced_not_dropped():
    # Canonical-new byte 'f' is absent from SIL's class table. Herald 'f' belongs
    # to a different layout and is tested separately below.
    res = convert_kiratrai("f")
    assert "U+0066" in res.unmapped_codepoints
    assert "f" in res.unicode_text
    with pytest.raises(ValueError):
        convert_kiratrai("f", strict=True)


def test_kiratrai_genuine_unicode_passes_through():
    text = "\U00016d43"
    res = convert_kiratrai(text, strict=True)
    assert res.unicode_text == text
    assert not res.unmapped_codepoints


def test_herald_full_observed_letter_premap_matches_exact_unicode_targets():
    expected = {
        "D": 0x16D4E,
        "F": 0x16D46,
        "G": 0x16D58,
        "H": 0x16D4B,
        "I": 0x16D51,
        "J": 0x16D4C,
        "K": 0x16D4F,
        "L": 0x16D6D,
        "O": 0x16D41,
        "R": 0x16D50,
        "S": 0x16D47,
        "U": 0x16D40,
        "a": 0x16D44,
        "b": 0x16D63,
        "c": 0x16D55,
        "d": 0x16D45,
        "e": 0x16D5B,
        "f": 0x16D48,
        "g": 0x16D60,
        "h": 0x16D43,
        "i": 0x16D5F,
        "j": 0x16D59,
        "k": 0x16D5D,
        "l": 0x16D64,
        "m": 0x16D49,
        "n": 0x16D57,
        "o": 0x16D56,
        "p": 0x16D52,
        "q": 0x16D54,
        "r": 0x16D67,
        "s": 0x16D4A,
        "t": 0x16D62,
        "u": 0x16D65,
        "v": 0x16D5A,
        "w": 0x16D5E,
        "x": 0x16D53,
        "y": 0x16D5C,
        "z": 0x16D6B,
    }
    assert set(KIRATRAI_HERALD_PREMAP) == set(expected)
    for byte, codepoint in expected.items():
        assert convert_kiratrai_herald(byte, strict=True).unicode_text == chr(codepoint)


def test_herald_corpus_masthead_regression():
    assert convert_kiratrai_herald("udzdle", strict=True).unicode_text == "".join(
        chr(codepoint) for codepoint in (0x16D65, 0x16D45, 0x16D6B, 0x16D45, 0x16D64, 0x16D5B)
    )


def test_herald_premap_preserves_canonical_multibyte_rules():
    assert convert_kiratrai_herald("rr", strict=True).unicode_text == chr(0x16D68)
    assert convert_kiratrai_herald("br", strict=True).unicode_text == chr(0x16D69)
    assert convert_kiratrai_herald("brr", strict=True).unicode_text == chr(0x16D6A)
    assert convert_kiratrai_herald("//", strict=True).unicode_text == chr(0x16D6F)


@pytest.mark.parametrize("blank", ["\\", "Z"])
def test_herald_blank_glyphs_normalize_to_space(blank):
    result = convert_kiratrai_herald(f"a{blank}a", strict=True)
    assert result.unicode_text == chr(0x16D44) + " " + chr(0x16D44)
    assert not result.unmapped_codepoints


def test_canonical_z_remains_kirat_rai_sang():
    assert convert_kiratrai("Z", strict=True).unicode_text == chr(0x16D6C)


def test_convert_dispatches_old_and_new_kiratrai_layouts_separately():
    assert convert("f", font="kiratraifont", strict=True) == chr(0x16D48)
    assert convert("N", font="kiratraifontnew", strict=True) == chr(0x16D48)
