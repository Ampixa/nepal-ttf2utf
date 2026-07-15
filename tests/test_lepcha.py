"""Sikkim Herald live-text Lepcha (Róng) conversion tests.

Anchors are the shape-identity + round-trip-verified cases from the source
derivation, including the pre-base vowel reordering this font requires.
"""

import hashlib
import json
import unicodedata
from collections import Counter
from importlib import resources

import pytest

from nepal_ttf2utf import convert, convert_lepcha
from nepal_ttf2utf.lepcha import LEPCHA_PASSTHROUGH, LepchaConverter


def test_lepcha_map_matches_the_pinned_derived_resource_and_inventory():
    map_resource = resources.files("nepal_ttf2utf.maps") / "sikkim_herald_lepcha.json"
    map_bytes = map_resource.read_bytes()
    assert len(map_bytes) == 2571
    assert len(map_bytes.decode("utf-8").splitlines()) == 79
    assert hashlib.sha256(map_bytes).hexdigest() == (
        "29f55542cf67d230a6bb2f1474f85e6688b0e30e36271251a2f24af2f6d78bb1"
    )

    raw = json.loads(map_bytes)
    assert set(raw) == {"_doc", "_confidence", "_unresolved_bytes", "map"}
    assert isinstance(raw["_doc"], str)
    assert isinstance(raw["_confidence"], str)
    assert len(raw["map"]) == 65
    assert all(len(target) == 1 for target in raw["map"].values())
    target_codepoints = {int(target[0], 16) for target in raw["map"].values()}
    assert len(target_codepoints) == 65
    assert Counter(unicodedata.category(chr(codepoint)) for codepoint in target_codepoints) == {
        "Lo": 36,
        "Mn": 10,
        "Mc": 9,
        "Nd": 10,
    }

    unresolved = {int(value, 16) for value in raw["_unresolved_bytes"]}
    assert unresolved == {0x28, 0x29, 0x2A, 0x2B, 0x2F}
    assert len(raw["_unresolved_bytes"]) == len(unresolved)
    assert unresolved.isdisjoint(int(source, 16) for source in raw["map"])
    assert LEPCHA_PASSTHROUGH == frozenset("-")
    assert ord("-") not in unresolved
    assert f"{ord('-'):02X}" not in raw["map"]

    converter = LepchaConverter.default()
    assert len(converter._byte_map) == 65
    assert len(set(converter._byte_map.values())) == 65
    functional_payload = json.dumps(
        [[source, list(target)] for source, target in sorted(converter._byte_map.items())],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(functional_payload) == 796
    assert hashlib.sha256(functional_payload).hexdigest() == (
        "ae61a37f712694d6e1b8541c0e9854ab3e1d2b8a5ffb4213f231bca86e029d60"
    )


def test_every_lepcha_map_entry_has_exact_isolated_behavior():
    raw = json.loads(
        (resources.files("nepal_ttf2utf.maps") / "sikkim_herald_lepcha.json").read_bytes()
    )
    converter = LepchaConverter.default()
    for source_hex, target_hex in raw["map"].items():
        source = chr(int(source_hex, 16))
        expected = unicodedata.normalize(
            "NFC", "".join(chr(int(value, 16)) for value in target_hex)
        )
        result = converter.convert(source)

        assert result.unicode_text == expected, source_hex
        assert result.lepcha_char_count == len(expected), source_hex
        assert result.replacement_count == 1, source_hex
        assert result.unmapped_bytes == [], source_hex


def test_every_single_byte_has_an_explicit_default_conversion_classification():
    raw = json.loads(
        (resources.files("nepal_ttf2utf.maps") / "sikkim_herald_lepcha.json").read_bytes()
    )
    expected_map = {
        int(source, 16): unicodedata.normalize(
            "NFC", "".join(chr(int(value, 16)) for value in target)
        )
        for source, target in raw["map"].items()
    }
    structural = {0x09, 0x0A, 0x0D, 0x20}
    passthrough = {ord(character) for character in LEPCHA_PASSTHROUGH}
    converter = LepchaConverter.default()

    for source in range(0x100):
        character = chr(source)
        result = converter.convert(character)
        if source in expected_map:
            expected = expected_map[source]
            assert result.unicode_text == expected, f"0x{source:02X}"
            assert result.lepcha_char_count == len(expected), f"0x{source:02X}"
            assert result.replacement_count == 1, f"0x{source:02X}"
            assert result.unmapped_bytes == [], f"0x{source:02X}"
        elif source in structural | passthrough:
            assert result.unicode_text == character, f"0x{source:02X}"
            assert result.lepcha_char_count == 0, f"0x{source:02X}"
            assert result.replacement_count == 0, f"0x{source:02X}"
            assert result.unmapped_bytes == [], f"0x{source:02X}"
        else:
            label = f"0x{source:02X}"
            assert result.unicode_text == character, label
            assert result.lepcha_char_count == 0, label
            assert result.replacement_count == 0, label
            assert result.unmapped_bytes == [label], label
            with pytest.raises(ValueError, match=label):
                convert_lepcha(character, strict=True)


@pytest.mark.parametrize(
    ("map_text", "message"),
    [
        ("{", "invalid JSON in Lepcha legacy map"),
        ("[]", "root must be an object"),
        ('{"_doc": [], "map": {"41": ["1C00"]}}', "metadata must be a string"),
        ('{"unknown": true, "map": {"41": ["1C00"]}}', "unexpected Lepcha legacy map"),
        ("{}", "missing 'map' object"),
        ('{"not_map": {}}', "unexpected Lepcha legacy map"),
        ('{"map": []}', "missing 'map' object"),
        ('{"map": {}}', "requires a non-empty map"),
        (
            '{"map": {"41": ["1C00"], "41": ["1C01"]}}',
            "duplicate JSON key",
        ),
        ('{"map": {"0x41": ["1C00"]}}', "expected two uppercase hex digits"),
        ('{"map": {"041": ["1C00"]}}', "expected two uppercase hex digits"),
        ('{"map": {"4a": ["1C00"]}}', "expected two uppercase hex digits"),
        ('{"map": {" 41 ": ["1C00"]}}', "expected two uppercase hex digits"),
        ('{"map": {"00": ["1C00"]}}', "must not be C0, SPACE, or DEL"),
        ('{"map": {"09": ["1C00"]}}', "must not be C0, SPACE, or DEL"),
        ('{"map": {"20": ["1C00"]}}', "must not be C0, SPACE, or DEL"),
        ('{"map": {"7F": ["1C00"]}}', "must not be C0, SPACE, or DEL"),
        ('{"map": {"2D": ["1C00"]}}', "fixed passthrough"),
        ('{"map": {"41": []}}', "must be a non-empty list"),
        ('{"map": {"41": "1C00"}}', "must be a non-empty list"),
        ('{"map": {"41": {"1C00": 1}}}', "must be a non-empty list"),
        ('{"map": {"41": [7168]}}', "expected four uppercase hex digits"),
        ('{"map": {"41": ["0x1C00"]}}', "expected four uppercase hex digits"),
        ('{"map": {"41": ["1c00"]}}', "expected four uppercase hex digits"),
        ('{"map": {"41": ["1C000"]}}', "expected four uppercase hex digits"),
        ('{"map": {"41": ["0041"]}}', "invalid or unassigned Lepcha target"),
        ('{"map": {"41": ["1C38"]}}', "invalid or unassigned Lepcha target"),
        ('{"map": {"41": ["D800"]}}', "invalid or unassigned Lepcha target"),
        (
            '{"_unresolved_bytes": "42", "map": {"41": ["1C00"]}}',
            "'_unresolved_bytes' must be a list",
        ),
        (
            '{"_unresolved_bytes": ["0x42"], "map": {"41": ["1C00"]}}',
            "invalid unresolved Lepcha byte",
        ),
        (
            '{"_unresolved_bytes": ["4a"], "map": {"41": ["1C00"]}}',
            "invalid unresolved Lepcha byte",
        ),
        (
            '{"_unresolved_bytes": ["42", "42"], "map": {"41": ["1C00"]}}',
            "duplicate unresolved Lepcha byte",
        ),
        (
            '{"_unresolved_bytes": ["41"], "map": {"41": ["1C00"]}}',
            "also marked unresolved",
        ),
        (
            '{"_unresolved_bytes": ["20"], "map": {"41": ["1C00"]}}',
            "must not be C0, SPACE, or DEL",
        ),
        (
            '{"_unresolved_bytes": ["2D"], "map": {"41": ["1C00"]}}',
            "fixed passthrough",
        ),
    ],
)
def test_lepcha_map_parser_rejects_malformed_or_ambiguous_schemas(tmp_path, map_text, message):
    map_path = tmp_path / "invalid.json"
    map_path.write_text(map_text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        LepchaConverter.from_map_file(map_path)


def test_lepcha_map_parser_accepts_an_exact_custom_schema(tmp_path):
    map_path = tmp_path / "valid.json"
    map_path.write_text(
        json.dumps(
            {
                "_doc": "Custom evidenced fixture",
                "_confidence": "Test-only mapping",
                "_unresolved_bytes": ["42"],
                "map": {"41": ["1C00", "1C27"]},
            }
        ),
        encoding="utf-8",
    )
    converter = LepchaConverter.from_map_file(map_path)
    result = converter.convert("AB")
    assert result.unicode_text == "ᰀᰧB"
    assert result.replacement_count == 1
    assert result.unmapped_bytes == ["0x42"]


def test_lepcha_map_parser_rejects_oversized_targets(tmp_path):
    map_path = tmp_path / "oversized.json"
    map_path.write_text(
        json.dumps({"map": {"41": ["1C00"] * 257}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="exceeds 256 codepoints"):
        LepchaConverter.from_map_file(map_path)


def test_lepcha_map_parser_rejects_invalid_utf8_with_context(tmp_path):
    map_path = tmp_path / "invalid-utf8.json"
    map_path.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="invalid UTF-8 in Lepcha legacy map"):
        LepchaConverter.from_map_file(map_path)


@pytest.mark.parametrize(
    "byte_map",
    [
        [],
        {},
        {True: (0x1C00,)},
        {-1: (0x1C00,)},
        {0x100: (0x1C00,)},
        {0x00: (0x1C00,)},
        {0x09: (0x1C00,)},
        {0x20: (0x1C00,)},
        {0x2D: (0x1C00,)},
        {0x7F: (0x1C00,)},
        {0x41: ()},
        {0x41: "ᰀ"},
        {0x41: 0x1C00},
        {0x41: {0x1C00: 1}},
        {0x41: {0x1C00}},
        {0x41: frozenset({0x1C00})},
        {0x41: (True,)},
        {0x41: (0x41,)},
        {0x41: (0x1C38,)},
        {0x41: (0xD800,)},
        {0x41: (0x110000,)},
    ],
)
def test_lepcha_constructor_rejects_unsafe_maps(byte_map):
    with pytest.raises(ValueError):
        LepchaConverter(byte_map)


def test_lepcha_constructor_freezes_mutable_mapping_and_targets():
    target = [0x1C00]
    byte_map = {0x41: target}
    converter = LepchaConverter(byte_map)

    target[0] = 0x110000
    byte_map[0x41] = [0x1C01]

    assert converter.convert("A").unicode_text == "ᰀ"


def test_lepcha_constructor_consumes_one_shot_targets_once():
    converter = LepchaConverter({0x41: iter([0x1C00])})

    assert converter.convert("A").unicode_text == "ᰀ"
    assert converter.convert("A").unicode_text == "ᰀ"


def test_lepcha_constructor_accepts_extended_sources_and_the_exact_target_limit():
    converter = LepchaConverter(
        {
            0x80: (0x1C00,) * 256,
            0x9F: (0x1C01,),
            0xFF: (0x1C02,),
        }
    )

    result = converter.convert("\x80\x9f\xff")
    assert result.unicode_text == "ᰀ" * 256 + "ᰁᰂ"
    assert result.lepcha_char_count == 258
    assert result.replacement_count == 3
    assert result.unmapped_bytes == []


def test_lepcha_constructor_rejects_an_unbounded_target_without_hanging():
    def forever():
        while True:
            yield 0x1C00

    with pytest.raises(ValueError, match="exceeds 256 codepoints"):
        LepchaConverter({0x41: forever()})


@pytest.mark.parametrize(
    ("source", "label"),
    [("(", "0x28"), (")", "0x29"), ("*", "0x2A"), ("+", "0x2B"), ("/", "0x2F")],
)
def test_each_observed_unresolved_lepcha_byte_is_preserved_and_strictly_rejected(source, label):
    result = convert_lepcha(source)
    assert result.unicode_text == source
    assert result.lepcha_char_count == 0
    assert result.replacement_count == 0
    assert result.unmapped_bytes == [label]
    with pytest.raises(ValueError, match=label):
        convert_lepcha(source, strict=True)
    with pytest.raises(ValueError, match=label):
        convert(source, font="lepcha-sikkimherald", strict=True)


def test_lepcha_consonant_bytes_map_to_base_series():
    conv = LepchaConverter.default()
    # Uppercase Latin A.. -> the Lepcha base-consonant series in Unicode order.
    assert conv.convert("A").unicode_text == "ᰀ"  # KA
    assert conv.convert("B").unicode_text == "ᰂ"  # KHA
    assert conv.convert("C").unicode_text == "ᰃ"  # GA
    assert conv.convert("Z").unicode_text == "ᰠ"  # SA
    # Lowercase carry the two overflow bases SHA/WA + the independent vowel A.
    assert conv.convert("k").unicode_text == "ᰡ"  # SHA
    assert conv.convert("p").unicode_text == "ᰢ"  # WA
    assert conv.convert("w").unicode_text == "ᰣ"  # independent A


def test_lepcha_digits_map_to_lepcha_digits():
    conv = LepchaConverter.default()
    assert conv.convert("0").unicode_text == "᱀"  # DIGIT ZERO
    assert conv.convert("539").unicode_text == "᱅᱃᱉"  # 5 3 9


@pytest.mark.parametrize(
    ("source", "name"),
    [("d", "I"), ("c", "O"), ("f", "OO")],
)
def test_every_lepcha_pre_base_vowel_reorders_after_base(source, name):
    conv = LepchaConverter.default()
    # In the legacy stream I/O/OO are keyed before the base; Unicode stores them after.
    out = conv.convert(source + "A")
    assert [unicodedata.name(ch) for ch in out.unicode_text] == [
        "LEPCHA LETTER KA",
        f"LEPCHA VOWEL SIGN {name}",
    ]
    # Same syllable typed base-first yields identical output.
    assert conv.convert("A" + source).unicode_text == out.unicode_text


def test_lepcha_canonical_cluster_order():
    conv = LepchaConverter.default()
    # base 'A'=KA + post-base vowel 'g'=U + final ':'=SIGN M -> base + vowel + final.
    out = conv.convert("Ag:").unicode_text
    assert [unicodedata.name(ch) for ch in out] == [
        "LEPCHA LETTER KA",
        "LEPCHA VOWEL SIGN U",
        "LEPCHA CONSONANT SIGN M",
    ]


def test_lepcha_two_syllable_word_keeps_pre_vowel_with_its_base():
    conv = LepchaConverter.default()
    # 'Ag' (KA+U) then pre-base 'c' (O) belonging to the NEXT base 'C' (GA): the
    # trailing-sign run must STOP at the pre-base vowel so O attaches to GA, not KA.
    out = conv.convert("AgcC").unicode_text
    assert [unicodedata.name(ch) for ch in out] == [
        "LEPCHA LETTER KA",
        "LEPCHA VOWEL SIGN U",
        "LEPCHA LETTER GA",
        "LEPCHA VOWEL SIGN O",
    ]


def test_lepcha_output_is_nfc_and_in_block():
    res = convert_lepcha("AgC: cA dC")
    non_space = [ch for ch in res.unicode_text if ch != " "]
    assert non_space, "expected Lepcha output"
    assert all(0x1C00 <= ord(ch) <= 0x1C4F for ch in non_space)
    assert res.unicode_text == unicodedata.normalize("NFC", res.unicode_text)


def test_lepcha_remaining_unmapped_bytes_are_flagged_not_silently_dropped():
    res = convert_lepcha("A*()+/")
    assert res.unmapped_bytes == ["0x28", "0x29", "0x2A", "0x2B", "0x2F"]
    with pytest.raises(ValueError):
        convert_lepcha("A*()+/", strict=True)


def test_lepcha_visual_leading_final_k_moves_to_following_base():
    # Legacy ]=FINAL K and d=pre-base I both precede the base T. The final must
    # not attach to the preceding A syllable.
    result = convert_lepcha("A]dT", strict=True)
    assert [unicodedata.name(ch) for ch in result.unicode_text] == [
        "LEPCHA LETTER KA",
        "LEPCHA LETTER DZA",
        "LEPCHA VOWEL SIGN I",
        "LEPCHA CONSONANT SIGN K",
    ]


def test_lepcha_subjoined_ra_and_hyphen_are_resolved():
    result = convert_lepcha(r"C\% -", strict=True)
    assert result.unicode_text == "ᰃ᰷ᰥ -"
    assert not result.unmapped_bytes


def test_lepcha_structural_whitespace_is_not_reported_as_unmapped():
    result = convert_lepcha("A\t\r\n", strict=True)
    assert result.unicode_text == "ᰀ\t\r\n"
    assert result.unmapped_bytes == []


@pytest.mark.parametrize("font", ["lepcha-sikkimherald", "lepcha", "sikkimherald-lepcha"])
def test_every_dispatcher_alias_routes_to_lepcha(font):
    assert convert("A-", font=font, strict=True) == "ᰀ-"
    with pytest.raises(ValueError, match="0x2A"):
        convert("*", font=font, strict=True)


def test_lepcha_genuine_unicode_passes_through():
    text = "ᰀᰪ"
    res = convert_lepcha(text, strict=True)
    assert res.unicode_text == text
    assert not res.unmapped_bytes


def test_lepcha_empty_map_rejected():
    with pytest.raises(ValueError):
        LepchaConverter({})


def test_nukta_precedes_subjoined_in_canonical_order():
    # The Unicode Standard ch.13 Table 13-9: encoding order is consonant,
    # nukta, subjoined consonant, vowel sign, final, ran. The spec's worked
    # example: retroflex t = <KA, NUKTA, SUBJOINED RA>. Regression for the
    # 2026-07-14 audit finding (nukta was emitted after subjoined marks).
    from nepal_ttf2utf.lepcha import convert_lepcha

    for raw in ("A\\&", "A&\\"):  # KA+NUKTA+SUBJ-YA in both input orders
        out = convert_lepcha(raw).unicode_text
        assert "ᰀ᰷ᰤ" in out, (raw, out.encode("unicode_escape"))
