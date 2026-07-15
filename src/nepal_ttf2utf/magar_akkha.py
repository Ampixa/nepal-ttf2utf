"""Standards-aligned Magar Akkha representation using Unicode Brahmi.

Unicode's script review recommends treating Magar Akkha as a Brahmi variant
unless evidence establishes distinct encoded characters or behavior. This
module transliterates Unicode Devanagari to the corresponding Unicode Brahmi
characters; it is not a mapping for an unknown legacy Akkha font.

The functional mapping is adapted from Ampixa's MIT-licensed magar-toolkit.
Default conversion preserves every supported distinction. Minimal-inventory
folding is explicit and lossy.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


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
        "ा": "𑀸",
        "ि": "𑀹",
        "ी": "𑀺",
        "ु": "𑀻",
        "ू": "𑀼",
        "े": "𑀾",
        "ै": "𑀿",
        "ो": "𑁀",
        "ौ": "𑁁",
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


DEVANAGARI_TO_BRAHMI = _build_map()
BRAHMI_TO_DEVANAGARI = {target: source for source, target in DEVANAGARI_TO_BRAHMI.items()}

FOLD_TO_MINIMAL_AKKHA = {
    "ट": "त",
    "ठ": "थ",
    "ड": "द",
    "ढ": "ध",
    "ण": "न",
    "श": "स",
    "ष": "स",
    "ळ": "ल",
}


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
    """Transliterate between Devanagari and standards-aligned Brahmi.

    ``target="brahmi"`` is the forward Magar Akkha representation.
    ``target="devanagari"`` performs the reverse substitution. Folding the
    retroflex and extra-sibilant distinctions is lossy and forward-only.
    """
    if target == "brahmi":
        table = DEVANAGARI_TO_BRAHMI
        source_range = range(0x0900, 0x0980)
    elif target == "devanagari":
        if fold_to_minimal_inventory:
            raise ValueError("minimal-inventory folding is available only for Brahmi output")
        table = BRAHMI_TO_DEVANAGARI
        source_range = range(0x11000, 0x11080)
    else:
        raise ValueError("target must be 'brahmi' or 'devanagari'")

    output: list[str] = []
    unmapped: set[str] = set()
    replacements = 0
    folded = 0
    for original in text:
        char = original
        if target == "brahmi" and fold_to_minimal_inventory:
            char = FOLD_TO_MINIMAL_AKKHA.get(char, char)
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
