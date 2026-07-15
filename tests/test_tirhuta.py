"""Corrected Janaki / Devanagari-coded Tirhuta project-contract tests."""

import hashlib
import json
import unicodedata
from collections import Counter
from itertools import product

import pytest

import nepal_ttf2utf as package_module
import nepal_ttf2utf.tirhuta as tirhuta_module
from nepal_ttf2utf import convert, convert_tirhuta
from nepal_ttf2utf.tirhuta import TirhutaConverter
from nepal_ttf2utf.unicode_span import _is_assigned_script_codepoint


def _mapping_rows(converter: TirhutaConverter) -> list[list[object]]:
    return [
        [source, list(target)] for source, target in sorted(converter._contract.mapping.items())
    ]


def _reorder_contract(converter: TirhutaConverter) -> dict[str, object]:
    contract = converter._contract
    return {
        "consonants": sorted(contract.consonants),
        "dependents": sorted(contract.dependents),
        "nukta": contract.nukta,
        "prebase_i": contract.prebase_i,
        "provenance": contract.provenance,
        "ra": contract.ra,
        "virama": contract.virama,
    }


def _json_payload(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")


def _singleton_source_by_target(
    converter: TirhutaConverter, targets: frozenset[int]
) -> dict[int, int]:
    result = {
        target[0]: source
        for source, target in converter._contract.mapping.items()
        if len(target) == 1 and target[0] in targets
    }
    assert set(result) == set(targets)
    return result


def _assert_clean_reorder(
    source: str,
    expected: str,
    *,
    replacements: int,
    prebase_moves: int = 0,
    reph_moves: int = 0,
) -> None:
    result = TirhutaConverter().convert(source)
    assert result.unicode_text == unicodedata.normalize("NFC", expected), repr(source)
    assert result.replacement_count == replacements, repr(source)
    assert result.prebase_i_moves == prebase_moves, repr(source)
    assert result.reph_moves == reph_moves, repr(source)
    assert result.unmapped_codepoints == [], repr(source)


def test_corrected_tirhuta_data_and_reorder_contracts_are_pinned():
    converter = TirhutaConverter()
    contract = converter._contract
    mapping = contract.mapping

    assert len(mapping) == 90
    assert 0x090E not in mapping
    assert 0x0912 not in mapping
    assert Counter(len(target) for target in mapping.values()) == {1: 81, 2: 9}
    assert sum(len(target) for target in mapping.values()) == 99
    assert len(set(mapping.values())) == 90
    assert len({codepoint for target in mapping.values() for codepoint in target}) == 81
    assert len(contract.passthrough) == 49
    assert contract.consonants == frozenset(range(0x1148F, 0x114B0))
    assert contract.dependents == frozenset(range(0x114B0, 0x114C2)) | {0x114C3}
    assert (contract.prebase_i, contract.ra, contract.virama, contract.nukta) == (
        0x114B1,
        0x114A9,
        0x114C2,
        0x114C3,
    )
    assert (contract.block_lo, contract.block_hi) == (0x11480, 0x114DF)
    assert contract.provenance == "devanagari-derived-only"

    mapping_payload = _json_payload(_mapping_rows(converter))
    assert len(mapping_payload) == 1403
    assert hashlib.sha256(mapping_payload).hexdigest() == (
        "0a740647420fdddac4221bfedfa50b46082f1a6f640a172df3f4bc4e94ebb12a"
    )

    reorder_payload = _json_payload(_reorder_contract(converter))
    assert len(reorder_payload) == 440
    assert hashlib.sha256(reorder_payload).hexdigest() == (
        "050b1b75760b9ac030bb247d83019ea28ccb4a829667a1d35040a7ad8e738a20"
    )

    passthrough_payload = _json_payload(sorted(ord(value) for value in contract.passthrough))
    assert len(passthrough_payload) == 164
    assert hashlib.sha256(passthrough_payload).hexdigest() == (
        "d6422caf7cf326bcd10a5c318e07e4dbf4b5e7ae55120785c7e6f2ddf141a7c4"
    )

    full_payload = _json_payload(
        {
            **_reorder_contract(converter),
            "mapping": _mapping_rows(converter),
            "passthrough": sorted(ord(value) for value in contract.passthrough),
        }
    )
    assert len(full_payload) == 2033
    assert hashlib.sha256(full_payload).hexdigest() == (
        "85ac0769069141339bf23824b9cb435deb5b3f2068d946881c62dd0514bce29f"
    )

    source = "".join(chr(codepoint) for codepoint in sorted(mapping))
    expected = "".join(chr(codepoint) for key in sorted(mapping) for codepoint in mapping[key])
    result = converter.convert(source)
    assert result.unicode_text == expected
    assert len(result.unicode_text) == 99
    assert hashlib.sha256(result.unicode_text.encode("utf-8")).hexdigest() == (
        "4c78fd1cfeb017e1b94d01903e51c9860795e94f4886e4a26976c6ae4f2213ec"
    )
    assert result.replacement_count == 90
    assert result.tirhuta_char_count == 97
    assert result.prebase_i_moves == result.reph_moves == 0
    assert result.unmapped_codepoints == []


def test_every_supported_tirhuta_mapping_has_an_independent_semantic_anchor():
    mapping = TirhutaConverter()._contract.mapping
    double_sources = {0x0933, *range(0x0958, 0x0960)}
    assert {source for source, target in mapping.items() if len(target) == 2} == double_sources

    for source, target in mapping.items():
        if len(target) != 1:
            continue
        source_name = unicodedata.name(chr(source)).removeprefix("DEVANAGARI ")
        target_name = (
            unicodedata.name(chr(target[0])).removeprefix("DEVANAGARI ").removeprefix("TIRHUTA ")
        )
        assert source_name == target_name, f"U+{source:04X}"

    assert mapping[0x0933] == (0x114AA, 0x114C3)
    for source in range(0x0958, 0x0960):
        base_source, nukta_source = (
            int(value, 16) for value in unicodedata.decomposition(chr(source)).split()
        )
        assert nukta_source == 0x093C
        assert mapping[source] == mapping[base_source] + (0x114C3,)


def test_every_tirhuta_mapping_has_exact_isolated_output_and_counts():
    converter = TirhutaConverter()
    for source, target in converter._contract.mapping.items():
        source_text = chr(source)
        expected = "".join(chr(codepoint) for codepoint in target)
        result = converter.convert(source_text)
        assert result.unicode_text == expected, f"U+{source:04X}"
        assert result.replacement_count == 1
        assert result.tirhuta_char_count == sum(
            converter._contract.block_lo <= codepoint <= converter._contract.block_hi
            for codepoint in target
        )
        assert result.prebase_i_moves == result.reph_moves == 0
        assert result.unmapped_codepoints == []
        assert convert_tirhuta(source_text, strict=True) == result


def test_every_devanagari_position_has_an_exact_tirhuta_classification():
    converter = TirhutaConverter()
    counts: Counter[str] = Counter()
    for codepoint in range(0x0900, 0x0980):
        source = chr(codepoint)
        result = converter.convert(source)
        target = converter._contract.mapping.get(codepoint)
        if target is not None:
            counts["mapped"] += 1
            assert result.unicode_text == "".join(chr(value) for value in target)
            assert result.replacement_count == 1
            assert result.unmapped_codepoints == []
        else:
            counts["diagnosed"] += 1
            assert result.unicode_text == source
            assert result.replacement_count == 0
            assert result.tirhuta_char_count == 0
            assert result.unmapped_codepoints == [f"U+{codepoint:04X}"]
            with pytest.raises(ValueError, match=rf"U\+{codepoint:04X}"):
                convert_tirhuta(source, strict=True)
    assert counts == {"mapped": 90, "diagnosed": 38}


def test_independent_short_e_and_o_are_preserved_diagnosed_and_strictly_rejected():
    source = "\u090e\u0912"
    result = convert_tirhuta(source)
    assert result.unicode_text == source
    assert result.replacement_count == 0
    assert result.tirhuta_char_count == 0
    assert result.prebase_i_moves == result.reph_moves == 0
    assert result.unmapped_codepoints == ["U+090E", "U+0912"]
    with pytest.raises(ValueError, match=r"U\+090E U\+0912"):
        convert_tirhuta(source, strict=True)


def test_every_native_tirhuta_position_has_an_exact_assignment_classification():
    counts: Counter[str] = Counter()
    for codepoint in range(0x11480, 0x114E0):
        source = chr(codepoint)
        result = convert_tirhuta(source)
        assert result.unicode_text == source
        assert result.replacement_count == 0
        assert result.tirhuta_char_count == 1
        assert result.prebase_i_moves == result.reph_moves == 0
        if _is_assigned_script_codepoint(codepoint, "Tirhuta"):
            counts["assigned"] += 1
            assert result.unmapped_codepoints == []
            assert convert_tirhuta(source, strict=True) == result
        else:
            counts["reserved"] += 1
            assert result.unmapped_codepoints == [f"U+{codepoint:04X}"]
            with pytest.raises(ValueError, match=rf"U\+{codepoint:04X}"):
                convert_tirhuta(source, strict=True)
    assert counts == {"assigned": 82, "reserved": 14}


def test_every_byte_and_every_literal_allowlist_value_has_an_exact_classification():
    converter = TirhutaConverter()
    counts: Counter[str] = Counter()
    for codepoint in range(0x100):
        source = chr(codepoint)
        result = converter.convert(source)
        if source in converter._contract.passthrough:
            counts["passthrough"] += 1
            assert result.unicode_text == source
            assert result.unmapped_codepoints == []
            assert convert_tirhuta(source, strict=True) == result
        else:
            counts["diagnosed"] += 1
            assert result.unicode_text == source
            assert result.unmapped_codepoints == [f"U+{codepoint:04X}"]
        assert result.replacement_count == 0
        assert result.prebase_i_moves == result.reph_moves == 0
    assert counts == {"passthrough": 43, "diagnosed": 213}

    for source in converter._contract.passthrough:
        result = convert_tirhuta(source, strict=True)
        assert result.unicode_text == source
        assert result.unmapped_codepoints == []


def test_prebase_i_repair_exhausts_consonants_nukta_and_conjunct_state():
    converter = TirhutaConverter()
    contract = converter._contract
    consonant_source = _singleton_source_by_target(converter, contract.consonants)
    i_source = _singleton_source_by_target(converter, frozenset({contract.prebase_i}))[
        contract.prebase_i
    ]
    nukta_source = _singleton_source_by_target(converter, frozenset({contract.nukta}))[
        contract.nukta
    ]
    virama_source = _singleton_source_by_target(converter, frozenset({contract.virama}))[
        contract.virama
    ]

    for consonant in sorted(contract.consonants):
        source = chr(i_source) + chr(consonant_source[consonant])
        _assert_clean_reorder(
            source, chr(consonant) + chr(contract.prebase_i), replacements=2, prebase_moves=1
        )
        source += chr(nukta_source)
        _assert_clean_reorder(
            source,
            chr(consonant) + chr(contract.nukta) + chr(contract.prebase_i),
            replacements=3,
            prebase_moves=1,
        )

    for first, second in product(sorted(contract.consonants), repeat=2):
        for first_nukta, second_nukta in product((False, True), repeat=2):
            source_values = [i_source, consonant_source[first]]
            expected_values = [first]
            if first_nukta:
                source_values.append(nukta_source)
                expected_values.append(contract.nukta)
            source_values.extend((virama_source, consonant_source[second]))
            expected_values.extend((contract.virama, second))
            if second_nukta:
                source_values.append(nukta_source)
                expected_values.append(contract.nukta)
            expected_values.append(contract.prebase_i)
            _assert_clean_reorder(
                "".join(chr(value) for value in source_values),
                "".join(chr(value) for value in expected_values),
                replacements=len(source_values),
                prebase_moves=1,
            )

    double_sources = [source for source, target in contract.mapping.items() if len(target) == 2]
    for source in double_sources:
        expected = contract.mapping[source] + (contract.prebase_i,)
        _assert_clean_reorder(
            chr(i_source) + chr(source),
            "".join(chr(value) for value in expected),
            replacements=2,
            prebase_moves=1,
        )


def test_trailing_reph_repair_exhausts_base_and_dependent_state():
    converter = TirhutaConverter()
    contract = converter._contract
    consonant_source = _singleton_source_by_target(converter, contract.consonants)
    dependent_source = _singleton_source_by_target(converter, contract.dependents)
    ra_source = consonant_source[contract.ra]
    virama_source = _singleton_source_by_target(converter, frozenset({contract.virama}))[
        contract.virama
    ]

    dependent_sequences = [()]
    dependent_sequences.extend((value,) for value in sorted(contract.dependents))
    dependent_sequences.extend(product(sorted(contract.dependents), repeat=2))
    for consonant in sorted(contract.consonants):
        for dependents in dependent_sequences:
            source_values = [consonant_source[consonant]]
            source_values.extend(dependent_source[value] for value in dependents)
            source_values.extend((ra_source, virama_source))
            expected_values = (contract.ra, contract.virama, consonant, *dependents)
            _assert_clean_reorder(
                "".join(chr(value) for value in source_values),
                "".join(chr(value) for value in expected_values),
                replacements=len(source_values),
                reph_moves=1,
            )

    for source, target in contract.mapping.items():
        if len(target) != 2:
            continue
        expected = (contract.ra, contract.virama, *target)
        _assert_clean_reorder(
            "".join(chr(value) for value in (source, ra_source, virama_source)),
            "".join(chr(value) for value in expected),
            replacements=3,
            reph_moves=1,
        )


def test_combined_prebase_and_reph_repairs_preserve_pass_order_and_counts():
    converter = TirhutaConverter()
    contract = converter._contract
    consonant_source = _singleton_source_by_target(converter, contract.consonants)
    i_source = _singleton_source_by_target(converter, frozenset({contract.prebase_i}))[
        contract.prebase_i
    ]
    nukta_source = _singleton_source_by_target(converter, frozenset({contract.nukta}))[
        contract.nukta
    ]
    virama_source = _singleton_source_by_target(converter, frozenset({contract.virama}))[
        contract.virama
    ]
    ra_source = consonant_source[contract.ra]

    for consonant in sorted(contract.consonants):
        for with_nukta in (False, True):
            source_values = [i_source, consonant_source[consonant]]
            expected_tail = [consonant]
            if with_nukta:
                source_values.append(nukta_source)
                expected_tail.append(contract.nukta)
            source_values.extend((ra_source, virama_source))
            expected = (contract.ra, contract.virama, *expected_tail, contract.prebase_i)
            _assert_clean_reorder(
                "".join(chr(value) for value in source_values),
                "".join(chr(value) for value in expected),
                replacements=len(source_values),
                prebase_moves=1,
                reph_moves=1,
            )


def test_reorder_loops_accept_representative_paths_beyond_bounded_state_matrices():
    _assert_clean_reorder(
        "\u093f\u0915\u093c\u094d\u0916\u093c\u094d\u0917\u093c",
        "\U0001148f\U000114c3\U000114c2\U00011490\U000114c3"
        "\U000114c2\U00011491\U000114c3\U000114b1",
        replacements=9,
        prebase_moves=1,
    )
    _assert_clean_reorder(
        "\u0915\u093e\u0941\u0947\u0930\u094d",
        "\U000114a9\U000114c2\U0001148f\U000114b0\U000114b3\U000114b9",
        replacements=6,
        reph_moves=1,
    )


def test_native_tirhuta_reorder_shaped_sequences_are_never_custom_reordered():
    converter = TirhutaConverter()
    contract = converter._contract

    for consonant in sorted(contract.consonants):
        for with_nukta in (False, True):
            source_values = [contract.prebase_i, consonant]
            if with_nukta:
                source_values.append(contract.nukta)
            source = "".join(chr(value) for value in source_values)
            _assert_clean_reorder(source, source, replacements=0)

    dependent_sequences = [()]
    dependent_sequences.extend((value,) for value in sorted(contract.dependents))
    dependent_sequences.extend(product(sorted(contract.dependents), repeat=2))
    for consonant in sorted(contract.consonants):
        for dependents in dependent_sequences:
            values = (consonant, *dependents, contract.ra, contract.virama)
            source = "".join(chr(value) for value in values)
            _assert_clean_reorder(source, source, replacements=0)


@pytest.mark.parametrize(
    ("source", "expected", "replacements"),
    [
        (
            "\U000114b1\u0935",
            "\U000114b1\U000114ab",
            1,
        ),
        (
            "\u093f\U000114ab",
            "\U000114b1\U000114ab",
            1,
        ),
        (
            "\U000114ab\u093e\u0930\u094d",
            "\U000114ab\U000114b0\U000114a9\U000114c2",
            3,
        ),
        (
            "\u0935\U000114b0\u0930\u094d",
            "\U000114ab\U000114b0\U000114a9\U000114c2",
            3,
        ),
        (
            "\u0935\u093e\U000114a9\u094d",
            "\U000114ab\U000114b0\U000114a9\U000114c2",
            3,
        ),
        (
            "\u0935\u093e\u0930\U000114c2",
            "\U000114ab\U000114b0\U000114a9\U000114c2",
            3,
        ),
    ],
)
def test_mixed_native_tokens_disable_their_visual_repair_window(source, expected, replacements):
    _assert_clean_reorder(source, expected, replacements=replacements)


@pytest.mark.parametrize(
    ("source", "expected", "replacements"),
    [
        (
            "\u093f\u0915\U000114c3",
            "\U000114b1\U0001148f\U000114c3",
            2,
        ),
        (
            "\u093f\u0915\U000114c2\u0916",
            "\U000114b1\U0001148f\U000114c2\U00011490",
            3,
        ),
        (
            "\u093f\u0915\u094d\U00011490",
            "\U000114b1\U0001148f\U000114c2\U00011490",
            3,
        ),
        (
            "\u093f\u0915\u094d\u0916\U000114c3",
            "\U000114b1\U0001148f\U000114c2\U00011490\U000114c3",
            4,
        ),
    ],
)
def test_prebase_repair_rejects_native_cluster_continuations(source, expected, replacements):
    _assert_clean_reorder(source, expected, replacements=replacements)


def test_incomplete_derived_prebase_cluster_retains_existing_repair_behavior():
    _assert_clean_reorder(
        "\u093f\u0915\u094d",
        "\U0001148f\U000114b1\U000114c2",
        replacements=3,
        prebase_moves=1,
    )


def test_tirhuta_block_neighbors_suppress_derived_boundary_repairs():
    converter = TirhutaConverter()
    contract = converter._contract
    consonant_source = _singleton_source_by_target(converter, contract.consonants)
    i_source = _singleton_source_by_target(converter, frozenset({contract.prebase_i}))[
        contract.prebase_i
    ]
    virama_source = _singleton_source_by_target(converter, frozenset({contract.virama}))[
        contract.virama
    ]
    ra_source = consonant_source[contract.ra]

    for boundary in range(contract.block_lo, contract.block_hi + 1):
        for consonant in sorted(contract.consonants):
            source = "".join(
                chr(value) for value in (boundary, i_source, consonant_source[consonant])
            )
            result = converter.convert(source)
            assert result.unicode_text == unicodedata.normalize(
                "NFC",
                "".join(chr(value) for value in (boundary, contract.prebase_i, consonant)),
            )
            assert result.prebase_i_moves == 0

            source = "".join(
                chr(value)
                for value in (
                    consonant_source[consonant],
                    ra_source,
                    virama_source,
                    boundary,
                )
            )
            result = converter.convert(source)
            assert result.unicode_text == unicodedata.normalize(
                "NFC",
                "".join(
                    chr(value) for value in (consonant, contract.ra, contract.virama, boundary)
                ),
            )
            assert result.reph_moves == 0


def test_non_tirhuta_boundaries_allow_derived_repairs_and_logical_reph_is_unchanged():
    converter = TirhutaConverter()
    contract = converter._contract
    consonant_source = _singleton_source_by_target(converter, contract.consonants)
    i_source = _singleton_source_by_target(converter, frozenset({contract.prebase_i}))[
        contract.prebase_i
    ]
    virama_source = _singleton_source_by_target(converter, frozenset({contract.virama}))[
        contract.virama
    ]
    ra_source = consonant_source[contract.ra]

    for boundary in contract.passthrough:
        for consonant in sorted(contract.consonants):
            source = boundary + chr(i_source) + chr(consonant_source[consonant])
            _assert_clean_reorder(
                source,
                boundary + chr(consonant) + chr(contract.prebase_i),
                replacements=2,
                prebase_moves=1,
            )
            source = (
                chr(consonant_source[consonant]) + chr(ra_source) + chr(virama_source) + boundary
            )
            _assert_clean_reorder(
                source,
                chr(contract.ra) + chr(contract.virama) + chr(consonant) + boundary,
                replacements=3,
                reph_moves=1,
            )

    for consonant in sorted(contract.consonants):
        source = "".join(
            chr(value) for value in (ra_source, virama_source, consonant_source[consonant])
        )
        expected = "".join(chr(value) for value in (contract.ra, contract.virama, consonant))
        _assert_clean_reorder(source, expected, replacements=3)


def _contract_arguments() -> dict[str, object]:
    contract = TirhutaConverter()._contract
    return {
        "mapping": dict(contract.mapping),
        "passthrough": contract.passthrough,
        "consonants": contract.consonants,
        "dependents": contract.dependents,
        "prebase_i": contract.prebase_i,
        "ra": contract.ra,
        "virama": contract.virama,
        "nukta": contract.nukta,
        "block_lo": contract.block_lo,
        "block_hi": contract.block_hi,
        "provenance": contract.provenance,
    }


class _IntSubclass(int):
    pass


def _invalid_contract(case: str) -> dict[str, object]:
    values = _contract_arguments()
    mapping = dict(values["mapping"])
    first = min(mapping)
    if case == "mapping-type":
        values["mapping"] = list(mapping.items())
    elif case == "mapping-count":
        mapping.pop(first)
        values["mapping"] = mapping
    elif case == "source-inventory":
        mapping[0x090E] = mapping.pop(first)
        values["mapping"] = mapping
    elif case == "source-type":
        values["mapping"] = {
            _IntSubclass(source) if source == first else source: target
            for source, target in mapping.items()
        }
    elif case == "target-container":
        mapping[first] = list(mapping[first])
        values["mapping"] = mapping
    elif case == "target-empty":
        mapping[first] = ()
        values["mapping"] = mapping
    elif case == "target-long":
        mapping[first] = (0x11481, 0x114B0, 0x114B1)
        values["mapping"] = mapping
    elif case == "target-type":
        mapping[first] = (True,)
        values["mapping"] = mapping
    elif case == "target-surrogate":
        mapping[first] = (0xD800,)
        values["mapping"] = mapping
    elif case == "target-reserved":
        mapping[first] = (0x114C8,)
        values["mapping"] = mapping
    elif case == "target-cross-script":
        mapping[first] = (0x0905,)
        values["mapping"] = mapping
    elif case == "target-nfc":
        mapping[first] = (0x114B9, 0x114B0)
        values["mapping"] = mapping
    elif case == "duplicate-target":
        second = sorted(mapping)[1]
        mapping[first] = mapping[second]
        values["mapping"] = mapping
    elif case == "semantic-drift":
        first, second = sorted(source for source, target in mapping.items() if len(target) == 1)[:2]
        mapping[first], mapping[second] = mapping[second], mapping[first]
        values["mapping"] = mapping
    elif case == "passthrough-type":
        values["passthrough"] = set(values["passthrough"])
    elif case == "passthrough-count":
        values["passthrough"] = frozenset(set(values["passthrough"]) - {"~"})
    elif case == "passthrough-value":
        passthrough = set(values["passthrough"])
        passthrough.remove("~")
        passthrough.add("AB")
        values["passthrough"] = frozenset(passthrough)
    elif case == "passthrough-overlap":
        passthrough = set(values["passthrough"])
        passthrough.remove("~")
        passthrough.add(chr(first))
        values["passthrough"] = frozenset(passthrough)
    elif case == "passthrough-drift":
        passthrough = set(values["passthrough"])
        passthrough.remove("~")
        passthrough.add("$")
        values["passthrough"] = frozenset(passthrough)
    elif case == "consonants":
        values["consonants"] = frozenset(set(values["consonants"]) - {0x1148F})
    elif case == "dependents":
        values["dependents"] = frozenset(set(values["dependents"]) | {0x114C2})
    elif case == "scalar":
        values["prebase_i"] = 0x114B0
    elif case == "scalar-type":
        values["ra"] = _IntSubclass(values["ra"])
    elif case == "bounds":
        values["block_hi"] = 0x114E0
    elif case == "provenance":
        values["provenance"] = "all-input"
    else:  # pragma: no cover - test helper contract
        raise AssertionError(case)
    return values


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("mapping-type", "exactly 90"),
        ("mapping-count", "exactly 90"),
        ("source-inventory", "source inventory"),
        ("source-type", "mapping source"),
        ("target-container", "mapping target"),
        ("target-empty", "mapping target"),
        ("target-long", "mapping target"),
        ("target-type", "mapping target"),
        ("target-surrogate", "mapping target"),
        ("target-reserved", "mapping target"),
        ("target-cross-script", "mapping target"),
        ("target-nfc", "non-NFC"),
        ("duplicate-target", "unique sequences"),
        ("semantic-drift", "mapping payload"),
        ("passthrough-type", "exactly 49"),
        ("passthrough-count", "exactly 49"),
        ("passthrough-value", "passthrough value"),
        ("passthrough-overlap", "sources overlap"),
        ("passthrough-drift", "passthrough payload"),
        ("consonants", "consonant inventory"),
        ("dependents", "dependent inventory"),
        ("scalar", "reorder scalar"),
        ("scalar-type", "scalar type"),
        ("bounds", "block bounds"),
        ("provenance", "reorder provenance"),
    ],
)
def test_fixed_tirhuta_contract_validation_fails_closed(case, message):
    values = _invalid_contract(case)
    mapping = values.pop("mapping")
    with pytest.raises(ValueError, match=message):
        tirhuta_module._freeze_tirhuta_contract(mapping, **values)


def test_tirhuta_contract_and_default_instances_ignore_live_module_rebinding(monkeypatch):
    converter = TirhutaConverter()
    source = "\u093f\u0958?\U000114b1\U000114ab"
    expected = converter.convert(source)

    with pytest.raises(TypeError):
        tirhuta_module._DEVANAGARI_TO_TIRHUTA[0x0915] = ()
    with pytest.raises(TypeError):
        converter._contract.mapping[0x0915] = ()
    with pytest.raises(AttributeError):
        converter._contract.passthrough.add("A")
    with pytest.raises(AttributeError):
        converter._contract.consonants.add(0x11480)

    monkeypatch.setattr(tirhuta_module, "_DEVANAGARI_TO_TIRHUTA", {0x0915: ()})
    monkeypatch.setattr(tirhuta_module, "_PASSTHROUGH", frozenset("?"))
    monkeypatch.setattr(tirhuta_module, "_TIRHUTA_CONSONANTS", frozenset())
    monkeypatch.setattr(tirhuta_module, "_TIRHUTA_DEPENDENTS", frozenset())
    monkeypatch.setattr(tirhuta_module, "_TIRHUTA_PREBASE_I", 0)
    monkeypatch.setattr(tirhuta_module, "_TIRHUTA_RA", 0)
    monkeypatch.setattr(tirhuta_module, "_TIRHUTA_VIRAMA", 0)
    monkeypatch.setattr(tirhuta_module, "_TIRHUTA_NUKTA", 0)
    monkeypatch.setattr(tirhuta_module, "TIRHUTA_LO", 0)
    monkeypatch.setattr(tirhuta_module, "TIRHUTA_HI", 0x10FFFF)
    monkeypatch.setattr(tirhuta_module, "_TIRHUTA_REORDER_PROVENANCE", "all-input")

    assert converter.convert(source) == expected
    assert TirhutaConverter().convert(source) == expected
    assert convert_tirhuta(source) == expected


def test_tirhuta_logical_devanagari_and_visual_examples_remain_stable():
    result = convert_tirhuta("मैथिली")
    assert result.unicode_text == "𑒧𑒻𑒟𑒱𑒪𑒲"
    assert result.tirhuta_char_count == 6
    assert result.unicode_text == unicodedata.normalize("NFC", result.unicode_text)

    result = convert_tirhuta("िवदेह")
    assert result.unicode_text == "𑒫𑒱𑒠𑒹𑒯"
    assert result.prebase_i_moves == 1

    result = convert_tirhuta("वषर्")
    assert result.unicode_text == "𑒫𑒩𑓂𑒭"
    assert result.reph_moves == 1

    assert convert_tirhuta("वर्ष").unicode_text == "𑒫𑒩𑓂𑒭"
    assert convert_tirhuta("कर्म").unicode_text == "𑒏𑒩𑓂𑒧"


def test_tirhuta_unrecoverable_pdf_characters_are_surfaced():
    result = convert_tirhuta("क�")
    assert result.unicode_text.endswith("�")
    assert result.unmapped_codepoints == ["U+FFFD"]
    with pytest.raises(ValueError):
        convert_tirhuta("क�", strict=True)


@pytest.mark.parametrize("font", ["janaki", "tirhuta", "mithilakshar"])
def test_every_legacy_tirhuta_alias_uses_the_corrected_project_contract(font):
    assert convert("क", font=font, strict=True) == "𑒏"
    with pytest.raises(ValueError, match=r"U\+090E"):
        convert("\u090e", font=font, strict=True)


@pytest.mark.parametrize(
    "font",
    [
        "noto sans tirhuta",
        "noto-sans-tirhuta",
        "notosanstirhuta",
        "notosanstirhuta-regular",
        "tirhuta-unicode",
        "unicode-tirhuta",
    ],
)
def test_every_unicode_tirhuta_alias_preserves_native_reorder_shaped_text(font):
    source = "\U000114b1\U000114ab \U000114ab\U000114a9\U000114c2"
    assert convert(source, font=font, strict=True) == unicodedata.normalize("NFC", source)


def test_tirhuta_legacy_and_unicode_alias_inventories_are_immutable_and_disjoint():
    assert isinstance(package_module._TIRHUTA_FONTS, frozenset)
    assert isinstance(package_module._TIRHUTA_UNICODE_FONTS, frozenset)
    assert not package_module._TIRHUTA_FONTS & package_module._TIRHUTA_UNICODE_FONTS
    with pytest.raises(AttributeError):
        package_module._TIRHUTA_FONTS.add("forged")
    with pytest.raises(AttributeError):
        package_module._TIRHUTA_UNICODE_FONTS.add("forged")
