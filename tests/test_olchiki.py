"""'Ol Chiki Optimum' legacy display-font conversion tests.

Anchors are the shape-identity / corpus-position-verified assignments from the
public Aale Chhatka Santali e-magazine evidence summarized in ``docs/EVIDENCE.md``.
"""

import hashlib
import json
import unicodedata
from collections import Counter
from collections.abc import Mapping
from importlib import resources
from itertools import repeat

import pytest

import nepal_ttf2utf.olchiki as olchiki_module
from nepal_ttf2utf import (
    convert,
    convert_olchiki,
    convert_olchiki_latic,
    supported_fonts,
)
from nepal_ttf2utf.olchiki import (
    OLCHIKI_LATIC_OVERRIDES,
    OLCHIKI_LATIC_PASSTHROUGH,
    OLCHIKI_PASSTHROUGH,
    OLChikiConverter,
    OLChikiLaticConverter,
)
from nepal_ttf2utf.unicode_span import _is_assigned_script_codepoint


class _InfiniteItemsMapping(Mapping):
    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 1

    def items(self):
        return repeat((0x61, 0x1C5F))


class _PathologicalItemsMapping(Mapping):
    def __init__(self, items):
        self._items = items

    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self):
        return len(self._items)

    def items(self):
        return iter(self._items)


def _load_raw_map() -> dict:
    with resources.as_file(resources.files("nepal_ttf2utf.maps") / "olck_optimum.json") as p:
        return json.loads(p.read_text(encoding="utf-8"))


def _mapping_payload(converter: OLChikiConverter) -> bytes:
    return json.dumps(
        [[source, [target]] for source, target in sorted(converter._confirmed.items())],
        separators=(",", ":"),
    ).encode("ascii")


def _combined_contract_payload() -> bytes:
    optimum = OLChikiConverter.default()
    latic = OLChikiLaticConverter.default()
    return json.dumps(
        {
            "latic_overrides": [list(item) for item in sorted(OLCHIKI_LATIC_OVERRIDES.items())],
            "layouts": {
                name: {
                    "confirmed": [list(item) for item in sorted(converter._confirmed.items())],
                    "uncertain": [list(item) for item in sorted(converter._uncertain.items())],
                    "passthrough": sorted(ord(character) for character in converter._passthrough),
                }
                for name, converter in (("latic", latic), ("optimum", optimum))
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def test_olchiki_resource_and_effective_layout_contracts_are_pinned():
    resource = resources.files("nepal_ttf2utf.maps") / "olck_optimum.json"
    map_bytes = resource.read_bytes()
    assert len(map_bytes) == 2707
    assert len(map_bytes.decode("utf-8").splitlines()) == 76
    assert hashlib.sha256(map_bytes).hexdigest() == (
        "ded27e2a142a04d086d6031b2583b8ae4306ed540f591aa8fac8a71a89e04ce7"
    )

    raw = json.loads(map_bytes)
    assert set(raw) == {
        "_doc",
        "_derivation",
        "_confidence",
        "_uncertain_bytes",
        "map",
        "uncertain_map",
    }
    assert all(isinstance(raw[field], str) for field in ("_doc", "_derivation", "_confidence"))
    assert raw["_uncertain_bytes"] == []
    assert raw["uncertain_map"] == {}
    assert len(raw["map"]) == 63
    assert len(set(raw["map"])) == 63
    assert len({target[0] for target in raw["map"].values()}) == 43
    assert Counter(
        unicodedata.category(chr(int(target[0], 16))) for target in raw["map"].values()
    ) == {"Lo": 49, "Lm": 3, "Nd": 10, "Po": 1}

    optimum = OLChikiConverter.default()
    latic = OLChikiLaticConverter.default()
    assert (len(optimum._confirmed), len(set(optimum._confirmed.values()))) == (63, 43)
    assert (len(latic._confirmed), len(set(latic._confirmed.values()))) == (67, 47)
    assert optimum._uncertain == latic._uncertain == {}
    assert len(OLCHIKI_LATIC_OVERRIDES) == 9
    assert len(optimum._passthrough) == 15
    assert len(latic._passthrough) == 11

    optimum_payload = _mapping_payload(optimum)
    assert len(optimum_payload) == 781
    assert hashlib.sha256(optimum_payload).hexdigest() == (
        "91355469f4c726923f5b4618aaced072cf6589b0a9ee59733400b52874fcbda3"
    )
    latic_payload = _mapping_payload(latic)
    assert len(latic_payload) == 830
    assert hashlib.sha256(latic_payload).hexdigest() == (
        "3f0337524ddf766289416bd303725e797d3a14a99c3beddb5af4c3dd56fd81c4"
    )
    combined_payload = _combined_contract_payload()
    assert len(combined_payload) == 1675
    assert hashlib.sha256(combined_payload).hexdigest() == (
        "0b7aa84e70c42100fcbc517ea238038e2c4f670684cf0148152cda89fd99a3ef"
    )


@pytest.mark.parametrize("converter", [OLChikiConverter.default(), OLChikiLaticConverter.default()])
def test_every_effective_olchiki_mapping_has_exact_isolated_behavior(converter):
    for source, target in converter._confirmed.items():
        result = converter.convert(chr(source))
        assert result.unicode_text == chr(target), f"0x{source:02X}"
        assert result.olchiki_char_count == 1, f"0x{source:02X}"
        assert result.replacement_count == 1, f"0x{source:02X}"
        assert result.confirmed_byte_count == 1, f"0x{source:02X}"
        assert result.uncertain_bytes == [], f"0x{source:02X}"
        assert result.unmapped_bytes == [], f"0x{source:02X}"


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
    # Observed vowel-final placement (for example, 'hoN') matches the MU TTUDDAG
    # nasalization mark.
    conv = OLChikiConverter.default()
    assert conv.convert("N").unicode_text == "ᱸ"


def test_olchiki_mucaad_punctuation_from_positional_evidence():
    # Observed sentence-final placement matches the OL CHIKI PUNCTUATION MUCAAD
    # danda-equivalent.
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


@pytest.mark.parametrize(
    ("converter", "public_convert", "expected_counts"),
    [
        (OLChikiConverter.default(), convert_olchiki, (63, 4, 13, 176)),
        (OLChikiLaticConverter.default(), convert_olchiki_latic, (67, 4, 9, 176)),
    ],
)
def test_every_byte_has_an_exact_olchiki_layout_classification(
    converter, public_convert, expected_counts
):
    classification_counts: Counter[str] = Counter()
    passthrough_bytes = {
        ord(character) for character in converter._passthrough if ord(character) <= 0xFF
    }
    structural = {0x09, 0x0A, 0x0D, 0x20}

    for source in range(0x100):
        character = chr(source)
        result = converter.convert(character)
        if source in converter._confirmed:
            classification = "mapped"
            assert result.unicode_text == chr(converter._confirmed[source])
            assert result.olchiki_char_count == 1
            assert result.replacement_count == 1
            assert result.confirmed_byte_count == 1
        elif source in structural:
            classification = "structural"
            assert result.unicode_text == character
            assert result.olchiki_char_count == 0
            assert result.replacement_count == 0
            assert result.confirmed_byte_count == 0
        elif source in passthrough_bytes:
            classification = "passthrough"
            assert result.unicode_text == character
            assert result.olchiki_char_count == 0
            assert result.replacement_count == 0
            assert result.confirmed_byte_count == 0
        else:
            classification = "unmapped"
            assert result.unicode_text == character
            assert result.olchiki_char_count == 0
            assert result.replacement_count == 0
            assert result.confirmed_byte_count == 0
            assert result.unmapped_bytes == [character]
        assert result.uncertain_bytes == []
        if classification != "unmapped":
            assert result.unmapped_bytes == []
            assert public_convert(character, strict=True) == result
        else:
            with pytest.raises(ValueError, match=rf"U\+{source:04X}"):
                public_convert(character, strict=True)
        classification_counts[classification] += 1

    assert (
        tuple(
            classification_counts[name]
            for name in (
                "mapped",
                "structural",
                "passthrough",
                "unmapped",
            )
        )
        == expected_counts
    )


@pytest.mark.parametrize("public_convert", [convert_olchiki, convert_olchiki_latic])
def test_every_assigned_unicode_olchiki_character_passes_through_strictly(public_convert):
    for codepoint in range(0x1C50, 0x1C80):
        assert _is_assigned_script_codepoint(codepoint, "Ol Chiki")
        character = chr(codepoint)
        result = public_convert(character, strict=True)
        assert result.unicode_text == character
        assert result.olchiki_char_count == 1
        assert result.replacement_count == 0
        assert result.confirmed_byte_count == 0
        assert result.uncertain_bytes == []
        assert result.unmapped_bytes == []


@pytest.mark.parametrize(
    ("converter", "public_convert"),
    [
        (OLChikiConverter.default(), convert_olchiki),
        (OLChikiLaticConverter.default(), convert_olchiki_latic),
    ],
)
def test_every_olchiki_passthrough_character_is_strictly_clean(converter, public_convert):
    for character in converter._passthrough:
        result = public_convert(character, strict=True)
        assert result.unicode_text == character
        assert result.replacement_count == 0
        assert result.confirmed_byte_count == 0
        assert result.uncertain_bytes == []
        assert result.unmapped_bytes == []


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


@pytest.mark.parametrize(
    "font",
    [
        "olck-optimum",
        "olchiki-optimum",
        "olchiki",
        "aale-chhatka",
        "OLCKOptimum-Medium",
        "ABCDEF+OLCKOptimum-ExtraBlack",
    ],
)
def test_every_evidenced_optimum_alias_has_exact_strict_behavior(font):
    assert convert("a", font=font, strict=True) == "ᱟ"
    with pytest.raises(ValueError, match=r"U\+0040"):
        convert("@", font=font, strict=True)


def test_latic_letters_and_digits_share_optimum_semantics_except_v_w_swap():
    optimum = OLChikiConverter.default()
    latic = OLChikiLaticConverter.default()
    for byte in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz":
        if byte.lower() in {"v", "w"}:
            continue
        assert latic.convert(byte).unicode_text == optimum.convert(byte).unicode_text, byte
    assert latic.convert("vVwW").unicode_text == "ᱶᱶᱣᱣ"


@pytest.mark.parametrize("apply_uncertain", [False, True])
def test_latic_from_map_file_matches_default_semantics(apply_uncertain):
    with resources.as_file(resources.files("nepal_ttf2utf.maps") / "olck_optimum.json") as p:
        loaded = OLChikiLaticConverter.from_map_file(p, apply_uncertain=apply_uncertain)

    printable_ascii = "".join(chr(codepoint) for codepoint in range(0x20, 0x7F))
    assert type(loaded) is OLChikiLaticConverter
    assert loaded.convert(printable_ascii) == OLChikiLaticConverter.default(
        apply_uncertain=apply_uncertain
    ).convert(printable_ascii)

    result = loaded.convert("vVwW.-:~|")
    assert result.unicode_text == "ᱶᱶᱣᱣᱹᱼᱺᱻ᱾"
    assert result.replacement_count == 9
    assert result.confirmed_byte_count == 9
    assert result.uncertain_bytes == []
    assert result.unmapped_bytes == []


def test_latic_fixed_overrides_win_over_custom_base_map_uncertainty(tmp_path):
    map_path = tmp_path / "custom-olchiki.json"
    map_path.write_text(
        json.dumps(
            {
                "map": {
                    "61": ["1C5F"],
                    "76": ["1C63"],
                    "2E": ["1C60"],
                },
                "uncertain_map": {
                    "56": ["1C63"],
                    "7C": ["1C60"],
                    "40": ["1C60"],
                },
            }
        ),
        encoding="utf-8",
    )

    base_lenient_result = OLChikiConverter.from_map_file(map_path).convert("vV.|@")
    assert base_lenient_result.unicode_text == "ᱣVᱠ|@"
    assert base_lenient_result.replacement_count == 2
    assert base_lenient_result.confirmed_byte_count == 2
    assert base_lenient_result.uncertain_bytes == ["@", "V", "|"]
    assert base_lenient_result.unmapped_bytes == []

    base_opted_in_result = OLChikiConverter.from_map_file(map_path, apply_uncertain=True).convert(
        "vV.|@"
    )
    assert base_opted_in_result.unicode_text == "ᱣᱣᱠᱠᱠ"
    assert base_opted_in_result.replacement_count == 5
    assert base_opted_in_result.confirmed_byte_count == 2
    assert base_opted_in_result.uncertain_bytes == []
    assert base_opted_in_result.unmapped_bytes == []

    lenient = OLChikiLaticConverter.from_map_file(map_path)
    lenient_result = lenient.convert("vV.|@")
    assert lenient_result.unicode_text == "ᱶᱶᱹ᱾@"
    assert lenient_result.replacement_count == 4
    assert lenient_result.confirmed_byte_count == 4
    assert lenient_result.uncertain_bytes == ["@"]
    assert lenient_result.unmapped_bytes == []

    opted_in = OLChikiLaticConverter.from_map_file(map_path, apply_uncertain=True)
    opted_in_result = opted_in.convert("vV.|@")
    assert opted_in_result.unicode_text == "ᱶᱶᱹ᱾ᱠ"
    assert opted_in_result.replacement_count == 5
    assert opted_in_result.confirmed_byte_count == 4
    assert opted_in_result.uncertain_bytes == []
    assert opted_in_result.unmapped_bytes == []


def test_olchiki_map_factories_reject_empty_confirmed_map(tmp_path):
    map_path = tmp_path / "empty-olchiki.json"
    map_path.write_text(json.dumps({"map": {}, "uncertain_map": {}}), encoding="utf-8")

    for converter_type in (OLChikiConverter, OLChikiLaticConverter):
        with pytest.raises(ValueError, match="requires a non-empty confirmed map"):
            converter_type.from_map_file(map_path)


@pytest.mark.parametrize("converter_type", [OLChikiConverter, OLChikiLaticConverter])
@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "must be a JSON object"),
        ({"map": {"61": [123]}, "uncertain_map": {}}, "single hexadecimal-codepoint list"),
        ({"map": {"61": ["not-hex"]}, "uncertain_map": {}}, "invalid Ol Chiki codepoint"),
    ],
)
def test_olchiki_map_factories_reject_malformed_json_shapes(
    converter_type, payload, message, tmp_path
):
    map_path = tmp_path / "malformed-olchiki.json"
    map_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        converter_type.from_map_file(map_path)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"map": {"61": ["1C5F"]}}, "missing 'uncertain_map'"),
        ({"uncertain_map": {}}, "missing 'map'"),
        (
            {"map": {"61": ["1C5F"]}, "uncertain_map": {}, "unknown": True},
            "unexpected Ol Chiki map field",
        ),
        (
            {"_doc": [], "map": {"61": ["1C5F"]}, "uncertain_map": {}},
            "metadata must be a string",
        ),
        (
            {"map": {"61": ["1C5F"]}, "uncertain_map": {"61": ["1C60"]}},
            "sources overlap",
        ),
        (
            {
                "_uncertain_bytes": "62",
                "map": {"61": ["1C5F"]},
                "uncertain_map": {"62": ["1C60"]},
            },
            "must be a list",
        ),
        (
            {
                "_uncertain_bytes": None,
                "map": {"61": ["1C5F"]},
                "uncertain_map": {},
            },
            "must be a list",
        ),
        (
            {
                "_uncertain_bytes": ["62", "62"],
                "map": {"61": ["1C5F"]},
                "uncertain_map": {"62": ["1C60"]},
            },
            "duplicate uncertain",
        ),
        (
            {
                "_uncertain_bytes": ["63"],
                "map": {"61": ["1C5F"]},
                "uncertain_map": {"62": ["1C60"]},
            },
            "exactly match uncertain_map",
        ),
        (
            {
                "_uncertain_bytes": ["00"],
                "map": {"61": ["1C5F"]},
                "uncertain_map": {},
            },
            "printable ASCII",
        ),
    ],
)
def test_olchiki_map_loader_rejects_ambiguous_schema(payload, message, tmp_path):
    map_path = tmp_path / "ambiguous-olchiki.json"
    map_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        OLChikiConverter.from_map_file(map_path)


@pytest.mark.parametrize(
    "byte_key",
    ["0", "000", "061", "+61", "0x61", "6a", "6g", " 61", "61 ", "00", "20", "7F", "80"],
)
def test_olchiki_map_loader_rejects_noncanonical_or_protected_source_keys(byte_key, tmp_path):
    map_path = tmp_path / "bad-source-olchiki.json"
    map_path.write_text(
        json.dumps({"map": {byte_key: ["1C5F"]}, "uncertain_map": {}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        OLChikiConverter.from_map_file(map_path)


@pytest.mark.parametrize(
    "target",
    [[], ["1C5F", "1C60"], "1C5F", [123], ["1c5f"], ["01C5F"], ["0x1C5F"], ["0041"], ["D800"]],
)
def test_olchiki_map_loader_rejects_noncanonical_or_invalid_targets(target, tmp_path):
    map_path = tmp_path / "bad-target-olchiki.json"
    map_path.write_text(
        json.dumps({"map": {"61": target}, "uncertain_map": {}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        OLChikiConverter.from_map_file(map_path)


@pytest.mark.parametrize(
    "raw_json",
    [
        '{"map":{"61":["1C5F"],"61":["1C60"]},"uncertain_map":{}}',
        '{"map":{"61":["1C5F"]},"map":{"62":["1C60"]},"uncertain_map":{}}',
        '{"map":{"61":["1C5F"]},"uncertain_map":{"62":["1C60"],"62":["1C61"]}}',
    ],
)
def test_olchiki_map_loader_rejects_duplicate_json_keys(raw_json, tmp_path):
    map_path = tmp_path / "duplicate-olchiki.json"
    map_path.write_text(raw_json, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        OLChikiConverter.from_map_file(map_path)


def test_olchiki_map_loader_rejects_invalid_utf8_json_and_size(tmp_path):
    invalid_utf8 = tmp_path / "invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="invalid UTF-8"):
        OLChikiConverter.from_map_file(invalid_utf8)

    invalid_json = tmp_path / "invalid-json.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        OLChikiConverter.from_map_file(invalid_json)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * 1_000_001)
    with pytest.raises(ValueError, match="exceeds 1000000 bytes"):
        OLChikiConverter.from_map_file(oversized)


def test_olchiki_map_loader_fails_closed_on_deep_json(tmp_path):
    deeply_nested = tmp_path / "deeply-nested.json"
    deeply_nested.write_text(
        '{"map":' + "[" * 10_000 + "0" + "]" * 10_000 + ',"uncertain_map":{}}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        OLChikiConverter.from_map_file(deeply_nested)


def test_olchiki_map_loader_normalizes_decoder_recursion_error(monkeypatch, tmp_path):
    map_path = tmp_path / "recursive-decoder.json"
    map_path.write_text('{"map":{},"uncertain_map":{}}', encoding="utf-8")

    def recursive_decoder(*args, **kwargs):
        raise RecursionError("decoder nesting limit")

    monkeypatch.setattr(olchiki_module.json, "loads", recursive_decoder)
    with pytest.raises(ValueError, match="invalid nested JSON"):
        OLChikiConverter.from_map_file(map_path)


def test_olchiki_map_loader_bounds_section_inventory(tmp_path):
    entries = {f"{source:02X}": ["1C5F"] for source in range(129)}
    map_path = tmp_path / "too-many-entries.json"
    map_path.write_text(json.dumps({"map": entries, "uncertain_map": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="map exceeds 128 entries"):
        OLChikiConverter.from_map_file(map_path)


def test_olchiki_map_loader_accepts_exact_uncertainty_inventory(tmp_path):
    map_path = tmp_path / "valid-uncertainty.json"
    map_path.write_text(
        json.dumps(
            {
                "_doc": "fixture",
                "_derivation": "fixture",
                "_confidence": "fixture",
                "_uncertain_bytes": ["62"],
                "map": {"61": ["1C5F"]},
                "uncertain_map": {"62": ["1C60"]},
            }
        ),
        encoding="utf-8",
    )
    converter = OLChikiConverter.from_map_file(map_path)
    result = converter.convert("ab")
    assert result.unicode_text == "ᱟb"
    assert result.uncertain_bytes == ["b"]


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


@pytest.mark.parametrize(
    "font",
    [
        "olck-latic",
        "olcklatic",
        "olchiki-latic",
        "ABCDEF+OLCKLatic-Normal",
        "OLCKLatic-Bold",
        "OLCKLatic-UltraBlack",
    ],
)
def test_every_evidenced_latic_alias_has_exact_strict_behavior(font):
    assert convert("a.", font=font, strict=True) == "ᱟᱹ"
    with pytest.raises(ValueError, match=r"U\+0040"):
        convert("@", font=font, strict=True)


@pytest.mark.parametrize(
    "font",
    [
        "olckoptimum-black",
        "olcklatic-black",
        "olcklatic-extrablack",
        "olcklatic-medium",
    ],
)
def test_unaudited_weight_aliases_are_not_advertised_or_dispatched(font):
    assert font not in supported_fonts()
    with pytest.raises(ValueError, match="unsupported font key"):
        convert("a", font=font, strict=True)


def test_olchiki_empty_map_rejected():
    with pytest.raises(ValueError):
        OLChikiConverter({})


@pytest.mark.parametrize(
    "confirmed_map",
    [
        [],
        repeat((0x61, 0x1C5F)),
        {True: 0x1C5F},
        {"61": 0x1C5F},
        {-1: 0x1C5F},
        {0x00: 0x1C5F},
        {0x09: 0x1C5F},
        {0x0A: 0x1C5F},
        {0x0D: 0x1C5F},
        {0x20: 0x1C5F},
        {0x7F: 0x1C5F},
        {0x80: 0x1C5F},
        {0x1C5F: 0x1C60},
        {0x61: True},
        {0x61: "1C5F"},
        {0x61: -1},
        {0x61: 0x41},
        {0x61: 0xD800},
        {0x61: 0x110000},
    ],
)
def test_olchiki_constructor_rejects_unsafe_confirmed_maps(confirmed_map):
    with pytest.raises(ValueError):
        OLChikiConverter(confirmed_map)


@pytest.mark.parametrize(
    "uncertain_map",
    [
        [],
        {True: 0x1C5F},
        {0x00: 0x1C5F},
        {0x7F: 0x1C5F},
        {0x61: 0x41},
        {0x61: 0xD800},
    ],
)
def test_olchiki_constructor_rejects_unsafe_uncertain_maps(uncertain_map):
    with pytest.raises(ValueError):
        OLChikiConverter({0x62: 0x1C60}, uncertain_map)


def test_olchiki_constructor_rejects_confirmed_uncertain_overlap():
    with pytest.raises(ValueError, match=r"overlap.*0x61"):
        OLChikiConverter({0x61: 0x1C5F}, {0x61: 0x1C60})


@pytest.mark.parametrize("apply_uncertain", [None, 0, 1, "yes", object()])
def test_olchiki_constructor_requires_boolean_apply_uncertain(apply_uncertain):
    with pytest.raises(ValueError, match="must be a bool"):
        OLChikiConverter({0x61: 0x1C5F}, apply_uncertain=apply_uncertain)


@pytest.mark.parametrize("public_convert", [convert_olchiki, convert_olchiki_latic])
@pytest.mark.parametrize("apply_uncertain", [None, 0, 1, "yes"])
def test_public_olchiki_functions_require_boolean_apply_uncertain(public_convert, apply_uncertain):
    with pytest.raises(ValueError, match="must be a bool"):
        public_convert("a", apply_uncertain=apply_uncertain)


@pytest.mark.parametrize(
    "passthrough",
    [
        "!",
        b"!",
        {"key": "!"},
        [""],
        ["ab"],
        [1],
        [" "],
        ["\t"],
        ["\r"],
        ["\n"],
        ["\x00"],
        ["\x7f"],
        ["\x80"],
        ["\u00a0"],
        ["\u200b"],
        ["!", "!"],
    ],
)
def test_olchiki_constructor_rejects_invalid_passthrough(passthrough):
    with pytest.raises(ValueError):
        OLChikiConverter({0x61: 0x1C5F}, passthrough=passthrough)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: OLChikiConverter({0x61: 0x1C5F}, uncertain_map=_InfiniteItemsMapping()),
        lambda: OLChikiConverter(_InfiniteItemsMapping()),
        lambda: OLChikiConverter({0x61: 0x1C5F}, passthrough=repeat("!")),
    ],
)
def test_olchiki_constructor_rejects_unbounded_inputs_without_hanging(factory):
    with pytest.raises(ValueError, match="exceeds"):
        factory()


@pytest.mark.parametrize(
    ("mapping", "message"),
    [
        (
            _PathologicalItemsMapping(((0x61, 0x1C5F), (0x61, 0x1C60))),
            "duplicate.*source",
        ),
        (_PathologicalItemsMapping(({0x61, 0x1C5F},)), "invalid.*entry"),
        (_PathologicalItemsMapping(((0x61,),)), "invalid.*entry"),
    ],
)
def test_olchiki_constructor_rejects_pathological_mapping_items(mapping, message):
    with pytest.raises(ValueError, match=message):
        OLChikiConverter(mapping)


def test_olchiki_constructor_freezes_maps_passthrough_and_internal_tables():
    confirmed = {0x61: 0x1C5F}
    uncertain = {0x62: 0x1C60}
    passthrough = {"!"}
    converter = OLChikiConverter(
        confirmed,
        uncertain,
        apply_uncertain=True,
        passthrough=passthrough,
    )

    confirmed[0x61] = 0x1C61
    uncertain[0x62] = 0x1C62
    passthrough.clear()
    assert converter.convert("ab!").unicode_text == "ᱟᱠ!"
    assert converter.convert("ab!").unmapped_bytes == []
    with pytest.raises(TypeError):
        converter._confirmed[0x61] = 0x1C61
    with pytest.raises(TypeError):
        converter._uncertain[0x62] = 0x1C62
    with pytest.raises(TypeError):
        converter._table[0x61] = 0x1C61


def test_olchiki_custom_uncertainty_has_exact_lenient_and_opted_in_counts():
    lenient = OLChikiConverter(
        {0x61: 0x1C5F},
        {0x62: 0x1C60},
        passthrough={"!"},
    ).convert("ab!")
    assert lenient.unicode_text == "ᱟb!"
    assert lenient.olchiki_char_count == 1
    assert lenient.replacement_count == 1
    assert lenient.confirmed_byte_count == 1
    assert lenient.uncertain_bytes == ["b"]
    assert lenient.unmapped_bytes == []

    opted_in = OLChikiConverter(
        {0x61: 0x1C5F},
        {0x62: 0x1C60},
        apply_uncertain=True,
        passthrough={"!"},
    ).convert("ab!")
    assert opted_in.unicode_text == "ᱟᱠ!"
    assert opted_in.olchiki_char_count == 2
    assert opted_in.replacement_count == 2
    assert opted_in.confirmed_byte_count == 1
    assert opted_in.uncertain_bytes == []
    assert opted_in.unmapped_bytes == []


def test_direct_latic_construction_always_applies_fixed_immutable_contract():
    converter = OLChikiLaticConverter({0x61: 0x1C5F})
    result = converter.convert("avVwW.-:~|")
    assert result.unicode_text == "ᱟᱶᱶᱣᱣᱹᱼᱺᱻ᱾"
    assert result.replacement_count == 10
    assert result.confirmed_byte_count == 10
    assert result.uncertain_bytes == []
    assert result.unmapped_bytes == []
    with pytest.raises(TypeError):
        OLCHIKI_LATIC_OVERRIDES[ord("v")] = 0x1C63
