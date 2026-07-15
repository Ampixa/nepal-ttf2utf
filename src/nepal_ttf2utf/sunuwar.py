"""Sunuwar / Jenticha (Koĩts) legacy display font -> Unicode Sunuwar (U+11BC0-U+11BFF).

The Sunuwar edition of the Sikkim Herald ("Mukhia") is typeset in a legacy display
font that ships under two BaseFont names — ``koits`` (the 2021 edition, a Type0/
Identity-H CID font) and ``kirat1`` (the 2023/2024 editions, byte-encoded TrueType,
WinAnsi). Each visible glyph is addressed by a single Latin byte, so the extractable
text stream is the raw legacy byte sequence, not Unicode.

There is no published byte->Unicode table for this layout. The map here was derived by
GLYPH-SHAPE IDENTITY: ``koits`` and ``kirat1`` were proven byte-for-byte identical
outlines, so one map serves both. Each legacy byte's outline was rendered and matched
against the 44 Sunuwar Unicode codepoints in Noto Sans Sunuwar; the Sunuwar block is a
33-letter alphabet + one auspicious sign + 10 digits with NO dependent vowel signs, so
every legacy byte is a full letter, digit, or punctuation mark. A first pass fixed the
digits + 19 letter bytes by printed-crop visual match; a second bijective pass resolved
8 more (``v q x r u g h j``) by shape (IoU + chamfer) with a hole-count constraint,
adjudicated against the L2/21-157R Unicode proposal chart and validated by a printed-ink
single-glyph round-trip.

The final observed byte, ``|``, is U+11BC5 SUNUWAR LETTER UTTHI. The Sikkim form in
Richard Ishida's reviewed orthography notes is the same flowing open-2 shape as the
legacy glyph: a 600-dpi corpus crop has normalized largest-component IoU 0.7395 with
the labeled Sikkim UTTHI image, versus 0.3681 with Sikkim SHYELE. This regional form
explains why comparison against Noto's Nepal-style glyph originally left it uncertain.
All observed Sunuwar letter and digit bytes are now confirmed.

Provenance / evidence: ocr-tech ``outputs/sunuwar-map-derivation/`` (contact sheets,
printed-crop verification, round-trip panels).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

# --- Digits: validated, byte '0'..'9' -> U+11BF0..U+11BF9 in order. ---
SUNUWAR_DIGITS: dict[str, str] = {str(i): chr(0x11BF0 + i) for i in range(10)}

# --- Letters: CONFIRMED tier (printed-crop and/or round-trip verified). ---
# byte -> Unicode codepoint (Noto glyph name in comment).
SUNUWAR_LETTERS_CONFIRMED: dict[str, str] = {
    "{": chr(0x11BC3),  # imarsunuwar  (cross '+')    round-trip IoU 0.74, printed-crop match
    "}": chr(0x11BC2),  # ekosunuwar   ('土')         round-trip IoU 0.55, printed-crop match
    "z": chr(0x11BC9),  # pipsunuwar   (curl '9')     printed-crop match (curl), margin 0.20
    "A": chr(0x11BD6),  # aalsunuwar   ('Z'/zigzag)   round-trip IoU 0.52, printed-crop match
    "O": chr(0x11BD1),  # otthisunuwar               round-trip IoU 0.58, margin 0.14
    "i": chr(0x11BCC),  # carmisunuwar ('<')          round-trip IoU 0.71, printed-crop match
    "k": chr(0x11BDE),  # tentusunuwar ('E'-stack)    round-trip IoU 0.71, printed-crop match
    "l": chr(0x11BDF),  # thelesunuwar               round-trip IoU 0.67, margin 0.17
    "m": chr(0x11BC1),  # taslasunuwar               round-trip IoU 0.58, margin 0.08
    "n": chr(0x11BD8),  # tharisunuwar               round-trip IoU 0.52, margin 0.07
    "o": chr(0x11BC0),  # devisunuwar  ('刀' box)      round-trip IoU 0.50, printed-crop match
    "p": chr(0x11BCD),  # nahsunuwar                 round-trip IoU 0.54, margin 0.10
    "w": chr(0x11BD0),  # loachasunuwar('Ш' comb)     round-trip IoU 0.46, printed-crop match
    "y": chr(0x11BDC),  # shyersunuwar ('U')          round-trip IoU 0.82, printed-crop match
    "f": chr(0x11BDB),  # khasunuwar   ('Π' gate)      round-trip IoU 0.46, printed-crop match
    "s": chr(0x11BCE),  # bursunuwar   (cross+hook)   round-trip IoU 0.54, printed-crop match
    "a": chr(0x11BC8),  # apphosunuwar (rev-'3' curl) round-trip IoU 0.51, printed-crop match
    "t": chr(0x11BC7),  # masunuwar    ('Ш' comb)      printed-crop match (comb=comb); n=1259
    "e": chr(0x11BCB),  # hamsosunuwar (cross+foot)   printed-crop match (cross+hook); n=1006
    # The 8 bytes resolved by the second derivation pass — bijective assignment of the
    # uncertain bytes to the still-free codepoints, scored by Kirat1-glyph-vs-Noto-glyph
    # shape (IoU + chamfer) with a topological hole-count constraint, adjudicated against
    # the L2/21-157R proposal chart and validated by a printed-ink single-glyph round-trip.
    "v": chr(
        0x11BC4
    ),  # reusunuwar   (N+diagonal)   shape 0.545>=floor; bijection+context-match; n=765
    "q": chr(
        0x11BE0
    ),  # klokosunuwar (bowl+stem)    shape 0.567>=floor; bijection+context-match; n=579
    "x": chr(
        0x11BD3
    ),  # varcasunuwar (N+hook)       shape 0.522>=floor; bijection+context-match; n=97
    "r": chr(0x11BD9),  # pharsunuwar  ('alpha')      shape 0.521>=floor; hole-match 1=1; n=40
    "u": chr(
        0x11BD4
    ),  # yatsunuwar   (looped 'e')   topology-locked (1 hole=loop); printed-ink 7/8 vote
    "g": chr(
        0x11BD5
    ),  # avasunuwar   (forked vert)  embedded-glyph 0.454 decisive over gil; printed-ink
    "h": chr(0x11BDA),  # ngarsunuwar  ('3')          printed-ink 7/8 vote over donga('5'); n=180
    "j": chr(
        0x11BCF
    ),  # jyahsunuwar  (dagger '+')   embedded-glyph 0.504 decisive (dagger=dagger); n=198
    # Sikkim UTTHI has a regional flowing open-2 form. It matches the Sikkim-labeled
    # reference glyph at IoU 0.7395 (versus 0.3681 for SHYELE); n=1079.
    "|": chr(0x11BC5),  # utthisunuwar /u/
}

# Kept as a public compatibility constant. No observed bytes remain uncertain.
SUNUWAR_LETTERS_UNCERTAIN: dict[str, str] = {}

# Punctuation / danda-like bytes: passed through unchanged (not Sunuwar letters).
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


def _build_default_table() -> dict[str, str]:
    table: dict[str, str] = {}
    table.update(SUNUWAR_DIGITS)
    table.update(SUNUWAR_LETTERS_CONFIRMED)
    return table


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

    All observed letter and digit bytes are confirmed. ``apply_uncertain`` remains an
    accepted compatibility argument but currently has no effect.
    """

    def __init__(self, apply_uncertain: bool = False) -> None:
        table = _build_default_table()
        if apply_uncertain:
            table.update(SUNUWAR_LETTERS_UNCERTAIN)
        if not table:
            raise ValueError("SunuwarConverter requires a non-empty map")
        self._table = table
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
                if ch in SUNUWAR_LETTERS_CONFIRMED or ch in SUNUWAR_DIGITS:
                    confirmed += 1
                continue
            if ch in SUNUWAR_LETTERS_UNCERTAIN:
                uncertain_seen.add(ch)
                out.append(ch)  # left untouched when not applying uncertain
                continue
            if ch in SUNUWAR_PASSTHROUGH:
                out.append(ch)
                continue
            out.append(ch)
            if not (_SUNUWAR_BLOCK_LO <= ord(ch) <= _SUNUWAR_BLOCK_HI):
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

    Returns a :class:`SunuwarConversion`. All observed script bytes are confirmed;
    ``apply_uncertain`` is retained for API compatibility and is currently a no-op.
    Bytes that are neither letters, digits, nor known punctuation are surfaced in
    ``unmapped_bytes``. With ``strict=True`` any unmapped byte raises ``ValueError``.
    """
    result = SunuwarConverter(apply_uncertain=apply_uncertain).convert(text)
    if strict and (result.uncertain_bytes or result.unmapped_bytes):
        flagged = result.uncertain_bytes + result.unmapped_bytes
        raise ValueError(
            "unmapped/uncertain bytes after Sunuwar conversion: " + " ".join(sorted(set(flagged)))
        )
    return result
