"""Sunuwar / Jenticha (Koĩts) legacy display font -> Unicode Sunuwar.

The project-derived layout is routed for the legacy ``koits`` and ``kirat1``
BaseFont names. Its 38 confirmed printable-ASCII sources map one-to-one to 28
Sunuwar letters and ten Sunuwar digits; twenty punctuation sources pass through
literally, and the contract contains no uncertain mapping entry.

The project does not use or cite a public upstream byte-to-Unicode table for
this legacy layout. The source PDFs, embedded fonts, crops, and intermediate
comparison artifacts used for the project derivation are not distributed by
this package. Public orthography and Unicode-proposal references document the
encoded characters and their regional forms, but do not independently define
the legacy byte assignments. The exact project contract and this evidence
boundary are recorded in ``docs/EVIDENCE.md``.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ._controls import codepoint_labels, require_boolean
from .unicode_span import _is_assigned_script_codepoint

# Digits: byte '0'..'9' -> U+11BF0..U+11BF9 in order.
SUNUWAR_DIGITS: Mapping[str, str] = MappingProxyType({str(i): chr(0x11BF0 + i) for i in range(10)})

# Confirmed byte -> Unicode letter assignments.
SUNUWAR_LETTERS_CONFIRMED: Mapping[str, str] = MappingProxyType(
    {
        "{": chr(0x11BC3),  # SUNUWAR LETTER IMAR
        "}": chr(0x11BC2),  # SUNUWAR LETTER EKO
        "z": chr(0x11BC9),  # SUNUWAR LETTER PIP
        "A": chr(0x11BD6),  # SUNUWAR LETTER AAL
        "O": chr(0x11BD1),  # SUNUWAR LETTER OTTHI
        "i": chr(0x11BCC),  # SUNUWAR LETTER CARMI
        "k": chr(0x11BDE),  # SUNUWAR LETTER TENTU
        "l": chr(0x11BDF),  # SUNUWAR LETTER THELE
        "m": chr(0x11BC1),  # SUNUWAR LETTER TASLA
        "n": chr(0x11BD8),  # SUNUWAR LETTER THARI
        "o": chr(0x11BC0),  # SUNUWAR LETTER DEVI
        "p": chr(0x11BCD),  # SUNUWAR LETTER NAH
        "w": chr(0x11BD0),  # SUNUWAR LETTER LOACHA
        "y": chr(0x11BDC),  # SUNUWAR LETTER SHYER
        "f": chr(0x11BDB),  # SUNUWAR LETTER KHA
        "s": chr(0x11BCE),  # SUNUWAR LETTER BUR
        "a": chr(0x11BC8),  # SUNUWAR LETTER APPHO
        "t": chr(0x11BC7),  # SUNUWAR LETTER MA
        "e": chr(0x11BCB),  # SUNUWAR LETTER HAMSO
        "v": chr(0x11BC4),  # SUNUWAR LETTER REU
        "q": chr(0x11BE0),  # SUNUWAR LETTER KLOKO
        "x": chr(0x11BD3),  # SUNUWAR LETTER VARCA
        "r": chr(0x11BD9),  # SUNUWAR LETTER PHAR
        "u": chr(0x11BD4),  # SUNUWAR LETTER YAT
        "g": chr(0x11BD5),  # SUNUWAR LETTER AVA
        "h": chr(0x11BDA),  # SUNUWAR LETTER NGAR
        "j": chr(0x11BCF),  # SUNUWAR LETTER JYAH
        "|": chr(0x11BC5),  # SUNUWAR LETTER UTTHI
    }
)

# Kept as a public compatibility constant. No uncertain mapping entry exists.
SUNUWAR_LETTERS_UNCERTAIN: Mapping[str, str] = MappingProxyType({})

# Literal punctuation sources: passed through unchanged.
SUNUWAR_PASSTHROUGH: frozenset[str] = frozenset(
    {
        ",",
        ":",
        "-",
        "(",
        ")",
        "\\",
        ".",
        "=",
        "/",
        "_",
        "<",
        "+",
        "]",
        "[",
        ";",
        "'",
        '"',
        "!",
        "?",
        "%",
    }
)

_SUNUWAR_BLOCK_LO = 0x11BC0
_SUNUWAR_BLOCK_HI = 0x11BFF


def _validate_contract_section(entries: Mapping[str, str], label: str) -> None:
    for source, target in entries.items():
        if not isinstance(source, str) or len(source) != 1 or not (0x21 <= ord(source) <= 0x7E):
            raise ValueError(f"invalid Sunuwar {label} source {source!r}")
        if (
            not isinstance(target, str)
            or len(target) != 1
            or not _is_assigned_script_codepoint(ord(target), "Sunuwar")
        ):
            raise ValueError(f"invalid Sunuwar {label} target {target!r} for {source!r}")


def _freeze_default_contract() -> tuple[Mapping[str, str], Mapping[str, str], frozenset[str]]:
    digit_sources = set(SUNUWAR_DIGITS)
    letter_sources = set(SUNUWAR_LETTERS_CONFIRMED)
    if digit_sources & letter_sources:
        raise ValueError("Sunuwar digit and letter sources overlap")

    confirmed = {**SUNUWAR_DIGITS, **SUNUWAR_LETTERS_CONFIRMED}
    uncertain = dict(SUNUWAR_LETTERS_UNCERTAIN)
    if not confirmed:
        raise ValueError("SunuwarConverter requires a non-empty confirmed map")
    overlap = set(confirmed) & set(uncertain)
    if overlap:
        labels = " ".join(repr(source) for source in sorted(overlap))
        raise ValueError(f"Sunuwar confirmed and uncertain sources overlap: {labels}")

    _validate_contract_section(confirmed, "confirmed")
    _validate_contract_section(uncertain, "uncertain")
    targets = list(confirmed.values()) + list(uncertain.values())
    if len(targets) != len(set(targets)):
        raise ValueError("Sunuwar confirmed and uncertain targets must be one-to-one")

    passthrough = frozenset(SUNUWAR_PASSTHROUGH)
    mapping_sources = set(confirmed) | set(uncertain)
    if mapping_sources & passthrough:
        raise ValueError("Sunuwar mapping and passthrough sources overlap")
    if any(
        not isinstance(source, str) or len(source) != 1 or not (0x21 <= ord(source) <= 0x7E)
        for source in passthrough
    ):
        raise ValueError("invalid Sunuwar passthrough source")

    return MappingProxyType(confirmed), MappingProxyType(uncertain), passthrough


_DEFAULT_CONFIRMED, _DEFAULT_UNCERTAIN, _DEFAULT_PASSTHROUGH = _freeze_default_contract()


@dataclass(frozen=True)
class SunuwarConversion:
    legacy_text: str
    unicode_text: str
    sunuwar_char_count: int
    replacement_count: int
    confirmed_byte_count: int
    uncertain_bytes: list[str] = field(default_factory=list)
    unmapped_bytes: list[str] = field(default_factory=list)


class SunuwarConverter:
    """Apply the derived Sunuwar legacy byte -> Unicode map.

    The built-in contract contains no uncertain mapping entry.
    ``apply_uncertain`` remains an accepted compatibility argument but currently
    has no effect.
    """

    def __init__(self, apply_uncertain: bool = False) -> None:
        require_boolean(apply_uncertain, "Sunuwar apply_uncertain")
        self._confirmed = _DEFAULT_CONFIRMED
        self._uncertain = _DEFAULT_UNCERTAIN
        self._passthrough = _DEFAULT_PASSTHROUGH
        table = dict(self._confirmed)
        if apply_uncertain:
            table.update(self._uncertain)
        self._table = MappingProxyType(table)
        self._apply_uncertain = apply_uncertain

    def convert(self, text: str) -> SunuwarConversion:
        out: list[str] = []
        replacements = 0
        confirmed = 0
        uncertain_seen: set[str] = set()
        unmapped: set[str] = set()
        for ch in text:
            if ch in " \t\r\n":
                out.append(ch)
                continue
            mapped = self._table.get(ch)
            if mapped is not None:
                out.append(mapped)
                replacements += 1
                if ch in self._confirmed:
                    confirmed += 1
                continue
            if ch in self._uncertain:
                uncertain_seen.add(ch)
                out.append(ch)  # left untouched when not applying uncertain
                continue
            if ch in self._passthrough:
                out.append(ch)
                continue
            out.append(ch)
            if not _is_assigned_script_codepoint(ord(ch), "Sunuwar"):
                unmapped.add(ch)
        converted = unicodedata.normalize("NFC", "".join(out))
        sun_count = sum(1 for c in converted if _SUNUWAR_BLOCK_LO <= ord(c) <= _SUNUWAR_BLOCK_HI)
        return SunuwarConversion(
            legacy_text=text,
            unicode_text=converted,
            sunuwar_char_count=sun_count,
            replacement_count=replacements,
            confirmed_byte_count=confirmed,
            uncertain_bytes=sorted(uncertain_seen),
            unmapped_bytes=sorted(unmapped),
        )


def convert_sunuwar(
    text: str, *, apply_uncertain: bool = False, strict: bool = False
) -> SunuwarConversion:
    """Convert Sunuwar/Jenticha legacy font text to Unicode Sunuwar (NFC).

    Returns a :class:`SunuwarConversion`. The built-in contract contains no
    uncertain mapping entry; ``apply_uncertain`` is retained for API
    compatibility and is currently a no-op. Input values that are neither mapped
    bytes, known punctuation, nor assigned Unicode Sunuwar are surfaced in
    ``unmapped_bytes``. With ``strict=True`` any such value raises ``ValueError``.
    """
    require_boolean(apply_uncertain, "Sunuwar apply_uncertain")
    require_boolean(strict, "strict")
    result = SunuwarConverter(apply_uncertain=apply_uncertain).convert(text)
    if strict and (result.uncertain_bytes or result.unmapped_bytes):
        flagged = result.uncertain_bytes + result.unmapped_bytes
        raise ValueError(
            "unmapped/uncertain bytes after Sunuwar conversion: "
            + " ".join(codepoint_labels(flagged))
        )
    return result
