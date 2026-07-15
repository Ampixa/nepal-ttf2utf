"""Sunuwar / Jenticha (Koĩts) legacy display-font conversion tests.

The tests pin the exact built-in project contract. Its underlying legacy-font
derivation artifacts are not distributed by this package; public regional-form
references and the evidence boundary are documented in ``docs/EVIDENCE.md``.
"""

import hashlib
import json
import unicodedata
from collections import Counter

import pytest

import nepal_ttf2utf.sunuwar as sunuwar_module
from nepal_ttf2utf import convert, convert_sunuwar, supported_fonts
from nepal_ttf2utf.sunuwar import (
    SUNUWAR_DIGITS,
    SUNUWAR_LETTERS_CONFIRMED,
    SUNUWAR_LETTERS_UNCERTAIN,
    SUNUWAR_PASSTHROUGH,
    SunuwarConverter,
)
from nepal_ttf2utf.unicode_span import _is_assigned_script_codepoint


def _contract_payload(converter: SunuwarConverter) -> bytes:
    return json.dumps(
        {
            "confirmed": [
                [ord(source), ord(target)]
                for source, target in sorted(converter._confirmed.items())
            ],
            "passthrough": sorted(ord(source) for source in converter._passthrough),
            "uncertain": [
                [ord(source), ord(target)]
                for source, target in sorted(converter._uncertain.items())
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def test_sunuwar_effective_contract_is_pinned():
    converter = SunuwarConverter()
    assert len(SUNUWAR_DIGITS) == 10
    assert len(SUNUWAR_LETTERS_CONFIRMED) == 28
    assert len(converter._confirmed) == 38
    assert len(set(converter._confirmed.values())) == 38
    assert converter._uncertain == SUNUWAR_LETTERS_UNCERTAIN == {}
    assert len(converter._passthrough) == len(SUNUWAR_PASSTHROUGH) == 20
    assert not set(converter._confirmed) & converter._passthrough

    payload = _contract_payload(converter)
    assert len(payload) == 549
    assert hashlib.sha256(payload).hexdigest() == (
        "d64f76e20aa9aa9a0d58469212235ad63cdfb11fea9ce692762ab06b77296d0b"
    )

    assigned = {
        codepoint
        for codepoint in range(0x11BC0, 0x11BFA)
        if _is_assigned_script_codepoint(codepoint, "Sunuwar")
    }
    targets = {ord(target) for target in converter._confirmed.values()}
    assert len(assigned) == 44
    assert assigned - targets == {0x11BC6, 0x11BCA, 0x11BD2, 0x11BD7, 0x11BDD, 0x11BE1}


@pytest.mark.parametrize(
    ("patches", "message"),
    [
        ({"SUNUWAR_DIGITS": {" ": "\U00011bf0"}}, "invalid Sunuwar confirmed source"),
        ({"SUNUWAR_DIGITS": {"0": "A"}}, "invalid Sunuwar confirmed target"),
        ({"SUNUWAR_DIGITS": {"0": "\U00011be2"}}, "invalid Sunuwar confirmed target"),
        ({"SUNUWAR_DIGITS": {"A": "\U00011bf0"}}, "digit and letter sources overlap"),
        ({"SUNUWAR_LETTERS_UNCERTAIN": {"A": "𑯁"}}, "sources overlap"),
        ({"SUNUWAR_DIGITS": {"0": "𑯃"}}, "targets must be one-to-one"),
        (
            {"SUNUWAR_PASSTHROUGH": SUNUWAR_PASSTHROUGH | {"A"}},
            "mapping and passthrough sources overlap",
        ),
        ({"SUNUWAR_PASSTHROUGH": frozenset({"\t"})}, "invalid Sunuwar passthrough"),
    ],
)
def test_sunuwar_default_contract_validation_fails_closed(monkeypatch, patches, message):
    for name, value in patches.items():
        monkeypatch.setattr(sunuwar_module, name, value)
    with pytest.raises(ValueError, match=message):
        sunuwar_module._freeze_default_contract()


def test_every_sunuwar_mapping_has_exact_isolated_behavior():
    converter = SunuwarConverter()
    for source, target in converter._confirmed.items():
        result = converter.convert(source)
        assert result.unicode_text == target, repr(source)
        assert result.sunuwar_char_count == 1, repr(source)
        assert result.replacement_count == 1, repr(source)
        assert result.confirmed_byte_count == 1, repr(source)
        assert result.uncertain_bytes == [], repr(source)
        assert result.unmapped_bytes == [], repr(source)
        assert convert_sunuwar(source, strict=True) == result


@pytest.mark.parametrize("apply_uncertain", [False, True])
def test_every_byte_has_an_exact_sunuwar_classification(apply_uncertain):
    converter = SunuwarConverter(apply_uncertain=apply_uncertain)
    counts: Counter[str] = Counter()
    structural = {" ", "\t", "\r", "\n"}

    for codepoint in range(0x100):
        source = chr(codepoint)
        result = converter.convert(source)
        if source in converter._confirmed:
            classification = "mapped"
            assert result.unicode_text == converter._confirmed[source]
            assert result.sunuwar_char_count == 1
            assert result.replacement_count == 1
            assert result.confirmed_byte_count == 1
        elif source in structural:
            classification = "structural"
            assert result.unicode_text == source
            assert result.sunuwar_char_count == 0
            assert result.replacement_count == 0
            assert result.confirmed_byte_count == 0
        elif source in converter._passthrough:
            classification = "passthrough"
            assert result.unicode_text == source
            assert result.sunuwar_char_count == 0
            assert result.replacement_count == 0
            assert result.confirmed_byte_count == 0
        else:
            classification = "unmapped"
            assert result.unicode_text == source
            assert result.sunuwar_char_count == 0
            assert result.replacement_count == 0
            assert result.confirmed_byte_count == 0
            assert result.unmapped_bytes == [source]

        assert result.uncertain_bytes == []
        if classification == "unmapped":
            with pytest.raises(ValueError, match=rf"U\+{codepoint:04X}"):
                convert_sunuwar(
                    source,
                    apply_uncertain=apply_uncertain,
                    strict=True,
                )
        else:
            assert result.unmapped_bytes == []
            assert (
                convert_sunuwar(
                    source,
                    apply_uncertain=apply_uncertain,
                    strict=True,
                )
                == result
            )
        counts[classification] += 1

    assert counts == {
        "mapped": 38,
        "structural": 4,
        "passthrough": 20,
        "unmapped": 194,
    }


def test_every_assigned_unicode_sunuwar_character_passes_through_strictly():
    assigned = [
        codepoint
        for codepoint in range(0x11BC0, 0x11BFA)
        if _is_assigned_script_codepoint(codepoint, "Sunuwar")
    ]
    assert len(assigned) == 44
    for codepoint in assigned:
        source = chr(codepoint)
        result = convert_sunuwar(source, strict=True)
        assert result.unicode_text == source
        assert result.sunuwar_char_count == 1
        assert result.replacement_count == 0
        assert result.confirmed_byte_count == 0
        assert result.uncertain_bytes == []
        assert result.unmapped_bytes == []


def test_every_reserved_sunuwar_position_is_diagnosed_and_strictly_rejected():
    reserved = [*range(0x11BE2, 0x11BF0), *range(0x11BFA, 0x11C00)]
    assert len(reserved) == 20
    for codepoint in reserved:
        source = chr(codepoint)
        result = convert_sunuwar(source)
        assert result.unicode_text == source
        assert result.sunuwar_char_count == 1
        assert result.replacement_count == 0
        assert result.confirmed_byte_count == 0
        assert result.uncertain_bytes == []
        assert result.unmapped_bytes == [source]
        with pytest.raises(ValueError, match=rf"U\+{codepoint:04X}"):
            convert_sunuwar(source, strict=True)


def test_every_sunuwar_passthrough_character_is_strictly_clean():
    for source in SUNUWAR_PASSTHROUGH:
        result = convert_sunuwar(source, strict=True)
        assert result.unicode_text == source
        assert result.sunuwar_char_count == 0
        assert result.replacement_count == 0
        assert result.confirmed_byte_count == 0
        assert result.uncertain_bytes == []
        assert result.unmapped_bytes == []


def test_sunuwar_digits_map_in_order_to_block():
    conv = SunuwarConverter()
    for i in range(10):
        assert conv.convert(str(i)).unicode_text == chr(0x11BF0 + i)


def test_sunuwar_confirmed_map_is_one_to_one_in_block():
    cps = [ord(v) for v in list(SUNUWAR_LETTERS_CONFIRMED.values()) + list(SUNUWAR_DIGITS.values())]
    assert all(0x11BC0 <= cp <= 0x11BFF for cp in cps)
    assert len(cps) == len(set(cps)), "confirmed map must be one-to-one"


def test_sunuwar_full_map_including_uncertain_is_one_to_one():
    cps = [
        ord(v)
        for v in list(SUNUWAR_LETTERS_CONFIRMED.values())
        + list(SUNUWAR_DIGITS.values())
        + list(SUNUWAR_LETTERS_UNCERTAIN.values())
    ]
    assert all(0x11BC0 <= cp <= 0x11BFF for cp in cps)
    assert len(cps) == len(set(cps)), "byte->codepoint map must be globally one-to-one"


def test_sunuwar_selected_named_letter_assignments():
    conv = SunuwarConverter()
    assert conv.convert("{").unicode_text == chr(0x11BC3)  # IMAR
    assert conv.convert("}").unicode_text == chr(0x11BC2)  # EKO
    assert conv.convert("A").unicode_text == chr(0x11BD6)  # AAL
    assert conv.convert("i").unicode_text == chr(0x11BCC)  # CARMI
    assert conv.convert("y").unicode_text == chr(0x11BDC)  # SHYER


def test_sunuwar_selected_additional_assignments_are_confirmed_by_default():
    conv = SunuwarConverter()
    resolved = {
        "v": 0x11BC4,  # reu
        "q": 0x11BE0,  # kloko
        "x": 0x11BD3,  # varca
        "r": 0x11BD9,  # phar
        "u": 0x11BD4,  # yat
        "g": 0x11BD5,  # ava
        "h": 0x11BDA,  # ngar
        "j": 0x11BCF,  # jyah
    }
    for byte, cp in resolved.items():
        res = conv.convert(byte)
        assert res.unicode_text == chr(cp), f"{byte!r} should map to U+{cp:05X}"
        assert res.confirmed_byte_count == 1
        assert res.uncertain_bytes == []


def test_sunuwar_no_uncertain_bytes_remain():
    assert SUNUWAR_LETTERS_UNCERTAIN == {}


def test_sunuwar_pipe_is_confirmed_utthi_by_default():
    res = convert_sunuwar("|")
    assert res.unicode_text == chr(0x11BC5)
    assert res.uncertain_bytes == []
    assert res.sunuwar_char_count == 1
    assert res.confirmed_byte_count == 1


def test_sunuwar_apply_uncertain_is_compatibility_noop():
    assert (
        convert_sunuwar("|").unicode_text == convert_sunuwar("|", apply_uncertain=True).unicode_text
    )

    source = "".join(chr(codepoint) for codepoint in range(0x100))
    assert convert_sunuwar(source) == convert_sunuwar(source, apply_uncertain=True)


@pytest.mark.parametrize("apply_uncertain", [None, 0, 1, "yes", object()])
def test_sunuwar_constructor_requires_boolean_apply_uncertain(apply_uncertain):
    with pytest.raises(ValueError, match="must be a bool"):
        SunuwarConverter(apply_uncertain=apply_uncertain)


@pytest.mark.parametrize("apply_uncertain", [None, 0, 1, "yes", object()])
def test_public_sunuwar_function_requires_boolean_apply_uncertain(apply_uncertain):
    with pytest.raises(ValueError, match="must be a bool"):
        convert_sunuwar("A", apply_uncertain=apply_uncertain)


def test_sunuwar_public_maps_and_internal_snapshots_are_immutable():
    converter = SunuwarConverter()
    with pytest.raises(TypeError):
        SUNUWAR_DIGITS["0"] = "𑯁"
    with pytest.raises(TypeError):
        SUNUWAR_LETTERS_CONFIRMED["A"] = "𑯀"
    with pytest.raises(TypeError):
        SUNUWAR_LETTERS_UNCERTAIN["B"] = "𑯀"
    with pytest.raises(TypeError):
        converter._confirmed["A"] = "𑯀"
    with pytest.raises(TypeError):
        converter._uncertain["B"] = "𑯀"
    with pytest.raises(TypeError):
        converter._table["A"] = "𑯀"

    assert converter.convert("A").unicode_text == "𑯖"
    assert converter.convert("A").confirmed_byte_count == 1


def test_sunuwar_strict_mode_accepts_confirmed_utthi():
    assert convert_sunuwar("|", strict=True).unicode_text == chr(0x11BC5)


def test_sunuwar_output_is_nfc_and_block_constrained_for_confirmed():
    res = convert_sunuwar("A{z}tO 18")
    non_ascii = [c for c in res.unicode_text if ord(c) > 0x7F]
    assert non_ascii
    assert all(0x11BC0 <= ord(c) <= 0x11BFF for c in non_ascii)
    assert res.sunuwar_char_count == len(non_ascii)
    assert res.unicode_text == unicodedata.normalize("NFC", res.unicode_text)
    # 6 confirmed letters (A { z } t O) + 2 confirmed digits (1 8) = 8.
    assert res.confirmed_byte_count == 8


def test_sunuwar_spaces_and_punctuation_pass_through():
    res = convert_sunuwar("A, O")
    assert " " in res.unicode_text
    assert "," in res.unicode_text


def test_sunuwar_structural_whitespace_is_not_reported_as_unmapped():
    res = convert_sunuwar("o\t\r\n", strict=True)
    assert res.unicode_text == "𑯀\t\r\n"
    assert res.uncertain_bytes == []
    assert res.unmapped_bytes == []


def test_sunuwar_unmapped_ascii_is_surfaced():
    res = convert_sunuwar("B")
    assert "B" in res.unmapped_bytes
    with pytest.raises(ValueError):
        convert_sunuwar("B", strict=True)


def test_sunuwar_genuine_unicode_passes_through():
    text = chr(0x11BC0)
    res = convert_sunuwar(text, strict=True)
    assert res.unicode_text == text
    assert not res.unmapped_bytes


def test_convert_dispatches_to_sunuwar():
    out = convert("A{z}", font="sunuwar")
    assert any(0x11BC0 <= ord(c) <= 0x11BFF for c in out)


@pytest.mark.parametrize("font", ["sunuwar", "jenticha", "koits", "kirat1"])
def test_every_declared_sunuwar_alias_has_exact_strict_behavior(font):
    assert supported_fonts()[font] == "Sunuwar"
    assert convert("A", font=font, strict=True) == "𑯖"
    with pytest.raises(ValueError, match=r"U\+0042"):
        convert("B", font=font, strict=True)


@pytest.mark.parametrize("font", ["ABCDEF+KOITS", "ABCDEF+KIRAT1"])
def test_sunuwar_pdf_subset_aliases_have_exact_strict_behavior(font):
    assert convert("A", font=font, strict=True) == "𑯖"
    with pytest.raises(ValueError, match=r"U\+0042"):
        convert("B", font=font, strict=True)
