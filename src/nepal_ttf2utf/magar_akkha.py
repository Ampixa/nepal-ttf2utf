"""Project Magar Akkha representation using Unicode Brahmi.

An individual contribution submitted for WG2 and UTC consideration recommends
treating Magar Akkha as a Brahmi variant unless evidence establishes distinct
encoded characters or behavior. The contribution is not a standardized Magar
Akkha encoding. This module provides an explicit project transliteration from
Unicode Devanagari to semantically corresponding Unicode Brahmi characters; it
is not a mapping for an unknown legacy Akkha font.

The functional mapping is derived from Ampixa's MIT-licensed magar-toolkit and
corrected against the Unicode 17 character identities. Default conversion
preserves every supported distinction. The optional project-defined
minimal-inventory fold is explicit and lossy.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from ._controls import require_boolean
from .unicode_span import _is_assigned_script_codepoint


def _build_map() -> dict[str, str]:
    table = {
        "ँ": "𑀀",
        "ं": "𑀁",
        "ः": "𑀂",
        "अ": "𑀅",
        "आ": "𑀆",
        "इ": "𑀇",
        "ई": "𑀈",
        "उ": "𑀉",
        "ऊ": "𑀊",
        "ए": "𑀏",
        "ऐ": "𑀐",
        "ओ": "𑀑",
        "औ": "𑀒",
        "ा": "\U00011038",  # BRAHMI VOWEL SIGN AA
        "ि": "\U0001103a",  # BRAHMI VOWEL SIGN I
        "ी": "\U0001103b",  # BRAHMI VOWEL SIGN II
        "ु": "\U0001103c",  # BRAHMI VOWEL SIGN U
        "ू": "\U0001103d",  # BRAHMI VOWEL SIGN UU
        "े": "\U00011042",  # BRAHMI VOWEL SIGN E
        "ै": "\U00011043",  # BRAHMI VOWEL SIGN AI
        "ो": "\U00011044",  # BRAHMI VOWEL SIGN O
        "ौ": "\U00011045",  # BRAHMI VOWEL SIGN AU
        "्": "𑁆",
        "।": "𑁇",
        "॥": "𑁈",
    }
    for source, target in zip(range(0x0915, 0x0929), range(0x11013, 0x11027)):
        table[chr(source)] = chr(target)
    for source, target in zip(range(0x092A, 0x0931), range(0x11027, 0x1102E)):
        table[chr(source)] = chr(target)
    table.update(
        {
            "ल": "𑀮",
            "व": "𑀯",
            "श": "𑀰",
            "ष": "𑀱",
            "स": "𑀲",
            "ह": "𑀳",
            "ळ": "𑀴",
        }
    )
    for source, target in zip(range(0x0966, 0x0970), range(0x11066, 0x11070)):
        table[chr(source)] = chr(target)
    return table


def _build_fold_map() -> dict[str, str]:
    return {
        "ट": "त",
        "ठ": "थ",
        "ड": "द",
        "ढ": "ध",
        "ण": "न",
        "श": "स",
        "ष": "स",
        "ळ": "ल",
    }


def _validate_character(value: object, label: str, script: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 1
        or not _is_assigned_script_codepoint(ord(value), script)
    ):
        raise ValueError(f"invalid Magar Akkha {label}: {value!r}")
    return value


def _freeze_contract(
    forward_entries: Mapping[str, str], fold_entries: Mapping[str, str]
) -> tuple[Mapping[str, str], Mapping[str, str], Mapping[str, str]]:
    forward = dict(forward_entries)
    folds = dict(fold_entries)
    if len(forward) != 69:
        raise ValueError(f"Magar Akkha forward map must contain 69 entries, got {len(forward)}")
    if len(folds) != 8:
        raise ValueError(f"Magar Akkha fold map must contain 8 entries, got {len(folds)}")

    for source, target in forward.items():
        _validate_character(source, "Devanagari source", "Devanagari")
        _validate_character(target, f"Brahmi target for {source!r}", "Brahmi")
    if len(set(forward.values())) != len(forward):
        raise ValueError("Magar Akkha forward targets must be one-to-one")

    for source, target in folds.items():
        _validate_character(source, "fold source", "Devanagari")
        _validate_character(target, f"fold target for {source!r}", "Devanagari")
        if source not in forward or target not in forward:
            raise ValueError("Magar Akkha fold sources and targets must exist in the forward map")
        if source == target:
            raise ValueError("Magar Akkha folds must change their source")

    reverse = {target: source for source, target in forward.items()}
    return (
        MappingProxyType(forward),
        MappingProxyType(reverse),
        MappingProxyType(folds),
    )


(
    _DEFAULT_DEVANAGARI_TO_BRAHMI,
    _DEFAULT_BRAHMI_TO_DEVANAGARI,
    _DEFAULT_FOLD_TO_MINIMAL_AKKHA,
) = _freeze_contract(_build_map(), _build_fold_map())

DEVANAGARI_TO_BRAHMI = _DEFAULT_DEVANAGARI_TO_BRAHMI
BRAHMI_TO_DEVANAGARI = _DEFAULT_BRAHMI_TO_DEVANAGARI
FOLD_TO_MINIMAL_AKKHA = _DEFAULT_FOLD_TO_MINIMAL_AKKHA


@dataclass(frozen=True)
class MagarAkkhaTransliteration:
    """Result of an explicit Devanagari/Brahmi transliteration."""

    source_text: str
    unicode_text: str
    target: str
    replacement_count: int
    folded_count: int
    unmapped_codepoints: list[str]


def transliterate_magar_akkha(
    text: str,
    *,
    target: str = "brahmi",
    fold_to_minimal_inventory: bool = False,
    strict: bool = False,
) -> MagarAkkhaTransliteration:
    """Transliterate between Devanagari and the project Brahmi representation.

    ``target="brahmi"`` is the forward Magar Akkha representation.
    ``target="devanagari"`` performs the reverse substitution. The
    project-defined fold of retroflex and extra-sibilant distinctions is lossy
    and forward-only.
    """
    require_boolean(fold_to_minimal_inventory, "Magar Akkha fold_to_minimal_inventory")
    require_boolean(strict, "strict")
    if type(target) is not str or target not in {"brahmi", "devanagari"}:
        raise ValueError("target must be 'brahmi' or 'devanagari'")
    if target == "brahmi":
        table = _DEFAULT_DEVANAGARI_TO_BRAHMI
        source_range = range(0x0900, 0x0980)
    elif target == "devanagari":
        if fold_to_minimal_inventory:
            raise ValueError("minimal-inventory folding is available only for Brahmi output")
        table = _DEFAULT_BRAHMI_TO_DEVANAGARI
        source_range = range(0x11000, 0x11080)

    output: list[str] = []
    unmapped: set[str] = set()
    replacements = 0
    folded = 0
    for original in text:
        char = original
        if target == "brahmi" and fold_to_minimal_inventory:
            char = _DEFAULT_FOLD_TO_MINIMAL_AKKHA.get(char, char)
            if char != original:
                folded += 1
        mapped = table.get(char)
        if mapped is not None:
            output.append(mapped)
            replacements += 1
            continue
        output.append(original)
        if ord(original) in source_range:
            unmapped.add(f"U+{ord(original):04X}")

    if strict and unmapped:
        raise ValueError(
            f"unmapped characters in Magar Akkha {target} transliteration: "
            + " ".join(sorted(unmapped))
        )
    return MagarAkkhaTransliteration(
        source_text=text,
        unicode_text=unicodedata.normalize("NFC", "".join(output)),
        target=target,
        replacement_count=replacements,
        folded_count=folded,
        unmapped_codepoints=sorted(unmapped),
    )
