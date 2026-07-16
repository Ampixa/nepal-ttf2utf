"""Project Janaki/Devanagari crosswalk -> Unicode Tirhuta.

Audited Videha Janaki spans draw Tirhuta/Mithilakshar glyphs while storing
semantically corresponding characters in the Devanagari block. PDF extraction
can additionally expose two visual-order artifacts: U+093F before its consonant
and a trailing RA+VIRAMA after the consonant that carries the reph. The fixed
project crosswalk remaps the supported shared Indic repertoire and applies those
repairs only to Devanagari-derived output, never to pre-existing Unicode Tirhuta.

This is not a published or universal Janaki encoding table. Devanagari
characters without a direct Tirhuta equivalent, including independent SHORT E
and SHORT O, replacement characters from broken PDF ToUnicode maps, and
non-script text are preserved and reported rather than approximated. The
evidence and corpus boundary are documented in ``docs/EVIDENCE.md``.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ._controls import require_boolean, require_text
from .unicode_span import _is_assigned_script_codepoint

TIRHUTA_LO, TIRHUTA_HI = 0x11480, 0x114DF

_TIRHUTA_CONSONANTS = frozenset(range(0x1148F, 0x114B0))
_TIRHUTA_PREBASE_I = 0x114B1
_TIRHUTA_RA = 0x114A9
_TIRHUTA_VIRAMA = 0x114C2
_TIRHUTA_NUKTA = 0x114C3
_TIRHUTA_DEPENDENTS = frozenset(range(0x114B0, 0x114C2)) | {_TIRHUTA_NUKTA}
_TIRHUTA_REORDER_PROVENANCE = "devanagari-derived-only"
_TIRHUTA_MAPPING_SHA256 = "0a740647420fdddac4221bfedfa50b46082f1a6f640a172df3f4bc4e94ebb12a"
_TIRHUTA_PASSTHROUGH_SHA256 = "d6422caf7cf326bcd10a5c318e07e4dbf4b5e7ae55120785c7e6f2ddf141a7c4"

_PASSTHROUGH = frozenset(" \t\r\n0123456789,.;:!?()[]{}<>/\\'\"-–—+_=%&@#|~\u00a0‘’“”")

_TIRHUTA_SOURCE_INVENTORY = frozenset(
    {
        0x0901,
        0x0902,
        0x0903,
        0x0905,
        0x0906,
        0x0907,
        0x0908,
        0x0909,
        0x090A,
        0x090B,
        0x090C,
        0x090F,
        0x0910,
        0x0913,
        0x0914,
        0x0932,
        0x0933,
        0x0935,
        0x0936,
        0x0937,
        0x0938,
        0x0939,
        0x093C,
        0x093D,
        0x093E,
        0x093F,
        0x0940,
        0x0941,
        0x0942,
        0x0943,
        0x0944,
        0x0946,
        0x0947,
        0x0948,
        0x094A,
        0x094B,
        0x094C,
        0x094D,
        0x0950,
        0x0960,
        0x0961,
        0x0962,
        0x0963,
        0x0964,
        0x0965,
    }
)
_TIRHUTA_SOURCE_INVENTORY |= frozenset(range(0x0915, 0x0929))
_TIRHUTA_SOURCE_INVENTORY |= frozenset(range(0x092A, 0x0931))
_TIRHUTA_SOURCE_INVENTORY |= frozenset(range(0x0958, 0x0960))
_TIRHUTA_SOURCE_INVENTORY |= frozenset(range(0x0966, 0x0970))


def _compact_json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _build_map() -> dict[int, tuple[int, ...]]:
    table: dict[int, tuple[int, ...]] = {
        # Independent vowels.
        0x0905: (0x11481,),
        0x0906: (0x11482,),
        0x0907: (0x11483,),
        0x0908: (0x11484,),
        0x0909: (0x11485,),
        0x090A: (0x11486,),
        0x090B: (0x11487,),
        0x0960: (0x11488,),
        0x090C: (0x11489,),
        0x0961: (0x1148A,),
        0x090F: (0x1148B,),
        0x0910: (0x1148C,),
        0x0913: (0x1148D,),
        0x0914: (0x1148E,),
        # U+090E/U+0912 deliberately have no entries. Unicode specifies that
        # Tirhuta SHORT E/O have dependent signs but no independent forms.
        # Signs and dependent vowels.
        0x0901: (0x114BF,),
        0x0902: (0x114C0,),
        0x0903: (0x114C1,),
        0x093E: (0x114B0,),
        0x093F: (0x114B1,),
        0x0940: (0x114B2,),
        0x0941: (0x114B3,),
        0x0942: (0x114B4,),
        0x0943: (0x114B5,),
        0x0944: (0x114B6,),
        0x0962: (0x114B7,),
        0x0963: (0x114B8,),
        0x0947: (0x114B9,),
        0x0946: (0x114BA,),
        0x0948: (0x114BB,),
        0x094B: (0x114BC,),
        0x094A: (0x114BD,),
        0x094C: (0x114BE,),
        0x094D: (0x114C2,),
        0x093C: (0x114C3,),
        0x093D: (0x114C4,),
        0x0950: (0x114C7,),
        # Tirhuta uses the shared Indic danda characters.
        0x0964: (0x0964,),
        0x0965: (0x0965,),
    }

    # The core consonant rows are aligned, with Devanagari's script-specific
    # letters skipped where Tirhuta has no distinct encoded counterpart.
    for source, target in zip(range(0x0915, 0x0929), range(0x1148F, 0x114A3)):
        table[source] = (target,)
    for source, target in zip(range(0x092A, 0x0931), range(0x114A3, 0x114AA)):
        table[source] = (target,)
    table[0x0932] = (0x114AA,)
    for source, target in zip(range(0x0935, 0x093A), range(0x114AB, 0x114B0)):
        table[source] = (target,)

    # Devanagari LLA and the precomposed nukta consonants have decomposed
    # Tirhuta spellings.
    # Devanagari LLA: Pandey L2/11-175R section 4.12 attests /l./ as LA+NUKTA.
    table[0x0933] = (0x114AA, 0x114C3)
    nukta_bases = (0x1148F, 0x11490, 0x11491, 0x11496, 0x1149B, 0x1149C, 0x114A4, 0x114A8)
    for source, base in zip(range(0x0958, 0x0960), nukta_bases):
        table[source] = (base, 0x114C3)

    for source, target in zip(range(0x0966, 0x0970), range(0x114D0, 0x114DA)):
        table[source] = (target,)
    return table


@dataclass(frozen=True)
class _TirhutaContract:
    mapping: Mapping[int, tuple[int, ...]]
    passthrough: frozenset[str]
    consonants: frozenset[int]
    dependents: frozenset[int]
    prebase_i: int
    ra: int
    virama: int
    nukta: int
    block_lo: int
    block_hi: int
    provenance: str


def _freeze_tirhuta_contract(
    mapping: Mapping[int, tuple[int, ...]],
    *,
    passthrough: frozenset[str],
    consonants: frozenset[int],
    dependents: frozenset[int],
    prebase_i: int,
    ra: int,
    virama: int,
    nukta: int,
    block_lo: int,
    block_hi: int,
    provenance: str,
) -> _TirhutaContract:
    """Validate and freeze the fixed project crosswalk and reorder state."""
    if not isinstance(mapping, Mapping) or len(mapping) != 90:
        raise ValueError("Tirhuta mapping must contain exactly 90 entries")
    if set(mapping) != _TIRHUTA_SOURCE_INVENTORY:
        raise ValueError("invalid Tirhuta source inventory")

    snapshot: dict[int, tuple[int, ...]] = {}
    for source, target in mapping.items():
        if type(source) is not int or not _is_assigned_script_codepoint(source, "Devanagari"):
            raise ValueError(f"invalid Tirhuta mapping source: {source!r}")
        if type(target) is not tuple or not (1 <= len(target) <= 2):
            raise ValueError(f"invalid Tirhuta mapping target for U+{source:04X}: {target!r}")
        for codepoint in target:
            if (
                type(codepoint) is not int
                or not (0 <= codepoint <= 0x10FFFF)
                or 0xD800 <= codepoint <= 0xDFFF
                or (
                    codepoint not in {0x0964, 0x0965}
                    and not _is_assigned_script_codepoint(codepoint, "Tirhuta")
                )
            ):
                raise ValueError(f"invalid Tirhuta mapping target for U+{source:04X}: {target!r}")
        if unicodedata.normalize("NFC", "".join(chr(value) for value in target)) != "".join(
            chr(value) for value in target
        ):
            raise ValueError(f"non-NFC Tirhuta mapping target for U+{source:04X}")
        snapshot[source] = target

    target_lengths = [len(target) for target in snapshot.values()]
    if target_lengths.count(1) != 81 or target_lengths.count(2) != 9:
        raise ValueError("invalid Tirhuta mapping target-length inventory")
    if sum(target_lengths) != 99 or len(set(snapshot.values())) != 90:
        raise ValueError("Tirhuta mapping targets must contain 90 unique sequences")
    if len({codepoint for target in snapshot.values() for codepoint in target}) != 81:
        raise ValueError("invalid Tirhuta mapping target-codepoint inventory")
    mapping_rows = [
        [source, list(snapshot[source])] for source in sorted(_TIRHUTA_SOURCE_INVENTORY)
    ]
    if _compact_json_sha256(mapping_rows) != _TIRHUTA_MAPPING_SHA256:
        raise ValueError("invalid Tirhuta mapping payload")

    if type(passthrough) is not frozenset or len(passthrough) != 49:
        raise ValueError("Tirhuta passthrough must contain exactly 49 values")
    if any(type(value) is not str or len(value) != 1 for value in passthrough):
        raise ValueError("invalid Tirhuta passthrough value")
    if set(snapshot) & {ord(value) for value in passthrough}:
        raise ValueError("Tirhuta mapping and passthrough sources overlap")
    if (
        _compact_json_sha256(sorted(ord(value) for value in passthrough))
        != _TIRHUTA_PASSTHROUGH_SHA256
    ):
        raise ValueError("invalid Tirhuta passthrough payload")

    expected_consonants = frozenset(range(0x1148F, 0x114B0))
    expected_dependents = frozenset(range(0x114B0, 0x114C2)) | {0x114C3}
    if type(consonants) is not frozenset or consonants != expected_consonants:
        raise ValueError("invalid Tirhuta consonant inventory")
    if type(dependents) is not frozenset or dependents != expected_dependents:
        raise ValueError("invalid Tirhuta dependent inventory")
    if (prebase_i, ra, virama, nukta) != (0x114B1, 0x114A9, 0x114C2, 0x114C3):
        raise ValueError("invalid Tirhuta reorder scalar")
    if any(type(value) is not int for value in (prebase_i, ra, virama, nukta)):
        raise ValueError("invalid Tirhuta reorder scalar type")
    if (block_lo, block_hi) != (0x11480, 0x114DF) or any(
        type(value) is not int for value in (block_lo, block_hi)
    ):
        raise ValueError("invalid Tirhuta block bounds")
    if type(provenance) is not str or provenance != "devanagari-derived-only":
        raise ValueError("invalid Tirhuta reorder provenance")

    return _TirhutaContract(
        mapping=MappingProxyType(snapshot),
        passthrough=passthrough,
        consonants=consonants,
        dependents=dependents,
        prebase_i=prebase_i,
        ra=ra,
        virama=virama,
        nukta=nukta,
        block_lo=block_lo,
        block_hi=block_hi,
        provenance=provenance,
    )


_initial_mapping = _build_map()
_DEFAULT_CONTRACT = _freeze_tirhuta_contract(
    _initial_mapping,
    passthrough=_PASSTHROUGH,
    consonants=_TIRHUTA_CONSONANTS,
    dependents=_TIRHUTA_DEPENDENTS,
    prebase_i=_TIRHUTA_PREBASE_I,
    ra=_TIRHUTA_RA,
    virama=_TIRHUTA_VIRAMA,
    nukta=_TIRHUTA_NUKTA,
    block_lo=TIRHUTA_LO,
    block_hi=TIRHUTA_HI,
    provenance=_TIRHUTA_REORDER_PROVENANCE,
)
_DEVANAGARI_TO_TIRHUTA: Mapping[int, tuple[int, ...]] = _DEFAULT_CONTRACT.mapping
del _initial_mapping


@dataclass(frozen=True)
class TirhutaConversion:
    legacy_text: str
    unicode_text: str
    tirhuta_char_count: int
    replacement_count: int
    prebase_i_moves: int
    reph_moves: int
    unmapped_codepoints: list[str]


def _move_prebase_i(
    chars: list[int], derived: list[bool], contract: _TirhutaContract
) -> tuple[list[int], list[bool], int]:
    """Repair mapped Janaki pre-base I without consuming native Tirhuta."""
    output: list[int] = []
    output_derived: list[bool] = []
    moves = 0
    index = 0
    while index < len(chars):
        if (
            derived[index]
            and chars[index] == contract.prebase_i
            and index + 1 < len(chars)
            and derived[index + 1]
            and chars[index + 1] in contract.consonants
            # This project rule is limited to an audited Janaki extraction
            # pattern at a text/run or word boundary.
            and (index == 0 or not (contract.block_lo <= chars[index - 1] <= contract.block_hi))
        ):
            end = index + 2
            blocked = False
            if end < len(chars) and chars[end] == contract.nukta:
                if not derived[end]:
                    blocked = True
                else:
                    end += 1
            while not blocked and end < len(chars) and chars[end] == contract.virama:
                if not derived[end]:
                    blocked = True
                    break
                if end + 1 >= len(chars) or chars[end + 1] not in contract.consonants:
                    break
                if not derived[end + 1]:
                    blocked = True
                    break
                end += 2
                if end < len(chars) and chars[end] == contract.nukta:
                    if not derived[end]:
                        blocked = True
                        break
                    end += 1
            if not blocked:
                output.extend(chars[index + 1 : end])
                output_derived.extend(derived[index + 1 : end])
                output.append(contract.prebase_i)
                output_derived.append(True)
                moves += 1
                index = end
                continue
        output.append(chars[index])
        output_derived.append(derived[index])
        index += 1
    return output, output_derived, moves


def _move_trailing_reph(
    chars: list[int], derived: list[bool], contract: _TirhutaContract
) -> tuple[list[int], list[bool], int]:
    """Repair mapped Janaki trailing reph without consuming native Tirhuta."""
    output: list[int] = []
    output_derived: list[bool] = []
    moves = 0
    index = 0
    while index < len(chars):
        current = chars[index]
        if derived[index] and current in contract.consonants:
            end = index + 1
            while end < len(chars) and derived[end] and chars[end] in contract.dependents:
                end += 1
            if (
                end + 1 < len(chars)
                and derived[end]
                and chars[end] == contract.ra
                and derived[end + 1]
                and chars[end + 1] == contract.virama
                # This project rule is limited to an audited trailing Janaki
                # extraction pattern at a text/run or word boundary.
                and (
                    end + 2 == len(chars)
                    or not (contract.block_lo <= chars[end + 2] <= contract.block_hi)
                )
            ):
                output.extend((contract.ra, contract.virama))
                output_derived.extend((True, True))
                output.extend(chars[index:end])
                output_derived.extend(derived[index:end])
                moves += 1
                index = end + 2
                continue
        output.append(current)
        output_derived.append(derived[index])
        index += 1
    return output, output_derived, moves


class TirhutaConverter:
    """Convert the frozen Janaki/Devanagari project contract to Unicode Tirhuta."""

    def __init__(self) -> None:
        self._contract = _DEFAULT_CONTRACT

    def convert(self, text: str) -> TirhutaConversion:
        require_text(text)
        mapped: list[int] = []
        derived: list[bool] = []
        unmapped: set[str] = set()
        replacements = 0
        for char in text:
            codepoint = ord(char)
            target = self._contract.mapping.get(codepoint)
            if target is not None:
                mapped.extend(target)
                derived.extend([True] * len(target))
                replacements += 1
                continue
            mapped.append(codepoint)
            derived.append(False)
            if (
                _is_assigned_script_codepoint(codepoint, "Tirhuta")
                or char in self._contract.passthrough
            ):
                continue
            unmapped.add(f"U+{codepoint:04X}")

        mapped, derived, prebase_moves = _move_prebase_i(mapped, derived, self._contract)
        mapped, _derived, reph_moves = _move_trailing_reph(mapped, derived, self._contract)
        converted = unicodedata.normalize("NFC", "".join(chr(cp) for cp in mapped))
        return TirhutaConversion(
            legacy_text=text,
            unicode_text=converted,
            tirhuta_char_count=sum(
                self._contract.block_lo <= ord(ch) <= self._contract.block_hi for ch in converted
            ),
            replacement_count=replacements,
            prebase_i_moves=prebase_moves,
            reph_moves=reph_moves,
            unmapped_codepoints=sorted(unmapped),
        )


_DEFAULT = TirhutaConverter()


def convert_tirhuta(text: str, *, strict: bool = False) -> TirhutaConversion:
    """Convert Janaki-font text to Unicode Tirhuta (NFC)."""
    require_boolean(strict, "strict")
    require_text(text)
    result = _DEFAULT.convert(text)
    if strict and result.unmapped_codepoints:
        raise ValueError(
            "unmapped/leftover characters after Tirhuta conversion: "
            + " ".join(result.unmapped_codepoints)
        )
    return result
