"""'Ol Chiki Optimum' legacy display-font conversion tests.

Anchors are the shape-identity / corpus-position-verified assignments from the
source derivation (Aale Chhatka Santali e-magazine). The formerly uncertain bytes
(``n``, ``T``) are now confirmed by the 2026-07-13 ocr-tech evidence packet.
"""

import json
import unicodedata
from importlib import resources

import pytest

from nepal_ttf2utf import convert, convert_olchiki, convert_olchiki_latic
from nepal_ttf2utf.olchiki import (
    OLCHIKI_LATIC_OVERRIDES,
    OLCHIKI_LATIC_PASSTHROUGH,
    OLCHIKI_PASSTHROUGH,
    OLChikiConverter,
    OLChikiLaticConverter,
)


def _load_raw_map() -> dict:
    with resources.as_file(resources.files("nepal_ttf2utf.maps") / "olck_optimum.json") as p:
        return json.loads(p.read_text(encoding="utf-8"))


def test_olchiki_digits_map_in_order_to_block():
    conv = OLChikiConverter.default()
    for i in range(10):
        assert conv.convert(str(i)).unicode_text == chr(0x1C50 + i)


def test_olchiki_vowel_family_bytes_map_to_row_starter_letters():
    # The structural sanity check from the derivation: the 6 Latin-vowel-family
    # bytes land exactly on Ol Chiki's 6 row-starter letters.
    conv = OLChikiConverter.default()
    assert conv.convert("a").unicode_text == "ᱟ"  # LAA
    assert conv.convert("e").unicode_text == "ᱮ"  # LE
    assert conv.convert("i").unicode_text == "ᱤ"  # LI
    assert conv.convert("o").unicode_text == "ᱚ"  # LA (most frequent byte)
    assert conv.convert("u").unicode_text == "ᱩ"  # LU
    assert conv.convert("O").unicode_text == "ᱳ"  # LO


def test_olchiki_case_pair_o_and_O_are_distinct_letters():
    conv = OLChikiConverter.default()
    assert conv.convert("o").unicode_text != conv.convert("O").unicode_text


def test_olchiki_identical_shape_case_pairs_map_to_same_codepoint():
    # 20 of the 26 case pairs share one glyph outline in the font (IoU=1.000);
    # each such uppercase byte must map to the SAME codepoint as its lowercase twin.
    conv = OLChikiConverter.default()
    for lc in "abcefgijklpqrsuvwxyz":
        assert conv.convert(lc).unicode_text == conv.convert(lc.upper()).unicode_text, lc


def test_olchiki_genuinely_case_distinct_pairs_differ():
    # d/D h/H m/M n/N o/O t/T have different outlines per case and must NOT
    # collapse to the same codepoint.
    conv = OLChikiConverter.default()
    for lc in "dhmnot":
        assert conv.convert(lc).unicode_text != conv.convert(lc.upper()).unicode_text, lc


def test_olchiki_nasalization_mark_from_positional_evidence():
    # 'N' only ever occurs immediately after a vowel in the corpus (e.g. 'hoN'),
    # matching the MU TTUDDAG nasalization mark.
    conv = OLChikiConverter.default()
    assert conv.convert("N").unicode_text == "ᱸ"


def test_olchiki_mucaad_punctuation_from_positional_evidence():
    # '|' occurs 206x in the corpus, always sentence-final after a space, matching
    # the OL CHIKI PUNCTUATION MUCAAD danda-equivalent.
    conv = OLChikiConverter.default()
    assert conv.convert("|").unicode_text == "᱾"


def test_olchiki_confirmed_map_targets_are_in_block():
    raw = _load_raw_map()
    cps = [int(target[0], 16) for target in raw["map"].values()]
    assert all(0x1C50 <= cp <= 0x1C7F for cp in cps)


def test_olchiki_confirmed_map_collisions_are_only_intentional_case_pairs():
    # The map is deliberately many-to-one for the 20 case pairs that share one
    # glyph outline (e.g. byte 0x61 'a' and byte 0x41 'A' both -> U+1C5F). Any
    # OTHER collision would mean two conceptually different bytes were mapped to
    # the same codepoint by mistake -- assert every collision group is exactly
    # a {lowercase, uppercase} pair of the same letter.
    raw = _load_raw_map()
    by_cp: dict[str, list[int]] = {}
    for byte_hex, target in raw["map"].items():
        by_cp.setdefault(target[0], []).append(int(byte_hex, 16))
    for cp, bytes_ in by_cp.items():
        if len(bytes_) == 1:
            continue
        assert len(bytes_) == 2, f"U+{cp} has {len(bytes_)} bytes mapped to it: {bytes_}"
        chars = {chr(b) for b in bytes_}
        assert len(chars) == 2 and {c.lower() for c in chars} == {next(iter(chars)).lower()}, (
            f"U+{cp} collision is not a same-letter case pair: {chars}"
        )


def test_olchiki_confirmed_and_uncertain_maps_dont_overlap_bytes():
    raw = _load_raw_map()
    confirmed_bytes = set(raw["map"])
    uncertain_bytes = set(raw["uncertain_map"])
    assert not confirmed_bytes & uncertain_bytes


def test_olchiki_no_uncertain_bytes_remain():
    raw = _load_raw_map()
    assert raw["uncertain_map"] == {}


def test_olchiki_resolved_n_and_uppercase_t_are_confirmed():
    res = convert_olchiki("nT")
    assert res.unicode_text == "ᱱᱛ"
    assert res.uncertain_bytes == []
    assert res.olchiki_char_count == 2


def test_olchiki_apply_uncertain_is_noop_when_no_uncertain_entries_remain():
    assert (
        convert_olchiki("nT").unicode_text
        == convert_olchiki("nT", apply_uncertain=True).unicode_text
    )


def test_olchiki_strict_mode_accepts_resolved_n_and_t():
    assert convert_olchiki("nT", strict=True).unicode_text == "ᱱᱛ"


def test_olchiki_strict_mode_surfaces_unmapped_byte():
    # '@' is plain ASCII in this font (not an Ol Chiki shape, not in the map, and
    # not in the passthrough punctuation set) -- surfaced, never guessed.
    with pytest.raises(ValueError):
        convert_olchiki("@", strict=True)
    res = convert_olchiki("@")
    assert "@" in res.unmapped_bytes
    assert res.unicode_text == "@"


def test_olchiki_ascii_punctuation_passes_through_unchanged():
    res = convert_olchiki("a, b. c-d")
    assert "," in res.unicode_text
    assert "." in res.unicode_text
    assert "-" in res.unicode_text
    assert not res.unmapped_bytes


@pytest.mark.parametrize("converter", [convert_olchiki, convert_olchiki_latic])
def test_olchiki_structural_whitespace_is_not_reported_as_unmapped(converter):
    res = converter("a\t\r\n", strict=True)
    assert res.unicode_text == "ᱟ\t\r\n"
    assert res.uncertain_bytes == []
    assert res.unmapped_bytes == []


def test_olchiki_passthrough_set_matches_module_constant():
    assert "," in OLCHIKI_PASSTHROUGH
    assert "." in OLCHIKI_PASSTHROUGH
    assert "|" not in OLCHIKI_PASSTHROUGH  # '|' is a mapped Ol Chiki mark, not literal


def test_olchiki_output_is_nfc_and_block_constrained_for_confirmed():
    res = convert_olchiki("abcdefgh 0123")
    non_space = [c for c in res.unicode_text if c != " "]
    assert non_space
    assert all(0x1C50 <= ord(c) <= 0x1C7F for c in non_space)
    assert res.unicode_text == unicodedata.normalize("NFC", res.unicode_text)


def test_olchiki_real_unicode_mixed_in_passes_through():
    # A genuine Ol Chiki codepoint mixed into otherwise legacy-encoded text (e.g.
    # a modifier the author typed via a fallback Unicode font) is not a failure.
    res = convert_olchiki("aᱸb")
    assert "ᱸ" in res.unicode_text
    assert not res.unmapped_bytes


def test_convert_dispatches_to_olchiki():
    out = convert("ab", font="olck-optimum")
    assert any(0x1C50 <= ord(c) <= 0x1C7F for c in out)


def test_latic_letters_and_digits_share_optimum_semantics_except_v_w_swap():
    optimum = OLChikiConverter.default()
    latic = OLChikiLaticConverter.default()
    for byte in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz":
        if byte.lower() in {"v", "w"}:
            continue
        assert latic.convert(byte).unicode_text == optimum.convert(byte).unicode_text, byte
    assert latic.convert("vVwW").unicode_text == "ᱶᱶᱣᱣ"


def test_latic_punctuation_uses_exact_unicode_cmap_matches():
    source = ".-:~|"
    expected = "".join(chr(OLCHIKI_LATIC_OVERRIDES[ord(byte)]) for byte in source)
    result = convert_olchiki_latic(source, strict=True)
    assert result.unicode_text == expected
    assert result.confirmed_byte_count == 5


def test_latic_literal_apostrophe_and_optimum_punctuation_stay_separate():
    assert convert_olchiki_latic("'", strict=True).unicode_text == "'"
    assert convert_olchiki(".-:~", strict=True).unicode_text == ".-:~"
    assert not frozenset(".-:~") & OLCHIKI_LATIC_PASSTHROUGH


def test_convert_dispatches_to_latic_layout():
    for font in ("OLCKLatic-Normal", "OLCKLatic-Bold", "OLCKLatic-UltraBlack"):
        assert convert("a.", font=font, strict=True) == "ᱟᱹ"


def test_olchiki_empty_map_rejected():
    with pytest.raises(ValueError):
        OLChikiConverter({})
