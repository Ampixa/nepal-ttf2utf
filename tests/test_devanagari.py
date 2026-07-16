"""Pinned Devanagari dependency-contract and conversion tests."""

import hashlib
import itertools
import json
from importlib import metadata
from pathlib import Path

import pytest

from nepal_ttf2utf import convert, devanagari
from nepal_ttf2utf.devanagari import convert_devanagari, supported_devanagari_fonts


def _installed_dependency_map() -> bytes:
    distribution = metadata.distribution("npttf2utf")
    assert distribution.version == "0.3.7"
    return Path(distribution.locate_file("npttf2utf/map.json")).read_bytes()


def _independent_semantic_payload(document: dict[str, object]) -> bytes:
    def codepoints(value: str) -> list[int]:
        return [ord(character) for character in value]

    payload = []
    for font_name in sorted(document):
        record = document[font_name]
        assert isinstance(record, dict)
        rules = record["rules"]
        assert isinstance(rules, dict)
        character_map = rules["character-map"]
        assert isinstance(character_map, dict)
        payload.append(
            [
                font_name,
                record["version"],
                [
                    [codepoints(source), codepoints(target)]
                    for source, target in sorted(character_map.items())
                ],
                [
                    [codepoints(pattern), codepoints(replacement)]
                    for pattern, replacement in rules["pre-rules"]
                ],
                [
                    [codepoints(pattern), codepoints(replacement)]
                    for pattern, replacement in rules["post-rules"]
                ],
            ]
        )
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def test_exact_npttf2utf_dependency_contract_is_independently_pinned():
    raw = _installed_dependency_map()
    assert len(raw) == 34_197
    assert hashlib.sha256(raw).hexdigest() == (
        "66a0a91f1209eb1c73540e443144f306d6daf27c426c09d24ec307a1506212e5"
    )
    document = json.loads(raw)
    inventories = {
        "FONTASY_HIMALI_TT": ("v0.01", 124, 1, 0, 32),
        "Kantipur": ("v0.01", 144, 0, 0, 32),
        "PCS NEPALI": ("v0.1a", 120, 0, 0, 32),
        "Preeti": ("v0.01", 136, 0, 0, 32),
        "Sagarmatha": ("v0.1a", 144, 0, 0, 32),
    }
    assert set(document) == set(inventories)
    for font_name, expected in inventories.items():
        record = document[font_name]
        rules = record["rules"]
        character_map = rules["character-map"]
        actual = (
            record["version"],
            len(character_map),
            sum(not target for target in character_map.values()),
            len(rules["pre-rules"]),
            len(rules["post-rules"]),
        )
        assert actual == expected
    assert all(
        document[font_name]["rules"]["post-rules"] == document["Preeti"]["rules"]["post-rules"]
        for font_name in document
    )

    semantic = _independent_semantic_payload(document)
    assert len(semantic) == 18_263
    assert hashlib.sha256(semantic).hexdigest() == (
        "d908813c55a66726534a3d617cf4b13d0f94134e1e7d563ad5ab5dce9938313e"
    )

    contract = devanagari._dependency_contract()
    assert contract.dependency_version == "0.3.7"
    assert (contract.map_size, contract.map_sha256) == (
        len(raw),
        hashlib.sha256(raw).hexdigest(),
    )
    assert (contract.semantic_size, contract.semantic_sha256) == (
        len(semantic),
        hashlib.sha256(semantic).hexdigest(),
    )
    assert {
        font_name: (
            rules.version,
            len(rules.character_map),
            len(rules.pre_rules),
            len(rules.post_rules),
        )
        for font_name, rules in contract.fonts.items()
    } == {
        font_name: (version, entries, pre_rules, post_rules)
        for font_name, (version, entries, _empty, pre_rules, post_rules) in inventories.items()
    }


def test_dependency_and_route_snapshots_are_transitively_immutable():
    contract = devanagari._dependency_contract()
    with pytest.raises(TypeError):
        contract.fonts["unexpected"] = contract.fonts["Preeti"]
    with pytest.raises(TypeError):
        contract.fonts["Preeti"].character_map["g"] = "x"
    with pytest.raises(TypeError):
        devanagari._NPTTF2UTF_FONTS["unexpected"] = "Preeti"
    with pytest.raises(TypeError):
        devanagari._PREETI_FAMILY_EXT["nayanepal"]["†"] = "x"


def test_invalid_font_type_fails_before_dependency_access(monkeypatch):
    def unexpected_dependency_access():
        raise AssertionError("dependency loaded before font validation")

    monkeypatch.setattr(devanagari, "_dependency_contract", unexpected_dependency_access)
    with pytest.raises(TypeError, match=r"^font must be a string$"):
        convert_devanagari("", font=[])


def test_dependency_contract_rejects_altered_bytes_and_duplicate_json_keys(monkeypatch):
    raw = _installed_dependency_map()
    with pytest.raises(RuntimeError, match="size"):
        devanagari._parse_dependency_map(raw + b" ")
    with pytest.raises(RuntimeError, match="SHA-256"):
        devanagari._parse_dependency_map(raw[:-1] + bytes([raw[-1] ^ 1]))
    with pytest.raises(RuntimeError, match="duplicate JSON key"):
        devanagari._unique_json_object([("font", 1), ("font", 2)])

    class WrongVersionDistribution:
        version = "0.3.6"

    monkeypatch.setattr(
        devanagari.metadata, "distribution", lambda _name: WrongVersionDistribution()
    )
    with pytest.raises(RuntimeError, match=r"0\.3\.6.*0\.3\.7"):
        devanagari._load_dependency_contract()


def test_preeti_known_words():
    assert convert("g]kfn", font="preeti") == "नेपाल"
    assert convert("du/", font="preeti") == "मगर"


def test_nayanepal_gorkhapatra_anchors():
    # Real Gorkhapatra masthead spans (legacy bytes incl. control chars + ƒ extension).
    assert "गोरखापत्र" in convert("uf]\x03ƒvfkqåfƒf", font="nayanepal")
    assert convert("k|sflzt", font="nayanepal") == "प्रकाशित"
    # ƒ -> र extension specifically (would be गोƒखापत्र without it).
    assert "ƒ" not in convert("uf]\x03ƒvfkqåfƒf", font="nayanepal")


def test_nayanepal_output_is_clean_devanagari():
    res = convert_devanagari("clgn a'9fduƒ,", font="nayanepal")
    assert res.clean
    assert res.unicode_text.startswith("अनिल")


def test_devanagari_preserves_structural_whitespace_but_cleans_other_c0_controls():
    res = convert_devanagari("g]kfn\t\r\n\x03du/", font="preeti")
    assert res.unicode_text == "नेपाल\t\r\nमगर"
    assert not res.clean
    assert res.leftover == ["\x03"]
    with pytest.raises(ValueError, match=r"U\+0003"):
        convert_devanagari("g]kfn\t\r\n\x03du/", font="preeti", strict=True)


def test_strict_mode_surfaces_leftovers():
    # An unmapped byte (á / U+00E1) should raise in strict mode rather than pass silently.
    with pytest.raises(ValueError):
        convert_devanagari("áá", font="preeti", strict=True)
    # ... and be reported (not dropped) in lenient mode.
    res = convert_devanagari("áá", font="preeti")
    assert not res.clean and "á" in res.leftover


@pytest.mark.parametrize("font", supported_devanagari_fonts())
def test_strict_mode_reports_dependency_deleting_post_rule(font):
    source = r"\f"
    result = convert_devanagari(source, font=font)
    assert result.unicode_text == ""
    assert result.leftover == ["\\", "f"]
    assert not result.clean

    with pytest.raises(ValueError, match=r"U\+005C.*U\+0066"):
        convert_devanagari(source, font=font, strict=True)
    with pytest.raises(ValueError, match=r"U\+005C.*U\+0066"):
        convert(source, font=font, strict=True)


def test_fontasy_empty_character_map_entry_is_reported():
    result = convert_devanagari("»", font="fontasy-himali")
    assert result.unicode_text == ""
    assert result.leftover == ["»"]
    assert not result.clean
    with pytest.raises(ValueError, match=r"U\+00BB"):
        convert("»", font="fontasy-himali", strict=True)


def test_dependency_empty_mappings_and_fully_consumed_deletions_are_diagnostic():
    contract = devanagari._dependency_contract()
    base_fonts = {
        **devanagari._NPTTF2UTF_FONTS,
        **{font: "Preeti" for font in devanagari._PREETI_FAMILY_EXT},
    }
    for font, base_font in base_fonts.items():
        rules = contract.fonts[base_font]
        assert rules.pre_rules == ()
        deleting_patterns = [rule.compiled for rule in rules.post_rules if not rule.replacement]
        assert deleting_patterns

        character_map = rules.character_map
        for source, target in character_map.items():
            if target:
                continue
            result = convert_devanagari(source, font=font)
            assert source in result.leftover

        keys = tuple(character_map)
        for length in (1, 2):
            for source_values in itertools.product(keys, repeat=length):
                mapped = "".join(character_map[value] for value in source_values)
                if not any(pattern.search(mapped) for pattern in deleting_patterns):
                    continue
                source = "".join(source_values)
                result = convert_devanagari(source, font=font)
                if result.unicode_text:
                    assert not set(source) & set(result.leftover)
                else:
                    assert set(source) <= set(result.leftover)


@pytest.mark.parametrize("font", supported_devanagari_fonts())
@pytest.mark.parametrize("source", [r"s\f", r"\fs", r"s\fs"])
def test_fully_consumed_deletion_is_reported_inside_nonempty_word(font, source):
    result = convert_devanagari(source, font=font)
    assert result.unicode_text
    assert result.leftover == ["\\", "f"]
    assert not result.clean

    with pytest.raises(ValueError, match=r"U\+005C.*U\+0066"):
        convert_devanagari(source, font=font, strict=True)
    with pytest.raises(ValueError, match=r"U\+005C.*U\+0066"):
        convert(source, font=font, strict=True)


@pytest.mark.parametrize("font", supported_devanagari_fonts())
@pytest.mark.parametrize("source", ["Sf", "0f"])
def test_deleting_post_rule_remains_clean_when_it_produces_valid_output(font, source):
    result = convert_devanagari(source, font=font, strict=True)
    assert result.unicode_text
    assert result.leftover == []
    assert result.clean
    assert convert(source, font=font, strict=True) == result.unicode_text


@pytest.mark.parametrize("font", supported_devanagari_fonts())
@pytest.mark.parametrize(("source", "expected"), [("lक", "कि"), ("कM", "कः")])
def test_mixed_unicode_devanagari_keeps_dependency_word_context(font, source, expected):
    result = convert_devanagari(source, font=font, strict=True)
    assert result.unicode_text == expected
    assert result.leftover == []
    assert result.clean
    assert convert(source, font=font, strict=True) == expected


@pytest.mark.parametrize(
    (
        "font",
        "output_characters",
        "utf8_bytes",
        "devanagari_characters",
        "leftover_count",
        "output_sha256",
        "leftover_payload_size",
        "leftover_sha256",
    ),
    [
        (
            "fontasy-himali",
            290,
            747,
            177,
            132,
            "14a85e92c514eb8c205b8f5c095659da2c76a5c31c15bf549d59e39e0f4173d4",
            493,
            "8a9e5c0b7103ca72aa87b56a3e286fe2d85bf523476466ccae4951d699058645",
        ),
        (
            "gorkhapatra",
            299,
            767,
            184,
            130,
            "f533df25050685b6a7417575da8aa913b90bf17222a7df4fe335d1b4a86304ed",
            482,
            "57a24105c0f223df7dc9fe483222a806472f6b0cec0fef8591c90b32b11495b5",
        ),
        (
            "kantipur",
            301,
            784,
            192,
            126,
            "ce497ef1c98d47cf382771bab104c50f895a0662cb1d94d381f772fc12e8ed52",
            470,
            "c21ed7c177ead28cc354588d9e5308e68956ad7a94dda6f815642d1ae4a9ffd6",
        ),
        (
            "nayanepal",
            299,
            767,
            184,
            130,
            "f533df25050685b6a7417575da8aa913b90bf17222a7df4fe335d1b4a86304ed",
            482,
            "57a24105c0f223df7dc9fe483222a806472f6b0cec0fef8591c90b32b11495b5",
        ),
        (
            "pcs-nepali",
            291,
            749,
            176,
            134,
            "b531e673e085b9d19eadf3133821d7d79f5533f7c3d856b3c656ccb4fb535659",
            501,
            "2f239007993a3057ca417ae2666a52c79555a123483c629a0f4c4cbc65dd4791",
        ),
        (
            "preeti",
            299,
            767,
            184,
            130,
            "f533df25050685b6a7417575da8aa913b90bf17222a7df4fe335d1b4a86304ed",
            482,
            "57a24105c0f223df7dc9fe483222a806472f6b0cec0fef8591c90b32b11495b5",
        ),
        (
            "sagarmatha",
            299,
            776,
            190,
            126,
            "0358195c277f097e76f39022378cd1561607846bf3074a17191f1cd5a9d58569",
            468,
            "864820e82809251f000d79c2e34a58ffdb8fa1bc9ecad5d1ece8813cf56e649c",
        ),
    ],
)
def test_ordered_byte_domain_and_diagnostics_are_independently_pinned(
    font,
    output_characters,
    utf8_bytes,
    devanagari_characters,
    leftover_count,
    output_sha256,
    leftover_payload_size,
    leftover_sha256,
):
    source = "".join(chr(codepoint) for codepoint in range(0x100))
    result = convert_devanagari(source, font=font)
    encoded = result.unicode_text.encode("utf-8")
    leftover_payload = json.dumps(
        [ord(character) for character in result.leftover], separators=(",", ":")
    ).encode("ascii")
    assert len(result.unicode_text) == output_characters
    assert len(encoded) == utf8_bytes
    assert sum(0x0900 <= ord(character) <= 0x097F for character in result.unicode_text) == (
        devanagari_characters
    )
    assert not result.clean
    assert len(result.leftover) == leftover_count
    assert hashlib.sha256(encoded).hexdigest() == output_sha256
    assert len(leftover_payload) == leftover_payload_size
    assert hashlib.sha256(leftover_payload).hexdigest() == leftover_sha256


@pytest.mark.parametrize("font", ["nayanepal", "gorkhapatra"])
def test_preeti_family_extensions_enter_before_post_rules(font):
    reordered = convert_devanagari("l†", font=font, strict=True)
    assert reordered.unicode_text == "ि्"
    assert reordered.clean and reordered.leftover == []

    deleted = convert_devanagari("†f", font=font)
    assert deleted.unicode_text == ""
    assert deleted.leftover == ["f", "†"]
    assert not deleted.clean
    embedded = convert_devanagari("s†f", font=font)
    assert embedded.unicode_text == "क"
    assert embedded.leftover == ["f", "†"]
    assert not embedded.clean
    with pytest.raises(ValueError, match=r"U\+0066.*U\+2020"):
        convert_devanagari("†f", font=font, strict=True)


@pytest.mark.parametrize("font", ["nayanepal", "gorkhapatra"])
@pytest.mark.parametrize(("extension", "canonical"), [("†", "\\"), ("ƒ", "/")])
def test_preeti_family_extensions_match_canonical_targets_in_all_byte_contexts(
    font, extension, canonical
):
    for codepoint in range(0x100):
        context = chr(codepoint)
        for extension_source, canonical_source in (
            (context + extension, context + canonical),
            (extension + context, canonical + context),
        ):
            actual = convert_devanagari(extension_source, font=font)
            expected = convert_devanagari(canonical_source, font=font)
            assert actual.unicode_text == expected.unicode_text
            assert {
                canonical if character == extension else character for character in actual.leftover
            } == set(expected.leftover)


def test_post_rule_subject_limit_is_enforced_before_regex_evaluation():
    exact_mapped = convert_devanagari("I" * 1024, font="preeti", strict=True)
    assert exact_mapped.unicode_text == "क्ष्" * 1024
    for strict in (False, True):
        with pytest.raises(ValueError, match=r"mapped.*segment.*4096"):
            convert_devanagari("I" * 1025, font="preeti", strict=strict)
    exact_post_rule_expansion = convert_devanagari("{" * 2048, font="preeti", strict=True)
    assert exact_post_rule_expansion.unicode_text == "र्" * 2048
    for strict in (False, True):
        with pytest.raises(ValueError, match=r"mapped.*segment.*4096"):
            convert_devanagari("{" * 2049, font="preeti", strict=strict)

    exact_source = convert_devanagari("उ" * 4096, font="preeti", strict=True)
    assert exact_source.unicode_text == "उ" * 4096
    for strict in (False, True):
        with pytest.raises(ValueError, match=r"source.*segment.*4096"):
            convert_devanagari("उ" * 4097, font="preeti", strict=strict)
    separated = convert_devanagari("उ" * 4096 + "\t" + "उ" * 4096, strict=True)
    assert separated.unicode_text == "उ" * 4096 + "\t" + "उ" * 4096
    for strict in (False, True):
        with pytest.raises(ValueError, match=r"source.*segment.*4096"):
            convert_devanagari("उ" * 4096 + "\x03" + "उ", strict=strict)


def test_mixed_unicode_devanagari_is_preserved_before_legacy_mapping():
    source = "g]kfn\u0903\u1cd0\ua8e0\U00011b00"
    expected = "नेपाल\u0903\u1cd0\ua8e0\U00011b00"
    result = convert_devanagari(source, font="preeti", strict=True)
    assert result.unicode_text == expected
    assert result.leftover == []
    assert result.clean


def test_unknown_font_raises():
    with pytest.raises(ValueError):
        convert("abc", font="not-a-font")


def test_supported_fonts_listed():
    fonts = supported_devanagari_fonts()
    assert "nayanepal" in fonts and "preeti" in fonts
