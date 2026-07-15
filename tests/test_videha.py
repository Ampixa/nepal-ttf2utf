"""Hash-pinned Videha Janaki glyph-ID recovery tests."""

import pytest

from nepal_ttf2utf import (
    VIDEHA_2008_04_15,
    VIDEHA_ISSUE_001,
    UnknownJanakiGlyphError,
    VidehaProfileError,
    janaki_gid_map_sha256,
    recover_videha_janaki_trace,
)
from nepal_ttf2utf.videha import (
    JANAKI_GID_EXTENSION_2008_04_15,
    JANAKI_GID_TO_DEVANAGARI,
    JANAKI_GID_TO_DEVANAGARI_2008_04_15,
)

ISSUE_001 = {
    "profile": VIDEHA_ISSUE_001,
    "pdf_sha256": "91ec43fdc5ccd22cf449457f94e159650b944fea5cf35c7baec89a695d146722",
    "janaki_font_sha256": {
        "b51da8d0c99bf8cc0e7ee85f18681272b0f57eb80f277838f4e2cdcaa5253755",
        "1e3da463c92b8563d4f22db4c0f31b366668988da5008dccdff68f96a44e3501",
    },
    "page_count": 152,
}

APRIL_2008 = {
    "profile": VIDEHA_2008_04_15,
    "pdf_sha256": "740782ecf5bfa9466727029bcb7733d9c8b046c36d848b598ddc60efc1c51bd2",
    "janaki_font_sha256": {
        "c64600a4edc0fa153717d66d2524c1665562eee47dd489848578e3cec1c56861",
        "d8863d057541d5cecb862fd43e93114a9a20c6d5de519fc30f3c990962a8b18b",
    },
    "page_count": 300,
}


def test_functional_gid_maps_are_complete_and_stable():
    assert len(JANAKI_GID_TO_DEVANAGARI) == 164
    assert len(JANAKI_GID_EXTENSION_2008_04_15) == 34
    assert len(JANAKI_GID_TO_DEVANAGARI_2008_04_15) == 198
    assert (
        janaki_gid_map_sha256(VIDEHA_ISSUE_001)
        == "ef23c410aeb6f75dedb3dffd255f00ba9da7ab66e9d4c76bc7b5ccf1af9cb963"
    )
    assert (
        janaki_gid_map_sha256(VIDEHA_2008_04_15)
        == "28ad7cf9b34f5da6c0d3d2cd03d2af2fbd159fdc1bd46dee905f2ccfe50ba326"
    )


def test_issue_001_recovers_replacement_gids_and_converts_to_tirhuta():
    result = recover_videha_janaki_trace(
        ((ord("क"), 1), (0xFFFD, 245), (0xFFFD, 424), (ord("।"), 2)),
        strict=True,
        **ISSUE_001,
    )
    assert result.devanagari_text == "कप्रने।"
    assert result.replacement_count == 2
    assert result.recovered_gids == (245, 424)
    assert "�" not in result.unicode_text
    assert result.tirhuta_char_count > 0
    assert not result.unmapped_codepoints


def test_april_extension_is_available_only_to_its_exact_profile():
    with pytest.raises(UnknownJanakiGlyphError, match="612"):
        recover_videha_janaki_trace(((0xFFFD, 612),), **ISSUE_001)
    result = recover_videha_janaki_trace(((0xFFFD, 612),), strict=True, **APRIL_2008)
    assert result.devanagari_text == "फ्रे"
    assert "�" not in result.unicode_text


@pytest.mark.parametrize(
    ("profile", "gid_map"),
    [
        pytest.param(ISSUE_001, JANAKI_GID_TO_DEVANAGARI, id="issue-001"),
        pytest.param(APRIL_2008, JANAKI_GID_TO_DEVANAGARI_2008_04_15, id="april-2008"),
    ],
)
def test_every_pinned_gid_expansion_passes_strict_tirhuta_conversion(profile, gid_map):
    gids = tuple(sorted(gid_map))
    result = recover_videha_janaki_trace(
        tuple((0xFFFD, gid) for gid in gids), strict=True, **profile
    )
    assert result.replacement_count == len(gids)
    assert result.recovered_gids == gids
    assert result.unmapped_codepoints == []


@pytest.mark.parametrize(
    ("profile", "gid"),
    [
        pytest.param(ISSUE_001, 245, id="issue-001"),
        pytest.param(APRIL_2008, 612, id="april-2008"),
    ],
)
def test_strict_residual_gate_is_opt_in_for_each_profile(profile, gid):
    chars = ((0x25CC, 1), (0xFFFD, gid), (ord("A"), 2), (0x25CC, 3))
    default = recover_videha_janaki_trace(chars, **profile)
    explicit_lenient = recover_videha_janaki_trace(chars, strict=False, **profile)
    assert default == explicit_lenient
    assert default.unmapped_codepoints == ["U+0041", "U+25CC"]
    with pytest.raises(
        ValueError,
        match=r"Tirhuta conversion: U\+0041 U\+25CC$",
    ):
        recover_videha_janaki_trace(chars, strict=True, **profile)


def test_strict_gate_reports_the_full_known_issue_001_residual_set():
    chars = tuple((ord(char), index) for index, char in enumerate("◌*^", start=1))
    result = recover_videha_janaki_trace(chars, **ISSUE_001)
    assert result.unicode_text == "◌*^"
    assert result.unmapped_codepoints == ["U+002A", "U+005E", "U+25CC"]
    with pytest.raises(
        ValueError,
        match=r"Tirhuta conversion: U\+002A U\+005E U\+25CC$",
    ):
        recover_videha_janaki_trace(chars, strict=True, **ISSUE_001)


def test_strict_recovery_accepts_shared_punctuation_and_structural_whitespace():
    text = "क।॥,!? 123\t\r\n"
    result = recover_videha_janaki_trace(
        tuple((ord(char), index) for index, char in enumerate(text)),
        strict=True,
        **ISSUE_001,
    )
    assert result.unicode_text == "𑒏।॥,!? 123\t\r\n"
    assert result.unmapped_codepoints == []


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"pdf_sha256": "0" * 64}, "PDF SHA-256"),
        ({"janaki_font_sha256": set()}, "font fingerprint"),
        ({"page_count": 1}, "page count"),
        ({"profile": "unknown"}, "unsupported Videha profile"),
    ],
)
def test_recovery_rejects_any_profile_mismatch(override, message):
    profile = {**ISSUE_001, **override}
    with pytest.raises(VidehaProfileError, match=message):
        recover_videha_janaki_trace(((ord("क"), 1),), **profile)


def test_recovery_rejects_unknown_or_malformed_trace_characters():
    with pytest.raises(UnknownJanakiGlyphError, match="9999"):
        recover_videha_janaki_trace(((0xFFFD, 9999),), **ISSUE_001)
    with pytest.raises(VidehaProfileError, match="fewer than two"):
        recover_videha_janaki_trace(((0xFFFD,),), **ISSUE_001)
    with pytest.raises(VidehaProfileError, match="invalid codepoint/GID"):
        recover_videha_janaki_trace((("not-a-codepoint", 245),), **ISSUE_001)


def test_strict_gate_runs_after_profile_and_trace_validation():
    bad_profile = {**ISSUE_001, "pdf_sha256": "0" * 64}
    with pytest.raises(VidehaProfileError, match="PDF SHA-256"):
        recover_videha_janaki_trace(((ord("A"), 1),), strict=True, **bad_profile)
    with pytest.raises(UnknownJanakiGlyphError, match="9999"):
        recover_videha_janaki_trace(((ord("A"), 1), (0xFFFD, 9999)), strict=True, **ISSUE_001)
    with pytest.raises(VidehaProfileError, match="fewer than two"):
        recover_videha_janaki_trace(((ord("A"), 1), (0xFFFD,)), strict=True, **ISSUE_001)
