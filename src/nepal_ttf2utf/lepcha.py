"""Sikkim Herald live-text Lepcha (Róng) font -> Unicode Lepcha (U+1C00-U+1C4F).

A cluster of 2021-2022 Sikkim Herald editions typeset the Lepcha body as live text
using an anonymised CFF-subset font family (PDF FontName ``TT<hex>O00``). The named
body layout (``TT21B1O00`` / ``TT106DO00`` / ``TTDA7O00`` / ``TT70AO00`` — verified
outline-identical across the four editions) shares ONE byte->glyph layout. The byte->
glyph code is the *identity Latin* encoding (byte 0x56 'V' draws the glyph named "V"),
but the glyph OUTLINE is a Lepcha letter, not a Latin V — so the recoverable PDF "text"
is Latin garbage and the real content lives in the glyph shapes. (This is a DIFFERENT
font from Jason Glavy's JG Lepcha; SIL's JG map decodes a different layout and yields
unfaithful output here.)

The map (``maps/sikkim_herald_lepcha.json``) was derived by GLYPH-SHAPE IDENTITY: each
body-font glyph was rendered and shape-matched (NCC/IoU) against the assigned Lepcha
codepoints in Noto Sans Lepcha + Mingzat, anchored on the alphabetic consonant series
(uppercase Latin A.. -> the Lepcha base consonants in Unicode order) and confirmed by
positional statistics + round-trip rendering against the printed crops.

Structure handled: base consonants, LA-conjuncts, the independent vowel A, PRE-BASE
dependent vowel signs (I/O/OO — keyed to the LEFT of their base in the legacy stream,
reordered after the base for Unicode storage), post-base vowel signs, final consonant
signs, RAN/NUKTA, and digits. Output is NFC in canonical Lepcha storage order
``C (subjoined) (vowel) (final) (ran)``.

The legacy ``]`` glyph is final K stored visually before the following base; it is
reordered with the pre-base vowels. ``%`` is subjoined RA, including the documented
NUKTA+RA retroflex sequences. A small set of rare bytes remains deliberately
unresolved and is surfaced in ``unmapped_bytes`` (or raised in ``strict`` mode).
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

LEPCHA_LO, LEPCHA_HI = 0x1C00, 0x1C4F
_LEPCHA_CODEPOINT_RE = re.compile(r"[ᰀ-ᱏ]")

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
_BASES = frozenset(
    list(range(0x1C00, 0x1C24)) + [0x1C4D, 0x1C4E, 0x1C4F]
)  # consonants + independent vowel A + TTA/TTHA/DDA


@dataclass(frozen=True)
class LepchaConversion:
    legacy_text: str
    unicode_text: str
    lepcha_char_count: int
    replacement_count: int
    unmapped_bytes: list[str]


class LepchaConverter:
    """Byte->Unicode converter for the Sikkim Herald live-text Lepcha body font.

    ``byte_map`` maps a single legacy byte value (the Latin code) to a tuple of Lepcha
    codepoints. Conversion is a single byte pass (no multi-byte rules in this font)
    followed by a per-cluster reorder that (a) moves pre-base vowel signs after the base
    and (b) sorts the dependent signs into canonical Lepcha storage order.
    """

    def __init__(self, byte_map: dict[int, tuple[int, ...]]) -> None:
        if not byte_map:
            raise ValueError("LepchaConverter requires a non-empty map")
        self._byte_map = dict(byte_map)

    @classmethod
    def from_map_file(cls, path: str | Path) -> "LepchaConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"Lepcha legacy map does not exist: {map_path}")
        raw = json.loads(map_path.read_text(encoding="utf-8"))
        entries = raw.get("map")
        if not isinstance(entries, dict):
            raise ValueError(f"Lepcha legacy map missing 'map' object: {map_path}")
        byte_map: dict[int, tuple[int, ...]] = {}
        for byte_hex, target in entries.items():
            try:
                b = int(byte_hex, 16)
            except ValueError as exc:
                raise ValueError(f"invalid byte key in Lepcha map: {byte_hex!r}") from exc
            if not (0 <= b <= 0xFF):
                raise ValueError(f"byte key out of range in Lepcha map: {byte_hex!r}")
            cps = tuple(int(u, 16) for u in target)
            for cp in cps:
                if not (LEPCHA_LO <= cp <= LEPCHA_HI):
                    raise ValueError(
                        f"Lepcha map target U+{cp:04X} outside Lepcha block for byte {byte_hex}"
                    )
            byte_map[b] = cps
        return cls(byte_map)

    @classmethod
    def default(cls) -> "LepchaConverter":
        with resources.as_file(
            resources.files("nepal_ttf2utf.maps") / "sikkim_herald_lepcha.json"
        ) as p:
            return cls.from_map_file(p)

    # ----- byte pass -----------------------------------------------------------

    def _byte_pass(self, text: str) -> tuple[list[int | str], int, list[str]]:
        """Map each input char (legacy byte) to codepoints; pass spaces through.

        Returns a token list where ints are Lepcha codepoints and str tokens are
        verbatim pass-through characters (spaces, untouched ASCII).
        """
        out: list[int | str] = []
        unmapped: list[str] = []
        replacements = 0
        for ch in text:
            code = ord(ch)
            if ch == " " or ch == "\n" or ch == "\t":
                out.append(ch)
                continue
            target = self._byte_map.get(code)
            if target is not None:
                out.extend(target)
                replacements += 1
            elif LEPCHA_LO <= code <= LEPCHA_HI:
                # Preserve genuine Unicode Lepcha mixed into a legacy run. Keeping
                # this as a string token also prevents the legacy visual-order pass
                # from reinterpreting already-logical Unicode input.
                out.append(ch)
            elif ch in LEPCHA_PASSTHROUGH:
                out.append(ch)
            else:
                # Unmapped legacy byte (layout/punctuation glyph not in the map).
                out.append(ch)
                unmapped.append(f"0x{code:02X}" if code <= 0xFF else f"U+{code:04X}")
        return out, replacements, unmapped

    # ----- reorder pass --------------------------------------------------------

    @staticmethod
    def _canonical_cluster(base: int, signs: list[int]) -> list[int]:
        """Order a base + its dependent signs into canonical Lepcha storage order.

        Order per The Unicode Standard ch.13 Table 13-9: base, nukta,
        subjoined (RA before YA), vowel sign, final consonant sign, RAN.
        """
        subjoined = [s for s in signs if s in _SUBJOINED]
        nukta = [s for s in signs if s == _NUKTA]
        vowels = [s for s in signs if s in _VOWEL_SIGNS]
        finals = [s for s in signs if s in _FINAL_SIGNS]
        ran = [s for s in signs if s == _RAN]
        other = [
            s
            for s in signs
            if s not in _SUBJOINED
            and s != _NUKTA
            and s not in _VOWEL_SIGNS
            and s not in _FINAL_SIGNS
            and s != _RAN
        ]
        # Table 13-9 medial order is RA then YA (RA=1C25, YA=1C24), i.e.
        # descending codepoint order for the two subjoined marks.
        subjoined.sort(reverse=True)
        return [base] + nukta + subjoined + vowels + finals + ran + other

    def _reorder(self, tokens: list[int | str]) -> list[int | str]:
        """Reorder visual-order codepoint runs into logical Lepcha clusters.

        A syllable begins with optional visually leading signs: I/O/OO and final K,
        all keyed left of the base in the legacy stream. Each syllable is emitted in
        canonical storage order. A trailing sign-run stops at the next visually
        leading sign, which begins the next syllable.
        """
        out: list[int | str] = []
        i = 0
        n = len(tokens)
        while i < n:
            tok = tokens[i]
            if isinstance(tok, str):
                out.append(tok)
                i += 1
                continue

            # Collect visually leading vowel/final signs for the upcoming base.
            pre: list[int] = []
            while (
                i < n
                and isinstance(tokens[i], int)
                and (tokens[i] in PRE_BASE_VOWELS or tokens[i] in VISUAL_LEADING_FINALS)
                and tokens[i] not in _BASES
            ):
                pre.append(tokens[i])  # type: ignore[arg-type]
                i += 1

            if i >= n or not isinstance(tokens[i], int):
                # No base follows the pre-vowel(s); emit them verbatim (degenerate).
                out.extend(pre)
                continue

            cur = tokens[i]
            if cur not in _BASES:
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
                and isinstance(tokens[i], int)
                and tokens[i] not in _BASES
                and tokens[i] not in PRE_BASE_VOWELS
                and tokens[i] not in VISUAL_LEADING_FINALS
            ):
                post.append(tokens[i])  # type: ignore[arg-type]
                i += 1
            out.extend(self._canonical_cluster(base, pre + post))
        return out

    # ----- public --------------------------------------------------------------

    def convert(self, text: str) -> LepchaConversion:
        tokens, replacements, unmapped = self._byte_pass(text)
        reordered = self._reorder(tokens)
        chars = []
        for t in reordered:
            chars.append(chr(t) if isinstance(t, int) else t)
        converted = unicodedata.normalize("NFC", "".join(chars))
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

    Returns a :class:`LepchaConversion`. Bytes outside the derived map (the small set
    of deliberately-unresolved rare bytes) pass through and are
    surfaced in ``unmapped_bytes``. With ``strict=True`` any such leftover raises
    ``ValueError`` instead of passing silently.
    """
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = LepchaConverter.default()
    result = _DEFAULT.convert(text)
    if strict and result.unmapped_bytes:
        raise ValueError(
            "unmapped/leftover bytes after Lepcha conversion: " + " ".join(result.unmapped_bytes)
        )
    return result
