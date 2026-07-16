"""Hash-pinned Videha Janaki glyph-ID recovery tests."""

import hashlib
import json
import unicodedata
from collections import Counter
from collections.abc import Sequence
from itertools import repeat

import pytest

import nepal_ttf2utf.videha as videha_module
from nepal_ttf2utf import (
    VIDEHA_2008_04_15,
    VIDEHA_ISSUE_001,
    UnknownJanakiGlyphError,
    VidehaProfileError,
    convert_tirhuta,
    janaki_gid_map_sha256,
    recover_videha_janaki_trace,
)
from nepal_ttf2utf.videha import (
    _MAX_GLYPH_ID,
    _MAX_TRACE_CHARACTERS,
    _MAX_TRACE_FIELDS,
    _PROFILES,
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


class _IntSubclass(int):
    pass


class _ExplosiveTruthiness:
    def __bool__(self):
        raise AssertionError("Videha Boolean validation invoked user truthiness")


class _StringSubclass(str):
    pass


class _IntProxy:
    def __int__(self):
        return 245


class _InfiniteFingerprints:
    def __iter__(self):
        return repeat(next(iter(ISSUE_001["janaki_font_sha256"])))


class _BrokenSequence(Sequence):
    def __init__(self, value):
        self._value = value

    def __len__(self):
        return 1

    def __getitem__(self, index):
        if index < 2:
            return self._value
        raise RuntimeError("sequence bomb")


class _LengthMismatchSequence(Sequence):
    def __init__(self, value):
        self._value = value

    def __len__(self):
        return 1

    def __getitem__(self, index):
        if index < 2:
            return self._value
        raise IndexError(index)


class _OversizedSequence(Sequence):
    def __init__(self, length):
        self._length = length

    def __len__(self):
        return self._length

    def __getitem__(self, index):
        raise AssertionError("oversized sequence should be rejected before iteration")


def _map_payload(mapping) -> bytes:
    return json.dumps(
        {str(gid): text for gid, text in sorted(mapping.items())},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _profile_registry_payload() -> bytes:
    return json.dumps(
        {
            name: {
                "pdf_sha256": profile.pdf_sha256,
                "page_count": profile.page_count,
                "janaki_font_sha256": sorted(profile.janaki_font_sha256),
                "gid_map_sha256": janaki_gid_map_sha256(name),
            }
            for name, profile in sorted(_PROFILES.items())
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def test_functional_gid_maps_are_complete_and_stable():
    assert len(JANAKI_GID_TO_DEVANAGARI) == 164
    assert len(JANAKI_GID_EXTENSION_2008_04_15) == 34
    assert len(JANAKI_GID_TO_DEVANAGARI_2008_04_15) == 198
    assert set(JANAKI_GID_TO_DEVANAGARI).isdisjoint(JANAKI_GID_EXTENSION_2008_04_15)
    assert dict(JANAKI_GID_TO_DEVANAGARI_2008_04_15) == {
        **JANAKI_GID_TO_DEVANAGARI,
        **JANAKI_GID_EXTENSION_2008_04_15,
    }
    assert Counter(map(len, JANAKI_GID_TO_DEVANAGARI.values())) == {
        2: 13,
        3: 142,
        4: 6,
        5: 3,
    }
    assert Counter(map(len, JANAKI_GID_EXTENSION_2008_04_15.values())) == {
        2: 3,
        3: 27,
        4: 3,
        5: 1,
    }
    assert Counter(map(len, JANAKI_GID_TO_DEVANAGARI_2008_04_15.values())) == {
        2: 16,
        3: 169,
        4: 9,
        5: 4,
    }
    assert len(set(JANAKI_GID_TO_DEVANAGARI.values())) == 164
    assert len(set(JANAKI_GID_EXTENSION_2008_04_15.values())) == 34
    assert len(set(JANAKI_GID_TO_DEVANAGARI_2008_04_15.values())) == 198
    assert set(JANAKI_GID_TO_DEVANAGARI.values()).isdisjoint(
        JANAKI_GID_EXTENSION_2008_04_15.values()
    )
    for gid, target in JANAKI_GID_TO_DEVANAGARI_2008_04_15.items():
        assert type(gid) is int and 0 <= gid <= _MAX_GLYPH_ID
        assert type(target) is str and target
        assert unicodedata.normalize("NFC", target) == target
        assert all(0x0900 <= ord(character) <= 0x097F for character in target)
        assert convert_tirhuta(target, strict=True).unmapped_codepoints == []

    payloads = (
        (
            _map_payload(JANAKI_GID_TO_DEVANAGARI),
            2918,
            "ef23c410aeb6f75dedb3dffd255f00ba9da7ab66e9d4c76bc7b5ccf1af9cb963",
        ),
        (
            _map_payload(JANAKI_GID_EXTENSION_2008_04_15),
            617,
            "ff8d10751fb8ea49836e48184cd8734d85071aec423ca1ec21469d97503bc4ec",
        ),
        (
            _map_payload(JANAKI_GID_TO_DEVANAGARI_2008_04_15),
            3534,
            "28ad7cf9b34f5da6c0d3d2cd03d2af2fbd159fdc1bd46dee905f2ccfe50ba326",
        ),
    )
    for payload, expected_length, expected_digest in payloads:
        assert len(payload) == expected_length
        assert hashlib.sha256(payload).hexdigest() == expected_digest
    assert (
        janaki_gid_map_sha256(VIDEHA_ISSUE_001)
        == "ef23c410aeb6f75dedb3dffd255f00ba9da7ab66e9d4c76bc7b5ccf1af9cb963"
    )
    assert (
        janaki_gid_map_sha256(VIDEHA_2008_04_15)
        == "28ad7cf9b34f5da6c0d3d2cd03d2af2fbd159fdc1bd46dee905f2ccfe50ba326"
    )

    profile_payload = _profile_registry_payload()
    assert len(profile_payload) == 720
    assert hashlib.sha256(profile_payload).hexdigest() == (
        "51a00c27f5e48fbef1c4d0e8814bfbb2058ec613dce1acadce9a4205d91488b8"
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
    expected_devanagari = "".join(gid_map[gid] for gid in gids)
    expected_tirhuta = convert_tirhuta(expected_devanagari, strict=True)
    result = recover_videha_janaki_trace(
        tuple((0xFFFD, gid) for gid in gids), strict=True, **profile
    )
    assert result.profile == profile["profile"]
    assert result.devanagari_text == expected_devanagari
    assert result.unicode_text == expected_tirhuta.unicode_text
    assert result.replacement_count == len(gids)
    assert result.recovered_gids == gids
    assert result.tirhuta_char_count == expected_tirhuta.tirhuta_char_count
    assert result.unmapped_codepoints == []

    for gid in gids:
        target = gid_map[gid]
        expected = convert_tirhuta(target, strict=True)
        individual = recover_videha_janaki_trace(((0xFFFD, gid),), strict=True, **profile)
        assert individual.devanagari_text == target, gid
        assert individual.unicode_text == expected.unicode_text, gid
        assert individual.replacement_count == 1, gid
        assert individual.recovered_gids == (gid,), gid
        assert individual.tirhuta_char_count == expected.tirhuta_char_count, gid
        assert individual.unmapped_codepoints == [], gid


def test_every_april_extension_gid_is_profile_separated():
    for gid, target in JANAKI_GID_EXTENSION_2008_04_15.items():
        with pytest.raises(UnknownJanakiGlyphError, match=str(gid)):
            recover_videha_janaki_trace(((0xFFFD, gid),), **ISSUE_001)
        recovered = recover_videha_janaki_trace(((0xFFFD, gid),), strict=True, **APRIL_2008)
        assert recovered.devanagari_text == target


@pytest.mark.parametrize(
    ("profile", "gid_map"),
    [
        pytest.param(ISSUE_001, JANAKI_GID_TO_DEVANAGARI, id="issue-001"),
        pytest.param(APRIL_2008, JANAKI_GID_TO_DEVANAGARI_2008_04_15, id="april-2008"),
    ],
)
def test_every_absent_16_bit_gid_is_outside_the_profile_contract(profile, gid_map):
    for gid in range(_MAX_GLYPH_ID + 1):
        if gid in gid_map:
            continue
        try:
            recover_videha_janaki_trace(((0xFFFD, gid),), **profile)
        except UnknownJanakiGlyphError:
            pass
        else:
            raise AssertionError(f"absent GID {gid} recovered under {profile['profile']}")


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


def test_strict_gate_rejects_a_reserved_tirhuta_position():
    chars = ((0x114C8, 1),)
    result = recover_videha_janaki_trace(chars, **ISSUE_001)
    assert result.unicode_text == "\U000114c8"
    assert result.unmapped_codepoints == ["U+114C8"]
    with pytest.raises(ValueError, match=r"Tirhuta conversion: U\+114C8$"):
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


def test_gid_maps_and_profile_registry_are_immutable_private_snapshots(monkeypatch):
    maps = (
        JANAKI_GID_TO_DEVANAGARI,
        JANAKI_GID_EXTENSION_2008_04_15,
        JANAKI_GID_TO_DEVANAGARI_2008_04_15,
    )
    for mapping in maps:
        gid = next(iter(mapping))
        with pytest.raises(TypeError):
            mapping[9999] = "क"
        with pytest.raises(TypeError):
            del mapping[gid]
    with pytest.raises(TypeError):
        _PROFILES["forged"] = _PROFILES[VIDEHA_ISSUE_001]

    issue_digest = janaki_gid_map_sha256(VIDEHA_ISSUE_001)
    april_digest = janaki_gid_map_sha256(VIDEHA_2008_04_15)
    monkeypatch.setattr(videha_module, "JANAKI_GID_TO_DEVANAGARI", {9999: "क"})
    monkeypatch.setattr(videha_module, "JANAKI_GID_EXTENSION_2008_04_15", {9998: "ख"})
    monkeypatch.setattr(videha_module, "JANAKI_GID_TO_DEVANAGARI_2008_04_15", {9997: "ग"})
    assert janaki_gid_map_sha256(VIDEHA_ISSUE_001) == issue_digest
    assert janaki_gid_map_sha256(VIDEHA_2008_04_15) == april_digest
    with pytest.raises(UnknownJanakiGlyphError, match="9999"):
        recover_videha_janaki_trace(((0xFFFD, 9999),), strict=True, **ISSUE_001)


@pytest.mark.parametrize(
    "profile",
    [None, [], 1, _StringSubclass(VIDEHA_ISSUE_001)],
)
def test_profile_names_require_exact_strings(profile):
    with pytest.raises(VidehaProfileError, match="profile"):
        janaki_gid_map_sha256(profile)
    values = {**ISSUE_001, "profile": profile}
    with pytest.raises(VidehaProfileError, match="profile"):
        recover_videha_janaki_trace((), **values)


@pytest.mark.parametrize(
    "pdf_sha256",
    [None, b"0" * 64, "0" * 63, "0" * 65, "g" * 64, "०" * 64, _StringSubclass("0" * 64)],
)
def test_pdf_fingerprint_requires_an_exact_64_hex_string(pdf_sha256):
    values = {**ISSUE_001, "pdf_sha256": pdf_sha256}
    with pytest.raises(VidehaProfileError, match="64 ASCII hexadecimal"):
        recover_videha_janaki_trace((), **values)


def test_profile_fingerprints_accept_uppercase_but_require_exact_sets():
    uppercase = {
        **ISSUE_001,
        "pdf_sha256": ISSUE_001["pdf_sha256"].upper(),
        "janaki_font_sha256": [value.upper() for value in ISSUE_001["janaki_font_sha256"]],
    }
    assert recover_videha_janaki_trace((), strict=True, **uppercase).unicode_text == ""

    expected_fonts = sorted(ISSUE_001["janaki_font_sha256"])
    invalid_sets = (
        None,
        "".join(expected_fonts),
        {expected_fonts[0]: expected_fonts[1]},
        [],
        [expected_fonts[0]],
        [expected_fonts[0], expected_fonts[0]],
        [*expected_fonts, expected_fonts[0]],
        [expected_fonts[0], b"0" * 64],
        [expected_fonts[0], "g" * 64],
        _InfiniteFingerprints(),
    )
    for fingerprints in invalid_sets:
        values = {**ISSUE_001, "janaki_font_sha256": fingerprints}
        with pytest.raises(VidehaProfileError, match="font"):
            recover_videha_janaki_trace((), **values)


@pytest.mark.parametrize("page_count", [None, True, 152.0, "152", _IntSubclass(152)])
def test_page_count_requires_an_exact_integer(page_count):
    values = {**ISSUE_001, "page_count": page_count}
    with pytest.raises(VidehaProfileError, match="page count"):
        recover_videha_janaki_trace((), **values)


@pytest.mark.parametrize(
    "strict",
    [
        None,
        0,
        1,
        -1,
        0.0,
        1.0,
        "",
        "false",
        (),
        [],
        {},
        object(),
        _IntSubclass(1),
        _ExplosiveTruthiness(),
    ],
)
def test_strict_flag_requires_a_boolean(strict):
    with pytest.raises(VidehaProfileError, match="strict flag"):
        recover_videha_janaki_trace((), strict=strict, **ISSUE_001)


def test_videha_preserves_profile_first_order_for_an_invalid_strict_flag():
    bad_profile = {**ISSUE_001, "pdf_sha256": "0" * 64}
    with pytest.raises(VidehaProfileError, match="PDF SHA-256"):
        recover_videha_janaki_trace((), strict=[], **bad_profile)


@pytest.mark.parametrize(
    "chars",
    [
        None,
        "trace",
        b"trace",
        bytearray(b"trace"),
        {(0xFFFD, 245): None},
        {(0xFFFD, 245)},
        iter(((0xFFFD, 245),)),
    ],
)
def test_trace_requires_a_finite_ordered_sequence(chars):
    with pytest.raises(VidehaProfileError, match="ordered sequence"):
        recover_videha_janaki_trace(chars, **ISSUE_001)


def test_trace_sequence_bounds_and_pathological_iteration_fail_closed():
    with pytest.raises(VidehaProfileError, match=str(_MAX_TRACE_CHARACTERS)):
        recover_videha_janaki_trace(
            _OversizedSequence(_MAX_TRACE_CHARACTERS + 1),
            **ISSUE_001,
        )
    with pytest.raises(VidehaProfileError, match="ordered sequence"):
        recover_videha_janaki_trace(_BrokenSequence((0xFFFD, 245)), **ISSUE_001)
    with pytest.raises(VidehaProfileError, match="length changed"):
        recover_videha_janaki_trace(
            _LengthMismatchSequence((0xFFFD, 245)),
            **ISSUE_001,
        )

    oversized_fields = (0xFFFD, 245, *(None for _ in range(_MAX_TRACE_FIELDS - 1)))
    with pytest.raises(VidehaProfileError, match=str(_MAX_TRACE_FIELDS)):
        recover_videha_janaki_trace((oversized_fields,), **ISSUE_001)
    with pytest.raises(VidehaProfileError, match="ordered sequence"):
        recover_videha_janaki_trace((_BrokenSequence(0xFFFD),), **ISSUE_001)


def test_trace_outer_and_field_limits_are_inclusive(monkeypatch):
    monkeypatch.setattr(videha_module, "_MAX_TRACE_CHARACTERS", 2)
    row = (ord("क"), 0, *(None for _ in range(_MAX_TRACE_FIELDS - 2)))
    result = recover_videha_janaki_trace((row, row), strict=True, **ISSUE_001)
    assert result.devanagari_text == "कक"
    with pytest.raises(VidehaProfileError, match="exceeds 2 values"):
        recover_videha_janaki_trace((row, row, row), **ISSUE_001)


@pytest.mark.parametrize(
    "trace_char",
    [
        None,
        "row",
        b"row",
        {"codepoint": 0xFFFD, "gid": 245},
        {0xFFFD, 245},
        iter((0xFFFD, 245)),
    ],
)
def test_trace_characters_require_finite_ordered_field_sequences(trace_char):
    with pytest.raises(VidehaProfileError, match="ordered sequence"):
        recover_videha_janaki_trace((trace_char,), **ISSUE_001)


@pytest.mark.parametrize(
    ("codepoint", "gid"),
    [
        (True, 245),
        (65533.9, 245.9),
        ("65533", "245"),
        (_IntSubclass(0xFFFD), 245),
        (0xFFFD, _IntSubclass(245)),
        (_IntProxy(), 245),
        (0xFFFD, _IntProxy()),
        (float("nan"), 245),
        (0xFFFD, float("inf")),
    ],
)
def test_trace_codepoint_and_gid_fields_require_exact_integers(codepoint, gid):
    with pytest.raises(VidehaProfileError, match="invalid codepoint/GID"):
        recover_videha_janaki_trace(((codepoint, gid),), **ISSUE_001)


@pytest.mark.parametrize("codepoint", [-1, 0xD800, 0xDFFF, 0x110000])
def test_trace_rejects_values_outside_the_unicode_scalar_domain(codepoint):
    with pytest.raises(VidehaProfileError, match="invalid Unicode codepoint"):
        recover_videha_janaki_trace(((codepoint, 0),), **ISSUE_001)


@pytest.mark.parametrize("gid", [-1, _MAX_GLYPH_ID + 1])
def test_trace_rejects_values_outside_the_glyph_id_domain(gid):
    with pytest.raises(VidehaProfileError, match="invalid glyph ID"):
        recover_videha_janaki_trace(((ord("क"), gid),), **ISSUE_001)


def test_trace_accepts_exact_scalar_gid_and_row_boundaries():
    for gid in (0, _MAX_GLYPH_ID):
        result = recover_videha_janaki_trace(
            ((ord("क"), gid, "origin", "bbox"),),
            strict=True,
            **ISSUE_001,
        )
        assert result.devanagari_text == "क"
        assert result.recovered_gids == ()

    result = recover_videha_janaki_trace(
        [(0, 0), (0x10FFFF, _MAX_GLYPH_ID)],
        **ISSUE_001,
    )
    assert result.devanagari_text == "\x00\U0010ffff"
    assert result.unmapped_codepoints == ["U+0000", "U+10FFFF"]


def test_trace_preserves_order_duplicates_and_empty_input():
    empty = recover_videha_janaki_trace([], strict=True, **ISSUE_001)
    assert empty.devanagari_text == empty.unicode_text == ""
    assert empty.recovered_gids == ()
    assert empty.replacement_count == 0

    trace = [(0xFFFD, 424), (0xFFFD, 245), (0xFFFD, 424)]
    result = recover_videha_janaki_trace(trace, strict=True, **ISSUE_001)
    assert result.devanagari_text == "नेप्रने"
    assert result.recovered_gids == (424, 245, 424)
    assert result.replacement_count == 3
