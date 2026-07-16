#!/usr/bin/env python3
"""Smoke resource-backed routes from an installed wheel, outside the source tree."""

from __future__ import annotations

import hashlib
import json
import subprocess
from importlib import metadata, resources
from pathlib import Path
from types import MappingProxyType

import nepal_ttf2utf
from nepal_ttf2utf import (
    UNICODE_REPERTOIRE_VERSION,
    VIDEHA_2008_04_15,
    VIDEHA_ISSUE_001,
    JGLepchaConverter,
    KiratRaiConverter,
    LepchaConverter,
    LimbuConverter,
    OLChikiConverter,
    OLChikiLaticConverter,
    TibetanMachineConverter,
    TirhutaConverter,
    convert_devanagari,
    convert_jg_lepcha,
    convert_kiratrai,
    convert_kiratrai_herald,
    convert_lepcha,
    convert_limbu,
    convert_olchiki,
    convert_olchiki_latic,
    convert_sunuwar,
    convert_tibetanmachine,
    convert_tirhuta,
    janaki_gid_map_sha256,
    recover_videha_janaki_trace,
    supported_fonts,
    supported_unicode_scripts,
    transliterate_magar_akkha,
    validate_unicode_span,
)
from nepal_ttf2utf import unicode_span as unicode_span_module

EXPECTED_RESOURCES = {
    "JGLepcha.map",
    "LICENSE.magar-toolkit-MIT.txt",
    "LICENSE.py-tiblegenc-APACHE-2.0.txt",
    "LICENSE.unicode-data.txt",
    "LICENSE.wsresources-MIT.txt",
    "Limbu.map",
    "TibetanMachine.csv",
    "__init__.py",
    "kiratraifontnew.map",
    "olck_optimum.json",
    "sikkim_herald_lepcha.json",
}
EXPECTED_LICENSE_FILES = {
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "src/nepal_ttf2utf/maps/LICENSE.magar-toolkit-MIT.txt",
    "src/nepal_ttf2utf/maps/LICENSE.py-tiblegenc-APACHE-2.0.txt",
    "src/nepal_ttf2utf/maps/LICENSE.unicode-data.txt",
    "src/nepal_ttf2utf/maps/LICENSE.wsresources-MIT.txt",
}


class _IntSubclass(int):
    pass


def main() -> int:
    repository_source = Path(__file__).resolve().parents[1] / "src"
    imported_from = Path(nepal_ttf2utf.__file__).resolve()
    try:
        imported_from.relative_to(repository_source)
    except ValueError:
        pass
    else:
        raise AssertionError(f"smoke imported the source checkout: {imported_from}")

    route_groups = nepal_ttf2utf._FONT_ROUTE_GROUPS
    assert isinstance(route_groups, MappingProxyType)
    assert len(route_groups) == 22
    assert all(isinstance(aliases, frozenset) for _, aliases, _ in route_groups.values())
    route_aliases = set().union(*(aliases for _, aliases, _ in route_groups.values()))
    assert sum(len(aliases) for _, aliases, _ in route_groups.values()) == 146
    assert len(route_aliases) == 146

    font_inventory = supported_fonts()
    assert type(font_inventory) is dict
    assert len(font_inventory) == 146
    assert route_aliases == set(font_inventory)
    assert all(nepal_ttf2utf._normalize_font_key(alias) == alias for alias in font_inventory)
    assert isinstance(nepal_ttf2utf._SUPPORTED_FONT_SCRIPTS, MappingProxyType)
    assert isinstance(nepal_ttf2utf._UNICODE_FONT_SCRIPTS, MappingProxyType)
    assert isinstance(nepal_ttf2utf._FONT_ALIAS_ROUTES, MappingProxyType)
    assert dict(nepal_ttf2utf._SUPPORTED_FONT_SCRIPTS) == font_inventory
    assert set(nepal_ttf2utf._FONT_ALIAS_ROUTES) == set(font_inventory)

    second_font_inventory = supported_fonts()
    assert second_font_inventory is not font_inventory
    assert second_font_inventory == font_inventory
    second_font_inventory["installed-smoke-mutation"] = "Newa"
    assert supported_fonts() == font_inventory

    invalid_text_calls = (
        ("dispatcher", lambda: nepal_ttf2utf.convert([], font="preeti")),
        ("converter method", lambda: LimbuConverter.default().convert([])),
    )
    for surface, call in invalid_text_calls:
        try:
            call()
        except TypeError as error:
            assert str(error) == "text must be a string", surface
        else:
            raise AssertionError(f"installed {surface} accepted non-string text")

    invalid_selector_calls = (
        ("dispatcher font", "font must be a string", lambda: nepal_ttf2utf.convert("", font=[])),
        (
            "Devanagari font",
            "font must be a string",
            lambda: convert_devanagari("", font=[]),
        ),
        (
            "Unicode script",
            "script must be a string",
            lambda: validate_unicode_span("", script=[]),
        ),
    )
    for surface, message, call in invalid_selector_calls:
        try:
            call()
        except TypeError as error:
            assert str(error) == message, surface
        else:
            raise AssertionError(f"installed {surface} accepted a non-string selector")

    invalid_integer_contracts = (
        (
            "Kirat Rai",
            lambda: KiratRaiConverter([((_IntSubclass(0x41),), (0x16D43,))]),
        ),
        ("Limbu", lambda: LimbuConverter([((_IntSubclass(0x41),), (0x1901,))])),
        (
            "JG Lepcha",
            lambda: JGLepchaConverter([((_IntSubclass(0x41),), (0x1C00,))], [], {}, None),
        ),
        ("Herald Lepcha", lambda: LepchaConverter({_IntSubclass(0x41): (0x1C00,)})),
        ("Ol Chiki", lambda: OLChikiConverter({_IntSubclass(0x61): 0x1C5F})),
        ("Ol Chiki Latic", lambda: OLChikiLaticConverter({_IntSubclass(0x61): 0x1C5F})),
        ("TibetanMachine", lambda: TibetanMachineConverter({_IntSubclass(0x21): "ཀ"})),
    )
    for surface, call in invalid_integer_contracts:
        try:
            call()
        except ValueError as error:
            assert str(error).endswith("must be an int"), surface
        else:
            raise AssertionError(f"installed {surface} accepted an integer subclass")

    font_inventory_payload = json.dumps(
        font_inventory, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    assert len(font_inventory_payload) == 4_196
    assert hashlib.sha256(font_inventory_payload).hexdigest() == (
        "dd2adfacfed5310d843363fac313fe2e52f7c20a66a2fa788af953904c2221ca"
    )

    unicode_font_scripts = nepal_ttf2utf._UNICODE_FONT_SCRIPTS
    assert len(unicode_font_scripts) == 100
    assert set(unicode_font_scripts) < set(font_inventory)
    assert all(font_inventory[alias] == script for alias, script in unicode_font_scripts.items())
    expected_unicode_font_scripts = {
        alias: script
        for script, aliases, is_unicode in route_groups.values()
        if is_unicode
        for alias in aliases
    }
    assert dict(unicode_font_scripts) == expected_unicode_font_scripts
    unicode_font_payload = json.dumps(
        dict(unicode_font_scripts), sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    assert len(unicode_font_payload) == 3_044
    assert hashlib.sha256(unicode_font_payload).hexdigest() == (
        "a59cf6d6bff2cd2693bac77ea1fc50e74d7fa0d365528abcf5a460c178bad78f"
    )

    supported_scripts = supported_unicode_scripts()
    assert len(supported_scripts) == 11
    assert set(unicode_font_scripts.values()) == set(supported_scripts)
    supported_scripts_payload = json.dumps(
        supported_scripts, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    assert len(supported_scripts_payload) == 115
    assert hashlib.sha256(supported_scripts_payload).hexdigest() == (
        "ea2615e345153f2500d29428d73dd02c20131a773ccc5f34076d6e3361da3aa3"
    )

    script_anchors = {
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
    assert set(script_anchors) == set(supported_scripts)
    for alias, script in unicode_font_scripts.items():
        anchor = chr(script_anchors[script])
        assert nepal_ttf2utf.convert(anchor, font=alias, strict=True) == anchor

    repertoire_mappings = (
        unicode_span_module._ASSIGNED_BLOCK_RANGES,
        unicode_span_module._SCRIPT_RANGES,
        unicode_span_module._SCRIPT_BLOCK_RANGES,
    )
    assert all(isinstance(mapping, MappingProxyType) for mapping in repertoire_mappings)
    assert all(
        isinstance(ranges, tuple) and all(isinstance(item, tuple) for item in ranges)
        for mapping in repertoire_mappings
        for ranges in mapping.values()
    )
    unicode_repertoire_contract = {
        "version": UNICODE_REPERTOIRE_VERSION,
        "assigned": {
            script: [list(item) for item in ranges]
            for script, ranges in unicode_span_module._ASSIGNED_BLOCK_RANGES.items()
        },
        "scripts": {
            script: [list(item) for item in ranges]
            for script, ranges in unicode_span_module._SCRIPT_RANGES.items()
        },
        "blocks": {
            script: [list(item) for item in ranges]
            for script, ranges in unicode_span_module._SCRIPT_BLOCK_RANGES.items()
        },
        "canonical_decompositions": [
            [composed, list(decomposed)]
            for composed, decomposed in unicode_span_module._PINNED_CANONICAL_DECOMPOSITIONS.items()
        ],
        "canonical_combining_classes": [
            list(item) for item in unicode_span_module._PINNED_CANONICAL_COMBINING_CLASSES.items()
        ],
    }
    unicode_repertoire_payload = json.dumps(
        unicode_repertoire_contract, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    assert len(unicode_repertoire_payload) == 1_757
    assert hashlib.sha256(unicode_repertoire_payload).hexdigest() == (
        "b34edb816eafd1b66ae5911d7e4120df1fd4a3d0a737a55e5a4e4f3077e7f469"
    )

    map_package = resources.files("nepal_ttf2utf.maps")
    actual_resources = {entry.name for entry in map_package.iterdir() if entry.is_file()}
    assert actual_resources == EXPECTED_RESOURCES
    for name in EXPECTED_RESOURCES:
        assert (map_package / name).read_bytes()

    limbu_map = (map_package / "Limbu.map").read_bytes()
    assert len(limbu_map) == 5981
    assert hashlib.sha256(limbu_map).hexdigest() == (
        "2e9f6b8205a7facc0732f54c3dd4cc64f8344c7767acdbc12dd3c11cfb535f58"
    )
    jg_lepcha_map = (map_package / "JGLepcha.map").read_bytes()
    assert len(jg_lepcha_map) == 11_600
    assert hashlib.sha256(jg_lepcha_map).hexdigest() == (
        "179d172b4bd4223f40b1ddc1a0daeb6547b5ad97dc1be7df2b09f2bf45ff6b2d"
    )

    assert convert_limbu("k", strict=True) == "ᤐ"
    limbu = LimbuConverter.default()
    legacy_limbu_multibyte = limbu.convert("f]f}")
    assert legacy_limbu_multibyte.unicode_text == "\u1925\u1926"
    assert legacy_limbu_multibyte.replacement_count == 2
    assert legacy_limbu_multibyte.unmapped_codepoints == []
    legacy_limbu_pair = limbu.convert("H")
    assert legacy_limbu_pair.unicode_text == "\u192a\u1922"
    assert legacy_limbu_pair.replacement_count == 1
    legacy_limbu_triple = limbu.convert("LJ")
    assert legacy_limbu_triple.unicode_text == "\u192b\u1921\u193a"
    assert legacy_limbu_triple.replacement_count == 2
    native_limbu = "\u1922\u192a\u1922\u193a\u192a"
    native_limbu_result = limbu.convert(native_limbu)
    assert native_limbu_result.unicode_text == native_limbu
    assert native_limbu_result.replacement_count == 0
    mixed_limbu_pair = limbu.convert("'\u192a")
    assert mixed_limbu_pair.unicode_text == "\u1922\u192a"
    assert mixed_limbu_pair.replacement_count == 1
    mixed_limbu_triple = limbu.convert("L\u192b")
    assert mixed_limbu_triple.unicode_text == "\u1921\u193a\u192b"
    assert mixed_limbu_triple.replacement_count == 1
    unresolved_limbu = limbu.convert("#X")
    assert unresolved_limbu.unicode_text == "#X"
    assert unresolved_limbu.replacement_count == 0
    assert unresolved_limbu.unmapped_codepoints == ["U+0023", "U+0058"]
    try:
        convert_limbu("#X", strict=True)
    except ValueError as error:
        assert "U+0023 U+0058" in str(error)
    else:
        raise AssertionError("strict Limbu conversion accepted unresolved bytes")
    ordered_limbu = limbu.convert("".join(chr(value) for value in range(256)))
    assert len(ordered_limbu.unicode_text) == 258
    assert len(ordered_limbu.unicode_text.encode("utf-8")) == 516
    assert ordered_limbu.limbu_char_count == 62
    assert ordered_limbu.replacement_count == 129
    assert len(ordered_limbu.unmapped_codepoints) == 156
    assert hashlib.sha256(ordered_limbu.unicode_text.encode("utf-8")).hexdigest() == (
        "f9f55d84875b4a73e5e324e95c0d97fb156d164c9f6d44fef9cf6ca08cc526ca"
    )
    limbu_diagnostics = json.dumps(
        [int(label[2:], 16) for label in ordered_limbu.unmapped_codepoints],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(limbu_diagnostics) == 585
    assert hashlib.sha256(limbu_diagnostics).hexdigest() == (
        "bc2b21c6ff8ef6f3e3dfcc8253b4489b1a47fe4c3fc94f90e1b5414b6a50742e"
    )
    assert convert_kiratrai("a", strict=True).unicode_text == "𖵃"
    canonical_kirat_longest = convert_kiratrai("Aee", strict=True)
    assert canonical_kirat_longest.unicode_text == "\U00016d6a"
    assert canonical_kirat_longest.replacement_count == 1
    assert nepal_ttf2utf.convert("Aee", font="akrs-new", strict=True) == "\U00016d6a"
    try:
        convert_kiratrai("f", strict=True)
    except ValueError as error:
        assert "U+0066" in str(error)
    else:
        raise AssertionError("strict canonical Kirat Rai conversion accepted an unmapped byte")
    assert convert_kiratrai_herald("fZ0", strict=True).unicode_text == "𖵈 𖵰"
    assert nepal_ttf2utf.convert("fZ0", font="kiratrai-herald", strict=True) == "𖵈 𖵰"
    gurung_ordered = validate_unicode_span(
        "\U00016100\u0300\U0001612f", script="Gurung Khema", strict=True
    )
    assert gurung_ordered.unicode_text == "\U00016100\U0001612f\u0300"
    gurung_composed = validate_unicode_span(
        "\U0001611e\U00016123", script="Gurung Khema", strict=True
    )
    assert gurung_composed.unicode_text == "\U00016126"
    kirat_overlap = "\U00016d63\U00016d68"
    assert (
        validate_unicode_span(kirat_overlap, script="Kirat Rai", strict=True).unicode_text
        == "\U00016d6a"
    )
    assert convert_kiratrai(kirat_overlap, strict=True).unicode_text == "\U00016d6a"
    assert convert_kiratrai_herald(kirat_overlap, strict=True).unicode_text == "\U00016d6a"
    assert convert_jg_lepcha("k", strict=True).unicode_text == "ᰀ"
    contextual_jg_start = convert_jg_lepcha("a", strict=True)
    assert contextual_jg_start.unicode_text == "ᰦ"
    assert contextual_jg_start.replacement_count == 1
    contextual_jg_vowel = convert_jg_lepcha("Oa", strict=True)
    assert contextual_jg_vowel.unicode_text == "ᰨᰨ"
    assert contextual_jg_vowel.replacement_count == 2
    native_jg_lepcha = "\u1c27\u1c00"
    native_jg_result = convert_jg_lepcha(native_jg_lepcha, strict=True)
    assert native_jg_result.unicode_text == native_jg_lepcha
    assert native_jg_result.replacement_count == 0
    mixed_jg_result = convert_jg_lepcha("i\u1c00", strict=True)
    assert mixed_jg_result.unicode_text == native_jg_lepcha
    assert mixed_jg_result.replacement_count == 1
    mixed_jg_suffix = convert_jg_lepcha("\u1c27k", strict=True)
    assert mixed_jg_suffix.unicode_text == native_jg_lepcha
    assert mixed_jg_suffix.replacement_count == 1
    legacy_jg_reorder = convert_jg_lepcha("ik", strict=True)
    assert legacy_jg_reorder.unicode_text == "\u1c00\u1c27"
    assert legacy_jg_reorder.replacement_count == 2
    uncertain_jg = convert_jg_lepcha("<=>")
    assert uncertain_jg.unicode_text == "\u25cc\u25cc\u25cc"
    assert uncertain_jg.replacement_count == 3
    assert uncertain_jg.unmapped_codepoints == []
    assert uncertain_jg.uncertain_codepoints == ["U+003C", "U+003D", "U+003E"]
    try:
        convert_jg_lepcha("<=>", strict=True)
    except ValueError as error:
        assert "U+003C U+003D U+003E" in str(error)
        assert "U+25CC" in str(error)
    else:
        raise AssertionError("strict JG Lepcha conversion accepted uncertain placeholders")
    ordered_jg = convert_jg_lepcha("".join(chr(value) for value in range(256)))
    assert len(ordered_jg.unicode_text) == 319
    assert len(ordered_jg.unicode_text.encode("utf-8")) == 784
    assert ordered_jg.lepcha_char_count == 186
    assert ordered_jg.replacement_count == 160
    assert len(ordered_jg.unmapped_codepoints) == 125
    assert len(ordered_jg.uncertain_codepoints) == 3
    assert hashlib.sha256(ordered_jg.unicode_text.encode("utf-8")).hexdigest() == (
        "2f9413d6d9a14c8f2c4f76aa2585094bb711d25a9c5c14297a8ad5b1be3568c2"
    )
    jg_unmapped_diagnostics = json.dumps(
        [int(label[2:], 16) for label in ordered_jg.unmapped_codepoints],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(jg_unmapped_diagnostics) == 459
    assert hashlib.sha256(jg_unmapped_diagnostics).hexdigest() == (
        "93f28b95392eae866f7ca5be24259e297852e15da2ea69818a015a78522950bf"
    )
    jg_uncertain_diagnostics = json.dumps(
        [int(label[2:], 16) for label in ordered_jg.uncertain_codepoints],
        separators=(",", ":"),
    ).encode("ascii")
    assert len(jg_uncertain_diagnostics) == 10
    assert hashlib.sha256(jg_uncertain_diagnostics).hexdigest() == (
        "e1f8c6585e46e58a491c74d684740d52ef5a5a372db7505c77fa031685b8cb7f"
    )
    jg_strict_diagnostics = json.dumps(
        sorted(
            {
                int(label[2:], 16)
                for label in (ordered_jg.unmapped_codepoints + ordered_jg.uncertain_codepoints)
            }
        ),
        separators=(",", ":"),
    ).encode("ascii")
    assert len(jg_strict_diagnostics) == 468
    assert hashlib.sha256(jg_strict_diagnostics).hexdigest() == (
        "f71586ce507965104547a0b0d42b7f999d4016ba63331256b94540a37409c8a3"
    )
    assert convert_tibetanmachine("!", strict=True).unicode_text == "ཀ"
    assert nepal_ttf2utf.convert("!", font="tibetan-machine", strict=True) == "ཀ"
    decoded_cp1252 = TibetanMachineConverter({0x20AC: "ཀ"})
    assert dict(decoded_cp1252._table) == {0x80: "ཀ", 0x20AC: "ཀ"}
    assert decoded_cp1252.convert("\x80€").unicode_text == "ཀཀ"
    try:
        convert_tibetanmachine("Ž", strict=True)
    except ValueError as error:
        assert "U+017D" in str(error)
    else:
        raise AssertionError("strict TibetanMachine conversion accepted defined-empty input")
    assert convert_olchiki("a", strict=True).unicode_text == "ᱟ"
    assert convert_olchiki_latic(".", strict=True).unicode_text == "ᱹ"
    assert convert_sunuwar("A", strict=True).unicode_text == "𑯖"
    assert nepal_ttf2utf.convert("A", font="kirat1", strict=True) == "𑯖"
    assert convert_tirhuta("िव", strict=True).unicode_text == "𑒫𑒱"
    native_tirhuta = "\U000114b1\U000114ab"
    native_result = TirhutaConverter().convert(native_tirhuta)
    assert native_result.unicode_text == native_tirhuta
    assert native_result.prebase_i_moves == native_result.reph_moves == 0
    assert nepal_ttf2utf.convert("क", font="janaki", strict=True) == "𑒏"
    try:
        convert_tirhuta("\u090e", strict=True)
    except ValueError as error:
        assert "U+090E" in str(error)
    else:
        raise AssertionError("strict Janaki conversion accepted independent SHORT E")
    magar_akkha = transliterate_magar_akkha("कि", strict=True).unicode_text
    assert magar_akkha == "\U00011013\U0001103a"
    assert nepal_ttf2utf.convert(magar_akkha, font="akkha-brahmi", strict=True) == magar_akkha
    assert janaki_gid_map_sha256(VIDEHA_ISSUE_001) == (
        "ef23c410aeb6f75dedb3dffd255f00ba9da7ab66e9d4c76bc7b5ccf1af9cb963"
    )
    videha_issue = recover_videha_janaki_trace(
        ((0xFFFD, 245),),
        profile=VIDEHA_ISSUE_001,
        pdf_sha256="91ec43fdc5ccd22cf449457f94e159650b944fea5cf35c7baec89a695d146722",
        janaki_font_sha256={
            "b51da8d0c99bf8cc0e7ee85f18681272b0f57eb80f277838f4e2cdcaa5253755",
            "1e3da463c92b8563d4f22db4c0f31b366668988da5008dccdff68f96a44e3501",
        },
        page_count=152,
        strict=True,
    )
    assert videha_issue.devanagari_text == "प्र"
    videha_april = recover_videha_janaki_trace(
        ((0xFFFD, 612),),
        profile=VIDEHA_2008_04_15,
        pdf_sha256="740782ecf5bfa9466727029bcb7733d9c8b046c36d848b598ddc60efc1c51bd2",
        janaki_font_sha256={
            "c64600a4edc0fa153717d66d2524c1665562eee47dd489848578e3cec1c56861",
            "d8863d057541d5cecb862fd43e93114a9a20c6d5de519fc30f3c990962a8b18b",
        },
        page_count=300,
        strict=True,
    )
    assert videha_april.devanagari_text == "फ्रे"
    assert convert_lepcha("A", strict=True).unicode_text == "ᰀ"
    herald_boundary = convert_lepcha("A0g", strict=True)
    assert herald_boundary.unicode_text == "\u1c00\u1c40\u1c2a"
    assert herald_boundary.replacement_count == 3
    assert herald_boundary.unmapped_bytes == []
    assert nepal_ttf2utf.convert("A0g", font="lepcha-sikkimherald", strict=True) == (
        "\u1c00\u1c40\u1c2a"
    )
    assert convert_lepcha("A0dC", strict=True).unicode_text == "\u1c00\u1c40\u1c03\u1c27"
    native_herald = convert_lepcha("\u1c27\u1c00", strict=True)
    assert native_herald.unicode_text == "\u1c27\u1c00"
    assert native_herald.replacement_count == 0
    assert convert_lepcha("d\u1c00", strict=True).unicode_text == "\u1c27\u1c00"
    assert convert_lepcha("\u1c27A", strict=True).unicode_text == "\u1c27\u1c00"
    try:
        convert_lepcha("*", strict=True)
    except ValueError as error:
        assert "0x2A" in str(error)
    else:
        raise AssertionError("strict Herald Lepcha conversion accepted unresolved input")
    assert convert_devanagari("g]kfn", strict=True).unicode_text == "नेपाल"
    dependency = metadata.distribution("npttf2utf")
    assert dependency.version == "0.3.7"
    dependency_map = Path(dependency.locate_file("npttf2utf/map.json")).read_bytes()
    assert len(dependency_map) == 34_197
    assert hashlib.sha256(dependency_map).hexdigest() == (
        "66a0a91f1209eb1c73540e443144f306d6daf27c426c09d24ec307a1506212e5"
    )
    devanagari_anchors = {
        "preeti": ("¥", "्र"),
        "kantipur": ("¨", "ङ्ग"),
        "sagarmatha": ("¤", "!"),
        "pcs-nepali": ("<", "्र"),
        "fontasy-himali": ("~", "ञ"),
    }
    for font, (source, expected) in devanagari_anchors.items():
        assert convert_devanagari(source, font=font, strict=True).unicode_text == expected
    for font in ("nayanepal", "gorkhapatra"):
        assert convert_devanagari("l†", font=font, strict=True).unicode_text == "ि्"
        extension_deletion = convert_devanagari("†f", font=font)
        assert extension_deletion.unicode_text == ""
        assert extension_deletion.leftover == ["f", "†"]
        embedded_extension = convert_devanagari("s†f", font=font)
        assert embedded_extension.unicode_text == "क"
        assert embedded_extension.leftover == ["f", "†"]
    assigned_devanagari = "\u0903\U00011b00"
    assert convert_devanagari(assigned_devanagari, strict=True).unicode_text == (
        assigned_devanagari
    )
    try:
        convert_devanagari(r"s\fs", strict=True)
    except ValueError as error:
        assert "U+005C" in str(error)
        assert "U+0066" in str(error)
    else:
        raise AssertionError("strict Devanagari conversion accepted deleted input")

    package_distribution = metadata.distribution("nepal-ttf2utf")
    package_metadata = package_distribution.metadata
    assert tuple(package_metadata.get_all("Name") or ()) == ("nepal-ttf2utf",)
    assert tuple(package_metadata.get_all("Version") or ()) == ("0.3.0",)
    assert package_distribution.version == nepal_ttf2utf.__version__ == "0.3.0"
    assert tuple(package_metadata.get_all("Requires-Python") or ()) == (">=3.9",)
    license_files = tuple(package_metadata.get_all("License-File") or ())
    assert len(license_files) == len(set(license_files))
    assert set(license_files) == EXPECTED_LICENSE_FILES
    requirements = tuple(package_metadata.get_all("Requires-Dist") or ())
    assert len(requirements) == len(set(requirements))
    assert set(requirements) == {
        "npttf2utf==0.3.7",
        "pytest>=7; extra == 'dev'",
    }
    assert tuple(package_metadata.get_all("Provides-Extra") or ()) == ("dev",)
    assert {
        (entry.group, entry.name, entry.value) for entry in package_distribution.entry_points
    } == {("console_scripts", "nepal-ttf2utf", "nepal_ttf2utf.cli:main")}
    completed = subprocess.run(
        ["nepal-ttf2utf", "--font", "jg-lepcha", "k"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == "ᰀ"
    assert completed.stderr == ""
    print(f"installed-wheel smoke passed from {imported_from}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
