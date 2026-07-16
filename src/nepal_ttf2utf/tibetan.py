"""Convert extracted TibetanMachine legacy text to Unicode Tibetan.

The bundled mapping is the TibetanMachine table from BDRC's Apache-2.0
``py-tiblegenc`` project. This module converts an already extracted font span;
PDF extraction, font-span segmentation, and routing remain the caller's
responsibility. Unicode Tibetan families such as Monlam Unicode, Microsoft
Himalaya, Qomolangma, and Jomolhari require Unicode-span validation instead of
this legacy-byte table.
"""

from __future__ import annotations

import csv
import io
import unicodedata
from collections.abc import Mapping, Set
from dataclasses import dataclass
from importlib import resources
from itertools import islice
from pathlib import Path
from types import MappingProxyType

from ._controls import require_boolean, require_text
from .unicode_span import _is_assigned_script_codepoint

TIBETAN_LO, TIBETAN_HI = 0x0F00, 0x0FFF
_MAX_MAP_FILE_BYTES = 1_000_000
_MAX_TARGET_CODEPOINTS = 3


def _decoded_cp1252_sources() -> frozenset[int]:
    decoded: set[int] = set()
    for raw_byte in range(0x80, 0xA0):
        try:
            character = bytes((raw_byte,)).decode("cp1252")
        except UnicodeDecodeError:
            continue
        decoded.add(ord(character))
    return frozenset(decoded)


_RAW_BYTE_SOURCES = frozenset(range(0x21, 0x100))
_DECODED_CP1252_SOURCES = _decoded_cp1252_sources()
_ALLOWED_SOURCES = _RAW_BYTE_SOURCES | _DECODED_CP1252_SOURCES
_MAX_TABLE_ENTRIES = len(_ALLOWED_SOURCES)
_MAX_SOURCE_DIGITS = len(str(max(_ALLOWED_SOURCES)))

# Corpus-observed Type0 ToUnicode values that resolve to GID 0 (the embedded
# TibetanMachine font's visible .notdef placeholder), not to recoverable text.
TIBETANMACHINE_NOTDEF_PUA: frozenset[int] = frozenset({0xE010, 0xE013})


def _bounded_tuple(values: object, limit: int, label: str) -> tuple[object, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(f"invalid TibetanMachine {label}")
    try:
        result = tuple(islice(iter(values), limit + 1))  # type: ignore[arg-type]
    except TypeError as error:
        raise ValueError(f"invalid TibetanMachine {label}") from error
    if len(result) > limit:
        raise ValueError(f"TibetanMachine {label} exceeds {limit} entries")
    return result


def _validate_source(source: object) -> int:
    if type(source) is not int or source not in _ALLOWED_SOURCES:
        raise ValueError(
            f"invalid TibetanMachine source {source!r}; expected raw byte 0x21..0xFF "
            "or a decoded CP1252 character"
        )
    return source


def _validate_target(target: object, source: int) -> str:
    if type(target) is not str or len(target) > _MAX_TARGET_CODEPOINTS:
        raise ValueError(
            f"invalid TibetanMachine target for source U+{source:04X}; "
            f"expected zero to {_MAX_TARGET_CODEPOINTS} assigned Tibetan characters"
        )
    if any(not _is_assigned_script_codepoint(ord(char), "Tibetan") for char in target):
        raise ValueError(f"non-Tibetan or unassigned target for TibetanMachine source {source}")
    if source == 0x00A0 and target:
        raise ValueError(
            "TibetanMachine U+00A0 target must be empty; NBSP always normalizes to SPACE"
        )
    return target


def _normalize_table(table: object) -> dict[int, str]:
    if not isinstance(table, Mapping):
        raise ValueError("TibetanMachine table must be a mapping")
    items = _bounded_tuple(table.items(), _MAX_TABLE_ENTRIES, "table item sequence")
    normalized: dict[int, str] = {}
    for raw_item in items:
        if isinstance(raw_item, (str, bytes, Mapping, Set)):
            raise ValueError(f"invalid TibetanMachine table entry: {raw_item!r}")
        pair = _bounded_tuple(raw_item, 2, "table entry")
        if len(pair) != 2:
            raise ValueError(f"invalid TibetanMachine table entry: {raw_item!r}")
        source = _validate_source(pair[0])
        if source in normalized:
            raise ValueError(f"duplicate TibetanMachine source: {source}")
        normalized[source] = _validate_target(pair[1], source)
    if not normalized:
        raise ValueError("TibetanMachineConverter requires a non-empty map")
    # Extractors may expose WinAnsi values as decoded CP1252 characters or raw
    # byte scalars. A decoded source therefore owns the equivalent raw alias in
    # every construction path; an explicitly conflicting pair fails closed.
    for decoded_source in _DECODED_CP1252_SOURCES:
        raw_source = chr(decoded_source).encode("cp1252")[0]
        if decoded_source not in normalized:
            continue
        if raw_source in normalized:
            if normalized[decoded_source] != normalized[raw_source]:
                raise ValueError(
                    "conflicting TibetanMachine decoded/raw CP1252 targets for "
                    f"U+{decoded_source:04X} and U+{raw_source:04X}"
                )
            continue
        normalized[raw_source] = normalized[decoded_source]
    return normalized


@dataclass(frozen=True)
class TibetanMachineConversion:
    legacy_text: str
    unicode_text: str
    tibetan_char_count: int
    replacement_count: int
    missing_glyph_codepoints: list[str]
    empty_codepoints: list[str]
    unmapped_codepoints: list[str]


class TibetanMachineConverter:
    """Apply BDRC's TibetanMachine character table to extracted legacy text."""

    def __init__(self, table: Mapping[int, str]) -> None:
        self._table = MappingProxyType(_normalize_table(table))

    @classmethod
    def from_map_file(cls, path: str | Path) -> "TibetanMachineConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"TibetanMachine map does not exist: {map_path}")
        with map_path.open("rb") as map_file:
            map_bytes = map_file.read(_MAX_MAP_FILE_BYTES + 1)
        if len(map_bytes) > _MAX_MAP_FILE_BYTES:
            raise ValueError(f"TibetanMachine map exceeds {_MAX_MAP_FILE_BYTES} bytes: {map_path}")
        try:
            map_text = map_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"invalid UTF-8 in TibetanMachine map {map_path}") from error

        table: dict[int, str] = {}
        with io.StringIO(map_text, newline="") as stream:
            rows = (line for line in stream if not line.startswith("#"))
            try:
                reader = csv.DictReader(rows, strict=True)
                if reader.fieldnames != ["source_codepoint", "target"]:
                    raise ValueError(
                        "invalid TibetanMachine CSV header: expected "
                        "['source_codepoint', 'target'], got "
                        f"{reader.fieldnames!r}"
                    )
                for row_number, row in enumerate(reader, start=1):
                    if row_number > _MAX_TABLE_ENTRIES:
                        raise ValueError(
                            f"TibetanMachine map exceeds {_MAX_TABLE_ENTRIES} source rows"
                        )
                    if None in row:
                        raise ValueError(
                            f"invalid TibetanMachine CSV row with extra fields: {row!r}"
                        )
                    source_text = row.get("source_codepoint")
                    if (
                        not isinstance(source_text, str)
                        or not source_text.isascii()
                        or not source_text.isdecimal()
                        or len(source_text) > _MAX_SOURCE_DIGITS
                        or (len(source_text) > 1 and source_text.startswith("0"))
                    ):
                        raise ValueError(f"invalid TibetanMachine source row: {row!r}")
                    source = int(source_text)
                    if source in table:
                        raise ValueError(f"duplicate TibetanMachine source: {source}")
                    target = row.get("target")
                    if target is None:
                        raise ValueError(f"missing TibetanMachine target for source {source}")
                    table[source] = target
            except csv.Error as error:
                raise ValueError(f"invalid TibetanMachine CSV: {error}") from error
        return cls(table)

    @classmethod
    def default(cls) -> "TibetanMachineConverter":
        with resources.as_file(
            resources.files("nepal_ttf2utf.maps") / "TibetanMachine.csv"
        ) as path:
            return cls.from_map_file(path)

    def convert(self, text: str) -> TibetanMachineConversion:
        require_text(text)
        output: list[str] = []
        empty: set[str] = set()
        missing: set[str] = set()
        unmapped: set[str] = set()
        replacements = 0

        for char in text:
            codepoint = ord(char)
            # Match py-tiblegenc's pre-table normalization: NBSP is a real
            # space, not the table's visually empty U+00A0 slot.
            if char == "\u00a0":
                output.append(" ")
                replacements += 1
                continue
            if codepoint in self._table:
                target = self._table[codepoint]
                output.append(target)
                replacements += 1
                if not target:
                    empty.add(f"U+{codepoint:04X}")
                continue
            output.append(char)
            if codepoint in TIBETANMACHINE_NOTDEF_PUA:
                missing.add(f"U+{codepoint:04X}")
                continue
            if char in " \t\r\n" or _is_assigned_script_codepoint(codepoint, "Tibetan"):
                continue
            unmapped.add(f"U+{codepoint:04X}")

        converted = unicodedata.normalize("NFC", "".join(output))
        return TibetanMachineConversion(
            legacy_text=text,
            unicode_text=converted,
            tibetan_char_count=sum(TIBETAN_LO <= ord(char) <= TIBETAN_HI for char in converted),
            replacement_count=replacements,
            missing_glyph_codepoints=sorted(missing),
            empty_codepoints=sorted(empty),
            unmapped_codepoints=sorted(unmapped),
        )


_DEFAULT: TibetanMachineConverter | None = None


def convert_tibetanmachine(text: str, *, strict: bool = False) -> TibetanMachineConversion:
    """Convert a TibetanMachine-encoded text span to Unicode Tibetan (NFC).

    Defined empty-glyph entries follow BDRC's table in lenient mode but are
    reported in ``empty_codepoints``. Strict mode raises on either an empty
    entry or an unknown character so corpus pipelines can gate lossless output.
    """
    require_boolean(strict, "strict")
    require_text(text)
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = TibetanMachineConverter.default()
    result = _DEFAULT.convert(text)
    if strict and (
        result.missing_glyph_codepoints or result.empty_codepoints or result.unmapped_codepoints
    ):
        flagged = (
            result.missing_glyph_codepoints + result.empty_codepoints + result.unmapped_codepoints
        )
        raise ValueError(
            "missing/empty/unmapped characters after TibetanMachine conversion: "
            + " ".join(sorted(set(flagged)))
        )
    return result
