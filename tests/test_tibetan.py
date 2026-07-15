"""BDRC TibetanMachine legacy-table conversion tests."""

import csv
import hashlib
import unicodedata
from importlib import resources

import pytest

from nepal_ttf2utf import convert, convert_tibetanmachine
from nepal_ttf2utf.tibetan import TibetanMachineConverter

_MAP_RESOURCE = resources.files("nepal_ttf2utf.maps") / "TibetanMachine.csv"
_MAP_BYTES = _MAP_RESOURCE.read_bytes()
_PINNED_ROWS = tuple(
    (int(row["source_codepoint"]), row["target"])
    for row in csv.DictReader(
        line for line in _MAP_BYTES.decode("utf-8").splitlines() if not line.startswith("#")
    )
)


def test_tibetanmachine_map_matches_the_pinned_bdrc_source_and_runtime_inventory():
    assert hashlib.sha256(_MAP_BYTES).hexdigest() == (
        "eabcdd119ee7fa81ca221e3879745d3886ec4293b1bca72801a18498972cbc24"
    )
    assert len(_PINNED_ROWS) == 217
    assert len({source for source, _target in _PINNED_ROWS}) == 217
    assert sum(not target for _source, target in _PINNED_ROWS) == 12

    converter = TibetanMachineConverter.default()
    assert len(converter._table) == 244


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
        ("source_codepoint,target\n-1,ཀ\n", "invalid/duplicate TibetanMachine source"),
        ("source_codepoint,target\n1114112,ཀ\n", "invalid/duplicate TibetanMachine source"),
        (
            "source_codepoint,target\n33,ཀ\n33,ཁ\n",
            "invalid/duplicate TibetanMachine source",
        ),
        ("source_codepoint,target\n33\n", "missing TibetanMachine target"),
        ("source_codepoint,target\n33,A\n", "non-Tibetan or unassigned target"),
        ("source_codepoint,target\n33,\u0f48\n", "non-Tibetan or unassigned target"),
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


@pytest.mark.parametrize("codepoint", [0xE010, 0xE013])
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


def test_convert_dispatches_to_tibetanmachine():
    assert convert("!", font="tibetanmachine", strict=True) == "ཀ"
