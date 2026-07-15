"""TibetanMachine legacy font -> Unicode Tibetan (U+0F00-U+0FFF).

The mapping is the TibetanMachine table from BDRC's Apache-2.0
``py-tiblegenc`` project. A recovered Gorkhapatra sample converted through the
same table produced 13,623 characters, including 12,801 Tibetan-block
characters and no U+FFFD replacements. This module converts an already
extracted text span; PDF font-span extraction and mixed-font segmentation stay
the caller's responsibility.

Monlam Unicode, Microsoft Himalaya, Qomolangma, and Jomolhari text observed in
the corpus is already Unicode and must not be sent through this legacy table.
"""

from __future__ import annotations

import csv
import unicodedata
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from .unicode_span import _is_assigned_script_codepoint

TIBETAN_LO, TIBETAN_HI = 0x0F00, 0x0FFF

# Corpus-observed Type0 ToUnicode values that resolve to GID 0 (the embedded
# TibetanMachine font's visible .notdef placeholder), not to recoverable text.
TIBETANMACHINE_NOTDEF_PUA: frozenset[int] = frozenset({0xE010, 0xE013})


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

    def __init__(self, table: dict[int, str]) -> None:
        if not table:
            raise ValueError("TibetanMachineConverter requires a non-empty map")
        self._table = dict(table)

    @classmethod
    def from_map_file(cls, path: str | Path) -> "TibetanMachineConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"TibetanMachine map does not exist: {map_path}")

        table: dict[int, str] = {}
        with map_path.open(encoding="utf-8", newline="") as stream:
            rows = (line for line in stream if not line.startswith("#"))
            try:
                reader = csv.DictReader(rows, strict=True)
                if reader.fieldnames != ["source_codepoint", "target"]:
                    raise ValueError(
                        "invalid TibetanMachine CSV header: expected "
                        "['source_codepoint', 'target'], got "
                        f"{reader.fieldnames!r}"
                    )
                for row in reader:
                    if None in row:
                        raise ValueError(
                            f"invalid TibetanMachine CSV row with extra fields: {row!r}"
                        )
                    try:
                        source = int(row["source_codepoint"])
                    except (KeyError, TypeError, ValueError) as error:
                        raise ValueError(f"invalid TibetanMachine source row: {row!r}") from error
                    if not (0 <= source <= 0x10FFFF) or source in table:
                        raise ValueError(f"invalid/duplicate TibetanMachine source: {source}")
                    target = row.get("target")
                    if target is None:
                        raise ValueError(f"missing TibetanMachine target for source {source}")
                    if any(
                        not _is_assigned_script_codepoint(ord(char), "Tibetan") for char in target
                    ):
                        raise ValueError(
                            f"non-Tibetan or unassigned target for TibetanMachine source {source}"
                        )
                    table[source] = target
            except csv.Error as error:
                raise ValueError(f"invalid TibetanMachine CSV: {error}") from error

        # PDF/text extractors may expose WinAnsi values either as their decoded
        # CP1252 character (for example U+20AC) or as the raw byte value. BDRC's
        # converter supports both representations; add the non-conflicting raw
        # aliases for CP1252's 0x80..0x9F region here too.
        aliases: dict[int, str] = {}
        for source, target in table.items():
            if source <= 0xFF:
                continue
            try:
                encoded = chr(source).encode("cp1252")
            except UnicodeEncodeError:
                continue
            if len(encoded) == 1 and encoded[0] not in table:
                aliases[encoded[0]] = target
        table.update(aliases)
        return cls(table)

    @classmethod
    def default(cls) -> "TibetanMachineConverter":
        with resources.as_file(
            resources.files("nepal_ttf2utf.maps") / "TibetanMachine.csv"
        ) as path:
            return cls.from_map_file(path)

    def convert(self, text: str) -> TibetanMachineConversion:
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
