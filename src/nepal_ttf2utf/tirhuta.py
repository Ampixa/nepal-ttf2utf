"""Janaki's Devanagari-coded Tirhuta glyphs -> Unicode Tirhuta.

The Janaki font used in early Maithili publishing draws Tirhuta/Mithilakshar
glyphs while storing the corresponding characters in the Devanagari block. PDF
text extraction can additionally expose two visual-order artifacts: U+093F
before its consonant and a trailing RA+VIRAMA after the consonant that carries
the reph. This converter remaps the shared Indic repertoire and repairs those
two observed orderings.

The mapping is intentionally conservative. Devanagari characters without a
direct Tirhuta equivalent, replacement characters from broken PDF ToUnicode
maps, and non-script text are preserved and reported rather than approximated.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

TIRHUTA_LO, TIRHUTA_HI = 0x11480, 0x114DF

_TIRHUTA_CONSONANTS = frozenset(range(0x1148F, 0x114B0))
_TIRHUTA_PREBASE_I = 0x114B1
_TIRHUTA_RA = 0x114A9
_TIRHUTA_VIRAMA = 0x114C2
_TIRHUTA_NUKTA = 0x114C3
_TIRHUTA_DEPENDENTS = frozenset(range(0x114B0, 0x114C2)) | {_TIRHUTA_NUKTA}

_PASSTHROUGH = frozenset(" \t\r\n0123456789,.;:!?()[]{}<>/\\'\"-–—+_=%&@#|~\u00a0‘’“”")


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
        # Tirhuta's short E/O forms are sequences with independent A.
        0x090E: (0x11481, 0x114BA),
        0x0912: (0x11481, 0x114BD),
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
    table[0x0933] = (0x1149D, 0x114C3)
    nukta_bases = (0x1148F, 0x11490, 0x11491, 0x11496, 0x1149B, 0x1149C, 0x114A4, 0x114A8)
    for source, base in zip(range(0x0958, 0x0960), nukta_bases):
        table[source] = (base, 0x114C3)

    for source, target in zip(range(0x0966, 0x0970), range(0x114D0, 0x114DA)):
        table[source] = (target,)
    return table


_DEVANAGARI_TO_TIRHUTA = _build_map()


@dataclass(frozen=True)
class TirhutaConversion:
    legacy_text: str
    unicode_text: str
    tirhuta_char_count: int
    replacement_count: int
    prebase_i_moves: int
    reph_moves: int
    unmapped_codepoints: list[str]


def _move_prebase_i(chars: list[int]) -> tuple[list[int], int]:
    """Move a visually extracted I sign behind the following consonant cluster."""
    output: list[int] = []
    moves = 0
    index = 0
    while index < len(chars):
        if (
            chars[index] == _TIRHUTA_PREBASE_I
            and index + 1 < len(chars)
            and chars[index + 1] in _TIRHUTA_CONSONANTS
            # Logical Unicode already stores I after its base. The Janaki PDF
            # artifact is distinguishable because I appears at a text/run or
            # word boundary before the consonant.
            and (index == 0 or not (TIRHUTA_LO <= chars[index - 1] <= TIRHUTA_HI))
        ):
            end = index + 2
            if end < len(chars) and chars[end] == _TIRHUTA_NUKTA:
                end += 1
            while (
                end + 1 < len(chars)
                and chars[end] == _TIRHUTA_VIRAMA
                and chars[end + 1] in _TIRHUTA_CONSONANTS
            ):
                end += 2
                if end < len(chars) and chars[end] == _TIRHUTA_NUKTA:
                    end += 1
            output.extend(chars[index + 1 : end])
            output.append(_TIRHUTA_PREBASE_I)
            moves += 1
            index = end
            continue
        output.append(chars[index])
        index += 1
    return output, moves


def _move_trailing_reph(chars: list[int]) -> tuple[list[int], int]:
    """Move visual ``base + RA VIRAMA`` to logical ``RA VIRAMA + base``."""
    output: list[int] = []
    moves = 0
    index = 0
    while index < len(chars):
        current = chars[index]
        if current in _TIRHUTA_CONSONANTS:
            end = index + 1
            while end < len(chars) and chars[end] in _TIRHUTA_DEPENDENTS:
                end += 1
            if (
                end + 1 < len(chars)
                and chars[end] == _TIRHUTA_RA
                and chars[end + 1] == _TIRHUTA_VIRAMA
                # A logical RA+VIRAMA precedes the consonant it joins. Janaki's
                # extracted reph is the trailing form at a word/run boundary.
                and (end + 2 == len(chars) or not (TIRHUTA_LO <= chars[end + 2] <= TIRHUTA_HI))
            ):
                output.extend((_TIRHUTA_RA, _TIRHUTA_VIRAMA))
                output.extend(chars[index:end])
                moves += 1
                index = end + 2
                continue
        output.append(current)
        index += 1
    return output, moves


class TirhutaConverter:
    """Convert Janaki/Devanagari-coded text to true Unicode Tirhuta."""

    def convert(self, text: str) -> TirhutaConversion:
        mapped: list[int] = []
        unmapped: set[str] = set()
        replacements = 0
        for char in text:
            codepoint = ord(char)
            target = _DEVANAGARI_TO_TIRHUTA.get(codepoint)
            if target is not None:
                mapped.extend(target)
                replacements += 1
                continue
            mapped.append(codepoint)
            if TIRHUTA_LO <= codepoint <= TIRHUTA_HI or char in _PASSTHROUGH:
                continue
            unmapped.add(f"U+{codepoint:04X}")

        mapped, prebase_moves = _move_prebase_i(mapped)
        mapped, reph_moves = _move_trailing_reph(mapped)
        converted = unicodedata.normalize("NFC", "".join(chr(cp) for cp in mapped))
        return TirhutaConversion(
            legacy_text=text,
            unicode_text=converted,
            tirhuta_char_count=sum(TIRHUTA_LO <= ord(ch) <= TIRHUTA_HI for ch in converted),
            replacement_count=replacements,
            prebase_i_moves=prebase_moves,
            reph_moves=reph_moves,
            unmapped_codepoints=sorted(unmapped),
        )


_DEFAULT = TirhutaConverter()


def convert_tirhuta(text: str, *, strict: bool = False) -> TirhutaConversion:
    """Convert Janaki-font text to Unicode Tirhuta (NFC)."""
    result = _DEFAULT.convert(text)
    if strict and result.unmapped_codepoints:
        raise ValueError(
            "unmapped/leftover characters after Tirhuta conversion: "
            + " ".join(result.unmapped_codepoints)
        )
    return result
