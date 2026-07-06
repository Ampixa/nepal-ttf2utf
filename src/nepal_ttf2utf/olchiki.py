"""'Ol Chiki Optimum' legacy display font -> Unicode Ol Chiki / Santali (U+1C50-U+1C7F).

The Aale Chhatka Santali e-magazine (self-published, archive.org) is typeset in the
'Ol Chiki Optimum' font family (BaseFont ``OLCKOptimum-Medium`` / ``OLCKOptimum-
ExtraBlack``; foundry Sengellabs, marketed as "unicoded"). Despite that marketing
claim, the embedded font's own cmap keys each Ol Chiki glyph OUTLINE to a Latin ASCII
codepoint: the font renders correctly on screen (an Ol Chiki reader sees real Ol Chiki
shapes) but the extractable PDF text is Latin garbage, e.g. the string
``CaDokiya. SanTazi savheD`` -- an identity-Latin encoding, the same class of problem
as the Sikkim Herald live-text Lepcha font (see ``lepcha.py``), not a rendering bug.

The map (``maps/olck_optimum.json``) was derived by GLYPH-SHAPE IDENTITY: each byte's
glyph was rendered (via the extracted embedded TTF) and shape-matched (IoU on
centered/scaled binary renders) against Noto Sans Ol Chiki, refined with a Hungarian
optimal-assignment pass across all 32 distinct legacy glyphs and the 38 Ol Chiki
base-letter + modifier-sign codepoints. Two corrections were applied on top of the raw
shape score: corpus byte FREQUENCY (the single most-frequent byte was anchored to LA,
the alphabet's first/most fundamental letter, overriding a marginally cheaper
shape-only optimum that would have given LA to a much rarer byte) and the alphabet's
own STRUCTURE (the 6 Latin-vowel-family bytes landed exactly on Ol Chiki's 6
row-starter letters LAA/LE/LI/LA/LU/LO -- a sanity check a wrong mapping would not
pass). Two entries were confirmed by corpus POSITION rather than shape alone: ``N``
(rare, always immediately after a vowel and before a consonant, e.g. ``hoN``) is the
MU TTUDDAG nasalization mark; ``|`` (206 occurrences, always sentence-final) is the OL
CHIKI PUNCTUATION MUCAAD danda-equivalent, whose raw pixel IoU against Noto's glyph was
misleadingly 0.0 (a 1-2px vertical bar shifted by a few pixels nets zero overlap) but
whose shape and position are unambiguous.

Coverage: 51 letter/mark bytes + 10 digits are CONFIRMED. Two bytes remain UNCERTAIN
(``n`` and ``T``, the two candidates left over after every better-matching Ol Chiki
codepoint was claimed by a stronger competitor) -- carried as best-guesses but NOT
applied unless the caller opts in, per the honest-uncertainty convention used
throughout this package (see ``sunuwar.py``). Twenty of the 26 upper/lowercase byte
pairs share an IDENTICAL glyph outline in the font (verified IoU=1.000 against each
other, not guessed) and so map to the same codepoint as their lowercase twin; only
``d/D h/H m/M n/N o/O t/T`` have genuinely different per-case outlines and were
derived independently. Uppercase ``W``/``X`` never occur in the source corpus but
their outline-identity with lowercase ``w``/``x`` was confirmed directly from the
font file, so they are mapped on that basis alone.

Scope: this module covers ONLY the 'Ol Chiki Optimum' body/heading font family
(Medium + ExtraBlack weights, verified outline-compatible with each other). The
'Ol Chiki Latic' display font family used for some headlines in the same documents is
a DIFFERENT, unverified glyph encoding (mean IoU only ~0.35-0.42 against Optimum on the
same bytes) and is explicitly OUT OF SCOPE -- do not assume this map applies to it.

Provenance / evidence: ocr-tech data/external-language-resources/native-script-real-
2026-07-06/ol-chiki/ (aale-chhatka-2023.pdf, aale-chhatka-september-2023.pdf).
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

OLCHIKI_LO, OLCHIKI_HI = 0x1C50, 0x1C7F

# ASCII punctuation the font renders as literal, unmodified glyphs (verified by
# rendering each candidate byte and comparing against a plain ASCII reference --
# these are NOT Ol Chiki shapes and pass through unchanged).
OLCHIKI_PASSTHROUGH: frozenset[str] = frozenset(
    {",", ".", "-", "'", "(", ")", '"', ":", ";", "?", "!", "~", "“", "”", "+"}
)


def _load_map_file(path: str | Path) -> tuple[dict[int, int], dict[int, int]]:
    map_path = Path(path)
    if not map_path.is_file():
        raise FileNotFoundError(f"Ol Chiki legacy map does not exist: {map_path}")
    raw = json.loads(map_path.read_text(encoding="utf-8"))
    confirmed = _parse_map_section(raw.get("map"), "map", map_path)
    uncertain = _parse_map_section(raw.get("uncertain_map"), "uncertain_map", map_path)
    return confirmed, uncertain


def _parse_map_section(
    entries: object, section_name: str, map_path: Path
) -> dict[int, int]:
    if not isinstance(entries, dict):
        raise ValueError(f"Ol Chiki map missing '{section_name}' object: {map_path}")
    table: dict[int, int] = {}
    for byte_hex, target in entries.items():
        try:
            byte = int(byte_hex, 16)
        except ValueError as exc:
            raise ValueError(f"invalid byte key in Ol Chiki map: {byte_hex!r}") from exc
        if not (0 <= byte <= 0x7F):
            raise ValueError(f"byte key out of ASCII range in Ol Chiki map: {byte_hex!r}")
        if not isinstance(target, list) or len(target) != 1:
            raise ValueError(
                f"Ol Chiki map target for byte {byte_hex} must be a single-codepoint list"
            )
        cp = int(target[0], 16)
        if not (OLCHIKI_LO <= cp <= OLCHIKI_HI):
            raise ValueError(
                f"Ol Chiki map target U+{cp:04X} outside Ol Chiki block for byte {byte_hex}"
            )
        table[byte] = cp
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
    already). By default only the CONFIRMED table is applied; set
    ``apply_uncertain=True`` to additionally apply the best-guess UNCERTAIN table
    (for exploration only -- never for ground-truth output).
    """

    def __init__(
        self,
        confirmed_map: dict[int, int],
        uncertain_map: dict[int, int] | None = None,
        *,
        apply_uncertain: bool = False,
    ) -> None:
        if not confirmed_map:
            raise ValueError("OLChikiConverter requires a non-empty confirmed map")
        self._confirmed = dict(confirmed_map)
        self._uncertain = dict(uncertain_map or {})
        self._apply_uncertain = apply_uncertain
        table = dict(self._confirmed)
        if apply_uncertain:
            table.update(self._uncertain)
        self._table = table

    @classmethod
    def from_map_file(cls, path: str | Path, *, apply_uncertain: bool = False) -> "OLChikiConverter":
        confirmed, uncertain = _load_map_file(path)
        return cls(confirmed, uncertain, apply_uncertain=apply_uncertain)

    @classmethod
    def default(cls, *, apply_uncertain: bool = False) -> "OLChikiConverter":
        with resources.as_file(
            resources.files("nepal_ttf2utf.maps") / "olck_optimum.json"
        ) as p:
            return cls.from_map_file(p, apply_uncertain=apply_uncertain)

    def convert(self, text: str) -> OLChikiConversion:
        out: list[str] = []
        replacements = 0
        confirmed = 0
        uncertain_seen: set[str] = set()
        unmapped: set[str] = set()
        for ch in text:
            if ch == " " or ch == "\n" or ch == "\t":
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
            if ch in OLCHIKI_PASSTHROUGH:
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


_DEFAULT: OLChikiConverter | None = None


def convert_olchiki(
    text: str, *, apply_uncertain: bool = False, strict: bool = False
) -> OLChikiConversion:
    """Convert 'Ol Chiki Optimum' legacy font text to Unicode Ol Chiki (NFC).

    Returns an :class:`OLChikiConversion`. The two uncertain bytes (``n``, ``T``) are
    left as-is and recorded in ``uncertain_bytes`` unless ``apply_uncertain=True``.
    Bytes that are neither confirmed letters/marks, digits, uncertain letters, nor
    known passthrough punctuation are surfaced in ``unmapped_bytes``. With
    ``strict=True`` the presence of any uncertain or unmapped byte raises
    ``ValueError`` instead of passing silently.
    """
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
            "unmapped/uncertain bytes after Ol Chiki conversion: " + " ".join(sorted(set(flagged)))
        )
    return result
