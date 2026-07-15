"""Canonical-new and Sikkim Herald legacy Kirat Rai conversion tests.

Anchors are the round-trip-verified cases from the source derivation: SIL's TECkit
``kiratraifontnew.map`` byte-class table + its explicit multi-byte ligature rules.
"""

import hashlib
import json
import unicodedata
from collections import Counter
from importlib import resources
from itertools import product

import pytest

import nepal_ttf2utf.kiratrai as kiratrai_module
from nepal_ttf2utf import convert, convert_kiratrai, convert_kiratrai_herald
from nepal_ttf2utf._controls import DIAGNOSTIC_C0
from nepal_ttf2utf.kiratrai import (
    KIRATRAI_HERALD_BLANKS,
    KIRATRAI_HERALD_PASSTHROUGH,
    KIRATRAI_HERALD_PREMAP,
    KiratRaiConverter,
    KiratRaiHeraldConverter,
)


def _has_kiratrai(s: str) -> bool:
    return any(0x16D40 <= ord(c) <= 0x16D7F for c in s)


def _herald_contract_payload(converter: KiratRaiHeraldConverter) -> bytes:
    return json.dumps(
        {
            "blanks": sorted(ord(source) for source in converter._blanks),
            "passthrough": sorted(ord(source) for source in converter._passthrough),
            "premap": [
                [ord(source), ord(target)] for source, target in sorted(converter._premap.items())
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _herald_projection(source: str, converter: KiratRaiHeraldConverter) -> str:
    return "".join(
        converter._premap.get(char, " " if char in converter._blanks else char) for char in source
    )


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
    assert isinstance(converter._rules, tuple)
    functional_payload = json.dumps(
        [[list(source), list(target)] for source, target in sorted(converter._rules)],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(functional_payload) == 1592
    assert hashlib.sha256(functional_payload).hexdigest() == (
        "d83310902ddacc1a04ed11c10d8b8f5ebf3af374745ca2f3c23fe9f1c49c0a8a"
    )


def test_kiratrai_herald_routing_and_effective_output_contracts_are_pinned():
    converter = KiratRaiHeraldConverter.default()
    assert len(converter._premap) == len(KIRATRAI_HERALD_PREMAP) == 38
    assert len(converter._passthrough) == len(KIRATRAI_HERALD_PASSTHROUGH) == 21
    assert len(converter._blanks) == len(KIRATRAI_HERALD_BLANKS) == 2
    assert len(set(converter._premap.values())) == 38
    assert not set(converter._premap) & converter._passthrough
    assert not set(converter._premap) & converter._blanks
    assert not converter._passthrough & converter._blanks

    premap_payload = json.dumps(
        [[ord(source), ord(target)] for source, target in sorted(converter._premap.items())],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(premap_payload) == 349
    assert hashlib.sha256(premap_payload).hexdigest() == (
        "49625e55234be5d752424ccf7ce9f3b2e1514d80d5268ab84cf7f42a42623f60"
    )

    payload = _herald_contract_payload(converter)
    assert len(payload) == 455
    assert hashlib.sha256(payload).hexdigest() == (
        "096ab0ff7d78d25eb529af2041b11510e60f958e749b1cd92c11fa3a313ce14d"
    )

    effective_payload = json.dumps(
        [
            [ord(source), [ord(char) for char in converter.convert(source).unicode_text]]
            for source in sorted(converter._premap)
        ],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(effective_payload) == 518
    assert hashlib.sha256(effective_payload).hexdigest() == (
        "6c176c661b8af8a73f38d16a44f477edeee8ec9bfd987d9457ecedb5f2318eb8"
    )


def _invalid_herald_contract(case: str):
    premap = dict(KIRATRAI_HERALD_PREMAP)
    passthrough = set(KIRATRAI_HERALD_PASSTHROUGH)
    blanks = set(KIRATRAI_HERALD_BLANKS)
    if case == "premap-count":
        premap.pop("D")
    elif case == "passthrough-count":
        passthrough.remove(";")
    elif case == "blank-count":
        blanks.remove("Z")
    elif case == "source-type":
        premap[68] = premap.pop("D")
    elif case == "source-length":
        premap["DD"] = premap.pop("D")
    elif case == "target-length":
        premap["D"] = "qq"
    elif case == "target-domain":
        premap["D"] = "\u2603"
    elif case == "duplicate-target":
        premap["D"] = premap["F"]
    elif case == "overlap":
        passthrough.remove(";")
        passthrough.add("D")
    elif case == "unsupported-target":
        premap["f"] = "f"
    elif case == "unclean-forward":
        passthrough.remove(";")
        passthrough.add("~")
    else:  # pragma: no cover - test helper contract
        raise AssertionError(case)
    return premap, frozenset(passthrough), frozenset(blanks)


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("premap-count", "exactly 38"),
        ("passthrough-count", "exactly 21"),
        ("blank-count", "exactly two"),
        ("source-type", "invalid Kirat Rai Herald premap entry"),
        ("source-length", "invalid Kirat Rai Herald premap entry"),
        ("target-length", "invalid Kirat Rai Herald premap entry"),
        ("target-domain", "invalid Kirat Rai Herald premap entry"),
        ("duplicate-target", "targets must be one-to-one"),
        ("overlap", "routing sources overlap"),
        ("unsupported-target", "unsupported Kirat Rai Herald canonical target"),
        ("unclean-forward", "unclean Kirat Rai Herald canonical projection"),
    ],
)
def test_kiratrai_herald_contract_validation_fails_closed(monkeypatch, case, message):
    premap, passthrough, blanks = _invalid_herald_contract(case)
    monkeypatch.setattr(kiratrai_module, "KIRATRAI_HERALD_PREMAP", premap)
    monkeypatch.setattr(kiratrai_module, "KIRATRAI_HERALD_PASSTHROUGH", passthrough)
    monkeypatch.setattr(kiratrai_module, "KIRATRAI_HERALD_BLANKS", blanks)

    with pytest.raises(ValueError, match=message):
        kiratrai_module._freeze_herald_contract()


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
        ("\U00016d63\U00016d68", "\U00016d6a"),
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
    ("converter", "source", "expected"),
    [
        (convert_kiratrai, "e\U00016d67", "\U00016d68"),
        (convert_kiratrai_herald, "r\U00016d67", "\U00016d68"),
        (convert_kiratrai, "A\U00016d68", "\U00016d6a"),
        (convert_kiratrai_herald, "b\U00016d68", "\U00016d6a"),
    ],
)
def test_kiratrai_unicode16_nfc_composes_across_legacy_unicode_boundary(
    converter, source, expected, monkeypatch
):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )

    result = converter(source, strict=True)

    assert result.unicode_text == expected
    assert result.kiratrai_char_count == 1
    assert result.replacement_count == 1
    assert result.unmapped_codepoints == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("\U00016d67\U00016d67", "\U00016d68"),
        ("\U00016d63\U00016d68", "\U00016d6a"),
    ],
)
def test_kiratrai_dispatchers_use_version_stable_unicode16_nfc(source, expected, monkeypatch):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )
    assert convert(source, font="kiratraifontnew", strict=True) == expected
    assert convert(source, font="kiratraifont", strict=True) == expected


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


def test_every_byte_has_an_exact_kiratrai_herald_classification():
    converter = KiratRaiHeraldConverter.default()
    categories: Counter[str] = Counter()
    outcomes: Counter[str] = Counter()

    for codepoint in range(0x100):
        source = chr(codepoint)
        result = converter.convert(source)
        if source in converter._premap:
            category = "premap"
            expected = converter._canonical.convert(converter._premap[source])
        elif source in converter._passthrough:
            category = "passthrough"
            expected = converter._canonical.convert(source)
        elif source in converter._blanks:
            category = "blank"
            expected = converter._canonical.convert(" ")
        else:
            category = "diagnosed"
            assert result.unicode_text == source
            assert result.kiratrai_char_count == 0
            assert result.replacement_count == 0
            assert result.unmapped_codepoints == [f"U+{codepoint:04X}"]
            with pytest.raises(ValueError, match=f"U\\+{codepoint:04X}"):
                convert_kiratrai_herald(source, strict=True)
            categories[category] += 1
            outcomes[category] += 1
            continue

        assert result.unicode_text == expected.unicode_text, f"U+{codepoint:04X}"
        assert result.kiratrai_char_count == expected.kiratrai_char_count
        assert result.replacement_count == expected.replacement_count == 1
        assert result.unmapped_codepoints == expected.unmapped_codepoints == []
        assert convert_kiratrai_herald(source, strict=True) == result
        categories[category] += 1
        if category == "blank":
            outcomes["blank-to-space"] += 1
        elif result.kiratrai_char_count:
            outcomes["assigned-kiratrai"] += 1
        else:
            outcomes["clean-literal"] += 1

    assert categories == {
        "premap": 38,
        "passthrough": 21,
        "blank": 2,
        "diagnosed": 195,
    }
    assert outcomes == {
        "assigned-kiratrai": 49,
        "clean-literal": 10,
        "blank-to-space": 2,
        "diagnosed": 195,
    }


def test_every_supported_herald_pair_and_premap_triple_preserves_projection_state():
    converter = KiratRaiHeraldConverter.default()
    supported = sorted(set(converter._premap) | converter._passthrough | converter._blanks)
    isolated = {source: converter.convert(source).unicode_text for source in supported}
    pair_interactions = 0
    for parts in product(supported, repeat=2):
        source = "".join(parts)
        result = converter.convert(source)
        expected = converter._canonical.convert(_herald_projection(source, converter))
        assert result.unicode_text == expected.unicode_text, repr(source)
        assert result.kiratrai_char_count == expected.kiratrai_char_count, repr(source)
        assert result.replacement_count == expected.replacement_count, repr(source)
        assert result.unmapped_codepoints == expected.unmapped_codepoints == [], repr(source)
        pair_interactions += result.unicode_text != "".join(isolated[part] for part in parts)

    premap_sources = sorted(converter._premap)
    triple_interactions = 0
    for parts in product(premap_sources, repeat=3):
        source = "".join(parts)
        result = converter.convert(source)
        expected = converter._canonical.convert(_herald_projection(source, converter))
        assert result.unicode_text == expected.unicode_text, repr(source)
        assert result.kiratrai_char_count == expected.kiratrai_char_count, repr(source)
        assert result.replacement_count == expected.replacement_count, repr(source)
        assert result.unmapped_codepoints == expected.unmapped_codepoints == [], repr(source)
        triple_interactions += result.unicode_text != "".join(isolated[part] for part in parts)

    assert pair_interactions == 3
    assert triple_interactions == 150


def test_kiratrai_herald_public_contract_and_private_snapshots_are_immutable(monkeypatch):
    canonical = KiratRaiConverter.default()
    converter = KiratRaiHeraldConverter(canonical)
    expected = converter.convert("a?Z0")

    with pytest.raises(TypeError):
        KIRATRAI_HERALD_PREMAP["a"] = "?"
    with pytest.raises(AttributeError):
        KIRATRAI_HERALD_PASSTHROUGH.add("?")
    with pytest.raises(AttributeError):
        KIRATRAI_HERALD_BLANKS.add("?")
    with pytest.raises(TypeError):
        converter._premap["a"] = "?"
    with pytest.raises(AttributeError):
        canonical._rules.clear()

    monkeypatch.setattr(kiratrai_module, "KIRATRAI_HERALD_PREMAP", {"?": "k"})
    monkeypatch.setattr(kiratrai_module, "KIRATRAI_HERALD_PASSTHROUGH", frozenset("?"))
    monkeypatch.setattr(kiratrai_module, "KIRATRAI_HERALD_BLANKS", frozenset("?"))
    canonical._rules = (((ord("?"),), (0x16D43,)),)

    assert converter.convert("a?Z0") == expected
    assert KiratRaiHeraldConverter.default().convert("a?Z0") == expected
    assert convert_kiratrai_herald("a?Z0") == expected


def test_kiratrai_herald_constructor_snapshots_custom_canonical_rules():
    canonical = KiratRaiConverter([((ord("k"),), (0x16D43,))])
    converter = KiratRaiHeraldConverter(canonical)
    canonical._rules = (((ord("k"),), (0x16D44,)),)

    assert converter.convert("a").unicode_text == chr(0x16D43)
    with pytest.raises(ValueError, match="requires a KiratRaiConverter"):
        KiratRaiHeraldConverter(object())


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


@pytest.mark.parametrize("font", ["kiratrai-herald", "kiratraifont", "sikkimherald-kiratrai"])
def test_every_herald_alias_uses_the_frozen_routing_contract(font):
    assert convert("fZ0", font=font, strict=True) == "".join((chr(0x16D48), " ", chr(0x16D70)))
