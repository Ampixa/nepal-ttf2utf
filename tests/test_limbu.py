"""Limbu/Sirijonga (Namdhinggo legacy) conversion tests."""

import hashlib
import json
import unicodedata
from collections import Counter
from dataclasses import FrozenInstanceError
from importlib import resources
from itertools import product

import pytest

import nepal_ttf2utf as package
import nepal_ttf2utf.limbu as limbu_module
from nepal_ttf2utf import convert, convert_limbu
from nepal_ttf2utf._controls import DIAGNOSTIC_C0
from nepal_ttf2utf.limbu import LimbuConverter

_VOWELS = tuple(range(0x1920, 0x1929))
_SUBJOINED = tuple(range(0x1929, 0x192C))
_KEMPHRENG = 0x193A


def _has_limbu(s: str) -> bool:
    return any(0x1900 <= ord(c) <= 0x194F for c in s)


def _legacy_source_for_target(converter: LimbuConverter, codepoint: int) -> str:
    matches = [source for source, target in converter._rules if target == (codepoint,)]
    assert len(matches) == 1, f"U+{codepoint:04X}"
    return "".join(chr(value) for value in matches[0])


def _provenance_input(
    converter: LimbuConverter, codepoints: tuple[int, ...], mask: tuple[bool, ...]
) -> str:
    assert len(codepoints) == len(mask)
    return "".join(
        _legacy_source_for_target(converter, codepoint) if derived else chr(codepoint)
        for codepoint, derived in zip(codepoints, mask)
    )


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

    reorder = converter._contract.reorder
    reorder_payload = json.dumps(
        {
            "kemphreng": reorder.kemphreng,
            "provenance": reorder.provenance,
            "subjoined": sorted(reorder.subjoined),
            "vowels": sorted(reorder.vowels),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    assert len(reorder_payload) == 143
    assert hashlib.sha256(reorder_payload).hexdigest() == (
        "33e0df0d27fafe33b5fe6126dbe7074613b4c3e344b1d3595a9b03069bdb535e"
    )


def test_every_limbu_rule_marks_each_emitted_scalar_as_legacy_derived():
    converter = LimbuConverter.default()
    for source, target in converter._rules:
        mapped, derived, replacements, unmapped = converter._byte_pass_with_provenance(
            "".join(chr(value) for value in source)
        )
        assert mapped == "".join(chr(value) for value in target)
        assert derived == (True,) * len(target)
        assert replacements == 1
        assert unmapped == []


def test_limbu_ordered_byte_inventory_remains_exact():
    result = LimbuConverter.default().convert("".join(chr(value) for value in range(256)))

    assert len(result.unicode_text) == 258
    assert result.limbu_char_count == 62
    assert result.replacement_count == 129
    assert len(result.unmapped_codepoints) == 156
    assert hashlib.sha256(result.unicode_text.encode("utf-8")).hexdigest() == (
        "f9f55d84875b4a73e5e324e95c0d97fb156d164c9f6d44fef9cf6ca08cc526ca"
    )


def test_every_limbu_reorder_product_and_provenance_mask():
    converter = LimbuConverter.default()
    derived_cases = 0
    preserved_cases = 0

    for vowel, subjoined in product(_VOWELS, _SUBJOINED):
        codepoints = (vowel, subjoined)
        for mask in product((False, True), repeat=2):
            result = converter.convert(_provenance_input(converter, codepoints, mask))
            expected = (
                "".join(chr(value) for value in (subjoined, vowel))
                if all(mask)
                else "".join(chr(value) for value in codepoints)
            )
            assert result.unicode_text == expected, (codepoints, mask)
            assert result.replacement_count == sum(mask), (codepoints, mask)
            assert result.unmapped_codepoints == [], (codepoints, mask)
            derived_cases += all(mask)
            preserved_cases += not all(mask)

        triple = (vowel, _KEMPHRENG, subjoined)
        for mask in product((False, True), repeat=3):
            result = converter.convert(_provenance_input(converter, triple, mask))
            expected = (
                "".join(chr(value) for value in (subjoined, vowel, _KEMPHRENG))
                if all(mask)
                else "".join(chr(value) for value in triple)
            )
            assert result.unicode_text == expected, (triple, mask)
            assert result.replacement_count == sum(mask), (triple, mask)
            assert result.unmapped_codepoints == [], (triple, mask)
            derived_cases += all(mask)
            preserved_cases += not all(mask)

    assert derived_cases == 54
    assert preserved_cases == 270


def test_every_exact_all_legacy_limbu_reorder_source_path():
    converter = LimbuConverter.default()
    pair_paths = []
    triple_paths = []

    for vowel, subjoined in product(_VOWELS, _SUBJOINED):
        pair_paths.append(
            (
                _provenance_input(converter, (vowel, subjoined), (True, True)),
                "".join(chr(value) for value in (subjoined, vowel)),
            )
        )
        triple_paths.append(
            (
                _provenance_input(
                    converter,
                    (vowel, _KEMPHRENG, subjoined),
                    (True, True, True),
                ),
                "".join(chr(value) for value in (subjoined, vowel, _KEMPHRENG)),
            )
        )

    pair_paths.append(("H", "\u192a\u1922"))
    triple_paths.extend(
        ("L" + source, chr(subjoined) + "\u1921\u193a")
        for source, subjoined in (("O", 0x1929), ("q", 0x192A), ("J", 0x192B))
    )

    assert len(pair_paths) == 28
    assert len(triple_paths) == 30
    for source, expected in pair_paths + triple_paths:
        result = converter.convert(source)
        assert result.unicode_text == expected, source
        assert result.unmapped_codepoints == [], source


def test_limbu_reorder_preserves_native_and_mixed_windows():
    converter = LimbuConverter.default()
    cases = {
        "\u1922\u192a": ("\u1922\u192a", 0),
        "\u1922\u193a\u192a": ("\u1922\u193a\u192a", 0),
        "'\u192a": ("\u1922\u192a", 1),
        "\u1922q": ("\u1922\u192a", 1),
        "'M\u192a": ("\u1922\u193a\u192a", 2),
        "'\u193aq": ("\u1922\u193a\u192a", 2),
        "\u1922Mq": ("\u1922\u193a\u192a", 2),
    }

    for source, (expected, replacements) in cases.items():
        result = converter.convert(source)
        assert result.unicode_text == expected, source
        assert result.replacement_count == replacements, source
        assert result.unmapped_codepoints == [], source

    assert converter.convert("H").unicode_text == "\u192a\u1922"
    assert converter.convert("LJ").unicode_text == "\u192b\u1921\u193a"
    assert converter.convert("\u1920H\u1929").unicode_text == ("\u1920\u192a\u1922\u1929")
    assert converter.convert("\u1920LJ\u1929").unicode_text == ("\u1920\u192b\u1921\u193a\u1929")


@pytest.mark.parametrize(
    ("text", "derived"),
    [
        ("\u1922\u192a", (True,)),
        ("\u1922\u192a", (True, 1)),
        ("\u1922\u192a", [True, True]),
    ],
)
def test_limbu_reorder_rejects_malformed_provenance(text, derived):
    with pytest.raises(ValueError, match="invalid Limbu reorder provenance"):
        limbu_module._reorder_limbu(text, derived)


def test_limbu_reorder_accepts_empty_and_retains_private_default_behavior():
    assert limbu_module._reorder_limbu("", ()) == ""
    assert limbu_module._reorder_limbu("\u1922\u192a") == "\u192a\u1922"


def test_limbu_runtime_contract_is_transitively_immutable(monkeypatch):
    converter = LimbuConverter.default()
    assert type(converter._rules) is tuple
    assert type(converter._contract.rules) is tuple
    assert type(converter._contract.reorder.vowels) is frozenset
    assert type(converter._contract.reorder.subjoined) is frozenset
    assert converter._contract.reorder.provenance == "legacy-byte-derived-only"

    with pytest.raises(FrozenInstanceError):
        converter._contract.reorder.kemphreng = 0x1900
    with pytest.raises(FrozenInstanceError):
        converter._contract.rules = ()
    with pytest.raises(AttributeError):
        converter._contract.reorder.vowels.add(0x1900)

    replacement = limbu_module._LimbuReorderContract(
        vowels=frozenset(),
        subjoined=frozenset(),
        kemphreng=0x1900,
        provenance="replacement",
    )
    monkeypatch.setattr(limbu_module, "_DEFAULT_REORDER_CONTRACT", replacement)
    monkeypatch.setattr(limbu_module, "_VOWELS", frozenset())
    monkeypatch.setattr(limbu_module, "_SUBJOINED", frozenset())
    monkeypatch.setattr(limbu_module, "_KEMPHRENG", 0x1900)
    assert converter.convert("H").unicode_text == "\u192a\u1922"


def test_limbu_dispatch_alias_inventories_are_frozen_disjoint_and_exact():
    legacy_aliases = frozenset({"limbu", "namdhinggo", "namdhinggosill", "sirijonga"})
    unicode_aliases = frozenset(
        {
            "limbu-unicode",
            "namdhinggo regular",
            "namdhinggo-bold",
            "namdhinggo-extrabold",
            "namdhinggo-medium",
            "namdhinggo-regular",
            "namdhinggo-semibold",
            "namdhinggo-unicode",
            "noto sans limbu",
            "noto-sans-limbu",
            "notosanslimbu",
            "notosanslimbu-regular",
            "unicode-limbu",
        }
    )
    assert package._LIMBU_FONTS == legacy_aliases
    assert package._LIMBU_UNICODE_FONTS == unicode_aliases
    assert not package._LIMBU_FONTS & package._LIMBU_UNICODE_FONTS
    with pytest.raises(AttributeError):
        package._LIMBU_FONTS.add("overlap")
    with pytest.raises(AttributeError):
        package._LIMBU_UNICODE_FONTS.add("overlap")

    for alias in legacy_aliases:
        assert convert("H", font=alias, strict=True) == "\u192a\u1922"
        assert convert("\u1922\u192a", font=alias, strict=True) == "\u1922\u192a"
        assert convert("'\u192a", font=alias, strict=True) == "\u1922\u192a"

    native_patterns = "\u1922\u192a \u1922\u193a\u192a"
    for alias in unicode_aliases:
        assert convert(native_patterns, font=alias, strict=True) == native_patterns


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
    # Representative Limbu/Sirijonga legacy span bytes.
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


@pytest.mark.parametrize("source", ["#", "X"])
def test_limbu_unmapped_ascii_is_surfaced_in_strict_mode(source):
    # The upstream map explicitly leaves both values unresolved.
    res = LimbuConverter.default().convert(source)
    assert res.unicode_text == source
    assert res.replacement_count == 0
    assert res.unmapped_codepoints == [f"U+{ord(source):04X}"]
    with pytest.raises(ValueError):
        convert_limbu(source, strict=True)
    with pytest.raises(ValueError):
        convert(source, font="namdhinggo", strict=True)
