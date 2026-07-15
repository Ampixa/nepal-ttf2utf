"""Legacy ASCII Devanagari fonts -> Unicode Devanagari.

Builds on the tested ``npttf2utf`` font maps (Preeti, Kantipur, Sagarmatha, PCS Nepali,
Fontasy Himali) and adds:

- ``nayanepal`` / Gorkhapatra newspaper-font support (Preeti-family + extension glyphs
  ``ƒ``->र and ``†``->्), validated against real Gorkhapatra pages (97-99% clean
  Devanagari output, anchors गोरखापत्रद्वारा / प्रकाशित / नेपाल / मगर correct).
- whitespace + smart-punctuation normalization,
- a strict mode that surfaces leftover non-Devanagari bytes instead of silently dropping
  them (the failure mode of most legacy converters),
- pinned Unicode-17 Devanagari passthrough for mixed legacy/Unicode spans,
- optional Kiranti glottal-stop normalization to U+097D.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field

from ._controls import DIAGNOSTIC_C0
from .unicode_span import _is_assigned_script_codepoint

# Strip C0 values outside the package's structural allowlist. TAB, LF, and CR
# are data boundaries for multiline conversion, not font bytes.
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# nayanepal/Gorkhapatra extension glyphs not present in the base Preeti map.
_NAYANEPAL_EXT = {"ƒ": "र", "†": "्"}
# Cosmetic normalizations: narrow-no-break-space, smart quotes/dashes -> plain forms.
_PUNCT_NORMALIZE = {" ": " ", "‘": "'", "’": "'", "–": "-", "—": "-"}
_GROUP_REFERENCE_RE = re.compile(r"\\([1-9][0-9]*)")
_MappedToken = tuple[str, frozenset[int], frozenset[int]]

# Fonts handled directly by the bundled npttf2utf maps.
_NPTTF2UTF_FONTS = {
    "preeti": "Preeti",
    "kantipur": "Kantipur",
    "sagarmatha": "Sagarmatha",
    "pcs-nepali": "PCS NEPALI",
    "fontasy-himali": "FONTASY_HIMALI_TT",
}
# Fonts that are Preeti-family with extra extension glyphs.
_PREETI_FAMILY_EXT = {"nayanepal": _NAYANEPAL_EXT, "gorkhapatra": _NAYANEPAL_EXT}

_FONT_MAPPER = None


def _font_mapper():
    global _FONT_MAPPER
    if _FONT_MAPPER is None:
        import npttf2utf  # tested base maps

        path = os.path.join(os.path.dirname(npttf2utf.__file__), "map.json")
        _FONT_MAPPER = npttf2utf.FontMapper(path)
    return _FONT_MAPPER


@dataclass
class DevanagariConversion:
    legacy_text: str
    unicode_text: str
    clean: bool
    leftover: list[str] = field(default_factory=list)


def supported_devanagari_fonts() -> list[str]:
    return sorted(set(_NPTTF2UTF_FONTS) | set(_PREETI_FAMILY_EXT))


def _replacement_tokens(
    match: re.Match[str], replacement: str, tokens: list[_MappedToken]
) -> list[_MappedToken]:
    """Expand a dependency replacement while retaining source ownership."""
    matched_owners = frozenset(
        owner
        for _char, owners, _protected in tokens[match.start() : match.end()]
        for owner in owners
    )
    expanded: list[_MappedToken] = []
    position = 0
    for reference in _GROUP_REFERENCE_RE.finditer(replacement):
        expanded.extend(
            (char, matched_owners, frozenset())
            for char in replacement[position : reference.start()]
        )
        start, end = match.span(int(reference.group(1)))
        if start >= 0:
            expanded.extend(tokens[start:end])
        position = reference.end()
    expanded.extend((char, matched_owners, frozenset()) for char in replacement[position:])
    value = "".join(char for char, _owners, _protected in expanded)
    if value != match.expand(replacement):
        raise ValueError(f"unsupported npttf2utf replacement syntax: {replacement!r}")
    return expanded


def _apply_post_rule(
    tokens: list[_MappedToken], pattern: str, replacement: str
) -> list[frozenset[int]]:
    """Apply one regex rule and return source-owner sets erased by the rule."""
    value = "".join(char for char, _owners, _protected in tokens)
    matches = list(re.compile(pattern).finditer(value))
    deletion_events: list[frozenset[int]] = []
    for match in reversed(matches):
        expanded = _replacement_tokens(match, replacement, tokens)
        protected_before = sorted(
            owner
            for _char, _owners, protected in tokens[match.start() : match.end()]
            for owner in protected
        )
        protected_after = sorted(
            owner for _char, _owners, protected in expanded for owner in protected
        )
        if protected_before != protected_after:
            continue
        if match.start() != match.end() and not expanded:
            deletion_events.append(
                frozenset(
                    owner
                    for _char, owners, _protected in tokens[match.start() : match.end()]
                    for owner in owners
                )
            )
        tokens[match.start() : match.end()] = expanded
    return deletion_events


def _map_with_unicode_passthrough(text: str, *, base_font: str) -> tuple[str, set[str]]:
    """Apply dependency rules while protecting assigned Unicode Devanagari input."""
    mapper = _font_mapper()
    rules = mapper.all_rules[base_font]["rules"]
    if rules["pre-rules"]:
        raise ValueError("unsupported npttf2utf pre-rules prevent protected mapping")

    output: list[str] = []
    dropped: set[str] = set()
    split_pattern = re.compile(r"(\s+|\S+)")
    for word in re.findall(split_pattern, text):
        tokens: list[_MappedToken] = []
        for source_index, source in enumerate(word):
            owners = frozenset({source_index})
            if _is_assigned_script_codepoint(ord(source), "Devanagari"):
                tokens.append((source, owners, owners))
                continue
            target = rules["character-map"].get(source, source)
            if not target:
                dropped.add(source)
                continue
            tokens.extend((char, owners, frozenset()) for char in target)

        deletion_events: list[frozenset[int]] = []
        for pattern, replacement in rules["post-rules"]:
            deletion_events.extend(_apply_post_rule(tokens, pattern, replacement))
        surviving_owners = {owner for _char, owners, _protected in tokens for owner in owners}
        for event in deletion_events:
            if event.isdisjoint(surviving_owners):
                dropped.update(word[source_index] for source_index in event)
        mapped_word = "".join(char for char, _owners, _protected in tokens)
        output.append(mapped_word)
    return "".join(output), dropped


def convert_devanagari(
    text: str,
    font: str = "preeti",
    *,
    strict: bool = False,
    normalize_glottal_stop: bool = False,
) -> DevanagariConversion:
    """Convert a legacy Devanagari ASCII-font string to Unicode Devanagari (NFC)."""
    key = font.strip().lower()
    if key in _PREETI_FAMILY_EXT:
        base_font = "Preeti"
        ext = _PREETI_FAMILY_EXT[key]
    elif key in _NPTTF2UTF_FONTS:
        base_font = _NPTTF2UTF_FONTS[key]
        ext = {}
    else:
        raise ValueError(
            f"unsupported Devanagari font {font!r}; supported: {supported_devanagari_fonts()}"
        )

    out, dropped = _map_with_unicode_passthrough(_CTRL.sub("", text), base_font=base_font)
    for src, dst in ext.items():
        out = out.replace(src, dst)
    for src, dst in _PUNCT_NORMALIZE.items():
        out = out.replace(src, dst)
    if normalize_glottal_stop:
        # Kiranti/Rai glottal stop written as a colon-like mark -> DEVANAGARI LETTER
        # GLOTTAL STOP (U+097D). Opt-in: only meaningful for Kiranti orthographies.
        out = out.replace("ʻ", "ॽ")
    out = unicodedata.normalize("NFC", out)

    leftover = sorted(
        (
            {
                c
                for c in out
                if not _is_assigned_script_codepoint(ord(c), "Devanagari")
                and c not in " \t\r\n।॥,.?!:;'\"()[]-/0123456789"
            }
        )
        | dropped
        | (set(text) & DIAGNOSTIC_C0)
    )
    clean = not leftover
    if strict and not clean:
        raise ValueError(
            f"unmapped/leftover characters after {font} conversion: "
            + " ".join(f"U+{ord(c):04X}" for c in leftover)
        )
    return DevanagariConversion(legacy_text=text, unicode_text=out, clean=clean, leftover=leftover)
