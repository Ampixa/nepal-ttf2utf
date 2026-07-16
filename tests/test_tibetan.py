"""BDRC TibetanMachine legacy-table conversion tests."""

import csv
import hashlib
import io
import json
import unicodedata
from collections import Counter
from collections.abc import Mapping
from importlib import resources
from itertools import repeat

import pytest

from nepal_ttf2utf import convert, convert_tibetanmachine, supported_fonts
from nepal_ttf2utf.tibetan import (
    _ALLOWED_SOURCES,
    _DECODED_CP1252_SOURCES,
    _MAX_MAP_FILE_BYTES,
    _MAX_TABLE_ENTRIES,
    _RAW_BYTE_SOURCES,
    TIBETANMACHINE_NOTDEF_PUA,
    TibetanMachineConverter,
)

_MAP_RESOURCE = resources.files("nepal_ttf2utf.maps") / "TibetanMachine.csv"
_MAP_BYTES = _MAP_RESOURCE.read_bytes()
_PINNED_ROWS = tuple(
    (int(row["source_codepoint"]), row["target"])
    for row in csv.DictReader(
        line for line in _MAP_BYTES.decode("utf-8").splitlines() if not line.startswith("#")
    )
)


class _InfiniteItemsMapping(Mapping):
    def __getitem__(self, key):
        raise KeyError(key)

    def __iter__(self):
        return iter(())

    def __len__(self):
        return 1

    def items(self):
        return repeat((0x21, "ཀ"))


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


class _TibetanString(str):
    pass


def _effective_payload(converter: TibetanMachineConverter) -> bytes:
    return json.dumps(
        [
            [source, [ord(character) for character in target]]
            for source, target in sorted(converter._table.items())
        ],
        separators=(",", ":"),
    ).encode("ascii")


def test_tibetanmachine_map_matches_the_pinned_bdrc_source_and_runtime_inventory():
    assert len(_MAP_BYTES) == 2270
    assert len(_MAP_BYTES.decode("utf-8").splitlines()) == 221
    assert hashlib.sha256(_MAP_BYTES).hexdigest() == (
        "eabcdd119ee7fa81ca221e3879745d3886ec4293b1bca72801a18498972cbc24"
    )
    assert len(_PINNED_ROWS) == 217
    assert len({source for source, _target in _PINNED_ROWS}) == 217
    assert sum(not target for _source, target in _PINNED_ROWS) == 12
    assert Counter(len(target) for _source, target in _PINNED_ROWS) == {
        0: 12,
        1: 105,
        2: 82,
        3: 18,
    }

    converter = TibetanMachineConverter.default()
    assert len(converter._table) == 244
    assert len(_RAW_BYTE_SOURCES) == 223
    assert len(_DECODED_CP1252_SOURCES) == 27
    assert len(_ALLOWED_SOURCES) == _MAX_TABLE_ENTRIES == 250
    assert set(converter._table) <= _ALLOWED_SOURCES
    assert _ALLOWED_SOURCES - set(converter._table) == {
        0x0081,
        0x008D,
        0x008F,
        0x0090,
        0x009D,
        0x00FF,
    }
    assert Counter(len(target) for target in converter._table.values()) == {
        0: 14,
        1: 107,
        2: 93,
        3: 30,
    }
    assert len(set(converter._table.values())) == 166
    payload = _effective_payload(converter)
    assert len(payload) == 3832
    assert hashlib.sha256(payload).hexdigest() == (
        "0601c7fafb91066fdbc5b5c7ac0d320494236b78fb176b04b74a4c93723208e8"
    )


def test_every_tibetanmachine_source_row_has_exact_nfc_output_and_diagnostics():
    converter = TibetanMachineConverter.default()
    for source, target in _PINNED_ROWS:
        label = f"U+{source:04X}"
        expected = " " if source == 0x00A0 else unicodedata.normalize("NFC", target)
        result = converter.convert(chr(source))

        assert result.unicode_text == expected, label
        assert result.replacement_count == 1, label
        assert result.tibetan_char_count == sum(
            0x0F00 <= ord(char) <= 0x0FFF for char in expected
        ), label
        expected_empty = [] if target or source == 0x00A0 else [label]
        assert result.empty_codepoints == expected_empty, label
        assert result.missing_glyph_codepoints == [], label
        assert result.unmapped_codepoints == [], label

        if target or source == 0x00A0:
            assert convert_tibetanmachine(chr(source), strict=True).unicode_text == expected


def test_every_cp1252_decoded_and_raw_byte_alias_has_identical_output():
    converter = TibetanMachineConverter.default()
    raw_sources = {source for source, _target in _PINNED_ROWS}
    aliases: list[tuple[int, int]] = []
    for decoded, _target in _PINNED_ROWS:
        if decoded <= 0xFF:
            continue
        try:
            raw = chr(decoded).encode("cp1252")
        except UnicodeEncodeError:
            continue
        if len(raw) == 1 and raw[0] not in raw_sources:
            aliases.append((decoded, raw[0]))

    assert len(aliases) == 27
    assert set(converter._table) == raw_sources | {raw for _decoded, raw in aliases}
    for decoded, raw in aliases:
        decoded_result = converter.convert(chr(decoded))
        raw_result = converter.convert(chr(raw))
        assert raw_result.unicode_text == decoded_result.unicode_text
        assert raw_result.tibetan_char_count == decoded_result.tibetan_char_count
        assert raw_result.replacement_count == decoded_result.replacement_count == 1
        assert raw_result.missing_glyph_codepoints == decoded_result.missing_glyph_codepoints == []
        assert raw_result.unmapped_codepoints == decoded_result.unmapped_codepoints == []


def test_every_byte_has_an_exact_tibetanmachine_classification():
    converter = TibetanMachineConverter.default()
    counts: Counter[str] = Counter()
    structural = {" ", "\t", "\r", "\n"}

    for codepoint in range(0x100):
        source = chr(codepoint)
        label = f"U+{codepoint:04X}"
        result = converter.convert(source)
        if codepoint == 0x00A0:
            classification = "nbsp"
            assert result.unicode_text == " "
            assert result.replacement_count == 1
            assert result.empty_codepoints == []
        elif codepoint in converter._table:
            target = converter._table[codepoint]
            classification = "mapped" if target else "empty"
            assert result.unicode_text == unicodedata.normalize("NFC", target)
            assert result.replacement_count == 1
            assert result.empty_codepoints == ([] if target else [label])
        elif source in structural:
            classification = "structural"
            assert result.unicode_text == source
            assert result.replacement_count == 0
            assert result.empty_codepoints == []
        else:
            classification = "unmapped"
            assert result.unicode_text == source
            assert result.replacement_count == 0
            assert result.empty_codepoints == []
            assert result.unmapped_codepoints == [label]

        assert result.tibetan_char_count == sum(
            0x0F00 <= ord(character) <= 0x0FFF for character in result.unicode_text
        )
        assert result.missing_glyph_codepoints == []
        if classification in {"empty", "unmapped"}:
            with pytest.raises(ValueError, match=label.replace("+", r"\+")):
                convert_tibetanmachine(source, strict=True)
        else:
            assert result.unmapped_codepoints == []
            assert convert_tibetanmachine(source, strict=True) == result
        counts[classification] += 1

    assert counts == {
        "mapped": 205,
        "empty": 11,
        "nbsp": 1,
        "structural": 4,
        "unmapped": 35,
    }


def test_every_effective_target_pair_obeys_whole_output_nfc():
    converter = TibetanMachineConverter.default()
    effective_targets = {
        source: " " if source == 0x00A0 else target for source, target in converter._table.items()
    }
    cross_boundary_reorders = 0
    for first_source, first_target in effective_targets.items():
        for second_source, second_target in effective_targets.items():
            separate_nfc = unicodedata.normalize("NFC", first_target) + unicodedata.normalize(
                "NFC", second_target
            )
            whole_nfc = unicodedata.normalize("NFC", first_target + second_target)
            cross_boundary_reorders += whole_nfc != separate_nfc
            result = converter.convert(chr(first_source) + chr(second_source))
            assert result.unicode_text == whole_nfc
            assert result.replacement_count == 2
    assert cross_boundary_reorders == 825


def test_every_effective_empty_mapping_is_diagnostic_and_strictly_rejected():
    converter = TibetanMachineConverter.default()
    expected_sources = {
        0x002D,
        0x007F,
        0x008E,
        0x009E,
        0x00A6,
        0x00B0,
        0x00B1,
        0x00B2,
        0x00B3,
        0x00F0,
        0x00FC,
        0x017D,
        0x017E,
    }
    actual_sources = {
        source for source, target in converter._table.items() if not target and source != 0x00A0
    }
    assert actual_sources == expected_sources

    for source in sorted(expected_sources):
        label = f"U+{source:04X}"
        result = convert_tibetanmachine(chr(source))
        assert result.unicode_text == "", label
        assert result.empty_codepoints == [label], label
        with pytest.raises(ValueError, match=label.replace("+", r"\+")):
            convert_tibetanmachine(chr(source), strict=True)
        with pytest.raises(ValueError, match=label.replace("+", r"\+")):
            convert(chr(source), font="tibetanmachine", strict=True)


@pytest.mark.parametrize(
    ("map_text", "message"),
    [
        ("source_codepoint,target\nnot-a-number,ཀ\n", "invalid TibetanMachine source row"),
        ("source_codepoint,target\n-1,ཀ\n", "invalid TibetanMachine source row"),
        ("source_codepoint,target\n+33,ཀ\n", "invalid TibetanMachine source row"),
        ("source_codepoint,target\n033,ཀ\n", "invalid TibetanMachine source row"),
        ("source_codepoint,target\n1114112,ཀ\n", "invalid TibetanMachine source"),
        ("source_codepoint,target\n9,ཀ\n", "invalid TibetanMachine source"),
        ("source_codepoint,target\n32,ཀ\n", "invalid TibetanMachine source"),
        ("source_codepoint,target\n3904,ཁ\n", "invalid TibetanMachine source"),
        ("source_codepoint,target\n1114111,ཀ\n", "invalid TibetanMachine source"),
        (
            "source_codepoint,target\n33,ཀ\n33,ཁ\n",
            "duplicate TibetanMachine source",
        ),
        ("source_codepoint,target\n33\n", "missing TibetanMachine target"),
        ("source_codepoint,target\n33,A\n", "non-Tibetan or unassigned target"),
        ("source_codepoint,target\n33,\u0f48\n", "non-Tibetan or unassigned target"),
        ("source_codepoint,target\n33,ཀཁགང\n", "invalid TibetanMachine target"),
        ("source_codepoint,target\n160,ཀ\n", "U\\+00A0 target must be empty"),
        ("source_codepoint,target\n", "requires a non-empty map"),
        ('source_codepoint,target\n33,"ཀ', "invalid TibetanMachine CSV"),
        (
            "source_codepoint,target\n33,ཀ,ignored\n",
            "invalid TibetanMachine CSV row with extra fields",
        ),
        (
            "source_codepoint,target,notes\n33,ཀ,ignored\n",
            "invalid TibetanMachine CSV header",
        ),
        (
            "source_codepoint,target,target\n33,ignored,ཀ\n",
            "invalid TibetanMachine CSV header",
        ),
    ],
)
def test_tibetanmachine_parser_rejects_malformed_or_unassigned_rows(tmp_path, map_text, message):
    map_path = tmp_path / "TibetanMachine.csv"
    map_path.write_text(map_text, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        TibetanMachineConverter.from_map_file(map_path)


def test_tibetanmachine_parser_rejects_oversized_files_and_row_inventories(tmp_path):
    oversized = tmp_path / "oversized.csv"
    oversized.write_text("x" * (_MAX_MAP_FILE_BYTES + 1), encoding="utf-8")
    with pytest.raises(ValueError, match="map exceeds"):
        TibetanMachineConverter.from_map_file(oversized)

    long_source = tmp_path / "long-source.csv"
    long_source.write_text(
        f"source_codepoint,target\n{'9' * 5_000},ཀ\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="invalid TibetanMachine source row"):
        TibetanMachineConverter.from_map_file(long_source)

    too_many_rows = tmp_path / "too-many-rows.csv"
    rows = ["source_codepoint,target"] + [f"{source},ཀ" for source in range(_MAX_TABLE_ENTRIES + 1)]
    too_many_rows.write_text("\n".join(rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="source rows"):
        TibetanMachineConverter.from_map_file(too_many_rows)


def test_tibetanmachine_parser_accepts_the_exact_file_size_limit(tmp_path):
    base = "source_codepoint,target\n33,ཀ\n".encode()
    payload = base + b"#" + b"x" * (_MAX_MAP_FILE_BYTES - len(base) - 1)
    assert len(payload) == _MAX_MAP_FILE_BYTES
    exact = tmp_path / "exact-limit.csv"
    exact.write_bytes(payload)

    converter = TibetanMachineConverter.from_map_file(exact)
    assert dict(converter._table) == {0x21: "ཀ"}


def test_tibetanmachine_parser_bounds_the_open_stream_instead_of_trusting_stat(
    tmp_path, monkeypatch
):
    map_path = tmp_path / "growing.csv"
    map_path.write_text("source_codepoint,target\n33,ཀ\n", encoding="utf-8")
    oversized = b"x" * (_MAX_MAP_FILE_BYTES + 1)
    path_type = type(map_path)
    original_open = path_type.open
    observed_sizes = []

    class ObservedStream(io.BytesIO):
        def read(self, size=-1):
            observed_sizes.append(size)
            return super().read(size)

    def growing_open(self, mode="r", *args, **kwargs):
        if self == map_path and mode == "rb":
            return ObservedStream(oversized)
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(path_type, "open", growing_open)
    with pytest.raises(ValueError, match="map exceeds 1000000 bytes"):
        TibetanMachineConverter.from_map_file(map_path)
    assert observed_sizes == [_MAX_MAP_FILE_BYTES + 1]


def test_tibetanmachine_parser_normalizes_invalid_utf8(tmp_path):
    invalid = tmp_path / "invalid-utf8.csv"
    invalid.write_bytes(b"source_codepoint,target\n33,\xff\n")

    with pytest.raises(ValueError, match="invalid UTF-8 in TibetanMachine map"):
        TibetanMachineConverter.from_map_file(invalid)


def test_tibetanmachine_parser_requires_consistent_explicit_cp1252_aliases(tmp_path):
    conflicting = tmp_path / "conflicting.csv"
    conflicting.write_text(
        "source_codepoint,target\n128,ཀ\n8364,ཁ\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="conflicting TibetanMachine decoded/raw CP1252"):
        TibetanMachineConverter.from_map_file(conflicting)

    consistent = tmp_path / "consistent.csv"
    consistent.write_text(
        "source_codepoint,target\n128,ཀ\n8364,ཀ\n",
        encoding="utf-8",
    )
    converter = TibetanMachineConverter.from_map_file(consistent)
    assert dict(converter._table) == {128: "ཀ", 8364: "ཀ"}
    assert converter.convert("\x80€").unicode_text == "ཀཀ"


def test_tibetanmachine_parser_adds_a_missing_raw_cp1252_alias(tmp_path):
    map_path = tmp_path / "decoded-only.csv"
    map_path.write_text("source_codepoint,target\n8364,ཀ\n", encoding="utf-8")
    converter = TibetanMachineConverter.from_map_file(map_path)
    assert dict(converter._table) == {128: "ཀ", 8364: "ཀ"}


def test_constructor_and_parser_complete_every_decoded_cp1252_raw_alias_identically(tmp_path):
    decoded_table = {source: "ཀ" for source in _DECODED_CP1252_SOURCES}
    map_path = tmp_path / "decoded-cp1252.csv"
    rows = ["source_codepoint,target", *(f"{source},ཀ" for source in sorted(decoded_table))]
    map_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    direct = TibetanMachineConverter(decoded_table)
    parsed = TibetanMachineConverter.from_map_file(map_path)
    assert dict(direct._table) == dict(parsed._table)
    assert len(direct._table) == 54

    for decoded_source in sorted(_DECODED_CP1252_SOURCES):
        raw_source = chr(decoded_source).encode("cp1252")[0]
        assert direct._table[decoded_source] == direct._table[raw_source] == "ཀ"
        assert direct.convert(chr(decoded_source)) == parsed.convert(chr(decoded_source))
        assert direct.convert(chr(raw_source)) == parsed.convert(chr(raw_source))


def test_constructor_does_not_invent_a_decoded_alias_from_a_raw_only_source():
    converter = TibetanMachineConverter({0x80: "ཀ"})

    assert dict(converter._table) == {0x80: "ཀ"}
    assert converter.convert("\x80").unicode_text == "ཀ"
    assert converter.convert("€").unmapped_codepoints == ["U+20AC"]


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ([], "table must be a mapping"),
        (None, "table must be a mapping"),
        ({}, "requires a non-empty map"),
        ({True: "ཀ"}, "invalid TibetanMachine source"),
        ({33.0: "ཀ"}, "invalid TibetanMachine source"),
        ({"33": "ཀ"}, "invalid TibetanMachine source"),
        ({0x20: "ཀ"}, "invalid TibetanMachine source"),
        ({0x09: "ཀ"}, "invalid TibetanMachine source"),
        ({0x100: "ཀ"}, "invalid TibetanMachine source"),
        ({0x0F40: "ཀ"}, "invalid TibetanMachine source"),
        ({0x2603: "ཀ"}, "invalid TibetanMachine source"),
        ({0xE010: "ཀ"}, "invalid TibetanMachine source"),
        ({0x10FFFF: "ཀ"}, "invalid TibetanMachine source"),
        ({0x21: None}, "invalid TibetanMachine target"),
        ({0x21: 3904}, "invalid TibetanMachine target"),
        ({0x21: _TibetanString("ཀ")}, "invalid TibetanMachine target"),
        ({0x21: "A"}, "non-Tibetan or unassigned target"),
        ({0x21: "\u0f48"}, "non-Tibetan or unassigned target"),
        ({0x21: "ཀཁགང"}, "invalid TibetanMachine target"),
        ({0xA0: "ཀ"}, "U\\+00A0 target must be empty"),
        ({0x80: "ཀ", 0x20AC: "ཁ"}, "conflicting TibetanMachine decoded/raw CP1252"),
        (_InfiniteItemsMapping(), "item sequence exceeds"),
        (_PathologicalItemsMapping(["bad"]), "invalid TibetanMachine table entry"),
        (_PathologicalItemsMapping([{0x21, "ཀ"}]), "invalid TibetanMachine table entry"),
        (_PathologicalItemsMapping([(0x21,)]), "invalid TibetanMachine table entry"),
        (_PathologicalItemsMapping([(0x21, "ཀ", "extra")]), "table entry exceeds"),
        (
            _PathologicalItemsMapping([(0x21, "ཀ"), (0x21, "ཁ")]),
            "duplicate TibetanMachine source",
        ),
    ],
)
def test_tibetanmachine_constructor_rejects_unsafe_tables(table, message):
    with pytest.raises(ValueError, match=message):
        TibetanMachineConverter(table)


def test_tibetanmachine_constructor_accepts_the_complete_source_and_target_boundaries():
    converter = TibetanMachineConverter(
        {
            0x21: "ཀ",
            0x80: "ཁ",
            0x20AC: "ཁ",
            0xA0: "",
            0xFF: "གངཅ",
        }
    )
    assert converter.convert("!").unicode_text == "ཀ"
    assert converter.convert("\x80€").unicode_text == "ཁཁ"
    assert converter.convert("\u00a0").unicode_text == " "
    assert converter.convert("ÿ").unicode_text == "གངཅ"


def test_tibetanmachine_constructor_snapshots_and_freezes_the_input_mapping():
    table = {0x21: "ཀ"}
    converter = TibetanMachineConverter(table)
    table[0x21] = "A"
    table[0x22] = "ཁ"
    assert converter.convert('!"').unicode_text == 'ཀ"'
    assert converter.convert('!"').unmapped_codepoints == ["U+0022"]
    with pytest.raises(TypeError):
        converter._table[0x21] = "A"


def test_tibetanmachine_basic_consonants_follow_bdrc_table():
    result = convert_tibetanmachine('!"#$')
    assert result.unicode_text == "ཀཁགང"
    assert result.tibetan_char_count == 4
    assert result.replacement_count == 4


def test_tibetanmachine_clusters_and_punctuation():
    assert convert_tibetanmachine("?@A", strict=True).unicode_text == "རྐརྒརྔ"
    assert convert_tibetanmachine(chr(201), strict=True).unicode_text == "༆༅"


def test_tibetanmachine_digits_map_in_order():
    assert convert_tibetanmachine("".join(chr(cp) for cp in range(190, 200))).unicode_text == (
        "༠༡༢༣༤༥༦༧༨༩"
    )


def test_tibetanmachine_cp1252_and_raw_byte_aliases_match():
    converter = TibetanMachineConverter.default()
    assert converter.convert("€").unicode_text == "སྒྱ"
    assert converter.convert(chr(0x80)).unicode_text == "སྒྱ"


def test_tibetanmachine_defined_empty_entry_is_reported():
    result = convert_tibetanmachine("-")
    assert result.unicode_text == ""
    assert result.empty_codepoints == ["U+002D"]
    with pytest.raises(ValueError):
        convert_tibetanmachine("-", strict=True)


def test_tibetanmachine_nbsp_matches_upstream_space_normalization():
    result = convert_tibetanmachine("\u00a0", strict=True)
    assert result.unicode_text == " "
    assert result.empty_codepoints == []


def test_tibetanmachine_unknown_and_unicode_passthrough():
    result = convert_tibetanmachine("☃")
    assert result.unicode_text == "☃"
    assert result.unmapped_codepoints == ["U+2603"]
    with pytest.raises(ValueError):
        convert_tibetanmachine("☃", strict=True)

    unicode_text = "བོད"
    result = convert_tibetanmachine(unicode_text, strict=True)
    assert result.unicode_text == unicode_text
    assert not result.unmapped_codepoints


@pytest.mark.parametrize("codepoint", sorted(TIBETANMACHINE_NOTDEF_PUA))
def test_tibetanmachine_notdef_pua_is_reported_as_missing_glyph(codepoint):
    source = chr(codepoint)
    result = convert_tibetanmachine(source)
    assert result.unicode_text == source
    assert result.missing_glyph_codepoints == [f"U+{codepoint:04X}"]
    assert result.unmapped_codepoints == []
    with pytest.raises(ValueError, match="missing"):
        convert_tibetanmachine(source, strict=True)


def test_tibetanmachine_map_targets_are_tibetan_and_output_is_nfc():
    converter = TibetanMachineConverter.default()
    result = converter.convert("!@A€¾")
    assert all(0x0F00 <= ord(char) <= 0x0FFF for char in result.unicode_text)
    assert result.unicode_text == unicodedata.normalize("NFC", result.unicode_text)


@pytest.mark.parametrize("font", ["tibetanmachine", "tibetan-machine"])
def test_every_tibetanmachine_alias_has_exact_strict_behavior(font):
    assert supported_fonts()[font] == "Tibetan"
    assert convert("!", font=font, strict=True) == "ཀ"
    with pytest.raises(ValueError, match=r"U\+002D"):
        convert("-", font=font, strict=True)
    with pytest.raises(ValueError, match=r"U\+2603"):
        convert("☃", font=font, strict=True)


@pytest.mark.parametrize("font", ["ABCDEF+TIBETANMACHINE", "ABCDEF+TIBETAN-MACHINE"])
def test_tibetanmachine_pdf_subset_aliases_have_exact_strict_behavior(font):
    assert convert("!", font=font, strict=True) == "ཀ"
    with pytest.raises(ValueError, match=r"U\+002D"):
        convert("-", font=font, strict=True)
