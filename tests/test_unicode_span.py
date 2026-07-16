"""Already-Unicode font-span routing tests."""

import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path
from types import MappingProxyType

import pytest

from nepal_ttf2utf import (
    _UNICODE_FONT_SCRIPTS,
    UNICODE_REPERTOIRE_VERSION,
    convert,
    supported_fonts,
    supported_unicode_scripts,
    validate_unicode_span,
)
from nepal_ttf2utf.limbu import convert_limbu
from nepal_ttf2utf.tirhuta import convert_tirhuta
from nepal_ttf2utf.unicode_span import (
    _ASSIGNED_BLOCK_RANGES,
    _PINNED_CANONICAL_COMBINING_CLASSES,
    _PINNED_CANONICAL_DECOMPOSITIONS,
    _PINNED_NORMALIZATION_PARTICIPANTS,
    _SCRIPT_BLOCK_RANGES,
    _SCRIPT_RANGES,
    _normalize_nfc,
    _pinned_combining_class,
)

_UNICODE17_SCRIPT_INVENTORY = {
    # assigned, Script-property, assigned Common/Inherited, reserved
    "Brahmi": (115, 115, 0, 13),
    "Devanagari": (213, 164, 49, 91),
    "Gurung Khema": (58, 58, 0, 6),
    "Kirat Rai": (58, 58, 0, 6),
    "Lepcha": (74, 74, 0, 6),
    "Limbu": (68, 68, 0, 12),
    "Newa": (97, 97, 0, 31),
    "Ol Chiki": (48, 48, 0, 0),
    "Sunuwar": (44, 44, 0, 20),
    "Tibetan": (211, 207, 4, 45),
    "Tirhuta": (82, 82, 0, 14),
}

_SCRIPT_ANCHORS = {
    "Brahmi": 0x11013,
    "Devanagari": 0x0915,
    "Gurung Khema": 0x16100,
    "Kirat Rai": 0x16D43,
    "Lepcha": 0x1C00,
    "Limbu": 0x1900,
    "Newa": 0x11400,
    "Ol Chiki": 0x1C5A,
    "Sunuwar": 0x11BC0,
    "Tibetan": 0x0F40,
    "Tirhuta": 0x11480,
}


def _expand_ranges(ranges):
    return {codepoint for start, end in ranges for codepoint in range(start, end + 1)}


@pytest.mark.parametrize(
    ("script", "codepoint"),
    [
        ("Brahmi", 0x11013),
        ("Devanagari", 0x0915),
        ("Gurung Khema", 0x16100),
        ("Kirat Rai", 0x16D43),
        ("Lepcha", 0x1C00),
        ("Limbu", 0x1900),
        ("Newa", 0x11400),
        ("Ol Chiki", 0x1C5A),
        ("Sunuwar", 0x11BC0),
        ("Tibetan", 0x0F40),
        ("Tirhuta", 0x11480),
    ],
)
def test_every_package_output_script_has_a_unicode_validator(script, codepoint):
    text = chr(codepoint)
    result = validate_unicode_span(text, script=script.lower(), strict=True)
    assert result.unicode_text == text
    assert result.script == script
    assert result.script_char_count == 1
    assert result.invalid_codepoints == []
    assert result.unexpected_script_codepoints == []


def test_unicode_repertoire_is_version_pinned_and_discoverable():
    assert UNICODE_REPERTOIRE_VERSION == "17.0.0"
    assert supported_unicode_scripts() == (
        "Brahmi",
        "Devanagari",
        "Gurung Khema",
        "Kirat Rai",
        "Lepcha",
        "Limbu",
        "Newa",
        "Ol Chiki",
        "Sunuwar",
        "Tibetan",
        "Tirhuta",
    )


@pytest.mark.parametrize(
    "table",
    (_ASSIGNED_BLOCK_RANGES, _SCRIPT_RANGES, _SCRIPT_BLOCK_RANGES),
)
def test_unicode_repertoire_range_tables_are_deeply_immutable(table):
    assert isinstance(table, MappingProxyType)
    assert all(
        isinstance(ranges, tuple)
        and all(
            isinstance(item, tuple)
            and len(item) == 2
            and all(isinstance(codepoint, int) for codepoint in item)
            for item in ranges
        )
        for ranges in table.values()
    )

    key = next(iter(table))
    original = table[key]
    with pytest.raises(TypeError):
        table[key] = ((0, 0),)
    with pytest.raises(TypeError):
        del table[key]
    assert table[key] is original


def test_unicode_font_alias_inventory_is_complete_and_hash_pinned():
    assert isinstance(_UNICODE_FONT_SCRIPTS, MappingProxyType)
    assert len(_UNICODE_FONT_SCRIPTS) == 100

    alias_payload = json.dumps(
        dict(_UNICODE_FONT_SCRIPTS), sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    assert len(alias_payload) == 3044
    assert hashlib.sha256(alias_payload).hexdigest() == (
        "a59cf6d6bff2cd2693bac77ea1fc50e74d7fa0d365528abcf5a460c178bad78f"
    )

    grouped = {
        script: sorted(
            alias
            for alias, routed_script in _UNICODE_FONT_SCRIPTS.items()
            if routed_script == script
        )
        for script in supported_unicode_scripts()
    }
    assert set(grouped) == set(_SCRIPT_ANCHORS)
    assert all(grouped.values())
    grouped_payload = json.dumps(grouped, sort_keys=True, separators=(",", ":")).encode("ascii")
    assert len(grouped_payload) == 2150
    assert hashlib.sha256(grouped_payload).hexdigest() == (
        "64bd004c6a18b827a7d9bf7e2ffc5f9dcf5e8b1d539b4315efa45b2f371d7403"
    )


def test_every_unicode_font_alias_strictly_routes_only_its_declared_script():
    checked = 0
    for alias, script in _UNICODE_FONT_SCRIPTS.items():
        source = chr(_SCRIPT_ANCHORS[script])
        assert convert(source, font=alias, strict=True) == source, (alias, script)

        other_script = next(candidate for candidate in _SCRIPT_ANCHORS if candidate != script)
        misrouted = chr(_SCRIPT_ANCHORS[other_script])
        with pytest.raises(ValueError, match="unexpected script characters"):
            convert(misrouted, font=alias, strict=True)
        checked += 1

    assert checked == 100


def test_every_unicode_font_alias_preserves_nfc_for_all_builtin_strict_values():
    checked = 0
    for alias, script in _UNICODE_FONT_SCRIPTS.items():
        source = chr(_SCRIPT_ANCHORS[script]) + " e\u0301"
        expected = chr(_SCRIPT_ANCHORS[script]) + " é"
        assert convert(source, font=alias) == expected, (alias, script)
        assert convert(source, font=alias, strict=False) == expected, (alias, script)
        assert convert(source, font=alias, strict=True) == expected, (alias, script)
        checked += 1

    assert checked == 100


def test_unicode_validator_rejects_invalid_strict_before_script_or_normalization(
    monkeypatch,
):
    def unexpected_work(*args, **kwargs):
        raise AssertionError("Unicode validation work ran before Boolean validation")

    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span._canonical_script_name",
        unexpected_work,
    )
    monkeypatch.setattr("nepal_ttf2utf.unicode_span._normalize_nfc", unexpected_work)
    with pytest.raises(ValueError, match=r"^strict must be a bool$"):
        validate_unicode_span("", script="Newa", strict=[])


def test_unicode17_contract_digest_and_complete_inventory():
    contract = {
        "version": UNICODE_REPERTOIRE_VERSION,
        "assigned": {
            script: [list(item) for item in ranges]
            for script, ranges in _ASSIGNED_BLOCK_RANGES.items()
        },
        "scripts": {
            script: [list(item) for item in ranges] for script, ranges in _SCRIPT_RANGES.items()
        },
        "blocks": {
            script: [list(item) for item in ranges]
            for script, ranges in _SCRIPT_BLOCK_RANGES.items()
        },
        "canonical_decompositions": [
            [composed, list(decomposed)]
            for composed, decomposed in _PINNED_CANONICAL_DECOMPOSITIONS.items()
        ],
        "canonical_combining_classes": [
            list(item) for item in _PINNED_CANONICAL_COMBINING_CLASSES.items()
        ],
    }
    payload = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("ascii")
    assert len(payload) == 1757
    assert hashlib.sha256(payload).hexdigest() == (
        "b34edb816eafd1b66ae5911d7e4120df1fd4a3d0a737a55e5a4e4f3077e7f469"
    )

    assert set(_ASSIGNED_BLOCK_RANGES) == set(_UNICODE17_SCRIPT_INVENTORY)
    assert set(_SCRIPT_RANGES) == set(_UNICODE17_SCRIPT_INVENTORY)
    assert set(_SCRIPT_BLOCK_RANGES) == set(_UNICODE17_SCRIPT_INVENTORY)
    assigned_total = specific_total = common_total = reserved_total = block_total = 0
    all_specific: set[int] = set()
    for script, expected_inventory in _UNICODE17_SCRIPT_INVENTORY.items():
        assigned = _expand_ranges(_ASSIGNED_BLOCK_RANGES[script])
        specific = _expand_ranges(_SCRIPT_RANGES[script])
        block = _expand_ranges(_SCRIPT_BLOCK_RANGES[script])
        assert specific <= assigned <= block
        inventory = (len(assigned), len(specific), len(assigned - specific), len(block - assigned))
        assert inventory == expected_inventory
        assert _SCRIPT_ANCHORS[script] in specific

        assigned_total += len(assigned)
        specific_total += len(specific)
        common_total += len(assigned - specific)
        reserved_total += len(block - assigned)
        block_total += len(block)
        all_specific.update(specific)

    assert (block_total, assigned_total, specific_total, common_total, reserved_total) == (
        1312,
        1068,
        1015,
        53,
        244,
    )
    assert len(all_specific) == specific_total
    assert len(_PINNED_CANONICAL_DECOMPOSITIONS) == 11
    assert Counter(map(len, _PINNED_CANONICAL_DECOMPOSITIONS.values())) == {2: 11}
    assert _PINNED_CANONICAL_COMBINING_CLASSES == {0x1612F: 9}
    assert _PINNED_NORMALIZATION_PARTICIPANTS == frozenset(
        {
            *range(0x1611E, 0x1612A),
            0x1612F,
            0x16D63,
            *range(0x16D67, 0x16D6B),
        }
    )


def test_every_assigned_unicode17_position_has_exact_validator_behavior():
    nfc_expansions: Counter[str] = Counter()
    for script in _UNICODE17_SCRIPT_INVENTORY:
        assigned = _expand_ranges(_ASSIGNED_BLOCK_RANGES[script])
        specific = _expand_ranges(_SCRIPT_RANGES[script])
        anchor = chr(_SCRIPT_ANCHORS[script])
        for codepoint in sorted(assigned):
            source = chr(codepoint)
            expected = unicodedata.normalize("NFC", source)
            result = validate_unicode_span(source, script=script)

            assert result.unicode_text == expected, (script, f"U+{codepoint:04X}")
            assert result.invalid_codepoints == [], (script, f"U+{codepoint:04X}")
            assert result.unexpected_script_codepoints == [], (script, f"U+{codepoint:04X}")
            assert result.script_char_count == sum(ord(char) in specific for char in expected), (
                script,
                f"U+{codepoint:04X}",
            )

            if expected != source:
                assert len(expected) == 2
                nfc_expansions[script] += 1

            if codepoint in specific:
                strict_result = validate_unicode_span(source, script=script, strict=True)
                assert strict_result.unicode_text == expected
            else:
                assert result.script_char_count == 0
                with pytest.raises(ValueError, match=rf"contains no {script}"):
                    validate_unicode_span(source, script=script, strict=True)
                anchored = validate_unicode_span(anchor + " " + source, script=script, strict=True)
                assert anchored.script_char_count == 1
                assert anchored.invalid_codepoints == []
                assert anchored.unexpected_script_codepoints == []

    assert nfc_expansions == {"Devanagari": 8, "Tibetan": 17}


def test_every_reserved_unicode17_position_is_preserved_labeled_and_rejected():
    checked = 0
    for script in _UNICODE17_SCRIPT_INVENTORY:
        assigned = _expand_ranges(_ASSIGNED_BLOCK_RANGES[script])
        reserved = _expand_ranges(_SCRIPT_BLOCK_RANGES[script]) - assigned
        for codepoint in sorted(reserved):
            source = chr(codepoint)
            label = f"U+{codepoint:04X}"
            result = validate_unicode_span(source, script=script)

            assert result.unicode_text == source, (script, label)
            assert result.script_char_count == 0, (script, label)
            assert result.invalid_codepoints == [label], (script, label)
            assert result.unexpected_script_codepoints == [], (script, label)
            with pytest.raises(ValueError, match=label.replace("+", r"\+")):
                validate_unicode_span(source, script=script, strict=True)
            checked += 1

    assert checked == 244


def test_reserved_positions_remain_invalid_if_the_runtime_reports_them_assigned(monkeypatch):
    monkeypatch.setattr("nepal_ttf2utf.unicode_span.unicodedata.category", lambda _char: "Lo")

    checked = 0
    for script in _UNICODE17_SCRIPT_INVENTORY:
        assigned = _expand_ranges(_ASSIGNED_BLOCK_RANGES[script])
        reserved = _expand_ranges(_SCRIPT_BLOCK_RANGES[script]) - assigned
        for codepoint in sorted(reserved):
            label = f"U+{codepoint:04X}"
            result = validate_unicode_span(chr(codepoint), script=script)
            assert result.invalid_codepoints == [label], (script, label)
            with pytest.raises(ValueError, match=label.replace("+", r"\+")):
                validate_unicode_span(chr(codepoint), script=script, strict=True)
            checked += 1

    assert checked == 244


def test_every_assigned_position_is_independent_of_runtime_assignment(monkeypatch):
    assigned_all = set().union(
        *(_expand_ranges(ranges) for ranges in _ASSIGNED_BLOCK_RANGES.values())
    )
    original_category = unicodedata.category

    def old_runtime_category(char):
        return "Cn" if ord(char) in assigned_all else original_category(char)

    monkeypatch.setattr("nepal_ttf2utf.unicode_span.unicodedata.category", old_runtime_category)

    checked = 0
    for script in _UNICODE17_SCRIPT_INVENTORY:
        assigned = _expand_ranges(_ASSIGNED_BLOCK_RANGES[script])
        specific = _expand_ranges(_SCRIPT_RANGES[script])
        anchor = chr(_SCRIPT_ANCHORS[script])
        for codepoint in sorted(assigned):
            result = validate_unicode_span(chr(codepoint), script=script)
            assert result.invalid_codepoints == [], (script, f"U+{codepoint:04X}")
            if codepoint in specific:
                validate_unicode_span(chr(codepoint), script=script, strict=True)
            else:
                validate_unicode_span(anchor + " " + chr(codepoint), script=script, strict=True)
            checked += 1

    assert checked == 1068


def test_every_script_specific_position_is_rejected_by_every_other_script_route():
    checked = 0
    for source_script in _UNICODE17_SCRIPT_INVENTORY:
        specific = _expand_ranges(_SCRIPT_RANGES[source_script])
        for codepoint in sorted(specific):
            source = chr(codepoint)
            normalized = unicodedata.normalize("NFC", source)
            expected_labels = sorted({f"U+{ord(char):04X}" for char in normalized})
            for target_script in _UNICODE17_SCRIPT_INVENTORY:
                if target_script == source_script:
                    continue
                result = validate_unicode_span(source, script=target_script)
                label = (source_script, target_script, f"U+{codepoint:04X}")

                assert result.unicode_text == normalized, label
                assert result.script_char_count == 0, label
                assert result.invalid_codepoints == [], label
                assert result.unexpected_script_codepoints == expected_labels, label
                with pytest.raises(
                    ValueError,
                    match=rf"unexpected script characters in Unicode {target_script}",
                ):
                    validate_unicode_span(source, script=target_script, strict=True)
                checked += 1

    assert checked == 10150


def test_new_unicode_scripts_do_not_depend_on_the_python_unicode_database(monkeypatch):
    original_category = unicodedata.category
    newer_codepoints = {0x11B00, 0x11BC0, 0x16100, 0x16D40}

    def old_runtime_category(char):
        if ord(char) in newer_codepoints:
            return "Cn"
        return original_category(char)

    monkeypatch.setattr("nepal_ttf2utf.unicode_span.unicodedata.category", old_runtime_category)
    for script, codepoint in (
        ("Devanagari", 0x11B00),
        ("Sunuwar", 0x11BC0),
        ("Gurung Khema", 0x16100),
        ("Kirat Rai", 0x16D40),
    ):
        result = validate_unicode_span(chr(codepoint), script=script, strict=True)
        assert result.script_char_count == 1
        assert result.invalid_codepoints == []


@pytest.mark.parametrize(
    ("script", "decomposed", "composed"),
    [
        ("Gurung Khema", "\U0001611e\U0001611e", "\U00016121"),
        ("Gurung Khema", "\U0001611e\U0001611e\U0001611f", "\U00016126"),
        ("Kirat Rai", "\U00016d67\U00016d67", "\U00016d68"),
        ("Kirat Rai", "\U00016d63\U00016d67\U00016d67", "\U00016d6a"),
    ],
)
def test_unicode16_nfc_composition_is_version_stable(script, decomposed, composed, monkeypatch):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )
    assert validate_unicode_span(decomposed, script=script, strict=True).unicode_text == composed


def test_every_pinned_unicode16_composition_is_version_stable(monkeypatch):
    monkeypatch.setattr(
        "nepal_ttf2utf.unicode_span.unicodedata.normalize", lambda _form, text: text
    )

    seen_targets = set()
    for codepoint, decomposition in _PINNED_CANONICAL_DECOMPOSITIONS.items():
        decomposed = "".join(chr(value) for value in decomposition)
        composed = chr(codepoint)
        script = "Gurung Khema" if 0x16100 <= codepoint <= 0x1613F else "Kirat Rai"
        result = validate_unicode_span(decomposed, script=script, strict=True)

        assert len(composed) == 1
        assert result.unicode_text == composed
        assert result.script_char_count == 1
        assert result.invalid_codepoints == []
        assert result.unexpected_script_codepoints == []
        seen_targets.add(composed)

    assert len(seen_targets) == 11


def test_unicode17_gurung_khema_kirat_rai_normalization_subset_is_exact():
    fixture = Path(__file__).with_name("unicode17_gurung_khema_kirat_rai_normalization.json")
    rows = json.loads(fixture.read_bytes())
    payload = json.dumps(rows, ensure_ascii=True, separators=(",", ":")).encode("ascii")

    assert len(rows) == 58
    assert len(payload) == 5277
    assert hashlib.sha256(payload).hexdigest() == (
        "dc014a9cd66314219defd47ac3a462f91c60597e7e464f50071f86d8d345115f"
    )
    assert all(
        type(row) is list
        and len(row) == 5
        and all(
            type(column) is list
            and column
            and all(type(codepoint) is int and 0 <= codepoint <= 0x10FFFF for codepoint in column)
            for column in row
        )
        for row in rows
    )

    equalities = 0
    for row_index, row in enumerate(rows):
        columns = ["".join(chr(codepoint) for codepoint in column) for column in row]
        expected = (columns[1], columns[1], columns[1], columns[3], columns[3])
        for column_index, (source, target) in enumerate(zip(columns, expected)):
            assert _normalize_nfc(source) == target, (row_index, column_index)
            assert _normalize_nfc(target) == target, (row_index, column_index)
            equalities += 1

    assert equalities == 290


def test_pinned_unicode16_normalization_tables_are_immutable():
    with pytest.raises(TypeError):
        _PINNED_CANONICAL_DECOMPOSITIONS[0x16121] = (0x1611E, 0x1611F)
    with pytest.raises(TypeError):
        _PINNED_CANONICAL_COMBINING_CLASSES[0x1612F] = 0
    with pytest.raises(AttributeError):
        _PINNED_NORMALIZATION_PARTICIPANTS.add(0x16130)


@pytest.mark.parametrize(
    ("script", "source", "expected"),
    [
        (
            "Gurung Khema",
            "\U00016100\u0300\U0001612f",
            "\U00016100\U0001612f\u0300",
        ),
        ("Gurung Khema", "\U0001611e\U00016123", "\U00016126"),
        ("Kirat Rai", "\U00016d63\U00016d68", "\U00016d6a"),
    ],
)
def test_unicode16_nfc_canonical_order_and_composition_closure(script, source, expected):
    result = validate_unicode_span(source, script=script, strict=True)
    assert result.unicode_text == expected
    assert result.invalid_codepoints == []
    assert result.unexpected_script_codepoints == []
    assert _normalize_nfc(result.unicode_text) == result.unicode_text


def test_tholhoma_uses_pinned_combining_class_and_unicode_blocking_rules():
    assert unicodedata.combining("\U0001612f") in {0, 9}
    assert _pinned_combining_class(0x1612F) == 9

    source = "A\U0001612f\u030a"
    assert _normalize_nfc(source) == "\u00c5\U0001612f"

    blocked = "A\U0001612f\u0301\u030a"
    assert _normalize_nfc(blocked) == "\u00c1\U0001612f\u030a"

    source_order = (0x05B0, 0x1612F, 0x094D, 0x093C)
    expected_order = (0x093C, 0x1612F, 0x094D, 0x05B0)
    assert tuple(_pinned_combining_class(codepoint) for codepoint in expected_order) == (
        7,
        9,
        9,
        10,
    )
    mixed = "\U00016100" + "".join(chr(codepoint) for codepoint in source_order)
    assert _normalize_nfc(mixed) == "\U00016100" + "".join(
        chr(codepoint) for codepoint in expected_order
    )


def test_unicode16_fallback_retains_post_normalization_diagnostics():
    source = "\U00016100\u0300\U0001612f\ud800\U0001613a\ue000\ufdd0"
    result = validate_unicode_span(source, script="Gurung Khema")

    assert result.unicode_text.startswith("\U00016100\U0001612f\u0300")
    assert result.invalid_codepoints == ["U+1613A", "U+D800", "U+E000", "U+FDD0"]
    assert result.unexpected_script_codepoints == []
    with pytest.raises(ValueError, match=r"U\+1613A.*U\+D800.*U\+E000.*U\+FDD0"):
        validate_unicode_span(source, script="Gurung Khema", strict=True)


def test_reserved_codepoint_in_a_supported_block_is_rejected():
    source = chr(0x1613A)
    result = validate_unicode_span(source, script="Gurung Khema")
    assert result.invalid_codepoints == ["U+1613A"]
    with pytest.raises(ValueError, match=r"U\+1613A"):
        validate_unicode_span(source, script="Gurung Khema", strict=True)


@pytest.mark.parametrize("codepoint", [0xE000, 0xF8FF, 0xF0000, 0xFFFFD, 0x100000, 0x10FFFD])
def test_unicode_span_reports_private_use_values(codepoint):
    source = "𑐣" + chr(codepoint)
    result = validate_unicode_span(source, script="Newa")
    assert result.invalid_codepoints == [f"U+{codepoint:04X}"]
    with pytest.raises(ValueError, match=f"U\\+{codepoint:04X}"):
        validate_unicode_span(source, script="Newa", strict=True)


def test_unicode_span_reports_a_supported_but_misrouted_script():
    result = validate_unicode_span("𑐣म", script="Newa")
    assert result.script_char_count == 1
    assert result.unexpected_script_codepoints == ["U+092E"]
    with pytest.raises(ValueError, match=r"U\+092E.*Devanagari"):
        validate_unicode_span("𑐣म", script="Newa", strict=True)


def test_unicode_span_allows_embedded_latin_digits_and_punctuation():
    text = "𑐣 Newa 2026!"
    assert validate_unicode_span(text, script="Newa", strict=True).unicode_text == text


def test_shared_indic_dandas_are_not_attributed_exclusively_to_devanagari():
    tirhuta = convert_tirhuta("क।", strict=True).unicode_text
    assert validate_unicode_span(tirhuta, script="Tirhuta", strict=True).unicode_text == tirhuta

    limbu = convert_limbu("k.", strict=True)
    assert limbu.endswith("॥")
    assert validate_unicode_span(limbu, script="Limbu", strict=True).unicode_text == limbu


def test_common_tibetan_block_symbols_are_not_attributed_to_tibetan_script():
    text = "𑐣\u0fd5"
    assert validate_unicode_span(text, script="Newa", strict=True).unicode_text == text
    assert validate_unicode_span("ཀ\u0fd5", script="Tibetan", strict=True).unicode_text == "ཀ\u0fd5"
    with pytest.raises(ValueError, match="contains no Tibetan"):
        validate_unicode_span("\u0fd5", script="Tibetan", strict=True)


SCX_POLICY_SAMPLES = "\u02bc\u0300\u0951\u0952\u0965\u1cd1\u20f0\u3008\u300b"


def test_script_extensions_are_not_a_negative_script_allowlist():
    # U+1CD1 has the singleton Script_Extensions value Deva; other samples have
    # target-omitting or multi-script associations. None is exclusive ownership.
    for script, base in (("Newa", "𑐣"), ("Tibetan", "ཀ")):
        result = validate_unicode_span(base + SCX_POLICY_SAMPLES, script=script, strict=True)
        assert result.script_char_count == 1
        assert result.unexpected_script_codepoints == []


def test_script_extensions_do_not_anchor_native_script_presence():
    result = validate_unicode_span(SCX_POLICY_SAMPLES, script="Newa")
    assert result.script_char_count == 0
    with pytest.raises(ValueError, match="contains no Newa"):
        validate_unicode_span(SCX_POLICY_SAMPLES, script="Newa", strict=True)


def test_runtime_unassigned_detection_remains_strict_outside_pinned_blocks():
    source = "𑐣\u0378"
    result = validate_unicode_span(source, script="Newa")
    assert result.invalid_codepoints == ["U+0378"]
    with pytest.raises(ValueError, match=r"U\+0378"):
        validate_unicode_span(source, script="Newa", strict=True)


@pytest.mark.parametrize("codepoint", [0xFDD0, 0xFFFE, 0x1FFFE, 0x10FFFF])
def test_unicode_noncharacters_are_always_invalid(codepoint):
    source = "𑐣" + chr(codepoint)
    result = validate_unicode_span(source, script="Newa")
    assert result.invalid_codepoints == [f"U+{codepoint:04X}"]
    with pytest.raises(ValueError, match=f"U\\+{codepoint:04X}"):
        validate_unicode_span(source, script="Newa", strict=True)


def _assert_complete_invalid_inventory(codepoints):
    anchor = "𑐀"
    source = anchor + "".join(chr(codepoint) for codepoint in codepoints)
    result = validate_unicode_span(source, script="Newa")

    assert result.unicode_text == source
    assert result.script_char_count == 1
    assert result.invalid_codepoints == sorted(f"U+{codepoint:04X}" for codepoint in codepoints)
    assert result.unexpected_script_codepoints == []
    with pytest.raises(ValueError, match="invalid characters in Unicode Newa span"):
        validate_unicode_span(source, script="Newa", strict=True)


def test_every_disallowed_c0_del_and_c1_control_is_invalid():
    disallowed_controls = (
        *range(0x00, 0x09),
        0x0B,
        0x0C,
        *range(0x0E, 0x20),
        0x7F,
        *range(0x80, 0xA0),
    )
    assert len(disallowed_controls) == 62
    _assert_complete_invalid_inventory(disallowed_controls)

    allowed = validate_unicode_span("𑐀\t\n\r", script="Newa", strict=True)
    assert allowed.unicode_text == "𑐀\t\n\r"
    assert allowed.invalid_codepoints == []


def test_every_surrogate_is_invalid():
    surrogates = tuple(range(0xD800, 0xE000))
    assert len(surrogates) == 2048
    _assert_complete_invalid_inventory(surrogates)


def test_every_unicode_noncharacter_is_invalid():
    noncharacters = (
        *range(0xFDD0, 0xFDF0),
        *(plane * 0x10000 + tail for plane in range(17) for tail in (0xFFFE, 0xFFFF)),
    )
    assert len(noncharacters) == 66
    assert len(set(noncharacters)) == 66
    _assert_complete_invalid_inventory(noncharacters)


def test_unicode_tibetan_font_families_are_normalized_without_legacy_mapping():
    text = "བོད་ཡིག"
    for font in (
        "monlam-unicode",
        "MonlamUniOuChan5",
        "microsoft-himalaya",
        "qomolangma-title",
        "jomolhari",
        "Jomolhari-ID",
        "Qomolangma-Uchen-Suring",
        "CTRC-HT",
    ):
        assert convert(text, font=font, strict=True) == text


def test_unicode_newa_font_families_are_normalized_without_legacy_mapping():
    text = "𑐣𑐾𑐥𑐵𑐮"
    assert convert(text, font="newa-unicode", strict=True) == text
    assert convert(text, font="Noto Sans Newa", strict=True) == text
    assert convert(text, font="Nithya Ranjana NU", strict=True) == text


@pytest.mark.parametrize(
    ("font", "text"),
    [
        ("Namdhinggo-Regular", "ᤀ"),
        ("NotoSansLimbu-Regular", "ᤀ"),
        ("Kanchenjunga-Regular", "𖵃"),
        ("NotoSansSunuwar-Regular", "𑯀"),
        ("Mingzat-Regular", "ᰀ"),
        ("NotoSansLepcha-Regular", "ᰀ"),
        ("NotoSansOlChiki-Regular", "ᱚ"),
        ("NotoSansTirhuta-Regular", "𑒀"),
        ("NotoSansGurungKhema", "𖄀"),
        ("NotoSansDevanagari-Regular", "म"),
        ("NotoSerifDevanagari-Regular", "म"),
        ("NotoSansNewa-Regular", "𑐣"),
    ],
)
def test_modern_native_unicode_font_families_are_identity_routed(font, text):
    assert convert(text, font=font, strict=True) == text


def test_modern_namdhinggo_route_is_distinct_from_legacy_namdhinggo():
    assert convert("k", font="namdhinggo") != "k"
    with pytest.raises(ValueError, match="contains no Limbu"):
        convert("k", font="namdhinggo-unicode", strict=True)


def test_unicode_devanagari_and_ranjana_du_fonts_are_identity_routed():
    text = "मगर नेपाल"
    assert convert(text, font="AnnapurnaSILNepal", strict=True) == text
    assert convert(text, font="Nithya Ranjana DU", strict=True) == text


def test_madan2_exact_name_routes_unicode_devanagari_without_a_legacy_pass():
    source = "नेपाल क्षेत्र e\u0301 २०८३।"
    expected = unicodedata.normalize("NFC", source)
    assert convert(source, font="Madan2", strict=True) == expected
    assert convert(source, font="  mAdAn2  ", strict=True) == expected
    assert convert(source, font="ABCDEF+Madan2", strict=True) == expected
    assert convert("g]kfn", font="Madan2") == "g]kfn"


def test_madan2_strict_route_rejects_unanchored_invalid_and_misrouted_text():
    with pytest.raises(ValueError, match="contains no Devanagari"):
        convert("g]kfn", font="Madan2", strict=True)
    with pytest.raises(ValueError, match=r"U\+11400.*Newa"):
        convert("म𑐀", font="Madan2", strict=True)
    with pytest.raises(ValueError, match=r"U\+11480.*Tirhuta"):
        convert("म𑒀", font="Madan2", strict=True)
    with pytest.raises(ValueError, match=r"U\+FFFD"):
        convert("म�", font="Madan2", strict=True)
    with pytest.raises(ValueError, match=r"U\+11B0A"):
        convert("म\U00011b0a", font="Madan2", strict=True)


@pytest.mark.parametrize(
    "font",
    ["madan", "madan.ttf", "madan2-regular", "Madan2 Regular", "ABCDE+Madan2"],
)
def test_madan2_route_does_not_infer_unsupported_names(font):
    with pytest.raises(ValueError, match="unsupported font key"):
        convert("नेपाल", font=font, strict=True)


def test_pdf_subset_prefix_is_removed_before_font_routing():
    assert convert("བོད", font="ABCDEF+Jomolhari-ID", strict=True) == "བོད"
    assert convert("नेपाल", font="ABCDEF+AnnapurnaSILNepal", strict=True) == "नेपाल"


def test_unicode_span_reports_replacement_characters():
    result = validate_unicode_span("བ�", script="Tibetan")
    assert result.invalid_codepoints == ["U+FFFD"]
    with pytest.raises(ValueError, match=r"U\+FFFD"):
        validate_unicode_span("བ�", script="Tibetan", strict=True)


def test_strict_unicode_span_rejects_a_misrouted_nonempty_span():
    with pytest.raises(ValueError, match="contains no Newa"):
        convert("legacy ASCII", font="newa", strict=True)


def test_unicode_fonts_are_discoverable():
    fonts = supported_fonts()
    assert fonts["monlam-unicode"] == "Tibetan"
    assert fonts["microsoft-himalaya"] == "Tibetan"
    assert fonts["newa-unicode"] == "Newa"
    assert fonts["annapurnasilnepal"] == "Devanagari"
    assert fonts["madan2"] == "Devanagari"
    assert "madan" not in fonts
    assert "madan2-regular" not in fonts
    assert fonts["nithyaranjanadu"] == "Devanagari"
    assert fonts["nithyaranjananu"] == "Newa"
    assert fonts["namdhinggo-regular"] == "Limbu"
    assert fonts["kanchenjunga-regular"] == "Kirat Rai"
    assert fonts["notosanssunuwar-regular"] == "Sunuwar"
    assert fonts["notosanslepcha-regular"] == "Lepcha"
    assert fonts["notosansolchiki-regular"] == "Ol Chiki"
    assert fonts["notosanstirhuta-regular"] == "Tirhuta"
    assert fonts["notosansgurungkhema"] == "Gurung Khema"
