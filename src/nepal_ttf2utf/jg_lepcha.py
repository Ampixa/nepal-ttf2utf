"""Jason Glavy's ``JG Lepcha`` legacy font -> Unicode Lepcha.

This converter applies SIL's two-pass TECkit map without requiring a TECkit
runtime. The byte pass handles classes, composite glyphs, and conjunct glyphs;
the Unicode pass reorders the font's visual-order vowel/final signs into Lepcha
logical order only when every participating scalar came from the legacy byte
pass. Pre-existing Unicode Lepcha and mixed-provenance windows are not custom
reordered. Three source rules explicitly marked uncertain by SIL emit the generic
U+25CC placeholder; their source values remain separate diagnostics.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass, field
from importlib import resources
from itertools import islice
from pathlib import Path
from types import MappingProxyType

from ._controls import diagnostic_c0_codepoints, require_boolean, require_text
from .unicode_span import _is_assigned_script_codepoint

LEPCHA_LO, LEPCHA_HI = 0x1C00, 0x1C4F
_DOTTED_CIRCLE = 0x25CC

_MAX_MAP_FILE_BYTES = 1_000_000
_MAX_MAP_LINES = 4_096
_MAX_MAP_LINE_CODEPOINTS = 4_096
_MAX_LOGICAL_LINE_CODEPOINTS = 4_096
_MAX_BYTE_RULES = 512
_MAX_BYTE_CLASSES = 128
_MAX_BYTE_CLASS_MEMBERS = 256
_MAX_SOURCE_LENGTH = 16
_MAX_TARGET_LENGTH = 32
_MAX_REORDER_RULES = 512
_MAX_REORDER_SLOTS = 16
_MAX_UNICODE_CLASSES = 128
_MAX_CLASS_MEMBERS = 1024
_STRUCTURAL_TEXT = frozenset(" \t\r\n")

_BYTE_TOKEN_RE = re.compile(r"0x([0-9A-Fa-f]{2})")
_UNI_TOKEN_RE = re.compile(r"U\+([0-9A-Fa-f]{4,6})")
_NAME = r"[A-Za-z][A-Za-z0-9_]*"
_BYTECLASS_RE = re.compile(rf"^ByteClass\s*\[({_NAME})\]\s*=\s*\((.*)\)\s*$")
_UNICLASS_RE = re.compile(rf"^UniClass\s*\[({_NAME})\]\s*=\s*\((.*)\)\s*$")
_PLAINCLASS_RE = re.compile(rf"^Class\s*\[({_NAME})\]\s*=\s*\((.*)\)\s*$")
_CLASS_RULE_RE = re.compile(rf"^\[({_NAME})\]\s*(?:<>|>)\s*\[({_NAME})\]\s*$")
_BOUND_CLASS_RE = re.compile(rf"\[({_NAME})\]\s*=\s*({_NAME})")
_VAR_REF_RE = re.compile(rf"@({_NAME})")
_PASS_RE = re.compile(r"^Pass\(\s*(Byte_Unicode|Unicode)\s*\)$", re.IGNORECASE)
_PASS_PREFIX_RE = re.compile(r"^Pass\b", re.IGNORECASE)
_HEADER_STRING_RE = re.compile(
    r'^(EncodingName|DescriptiveName|Version|Contact|RegistrationAuthority|RegistrationName)\s+"[^"]*"$'
)
_HEADER_PREFIX_RE = re.compile(
    r"^(?:EncodingName|DescriptiveName|Version|Contact|RegistrationAuthority|RegistrationName|RHSFlags)\b"
)
_RHS_FLAGS_RE = re.compile(r"^RHSFlags\s+\(ExpectsNFC\)$")
_EXPLICIT_RULE_RE = re.compile(
    r"^(?P<source>0x[0-9A-Fa-f]{2}(?:\s+0x[0-9A-Fa-f]{2})*)\s*"
    r"(?:<>|>)\s*"
    r"(?P<target>U\+[0-9A-Fa-f]{4,6}(?:\s+U\+[0-9A-Fa-f]{4,6})*)$"
)
_CONTEXT_RULE_RE = re.compile(
    rf"^0x([0-9A-Fa-f]{{2}})\s*/\s*\^\s*\[({_NAME})\]\s*_\s*>\s*"
    r"U\+([0-9A-Fa-f]{4,6})\s*$"
)
_REORDER_LEFT_RE = re.compile(rf"(?:\s*\[{_NAME}\]\s*=\s*{_NAME})+\s*")
_REORDER_RIGHT_RE = re.compile(rf"(?:\s*@{_NAME})+\s*")


def _tokens(body: str) -> list[str]:
    body = re.sub(r"\s*\.\.\s*", " .. ", body)
    return [token for token in body.split() if token]


def _validate_unicode_scalar(codepoint: object) -> int:
    if (
        isinstance(codepoint, bool)
        or not isinstance(codepoint, int)
        or not (0 <= codepoint <= 0x10FFFF)
        or 0xD800 <= codepoint <= 0xDFFF
    ):
        raise ValueError(f"invalid Unicode scalar in JG Lepcha map: {codepoint!r}")
    return codepoint


def _validate_byte(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= 0xFF):
        raise ValueError(f"invalid JG Lepcha {label} byte: {value!r}")
    return value


def _bounded_tuple(
    values: object, limit: int, label: str, *, reject_unordered: bool = False
) -> tuple[object, ...]:
    if isinstance(values, (str, bytes, Mapping)) or (reject_unordered and isinstance(values, Set)):
        raise ValueError(f"invalid JG Lepcha {label}")
    try:
        result = tuple(islice(iter(values), limit + 1))  # type: ignore[arg-type]
    except TypeError as error:
        raise ValueError(f"invalid JG Lepcha {label}") from error
    if len(result) > limit:
        raise ValueError(f"JG Lepcha {label} exceeds {limit} entries")
    return result


def _expand_byte_tokens(body: str) -> tuple[int, ...]:
    values: list[int] = []
    tokens = _tokens(body)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start_match = _BYTE_TOKEN_RE.fullmatch(token)
            end_match = _BYTE_TOKEN_RE.fullmatch(tokens[index + 2])
            if start_match is None or end_match is None:
                raise ValueError(
                    f"invalid byte range in JG Lepcha map: {token}..{tokens[index + 2]}"
                )
            start = int(start_match.group(1), 16)
            end = int(end_match.group(1), 16)
            if end < start:
                raise ValueError(
                    f"invalid byte range in JG Lepcha map: {token}..{tokens[index + 2]}"
                )
            if len(values) + end - start + 1 > _MAX_BYTE_CLASS_MEMBERS:
                raise ValueError(f"JG Lepcha byte class exceeds {_MAX_BYTE_CLASS_MEMBERS} members")
            values.extend(range(start, end + 1))
            index += 3
            continue
        if _BYTE_TOKEN_RE.fullmatch(token) is None:
            raise ValueError(f"unparseable byte token in JG Lepcha map: {token!r}")
        if len(values) == _MAX_BYTE_CLASS_MEMBERS:
            raise ValueError(f"JG Lepcha byte class exceeds {_MAX_BYTE_CLASS_MEMBERS} members")
        values.append(int(token, 16))
        index += 1
    if not values:
        raise ValueError("empty byte class in JG Lepcha map")
    if len(values) != len(set(values)):
        raise ValueError("duplicate member in JG Lepcha byte class")
    return tuple(values)


def _expand_uni_tokens(body: str, *, allow_duplicates: bool = False) -> tuple[int, ...]:
    values: list[int] = []
    tokens = _tokens(body)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start_match = _UNI_TOKEN_RE.fullmatch(token)
            end_match = _UNI_TOKEN_RE.fullmatch(tokens[index + 2])
            if start_match is None or end_match is None:
                raise ValueError(
                    f"invalid Unicode range in JG Lepcha map: {token}..{tokens[index + 2]}"
                )
            start = int(start_match.group(1), 16)
            end = int(end_match.group(1), 16)
            _validate_unicode_scalar(start)
            _validate_unicode_scalar(end)
            if end < start:
                raise ValueError(
                    f"invalid Unicode range in JG Lepcha map: {token}..{tokens[index + 2]}"
                )
            if start <= 0xDFFF and end >= 0xD800:
                raise ValueError(
                    f"invalid Unicode scalar range in JG Lepcha map: {token}..{tokens[index + 2]}"
                )
            if len(values) + end - start + 1 > _MAX_CLASS_MEMBERS:
                raise ValueError(f"JG Lepcha Unicode class exceeds {_MAX_CLASS_MEMBERS} members")
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _UNI_TOKEN_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable Unicode token in JG Lepcha map: {token!r}")
        if len(values) == _MAX_CLASS_MEMBERS:
            raise ValueError(f"JG Lepcha Unicode class exceeds {_MAX_CLASS_MEMBERS} members")
        values.append(_validate_unicode_scalar(int(match.group(1), 16)))
        index += 1
    if not values:
        raise ValueError("empty Unicode class in JG Lepcha map")
    if not allow_duplicates and len(values) != len(set(values)):
        raise ValueError("duplicate member in JG Lepcha Unicode class")
    return tuple(values)


def _parse_explicit_rule(line: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    match = _EXPLICIT_RULE_RE.fullmatch(line)
    if match is None:
        raise ValueError(f"invalid explicit JG Lepcha rule: {line!r}")
    source = tuple(
        _validate_byte(value, "source")
        for value in _bounded_tuple(
            (int(token.group(1), 16) for token in _BYTE_TOKEN_RE.finditer(match.group("source"))),
            _MAX_SOURCE_LENGTH,
            "source rule",
        )
    )
    target = tuple(
        _validate_unicode_scalar(value)
        for value in _bounded_tuple(
            (int(token.group(1), 16) for token in _UNI_TOKEN_RE.finditer(match.group("target"))),
            _MAX_TARGET_LENGTH,
            "target rule",
        )
    )
    return source, target


@dataclass(frozen=True)
class _ReorderRule:
    slots: tuple[tuple[str, str], ...]
    output_vars: tuple[str, ...]


@dataclass(frozen=True)
class _JGLepchaContract:
    byte_rules: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]
    reorder_rules: tuple[_ReorderRule, ...]
    unicode_classes: Mapping[str, frozenset[int]]
    context_rule: tuple[int, frozenset[int], int] | None
    uncertain_source_codepoints: frozenset[int]
    byte_precedence: str
    reorder_precedence: str
    source_domain: str
    pass_order: tuple[str, str]
    reorder_provenance: str


@dataclass(frozen=True)
class JGLepchaConversion:
    legacy_text: str
    unicode_text: str
    lepcha_char_count: int
    replacement_count: int
    unmapped_codepoints: list[str]
    uncertain_codepoints: list[str] = field(default_factory=list)


class JGLepchaConverter:
    """Native forward reader for SIL's ``JGLepcha.map``."""

    def __init__(
        self,
        byte_rules: Iterable[tuple[Iterable[int], Iterable[int]]],
        reorder_rules: Iterable[_ReorderRule],
        unicode_classes: Mapping[str, Iterable[int]],
        context_rule: tuple[int, Iterable[int], int] | None,
        uncertain_source_codepoints: Iterable[int] = frozenset(),
    ) -> None:
        raw_byte_rules = _bounded_tuple(
            byte_rules, _MAX_BYTE_RULES, "byte-rule sequence", reject_unordered=True
        )
        if not raw_byte_rules:
            raise ValueError("JGLepchaConverter requires at least one byte rule")
        normalized_byte_rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        seen_sources: set[tuple[int, ...]] = set()
        for raw_rule in raw_byte_rules:
            if isinstance(raw_rule, (str, bytes, Mapping, Set)):
                raise ValueError(f"invalid JG Lepcha byte rule: {raw_rule!r}")
            try:
                raw_source, raw_target = raw_rule  # type: ignore[misc]
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid JG Lepcha byte rule: {raw_rule!r}") from error
            source = tuple(
                _validate_byte(value, "source")
                for value in _bounded_tuple(
                    raw_source,
                    _MAX_SOURCE_LENGTH,
                    "source rule",
                    reject_unordered=True,
                )
            )
            target = tuple(
                _validate_unicode_scalar(value)
                for value in _bounded_tuple(
                    raw_target,
                    _MAX_TARGET_LENGTH,
                    "target rule",
                    reject_unordered=True,
                )
            )
            if not source:
                raise ValueError("empty JG Lepcha source rule")
            if not target:
                raise ValueError(f"empty JG Lepcha target rule for source: {source!r}")
            if source in seen_sources:
                label = " ".join(f"0x{value:02X}" for value in source)
                raise ValueError(f"duplicate JG Lepcha source rule: {label}")
            seen_sources.add(source)
            normalized_byte_rules.append((source, target))

            protected_source = next((value for value in source if value <= 0x20), None)
            if protected_source is not None:
                if source != (protected_source,) or target != (protected_source,):
                    raise ValueError(
                        "JG Lepcha C0 and SPACE sources must be singleton identity rules"
                    )

        for index, (source, _target) in enumerate(normalized_byte_rules):
            for other_source, _other_target in normalized_byte_rules[index + 1 :]:
                shorter, longer = sorted((source, other_source), key=len)
                if len(shorter) < len(longer) and longer[: len(shorter)] == shorter:
                    raise ValueError(
                        "prefix-conflicting JG Lepcha source rules: "
                        + " ".join(f"0x{value:02X}" for value in shorter)
                    )

        if not isinstance(unicode_classes, Mapping):
            raise ValueError("JG Lepcha Unicode classes must be a mapping")
        class_items = _bounded_tuple(
            unicode_classes.items(), _MAX_UNICODE_CLASSES, "Unicode class sequence"
        )
        normalized_classes: dict[str, frozenset[int]] = {}
        for raw_item in class_items:
            if isinstance(raw_item, (str, bytes, Mapping, Set)):
                raise ValueError(f"invalid JG Lepcha Unicode class entry: {raw_item!r}")
            try:
                name, raw_members = raw_item  # type: ignore[misc]
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid JG Lepcha Unicode class entry: {raw_item!r}") from error
            if not isinstance(name, str) or re.fullmatch(_NAME, name) is None:
                raise ValueError(f"invalid JG Lepcha Unicode class name: {name!r}")
            if name in normalized_classes:
                raise ValueError(f"duplicate JG Lepcha Unicode class: {name!r}")
            member_sequence = tuple(
                _validate_unicode_scalar(value)
                for value in _bounded_tuple(
                    raw_members, _MAX_CLASS_MEMBERS, f"class {name!r} members"
                )
            )
            if len(member_sequence) != len(set(member_sequence)):
                raise ValueError(f"duplicate member in JG Lepcha Unicode class: {name!r}")
            members = frozenset(member_sequence)
            if not members:
                raise ValueError(f"empty JG Lepcha Unicode class: {name!r}")
            if any(not _is_assigned_script_codepoint(value, "Lepcha") for value in members):
                raise ValueError(f"non-Lepcha member in JG Lepcha Unicode class: {name!r}")
            normalized_classes[name] = members

        raw_reorder_rules = _bounded_tuple(
            reorder_rules,
            _MAX_REORDER_RULES,
            "reorder-rule sequence",
            reject_unordered=True,
        )
        normalized_reorder_rules: list[_ReorderRule] = []
        reorder_patterns: dict[tuple[str, ...], tuple[int, ...]] = {}
        reorder_semantics: list[tuple[tuple[str, ...], tuple[int, ...]]] = []
        for raw_rule in raw_reorder_rules:
            if not isinstance(raw_rule, _ReorderRule):
                raise ValueError(f"invalid JG Lepcha reorder rule: {raw_rule!r}")
            raw_slots = _bounded_tuple(
                raw_rule.slots,
                _MAX_REORDER_SLOTS,
                "reorder slots",
                reject_unordered=True,
            )
            raw_output_vars = _bounded_tuple(
                raw_rule.output_vars,
                _MAX_REORDER_SLOTS,
                "reorder output",
                reject_unordered=True,
            )
            if not raw_slots or not raw_output_vars:
                raise ValueError("empty JG Lepcha reorder rule")
            slots: list[tuple[str, str]] = []
            for raw_slot in raw_slots:
                if isinstance(raw_slot, (str, bytes, Mapping, Set)):
                    raise ValueError(f"invalid JG Lepcha reorder slot: {raw_slot!r}")
                try:
                    class_name, variable = raw_slot  # type: ignore[misc]
                except (TypeError, ValueError) as error:
                    raise ValueError(f"invalid JG Lepcha reorder slot: {raw_slot!r}") from error
                if (
                    not isinstance(class_name, str)
                    or re.fullmatch(_NAME, class_name) is None
                    or not isinstance(variable, str)
                    or re.fullmatch(_NAME, variable) is None
                ):
                    raise ValueError(f"invalid JG Lepcha reorder slot: {raw_slot!r}")
                if class_name not in normalized_classes:
                    raise ValueError(
                        f"JG Lepcha reorder rule references unknown class: {class_name!r}"
                    )
                slots.append((class_name, variable))
            output_vars = tuple(raw_output_vars)
            if any(
                not isinstance(variable, str) or re.fullmatch(_NAME, variable) is None
                for variable in output_vars
            ):
                raise ValueError(f"invalid JG Lepcha reorder output: {output_vars!r}")
            bound_variables = tuple(variable for _class_name, variable in slots)
            if len(bound_variables) != len(set(bound_variables)):
                raise ValueError("duplicate variable binding in JG Lepcha reorder rule")
            if len(output_vars) != len(bound_variables) or set(output_vars) != set(bound_variables):
                raise ValueError(
                    "JG Lepcha reorder output must be a permutation of bound variables"
                )
            class_pattern = tuple(class_name for class_name, _variable in slots)
            permutation = tuple(bound_variables.index(variable) for variable in output_vars)
            previous_permutation = reorder_patterns.get(class_pattern)
            if previous_permutation is not None and previous_permutation != permutation:
                raise ValueError(f"conflicting JG Lepcha reorder pattern: {class_pattern!r}")
            for previous_pattern, previous_permutation in reorder_semantics:
                if len(previous_pattern) != len(class_pattern):
                    continue
                overlaps = all(
                    normalized_classes[previous_name] & normalized_classes[current_name]
                    for previous_name, current_name in zip(previous_pattern, class_pattern)
                )
                if overlaps and previous_permutation != permutation:
                    raise ValueError(
                        "conflicting overlapping JG Lepcha reorder patterns: "
                        f"{previous_pattern!r} and {class_pattern!r}"
                    )
            reorder_patterns[class_pattern] = permutation
            reorder_semantics.append((class_pattern, permutation))
            normalized_reorder_rules.append(_ReorderRule(tuple(slots), output_vars))

        uncertain_sequence = tuple(
            _validate_byte(value, "uncertain source")
            for value in _bounded_tuple(
                uncertain_source_codepoints, 256, "uncertain-source sequence"
            )
        )
        if len(uncertain_sequence) != len(set(uncertain_sequence)):
            raise ValueError("duplicate JG Lepcha uncertain source")
        uncertain = frozenset(uncertain_sequence)
        dotted_sources: set[int] = set()
        for source, target in normalized_byte_rules:
            if _DOTTED_CIRCLE in target:
                if target != (_DOTTED_CIRCLE,):
                    raise ValueError("U+25CC must be the sole JG Lepcha rule target")
                if len(source) != 1:
                    raise ValueError("U+25CC requires a singleton JG Lepcha source rule")
                dotted_sources.add(source[0])
            for codepoint in target:
                if _is_assigned_script_codepoint(codepoint, "Lepcha"):
                    continue
                if 0 <= codepoint <= 0x1F:
                    if source != (codepoint,) or target != (codepoint,):
                        raise ValueError(
                            "JG Lepcha C0 targets are allowed only as singleton identity rules"
                        )
                    continue
                if codepoint == 0x20:
                    if source not in {(0x20,), (0x2F,)} or target != (0x20,):
                        raise ValueError(
                            "JG Lepcha SPACE target is allowed only for source 0x20 or 0x2F"
                        )
                    continue
                if codepoint == _DOTTED_CIRCLE:
                    continue
                raise ValueError(f"invalid JG Lepcha rule target: U+{codepoint:04X}")
        if uncertain != dotted_sources:
            raise ValueError(
                "JG Lepcha uncertainty metadata must exactly match U+25CC source rules"
            )

        normalized_context: tuple[int, frozenset[int], int] | None = None
        if context_rule is not None:
            if not isinstance(context_rule, tuple) or len(context_rule) != 3:
                raise ValueError("invalid JG Lepcha context rule")
            trigger = _validate_byte(context_rule[0], "context trigger")
            if trigger <= 0x20:
                raise ValueError("JG Lepcha context trigger cannot be C0 or SPACE")
            excluded_sequence = tuple(
                _validate_byte(value, "context class")
                for value in _bounded_tuple(context_rule[1], 256, "context exclusion class")
            )
            if len(excluded_sequence) != len(set(excluded_sequence)):
                raise ValueError("duplicate byte in JG Lepcha context exclusion class")
            excluded = frozenset(excluded_sequence)
            replacement = _validate_unicode_scalar(context_rule[2])
            if not excluded:
                raise ValueError("empty JG Lepcha context exclusion class")
            if not _is_assigned_script_codepoint(replacement, "Lepcha"):
                raise ValueError(f"invalid JG Lepcha context target: U+{replacement:04X}")
            if (trigger,) not in seen_sources:
                raise ValueError("JG Lepcha context trigger requires a singleton fallback rule")
            normalized_context = (trigger, excluded, replacement)

        self._contract = _JGLepchaContract(
            byte_rules=tuple(
                sorted(normalized_byte_rules, key=lambda item: len(item[0]), reverse=True)
            ),
            reorder_rules=tuple(
                sorted(normalized_reorder_rules, key=lambda rule: len(rule.slots), reverse=True)
            ),
            unicode_classes=MappingProxyType(dict(normalized_classes)),
            context_rule=normalized_context,
            uncertain_source_codepoints=uncertain,
            byte_precedence="context-first-then-longest-source-first-stable",
            reorder_precedence="longest-pattern-first-stable",
            source_domain="byte-scalars",
            pass_order=("byte_unicode", "unicode"),
            reorder_provenance="legacy-byte-derived-only",
        )

    @property
    def _byte_rules(self) -> tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]:
        return self._contract.byte_rules

    @property
    def _reorder_rules(self) -> tuple[_ReorderRule, ...]:
        return self._contract.reorder_rules

    @property
    def _unicode_classes(self) -> Mapping[str, frozenset[int]]:
        return self._contract.unicode_classes

    @property
    def _context_rule(self) -> tuple[int, frozenset[int], int] | None:
        return self._contract.context_rule

    @property
    def _uncertain_source_codepoints(self) -> frozenset[int]:
        return self._contract.uncertain_source_codepoints

    @classmethod
    def from_map_file(cls, path: str | Path) -> "JGLepchaConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"JG Lepcha map does not exist: {map_path}")
        with map_path.open("rb") as stream:
            map_bytes = stream.read(_MAX_MAP_FILE_BYTES + 1)
        if len(map_bytes) > _MAX_MAP_FILE_BYTES:
            raise ValueError(f"JG Lepcha map exceeds {_MAX_MAP_FILE_BYTES} bytes")
        try:
            map_text = map_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError(f"invalid UTF-8 in JG Lepcha map {map_path}") from error
        physical_lines = map_text.splitlines()
        if len(physical_lines) > _MAX_MAP_LINES:
            raise ValueError(f"JG Lepcha map exceeds {_MAX_MAP_LINES} physical lines")
        if any(len(line) > _MAX_MAP_LINE_CODEPOINTS for line in physical_lines):
            raise ValueError(
                f"JG Lepcha physical line exceeds {_MAX_MAP_LINE_CODEPOINTS} codepoints"
            )

        logical_lines: list[tuple[str, str]] = []
        continued_code = ""
        continued_comments: list[str] = []
        continuation_pending = False
        for physical_line in physical_lines:
            code, separator, comment = physical_line.partition(";")
            stripped_code = code.rstrip()
            continues = stripped_code.endswith("\\")
            if continues:
                stripped_code = stripped_code[:-1].rstrip()
            continued_code = f"{continued_code} {stripped_code}".strip()
            if separator:
                continued_comments.append(comment)
            logical_length = len(continued_code) + sum(map(len, continued_comments))
            logical_length += max(0, len(continued_comments) - 1)
            logical_length += bool(continued_code and continued_comments)
            if logical_length > _MAX_LOGICAL_LINE_CODEPOINTS:
                raise ValueError(
                    "JG Lepcha reconstructed logical line exceeds "
                    f"{_MAX_LOGICAL_LINE_CODEPOINTS} codepoints"
                )
            if continues:
                continuation_pending = True
                continue
            logical_lines.append((continued_code, " ".join(continued_comments)))
            continued_code = ""
            continued_comments = []
            continuation_pending = False
        if continuation_pending:
            raise ValueError("dangling continuation in JG Lepcha map")

        byte_classes: dict[str, tuple[int, ...]] = {}
        unicode_classes_ordered: dict[str, tuple[int, ...]] = {}
        unicode_classes: dict[str, frozenset[int]] = {}
        byte_rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        reorder_rules: list[_ReorderRule] = []
        uncertain_source_codepoints: set[int] = set()
        current_pass = ""
        seen_passes: list[str] = []
        seen_headers: set[str] = set()
        context_rule: tuple[int, frozenset[int], int] | None = None

        for code, comment in logical_lines:
            line = code.strip()
            if not line:
                continue
            if _PASS_PREFIX_RE.match(line):
                pass_match = _PASS_RE.fullmatch(line)
                if pass_match is None:
                    raise ValueError(f"invalid JG Lepcha pass declaration: {line!r}")
                pass_name = pass_match.group(1).casefold()
                if pass_name in seen_passes:
                    raise ValueError(f"duplicate JG Lepcha pass declaration: {line!r}")
                if pass_name == "unicode" and seen_passes != ["byte_unicode"]:
                    raise ValueError("JG Lepcha Byte_Unicode pass must precede Unicode pass")
                if pass_name == "byte_unicode" and seen_passes:
                    raise ValueError("JG Lepcha Byte_Unicode pass must precede Unicode pass")
                seen_passes.append(pass_name)
                current_pass = pass_name
                continue
            if not current_pass:
                header_match = _HEADER_STRING_RE.fullmatch(line)
                if header_match is not None:
                    header_name = header_match.group(1)
                    if header_name in seen_headers:
                        raise ValueError(f"duplicate JG Lepcha header: {header_name}")
                    seen_headers.add(header_name)
                    continue
                if _RHS_FLAGS_RE.fullmatch(line):
                    if "RHSFlags" in seen_headers:
                        raise ValueError("duplicate JG Lepcha header: RHSFlags")
                    seen_headers.add("RHSFlags")
                    continue
                if _HEADER_PREFIX_RE.match(line):
                    raise ValueError(f"invalid JG Lepcha header declaration: {line!r}")
                raise ValueError(f"unsupported JG Lepcha pre-pass syntax: {line!r}")

            if current_pass == "byte_unicode":
                byte_match = _BYTECLASS_RE.fullmatch(line)
                if byte_match:
                    name = byte_match.group(1)
                    if name in byte_classes:
                        raise ValueError(f"duplicate JG Lepcha byte class: {name!r}")
                    if len(byte_classes) == _MAX_BYTE_CLASSES:
                        raise ValueError(
                            f"JG Lepcha byte classes exceed {_MAX_BYTE_CLASSES} entries"
                        )
                    byte_classes[name] = _expand_byte_tokens(byte_match.group(2))
                    continue
                unicode_match = _UNICLASS_RE.fullmatch(line)
                if unicode_match:
                    name = unicode_match.group(1)
                    if name in unicode_classes_ordered:
                        raise ValueError(f"duplicate JG Lepcha Unicode class: {name!r}")
                    if len(unicode_classes_ordered) == _MAX_UNICODE_CLASSES:
                        raise ValueError(
                            "JG Lepcha byte-pass Unicode classes exceed "
                            f"{_MAX_UNICODE_CLASSES} entries"
                        )
                    # Byte-pass classes are positional lookup tables. SIL's
                    # DepVow class intentionally maps two bytes to U+1C28.
                    unicode_classes_ordered[name] = _expand_uni_tokens(
                        unicode_match.group(2), allow_duplicates=True
                    )
                    continue
                context_match = _CONTEXT_RULE_RE.fullmatch(line)
                if context_match:
                    if context_rule is not None:
                        raise ValueError("multiple JG Lepcha context rules are unsupported")
                    class_name = context_match.group(2)
                    previous_bytes = byte_classes.get(class_name)
                    if previous_bytes is None:
                        raise ValueError(
                            f"context rule references unknown byte class: {class_name!r}"
                        )
                    context_rule = (
                        int(context_match.group(1), 16),
                        frozenset(previous_bytes),
                        _validate_unicode_scalar(int(context_match.group(3), 16)),
                    )
                    continue
                class_match = _CLASS_RULE_RE.fullmatch(line)
                if class_match:
                    left_name, right_name = class_match.groups()
                    left = byte_classes.get(left_name)
                    right = unicode_classes_ordered.get(right_name)
                    if left is None:
                        raise ValueError(f"unknown byte class in JG Lepcha rule: {left_name!r}")
                    if right is None:
                        raise ValueError(f"unknown Unicode class in JG Lepcha rule: {right_name!r}")
                    if len(left) != len(right):
                        raise ValueError(
                            f"JG Lepcha class length mismatch: [{left_name}] has {len(left)}, "
                            f"[{right_name}] has {len(right)}"
                        )
                    if len(byte_rules) + len(left) > _MAX_BYTE_RULES:
                        raise ValueError(
                            f"JG Lepcha byte-rule sequence exceeds {_MAX_BYTE_RULES} entries"
                        )
                    byte_rules.extend(
                        ((byte,), (codepoint,)) for byte, codepoint in zip(left, right)
                    )
                    continue
                source, target = _parse_explicit_rule(line)
                if len(byte_rules) == _MAX_BYTE_RULES:
                    raise ValueError(
                        f"JG Lepcha byte-rule sequence exceeds {_MAX_BYTE_RULES} entries"
                    )
                byte_rules.append((source, target))
                if "???" in comment and target == (_DOTTED_CIRCLE,):
                    uncertain_source_codepoints.update(source)
                continue

            if current_pass == "unicode":
                plain_match = _PLAINCLASS_RE.fullmatch(line)
                if plain_match:
                    name = plain_match.group(1)
                    if name in unicode_classes:
                        raise ValueError(f"duplicate JG Lepcha reorder class: {name!r}")
                    if len(unicode_classes) == _MAX_UNICODE_CLASSES:
                        raise ValueError(
                            f"JG Lepcha Unicode classes exceed {_MAX_UNICODE_CLASSES} entries"
                        )
                    members = _expand_uni_tokens(plain_match.group(2))
                    if any(
                        not _is_assigned_script_codepoint(codepoint, "Lepcha")
                        for codepoint in members
                    ):
                        raise ValueError(f"non-Lepcha member in JG Lepcha reorder class: {name!r}")
                    unicode_classes[name] = frozenset(members)
                    continue
                rule = cls._parse_reorder_rule(line)
                for class_name, _variable in rule.slots:
                    if class_name not in unicode_classes:
                        raise ValueError(
                            f"JG Lepcha reorder rule references unknown class: {class_name!r}"
                        )
                if len(reorder_rules) == _MAX_REORDER_RULES:
                    raise ValueError(
                        f"JG Lepcha reorder-rule sequence exceeds {_MAX_REORDER_RULES} entries"
                    )
                reorder_rules.append(rule)
                continue

            raise ValueError(f"unsupported JG Lepcha active pass: {current_pass!r}")

        if "byte_unicode" not in seen_passes:
            raise ValueError("JG Lepcha map is missing Pass(Byte_Unicode)")

        # Normalize and validate the parsed byte/reorder structures before
        # reporting a later missing pass. This keeps a malformed active rule
        # from being masked by an independently truncated map file.
        converter = cls(
            byte_rules,
            reorder_rules,
            unicode_classes,
            context_rule,
            frozenset(uncertain_source_codepoints),
        )

        if seen_passes != ["byte_unicode", "unicode"]:
            raise ValueError("JG Lepcha map is missing Pass(Unicode)")
        if not unicode_classes:
            raise ValueError("JG Lepcha Unicode pass requires at least one class")
        if not reorder_rules:
            raise ValueError("JG Lepcha Unicode pass requires at least one reorder rule")

        reachable_targets = {codepoint for _source, target in byte_rules for codepoint in target}
        if context_rule is not None:
            reachable_targets.add(context_rule[2])
        unreachable = set().union(*unicode_classes.values()) - reachable_targets
        if unreachable:
            labels = " ".join(f"U+{codepoint:04X}" for codepoint in sorted(unreachable))
            raise ValueError(f"unreachable JG Lepcha Unicode reorder class member: {labels}")

        return converter

    @classmethod
    def default(cls) -> "JGLepchaConverter":
        with resources.as_file(resources.files("nepal_ttf2utf.maps") / "JGLepcha.map") as path:
            return cls.from_map_file(path)

    @staticmethod
    def _parse_reorder_rule(line: str) -> _ReorderRule:
        if line.count("<>") != 1:
            raise ValueError(f"invalid JG Lepcha reorder rule: {line!r}")
        left, right = line.split("<>", 1)
        if _REORDER_LEFT_RE.fullmatch(left) is None or _REORDER_RIGHT_RE.fullmatch(right) is None:
            raise ValueError(f"invalid JG Lepcha reorder rule: {line!r}")
        slots = tuple(
            _bounded_tuple(
                ((match.group(1), match.group(2)) for match in _BOUND_CLASS_RE.finditer(left)),
                _MAX_REORDER_SLOTS,
                "reorder slots",
            )
        )
        output_vars = tuple(
            _bounded_tuple(
                (match.group(1) for match in _VAR_REF_RE.finditer(right)),
                _MAX_REORDER_SLOTS,
                "reorder output",
            )
        )
        bound_variables = tuple(variable for _name, variable in slots)
        if len(bound_variables) != len(set(bound_variables)):
            raise ValueError("duplicate variable binding in JG Lepcha reorder rule")
        if len(output_vars) != len(bound_variables) or set(output_vars) != set(bound_variables):
            raise ValueError("JG Lepcha reorder output must permute all bound variables")
        return _ReorderRule(slots, output_vars)

    @staticmethod
    def _matches(text: str, index: int, source: tuple[int, ...]) -> bool:
        return index + len(source) <= len(text) and all(
            ord(text[index + offset]) == codepoint for offset, codepoint in enumerate(source)
        )

    def _byte_pass_with_provenance(
        self, text: str
    ) -> tuple[str, tuple[bool, ...], int, list[str], list[str]]:
        output: list[str] = []
        derived: list[bool] = []
        unmapped: set[str] = set()
        uncertain: set[str] = set()
        replacements = 0
        index = 0
        while index < len(text):
            if self._context_rule is not None:
                trigger, excluded_previous, replacement = self._context_rule
                previous = ord(text[index - 1]) if index else None
                if ord(text[index]) == trigger and (
                    previous is None or previous not in excluded_previous
                ):
                    output.append(chr(replacement))
                    derived.append(True)
                    replacements += 1
                    index += 1
                    continue

            for source, target in self._byte_rules:
                if self._matches(text, index, source):
                    output.extend(chr(codepoint) for codepoint in target)
                    derived.extend([True] * len(target))
                    uncertain.update(
                        f"U+{codepoint:04X}"
                        for codepoint in source
                        if codepoint in self._uncertain_source_codepoints
                    )
                    replacements += 1
                    index += len(source)
                    break
            else:
                char = text[index]
                output.append(char)
                derived.append(False)
                codepoint = ord(char)
                if char not in _STRUCTURAL_TEXT and not _is_assigned_script_codepoint(
                    codepoint, "Lepcha"
                ):
                    unmapped.add(f"U+{codepoint:04X}")
                index += 1
        return (
            "".join(output),
            tuple(derived),
            replacements,
            sorted(unmapped),
            sorted(uncertain),
        )

    def _byte_pass(self, text: str) -> tuple[str, int, list[str], list[str]]:
        mapped, _derived, replacements, unmapped, uncertain = self._byte_pass_with_provenance(text)
        return mapped, replacements, unmapped, uncertain

    def _reorder_pass(self, text: str, derived: tuple[bool, ...] | None = None) -> str:
        if derived is None:
            derived = (True,) * len(text)
        if (
            type(derived) is not tuple
            or len(derived) != len(text)
            or any(type(value) is not bool for value in derived)
        ):
            raise ValueError("invalid JG Lepcha reorder provenance")
        output: list[str] = []
        index = 0
        while index < len(text):
            for rule in self._reorder_rules:
                if index + len(rule.slots) > len(text):
                    continue
                bound: dict[str, str] = {}
                for offset, (class_name, variable) in enumerate(rule.slots):
                    members = self._unicode_classes.get(class_name)
                    char = text[index + offset]
                    if members is None or ord(char) not in members:
                        break
                    bound[variable] = char
                else:
                    end = index + len(rule.slots)
                    if all(derived[index:end]):
                        output.extend(bound[variable] for variable in rule.output_vars)
                    else:
                        output.extend(text[index:end])
                    index = end
                    break
            else:
                output.append(text[index])
                index += 1
        return "".join(output)

    def convert(self, text: str) -> JGLepchaConversion:
        require_text(text)
        mapped, derived, replacements, unmapped, uncertain = self._byte_pass_with_provenance(text)
        converted = unicodedata.normalize("NFC", self._reorder_pass(mapped, derived))
        # The source CTL class maps every C0 value to itself. Preserve that
        # output/count behavior while diagnosing values outside the allowlist.
        unmapped = sorted(set(unmapped) | diagnostic_c0_codepoints(converted))
        return JGLepchaConversion(
            legacy_text=text,
            unicode_text=converted,
            lepcha_char_count=sum(LEPCHA_LO <= ord(char) <= LEPCHA_HI for char in converted),
            replacement_count=replacements,
            unmapped_codepoints=unmapped,
            uncertain_codepoints=uncertain,
        )


_DEFAULT: JGLepchaConverter | None = None


def convert_jg_lepcha(text: str, *, strict: bool = False) -> JGLepchaConversion:
    """Convert JG-Lepcha-encoded text to Unicode Lepcha (NFC)."""
    require_boolean(strict, "strict")
    require_text(text)
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = JGLepchaConverter.default()
    result = _DEFAULT.convert(text)
    if strict and result.uncertain_codepoints:
        flagged = sorted(set(result.unmapped_codepoints + result.uncertain_codepoints))
        message = "unmapped/uncertain characters after JG Lepcha conversion: " + " ".join(flagged)
        message += "; uncertain source glyphs map to placeholder U+25CC"
        raise ValueError(message)
    if strict and result.unmapped_codepoints:
        raise ValueError(
            "unmapped/leftover characters after JG Lepcha conversion: "
            + " ".join(result.unmapped_codepoints)
        )
    return result
