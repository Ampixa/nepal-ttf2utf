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

from .unicode_span import _is_assigned_script_codepoint

LEPCHA_LO, LEPCHA_HI = 0x1C00, 0x1C4F
_LEPCHA_CODEPOINT_RE = re.compile(r"[ᰀ-ᱏ]")
_BYTE_KEY_RE = re.compile(r"[0-9A-F]{2}")
_TARGET_KEY_RE = re.compile(r"[0-9A-F]{4}")
_FORBIDDEN_SOURCE_BYTES = frozenset(range(0x21)) | {0x7F}
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


class LepchaConverter:
    """Byte->Unicode converter for the Sikkim Herald live-text Lepcha body font.

    ``byte_map`` maps a single legacy byte value (the Latin code) to a nonempty ordered
    iterable of at most 256 assigned Lepcha codepoints. Conversion is a single byte pass
    (no multi-byte rules in this font) followed by a per-cluster reorder that (a) moves
    pre-base vowel signs after the base and (b) sorts the dependent signs into canonical
    Lepcha storage order.
    """

    def __init__(self, byte_map: Mapping[int, Iterable[int]]) -> None:
        if not isinstance(byte_map, Mapping) or not byte_map:
            raise ValueError("LepchaConverter requires a non-empty map")
        normalized: dict[int, tuple[int, ...]] = {}
        for raw_source, raw_target in byte_map.items():
            source = _validate_source_byte(raw_source)
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
        self._byte_map = normalized

    @classmethod
    def from_map_file(cls, path: str | Path) -> "LepchaConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"Lepcha legacy map does not exist: {map_path}")
        try:
            map_text = map_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"invalid UTF-8 in Lepcha legacy map {map_path}") from error
        try:
            raw = json.loads(map_text, object_pairs_hook=_unique_json_object)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"invalid JSON in Lepcha legacy map {map_path}: {error.msg}"
            ) from error
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
            if ch in " \t\r\n":
                out.append(ch)
                continue
            target = self._byte_map.get(code)
            if target is not None:
                out.extend(target)
                replacements += 1
            elif _is_assigned_script_codepoint(code, "Lepcha"):
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

    Returns a :class:`LepchaConversion`. Bytes outside the derived map, including the
    documented observed unresolved values, and Unicode values outside the pinned
    assigned Lepcha repertoire pass through and are surfaced in ``unmapped_bytes``.
    With ``strict=True`` any such leftover raises ``ValueError`` instead of passing
    silently.
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
