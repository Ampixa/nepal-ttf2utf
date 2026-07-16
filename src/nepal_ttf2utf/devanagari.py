"""Legacy ASCII Devanagari fonts -> Unicode Devanagari.

The five base maps come from the exact validated ``npttf2utf`` 0.3.7
dependency contract. NayaNepal and Gorkhapatra use the Preeti map plus two
project extension glyphs. Conversion preserves structural whitespace, reports
unresolved legacy values, protects assigned Unicode 17 Devanagari in mixed
input, and optionally normalizes the Kiranti glottal stop to U+097D.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from ._controls import DIAGNOSTIC_C0, require_boolean
from .unicode_span import _is_assigned_script_codepoint

# Strip C0 values outside the package's structural allowlist. TAB, LF, and CR
# are data boundaries for multiline conversion, not font bytes.
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_GROUP_REFERENCE_RE = re.compile(r"\\([1-9][0-9]*)")
_SPLIT_PATTERN = re.compile(r"\s+|\S+")
_STRUCTURAL_WHITESPACE = frozenset(" \t\r\n")
_MappedToken = tuple[str, frozenset[int], frozenset[int]]

_NPTTF2UTF_VERSION = "0.3.7"
_NPTTF2UTF_MAP_SIZE = 34_197
_NPTTF2UTF_MAP_SHA256 = "66a0a91f1209eb1c73540e443144f306d6daf27c426c09d24ec307a1506212e5"
_NPTTF2UTF_SEMANTIC_SIZE = 18_263
_NPTTF2UTF_SEMANTIC_SHA256 = "d908813c55a66726534a3d617cf4b13d0f94134e1e7d563ad5ab5dce9938313e"
_MAX_DEPENDENCY_MAP_BYTES = 1_000_000
_MAX_RULE_PATTERN_CODEPOINTS = 256
_MAX_RULE_REPLACEMENT_CODEPOINTS = 64
_MAX_CHARACTER_TARGET_CODEPOINTS = 16
_MAX_CHARACTER_MAP_ENTRIES = 256
_MAX_POST_RULES = 64
_MAX_LEGACY_SEGMENT_CODEPOINTS = 4_096

_EXPECTED_FONT_VERSIONS: Mapping[str, str] = MappingProxyType(
    {
        "Preeti": "v0.01",
        "FONTASY_HIMALI_TT": "v0.01",
        "Kantipur": "v0.01",
        "PCS NEPALI": "v0.1a",
        "Sagarmatha": "v0.1a",
    }
)

# NayaNepal/Gorkhapatra extension glyphs not present in the base Preeti map.
_NAYANEPAL_EXT: Mapping[str, str] = MappingProxyType({"ƒ": "र", "†": "्"})
# Cosmetic normalizations: narrow-no-break-space, smart quotes/dashes -> plain forms.
_PUNCT_NORMALIZE: Mapping[str, str] = MappingProxyType(
    {" ": " ", "‘": "'", "’": "'", "–": "-", "—": "-"}
)
_EMPTY_CHARACTER_MAP: Mapping[str, str] = MappingProxyType({})

# Public font keys handled by each dependency map.
_NPTTF2UTF_FONTS: Mapping[str, str] = MappingProxyType(
    {
        "preeti": "Preeti",
        "kantipur": "Kantipur",
        "sagarmatha": "Sagarmatha",
        "pcs-nepali": "PCS NEPALI",
        "fontasy-himali": "FONTASY_HIMALI_TT",
    }
)
# Fonts that are Preeti-family with extra extension glyphs.
_PREETI_FAMILY_EXT: Mapping[str, Mapping[str, str]] = MappingProxyType(
    {"nayanepal": _NAYANEPAL_EXT, "gorkhapatra": _NAYANEPAL_EXT}
)


@dataclass(frozen=True)
class _PostRule:
    pattern: str
    replacement: str
    compiled: re.Pattern[str]


@dataclass(frozen=True)
class _FontRuleContract:
    version: str
    character_map: Mapping[str, str]
    pre_rules: tuple[tuple[str, str], ...]
    post_rules: tuple[_PostRule, ...]


@dataclass(frozen=True)
class _DevanagariDependencyContract:
    dependency_version: str
    map_size: int
    map_sha256: str
    semantic_size: int
    semantic_sha256: str
    fonts: Mapping[str, _FontRuleContract]


_DEPENDENCY_CONTRACT: _DevanagariDependencyContract | None = None


def _contract_error(message: str) -> RuntimeError:
    return RuntimeError(f"invalid npttf2utf {_NPTTF2UTF_VERSION} map contract: {message}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _contract_error(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _is_scalar_text(value: str) -> bool:
    return all(not 0xD800 <= ord(character) <= 0xDFFF for character in value)


def _validate_post_rule(font_name: str, row_index: int, row: object) -> _PostRule:
    if (
        not isinstance(row, list)
        or len(row) != 2
        or not all(isinstance(value, str) for value in row)
    ):
        raise _contract_error(f"{font_name} post-rule {row_index} is not a string pair")
    pattern, replacement = row
    if not pattern or len(pattern) > _MAX_RULE_PATTERN_CODEPOINTS:
        raise _contract_error(f"{font_name} post-rule {row_index} pattern is out of bounds")
    if len(replacement) > _MAX_RULE_REPLACEMENT_CODEPOINTS:
        raise _contract_error(f"{font_name} post-rule {row_index} replacement is out of bounds")
    if not _is_scalar_text(pattern) or not _is_scalar_text(replacement):
        raise _contract_error(f"{font_name} post-rule {row_index} contains a surrogate")
    try:
        compiled = re.compile(pattern)
    except re.error as error:
        raise _contract_error(
            f"{font_name} post-rule {row_index} has an invalid pattern"
        ) from error
    empty_match = compiled.search("")
    if empty_match is not None and empty_match.start() == empty_match.end():
        raise _contract_error(f"{font_name} post-rule {row_index} can match empty text")
    literal_portion = _GROUP_REFERENCE_RE.sub("", replacement)
    if "\\" in literal_portion:
        raise _contract_error(
            f"{font_name} post-rule {row_index} uses unsupported replacement syntax"
        )
    references = [
        int(reference.group(1)) for reference in _GROUP_REFERENCE_RE.finditer(replacement)
    ]
    if any(reference > compiled.groups for reference in references):
        raise _contract_error(
            f"{font_name} post-rule {row_index} references a missing capture group"
        )
    return _PostRule(pattern=pattern, replacement=replacement, compiled=compiled)


def _semantic_payload(fonts: Mapping[str, _FontRuleContract]) -> bytes:
    def codepoints(value: str) -> list[int]:
        return [ord(character) for character in value]

    payload: list[object] = []
    for font_name in sorted(fonts):
        rules = fonts[font_name]
        payload.append(
            [
                font_name,
                rules.version,
                [
                    [codepoints(source), codepoints(target)]
                    for source, target in sorted(rules.character_map.items())
                ],
                [
                    [codepoints(pattern), codepoints(replacement)]
                    for pattern, replacement in rules.pre_rules
                ],
                [
                    [codepoints(rule.pattern), codepoints(rule.replacement)]
                    for rule in rules.post_rules
                ],
            ]
        )
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _parse_dependency_map(raw: bytes) -> _DevanagariDependencyContract:
    if len(raw) != _NPTTF2UTF_MAP_SIZE:
        raise _contract_error(f"map.json size is {len(raw)} bytes, expected {_NPTTF2UTF_MAP_SIZE}")
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    if raw_sha256 != _NPTTF2UTF_MAP_SHA256:
        raise _contract_error(f"map.json SHA-256 is {raw_sha256}")
    try:
        decoded = raw.decode("utf-8")
        document = json.loads(decoded, object_pairs_hook=_unique_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _contract_error("map.json is not valid UTF-8 JSON") from error
    if not isinstance(document, dict) or set(document) != set(_EXPECTED_FONT_VERSIONS):
        raise _contract_error("top-level font inventory differs from the pinned five maps")

    fonts: dict[str, _FontRuleContract] = {}
    for font_name, expected_version in _EXPECTED_FONT_VERSIONS.items():
        record = document[font_name]
        if not isinstance(record, dict) or set(record) != {"version", "rules"}:
            raise _contract_error(f"{font_name} record schema differs from the pinned schema")
        version = record["version"]
        rule_document = record["rules"]
        if version != expected_version:
            raise _contract_error(
                f"{font_name} version is {version!r}, expected {expected_version!r}"
            )
        if not isinstance(rule_document, dict) or set(rule_document) != {
            "character-map",
            "pre-rules",
            "post-rules",
        }:
            raise _contract_error(f"{font_name} rule schema differs from the pinned schema")

        character_document = rule_document["character-map"]
        if not isinstance(character_document, dict) or not (
            1 <= len(character_document) <= _MAX_CHARACTER_MAP_ENTRIES
        ):
            raise _contract_error(f"{font_name} character-map size is out of bounds")
        character_map: dict[str, str] = {}
        for source, target in character_document.items():
            if (
                not isinstance(source, str)
                or len(source) != 1
                or not _is_scalar_text(source)
                or not isinstance(target, str)
                or len(target) > _MAX_CHARACTER_TARGET_CODEPOINTS
                or not _is_scalar_text(target)
            ):
                raise _contract_error(f"{font_name} contains an invalid character-map entry")
            if source in _STRUCTURAL_WHITESPACE and target != source:
                raise _contract_error(f"{font_name} rewrites structural whitespace")
            if source not in _STRUCTURAL_WHITESPACE and any(
                character in _STRUCTURAL_WHITESPACE for character in target
            ):
                raise _contract_error(f"{font_name} introduces structural whitespace")
            character_map[source] = target

        pre_document = rule_document["pre-rules"]
        if pre_document != []:
            raise _contract_error(f"{font_name} has unsupported pre-rules")
        post_document = rule_document["post-rules"]
        if not isinstance(post_document, list) or not (1 <= len(post_document) <= _MAX_POST_RULES):
            raise _contract_error(f"{font_name} post-rule count is out of bounds")
        post_rules = tuple(
            _validate_post_rule(font_name, row_index, row)
            for row_index, row in enumerate(post_document)
        )
        if any(
            character in _STRUCTURAL_WHITESPACE
            for rule in post_rules
            for character in rule.replacement
        ):
            raise _contract_error(f"{font_name} post-rules introduce structural whitespace")
        fonts[font_name] = _FontRuleContract(
            version=version,
            character_map=MappingProxyType(character_map),
            pre_rules=(),
            post_rules=post_rules,
        )

    frozen_fonts: Mapping[str, _FontRuleContract] = MappingProxyType(fonts)
    semantic = _semantic_payload(frozen_fonts)
    semantic_sha256 = hashlib.sha256(semantic).hexdigest()
    if len(semantic) != _NPTTF2UTF_SEMANTIC_SIZE:
        raise _contract_error(
            f"semantic payload size is {len(semantic)}, expected {_NPTTF2UTF_SEMANTIC_SIZE}"
        )
    if semantic_sha256 != _NPTTF2UTF_SEMANTIC_SHA256:
        raise _contract_error(f"semantic payload SHA-256 is {semantic_sha256}")
    return _DevanagariDependencyContract(
        dependency_version=_NPTTF2UTF_VERSION,
        map_size=len(raw),
        map_sha256=raw_sha256,
        semantic_size=len(semantic),
        semantic_sha256=semantic_sha256,
        fonts=frozen_fonts,
    )


def _load_dependency_contract() -> _DevanagariDependencyContract:
    try:
        distribution = metadata.distribution("npttf2utf")
    except metadata.PackageNotFoundError as error:
        raise _contract_error("dependency is not installed") from error
    if distribution.version != _NPTTF2UTF_VERSION:
        raise _contract_error(
            f"installed version is {distribution.version!r}, expected {_NPTTF2UTF_VERSION!r}"
        )
    map_path = Path(str(distribution.locate_file("npttf2utf/map.json")))
    try:
        with map_path.open("rb") as stream:
            raw = stream.read(_MAX_DEPENDENCY_MAP_BYTES + 1)
    except OSError as error:
        raise _contract_error("map.json cannot be read") from error
    if len(raw) > _MAX_DEPENDENCY_MAP_BYTES:
        raise _contract_error("map.json exceeds the read bound")
    return _parse_dependency_map(raw)


def _dependency_contract() -> _DevanagariDependencyContract:
    global _DEPENDENCY_CONTRACT
    if _DEPENDENCY_CONTRACT is None:
        _DEPENDENCY_CONTRACT = _load_dependency_contract()
    return _DEPENDENCY_CONTRACT


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
        raise _contract_error(f"unsupported replacement syntax {replacement!r}")
    return expanded


def _apply_post_rule(tokens: list[_MappedToken], rule: _PostRule) -> list[frozenset[int]]:
    """Apply one regex rule and return source-owner sets erased by the rule."""
    value = "".join(char for char, _owners, _protected in tokens)
    matches = list(rule.compiled.finditer(value))
    deletion_events: list[frozenset[int]] = []
    for match in reversed(matches):
        expanded = _replacement_tokens(match, rule.replacement, tokens)
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


def _map_with_unicode_passthrough(
    text: str,
    *,
    base_font: str,
    extension_map: Mapping[str, str] = _EMPTY_CHARACTER_MAP,
) -> tuple[str, set[str]]:
    """Apply frozen dependency rules while protecting assigned Unicode input."""
    rules = _dependency_contract().fonts[base_font]

    output: list[str] = []
    dropped: set[str] = set()
    for word in _SPLIT_PATTERN.findall(text):
        if word.isspace():
            output.append(word)
            continue
        if len(word) > _MAX_LEGACY_SEGMENT_CODEPOINTS:
            raise ValueError(
                "legacy Devanagari non-whitespace source segment exceeds "
                f"{_MAX_LEGACY_SEGMENT_CODEPOINTS} codepoints"
            )
        tokens: list[_MappedToken] = []
        for source_index, source in enumerate(word):
            owners = frozenset({source_index})
            if _is_assigned_script_codepoint(ord(source), "Devanagari"):
                tokens.append((source, owners, owners))
                continue
            target = extension_map.get(source)
            if target is None:
                target = rules.character_map.get(source, source)
            if not target:
                dropped.add(source)
                continue
            tokens.extend((char, owners, frozenset()) for char in target)

        if len(tokens) > _MAX_LEGACY_SEGMENT_CODEPOINTS:
            raise ValueError(
                "legacy Devanagari mapped non-whitespace segment exceeds "
                f"{_MAX_LEGACY_SEGMENT_CODEPOINTS} codepoints"
            )

        deletion_events: list[frozenset[int]] = []
        for rule in rules.post_rules:
            deletion_events.extend(_apply_post_rule(tokens, rule))
            if len(tokens) > _MAX_LEGACY_SEGMENT_CODEPOINTS:
                raise ValueError(
                    "legacy Devanagari mapped non-whitespace segment exceeds "
                    f"{_MAX_LEGACY_SEGMENT_CODEPOINTS} codepoints"
                )
        surviving_owners = {owner for _char, owners, _protected in tokens for owner in owners}
        for event in deletion_events:
            if event.isdisjoint(surviving_owners):
                dropped.update(word[owner] for owner in event)
        output.append("".join(char for char, _owners, _protected in tokens))
    return "".join(output), dropped


def convert_devanagari(
    text: str,
    font: str = "preeti",
    *,
    strict: bool = False,
    normalize_glottal_stop: bool = False,
) -> DevanagariConversion:
    """Convert a legacy Devanagari ASCII-font string to Unicode Devanagari (NFC)."""
    require_boolean(strict, "strict")
    require_boolean(normalize_glottal_stop, "Devanagari normalize_glottal_stop")
    key = font.strip().lower()
    if key in _PREETI_FAMILY_EXT:
        base_font = "Preeti"
        extension_map = _PREETI_FAMILY_EXT[key]
    elif key in _NPTTF2UTF_FONTS:
        base_font = _NPTTF2UTF_FONTS[key]
        extension_map = _EMPTY_CHARACTER_MAP
    else:
        raise ValueError(
            f"unsupported Devanagari font {font!r}; supported: {supported_devanagari_fonts()}"
        )

    out, dropped = _map_with_unicode_passthrough(
        _CTRL.sub("", text), base_font=base_font, extension_map=extension_map
    )
    for source, target in _PUNCT_NORMALIZE.items():
        out = out.replace(source, target)
    if normalize_glottal_stop:
        # Kiranti/Rai glottal stop written as a colon-like mark -> DEVANAGARI LETTER
        # GLOTTAL STOP (U+097D). Opt-in: only meaningful for Kiranti orthographies.
        out = out.replace("ʻ", "ॽ")
    out = unicodedata.normalize("NFC", out)

    leftover = sorted(
        (
            {
                character
                for character in out
                if not _is_assigned_script_codepoint(ord(character), "Devanagari")
                and character not in " \t\r\n।॥,.?!:;'\"()[]-/0123456789"
            }
        )
        | dropped
        | (set(text) & DIAGNOSTIC_C0)
    )
    clean = not leftover
    if strict and not clean:
        raise ValueError(
            f"unmapped/leftover characters after {font} conversion: "
            + " ".join(f"U+{ord(character):04X}" for character in leftover)
        )
    return DevanagariConversion(legacy_text=text, unicode_text=out, clean=clean, leftover=leftover)
