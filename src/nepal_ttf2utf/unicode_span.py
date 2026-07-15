"""Version-stable validation for font spans that already contain Unicode.

Some source documents label text with a script-specific font even though the
text layer already stores the intended Unicode characters. These spans need
normalization and validation, not a legacy byte map. The assigned repertoires
are pinned so script membership does not depend on the older Unicode Character
Database bundled with a particular supported Python release.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

UNICODE_REPERTOIRE_VERSION = "17.0.0"


@dataclass(frozen=True)
class UnicodeSpanConversion:
    """Result of validating an already-Unicode font span."""

    source_text: str
    unicode_text: str
    script: str
    script_char_count: int
    invalid_codepoints: list[str]
    unexpected_script_codepoints: list[str] = field(default_factory=list)


# Assigned repertoire from Unicode 17.0 DerivedAge.txt, intersected with the
# named script blocks used by this package. Explicit ranges are necessary for
# Unicode 16 scripts such as Gurung Khema, Sunuwar, and Kirat Rai: runtimes
# predating Unicode 16 may otherwise report their assigned characters as ``Cn``.
_ASSIGNED_BLOCK_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "Brahmi": (
        (0x11000, 0x1104D),
        (0x11052, 0x11075),
        (0x1107F, 0x1107F),
    ),
    "Devanagari": (
        (0x0900, 0x097F),
        (0x1CD0, 0x1CFA),
        (0xA8E0, 0xA8FF),
        (0x11B00, 0x11B09),
    ),
    "Gurung Khema": ((0x16100, 0x16139),),
    "Kirat Rai": ((0x16D40, 0x16D79),),
    "Lepcha": (
        (0x1C00, 0x1C37),
        (0x1C3B, 0x1C49),
        (0x1C4D, 0x1C4F),
    ),
    "Limbu": (
        (0x1900, 0x191E),
        (0x1920, 0x192B),
        (0x1930, 0x193B),
        (0x1940, 0x1940),
        (0x1944, 0x194F),
    ),
    "Newa": (
        (0x11400, 0x1145B),
        (0x1145D, 0x11461),
    ),
    "Ol Chiki": ((0x1C50, 0x1C7F),),
    "Sunuwar": (
        (0x11BC0, 0x11BE1),
        (0x11BF0, 0x11BF9),
    ),
    "Tibetan": (
        (0x0F00, 0x0F47),
        (0x0F49, 0x0F6C),
        (0x0F71, 0x0F97),
        (0x0F99, 0x0FBC),
        (0x0FBE, 0x0FCC),
        (0x0FCE, 0x0FDA),
    ),
    "Tirhuta": (
        (0x11480, 0x114C7),
        (0x114D0, 0x114D9),
    ),
}

# Script-property ranges from Unicode 17.0 Scripts.txt. These are separate from
# assigned block repertoire so Common/Inherited values such as the Indic danda
# and Vedic marks are not attributed exclusively to Devanagari.
_SCRIPT_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    **_ASSIGNED_BLOCK_RANGES,
    "Devanagari": (
        (0x0900, 0x0950),
        (0x0955, 0x0963),
        (0x0966, 0x097F),
        (0xA8E0, 0xA8FF),
        (0x11B00, 0x11B09),
    ),
    "Tibetan": (
        (0x0F00, 0x0F47),
        (0x0F49, 0x0F6C),
        (0x0F71, 0x0F97),
        (0x0F99, 0x0FBC),
        (0x0FBE, 0x0FCC),
        (0x0FCE, 0x0FD4),
        (0x0FD9, 0x0FDA),
    ),
}

# Canonical normalization data added in Unicode 16.0. Older Python runtimes do
# not know these immediate decompositions or U+1612F's nonzero combining class.
# The bounded fallback below supplies only this pinned delta, then delegates all
# older decomposition and pair-composition knowledge to the runtime UCD.
_PINNED_CANONICAL_DECOMPOSITIONS: Mapping[int, tuple[int, int]] = MappingProxyType(
    {
        0x16121: (0x1611E, 0x1611E),
        0x16122: (0x1611E, 0x16129),
        0x16123: (0x1611E, 0x1611F),
        0x16124: (0x16129, 0x1611F),
        0x16125: (0x1611E, 0x16120),
        0x16126: (0x16121, 0x1611F),
        0x16127: (0x16122, 0x1611F),
        0x16128: (0x16121, 0x16120),
        0x16D68: (0x16D67, 0x16D67),
        0x16D69: (0x16D63, 0x16D67),
        0x16D6A: (0x16D69, 0x16D67),
    }
)
_PINNED_CANONICAL_COMBINING_CLASSES: Mapping[int, int] = MappingProxyType({0x1612F: 9})
_PINNED_CANONICAL_COMPOSITIONS: Mapping[tuple[int, int], int] = MappingProxyType(
    {
        decomposition: composed
        for composed, decomposition in _PINNED_CANONICAL_DECOMPOSITIONS.items()
    }
)
_PINNED_NORMALIZATION_PARTICIPANTS = frozenset(
    set(_PINNED_CANONICAL_DECOMPOSITIONS)
    | set(_PINNED_CANONICAL_COMBINING_CLASSES)
    | {
        member
        for decomposition in _PINNED_CANONICAL_DECOMPOSITIONS.values()
        for member in decomposition
    }
)

# Complete block boundaries are kept separately so reserved codepoints remain
# invalid even if a future Python runtime assigns them after the pinned UCD.
_SCRIPT_BLOCK_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "Brahmi": ((0x11000, 0x1107F),),
    "Devanagari": (
        (0x0900, 0x097F),
        (0x1CD0, 0x1CFF),
        (0xA8E0, 0xA8FF),
        (0x11B00, 0x11B5F),
    ),
    "Gurung Khema": ((0x16100, 0x1613F),),
    "Kirat Rai": ((0x16D40, 0x16D7F),),
    "Lepcha": ((0x1C00, 0x1C4F),),
    "Limbu": ((0x1900, 0x194F),),
    "Newa": ((0x11400, 0x1147F),),
    "Ol Chiki": ((0x1C50, 0x1C7F),),
    "Sunuwar": ((0x11BC0, 0x11BFF),),
    "Tibetan": ((0x0F00, 0x0FFF),),
    "Tirhuta": ((0x11480, 0x114DF),),
}


def _in_ranges(codepoint: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)


def _canonical_script_name(script: str) -> str:
    key = " ".join(script.strip().replace("_", " ").replace("-", " ").split()).casefold()
    names = {name.casefold(): name for name in _ASSIGNED_BLOCK_RANGES}
    try:
        return names[key]
    except KeyError as error:
        raise ValueError(
            f"unsupported Unicode span script {script!r}; "
            f"expected one of {supported_unicode_scripts()}"
        ) from error


def supported_unicode_scripts() -> tuple[str, ...]:
    """Return canonical script names accepted by :func:`validate_unicode_span`."""
    return tuple(sorted(_ASSIGNED_BLOCK_RANGES))


def _specific_scripts(codepoint: int) -> tuple[str, ...]:
    return tuple(
        script for script, ranges in _SCRIPT_RANGES.items() if _in_ranges(codepoint, ranges)
    )


def _assigned_in_supported_block(codepoint: int) -> bool:
    return any(_in_ranges(codepoint, ranges) for ranges in _ASSIGNED_BLOCK_RANGES.values())


def _is_assigned_script_codepoint(codepoint: int, script: str) -> bool:
    """Return pinned Unicode-17 assignment for one supported script repertoire."""
    canonical_script = (
        script if script in _ASSIGNED_BLOCK_RANGES else _canonical_script_name(script)
    )
    return _in_ranges(codepoint, _ASSIGNED_BLOCK_RANGES[canonical_script])


def _inside_supported_block(codepoint: int) -> bool:
    return any(_in_ranges(codepoint, ranges) for ranges in _SCRIPT_BLOCK_RANGES.values())


def _is_noncharacter(codepoint: int) -> bool:
    return 0xFDD0 <= codepoint <= 0xFDEF or codepoint & 0xFFFF in {0xFFFE, 0xFFFF}


def _pinned_combining_class(codepoint: int) -> int:
    return _PINNED_CANONICAL_COMBINING_CLASSES.get(codepoint, unicodedata.combining(chr(codepoint)))


def _decompose_codepoint(codepoint: int, output: list[int]) -> None:
    pinned = _PINNED_CANONICAL_DECOMPOSITIONS.get(codepoint)
    if pinned is not None:
        for member in pinned:
            _decompose_codepoint(member, output)
        return
    output.extend(ord(char) for char in unicodedata.normalize("NFD", chr(codepoint)))


def _canonical_order(codepoints: list[int]) -> list[int]:
    ordered: list[int] = []
    pending_nonstarters: list[int] = []
    for codepoint in codepoints:
        if _pinned_combining_class(codepoint) == 0:
            ordered.extend(sorted(pending_nonstarters, key=_pinned_combining_class))
            pending_nonstarters.clear()
            ordered.append(codepoint)
        else:
            pending_nonstarters.append(codepoint)
    ordered.extend(sorted(pending_nonstarters, key=_pinned_combining_class))
    return ordered


def _compose_pair(starter: int, codepoint: int) -> int | None:
    pinned = _PINNED_CANONICAL_COMPOSITIONS.get((starter, codepoint))
    if pinned is not None:
        return pinned
    runtime_pair = unicodedata.normalize("NFC", chr(starter) + chr(codepoint))
    if len(runtime_pair) == 1:
        return ord(runtime_pair)
    return None


def _canonical_compose(codepoints: list[int]) -> str:
    result: list[int] = []
    starter_index: int | None = None
    starter: int | None = None
    last_combining_class = 0

    for codepoint in codepoints:
        current_class = _pinned_combining_class(codepoint)
        composed = None
        if starter is not None and (
            last_combining_class == 0 or last_combining_class < current_class
        ):
            composed = _compose_pair(starter, codepoint)

        if composed is not None:
            assert starter_index is not None
            result[starter_index] = composed
            starter = composed
            continue

        if current_class == 0:
            starter_index = len(result)
            starter = codepoint
        last_combining_class = current_class
        result.append(codepoint)

    return "".join(chr(codepoint) for codepoint in result)


def _normalize_nfc(text: str) -> str:
    if not any(ord(char) in _PINNED_NORMALIZATION_PARTICIPANTS for char in text):
        return unicodedata.normalize("NFC", text)

    decomposed: list[int] = []
    for char in text:
        _decompose_codepoint(ord(char), decomposed)
    return _canonical_compose(_canonical_order(decomposed))


def validate_unicode_span(
    text: str,
    *,
    script: str,
    strict: bool = False,
) -> UnicodeSpanConversion:
    """Normalize and validate text already encoded for ``script``.

    Common punctuation, whitespace, ASCII digits, and embedded Latin text are kept.
    Invalid replacement characters, private-use values, surrogates, reserved
    codepoints inside a pinned script block, and non-text controls are reported.
    Characters assigned to a different supported Script property are reported
    separately. In strict mode, every diagnostic raises and a nonempty span
    must contain at least one script-specific character from the declared
    script.
    """
    canonical_script = _canonical_script_name(script)
    normalized = _normalize_nfc(text)
    invalid: set[str] = set()
    unexpected: dict[int, tuple[str, ...]] = {}
    script_count = 0

    for char in normalized:
        codepoint = ord(char)
        specific_scripts = _specific_scripts(codepoint)
        if canonical_script in specific_scripts:
            script_count += 1
        elif specific_scripts:
            unexpected[codepoint] = specific_scripts

        category = unicodedata.category(char)
        known_assigned = _assigned_in_supported_block(codepoint)
        if (
            char == "\ufffd"
            or category in {"Cs", "Co"}
            or _is_noncharacter(codepoint)
            or (_inside_supported_block(codepoint) and not known_assigned)
            or (category == "Cn" and not known_assigned)
            or (category == "Cc" and char not in "\t\r\n")
        ):
            invalid.add(f"U+{codepoint:04X}")

    if strict and invalid:
        raise ValueError(
            f"invalid characters in Unicode {canonical_script} span: " + " ".join(sorted(invalid))
        )
    if strict and unexpected:
        details = " ".join(
            f"U+{codepoint:04X} ({'/'.join(scripts)})"
            for codepoint, scripts in sorted(unexpected.items())
        )
        raise ValueError(
            f"unexpected script characters in Unicode {canonical_script} span: {details}"
        )
    if strict and normalized.strip() and script_count == 0:
        raise ValueError(
            f"nonempty {canonical_script} span contains no {canonical_script} characters"
        )

    return UnicodeSpanConversion(
        source_text=text,
        unicode_text=normalized,
        script=canonical_script,
        script_char_count=script_count,
        invalid_codepoints=sorted(invalid),
        unexpected_script_codepoints=[f"U+{codepoint:04X}" for codepoint in sorted(unexpected)],
    )
