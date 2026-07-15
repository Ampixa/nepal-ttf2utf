"""Pinned project Magar Akkha/Brahmi transliteration contract tests."""

import hashlib
import json
import unicodedata
from collections import Counter

import pytest

import nepal_ttf2utf.magar_akkha as magar_akkha_module
from nepal_ttf2utf import convert, supported_fonts, transliterate_magar_akkha
from nepal_ttf2utf.magar_akkha import (
    BRAHMI_TO_DEVANAGARI,
    DEVANAGARI_TO_BRAHMI,
    FOLD_TO_MINIMAL_AKKHA,
)
from nepal_ttf2utf.unicode_span import _is_assigned_script_codepoint


def _contract_payload() -> bytes:
    return json.dumps(
        {
            "forward": [
                [ord(source), ord(target)]
                for source, target in sorted(DEVANAGARI_TO_BRAHMI.items())
            ],
            "fold": [
                [ord(source), ord(target)]
                for source, target in sorted(FOLD_TO_MINIMAL_AKKHA.items())
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def test_magar_akkha_effective_contract_is_pinned():
    assert len(DEVANAGARI_TO_BRAHMI) == len(BRAHMI_TO_DEVANAGARI) == 69
    assert len(set(DEVANAGARI_TO_BRAHMI.values())) == 69
    assert BRAHMI_TO_DEVANAGARI == {
        target: source for source, target in DEVANAGARI_TO_BRAHMI.items()
    }
    assert len(FOLD_TO_MINIMAL_AKKHA) == 8
    assert set(FOLD_TO_MINIMAL_AKKHA) <= set(DEVANAGARI_TO_BRAHMI)
    assert set(FOLD_TO_MINIMAL_AKKHA.values()) <= set(DEVANAGARI_TO_BRAHMI)

    payload = _contract_payload()
    assert len(payload) == 1015
    assert hashlib.sha256(payload).hexdigest() == (
        "7be4d246c8b994cd7dd81f96681b8cbf3f220873e38a4b30895a13eb6aebb021"
    )

    for source, target in DEVANAGARI_TO_BRAHMI.items():
        assert _is_assigned_script_codepoint(ord(source), "Devanagari")
        assert _is_assigned_script_codepoint(ord(target), "Brahmi")


@pytest.mark.parametrize(
    ("source", "target", "target_name"),
    [
        ("ा", "\U00011038", "BRAHMI VOWEL SIGN AA"),
        ("ि", "\U0001103a", "BRAHMI VOWEL SIGN I"),
        ("ी", "\U0001103b", "BRAHMI VOWEL SIGN II"),
        ("ु", "\U0001103c", "BRAHMI VOWEL SIGN U"),
        ("ू", "\U0001103d", "BRAHMI VOWEL SIGN UU"),
        ("े", "\U00011042", "BRAHMI VOWEL SIGN E"),
        ("ै", "\U00011043", "BRAHMI VOWEL SIGN AI"),
        ("ो", "\U00011044", "BRAHMI VOWEL SIGN O"),
        ("ौ", "\U00011045", "BRAHMI VOWEL SIGN AU"),
    ],
)
def test_magar_akkha_vowel_signs_have_exact_semantic_targets(source, target, target_name):
    assert DEVANAGARI_TO_BRAHMI[source] == target
    assert unicodedata.name(target) == target_name
    assert transliterate_magar_akkha(source, strict=True).unicode_text == target
    assert (
        transliterate_magar_akkha(target, target="devanagari", strict=True).unicode_text == source
    )


def _invalid_contract(case):
    forward = dict(DEVANAGARI_TO_BRAHMI)
    folds = dict(FOLD_TO_MINIMAL_AKKHA)
    if case == "forward-count":
        forward.pop("क")
    elif case == "fold-count":
        folds.pop("ट")
    elif case == "source":
        target = forward.pop("क")
        forward["A"] = target
    elif case == "target":
        forward["क"] = "A"
    elif case == "reserved-target":
        forward["क"] = "\U0001104e"
    elif case == "duplicate-target":
        forward["ख"] = forward["क"]
    elif case == "fold-source":
        folds.pop("ट")
        folds["A"] = "त"
    elif case == "missing-fold-source":
        folds.pop("ट")
        folds["ऋ"] = "त"
    elif case == "missing-fold-target":
        folds["ट"] = "ऋ"
    elif case == "identity-fold":
        folds["ट"] = "ट"
    else:  # pragma: no cover - test helper contract
        raise AssertionError(case)
    return forward, folds


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("forward-count", "must contain 69 entries"),
        ("fold-count", "must contain 8 entries"),
        ("source", "invalid Magar Akkha Devanagari source"),
        ("target", "invalid Magar Akkha Brahmi target"),
        ("reserved-target", "invalid Magar Akkha Brahmi target"),
        ("duplicate-target", "targets must be one-to-one"),
        ("fold-source", "invalid Magar Akkha fold source"),
        ("missing-fold-source", "sources and targets must exist"),
        ("missing-fold-target", "sources and targets must exist"),
        ("identity-fold", "folds must change their source"),
    ],
)
def test_magar_akkha_fixed_contract_validation_fails_closed(case, message):
    with pytest.raises(ValueError, match=message):
        magar_akkha_module._freeze_contract(*_invalid_contract(case))


def test_every_magar_akkha_mapping_has_exact_forward_and_reverse_behavior():
    for source, target in DEVANAGARI_TO_BRAHMI.items():
        forward = transliterate_magar_akkha(source, strict=True)
        assert forward.source_text == source
        assert forward.unicode_text == target
        assert forward.target == "brahmi"
        assert forward.replacement_count == 1
        assert forward.folded_count == 0
        assert forward.unmapped_codepoints == []

        reverse = transliterate_magar_akkha(target, target="devanagari", strict=True)
        assert reverse.source_text == target
        assert reverse.unicode_text == source
        assert reverse.target == "devanagari"
        assert reverse.replacement_count == 1
        assert reverse.folded_count == 0
        assert reverse.unmapped_codepoints == []


@pytest.mark.parametrize("apply_folds", [False, True])
def test_every_devanagari_block_position_has_an_exact_forward_classification(apply_folds):
    counts: Counter[str] = Counter()
    for codepoint in range(0x0900, 0x0980):
        source = chr(codepoint)
        result = transliterate_magar_akkha(source, fold_to_minimal_inventory=apply_folds)
        if source in DEVANAGARI_TO_BRAHMI:
            mapped_source = FOLD_TO_MINIMAL_AKKHA.get(source, source) if apply_folds else source
            classification = "folded" if mapped_source != source else "mapped"
            counts[classification] += 1
            assert result.unicode_text == DEVANAGARI_TO_BRAHMI[mapped_source]
            assert result.replacement_count == 1
            assert result.unmapped_codepoints == []
            assert result.folded_count == int(classification == "folded")
            assert (
                transliterate_magar_akkha(
                    source,
                    fold_to_minimal_inventory=apply_folds,
                    strict=True,
                )
                == result
            )
        else:
            counts["unmapped"] += 1
            assert result.unicode_text == unicodedata.normalize("NFC", source)
            assert result.replacement_count == 0
            assert result.unmapped_codepoints == [f"U+{codepoint:04X}"]
            with pytest.raises(ValueError, match=rf"U\+{codepoint:04X}"):
                transliterate_magar_akkha(
                    source,
                    fold_to_minimal_inventory=apply_folds,
                    strict=True,
                )
            assert result.folded_count == 0
    expected = (
        {"mapped": 61, "folded": 8, "unmapped": 59}
        if apply_folds
        else {
            "mapped": 69,
            "unmapped": 59,
        }
    )
    assert counts == expected


def test_every_brahmi_block_position_has_an_exact_reverse_classification():
    counts: Counter[str] = Counter()
    for codepoint in range(0x11000, 0x11080):
        source = chr(codepoint)
        result = transliterate_magar_akkha(source, target="devanagari")
        if source in BRAHMI_TO_DEVANAGARI:
            counts["mapped"] += 1
            assert result.unicode_text == BRAHMI_TO_DEVANAGARI[source]
            assert result.replacement_count == 1
            assert result.unmapped_codepoints == []
            assert transliterate_magar_akkha(source, target="devanagari", strict=True) == result
        else:
            counts["unmapped"] += 1
            assert result.unicode_text == source
            assert result.replacement_count == 0
            assert result.unmapped_codepoints == [f"U+{codepoint:05X}"]
            with pytest.raises(ValueError, match=rf"U\+{codepoint:05X}"):
                transliterate_magar_akkha(source, target="devanagari", strict=True)
        assert result.folded_count == 0
    assert counts == {"mapped": 69, "unmapped": 59}


def test_every_project_fold_is_explicit_counted_and_lossy():
    for source, folded_source in FOLD_TO_MINIMAL_AKKHA.items():
        lossless = transliterate_magar_akkha(source, strict=True)
        folded = transliterate_magar_akkha(
            source,
            fold_to_minimal_inventory=True,
            strict=True,
        )
        assert folded.unicode_text == DEVANAGARI_TO_BRAHMI[folded_source]
        assert folded.unicode_text != lossless.unicode_text
        assert folded.replacement_count == 1
        assert folded.folded_count == 1
        assert folded.unmapped_codepoints == []
        assert (
            transliterate_magar_akkha(
                folded.unicode_text,
                target="devanagari",
                strict=True,
            ).unicode_text
            == folded_source
        )


@pytest.mark.parametrize("value", [None, 0, 1, "yes", object()])
def test_magar_akkha_fold_flag_requires_a_boolean(value):
    with pytest.raises(ValueError, match="must be a bool"):
        transliterate_magar_akkha("क", fold_to_minimal_inventory=value)


def test_minimal_inventory_folding_is_forward_only():
    with pytest.raises(ValueError, match="available only for Brahmi output"):
        transliterate_magar_akkha(
            "\U00011013",
            target="devanagari",
            fold_to_minimal_inventory=True,
        )


class _PretendsToBeBrahmi:
    def __eq__(self, other):
        return other == "brahmi"


class _PretendingString(str):
    def __eq__(self, other):
        return other == "brahmi"


@pytest.mark.parametrize(
    "target",
    ["", "Brahmi", "roman", None, 1, object(), _PretendsToBeBrahmi(), _PretendingString("x")],
)
def test_magar_akkha_target_is_exact(target):
    with pytest.raises(ValueError, match="target must be"):
        transliterate_magar_akkha("क", target=target)


def test_public_magar_akkha_maps_and_internal_snapshots_are_immutable(monkeypatch):
    with pytest.raises(TypeError):
        DEVANAGARI_TO_BRAHMI["क"] = "\U00011014"
    with pytest.raises(TypeError):
        BRAHMI_TO_DEVANAGARI["\U00011013"] = "ख"
    with pytest.raises(TypeError):
        FOLD_TO_MINIMAL_AKKHA["ट"] = "क"

    monkeypatch.setattr(magar_akkha_module, "DEVANAGARI_TO_BRAHMI", {"क": "A"})
    monkeypatch.setattr(magar_akkha_module, "BRAHMI_TO_DEVANAGARI", {"\U00011013": "A"})
    monkeypatch.setattr(magar_akkha_module, "FOLD_TO_MINIMAL_AKKHA", {"ट": "क"})
    assert transliterate_magar_akkha("क", strict=True).unicode_text == "\U00011013"
    assert (
        transliterate_magar_akkha("\U00011013", target="devanagari", strict=True).unicode_text
        == "क"
    )
    assert (
        transliterate_magar_akkha("ट", fold_to_minimal_inventory=True).unicode_text == "\U00011022"
    )


@pytest.mark.parametrize(
    "old_target", ["\U00011039", "\U0001103e", "\U0001103f", "\U00011040", "\U00011041"]
)
def test_old_nonoverlapping_incorrect_vowel_targets_are_not_reverse_compatibility_aliases(
    old_target,
):
    result = transliterate_magar_akkha(old_target, target="devanagari")
    assert result.unicode_text == old_target
    assert result.unmapped_codepoints == [f"U+{ord(old_target):05X}"]
    with pytest.raises(ValueError, match=rf"U\+{ord(old_target):05X}"):
        transliterate_magar_akkha(old_target, target="devanagari", strict=True)


def test_overlapping_old_vowel_targets_follow_the_corrected_contract():
    assert (
        transliterate_magar_akkha("\U0001103a", target="devanagari", strict=True).unicode_text
        == "ि"
    )
    assert (
        transliterate_magar_akkha("\U0001103b", target="devanagari", strict=True).unicode_text
        == "ी"
    )
    assert (
        transliterate_magar_akkha("\U0001103c", target="devanagari", strict=True).unicode_text == "ु"
    )


def test_roundtrip_is_lossless_over_the_supported_inventory_by_default():
    devanagari = "मगर ढुट नेपाल क्षेत्र ज्ञान नमस्ते १२३४५६७८९०"
    brahmi = transliterate_magar_akkha(devanagari, strict=True)
    restored = transliterate_magar_akkha(brahmi.unicode_text, target="devanagari", strict=True)
    assert restored.unicode_text == devanagari


def test_strict_scope_is_the_selected_source_block_only():
    text = "Latin 𑒏"
    assert transliterate_magar_akkha(text, strict=True).unicode_text == text
    assert transliterate_magar_akkha(text, target="devanagari", strict=True).unicode_text == text


@pytest.mark.parametrize(
    "font", ["magar-akkha-brahmi", "akkha-brahmi", "brahmi-unicode", "unicode-brahmi"]
)
def test_every_brahmi_alias_validates_already_unicode_text(font):
    text = transliterate_magar_akkha("मगर", strict=True).unicode_text
    assert supported_fonts()[font] == "Brahmi"
    assert convert(text, font=font, strict=True) == text
    with pytest.raises(ValueError, match=r"U\+1104E"):
        convert("\U0001104e", font=font, strict=True)


@pytest.mark.parametrize("font", ["ABCDEF+MAGAR-AKKHA-BRAHMI", "ABCDEF+AKKHA-BRAHMI"])
def test_magar_akkha_brahmi_pdf_subset_aliases_validate_already_unicode_text(font):
    assert convert("\U00011013", font=font, strict=True) == "\U00011013"
