"""Sikkim Herald live-text Lepcha (Róng) conversion tests.

Anchors are the shape-identity + round-trip-verified cases from the source
derivation, including the pre-base vowel reordering this font requires.
"""

import hashlib
import json
import unicodedata
from collections import Counter
from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from importlib import resources
from itertools import product, repeat
from types import MappingProxyType

import pytest

import nepal_ttf2utf as package_module
import nepal_ttf2utf.lepcha as lepcha_module
from nepal_ttf2utf import convert, convert_lepcha
from nepal_ttf2utf.lepcha import LEPCHA_PASSTHROUGH, LepchaConverter
from nepal_ttf2utf.unicode_span import _is_assigned_script_codepoint


def _singleton_legacy_source_by_target(converter: LepchaConverter) -> dict[int, str]:
    result: dict[int, str] = {}
    for source, target in converter._byte_map.items():
        if len(target) == 1:
            assert target[0] not in result
            result[target[0]] = chr(source)
    return result


def _provenance_input(
    legacy_source: dict[int, str], codepoints: tuple[int, ...], mask: tuple[bool, ...]
) -> str:
    assert len(codepoints) == len(mask)
    return "".join(
        legacy_source[codepoint] if is_derived else chr(codepoint)
        for codepoint, is_derived in zip(codepoints, mask)
    )


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

    reorder = converter._contract.reorder
    runtime_payload = json.dumps(
        {
            "byte_map": [
                [source, list(target)]
                for source, target in sorted(converter._contract.byte_map.items())
            ],
            "passthrough": sorted(converter._contract.passthrough),
            "reorder": {
                "bases": sorted(reorder.bases),
                "cluster_boundaries": sorted(reorder.cluster_boundaries),
                "dependent_signs": sorted(reorder.dependent_signs),
                "final_signs": sorted(reorder.final_signs),
                "nukta": reorder.nukta,
                "pre_base_vowels": sorted(reorder.pre_base_vowels),
                "provenance": reorder.provenance,
                "ran": reorder.ran,
                "subjoined": sorted(reorder.subjoined),
                "visual_leading_finals": sorted(reorder.visual_leading_finals),
                "vowel_signs": sorted(reorder.vowel_signs),
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    assert len(runtime_payload) == 1530
    assert hashlib.sha256(runtime_payload).hexdigest() == (
        "71679f0b524f9c82acdc68ec02db96ab0096a53c4efab895964aaedf3c875d08"
    )

    assigned = {
        codepoint
        for codepoint in range(0x1C00, 0x1C50)
        if _is_assigned_script_codepoint(codepoint, "Lepcha")
    }
    assert (len(reorder.bases), len(reorder.dependent_signs), len(reorder.cluster_boundaries)) == (
        39,
        20,
        15,
    )
    assert not reorder.bases & reorder.dependent_signs
    assert not reorder.bases & reorder.cluster_boundaries
    assert not reorder.dependent_signs & reorder.cluster_boundaries
    assert reorder.bases | reorder.dependent_signs | reorder.cluster_boundaries == assigned
    assert reorder.pre_base_vowels == frozenset({0x1C27, 0x1C28, 0x1C29})
    assert reorder.visual_leading_finals == frozenset({0x1C2D})
    assert reorder.provenance == "legacy-byte-derived-only"


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
        mapped, derived, replacements, unmapped = converter._byte_pass_with_provenance(source)

        assert mapped == expected, source_hex
        assert derived == (True,) * len(expected), source_hex
        assert replacements == 1, source_hex
        assert unmapped == [], source_hex
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
    classification_counts: Counter[str] = Counter()

    for source in range(0x100):
        character = chr(source)
        result = converter.convert(character)
        _mapped, derived, _replacements, _unmapped = converter._byte_pass_with_provenance(character)
        if source in expected_map:
            classification = "mapped"
            expected = expected_map[source]
            assert derived == (True,) * len(expected), f"0x{source:02X}"
            assert result.unicode_text == expected, f"0x{source:02X}"
            assert result.lepcha_char_count == len(expected), f"0x{source:02X}"
            assert result.replacement_count == 1, f"0x{source:02X}"
            assert result.unmapped_bytes == [], f"0x{source:02X}"
        elif source in structural | passthrough:
            classification = "structural" if source in structural else "passthrough"
            assert derived == (False,), f"0x{source:02X}"
            assert result.unicode_text == character, f"0x{source:02X}"
            assert result.lepcha_char_count == 0, f"0x{source:02X}"
            assert result.replacement_count == 0, f"0x{source:02X}"
            assert result.unmapped_bytes == [], f"0x{source:02X}"
        else:
            classification = "diagnosed"
            assert derived == (False,), f"0x{source:02X}"
            label = f"0x{source:02X}"
            assert result.unicode_text == character, label
            assert result.lepcha_char_count == 0, label
            assert result.replacement_count == 0, label
            assert result.unmapped_bytes == [label], label
            with pytest.raises(ValueError, match=label):
                convert_lepcha(character, strict=True)
        classification_counts[classification] += 1

    assert classification_counts == {
        "mapped": 65,
        "structural": 4,
        "passthrough": 1,
        "diagnosed": 186,
    }


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
        (
            '{"_doc": 0, "map": {"41": ["1C00"], "41": ["1C01"]}}',
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
        ('{"map": {"41": {"1C00": "1"}}}', "must be a non-empty list"),
        ('{"map": {"41": [7168]}}', "numeric JSON values are not permitted"),
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


@pytest.mark.parametrize(
    "literal",
    [
        pytest.param("0", id="zero"),
        pytest.param("-1", id="negative-integer"),
        pytest.param("1.25", id="decimal"),
        pytest.param("-0.25", id="negative-decimal"),
        pytest.param("1e400", id="positive-exponent"),
        pytest.param("1E-4000", id="negative-exponent"),
        pytest.param("NaN", id="nan"),
        pytest.param("Infinity", id="infinity"),
        pytest.param("-Infinity", id="negative-infinity"),
        pytest.param("9" * 4_301, id="long-integer"),
    ],
)
def test_lepcha_map_parser_rejects_every_json_numeric_form(literal, tmp_path):
    map_path = tmp_path / "numeric.json"
    map_path.write_text(
        '{"_doc":' + literal + ',"map":{"41":["1C00"]}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as error:
        LepchaConverter.from_map_file(map_path)
    assert str(error.value) == (
        f"numeric JSON values are not permitted in Lepcha legacy map: {map_path}"
    )


@pytest.mark.parametrize(
    "map_text",
    [
        "0",
        '{"_doc":0,"map":{"41":["1C00"]}}',
        '{"_confidence":0,"map":{"41":["1C00"]}}',
        '{"map":0}',
        '{"map":{"41":[0]}}',
        '{"_unresolved_bytes":[0],"map":{"41":["1C00"]}}',
    ],
)
def test_lepcha_map_parser_rejects_numeric_values_in_every_schema_position(map_text, tmp_path):
    map_path = tmp_path / "numeric-position.json"
    map_path.write_text(map_text, encoding="utf-8")

    with pytest.raises(ValueError) as error:
        LepchaConverter.from_map_file(map_path)
    assert str(error.value) == (
        f"numeric JSON values are not permitted in Lepcha legacy map: {map_path}"
    )


@pytest.mark.parametrize("malformed_number", ["1e", "01"])
def test_lepcha_map_parser_preserves_invalid_json_precedence(malformed_number, tmp_path):
    map_path = tmp_path / "malformed-number.json"
    map_path.write_text('{"_doc":' + malformed_number + "}", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON in Lepcha legacy map"):
        LepchaConverter.from_map_file(map_path)


@pytest.mark.parametrize("literal", ["true", "false", "null"])
def test_lepcha_map_parser_keeps_boolean_and_null_schema_validation(literal, tmp_path):
    map_path = tmp_path / "non-numeric-scalar.json"
    map_path.write_text(
        '{"_doc":' + literal + ',"map":{"41":["1C00"]}}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="metadata must be a string"):
        LepchaConverter.from_map_file(map_path)


def test_lepcha_map_parser_accepts_numeric_looking_metadata_strings(tmp_path):
    map_path = tmp_path / "numeric-looking-string.json"
    map_path.write_text(
        json.dumps(
            {
                "_doc": "0 -1 1.25 1e400 NaN Infinity -Infinity",
                "map": {"41": ["1C00"]},
            }
        ),
        encoding="utf-8",
    )

    assert LepchaConverter.from_map_file(map_path).convert("A").unicode_text == "ᰀ"


def test_lepcha_map_parser_rejects_exact_size_numeric_token_without_conversion(tmp_path):
    map_path = tmp_path / "exact-size-numeric.json"
    prefix = b'{"_doc":'
    suffix = b',"map":{"41":["1C00"]}}'
    digits = b"9" * (lepcha_module._MAX_MAP_FILE_BYTES - len(prefix) - len(suffix))
    payload = prefix + digits + suffix
    assert len(payload) == lepcha_module._MAX_MAP_FILE_BYTES
    map_path.write_bytes(payload)

    with pytest.raises(ValueError) as error:
        LepchaConverter.from_map_file(map_path)
    assert str(error.value) == (
        f"numeric JSON values are not permitted in Lepcha legacy map: {map_path}"
    )


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


def test_lepcha_map_parser_rejects_oversized_files_before_decoding(tmp_path):
    map_path = tmp_path / "oversized.json"
    map_path.write_bytes(b" " * 1_000_001)

    with pytest.raises(ValueError, match="exceeds 1000000 bytes"):
        LepchaConverter.from_map_file(map_path)


def test_lepcha_map_parser_fails_closed_on_deep_json(tmp_path):
    map_path = tmp_path / "deeply-nested.json"
    map_path.write_text(
        '{"map":' + "[" * 10_000 + '"x"' + "]" * 10_000 + "}",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="exceeds 64 JSON nesting levels"):
        LepchaConverter.from_map_file(map_path)


def test_lepcha_map_parser_normalizes_decoder_recursion_error(monkeypatch, tmp_path):
    map_path = tmp_path / "recursive-decoder.json"
    map_path.write_text('{"map":{"41":["1C00"]}}', encoding="utf-8")
    decoder_calls = []

    def recursive_decoder(*args, **kwargs):
        decoder_calls.append((args, kwargs))
        raise RecursionError("decoder nesting limit")

    monkeypatch.setattr(lepcha_module.json, "loads", recursive_decoder)
    with pytest.raises(ValueError, match="invalid nested JSON in Lepcha legacy map"):
        LepchaConverter.from_map_file(map_path)
    assert len(decoder_calls) == 1
    args, kwargs = decoder_calls[0]
    assert args == ('{"map":{"41":["1C00"]}}',)
    assert kwargs["object_pairs_hook"] is lepcha_module._unique_json_object
    number_token = kwargs["parse_int"]
    assert isinstance(number_token, lepcha_module._JSONNumberToken)
    assert kwargs["parse_float"] is number_token
    assert kwargs["parse_constant"] is number_token


def test_lepcha_json_depth_scan_ignores_container_tokens_inside_strings(tmp_path):
    map_path = tmp_path / "brackets-in-metadata.json"
    map_path.write_text(
        json.dumps({"_doc": '[\\"]{' * 1_000, "map": {"41": ["1C00"]}}),
        encoding="utf-8",
    )

    assert LepchaConverter.from_map_file(map_path).convert("A").unicode_text == "ᰀ"


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


def test_lepcha_constructor_rejects_an_unbounded_mapping_without_hanging():
    class EndlessMapping(Mapping):
        def __getitem__(self, _key):
            return (0x1C00,)

        def __iter__(self):
            return repeat(0x41)

        def __len__(self):
            return 1

    with pytest.raises(ValueError, match="source map exceeds 256 entries"):
        LepchaConverter(EndlessMapping())


class _PathologicalLepchaItemsMapping(Mapping):
    def __init__(self, items):
        self._items = items

    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 1

    def items(self):
        return self._items


@pytest.mark.parametrize(
    "raw_item",
    [
        0x41,
        {0x41, 0x1C00},
        (0x41,),
        (0x41, (0x1C00,), "extra"),
        {0x41: (0x1C00,)},
        "AB",
    ],
)
def test_lepcha_constructor_rejects_malformed_mapping_items(raw_item):
    byte_map = _PathologicalLepchaItemsMapping((raw_item,))

    with pytest.raises(ValueError, match="invalid Lepcha source map entry"):
        LepchaConverter(byte_map)


def test_lepcha_constructor_rejects_duplicate_semantic_sources():
    byte_map = _PathologicalLepchaItemsMapping(((0x41, (0x1C00,)), (0x41, (0x1C01,))))

    with pytest.raises(ValueError, match="duplicate Lepcha source byte: 0x41"):
        LepchaConverter(byte_map)


@pytest.mark.parametrize(
    ("items", "message"),
    [
        (None, "invalid Lepcha source map item sequence"),
        (repeat((0x41, (0x1C00,))), "source map exceeds 256 entries"),
    ],
)
def test_lepcha_constructor_rejects_invalid_or_unbounded_item_sequences(items, message):
    byte_map = _PathologicalLepchaItemsMapping(items)

    with pytest.raises(ValueError, match=message):
        LepchaConverter(byte_map)


def test_complete_byte_aggregate_retains_the_corrected_pinned_output():
    source = "".join(chr(codepoint) for codepoint in range(0x100))
    result = LepchaConverter.default().convert(source)

    assert len(result.unicode_text) == 256
    assert result.lepcha_char_count == 65
    assert result.replacement_count == 65
    assert len(result.unmapped_bytes) == 186
    assert hashlib.sha256(result.unicode_text.encode("utf-8")).hexdigest() == (
        "bd7cd93d6e0a683440b903a80c159fa8c036880d2e5f8da92b3ae62220115ee1"
    )


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


def test_every_assigned_lepcha_punctuation_and_digit_is_a_cluster_boundary():
    converter = LepchaConverter.default()
    reorder = converter._contract.reorder
    exercised = 0

    for base, boundary, sign in product(
        sorted(reorder.bases),
        sorted(reorder.cluster_boundaries),
        sorted(reorder.dependent_signs),
    ):
        source = "".join(chr(codepoint) for codepoint in (base, boundary, sign))
        assert converter._reorder_pass(source) == source, (base, boundary, sign)
        exercised += 1

    assert exercised == 11_700


def test_every_legacy_digit_blocks_every_mapped_sign_after_every_mapped_base():
    converter = LepchaConverter.default()
    legacy_source = _singleton_legacy_source_by_target(converter)
    reorder = converter._contract.reorder
    bases = sorted(set(legacy_source) & reorder.bases)
    digits = sorted(set(legacy_source) & set(range(0x1C40, 0x1C4A)))
    signs = sorted(set(legacy_source) & reorder.dependent_signs)
    exercised = 0

    assert (len(bases), len(digits), len(signs)) == (36, 10, 19)
    for base, digit, sign in product(bases, digits, signs):
        expected = "".join(chr(codepoint) for codepoint in (base, digit, sign))
        legacy_result = converter.convert(
            legacy_source[base] + legacy_source[digit] + legacy_source[sign]
        )
        native_digit_result = converter.convert(
            legacy_source[base] + chr(digit) + legacy_source[sign]
        )

        assert legacy_result.unicode_text == expected, (base, digit, sign)
        assert legacy_result.replacement_count == 3, (base, digit, sign)
        assert native_digit_result.unicode_text == expected, (base, digit, sign)
        assert native_digit_result.replacement_count == 2, (base, digit, sign)
        assert legacy_result.unmapped_bytes == native_digit_result.unmapped_bytes == []
        exercised += 1

    assert exercised == 6_840


def test_every_legacy_digit_stops_signs_on_both_sides():
    converter = LepchaConverter.default()
    legacy_source = _singleton_legacy_source_by_target(converter)
    reorder = converter._contract.reorder
    base = 0x1C00
    digits = sorted(set(legacy_source) & set(range(0x1C40, 0x1C4A)))
    signs = sorted(set(legacy_source) & reorder.dependent_signs)
    left_clusters = {
        sign: converter.convert(legacy_source[base] + legacy_source[sign]).unicode_text
        for sign in signs
    }
    exercised = 0

    for left_sign, digit, right_sign in product(signs, digits, signs):
        source = (
            legacy_source[base]
            + legacy_source[left_sign]
            + legacy_source[digit]
            + legacy_source[right_sign]
        )
        expected = left_clusters[left_sign] + chr(digit) + chr(right_sign)
        result = converter.convert(source)

        assert result.unicode_text == expected, (left_sign, digit, right_sign)
        assert result.replacement_count == 4, (left_sign, digit, right_sign)
        assert result.unmapped_bytes == [], (left_sign, digit, right_sign)
        exercised += 1

    assert exercised == 3_610


def test_digits_block_leading_signs_but_do_not_disable_the_next_cluster():
    converter = LepchaConverter.default()
    legacy_source = _singleton_legacy_source_by_target(converter)
    reorder = converter._contract.reorder
    leaders = sorted(reorder.pre_base_vowels | reorder.visual_leading_finals)
    digits = sorted(set(legacy_source) & set(range(0x1C40, 0x1C4A)))
    bases = sorted(set(legacy_source) & reorder.bases)
    exercised = 0

    for leader, digit, base in product(leaders, digits, bases):
        before_digit = converter.convert(
            legacy_source[leader] + legacy_source[digit] + legacy_source[base]
        )
        after_digit = converter.convert(
            legacy_source[base] + legacy_source[digit] + legacy_source[leader] + legacy_source[base]
        )

        assert before_digit.unicode_text == "".join(
            chr(codepoint) for codepoint in (leader, digit, base)
        ), (leader, digit, base)
        assert after_digit.unicode_text == "".join(
            chr(codepoint) for codepoint in (base, digit, base, leader)
        ), (leader, digit, base)
        assert before_digit.replacement_count == 3
        assert after_digit.replacement_count == 4
        assert before_digit.unmapped_bytes == after_digit.unmapped_bytes == []
        exercised += 1

    assert exercised == 1_440


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


def test_every_visual_leader_and_mapped_base_provenance_mask_is_exact():
    converter = LepchaConverter.default()
    legacy_source = _singleton_legacy_source_by_target(converter)
    reorder = converter._contract.reorder
    leaders = sorted(reorder.pre_base_vowels | reorder.visual_leading_finals)
    bases = sorted(set(legacy_source) & reorder.bases)
    derived_cases = preserved_cases = 0

    for leader, base in product(leaders, bases):
        codepoints = (leader, base)
        for mask in product((False, True), repeat=2):
            result = converter.convert(_provenance_input(legacy_source, codepoints, mask))
            expected_codepoints = (base, leader) if all(mask) else codepoints

            assert result.unicode_text == "".join(map(chr, expected_codepoints)), (
                codepoints,
                mask,
            )
            assert result.replacement_count == sum(mask), (codepoints, mask)
            assert result.unmapped_bytes == [], (codepoints, mask)
            derived_cases += all(mask)
            preserved_cases += not all(mask)

    assert derived_cases == 144
    assert preserved_cases == 432


def test_representative_cluster_sort_requires_complete_legacy_provenance():
    converter = LepchaConverter.default()
    legacy_source = _singleton_legacy_source_by_target(converter)
    source_order = (0x1C00, 0x1C2E, 0x1C37)  # base, final M, nukta
    canonical_order = (0x1C00, 0x1C37, 0x1C2E)

    for mask in product((False, True), repeat=3):
        result = converter.convert(_provenance_input(legacy_source, source_order, mask))
        expected = canonical_order if all(mask) else source_order

        assert result.unicode_text == "".join(map(chr, expected)), mask
        assert result.replacement_count == sum(mask), mask
        assert result.unmapped_bytes == [], mask


@pytest.mark.parametrize(
    "derived",
    [
        (True,),
        (True, 1),
        [True, True],
    ],
)
def test_lepcha_reorder_rejects_invalid_internal_provenance(derived):
    with pytest.raises(ValueError, match="invalid Lepcha reorder provenance"):
        LepchaConverter.default()._reorder_pass("\u1c27\u1c00", derived)


def test_lepcha_reorder_accepts_empty_and_retains_private_default_behavior():
    converter = LepchaConverter.default()
    assert converter._reorder_pass("", ()) == ""
    assert converter._reorder_pass("\u1c27\u1c00") == "\u1c00\u1c27"


def test_lepcha_runtime_contract_is_transitively_immutable(monkeypatch):
    converter = LepchaConverter.default()
    reorder = converter._contract.reorder

    assert isinstance(converter._byte_map, MappingProxyType)
    assert isinstance(converter._contract.byte_map, MappingProxyType)
    assert type(converter._contract.passthrough) is frozenset
    assert type(reorder.bases) is frozenset
    assert type(reorder.dependent_signs) is frozenset
    assert type(reorder.cluster_boundaries) is frozenset

    with pytest.raises(TypeError):
        converter._byte_map[0x41] = (0x1C01,)
    with pytest.raises(FrozenInstanceError):
        converter._contract.byte_map = MappingProxyType({})
    with pytest.raises(FrozenInstanceError):
        reorder.nukta = 0x1C00
    with pytest.raises(AttributeError):
        reorder.bases.add(0x1C38)

    monkeypatch.setattr(lepcha_module, "_DEFAULT_REORDER_CONTRACT", None)
    monkeypatch.setattr(lepcha_module, "_BASES", frozenset())
    monkeypatch.setattr(lepcha_module, "_DEPENDENT_SIGNS", frozenset())
    monkeypatch.setattr(lepcha_module, "PRE_BASE_VOWELS", frozenset())
    monkeypatch.setattr(lepcha_module, "VISUAL_LEADING_FINALS", frozenset())
    monkeypatch.setattr(lepcha_module, "LEPCHA_PASSTHROUGH", frozenset())

    assert converter.convert("dA").unicode_text == "\u1c00\u1c27"
    assert converter.convert("A0g").unicode_text == "\u1c00\u1c40\u1c2a"
    assert converter.convert("-").unmapped_bytes == []


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


def test_lepcha_combined_diagnostics_are_preserved_deduplicated_and_sorted():
    leftovers = "((\x00\x7f\x80\ud800\ue000\ufdd0\U0001f600"
    result = convert_lepcha("A" + leftovers)
    expected_labels = [
        "0x00",
        "0x28",
        "0x7F",
        "0x80",
        "U+1F600",
        "U+D800",
        "U+E000",
        "U+FDD0",
    ]

    assert result.unicode_text == "\u1c00" + leftovers
    assert result.lepcha_char_count == 1
    assert result.replacement_count == 1
    assert result.unmapped_bytes == expected_labels

    with pytest.raises(ValueError) as error:
        convert_lepcha("A" + leftovers, strict=True)
    assert all(label in str(error.value) for label in expected_labels)


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
    assert convert("A0g", font=font, strict=True) == "\u1c00\u1c40\u1c2a"
    assert convert("\u1c27\u1c00", font=font, strict=True) == "\u1c27\u1c00"
    assert convert("d\u1c00", font=font, strict=True) == "\u1c27\u1c00"
    assert convert("\u1c27A", font=font, strict=True) == "\u1c27\u1c00"
    with pytest.raises(ValueError, match="0x2A"):
        convert("*", font=font, strict=True)


def test_lepcha_dispatcher_alias_inventories_are_frozen_disjoint_and_exact():
    herald = frozenset({"lepcha", "lepcha-sikkimherald", "sikkimherald-lepcha"})
    jg = frozenset({"jg-lepcha", "jglepcha", "lepcha-jg"})
    unicode_fonts = frozenset(
        {
            "lepcha-unicode",
            "mingzat",
            "mingzat-regular",
            "noto sans lepcha",
            "noto-sans-lepcha",
            "notosanslepcha",
            "notosanslepcha-regular",
            "unicode-lepcha",
        }
    )

    assert package_module._LEPCHA_FONTS == herald
    assert package_module._JG_LEPCHA_FONTS == jg
    assert package_module._LEPCHA_UNICODE_FONTS == unicode_fonts
    assert not herald & jg
    assert not herald & unicode_fonts
    assert not jg & unicode_fonts
    with pytest.raises(AttributeError):
        package_module._LEPCHA_FONTS.add("forged")
    with pytest.raises(AttributeError):
        package_module._JG_LEPCHA_FONTS.add("forged")
    with pytest.raises(AttributeError):
        package_module._LEPCHA_UNICODE_FONTS.add("forged")

    for font in unicode_fonts:
        assert convert("A", font=font) == "A"
        assert convert("\u1c27\u1c00", font=font, strict=True) == "\u1c27\u1c00"

    assert convert("A0g", font="ABCDEF+SikkimHerald_Lepcha", strict=True) == ("\u1c00\u1c40\u1c2a")


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
