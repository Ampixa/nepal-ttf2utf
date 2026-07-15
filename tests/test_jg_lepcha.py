"""SIL JG Lepcha legacy-font conversion tests."""

import hashlib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from importlib import resources
from itertools import product, repeat
from types import MappingProxyType

import pytest

import nepal_ttf2utf as package_module
from nepal_ttf2utf import convert, convert_jg_lepcha
from nepal_ttf2utf._controls import DIAGNOSTIC_C0
from nepal_ttf2utf.jg_lepcha import JGLepchaConverter, _ReorderRule
from nepal_ttf2utf.unicode_span import _is_assigned_script_codepoint


class _InfiniteItemsMapping(Mapping):
    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 1

    def items(self):
        return repeat(("Cons", (0x1C00,)))


def _functional_payload(converter: JGLepchaConverter) -> bytes:
    context = converter._context_rule
    return json.dumps(
        {
            "byte_rules": [
                [list(source), list(target)] for source, target in converter._byte_rules
            ],
            "context_rule": (
                [context[0], sorted(context[1]), context[2]] if context is not None else None
            ),
            "reorder_rules": [
                [
                    [list(slot) for slot in rule.slots],
                    list(rule.output_vars),
                ]
                for rule in converter._reorder_rules
            ],
            "uncertain_sources": sorted(converter._uncertain_source_codepoints),
            "unicode_classes": [
                [name, sorted(members)]
                for name, members in sorted(converter._unicode_classes.items())
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _singleton_legacy_source_by_target(converter: JGLepchaConverter) -> dict[int, str]:
    result: dict[int, str] = {}
    for source, target in converter._byte_rules:
        if len(source) != 1 or len(target) != 1 or source[0] == 0x61:
            continue
        result.setdefault(target[0], chr(source[0]))
    assert all(set(members) & set(result) for members in converter._unicode_classes.values())
    return result


def test_jg_lepcha_map_matches_the_pinned_sil_source_and_parser_inventory():
    map_resource = resources.files("nepal_ttf2utf.maps") / "JGLepcha.map"
    map_bytes = map_resource.read_bytes()
    assert len(map_bytes) == 11600
    assert len(map_bytes.decode("utf-8-sig").splitlines()) == 272
    assert hashlib.sha256(map_bytes).hexdigest() == (
        "179d172b4bd4223f40b1ddc1a0daeb6547b5ad97dc1be7df2b09f2bf45ff6b2d"
    )

    converter = JGLepchaConverter.default()
    assert len(converter._byte_rules) == 160
    assert len({source for source, _target in converter._byte_rules}) == 160
    assert Counter(len(source) for source, _target in converter._byte_rules) == {1: 160}
    assert Counter(len(target) for _source, target in converter._byte_rules) == {
        1: 105,
        2: 47,
        3: 8,
    }
    assert len(converter._reorder_rules) == 72
    assert Counter(len(rule.slots) for rule in converter._reorder_rules) == {
        2: 5,
        3: 20,
        4: 28,
        5: 16,
        6: 3,
    }
    exact_reorder_counts = Counter(
        (rule.slots, rule.output_vars) for rule in converter._reorder_rules
    )
    assert len(exact_reorder_counts) == 68
    assert Counter(exact_reorder_counts.values()) == {1: 64, 2: 4}
    assert len(converter._unicode_classes) == 11
    assert {name: len(members) for name, members in converter._unicode_classes.items()} == {
        "AfterDepVow": 4,
        "AfterFCS": 7,
        "Cons": 36,
        "DepVow": 7,
        "FCS": 9,
        "InitDepVow": 3,
        "InitFCS": 2,
        "Nukta": 1,
        "Ra": 1,
        "Ran": 1,
        "Ya": 1,
    }
    assert converter._context_rule == (
        0x61,
        frozenset({0x61, 0x4F, 0x69, 0x6F, 0x75, 0x55, 0x65}),
        0x1C26,
    )
    assert converter._uncertain_source_codepoints == frozenset({0x3C, 0x3D, 0x3E})
    assert isinstance(converter._byte_rules, tuple)
    assert isinstance(converter._reorder_rules, tuple)
    assert isinstance(converter._unicode_classes, MappingProxyType)
    assert converter._contract.reorder_provenance == "legacy-byte-derived-only"
    payload = _functional_payload(converter)
    assert len(payload) == 8730
    assert hashlib.sha256(payload).hexdigest() == (
        "18b020ec8f679ae35f00b0354610a8f41391e5da19d5fbcc6ab727c041bfc2a1"
    )


def test_every_jg_lepcha_byte_rule_has_exact_isolated_behavior():
    converter = JGLepchaConverter.default()
    for source, target in converter._byte_rules:
        source_byte = source[0]
        expected_target = (0x1C26,) if source_byte == 0x61 else target
        expected = unicodedata.normalize(
            "NFC", "".join(chr(codepoint) for codepoint in expected_target)
        )
        result = converter.convert(chr(source_byte))
        mapped, derived, *_metadata = converter._byte_pass_with_provenance(chr(source_byte))
        label = f"U+{source_byte:04X}"

        assert mapped == "".join(chr(codepoint) for codepoint in expected_target), label
        assert derived == (True,) * len(mapped), label
        assert result.unicode_text == expected, label
        assert result.lepcha_char_count == sum(
            0x1C00 <= ord(character) <= 0x1C4F for character in expected
        ), label
        assert result.replacement_count == 1, label
        assert result.unmapped_codepoints == (
            [label] if chr(source_byte) in DIAGNOSTIC_C0 else []
        ), label
        assert result.uncertain_codepoints == (
            [label] if source_byte in converter._uncertain_source_codepoints else []
        ), label


def test_every_single_byte_has_an_explicit_jg_lepcha_classification():
    converter = JGLepchaConverter.default()
    byte_map = {source[0]: target for source, target in converter._byte_rules}
    classification_counts: Counter[str] = Counter()

    for source in range(0x100):
        character = chr(source)
        label = f"U+{source:04X}"
        result = converter.convert(character)
        mapped, derived, *_metadata = converter._byte_pass_with_provenance(character)
        if source in byte_map:
            expected_target = (0x1C26,) if source == 0x61 else byte_map[source]
            expected = unicodedata.normalize(
                "NFC", "".join(chr(codepoint) for codepoint in expected_target)
            )
            assert result.unicode_text == expected, label
            assert derived == (True,) * len(mapped), label
            assert result.replacement_count == 1, label
            assert result.lepcha_char_count == sum(
                0x1C00 <= ord(output) <= 0x1C4F for output in expected
            ), label
            if source in converter._uncertain_source_codepoints:
                classification = "uncertain"
                assert result.unmapped_codepoints == [], label
                assert result.uncertain_codepoints == [label], label
            elif character in DIAGNOSTIC_C0:
                classification = "diagnostic-control"
                assert result.unmapped_codepoints == [label], label
                assert result.uncertain_codepoints == [], label
            else:
                classification = "clean"
                assert result.unmapped_codepoints == [], label
                assert result.uncertain_codepoints == [], label
        else:
            classification = "unmapped"
            assert result.unicode_text == character, label
            assert derived == (False,), label
            assert result.lepcha_char_count == 0, label
            assert result.replacement_count == 0, label
            assert result.unmapped_codepoints == [label], label
            assert result.uncertain_codepoints == [], label
        classification_counts[classification] += 1

        if classification == "clean":
            assert convert_jg_lepcha(character, strict=True) == result
        else:
            with pytest.raises(ValueError, match=re.escape(label)):
                convert_jg_lepcha(character, strict=True)

    assert classification_counts == {
        "clean": 128,
        "diagnostic-control": 29,
        "uncertain": 3,
        "unmapped": 96,
    }


def test_complete_byte_aggregate_retains_the_pinned_legacy_output():
    source = "".join(chr(codepoint) for codepoint in range(0x100))
    result = JGLepchaConverter.default().convert(source)
    assert len(result.unicode_text) == 319
    assert result.lepcha_char_count == 186
    assert result.replacement_count == 160
    assert len(result.unmapped_codepoints) == 125
    assert result.uncertain_codepoints == ["U+003C", "U+003D", "U+003E"]
    assert hashlib.sha256(result.unicode_text.encode("utf-8")).hexdigest() == (
        "2f9413d6d9a14c8f2c4f76aa2585094bb711d25a9c5c14297a8ad5b1be3568c2"
    )


def test_jg_lepcha_context_rule_decision_is_exhaustive_over_previous_bytes():
    converter = JGLepchaConverter.default()
    assert converter._byte_pass("a")[0] == "ᰦ"
    excluded_previous = converter._context_rule[1]  # type: ignore[index]
    for previous in range(0x100):
        mapped, _replacements, _unmapped, _uncertain = converter._byte_pass(chr(previous) + "a")
        expected = 0x1C28 if previous in excluded_previous else 0x1C26
        assert ord(mapped[-1]) == expected, f"previous byte 0x{previous:02X}"


def test_every_jg_lepcha_reorder_rule_performs_its_exact_permutation():
    converter = JGLepchaConverter.default()
    for rule in converter._reorder_rules:
        bound: dict[str, str] = {}
        source: list[str] = []
        for class_name, variable in rule.slots:
            character = chr(min(converter._unicode_classes[class_name]))
            source.append(character)
            bound[variable] = character
        expected = "".join(bound[variable] for variable in rule.output_vars)
        isolated = JGLepchaConverter(
            [((0x41,), (0x1C00,))],
            [rule],
            converter._unicode_classes,
            None,
        )
        assert isolated._reorder_pass("".join(source)) == expected, rule


def test_every_jg_lepcha_reorder_class_product_is_provenance_safe():
    converter = JGLepchaConverter.default()
    exercised = 0
    for rule in converter._reorder_rules:
        member_axes = [sorted(converter._unicode_classes[name]) for name, _variable in rule.slots]
        for values in product(*member_axes):
            source = "".join(chr(value) for value in values)
            bound = {
                variable: chr(value) for (_class_name, variable), value in zip(rule.slots, values)
            }
            expected = "".join(bound[variable] for variable in rule.output_vars)
            assert converter._reorder_pass(source) == expected, (rule, values)
            assert converter._reorder_pass(source, (False,) * len(source)) == source, (
                rule,
                values,
            )
            exercised += 1
    assert exercised == 28_512


def test_every_jg_lepcha_reorder_rule_exhausts_representative_provenance_masks():
    converter = JGLepchaConverter.default()
    legacy_source = _singleton_legacy_source_by_target(converter)
    all_derived = 0
    mixed_or_native = 0

    for rule in converter._reorder_rules:
        values = tuple(
            min(set(converter._unicode_classes[name]) & set(legacy_source))
            for name, _variable in rule.slots
        )
        bound = {variable: chr(value) for (_class_name, variable), value in zip(rule.slots, values)}
        expected_reordered = unicodedata.normalize(
            "NFC", "".join(bound[variable] for variable in rule.output_vars)
        )
        legacy_input = "".join(legacy_source[value] for value in values)
        result = converter.convert(legacy_input)
        assert result.unicode_text == expected_reordered, rule
        assert result.replacement_count == len(values), rule
        assert result.unmapped_codepoints == result.uncertain_codepoints == [], rule
        all_derived += 1

        expected_preserved = unicodedata.normalize("NFC", "".join(chr(value) for value in values))
        for mask in product((False, True), repeat=len(values)):
            if all(mask):
                continue
            source = "".join(
                legacy_source[value] if is_derived else chr(value)
                for value, is_derived in zip(values, mask)
            )
            result = converter.convert(source)
            assert result.unicode_text == expected_preserved, (rule, mask)
            assert result.replacement_count == sum(mask), (rule, mask)
            assert result.unmapped_codepoints == result.uncertain_codepoints == [], (rule, mask)
            mixed_or_native += 1

    assert all_derived == 72
    assert mixed_or_native == 1_260


@pytest.mark.parametrize(
    ("source", "expected", "replacements"),
    [
        ("\u1c27\u1c00", "\u1c27\u1c00", 0),
        ("i\u1c00", "\u1c27\u1c00", 1),
        ("\u1c27k", "\u1c27\u1c00", 1),
        ("ik", "\u1c00\u1c27", 2),
    ],
)
def test_public_jg_lepcha_reorder_requires_fully_legacy_derived_window(
    source, expected, replacements
):
    result = convert_jg_lepcha(source, strict=True)
    assert result.unicode_text == unicodedata.normalize("NFC", expected)
    assert result.replacement_count == replacements
    assert result.unmapped_codepoints == result.uncertain_codepoints == []


@pytest.mark.parametrize(
    "derived",
    [
        (True,),
        (True, 1),
        [True, True],
    ],
)
def test_jg_lepcha_reorder_rejects_invalid_internal_provenance(derived):
    with pytest.raises(ValueError, match="reorder provenance"):
        JGLepchaConverter.default()._reorder_pass("\u1c27\u1c00", derived)


def test_every_assigned_unicode_lepcha_character_passes_through_strictly():
    for codepoint in range(0x1C00, 0x1C50):
        if not _is_assigned_script_codepoint(codepoint, "Lepcha"):
            continue
        character = chr(codepoint)
        result = convert_jg_lepcha(character, strict=True)
        assert result.unicode_text == character
        assert result.replacement_count == 0
        assert result.unmapped_codepoints == []
        assert result.uncertain_codepoints == []


@pytest.mark.parametrize(
    "byte_rules",
    [
        [],
        1,
        {((0x41,), (0x1C00,))},
        [((), (0x1C00,))],
        [((0x41,), ())],
        [((True,), (0x1C00,))],
        [((0x100,), (0x1C00,))],
        [((0x41,), (True,))],
        [((0x41,), (0x41,))],
        [((0x41,), (0xD800,))],
        [((0x41,), (0x110000,))],
        [((0x41,), (0x00,))],
        [((0x41,), (0x20,))],
        [((0x41,), (0x25CC,))],
        [((0x41, 0x42), (0x25CC,))],
        [((0x00,), (0x1C00,))],
        [((0x09,), (0x1C00,))],
        [((0x0A,), (0x1C00,))],
        [((0x0D,), (0x1C00,))],
        [((0x20,), (0x1C00,))],
        [((0x20, 0x41), (0x1C00,))],
        [{(0x22,), (0x1C00,)}],
        [((0x41,), (0x1C00,)), ((0x41,), (0x1C01,))],
        [((0x41,), (0x1C00,)), ((0x41, 0x42), (0x1C01,))],
        [(0x41, 0x1C00, 0x1C01)],
    ],
)
def test_jg_lepcha_constructor_rejects_unsafe_byte_rules(byte_rules):
    with pytest.raises(ValueError):
        JGLepchaConverter(byte_rules, [], {}, None)


@pytest.mark.parametrize(
    ("classes", "rules", "message"),
    [
        ([], [], "must be a mapping"),
        ({1: (0x1C00,)}, [], "class name"),
        ({"bad name": (0x1C00,)}, [], "class name"),
        ({"Cons": ()}, [], "empty"),
        ({"Cons": (0x1C00, 0x1C00)}, [], "duplicate member"),
        ({"Cons": (0x41,)}, [], "non-Lepcha"),
        ({"Cons": (0xD800,)}, [], "Unicode scalar"),
        ({"Cons": (0x1C00,)}, ["not-a-rule"], "reorder rule"),
        ({"Cons": (0x1C00,)}, [_ReorderRule((), ())], "empty"),
        (
            {"Cons": (0x1C00,)},
            [_ReorderRule(("Cc",), ("c",))],
            "reorder slot",
        ),
        (
            {"Cons": (0x1C00,)},
            [_ReorderRule((("Missing", "c"),), ("c",))],
            "unknown class",
        ),
        (
            {"Cons": (0x1C00,)},
            [_ReorderRule((("Cons", "c"), ("Cons", "c")), ("c", "c"))],
            "duplicate variable",
        ),
        (
            {"Cons": (0x1C00,), "Vowel": (0x1C27,)},
            [_ReorderRule((("Vowel", "v"), ("Cons", "c")), ("c",))],
            "permutation",
        ),
        (
            {"Cons": (0x1C00,), "Vowel": (0x1C27,)},
            [
                _ReorderRule((("Vowel", "v"), ("Cons", "c")), ("c", "v")),
                _ReorderRule((("Vowel", "x"), ("Cons", "y")), ("x", "y")),
            ],
            "conflicting",
        ),
        (
            {
                "A": (0x1C00,),
                "AOverlap": (0x1C00,),
                "B": (0x1C01,),
                "BOverlap": (0x1C01,),
            },
            [
                _ReorderRule((("A", "a"), ("B", "b")), ("a", "b")),
                _ReorderRule((("AOverlap", "x"), ("BOverlap", "y")), ("y", "x")),
            ],
            "conflicting overlapping",
        ),
    ],
)
def test_jg_lepcha_constructor_rejects_unsafe_classes_and_reorder_rules(classes, rules, message):
    with pytest.raises(ValueError, match=message):
        JGLepchaConverter([((0x41,), (0x1C00,))], rules, classes, None)


@pytest.mark.parametrize(
    ("context_rule", "message"),
    [
        ([0x41, {0x42}, 0x1C01], "context rule"),
        ((True, {0x42}, 0x1C01), "trigger"),
        ((0x41, set(), 0x1C01), "empty"),
        ((0x41, [0x42, 0x42], 0x1C01), "duplicate byte"),
        ((0x41, {0x42}, 0x41), "context target"),
        ((0x42, {0x41}, 0x1C01), "fallback rule"),
        ((0x00, {0x41}, 0x1C01), "cannot be C0 or SPACE"),
        ((0x09, {0x41}, 0x1C01), "cannot be C0 or SPACE"),
        ((0x0A, {0x41}, 0x1C01), "cannot be C0 or SPACE"),
        ((0x0D, {0x41}, 0x1C01), "cannot be C0 or SPACE"),
        ((0x20, {0x41}, 0x1C01), "cannot be C0 or SPACE"),
    ],
)
def test_jg_lepcha_constructor_rejects_unsafe_context_rules(context_rule, message):
    with pytest.raises(ValueError, match=message):
        JGLepchaConverter([((0x41,), (0x1C00,))], [], {}, context_rule)


def test_jg_lepcha_constructor_requires_exact_uncertainty_metadata():
    with pytest.raises(ValueError, match="uncertainty metadata"):
        JGLepchaConverter(
            [((0x3C,), (0x25CC,))],
            [],
            {},
            None,
        )
    with pytest.raises(ValueError, match="uncertainty metadata"):
        JGLepchaConverter(
            [((0x3C,), (0x1C00,))],
            [],
            {},
            None,
            {0x3C},
        )
    with pytest.raises(ValueError, match="duplicate JG Lepcha uncertain"):
        JGLepchaConverter(
            [((0x3C,), (0x25CC,))],
            [],
            {},
            None,
            [0x3C, 0x3C],
        )


def test_jg_lepcha_constructor_accepts_the_pinned_special_target_policies():
    converter = JGLepchaConverter(
        [
            ((0x00,), (0x00,)),
            ((0x20,), (0x20,)),
            ((0x2F,), (0x20,)),
            ((0x3C,), (0x25CC,)),
            ((0x41,), (0x1C00,)),
        ],
        [],
        {},
        None,
        {0x3C},
    )
    assert converter.convert("\x00 /<A").unicode_text == "\x00  ◌ᰀ"
    assert converter.convert("<").uncertain_codepoints == ["U+003C"]


def test_jg_lepcha_constructor_freezes_mutable_and_one_shot_inputs():
    source = [0x41]
    target = [0x1C00]
    slots = [("Vowel", "v"), ("Cons", "c")]
    output_vars = ["c", "v"]
    vowel_members = [0x1C27]
    cons_members = [0x1C00]
    converter = JGLepchaConverter(
        iter([(iter(source), iter(target))]),
        iter([_ReorderRule(slots, output_vars)]),
        {"Vowel": iter(vowel_members), "Cons": iter(cons_members)},
        None,
    )

    excluded = [0x42]
    context_converter = JGLepchaConverter(
        [((0x41,), (0x1C00,)), ((0x42,), (0x1C01,))],
        [],
        {},
        (0x41, iter(excluded), 0x1C02),
    )

    source[0] = 0x42
    target[0] = 0x110000
    slots[0] = ("Missing", "x")
    output_vars[0] = "v"
    vowel_members[0] = 0x41
    cons_members[0] = 0x41
    excluded[0] = 0x43

    assert converter.convert("A").unicode_text == "ᰀ"
    assert converter._reorder_pass("ᰧᰀ") == "ᰀᰧ"
    assert context_converter.convert("BA").unicode_text == "ᰁᰀ"

    with pytest.raises(AttributeError):
        converter._byte_rules.append(((0x42,), (0x1C01,)))
    with pytest.raises(AttributeError):
        converter._reorder_rules.append(_ReorderRule((), ()))
    with pytest.raises(TypeError):
        converter._unicode_classes["Forged"] = frozenset({0x1C00})
    with pytest.raises(AttributeError):
        converter._unicode_classes["Cons"].add(0x1C01)
    with pytest.raises(FrozenInstanceError):
        converter._contract.reorder_provenance = "all-input"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: JGLepchaConverter(repeat(((0x41,), (0x1C00,))), [], {}, None),
        lambda: JGLepchaConverter([(repeat(0x41), (0x1C00,))], [], {}, None),
        lambda: JGLepchaConverter([((0x41,), repeat(0x1C00))], [], {}, None),
        lambda: JGLepchaConverter([((0x41,), (0x1C00,))], repeat(_ReorderRule((), ())), {}, None),
        lambda: JGLepchaConverter([((0x41,), (0x1C00,))], [], {"Cons": repeat(0x1C00)}, None),
        lambda: JGLepchaConverter([((0x41,), (0x1C00,))], [], _InfiniteItemsMapping(), None),
    ],
)
def test_jg_lepcha_constructor_rejects_unbounded_iterables_without_hanging(factory):
    with pytest.raises(ValueError, match="exceeds"):
        factory()


def test_jg_lepcha_constructor_preserves_identical_upstream_reorder_redundancy():
    rule = _ReorderRule((("Vowel", "v"), ("Cons", "c")), ("c", "v"))
    converter = JGLepchaConverter(
        [((0x41,), (0x1C00,))],
        [rule, rule],
        {"Vowel": (0x1C27,), "Cons": (0x1C00,)},
        None,
    )
    assert converter._reorder_rules == (rule, rule)


VALID_CUSTOM_MAP = """EncodingName "Fixture"
RHSFlags (ExpectsNFC)
Pass(Byte_Unicode)
ByteClass [Bytes] = (0x41 0x42)
UniClass [Letters] = (U+1C00 U+1C01)
[Bytes] <> [Letters]
ByteClass [Vowels] = (0x4F)
0x4F > U+1C28
0x61 > U+1C28
0x61 / ^[Vowels] _ > U+1C26
0x3C > U+25CC ; ??? fixture placeholder
Pass(Unicode)
Class[Cons] = (U+1C00 U+1C01)
Class[InitDepVow] = (U+1C27)
[InitDepVow]=v [Cons]=c <> @c @v
"""


def test_jg_lepcha_parser_accepts_the_exact_supported_two_pass_subset(tmp_path):
    map_path = tmp_path / "valid.map"
    map_path.write_text(VALID_CUSTOM_MAP, encoding="utf-8")
    converter = JGLepchaConverter.from_map_file(map_path)

    assert converter.convert("AB").unicode_text == "ᰀᰁ"
    assert converter.convert("a").unicode_text == "ᰦ"
    assert converter.convert("Oa").unicode_text == "ᰨᰨ"
    assert converter.convert("<").uncertain_codepoints == ["U+003C"]
    assert converter._reorder_pass("ᰧᰀ") == "ᰀᰧ"


@pytest.mark.parametrize(
    ("map_text", "message"),
    [
        ('UnknownHeader "x"\nPass(Byte_Unicode)\n0x41 > U+1C00\n', "pre-pass"),
        ("EncodingName x\nPass(Byte_Unicode)\n0x41 > U+1C00\n", "header declaration"),
        (
            'EncodingName "a"\nEncodingName "b"\nPass(Byte_Unicode)\n0x41 > U+1C00\n',
            "duplicate JG Lepcha header",
        ),
        ("Pass (Byte_Unicode)\n0x41 > U+1C00\n", "pass declaration"),
        (
            "Pass(Byte_Unicode)\nPass(Byte_Unicode)\n0x41 > U+1C00\n",
            "duplicate JG Lepcha pass",
        ),
        (
            "Pass(Unicode)\nPass(Byte_Unicode)\n0x41 > U+1C00\n",
            "must precede Unicode",
        ),
        ('EncodingName "no pass"\n', "missing Pass"),
        ("Pass(Byte_Unicode)\nByteClass [B] = ()\n", "empty byte class"),
        (
            "Pass(Byte_Unicode)\nByteClass [B] = (0x41 0x41)\n",
            "duplicate member",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [B] = (0x41)\nByteClass [B] = (0x42)\n",
            "duplicate JG Lepcha byte class",
        ),
        ("Pass(Byte_Unicode)\nByteClass [B] = (41)\n", "byte token"),
        (
            "Pass(Byte_Unicode)\nByteClass [B] = (0x41 .. 42)\n",
            "invalid byte range",
        ),
        ("Pass(Byte_Unicode)\nUniClass [U] = ()\n", "empty Unicode class"),
        (
            "Pass(Byte_Unicode)\nUniClass [U] = (U+D7FF .. U+E000)\n",
            "Unicode scalar range",
        ),
        (
            "Pass(Byte_Unicode)\nUniClass [U] = (U+1C00)\nUniClass [U] = (U+1C01)\n",
            "duplicate JG Lepcha Unicode class",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [B] = (0x41)\n[B] > [Missing]\n",
            "unknown Unicode class",
        ),
        (
            "Pass(Byte_Unicode)\nUniClass [U] = (U+1C00)\n[Missing] > [U]\n",
            "unknown byte class",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [B] = (0x41 0x42)\nUniClass [U] = (U+1C00)\n[B] > [U]\n",
            "length mismatch",
        ),
        ("Pass(Byte_Unicode)\n0x41 > U+1C00 trailing\n", "explicit JG Lepcha"),
        ("Pass(Byte_Unicode)\n0x41 > U+110000\n", "Unicode scalar"),
        ("Pass(Byte_Unicode)\n0x41 > U+0041\n", "rule target"),
        (
            "Pass(Byte_Unicode)\n0x09 > U+1C00\n",
            "C0 and SPACE sources must be singleton identity",
        ),
        (
            "Pass(Byte_Unicode)\nUniClass [U] = (U+10000 .. U+10400)\n",
            "Unicode class exceeds",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\n0x41 > U+1C01\n",
            "duplicate JG Lepcha source",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\n0x41 0x42 > U+1C01\n",
            "prefix-conflicting",
        ),
        (
            "Pass(Byte_Unicode)\n0x61 > U+1C28\n0x61 / ^[Missing] _ > U+1C26\n",
            "unknown byte class",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [B] = (0x41)\n0x61 > U+1C28\n"
            "0x61 / ^[B] _ > U+1C26\n0x61 / ^[B] _ > U+1C26\n",
            "multiple JG Lepcha context",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [B] = (0x41)\n0x41 > U+1C00\n0x61 / ^[B] _ > U+1C26\n",
            "fallback rule",
        ),
        (
            "Pass(Byte_Unicode)\nByteClass [B] = (0x41)\n0x09 > U+0009\n0x09 / ^[B] _ > U+1C26\n",
            "context trigger cannot be C0 or SPACE",
        ),
        ("Pass(Byte_Unicode)\n0x3C > U+25CC\n", "uncertainty metadata"),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\n"
            "; comment ending in a continuation marker \\\nunsupported active syntax\n",
            "explicit JG Lepcha rule",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\n\\\n",
            "dangling continuation",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\nPass(Unicode)\nClass[Cons] = ()\n",
            "empty Unicode class",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\nPass(Unicode)\nClass[Cons] = (U+1C00 U+1C00)\n",
            "duplicate member",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\nPass(Unicode)\nClass[Cons] = (U+0041)\n",
            "non-Lepcha member",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\nPass(Unicode)\n"
            "Class[Cons] = (U+1C00)\nClass[Cons] = (U+1C01)\n",
            "duplicate JG Lepcha reorder class",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\nPass(Unicode)\nunsupported syntax\n",
            "reorder rule",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\nPass(Unicode)\n"
            "Class[Cons] = (U+1C00)\n[Missing]=c <> @c\n",
            "unknown class",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\nPass(Unicode)\n"
            "Class[Cons] = (U+1C00)\n[Cons]=c <> @missing\n",
            "permute all bound",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\nPass(Unicode)\n"
            "Class[Cons] = (U+1C00)\n[Cons]=c [Cons]=c <> @c @c\n",
            "duplicate variable",
        ),
        (
            "Pass(Byte_Unicode)\n0x41 > U+1C00\nPass(Unicode)\n"
            "Class[A] = (U+1C00)\nClass[B] = (U+1C01)\n"
            "[A]=a [B]=b <> @a @b\n[A]=x [B]=y <> @y @x\n",
            "conflicting",
        ),
    ],
)
def test_jg_lepcha_parser_rejects_malformed_or_ambiguous_maps(tmp_path, map_text, message):
    map_path = tmp_path / "invalid.map"
    map_path.write_text(map_text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        JGLepchaConverter.from_map_file(map_path)


def test_jg_lepcha_parser_rejects_invalid_utf8_with_context(tmp_path):
    map_path = tmp_path / "invalid-utf8.map"
    map_path.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="invalid UTF-8 in JG Lepcha map"):
        JGLepchaConverter.from_map_file(map_path)


def test_jg_lepcha_parser_does_not_let_inline_comment_backslashes_swallow_rules(tmp_path):
    map_path = tmp_path / "comment-backslash.map"
    map_path.write_text(
        "Pass(Byte_Unicode)\n0x41 > U+1C00 ; comment ending in backslash \\\n0x42 > U+1C01\n",
        encoding="utf-8",
    )
    converter = JGLepchaConverter.from_map_file(map_path)
    assert converter.convert("AB").unicode_text == "ᰀᰁ"


def test_jg_lepcha_parser_bounds_class_and_rule_inventories(tmp_path):
    too_many_classes = tmp_path / "too-many-classes.map"
    too_many_classes.write_text(
        "Pass(Byte_Unicode)\n"
        + "\n".join(f"ByteClass [B{index}] = (0x41)" for index in range(129))
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="byte classes exceed"):
        JGLepchaConverter.from_map_file(too_many_classes)

    too_many_rules = tmp_path / "too-many-rules.map"
    too_many_rules.write_text(
        "Pass(Byte_Unicode)\n"
        + "\n".join(f"0x41 > U+1C00 ; rule {index}" for index in range(513))
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="byte-rule sequence exceeds"):
        JGLepchaConverter.from_map_file(too_many_rules)


def test_jg_lepcha_consonants_and_digits_follow_sil_classes():
    converter = JGLepchaConverter.default()
    assert converter.convert("k").unicode_text == "ᰀ"
    assert converter.convert("W").unicode_text == "ᰁ"
    assert converter.convert("0123456789").unicode_text == "᱀᱁᱂᱃᱄᱅᱆᱇᱈᱉"


def test_jg_lepcha_visual_prebase_vowel_reorders():
    # byte i = vowel sign I, byte k = letter KA
    assert convert_jg_lepcha("ik").unicode_text == "ᰀᰧ"


def test_jg_lepcha_composites_and_conjuncts():
    # '!' is SIL's OO + final K composite. Latin-1 À is byte 0xC0,
    # the precomposed legacy KA+subjoined-YA conjunct.
    assert convert_jg_lepcha("!").unicode_text == "ᰩᰭ"
    assert convert_jg_lepcha("À").unicode_text == "ᰀᰤ"


def test_jg_lepcha_contextual_a_rule_uses_negated_previous_class():
    # Standalone a is independent A. After a dependent-vowel byte it falls
    # through to the regular dependent-vowel class, exactly as SIL specifies.
    assert convert_jg_lepcha("a").unicode_text == "ᰦ"
    assert convert_jg_lepcha("Oa").unicode_text == "ᰨᰨ"


@pytest.mark.parametrize(
    ("source", "source_label"),
    [("<", "U+003C"), ("=", "U+003D"), (">", "U+003E")],
)
def test_jg_lepcha_upstream_placeholder_mappings_are_uncertain(source, source_label):
    result = convert_jg_lepcha(source)
    assert result.unicode_text == "◌"
    assert result.lepcha_char_count == 0
    assert result.replacement_count == 1
    assert result.unmapped_codepoints == []
    assert result.uncertain_codepoints == [source_label]

    with pytest.raises(ValueError, match=rf"{re.escape(source_label)}.*U\+25CC"):
        convert_jg_lepcha(source, strict=True)
    with pytest.raises(ValueError, match=rf"{re.escape(source_label)}.*U\+25CC"):
        convert(source, font="jg-lepcha", strict=True)


def test_jg_lepcha_placeholder_diagnostics_preserve_all_source_values():
    result = convert_jg_lepcha("<=>")
    assert result.unicode_text == "◌◌◌"
    assert result.replacement_count == 3
    assert result.unmapped_codepoints == []
    assert result.uncertain_codepoints == ["U+003C", "U+003D", "U+003E"]


def test_jg_lepcha_direct_dotted_circle_remains_an_unmapped_value():
    result = convert_jg_lepcha("◌")
    assert result.unicode_text == "◌"
    assert result.replacement_count == 0
    assert result.unmapped_codepoints == ["U+25CC"]
    assert result.uncertain_codepoints == []
    with pytest.raises(ValueError, match=r"U\+25CC"):
        convert_jg_lepcha("◌", strict=True)


def test_jg_lepcha_neighboring_evidenced_rules_remain_strict_clean():
    result = convert_jg_lepcha("./k", strict=True)
    assert result.unicode_text == "᰿ ᰀ"
    assert result.replacement_count == 3
    assert result.unmapped_codepoints == []
    assert result.uncertain_codepoints == []


def test_jg_lepcha_unmapped_ascii_is_surfaced():
    result = convert_jg_lepcha("~")
    assert result.unicode_text == "~"
    assert result.unmapped_codepoints == ["U+007E"]
    with pytest.raises(ValueError, match="unmapped/leftover characters"):
        convert_jg_lepcha("~", strict=True)


def test_jg_lepcha_genuine_unicode_passes_through():
    result = convert_jg_lepcha("ᰀ", strict=True)
    assert result.unicode_text == "ᰀ"
    assert not result.unmapped_codepoints


@pytest.mark.parametrize("font", ["jg-lepcha", "jglepcha", "lepcha-jg"])
def test_every_jg_lepcha_dispatcher_alias_has_exact_strict_behavior(font):
    assert convert("k", font=font, strict=True) == "ᰀ"
    assert convert("\u1c27\u1c00", font=font, strict=True) == "\u1c27\u1c00"
    assert convert("i\u1c00", font=font, strict=True) == "\u1c27\u1c00"
    with pytest.raises(ValueError, match=r"U\+003C.*U\+25CC"):
        convert("<", font=font, strict=True)
    with pytest.raises(ValueError, match=r"U\+007E"):
        convert("~", font=font, strict=True)


def test_jg_lepcha_alias_inventory_is_immutable():
    assert package_module._JG_LEPCHA_FONTS == frozenset({"jg-lepcha", "jglepcha", "lepcha-jg"})
    with pytest.raises(AttributeError):
        package_module._JG_LEPCHA_FONTS.add("forged")
