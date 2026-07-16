"""Ol Chiki Optimum/Latic legacy fonts -> Unicode Ol Chiki (U+1C50-U+1C7F).

The public evidence source is the 2023 Aale Chhatka Santali e-magazine archived
as Internet Archive item ``aale-chhatka-pdf-e-magazine-2023``. Its embedded
OLCKOptimum display fonts address Ol Chiki glyph outlines with printable ASCII
source codes, so extracted PDF text requires a legacy-byte conversion.

The bundled Optimum table was derived from normalized rendered-outline
comparison against Unicode Ol Chiki references, constrained by script structure
and corpus context. It contains 52 letter or modifier sources, ten digit sources,
and one punctuation source. Twenty uppercase/lowercase pairs intentionally share
targets because their font outlines are identical; no Optimum source remains
uncertain.

OLCKLatic is a separate evidenced layout. It retains most Optimum semantics,
swaps the ``v/V`` and ``w/W`` assignments, and maps ``. - : ~ |`` to U+1C79,
U+1C7C, U+1C7A, U+1C7B, and U+1C7E. Exact PDF and embedded-font hashes,
derivation limits, and the pinned functional contracts are documented in
``docs/EVIDENCE.md``.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass, field
from importlib import resources
from itertools import islice
from pathlib import Path
from types import MappingProxyType

from ._controls import codepoint_labels, require_boolean, require_integer, require_text
from .unicode_span import _is_assigned_script_codepoint

OLCHIKI_LO, OLCHIKI_HI = 0x1C50, 0x1C7F
_BYTE_KEY_RE = re.compile(r"[0-9A-F]{2}")
_TARGET_KEY_RE = re.compile(r"[0-9A-F]{4}")
_MAX_MAP_FILE_BYTES = 1_000_000
_MAX_MAP_JSON_DEPTH = 64
_MAX_MAP_ENTRIES = 128
_MAX_PASSTHROUGH = 128
_MAP_FIELDS = frozenset(
    {"_doc", "_derivation", "_confidence", "_uncertain_bytes", "map", "uncertain_map"}
)

# ASCII punctuation the font renders as literal, unmodified glyphs (verified by
# rendering each candidate byte and comparing against a plain ASCII reference --
# these are NOT Ol Chiki shapes and pass through unchanged).
OLCHIKI_PASSTHROUGH: frozenset[str] = frozenset(
    {",", ".", "-", "'", "(", ")", '"', ":", ";", "?", "!", "~", "“", "”", "+"}
)

OLCHIKI_LATIC_OVERRIDES: Mapping[int, int] = MappingProxyType(
    {
        ord("v"): 0x1C76,
        ord("V"): 0x1C76,
        ord("w"): 0x1C63,
        ord("W"): 0x1C63,
        ord("."): 0x1C79,
        ord("-"): 0x1C7C,
        ord(":"): 0x1C7A,
        ord("~"): 0x1C7B,
        ord("|"): 0x1C7E,
    }
)
OLCHIKI_LATIC_PASSTHROUGH: frozenset[str] = OLCHIKI_PASSTHROUGH - frozenset(".-:~")


def _bounded_tuple(values: object, limit: int, label: str) -> tuple[object, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(f"invalid Ol Chiki {label}")
    try:
        result = tuple(islice(iter(values), limit + 1))  # type: ignore[arg-type]
    except Exception as error:
        if isinstance(error, (MemoryError, RecursionError)):
            raise
        raise ValueError(f"invalid Ol Chiki {label}") from error
    if len(result) > limit:
        raise ValueError(f"Ol Chiki {label} exceeds {limit} entries")
    return result


def _bounded_mapping_items(
    values: Mapping[object, object], limit: int, label: str
) -> tuple[object, ...]:
    try:
        items = values.items()
    except Exception as error:
        if isinstance(error, (MemoryError, RecursionError)):
            raise
        raise ValueError(f"invalid Ol Chiki {label}") from error
    return _bounded_tuple(items, limit, label)


def _validate_source_byte(source: object, label: str) -> int:
    source = require_integer(source, f"invalid Ol Chiki {label} source")
    if not (0x21 <= source <= 0x7E):
        raise ValueError(
            f"invalid Ol Chiki {label} source {source!r}; expected printable ASCII 0x21..0x7E"
        )
    return source


def _validate_target_codepoint(target: object, source: int, label: str) -> int:
    target = require_integer(
        target, f"invalid or unassigned Ol Chiki {label} target for source 0x{source:02X}"
    )
    if not _is_assigned_script_codepoint(target, "Ol Chiki"):
        raise ValueError(
            f"invalid or unassigned Ol Chiki {label} target {target!r} for source 0x{source:02X}"
        )
    return target


def _normalize_map(entries: object, label: str) -> dict[int, int]:
    if not isinstance(entries, Mapping):
        raise ValueError(f"Ol Chiki {label} must be a mapping")
    items = _bounded_mapping_items(entries, _MAX_MAP_ENTRIES, f"{label} item sequence")
    table: dict[int, int] = {}
    for raw_item in items:
        if isinstance(raw_item, (str, bytes, Mapping, Set)):
            raise ValueError(f"invalid Ol Chiki {label} entry")
        pair = _bounded_tuple(raw_item, 2, f"{label} entry")
        if len(pair) != 2:
            raise ValueError(f"invalid Ol Chiki {label} entry")
        raw_source, raw_target = pair
        source = _validate_source_byte(raw_source, label)
        if source in table:
            raise ValueError(f"duplicate Ol Chiki {label} source: 0x{source:02X}")
        table[source] = _validate_target_codepoint(raw_target, source, label)
    return table


def _normalize_passthrough(values: object) -> frozenset[str]:
    members = _bounded_tuple(values, _MAX_PASSTHROUGH, "passthrough sequence")
    normalized: set[str] = set()
    for member in members:
        if type(member) is not str:
            raise ValueError("invalid Ol Chiki passthrough character")
        if len(member) != 1 or member.isspace() or unicodedata.category(member).startswith("C"):
            raise ValueError(f"invalid Ol Chiki passthrough character: {member!r}")
        if member in normalized:
            raise ValueError(f"duplicate Ol Chiki passthrough character: {member!r}")
        normalized.add(member)
    return frozenset(normalized)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key in Ol Chiki map: {key!r}")
        result[key] = value
    return result


class _JSONNumberToken:
    __slots__ = ("seen",)

    def __init__(self) -> None:
        self.seen = False

    def __call__(self, _literal: str) -> object:
        self.seen = True
        return self


def _reject_excessive_json_depth(map_text: str, map_path: Path) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in map_text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > _MAX_MAP_JSON_DEPTH:
                raise ValueError(
                    f"Ol Chiki map exceeds {_MAX_MAP_JSON_DEPTH} JSON nesting levels: {map_path}"
                )
        elif character in "]}":
            depth = max(0, depth - 1)


def _load_map_file(path: str | Path) -> tuple[dict[int, int], dict[int, int]]:
    map_path = Path(path)
    if not map_path.is_file():
        raise FileNotFoundError(f"Ol Chiki legacy map does not exist: {map_path}")
    with map_path.open("rb") as map_file:
        map_bytes = map_file.read(_MAX_MAP_FILE_BYTES + 1)
    if len(map_bytes) > _MAX_MAP_FILE_BYTES:
        raise ValueError(f"Ol Chiki map exceeds {_MAX_MAP_FILE_BYTES} bytes: {map_path}")
    try:
        map_text = map_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"invalid UTF-8 in Ol Chiki map {map_path}") from error
    _reject_excessive_json_depth(map_text, map_path)
    number_token = _JSONNumberToken()
    try:
        raw = json.loads(
            map_text,
            object_pairs_hook=_unique_json_object,
            parse_int=number_token,
            parse_float=number_token,
            parse_constant=number_token,
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in Ol Chiki map {map_path}: {error.msg}") from error
    except RecursionError as error:
        raise ValueError(f"invalid nested JSON in Ol Chiki map {map_path}") from error
    if number_token.seen:
        raise ValueError(f"numeric JSON values are not permitted in Ol Chiki map: {map_path}")
    if not isinstance(raw, dict):
        raise ValueError(f"Ol Chiki map must be a JSON object: {map_path}")
    unexpected_fields = set(raw) - _MAP_FIELDS
    if unexpected_fields:
        fields = ", ".join(repr(field) for field in sorted(unexpected_fields))
        raise ValueError(f"unexpected Ol Chiki map field(s) {fields}: {map_path}")
    for metadata_name in ("_doc", "_derivation", "_confidence"):
        if metadata_name in raw and not isinstance(raw[metadata_name], str):
            raise ValueError(
                f"Ol Chiki map {metadata_name!r} metadata must be a string: {map_path}"
            )
    confirmed = _parse_map_section(raw.get("map"), "map", map_path)
    uncertain = _parse_map_section(raw.get("uncertain_map"), "uncertain_map", map_path)
    overlap = set(confirmed) & set(uncertain)
    if overlap:
        labels = " ".join(f"0x{source:02X}" for source in sorted(overlap))
        raise ValueError(f"Ol Chiki confirmed and uncertain map sources overlap: {labels}")

    if "_uncertain_bytes" in raw:
        uncertain_inventory = raw["_uncertain_bytes"]
        if not isinstance(uncertain_inventory, list):
            raise ValueError(f"Ol Chiki map '_uncertain_bytes' must be a list: {map_path}")
        if len(uncertain_inventory) > _MAX_MAP_ENTRIES:
            raise ValueError(
                f"Ol Chiki uncertain-byte inventory exceeds {_MAX_MAP_ENTRIES} entries"
            )
        inventory: set[int] = set()
        for byte_hex in uncertain_inventory:
            if not isinstance(byte_hex, str) or _BYTE_KEY_RE.fullmatch(byte_hex) is None:
                raise ValueError(
                    f"invalid uncertain Ol Chiki byte {byte_hex!r}; "
                    "expected two uppercase hex digits"
                )
            source = _validate_source_byte(int(byte_hex, 16), "uncertain inventory")
            if source in inventory:
                raise ValueError(f"duplicate uncertain Ol Chiki byte: {byte_hex}")
            inventory.add(source)
        if inventory != set(uncertain):
            raise ValueError("Ol Chiki '_uncertain_bytes' must exactly match uncertain_map sources")
    return confirmed, uncertain


def _parse_map_section(entries: object, section_name: str, map_path: Path) -> dict[int, int]:
    if not isinstance(entries, dict):
        raise ValueError(f"Ol Chiki map missing '{section_name}' object: {map_path}")
    if len(entries) > _MAX_MAP_ENTRIES:
        raise ValueError(f"Ol Chiki {section_name} exceeds {_MAX_MAP_ENTRIES} entries")
    table: dict[int, int] = {}
    for byte_hex, target in entries.items():
        if _BYTE_KEY_RE.fullmatch(byte_hex) is None:
            raise ValueError(
                f"invalid byte key in Ol Chiki map: {byte_hex!r}; expected two uppercase hex digits"
            )
        byte = _validate_source_byte(int(byte_hex, 16), section_name)
        if not isinstance(target, list) or len(target) != 1 or not isinstance(target[0], str):
            raise ValueError(
                f"Ol Chiki map target for byte {byte_hex} must be a single hexadecimal-codepoint "
                "list"
            )
        if _TARGET_KEY_RE.fullmatch(target[0]) is None:
            raise ValueError(
                f"invalid Ol Chiki codepoint target for byte {byte_hex}: {target[0]!r}; "
                "expected four uppercase hex digits"
            )
        table[byte] = _validate_target_codepoint(int(target[0], 16), byte, section_name)
    return table


@dataclass(frozen=True)
class OLChikiConversion:
    legacy_text: str
    unicode_text: str
    olchiki_char_count: int
    replacement_count: int
    confirmed_byte_count: int
    uncertain_bytes: list[str] = field(default_factory=list)
    unmapped_bytes: list[str] = field(default_factory=list)


class OLChikiConverter:
    """Byte->Unicode converter for the 'Ol Chiki Optimum' legacy display font.

    Each legacy byte maps to exactly one Ol Chiki codepoint (no reordering needed --
    unlike Lepcha, this font's vowel/modifier signs are typed in logical order
    already). No OLCKOptimum bytes are currently uncertain; ``apply_uncertain`` is
    retained for compatibility with the shared converter interface.
    """

    def __init__(
        self,
        confirmed_map: Mapping[int, int],
        uncertain_map: Mapping[int, int] | None = None,
        *,
        apply_uncertain: bool = False,
        passthrough: Iterable[str] = OLCHIKI_PASSTHROUGH,
    ) -> None:
        """Freeze a validated custom contract; explicit map entries precede passthrough."""
        require_boolean(apply_uncertain, "Ol Chiki apply_uncertain")
        confirmed = _normalize_map(confirmed_map, "confirmed map")
        uncertain = _normalize_map(
            uncertain_map if uncertain_map is not None else {}, "uncertain map"
        )
        if not confirmed:
            raise ValueError("OLChikiConverter requires a non-empty confirmed map")
        overlap = set(confirmed) & set(uncertain)
        if overlap:
            labels = " ".join(f"0x{source:02X}" for source in sorted(overlap))
            raise ValueError(f"Ol Chiki confirmed and uncertain map sources overlap: {labels}")
        normalized_passthrough = _normalize_passthrough(passthrough)
        self._confirmed = MappingProxyType(confirmed)
        self._uncertain = MappingProxyType(uncertain)
        self._apply_uncertain = apply_uncertain
        self._passthrough = normalized_passthrough
        table = dict(confirmed)
        if apply_uncertain:
            table.update(uncertain)
        self._table = MappingProxyType(table)

    @classmethod
    def from_map_file(
        cls, path: str | Path, *, apply_uncertain: bool = False
    ) -> "OLChikiConverter":
        require_boolean(apply_uncertain, "Ol Chiki apply_uncertain")
        confirmed, uncertain = _load_map_file(path)
        return cls(confirmed, uncertain, apply_uncertain=apply_uncertain)

    @classmethod
    def default(cls, *, apply_uncertain: bool = False) -> "OLChikiConverter":
        require_boolean(apply_uncertain, "Ol Chiki apply_uncertain")
        with resources.as_file(resources.files("nepal_ttf2utf.maps") / "olck_optimum.json") as p:
            return cls.from_map_file(p, apply_uncertain=apply_uncertain)

    def convert(self, text: str) -> OLChikiConversion:
        require_text(text)
        out: list[str] = []
        replacements = 0
        confirmed = 0
        uncertain_seen: set[str] = set()
        unmapped: set[str] = set()
        for ch in text:
            if ch in " \t\r\n":
                out.append(ch)
                continue
            code = ord(ch)
            mapped = self._table.get(code)
            if mapped is not None:
                out.append(chr(mapped))
                replacements += 1
                if code in self._confirmed:
                    confirmed += 1
                continue
            if code in self._uncertain:
                uncertain_seen.add(ch)
                out.append(ch)  # left untouched when not applying uncertain
                continue
            if ch in self._passthrough:
                out.append(ch)
                continue
            out.append(ch)
            if OLCHIKI_LO <= code <= OLCHIKI_HI:
                # Already a genuine Ol Chiki codepoint (e.g. a modifier sign the
                # author typed via a fallback Unicode font mixed into otherwise
                # legacy-encoded text) -- pass through, not a conversion failure.
                continue
            # Anything else reaching here is neither a mapped/uncertain legacy byte
            # nor known passthrough punctuation nor genuine Ol Chiki: surface it.
            unmapped.add(ch)
        converted = unicodedata.normalize("NFC", "".join(out))
        olc_count = sum(1 for c in converted if OLCHIKI_LO <= ord(c) <= OLCHIKI_HI)
        return OLChikiConversion(
            legacy_text=text,
            unicode_text=converted,
            olchiki_char_count=olc_count,
            replacement_count=replacements,
            confirmed_byte_count=confirmed,
            uncertain_bytes=sorted(uncertain_seen),
            unmapped_bytes=sorted(unmapped),
        )


class OLChikiLaticConverter(OLChikiConverter):
    """Converter for the OLCKLatic display family and its punctuation map.

    :meth:`from_map_file` accepts the same two-section Optimum base-map schema
    as :class:`OLChikiConverter`. The evidenced Latic assignments are
    authoritative and promoted to confirmed mappings even if the base map
    marks one as uncertain. ``apply_uncertain`` therefore affects only the
    remaining base-map bytes.
    """

    def __init__(
        self,
        confirmed_map: Mapping[int, int],
        uncertain_map: Mapping[int, int] | None = None,
        *,
        apply_uncertain: bool = False,
    ) -> None:
        require_boolean(apply_uncertain, "Ol Chiki apply_uncertain")
        confirmed = _normalize_map(confirmed_map, "confirmed map")
        uncertain = _normalize_map(
            uncertain_map if uncertain_map is not None else {}, "uncertain map"
        )
        if not confirmed:
            raise ValueError("OLChikiConverter requires a non-empty confirmed map")
        for source, target in OLCHIKI_LATIC_OVERRIDES.items():
            uncertain.pop(source, None)
            confirmed[source] = target
        super().__init__(
            confirmed,
            uncertain,
            apply_uncertain=apply_uncertain,
            passthrough=OLCHIKI_LATIC_PASSTHROUGH,
        )

    @classmethod
    def from_map_file(
        cls, path: str | Path, *, apply_uncertain: bool = False
    ) -> "OLChikiLaticConverter":
        require_boolean(apply_uncertain, "Ol Chiki apply_uncertain")
        confirmed, uncertain = _load_map_file(path)
        return cls(confirmed, uncertain, apply_uncertain=apply_uncertain)

    @classmethod
    def default(cls, *, apply_uncertain: bool = False) -> "OLChikiLaticConverter":
        require_boolean(apply_uncertain, "Ol Chiki apply_uncertain")
        with resources.as_file(resources.files("nepal_ttf2utf.maps") / "olck_optimum.json") as p:
            return cls.from_map_file(p, apply_uncertain=apply_uncertain)


_DEFAULT: OLChikiConverter | None = None
_LATIC_DEFAULT: OLChikiLaticConverter | None = None


def convert_olchiki(
    text: str, *, apply_uncertain: bool = False, strict: bool = False
) -> OLChikiConversion:
    """Convert 'Ol Chiki Optimum' legacy font text to Unicode Ol Chiki (NFC).

    Returns an :class:`OLChikiConversion`. No OLCKOptimum bytes are currently
    uncertain; bytes that are neither confirmed letters/marks, digits, nor known
    passthrough punctuation are surfaced in ``unmapped_bytes``. With ``strict=True``
    the presence of any uncertain or unmapped byte raises ``ValueError`` instead of
    passing silently.
    """
    require_boolean(apply_uncertain, "Ol Chiki apply_uncertain")
    require_boolean(strict, "strict")
    require_text(text)
    global _DEFAULT
    if _DEFAULT is None or apply_uncertain:
        converter = OLChikiConverter.default(apply_uncertain=apply_uncertain)
        if not apply_uncertain:
            _DEFAULT = converter
    else:
        converter = _DEFAULT
    result = converter.convert(text)
    if strict and (result.uncertain_bytes or result.unmapped_bytes):
        flagged = result.uncertain_bytes + result.unmapped_bytes
        raise ValueError(
            "unmapped/uncertain bytes after Ol Chiki conversion: "
            + " ".join(codepoint_labels(flagged))
        )
    return result


def convert_olchiki_latic(
    text: str, *, apply_uncertain: bool = False, strict: bool = False
) -> OLChikiConversion:
    """Convert an OLCKLatic legacy span to Unicode Ol Chiki (NFC)."""
    require_boolean(apply_uncertain, "Ol Chiki apply_uncertain")
    require_boolean(strict, "strict")
    require_text(text)
    global _LATIC_DEFAULT
    if _LATIC_DEFAULT is None or apply_uncertain:
        converter = OLChikiLaticConverter.default(apply_uncertain=apply_uncertain)
        if not apply_uncertain:
            _LATIC_DEFAULT = converter
    else:
        converter = _LATIC_DEFAULT
    result = converter.convert(text)
    if strict and (result.uncertain_bytes or result.unmapped_bytes):
        flagged = result.uncertain_bytes + result.unmapped_bytes
        raise ValueError(
            "unmapped/uncertain bytes after Ol Chiki Latic conversion: "
            + " ".join(codepoint_labels(flagged))
        )
    return result
