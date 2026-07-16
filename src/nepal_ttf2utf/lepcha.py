"""Sikkim Herald live-text Lepcha (Róng) font -> Unicode Lepcha (U+1C00-U+1C4F).

Four 2021-2022 Sikkim Herald editions contain an anonymized CFF-subset body-font
family with one shared ASCII-keyed glyph layout. The recoverable text layer stores
Latin character codes, while the embedded glyph outlines represent Lepcha. This
layout differs from Jason Glavy's JG Lepcha encoding and requires a separate map.

The project-derived map (``maps/sikkim_herald_lepcha.json``) aligns rendered glyph
shapes with assigned Lepcha codepoints in Noto Sans Lepcha and Mingzat, anchored by
the alphabetic consonant series and checked against positional statistics and
round-trip renderings of the source material. Its evidence boundary and limitations
are documented in ``docs/EVIDENCE.md``.

Structure handled: base consonants, LA-conjuncts, the independent vowel A, pre-base
dependent vowel signs (I/O/OO, keyed to the left of their base in the legacy stream),
post-base vowel signs, final consonant signs, RAN, nukta, and digits. Fully
legacy-derived clusters are repaired to the Unicode storage order
``C (nukta) (subjoined) (vowel) (final) (ran)``. Native and mixed-provenance input
is preserved apart from whole-output NFC.

The legacy ``]`` glyph is final K stored visually before the following base; it is
reordered with the pre-base vowels. ``%`` is subjoined RA, including the documented
NUKTA+RA retroflex sequences. A small set of rare bytes remains deliberately
unresolved in the observed material and is surfaced in ``unmapped_bytes`` (or
raised in ``strict`` mode). Other bytes outside the supported inventory receive
the same diagnostic treatment.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from importlib import resources
from itertools import islice
from pathlib import Path
from types import MappingProxyType

from ._controls import require_boolean, require_text
from .unicode_span import _is_assigned_script_codepoint

LEPCHA_LO, LEPCHA_HI = 0x1C00, 0x1C4F
_LEPCHA_CODEPOINT_RE = re.compile(r"[ᰀ-ᱏ]")
_BYTE_KEY_RE = re.compile(r"[0-9A-F]{2}")
_TARGET_KEY_RE = re.compile(r"[0-9A-F]{4}")
_FORBIDDEN_SOURCE_BYTES = frozenset(range(0x21)) | {0x7F}
_MAX_MAP_ENTRIES = 256
_MAX_MAP_FILE_BYTES = 1_000_000
_MAX_MAP_JSON_DEPTH = 64
_MAX_TARGET_CODEPOINTS = 256

# Pre-base dependent vowel signs (keyed before the base in the legacy visual stream;
# Unicode stores them after the base). I / O / OO.
PRE_BASE_VOWELS = frozenset({0x1C27, 0x1C28, 0x1C29})
VISUAL_LEADING_FINALS = frozenset({0x1C2D})  # final K, legacy byte 0x5D
LEPCHA_PASSTHROUGH = frozenset("-")

# Codepoint classes for canonical ordering within a cluster.
_SUBJOINED = frozenset({0x1C24, 0x1C25})  # subjoined YA, RA
_VOWEL_SIGNS = frozenset(range(0x1C26, 0x1C2D))  # AA, I, O, OO, U, UU, E
_FINAL_SIGNS = frozenset(range(0x1C2D, 0x1C36))  # K, M, L, N, P, R, T, NYIN-DO, KANG
_RAN = 0x1C36
_NUKTA = 0x1C37
_DEPENDENT_SIGNS = _SUBJOINED | _VOWEL_SIGNS | _FINAL_SIGNS | {_RAN, _NUKTA}
_BASES = frozenset(
    list(range(0x1C00, 0x1C24)) + [0x1C4D, 0x1C4E, 0x1C4F]
)  # consonants + independent vowel A + TTA/TTHA/DDA
_CLUSTER_BOUNDARIES = frozenset(range(0x1C3B, 0x1C4A))  # punctuation and digits


@dataclass(frozen=True)
class LepchaConversion:
    legacy_text: str
    unicode_text: str
    lepcha_char_count: int
    replacement_count: int
    unmapped_bytes: list[str]


@dataclass(frozen=True)
class _LepchaReorderContract:
    bases: frozenset[int]
    dependent_signs: frozenset[int]
    pre_base_vowels: frozenset[int]
    visual_leading_finals: frozenset[int]
    subjoined: frozenset[int]
    vowel_signs: frozenset[int]
    final_signs: frozenset[int]
    ran: int
    nukta: int
    cluster_boundaries: frozenset[int]
    provenance: str


_DEFAULT_REORDER_CONTRACT = _LepchaReorderContract(
    bases=_BASES,
    dependent_signs=_DEPENDENT_SIGNS,
    pre_base_vowels=PRE_BASE_VOWELS,
    visual_leading_finals=VISUAL_LEADING_FINALS,
    subjoined=_SUBJOINED,
    vowel_signs=_VOWEL_SIGNS,
    final_signs=_FINAL_SIGNS,
    ran=_RAN,
    nukta=_NUKTA,
    cluster_boundaries=_CLUSTER_BOUNDARIES,
    provenance="legacy-byte-derived-only",
)


@dataclass(frozen=True)
class _LepchaContract:
    byte_map: Mapping[int, tuple[int, ...]]
    passthrough: frozenset[str]
    reorder: _LepchaReorderContract


def _validate_source_byte(source: object) -> int:
    if isinstance(source, bool) or not isinstance(source, int) or not (0 <= source <= 0xFF):
        raise ValueError(f"invalid Lepcha source byte: {source!r}")
    if source in _FORBIDDEN_SOURCE_BYTES:
        raise ValueError(f"Lepcha source byte must not be C0, SPACE, or DEL: 0x{source:02X}")
    if chr(source) in LEPCHA_PASSTHROUGH:
        raise ValueError(f"Lepcha source byte is a fixed passthrough: 0x{source:02X}")
    return source


def _validate_target_codepoint(codepoint: object, source: int) -> int:
    if (
        isinstance(codepoint, bool)
        or not isinstance(codepoint, int)
        or not _is_assigned_script_codepoint(codepoint, "Lepcha")
    ):
        raise ValueError(
            f"invalid or unassigned Lepcha target {codepoint!r} for source 0x{source:02X}"
        )
    return codepoint


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key in Lepcha map: {key!r}")
        result[key] = value
    return result


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
                    f"Lepcha legacy map exceeds {_MAX_MAP_JSON_DEPTH} JSON nesting levels: "
                    f"{map_path}"
                )
        elif character in "]}":
            depth = max(0, depth - 1)


def _bounded_map_items(byte_map: Mapping[object, object]) -> tuple[object, ...]:
    try:
        map_items = tuple(islice(iter(byte_map.items()), _MAX_MAP_ENTRIES + 1))
    except (TypeError, ValueError) as error:
        raise ValueError("invalid Lepcha source map item sequence") from error
    if not map_items:
        raise ValueError("LepchaConverter requires a non-empty map")
    if len(map_items) > _MAX_MAP_ENTRIES:
        raise ValueError(f"Lepcha source map exceeds {_MAX_MAP_ENTRIES} entries")
    return map_items


class LepchaConverter:
    """Byte->Unicode converter for the Sikkim Herald live-text Lepcha body font.

    ``byte_map`` maps a single legacy byte value (the Latin code) to a nonempty ordered
    iterable of at most 256 assigned Lepcha codepoints. Conversion is a single byte pass
    (no multi-byte rules in this font) followed by a per-cluster reorder that (a) moves
    pre-base vowel signs after the base and (b) sorts the dependent signs into canonical
    Lepcha storage order.
    """

    def __init__(self, byte_map: Mapping[int, Iterable[int]]) -> None:
        if not isinstance(byte_map, Mapping):
            raise ValueError("LepchaConverter requires a non-empty map")
        map_items = _bounded_map_items(byte_map)
        normalized: dict[int, tuple[int, ...]] = {}
        for raw_item in map_items:
            if isinstance(raw_item, (str, bytes, Mapping, Set)):
                raise ValueError(f"invalid Lepcha source map entry: {raw_item!r}")
            try:
                raw_source, raw_target = raw_item  # type: ignore[misc]
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid Lepcha source map entry: {raw_item!r}") from error
            source = _validate_source_byte(raw_source)
            if source in normalized:
                raise ValueError(f"duplicate Lepcha source byte: 0x{source:02X}")
            if isinstance(raw_target, (str, bytes, Mapping, Set)):
                raise ValueError(f"invalid Lepcha target sequence for source 0x{source:02X}")
            try:
                target = tuple(islice(iter(raw_target), _MAX_TARGET_CODEPOINTS + 1))
            except TypeError as error:
                raise ValueError(
                    f"invalid Lepcha target sequence for source 0x{source:02X}"
                ) from error
            if not target:
                raise ValueError(f"empty Lepcha target sequence for source 0x{source:02X}")
            if len(target) > _MAX_TARGET_CODEPOINTS:
                raise ValueError(
                    f"Lepcha target sequence for source 0x{source:02X} exceeds "
                    f"{_MAX_TARGET_CODEPOINTS} codepoints"
                )
            normalized[source] = tuple(
                _validate_target_codepoint(codepoint, source) for codepoint in target
            )
        self._contract = _LepchaContract(
            byte_map=MappingProxyType(dict(normalized)),
            passthrough=LEPCHA_PASSTHROUGH,
            reorder=_DEFAULT_REORDER_CONTRACT,
        )

    @property
    def _byte_map(self) -> Mapping[int, tuple[int, ...]]:
        return self._contract.byte_map

    @classmethod
    def from_map_file(cls, path: str | Path) -> "LepchaConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"Lepcha legacy map does not exist: {map_path}")
        with map_path.open("rb") as map_file:
            map_bytes = map_file.read(_MAX_MAP_FILE_BYTES + 1)
        if len(map_bytes) > _MAX_MAP_FILE_BYTES:
            raise ValueError(f"Lepcha legacy map exceeds {_MAX_MAP_FILE_BYTES} bytes: {map_path}")
        try:
            map_text = map_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"invalid UTF-8 in Lepcha legacy map {map_path}") from error
        _reject_excessive_json_depth(map_text, map_path)
        try:
            raw = json.loads(map_text, object_pairs_hook=_unique_json_object)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"invalid JSON in Lepcha legacy map {map_path}: {error.msg}"
            ) from error
        except RecursionError as error:
            raise ValueError(f"invalid nested JSON in Lepcha legacy map {map_path}") from error
        if not isinstance(raw, dict):
            raise ValueError(f"Lepcha legacy map root must be an object: {map_path}")
        unexpected_fields = set(raw) - {"_doc", "_confidence", "_unresolved_bytes", "map"}
        if unexpected_fields:
            fields = ", ".join(repr(field) for field in sorted(unexpected_fields))
            raise ValueError(f"unexpected Lepcha legacy map field(s) {fields}: {map_path}")
        for metadata_name in ("_doc", "_confidence"):
            if metadata_name in raw and not isinstance(raw[metadata_name], str):
                raise ValueError(
                    f"Lepcha legacy map {metadata_name!r} metadata must be a string: {map_path}"
                )
        entries = raw.get("map")
        if not isinstance(entries, dict):
            raise ValueError(f"Lepcha legacy map missing 'map' object: {map_path}")
        byte_map: dict[int, tuple[int, ...]] = {}
        for byte_hex, target in entries.items():
            if _BYTE_KEY_RE.fullmatch(byte_hex) is None:
                raise ValueError(
                    f"invalid Lepcha byte key {byte_hex!r}; expected two uppercase hex digits"
                )
            source = _validate_source_byte(int(byte_hex, 16))
            if not isinstance(target, list) or not target:
                raise ValueError(f"Lepcha map target for byte {byte_hex} must be a non-empty list")
            if len(target) > _MAX_TARGET_CODEPOINTS:
                raise ValueError(
                    f"Lepcha map target for byte {byte_hex} exceeds "
                    f"{_MAX_TARGET_CODEPOINTS} codepoints"
                )
            target_codepoints: list[int] = []
            for value in target:
                if not isinstance(value, str) or _TARGET_KEY_RE.fullmatch(value) is None:
                    raise ValueError(
                        f"invalid Lepcha target {value!r} for byte {byte_hex}; "
                        "expected four uppercase hex digits"
                    )
                target_codepoints.append(_validate_target_codepoint(int(value, 16), source))
            byte_map[source] = tuple(target_codepoints)

        unresolved_raw = raw.get("_unresolved_bytes", [])
        if not isinstance(unresolved_raw, list):
            raise ValueError(f"Lepcha map '_unresolved_bytes' must be a list: {map_path}")
        unresolved: set[int] = set()
        for byte_hex in unresolved_raw:
            if not isinstance(byte_hex, str) or _BYTE_KEY_RE.fullmatch(byte_hex) is None:
                raise ValueError(
                    f"invalid unresolved Lepcha byte {byte_hex!r}; "
                    "expected two uppercase hex digits"
                )
            source = _validate_source_byte(int(byte_hex, 16))
            if source in unresolved:
                raise ValueError(f"duplicate unresolved Lepcha byte: {byte_hex}")
            if source in byte_map:
                raise ValueError(f"mapped Lepcha byte is also marked unresolved: {byte_hex}")
            unresolved.add(source)
        return cls(byte_map)

    @classmethod
    def default(cls) -> "LepchaConverter":
        with resources.as_file(
            resources.files("nepal_ttf2utf.maps") / "sikkim_herald_lepcha.json"
        ) as p:
            return cls.from_map_file(p)

    # ----- byte pass -----------------------------------------------------------

    def _byte_pass_with_provenance(self, text: str) -> tuple[str, tuple[bool, ...], int, list[str]]:
        """Map input and mark every scalar emitted by a legacy rule."""
        out: list[str] = []
        derived: list[bool] = []
        unmapped: list[str] = []
        replacements = 0
        for ch in text:
            code = ord(ch)
            if ch in " \t\r\n":
                out.append(ch)
                derived.append(False)
                continue
            target = self._byte_map.get(code)
            if target is not None:
                out.extend(chr(codepoint) for codepoint in target)
                derived.extend([True] * len(target))
                replacements += 1
            elif _is_assigned_script_codepoint(code, "Lepcha"):
                out.append(ch)
                derived.append(False)
            elif ch in self._contract.passthrough:
                out.append(ch)
                derived.append(False)
            else:
                # Unmapped legacy byte (layout/punctuation glyph not in the map).
                out.append(ch)
                derived.append(False)
                unmapped.append(f"0x{code:02X}" if code <= 0xFF else f"U+{code:04X}")
        return "".join(out), tuple(derived), replacements, unmapped

    def _byte_pass(self, text: str) -> tuple[list[int | str], int, list[str]]:
        """Return the original int/string token view for private compatibility."""
        mapped, derived, replacements, unmapped = self._byte_pass_with_provenance(text)
        tokens = [ord(char) if is_derived else char for char, is_derived in zip(mapped, derived)]
        return tokens, replacements, unmapped

    # ----- reorder pass --------------------------------------------------------

    @staticmethod
    def _canonical_cluster(
        base: int, signs: list[int], contract: _LepchaReorderContract
    ) -> list[int]:
        """Order a base + its dependent signs into canonical Lepcha storage order.

        Order per The Unicode Standard ch.13 Table 13-9: base, nukta,
        subjoined (RA before YA), vowel sign, final consonant sign, RAN.
        """
        subjoined = [s for s in signs if s in contract.subjoined]
        nukta = [s for s in signs if s == contract.nukta]
        vowels = [s for s in signs if s in contract.vowel_signs]
        finals = [s for s in signs if s in contract.final_signs]
        ran = [s for s in signs if s == contract.ran]
        other = [
            s
            for s in signs
            if s not in contract.subjoined
            and s != contract.nukta
            and s not in contract.vowel_signs
            and s not in contract.final_signs
            and s != contract.ran
        ]
        # Table 13-9 medial order is RA then YA (RA=1C25, YA=1C24), i.e.
        # descending codepoint order for the two subjoined marks.
        subjoined.sort(reverse=True)
        return [base] + nukta + subjoined + vowels + finals + ran + other

    @classmethod
    def _reorder_derived_run(
        cls, codepoints: list[int], contract: _LepchaReorderContract
    ) -> list[int]:
        """Reorder one all-derived run that contains no cluster boundary.

        A syllable begins with optional visually leading signs: I/O/OO and final K,
        all keyed left of the base in the legacy stream. Each syllable is emitted in
        canonical storage order. A trailing sign-run stops at the next visually
        leading sign, which begins the next syllable.
        """
        out: list[int] = []
        i = 0
        n = len(codepoints)
        while i < n:
            # Collect visually leading vowel/final signs for the upcoming base.
            pre: list[int] = []
            while (
                i < n
                and (
                    codepoints[i] in contract.pre_base_vowels
                    or codepoints[i] in contract.visual_leading_finals
                )
                and codepoints[i] not in contract.bases
            ):
                pre.append(codepoints[i])
                i += 1

            if i >= n:
                # No base follows the pre-vowel(s); emit them verbatim (degenerate).
                out.extend(pre)
                continue

            cur = codepoints[i]
            if cur not in contract.bases:
                # A stray dependent sign with no base (and not a pre-vowel).
                out.extend(pre)
                out.append(cur)
                i += 1
                continue

            base = cur
            i += 1
            # Trailing dependent signs, stopping at the next base or visually
            # leading sign (which starts a new syllable).
            post: list[int] = []
            while (
                i < n
                and codepoints[i] in contract.dependent_signs
                and codepoints[i] not in contract.pre_base_vowels
                and codepoints[i] not in contract.visual_leading_finals
            ):
                post.append(codepoints[i])
                i += 1
            out.extend(cls._canonical_cluster(base, pre + post, contract))
        return out

    def _reorder_pass(self, text: str, derived: tuple[bool, ...] | None = None) -> str:
        """Apply the Herald visual-order repair only to legacy-derived runs."""
        if derived is None:
            derived = (True,) * len(text)
        if (
            type(derived) is not tuple
            or len(derived) != len(text)
            or any(type(value) is not bool for value in derived)
        ):
            raise ValueError("invalid Lepcha reorder provenance")

        contract = self._contract.reorder
        output: list[str] = []
        run: list[int] = []
        for char, is_derived in zip(text, derived):
            codepoint = ord(char)
            if not is_derived or codepoint in contract.cluster_boundaries:
                output.extend(chr(value) for value in self._reorder_derived_run(run, contract))
                run.clear()
                output.append(char)
            else:
                run.append(codepoint)
        output.extend(chr(value) for value in self._reorder_derived_run(run, contract))
        return "".join(output)

    # ----- public --------------------------------------------------------------

    def convert(self, text: str) -> LepchaConversion:
        require_text(text)
        mapped, derived, replacements, unmapped = self._byte_pass_with_provenance(text)
        converted = unicodedata.normalize("NFC", self._reorder_pass(mapped, derived))
        return LepchaConversion(
            legacy_text=text,
            unicode_text=converted,
            lepcha_char_count=len(_LEPCHA_CODEPOINT_RE.findall(converted)),
            replacement_count=replacements,
            unmapped_bytes=sorted(set(unmapped)),
        )


_DEFAULT: LepchaConverter | None = None


def convert_lepcha(text: str, *, strict: bool = False) -> LepchaConversion:
    """Convert Sikkim Herald live-text Lepcha to Unicode Lepcha (NFC).

    Returns a :class:`LepchaConversion`. Bytes outside the derived map, including the
    documented observed unresolved values, and Unicode values outside the pinned
    assigned Lepcha repertoire pass through and are surfaced in ``unmapped_bytes``.
    With ``strict=True`` any such leftover raises ``ValueError`` instead of passing
    silently.
    """
    require_boolean(strict, "strict")
    require_text(text)
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = LepchaConverter.default()
    result = _DEFAULT.convert(text)
    if strict and result.unmapped_bytes:
        raise ValueError(
            "unmapped/leftover bytes after Lepcha conversion: " + " ".join(result.unmapped_bytes)
        )
    return result
