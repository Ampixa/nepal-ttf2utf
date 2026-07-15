"""Limbu/Sirijonga (Namdhinggo legacy) conversion tests."""

import hashlib
import json
import unicodedata
from collections import Counter
from dataclasses import FrozenInstanceError
from importlib import resources
from itertools import product, repeat

import pytest

import nepal_ttf2utf as package
import nepal_ttf2utf.limbu as limbu_module
from nepal_ttf2utf import convert, convert_limbu
from nepal_ttf2utf._controls import DIAGNOSTIC_C0
from nepal_ttf2utf.limbu import LimbuConverter

_VOWELS = tuple(range(0x1920, 0x1929))
_SUBJOINED = tuple(range(0x1929, 0x192C))
_KEMPHRENG = 0x193A

_CANONICAL_HEADERS = """EncodingName "Fixture"
DescriptiveName "Limbu"
Version "1.0"
Contact "mailto:fixture@example.invalid"
RegistrationAuthority "SIL International"
RegistrationName "Limbu-test"
Copyright "fixture"
"""
_CANONICAL_DEFAULTS = """ByteDefault 0x5E
UniDefault replacement_character
"""
_CANONICAL_UNICODE_PASS = """Pass(Unicode)
UniClass [VOWEL] = ( U+1920 .. U+1928 )
UniClass [SUBJ] = ( U+1929 .. U+192B )
[VOWEL]=V [SUBJ]=S <> @S @V
[VOWEL]=V U+193A [SUBJ]=S <> @S @V U+193A
"""
_REORDER_ROLE_CODEPOINTS = (*_VOWELS, *_SUBJOINED, _KEMPHRENG)


def _reorder_reachability_rules(*, omitted: frozenset[int] = frozenset()) -> str:
    return "\n".join(
        f"0x{0x80 + index:02X} > U+{codepoint:04X}"
        for index, codepoint in enumerate(_REORDER_ROLE_CODEPOINTS)
        if codepoint not in omitted
    )


def _valid_limbu_map(
    byte_body: str = "0x41 > U+1901",
    *,
    headers: str = _CANONICAL_HEADERS,
    defaults: str = _CANONICAL_DEFAULTS,
    unicode_pass: str = _CANONICAL_UNICODE_PASS,
    omitted_reorder_targets: frozenset[int] = frozenset(),
) -> str:
    sections = (
        headers.rstrip(),
        "Pass(Byte_Unicode)",
        defaults.rstrip(),
        byte_body.rstrip(),
        _reorder_reachability_rules(omitted=omitted_reorder_targets),
        unicode_pass.rstrip(),
    )
    return "\n".join(section for section in sections if section) + "\n"


def _pad_map_to_exact_bytes(map_text: str, total_bytes: int) -> str:
    remaining = total_bytes - len(map_text.encode("utf-8"))
    assert remaining >= 0
    chunks = [map_text]
    while remaining:
        chunk_bytes = min(remaining, limbu_module._MAX_MAP_LINE_CODEPOINTS + 1)
        if chunk_bytes == 1:
            chunks.append("\n")
        else:
            chunks.append(";" * (chunk_bytes - 1) + "\n")
        remaining -= chunk_bytes
    padded = "".join(chunks)
    assert len(padded.encode("utf-8")) == total_bytes
    return padded


def _flat_class_map(explicit_rule_count: int) -> str:
    target_values = list(range(256))
    for index, codepoint in enumerate(_REORDER_ROLE_CODEPOINTS):
        target_values[0x80 + index] = codepoint
    explicit_sources = list(product(range(0x21, 0x100), repeat=2))[:explicit_rule_count]
    byte_body = "\n".join(
        [
            "ByteClass [all_bytes] = (0x00 .. 0xFF)",
            "UniClass [all_targets] = ("
            + " ".join(f"U+{codepoint:04X}" for codepoint in target_values)
            + ")",
            *(f"0x{first:02X} 0x{second:02X} > U+1901" for first, second in explicit_sources),
            "[all_bytes] > [all_targets]",
        ]
    )
    return _valid_limbu_map(
        byte_body,
        omitted_reorder_targets=frozenset(_REORDER_ROLE_CODEPOINTS),
    )


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

    header_pairs = []
    pass_order = []
    defaults = []
    current_pass = ""
    unicode_lines = []
    for raw_line in lines:
        line = raw_line.split(";", 1)[0].strip()
        if not line:
            continue
        pass_match = limbu_module._PASS_RE.fullmatch(line)
        if pass_match is not None:
            current_pass = pass_match.group(1).casefold()
            pass_order.append(current_pass)
            continue
        if not current_pass:
            header_match = limbu_module._HEADER_STRING_RE.fullmatch(line)
            assert header_match is not None, line
            header_pairs.append((header_match.group(1), line.split('"', 1)[1][:-1]))
        elif current_pass == "byte_unicode" and limbu_module._DEFAULT_PREFIX_RE.match(line):
            defaults.append(line)
        elif current_pass == "unicode":
            unicode_lines.append(" ".join(line.split()))

    assert header_pairs == [
        ("EncodingName", "Limbu-Sirijonga"),
        ("DescriptiveName", "Limbu"),
        ("Version", "1.0"),
        ("Contact", "mailto:victor_gaultney@sil.org"),
        ("RegistrationAuthority", "SIL International"),
        ("RegistrationName", "Limbu-001"),
        ("Copyright", "(c)2007 SIL International"),
    ]
    assert pass_order == ["byte_unicode", "unicode"]
    assert defaults == ["ByteDefault 0x5E", "UniDefault replacement_character"]
    assert unicode_lines == [
        "UniClass [VOWEL] = ( U+1920 .. U+1928 )",
        "UniClass [SUBJ] = ( U+1929 .. U+192B )",
        "[VOWEL]=V [SUBJ]=S <> @S @V",
        "[VOWEL]=V U+193A [SUBJ]=S <> @S @V U+193A",
    ]
    unicode_payload = json.dumps(unicode_lines, separators=(",", ":")).encode("ascii")
    assert len(unicode_payload) == 158
    assert hashlib.sha256(unicode_payload).hexdigest() == (
        "62ea3686454059d2aacc9a60cb951403a7e581beb181522d066765a5338960dd"
    )

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
    assert converter._contract.precedence == "longest-source-first-stable"
    assert converter._contract.source_domain == "byte-scalars"
    assert converter._contract.pass_order == ("byte_unicode", "unicode")

    prefix_relations = {
        (shorter, longer)
        for shorter, _shorter_target in converter._rules
        for longer, _longer_target in converter._rules
        if len(shorter) < len(longer) and longer[: len(shorter)] == shorter
    }
    assert prefix_relations == {
        ((0x66,), (0x66, 0x5D)),
        ((0x66,), (0x66, 0x7D)),
    }
    prefix_payload = json.dumps(
        [[list(shorter), list(longer)] for shorter, longer in sorted(prefix_relations)],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(prefix_payload) == 36
    assert hashlib.sha256(prefix_payload).hexdigest() == (
        "40d56d22e57a8e22c1bcf04b98e174bb1e066158ed664a2921897d8fb2365293"
    )

    functional_payload = json.dumps(
        [[list(source), list(target)] for source, target in sorted(converter._rules)],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(functional_payload) == 1741
    assert hashlib.sha256(functional_payload).hexdigest() == (
        "31c47c252d2c82e9ab0d05619e80e1e0d1897a2b55f581edf8f987897e97956e"
    )

    runtime_order_payload = json.dumps(
        [[list(source), list(target)] for source, target in converter._rules],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(runtime_order_payload) == 1741
    assert hashlib.sha256(runtime_order_payload).hexdigest() == (
        "5f5073d61a43689f0de70aea6858a35f01482329816044a4d31a83920b62d7b6"
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
    assert len(result.unicode_text.encode("utf-8")) == 516
    assert result.limbu_char_count == 62
    assert result.replacement_count == 129
    assert len(result.unmapped_codepoints) == 156
    assert hashlib.sha256(result.unicode_text.encode("utf-8")).hexdigest() == (
        "f9f55d84875b4a73e5e324e95c0d97fb156d164c9f6d44fef9cf6ca08cc526ca"
    )
    diagnostic_payload = json.dumps(
        [int(label[2:], 16) for label in result.unmapped_codepoints],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(diagnostic_payload) == 585
    assert hashlib.sha256(diagnostic_payload).hexdigest() == (
        "bc2b21c6ff8ef6f3e3dfcc8253b4489b1a47fe4c3fc94f90e1b5414b6a50742e"
    )


def test_limbu_singleton_byte_categories_are_independently_pinned():
    converter = LimbuConverter.default()
    categories = {
        "mapped-clean": [],
        "mapped-diagnostic": [],
        "preserved-diagnostic": [],
    }

    for value in range(256):
        result = converter.convert(chr(value))
        if result.replacement_count:
            category = "mapped-diagnostic" if result.unmapped_codepoints else "mapped-clean"
        else:
            category = "preserved-diagnostic"
        categories[category].append(value)

    expected = {
        "mapped-clean": (
            100,
            331,
            "ecc86fec8949217c44ffc5200c3855f91f6545b7abd2ca3c1b47cd5124851f5b",
        ),
        "mapped-diagnostic": (
            29,
            79,
            "e7448b559456305cf21a1a3753e75c6a26c2884d3de62ab8c478976f8219aaf4",
        ),
        "preserved-diagnostic": (
            127,
            507,
            "398ff2401d15e416bb93a47326513bf4b6550564a9eab00eb08ec4b7db895256",
        ),
    }
    for category, values in categories.items():
        payload = json.dumps(values, separators=(",", ":")).encode("ascii")
        count, size, digest = expected[category]
        assert len(values) == count, category
        assert len(payload) == size, category
        assert hashlib.sha256(payload).hexdigest() == digest, category


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
    assert converter._contract.precedence == "longest-source-first-stable"
    assert converter._contract.source_domain == "byte-scalars"
    assert converter._contract.pass_order == ("byte_unicode", "unicode")

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


def test_limbu_constructor_copies_a_valid_private_reorder_contract():
    supplied = limbu_module._LimbuReorderContract(
        vowels=frozenset(_VOWELS),
        subjoined=frozenset(_SUBJOINED),
        kemphreng=_KEMPHRENG,
        provenance="legacy-byte-derived-only",
    )
    converter = LimbuConverter([((0x41,), (0x1901,))], _reorder_contract=supplied)

    assert converter._contract.reorder == supplied
    assert converter._contract.reorder is not supplied
    assert type(converter._contract.reorder.vowels) is frozenset
    assert type(converter._contract.reorder.subjoined) is frozenset


@pytest.mark.parametrize(
    "contract",
    [
        object(),
        limbu_module._LimbuReorderContract(
            vowels=set(_VOWELS),
            subjoined=frozenset(_SUBJOINED),
            kemphreng=_KEMPHRENG,
            provenance="legacy-byte-derived-only",
        ),
        limbu_module._LimbuReorderContract(
            vowels=frozenset(_VOWELS),
            subjoined=set(_SUBJOINED),
            kemphreng=_KEMPHRENG,
            provenance="legacy-byte-derived-only",
        ),
        limbu_module._LimbuReorderContract(
            vowels=frozenset(),
            subjoined=frozenset(_SUBJOINED),
            kemphreng=_KEMPHRENG,
            provenance="legacy-byte-derived-only",
        ),
        limbu_module._LimbuReorderContract(
            vowels=frozenset(_VOWELS),
            subjoined=frozenset((*_SUBJOINED, _VOWELS[0])),
            kemphreng=_KEMPHRENG,
            provenance="legacy-byte-derived-only",
        ),
        limbu_module._LimbuReorderContract(
            vowels=frozenset((*_VOWELS, _KEMPHRENG)),
            subjoined=frozenset(_SUBJOINED),
            kemphreng=_KEMPHRENG,
            provenance="legacy-byte-derived-only",
        ),
        limbu_module._LimbuReorderContract(
            vowels=frozenset(_VOWELS),
            subjoined=frozenset(_SUBJOINED),
            kemphreng=True,
            provenance="legacy-byte-derived-only",
        ),
        limbu_module._LimbuReorderContract(
            vowels=frozenset((*_VOWELS, 0x41)),
            subjoined=frozenset(_SUBJOINED),
            kemphreng=_KEMPHRENG,
            provenance="legacy-byte-derived-only",
        ),
        limbu_module._LimbuReorderContract(
            vowels=frozenset(_VOWELS),
            subjoined=frozenset(_SUBJOINED),
            kemphreng=_KEMPHRENG,
            provenance="all-input",
        ),
    ],
)
def test_limbu_constructor_rejects_noncanonical_or_mutable_reorder_contracts(contract):
    with pytest.raises(ValueError, match="invalid Limbu reorder contract"):
        LimbuConverter([((0x41,), (0x1901,))], _reorder_contract=contract)


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
            "Pass(Byte_Unicode)\nByteDefault 0x5E\nByteDefault 0x5E\n0x41 > U+1901\n",
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
        _valid_limbu_map(
            "ByteClass [b] = (0x41)\nUniClass [u] = (U+1901)\n[b] > [u]\n0x42 <> U+1902"
        ),
        encoding="utf-8",
    )
    converter = LimbuConverter.from_map_file(map_path)
    assert converter.convert("AB").unicode_text == "ᤁᤂ"


@pytest.mark.parametrize(
    ("map_text", "message"),
    [
        (_CANONICAL_HEADERS, r"missing Pass\(Byte_Unicode\)"),
        (_CANONICAL_HEADERS + _CANONICAL_UNICODE_PASS, "must precede Unicode pass"),
        (_valid_limbu_map(unicode_pass=""), r"missing Pass\(Unicode\)"),
        (_valid_limbu_map() + "Pass(Byte_Unicode)\n", "duplicate Limbu pass"),
        (_valid_limbu_map() + "Pass(Unsupported)\n", "invalid Limbu pass"),
        (_valid_limbu_map(headers='UnknownHeader "x"'), "pre-pass syntax"),
        (_valid_limbu_map(headers="EncodingName unquoted"), "header declaration"),
        (
            _valid_limbu_map(headers='EncodingName "one"\nEncodingName "two"'),
            "duplicate Limbu header",
        ),
        (_valid_limbu_map(defaults=""), "two canonical default declarations"),
        (_valid_limbu_map(defaults="ByteDefault 0x5E"), "two canonical default declarations"),
        (
            _valid_limbu_map(defaults="ByteDefault 0x5F\nUniDefault replacement_character"),
            "invalid Limbu default declaration",
        ),
    ],
)
def test_limbu_parser_requires_exact_headers_defaults_and_pass_order(tmp_path, map_text, message):
    map_path = tmp_path / "contract.map"
    map_path.write_text(map_text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        LimbuConverter.from_map_file(map_path)


@pytest.mark.parametrize(
    ("unicode_pass", "message"),
    [
        (
            "Pass(Unicode)\nUniClass [VOWEL] = (U+1920..U+1928)\n"
            "UniClass [SUBJ] = (U+1929..U+192B)\n"
            "[VOWEL]=V [SUBJ]=S <> @S @V\n",
            "exactly two reorder rules",
        ),
        (
            _CANONICAL_UNICODE_PASS + "[VOWEL]=V [SUBJ]=S <> @S @V\n",
            "more than two reorder rules",
        ),
        (
            "Pass(Unicode)\n"
            "UniClass [SUBJ] = ( U+1929 .. U+192B )\n"
            "UniClass [VOWEL] = ( U+1920 .. U+1928 )\n"
            "[VOWEL]=V [SUBJ]=S <> @S @V\n"
            "[VOWEL]=V U+193A [SUBJ]=S <> @S @V U+193A\n",
            "referenced classes in source order",
        ),
        (
            "Pass(Unicode)\n[VOWEL]=V [SUBJ]=S <> @S @V\nUniClass [VOWEL] = ( U+1920 .. U+1928 )\n",
            "classes must precede the reorder rules",
        ),
        (
            "Pass(Unicode)\n"
            "UniClass [VOWEL] = ( U+1920 .. U+1928 )\n"
            "UniClass [SUBJ] = ( U+1929 .. U+192B )\n"
            "[VOWEL]=V U+193A [SUBJ]=S <> @S @V U+193A\n"
            "[VOWEL]=V [SUBJ]=S <> @S @V\n",
            "invalid Limbu Unicode pair reorder rule",
        ),
        (
            _CANONICAL_UNICODE_PASS.replace(
                "[VOWEL]=V [SUBJ]=S <> @S @V", "unsupported Unicode syntax"
            ),
            "invalid Limbu Unicode pair reorder rule",
        ),
        (
            _CANONICAL_UNICODE_PASS.replace("[SUBJ]=S", "[SUBJOINED]=S"),
            "canonical role contract",
        ),
        (
            _CANONICAL_UNICODE_PASS.replace("[VOWEL]=V", "[VOWEL]=X"),
            "canonical role contract",
        ),
        (
            _CANONICAL_UNICODE_PASS.replace("<> @S @V", "<> @V @S"),
            "swap the two bound variables",
        ),
        (
            _CANONICAL_UNICODE_PASS.replace("U+193A", "U+193B"),
            "values differ from the canonical contract",
        ),
        (
            _CANONICAL_UNICODE_PASS.replace("@S @V U+193A", "@S @V U+193B"),
            "preserve its literal codepoint",
        ),
        (
            _CANONICAL_UNICODE_PASS.replace("U+1920 .. U+1928", "U+1921 .. U+1928"),
            "values differ from the canonical contract",
        ),
        (
            _CANONICAL_UNICODE_PASS.replace("U+1929 .. U+192B", "U+1929 .. U+192A"),
            "values differ from the canonical contract",
        ),
        (
            _CANONICAL_UNICODE_PASS.replace(
                "UniClass [SUBJ] = ( U+1929 .. U+192B )",
                "UniClass [SUBJ] = ( U+1929 .. U+192B )\nUniClass [EXTRA] = (U+1901)",
            ),
            "declare exactly its two referenced classes",
        ),
        (
            _CANONICAL_UNICODE_PASS.replace(
                "UniClass [SUBJ] = ( U+1929 .. U+192B )",
                "UniClass [SUBJ] = ( U+1929 .. U+192B )\nUniClass [SUBJ] = (U+1929..U+192B)",
            ),
            "duplicate Limbu reorder class",
        ),
    ],
)
def test_limbu_parser_validates_the_exact_active_unicode_grammar(tmp_path, unicode_pass, message):
    map_path = tmp_path / "unicode-contract.map"
    map_path.write_text(_valid_limbu_map(unicode_pass=unicode_pass), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        LimbuConverter.from_map_file(map_path)


def test_limbu_unicode_reorder_roles_must_be_reachable_from_the_byte_pass(tmp_path):
    map_path = tmp_path / "unreachable.map"
    map_path.write_text(
        _valid_limbu_map(omitted_reorder_targets=frozenset({0x1920})),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"unreachable Limbu Unicode reorder role: U\+1920"):
        LimbuConverter.from_map_file(map_path)


def test_limbu_parser_rejects_oversized_or_non_utf8_files(tmp_path):
    oversized = tmp_path / "oversized.map"
    oversized.write_bytes(b";" * (limbu_module._MAX_MAP_FILE_BYTES + 1))
    with pytest.raises(ValueError, match="map exceeds 1000000 bytes"):
        LimbuConverter.from_map_file(oversized)

    invalid_utf8 = tmp_path / "invalid-utf8.map"
    invalid_utf8.write_bytes(b"Pass(Byte_Unicode)\n\xff")
    with pytest.raises(ValueError, match="invalid UTF-8"):
        LimbuConverter.from_map_file(invalid_utf8)


@pytest.mark.parametrize(
    ("map_text", "message"),
    [
        (";\n" * (limbu_module._MAX_MAP_LINES + 1), "map exceeds 4096 lines"),
        (";" * (limbu_module._MAX_MAP_LINE_CODEPOINTS + 1), "line exceeds 4096 codepoints"),
        (
            _valid_limbu_map(
                "ByteClass [oversized] = ("
                + " ".join(f"0x{value:02X}" for value in range(256))
                + " 0x00)"
            ),
            "byte class exceeds 256 members",
        ),
        (
            _valid_limbu_map("UniClass [oversized] = (U+1000 .. U+1400)"),
            "Unicode class exceeds 1024 members",
        ),
        (
            _valid_limbu_map("\n".join(f"ByteClass [b{index}] = (0x41)" for index in range(129))),
            "byte classes exceed 128 entries",
        ),
        (
            _valid_limbu_map("\n".join(f"UniClass [u{index}] = (U+1901)" for index in range(129))),
            "byte-pass Unicode classes exceed 128 entries",
        ),
        (
            _valid_limbu_map(
                unicode_pass="Pass(Unicode)\n"
                + "\n".join(f"UniClass [u{index}] = (U+1901)" for index in range(129))
            ),
            "reorder classes exceed 128 entries",
        ),
        (
            _valid_limbu_map("\n".join("0x41 > U+1901" for _ in range(500))),
            "byte-rule sequence exceeds 512 entries",
        ),
        (
            _valid_limbu_map(" ".join(["0x41"] * 17) + " > U+1901"),
            "source rule exceeds 16 entries",
        ),
        (
            _valid_limbu_map("0x41 > " + " ".join(["U+1901"] * 33)),
            "target rule exceeds 32 entries",
        ),
    ],
)
def test_limbu_parser_enforces_every_declared_resource_bound(tmp_path, map_text, message):
    map_path = tmp_path / "bounded.map"
    map_path.write_text(map_text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        LimbuConverter.from_map_file(map_path)


def test_limbu_parser_accepts_exact_file_line_and_line_count_limits(tmp_path):
    base_map = _valid_limbu_map()
    exact_file = tmp_path / "exact-bytes.map"
    exact_file.write_text(
        _pad_map_to_exact_bytes(base_map, limbu_module._MAX_MAP_FILE_BYTES),
        encoding="utf-8",
    )
    assert exact_file.stat().st_size == limbu_module._MAX_MAP_FILE_BYTES
    assert len(LimbuConverter.from_map_file(exact_file)._rules) == 14

    base_lines = base_map.splitlines()
    exact_lines = tmp_path / "exact-lines.map"
    exact_lines.write_text(
        base_map + ";\n" * (limbu_module._MAX_MAP_LINES - len(base_lines)),
        encoding="utf-8",
    )
    assert len(exact_lines.read_text(encoding="utf-8").splitlines()) == 4096
    assert len(LimbuConverter.from_map_file(exact_lines)._rules) == 14

    exact_line = tmp_path / "exact-line-codepoints.map"
    exact_line.write_text(
        base_map + ";" * limbu_module._MAX_MAP_LINE_CODEPOINTS + "\n",
        encoding="utf-8",
    )
    assert max(len(line) for line in exact_line.read_text(encoding="utf-8").splitlines()) == 4096
    assert len(LimbuConverter.from_map_file(exact_line)._rules) == 14


@pytest.mark.parametrize(
    "byte_body",
    [
        "ByteClass [all_bytes] = (0x00 .. 0xFF)",
        "UniClass [all_scalars] = (U+1000 .. U+13FF)",
        "\n".join(f"ByteClass [b{index}] = (0x41)" for index in range(128)),
        "\n".join(f"UniClass [u{index}] = (U+1901)" for index in range(128)),
    ],
)
def test_limbu_parser_accepts_exact_class_member_and_inventory_limits(tmp_path, byte_body):
    map_path = tmp_path / "exact-class-bound.map"
    map_path.write_text(_valid_limbu_map(byte_body), encoding="utf-8")
    assert len(LimbuConverter.from_map_file(map_path)._rules) == 13


def test_limbu_parser_accepts_exact_flattened_rule_limit(tmp_path):
    map_path = tmp_path / "exact-flattened-rules.map"
    map_path.write_text(_flat_class_map(256), encoding="utf-8")
    converter = LimbuConverter.from_map_file(map_path)
    assert len(converter._rules) == limbu_module._MAX_BYTE_RULES


def test_limbu_parser_accepts_exact_source_and_target_sequence_limits(tmp_path):
    source = " ".join(["0x41"] * limbu_module._MAX_SOURCE_LENGTH)
    target = " ".join(["U+1901"] * limbu_module._MAX_TARGET_LENGTH)
    map_path = tmp_path / "exact-sequence-bounds.map"
    map_path.write_text(_valid_limbu_map(f"{source} > {target}"), encoding="utf-8")

    result = LimbuConverter.from_map_file(map_path).convert("A" * limbu_module._MAX_SOURCE_LENGTH)
    assert result.unicode_text == "ᤁ" * limbu_module._MAX_TARGET_LENGTH
    assert result.replacement_count == 1


def test_limbu_parser_rejects_class_expansion_past_flattened_rule_limit(tmp_path):
    map_path = tmp_path / "too-many-flattened-rules.map"
    map_path.write_text(_flat_class_map(257), encoding="utf-8")
    with pytest.raises(ValueError, match="byte-rule sequence exceeds 512 entries"):
        LimbuConverter.from_map_file(map_path)


def test_limbu_parser_rejects_non_ascii_class_identifiers(tmp_path):
    map_path = tmp_path / "identifier.map"
    map_path.write_text(
        _valid_limbu_map("ByteClass [bét] = (0x41)"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid Limbu byte class name"):
        LimbuConverter.from_map_file(map_path)


def test_limbu_parser_applies_structural_identity_policy_after_flattening(tmp_path):
    map_path = tmp_path / "structural.map"
    map_path.write_text(
        _valid_limbu_map(
            "ByteClass [protected] = (0x20)\nUniClass [unsafe] = (U+1901)\n[protected] > [unsafe]"
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="C0 and SPACE"):
        LimbuConverter.from_map_file(map_path)


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


@pytest.mark.parametrize(
    "rules",
    [
        "not-rules",
        b"not-rules",
        {"source": ((0x41,), (0x1901,))},
        {((0x41,), (0x1901,))},
        ["not-a-rule"],
        [{"source": (0x41,), "target": (0x1901,)}],
        [((0x41,), (0x1901,), (0x1902,))],
        [("A", (0x1901,))],
        [((0x41,), "ᤁ")],
        [({0x41}, (0x1901,))],
        [((0x41,), {0x1901})],
    ],
)
def test_limbu_constructor_rejects_unordered_or_ambiguous_containers(rules):
    with pytest.raises(ValueError):
        LimbuConverter(rules)


def test_limbu_constructor_bounds_outer_rule_and_nested_iterables():
    with pytest.raises(ValueError, match="byte-rule sequence exceeds 512 entries"):
        LimbuConverter(repeat(((0x41,), (0x1901,))))
    with pytest.raises(ValueError, match="byte rule exceeds 2 entries"):
        LimbuConverter([repeat((0x41,))])
    with pytest.raises(ValueError, match="source rule exceeds 16 entries"):
        LimbuConverter([(repeat(0x41), (0x1901,))])
    with pytest.raises(ValueError, match="target rule exceeds 32 entries"):
        LimbuConverter([((0x41,), repeat(0x1901))])


def test_limbu_constructor_accepts_each_exact_sequence_limit():
    source = (0x41,) * limbu_module._MAX_SOURCE_LENGTH
    target = (0x1901,) * limbu_module._MAX_TARGET_LENGTH
    bounded_rule = LimbuConverter([(source, target)]).convert("A" * len(source))
    assert bounded_rule.unicode_text == "ᤁ" * len(target)
    assert bounded_rule.replacement_count == 1

    sources = [(first, second) for first in range(0x21, 0x24) for second in range(0x21, 0x100)][
        : limbu_module._MAX_BYTE_RULES
    ]
    converter = LimbuConverter((source_value, (0x1901,)) for source_value in sources)
    assert len(converter._rules) == limbu_module._MAX_BYTE_RULES


def test_limbu_constructor_accepts_all_c0_and_space_singleton_identities():
    rules = [((value,), (value,)) for value in range(0x21)]
    text = "".join(chr(value) for value in range(0x21))
    result = LimbuConverter(rules).convert(text)

    assert result.unicode_text == text
    assert result.replacement_count == 33
    assert len(result.unmapped_codepoints) == 29


def test_namdhinggo_legacy_produces_unicode_limbu():
    # Representative Limbu/Sirijonga legacy span bytes.
    out = convert_limbu("kfMG g' ;fK;SF[ yf]af]cf")
    assert _has_limbu(out)
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
    res = LimbuConverter.default().convert("k \t\r\n")
    assert res.unicode_text == "ᤐ \t\r\n"
    assert res.replacement_count == 5
    assert res.unmapped_codepoints == []
    assert hashlib.sha256(res.unicode_text[1:].encode("utf-8")).hexdigest() == (
        "bb403f616bb62f0c473c42534601e3d8fe24fa61add49f51f4cdba8bd585ce29"
    )

    c0_and_space = "".join(chr(value) for value in range(0x21))
    aggregate = LimbuConverter.default().convert(c0_and_space)
    assert aggregate.unicode_text == c0_and_space
    assert aggregate.replacement_count == 33
    assert len(aggregate.unmapped_codepoints) == 29
    assert hashlib.sha256(aggregate.unicode_text.encode("utf-8")).hexdigest() == (
        "5d8fcfefa9aeeb711fb8ed1e4b7d5c8a9bafa46e8e76e68aa18adce5a10df6ab"
    )


def test_custom_limbu_rules_preserve_unmatched_structural_whitespace_cleanly():
    converter = LimbuConverter([((0x30,), (0x1946,))])
    result = converter.convert(" \t\r\n")
    assert result.unicode_text == " \t\r\n"
    assert result.replacement_count == 0
    assert result.unmapped_codepoints == []


@pytest.mark.parametrize(
    "rules",
    [
        [((0x09,), (0x1901,))],
        [((0x20,), (0x1901,))],
        [((0x09, 0x41), (0x1901,))],
        [((0x41,), (0x09,))],
        [((0x41,), (0x1901, 0x20))],
    ],
)
def test_limbu_rules_cannot_consume_or_synthesize_c0_and_space(rules):
    with pytest.raises(ValueError, match="C0 and SPACE"):
        LimbuConverter(rules)


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
        _valid_limbu_map(
            """ByteClass [bytes] = (0x30 0x31..0x32)
UniClass [digits] = (U+1946 U+1947 .. U+1948)
[bytes] <> [digits]
"""
        ),
        encoding="utf-8",
    )

    converter = LimbuConverter.from_map_file(map_path)
    result = converter.convert("012A")
    assert result.unicode_text == "᥆᥇᥈A"
    assert result.replacement_count == 3
    assert result.unmapped_codepoints == ["U+0041"]


def test_limbu_parser_rejects_byte_class_syntax_in_the_unicode_pass(tmp_path):
    map_path = tmp_path / "wrong-pass.map"
    unicode_pass = """Pass(Unicode)
ByteClass [ignored_bytes] = (0x41)
UniClass [VOWEL] = ( U+1920 .. U+1928 )
UniClass [SUBJ] = ( U+1929 .. U+192B )
[VOWEL]=V [SUBJ]=S <> @S @V
[VOWEL]=V U+193A [SUBJ]=S <> @S @V U+193A
"""
    map_path.write_text(_valid_limbu_map(unicode_pass=unicode_pass), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported Limbu Unicode-pass syntax"):
        LimbuConverter.from_map_file(map_path)


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
