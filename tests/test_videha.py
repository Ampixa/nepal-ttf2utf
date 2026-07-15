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
    result = recover_videha_janaki_trace(((0xFFFD, 612),), **APRIL_2008)
    assert result.devanagari_text == "फ्रे"
    assert "�" not in result.unicode_text


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
