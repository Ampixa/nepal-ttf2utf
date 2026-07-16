"""Limbu/Sirijonga legacy-font (Namdhinggo SIL) -> Unicode Limbu (U+1900-U+194F).

Applies the forward explicit assignments from the SIL TECkit ``Byte_Unicode`` pass,
including positional class rules, in the vendored ``Limbu.map``. It also applies the
vowel / subjoined-consonant reordering that Unicode logical order requires, limited to
scalars emitted by the legacy byte pass. Pre-existing Unicode Limbu and mixed-provenance
windows are not custom reordered.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from importlib import resources
from itertools import islice
from pathlib import Path

from ._controls import diagnostic_c0_codepoints, require_boolean, require_integer, require_text
from .unicode_span import _is_assigned_script_codepoint

_BYTE_RULE_RE = re.compile(r"0x([0-9A-Fa-f]{2})")
_UNICODE_RULE_RE = re.compile(r"U\+([0-9A-Fa-f]{4,6})")
_CLASS_IDENTIFIER = r"[A-Za-z][A-Za-z0-9_]*"
_CLASS_NAME_RE = re.compile(_CLASS_IDENTIFIER)
_BYTECLASS_RE = re.compile(r"^ByteClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_UNICLASS_RE = re.compile(r"^UniClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_CLASS_RULE_RE = re.compile(r"^\[([^\]]+)\]\s*<?>\s*\[([^\]]+)\]\s*$")
_PASS_RE = re.compile(r"^Pass\(\s*(Byte_Unicode|Unicode)\s*\)$", re.IGNORECASE)
_PASS_PREFIX_RE = re.compile(r"^Pass\b", re.IGNORECASE)
_BYTE_DEFAULT_RE = re.compile(r"^ByteDefault\s+0x5E$", re.IGNORECASE)
_UNI_DEFAULT_RE = re.compile(r"^UniDefault\s+replacement_character$", re.IGNORECASE)
_DEFAULT_PREFIX_RE = re.compile(r"^(?:ByteDefault|UniDefault)\b", re.IGNORECASE)
_HEADER_STRING_RE = re.compile(
    r"^(EncodingName|DescriptiveName|Version|Contact|RegistrationAuthority|"
    r'RegistrationName|Copyright)\s+"[^"]*"$'
)
_HEADER_PREFIX_RE = re.compile(
    r"^(?:EncodingName|DescriptiveName|Version|Contact|RegistrationAuthority|"
    r"RegistrationName|Copyright)\b"
)
_EXPLICIT_RULE_RE = re.compile(
    r"^(?P<source>0x[0-9A-Fa-f]{2}(?:\s+0x[0-9A-Fa-f]{2})*)\s*"
    r"(?:<>|>)\s*"
    r"(?P<target>U\+[0-9A-Fa-f]{4,6}(?:\s+U\+[0-9A-Fa-f]{4,6})*)$"
)
_REORDER_PAIR_RE = re.compile(
    rf"^\[(?P<first_class>{_CLASS_IDENTIFIER})\]="
    rf"(?P<first_var>{_CLASS_IDENTIFIER})\s+"
    rf"\[(?P<second_class>{_CLASS_IDENTIFIER})\]="
    rf"(?P<second_var>{_CLASS_IDENTIFIER})\s*"
    rf"<>\s*@(?P<output_first>{_CLASS_IDENTIFIER})\s+"
    rf"@(?P<output_second>{_CLASS_IDENTIFIER})$"
)
_REORDER_TRIPLE_RE = re.compile(
    rf"^\[(?P<first_class>{_CLASS_IDENTIFIER})\]="
    rf"(?P<first_var>{_CLASS_IDENTIFIER})\s+"
    r"U\+(?P<input_literal>[0-9A-Fa-f]{4,6})\s+"
    rf"\[(?P<second_class>{_CLASS_IDENTIFIER})\]="
    rf"(?P<second_var>{_CLASS_IDENTIFIER})\s*"
    rf"<>\s*@(?P<output_first>{_CLASS_IDENTIFIER})\s+"
    rf"@(?P<output_second>{_CLASS_IDENTIFIER})\s+"
    r"U\+(?P<output_literal>[0-9A-Fa-f]{4,6})$"
)
_LIMBU_CODEPOINT_RE = re.compile(r"[ᤀ-᥏]")
_MAX_MAP_FILE_BYTES = 1_000_000
_MAX_MAP_LINES = 4_096
_MAX_MAP_LINE_CODEPOINTS = 4_096
_MAX_BYTE_RULES = 512
_MAX_BYTE_CLASSES = 128
_MAX_UNICODE_CLASSES = 128
_MAX_BYTE_CLASS_MEMBERS = 256
_MAX_UNICODE_CLASS_MEMBERS = 1_024
_MAX_SOURCE_LENGTH = 16
_MAX_TARGET_LENGTH = 32
_STRUCTURAL_TEXT = frozenset(" \t\r\n")
_VOWELS = frozenset(range(0x1920, 0x1929))
_SUBJOINED = frozenset(range(0x1929, 0x192C))
_KEMPHRENG = 0x193A


def _tokens(body: str) -> list[str]:
    body = re.sub(r"\s*\.\.\s*", " .. ", body)
    return [token for token in body.split() if token]


def _validate_unicode_scalar(codepoint: object) -> int:
    codepoint = require_integer(codepoint, "invalid Unicode scalar in Limbu map")
    if not (0 <= codepoint <= 0x10FFFF) or 0xD800 <= codepoint <= 0xDFFF:
        raise ValueError(f"invalid Unicode scalar in Limbu map: {codepoint!r}")
    return codepoint


def _validate_byte(value: object) -> int:
    value = require_integer(value, "invalid Limbu source byte")
    if not (0 <= value <= 0xFF):
        raise ValueError(f"invalid Limbu source byte: {value!r}")
    return value


def _bounded_tuple(
    values: object, limit: int, label: str, *, reject_unordered: bool = False
) -> tuple[object, ...]:
    if isinstance(values, (str, bytes, Mapping)) or (reject_unordered and isinstance(values, Set)):
        raise ValueError(f"invalid Limbu {label}")
    try:
        result = tuple(islice(iter(values), limit + 1))  # type: ignore[call-overload]
    except TypeError as error:
        raise ValueError(f"invalid Limbu {label}") from error
    if len(result) > limit:
        raise ValueError(f"Limbu {label} exceeds {limit} entries")
    return result


def _bounded_contract_tuple(
    values: object, limit: int, label: str, *, reject_unordered: bool = False
) -> tuple[object, ...]:
    if isinstance(values, (str, bytes, Mapping)) or (reject_unordered and isinstance(values, Set)):
        raise ValueError(f"invalid Limbu {label}")
    try:
        result = tuple(islice(iter(values), limit + 1))  # type: ignore[call-overload]
    except Exception as error:
        if isinstance(error, (MemoryError, RecursionError)):
            raise
        raise ValueError(f"invalid Limbu {label}") from error
    if len(result) > limit:
        raise ValueError(f"Limbu {label} exceeds {limit} entries")
    return result


def _expand_byte_tokens(body: str) -> tuple[int, ...]:
    values: list[int] = []
    tokens = _tokens(body)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start_match = _BYTE_RULE_RE.fullmatch(token)
            end_match = _BYTE_RULE_RE.fullmatch(tokens[index + 2])
            if start_match is None or end_match is None:
                raise ValueError(f"invalid byte range in Limbu map: {token}..{tokens[index + 2]}")
            start = int(start_match.group(1), 16)
            end = int(end_match.group(1), 16)
            if end < start:
                raise ValueError(f"invalid byte range in Limbu map: {token}..{tokens[index + 2]}")
            if len(values) + end - start + 1 > _MAX_BYTE_CLASS_MEMBERS:
                raise ValueError(f"Limbu byte class exceeds {_MAX_BYTE_CLASS_MEMBERS} members")
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _BYTE_RULE_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable byte token in Limbu map: {token!r}")
        if len(values) == _MAX_BYTE_CLASS_MEMBERS:
            raise ValueError(f"Limbu byte class exceeds {_MAX_BYTE_CLASS_MEMBERS} members")
        values.append(int(match.group(1), 16))
        index += 1
    if not values:
        raise ValueError("empty byte class in Limbu map")
    if len(values) != len(set(values)):
        raise ValueError("duplicate member in Limbu byte class")
    return tuple(values)


def _expand_unicode_tokens(body: str) -> tuple[int, ...]:
    values: list[int] = []
    tokens = _tokens(body)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start_match = _UNICODE_RULE_RE.fullmatch(token)
            end_match = _UNICODE_RULE_RE.fullmatch(tokens[index + 2])
            if start_match is None or end_match is None:
                raise ValueError(
                    f"invalid Unicode range in Limbu map: {token}..{tokens[index + 2]}"
                )
            start = _validate_unicode_scalar(int(start_match.group(1), 16))
            end = _validate_unicode_scalar(int(end_match.group(1), 16))
            if end < start:
                raise ValueError(
                    f"invalid Unicode range in Limbu map: {token}..{tokens[index + 2]}"
                )
            if start <= 0xDFFF and end >= 0xD800:
                raise ValueError(
                    f"invalid Unicode scalar range in Limbu map: {token}..{tokens[index + 2]}"
                )
            if len(values) + end - start + 1 > _MAX_UNICODE_CLASS_MEMBERS:
                raise ValueError(
                    f"Limbu Unicode class exceeds {_MAX_UNICODE_CLASS_MEMBERS} members"
                )
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _UNICODE_RULE_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable Unicode token in Limbu map: {token!r}")
        if len(values) == _MAX_UNICODE_CLASS_MEMBERS:
            raise ValueError(f"Limbu Unicode class exceeds {_MAX_UNICODE_CLASS_MEMBERS} members")
        values.append(_validate_unicode_scalar(int(match.group(1), 16)))
        index += 1
    if not values:
        raise ValueError("empty Unicode class in Limbu map")
    if len(values) != len(set(values)):
        raise ValueError("duplicate member in Limbu Unicode class")
    return tuple(values)


def _parse_explicit_rule(line: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    match = _EXPLICIT_RULE_RE.fullmatch(line)
    if match is None:
        raise ValueError(f"invalid explicit Limbu rule: {line!r}")
    source = tuple(
        _validate_byte(value)
        for value in _bounded_tuple(
            (int(token.group(1), 16) for token in _BYTE_RULE_RE.finditer(match.group("source"))),
            _MAX_SOURCE_LENGTH,
            "source rule",
        )
    )
    target = tuple(
        _validate_unicode_scalar(value)
        for value in _bounded_tuple(
            (int(token.group(1), 16) for token in _UNICODE_RULE_RE.finditer(match.group("target"))),
            _MAX_TARGET_LENGTH,
            "target rule",
        )
    )
    return source, target


@dataclass(frozen=True)
class LimbuConversion:
    legacy_text: str
    unicode_text: str
    limbu_char_count: int
    replacement_count: int
    unmapped_codepoints: list[str]


@dataclass(frozen=True)
class _LimbuReorderContract:
    vowels: frozenset[int]
    subjoined: frozenset[int]
    kemphreng: int
    provenance: str


_DEFAULT_REORDER_CONTRACT = _LimbuReorderContract(
    vowels=_VOWELS,
    subjoined=_SUBJOINED,
    kemphreng=_KEMPHRENG,
    provenance="legacy-byte-derived-only",
)


@dataclass(frozen=True)
class _LimbuContract:
    rules: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]
    reorder: _LimbuReorderContract
    precedence: str
    source_domain: str
    pass_order: tuple[str, str]


def _parse_reorder_contract(
    unicode_classes: Mapping[str, tuple[int, ...]],
    rule_lines: tuple[str, ...],
    reachable_targets: frozenset[int],
) -> _LimbuReorderContract:
    if len(rule_lines) != 2:
        raise ValueError("Limbu Unicode pass requires exactly two reorder rules")
    pair = _REORDER_PAIR_RE.fullmatch(rule_lines[0])
    if pair is None:
        raise ValueError(f"invalid Limbu Unicode pair reorder rule: {rule_lines[0]!r}")
    triple = _REORDER_TRIPLE_RE.fullmatch(rule_lines[1])
    if triple is None:
        raise ValueError(f"invalid Limbu Unicode triple reorder rule: {rule_lines[1]!r}")

    pair_roles = (
        pair.group("first_class"),
        pair.group("first_var"),
        pair.group("second_class"),
        pair.group("second_var"),
    )
    triple_roles = (
        triple.group("first_class"),
        triple.group("first_var"),
        triple.group("second_class"),
        triple.group("second_var"),
    )
    if pair_roles != triple_roles:
        raise ValueError("Limbu Unicode reorder rules use inconsistent classes or variables")
    if pair_roles != ("VOWEL", "V", "SUBJ", "S"):
        raise ValueError("Limbu Unicode reorder rules differ from the canonical role contract")
    first_class, first_variable, second_class, second_variable = pair_roles
    if first_class == second_class or first_variable == second_variable:
        raise ValueError("Limbu Unicode reorder roles must be distinct")
    if (
        pair.group("output_first") != second_variable
        or pair.group("output_second") != first_variable
        or triple.group("output_first") != second_variable
        or triple.group("output_second") != first_variable
    ):
        raise ValueError("Limbu Unicode reorder output must swap the two bound variables")

    input_literal = _validate_unicode_scalar(int(triple.group("input_literal"), 16))
    output_literal = _validate_unicode_scalar(int(triple.group("output_literal"), 16))
    if input_literal != output_literal:
        raise ValueError("Limbu Unicode triple reorder must preserve its literal codepoint")
    if tuple(unicode_classes) != (first_class, second_class):
        raise ValueError(
            "Limbu Unicode pass must declare exactly its two referenced classes in source order"
        )
    first_members = frozenset(unicode_classes[first_class])
    second_members = frozenset(unicode_classes[second_class])
    if first_members != _VOWELS or second_members != _SUBJOINED or input_literal != _KEMPHRENG:
        raise ValueError("Limbu Unicode reorder values differ from the canonical contract")
    if first_members & second_members or input_literal in first_members | second_members:
        raise ValueError("Limbu Unicode reorder roles must have disjoint codepoints")
    role_codepoints = first_members | second_members | {input_literal}
    if any(not _is_assigned_script_codepoint(codepoint, "Limbu") for codepoint in role_codepoints):
        raise ValueError("Limbu Unicode reorder roles must contain assigned Limbu codepoints")
    unreachable = role_codepoints - reachable_targets
    if unreachable:
        labels = " ".join(f"U+{codepoint:04X}" for codepoint in sorted(unreachable))
        raise ValueError(f"unreachable Limbu Unicode reorder role: {labels}")
    return _LimbuReorderContract(
        vowels=first_members,
        subjoined=second_members,
        kemphreng=input_literal,
        provenance="legacy-byte-derived-only",
    )


def _normalize_reorder_contract(contract: object) -> _LimbuReorderContract:
    if type(contract) is not _LimbuReorderContract:
        raise ValueError("invalid Limbu reorder contract")
    if type(contract.vowels) is not frozenset or type(contract.subjoined) is not frozenset:
        raise ValueError("invalid Limbu reorder contract")
    try:
        vowels = frozenset(_validate_unicode_scalar(value) for value in contract.vowels)
        subjoined = frozenset(_validate_unicode_scalar(value) for value in contract.subjoined)
        kemphreng = _validate_unicode_scalar(contract.kemphreng)
    except ValueError as error:
        raise ValueError("invalid Limbu reorder contract") from error
    if (
        vowels != _VOWELS
        or subjoined != _SUBJOINED
        or kemphreng != _KEMPHRENG
        or type(contract.provenance) is not str
        or contract.provenance != "legacy-byte-derived-only"
        or any(
            not _is_assigned_script_codepoint(codepoint, "Limbu")
            for codepoint in vowels | subjoined | {kemphreng}
        )
    ):
        raise ValueError("invalid Limbu reorder contract")
    return _LimbuReorderContract(
        vowels=vowels,
        subjoined=subjoined,
        kemphreng=kemphreng,
        provenance="legacy-byte-derived-only",
    )


class LimbuConverter:
    """Forward ``Byte_Unicode`` reader for the SIL Namdhinggo Limbu legacy map."""

    def __init__(
        self,
        rules: Iterable[tuple[Iterable[int], Iterable[int]]],
        *,
        _reorder_contract: _LimbuReorderContract = _DEFAULT_REORDER_CONTRACT,
    ) -> None:
        raw_rules = _bounded_contract_tuple(
            rules, _MAX_BYTE_RULES, "byte-rule sequence", reject_unordered=True
        )
        if not raw_rules:
            raise ValueError("LimbuConverter requires at least one mapping rule")
        normalized_rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        seen: set[tuple[int, ...]] = set()
        for raw_rule in raw_rules:
            if isinstance(raw_rule, (str, bytes, Mapping, Set)):
                raise ValueError("invalid Limbu byte rule")
            raw_parts = _bounded_contract_tuple(raw_rule, 2, "byte rule", reject_unordered=True)
            if len(raw_parts) != 2:
                raise ValueError("invalid Limbu byte rule")
            raw_source, raw_target = raw_parts
            source = tuple(
                _validate_byte(value)
                for value in _bounded_contract_tuple(
                    raw_source,
                    _MAX_SOURCE_LENGTH,
                    "source rule",
                    reject_unordered=True,
                )
            )
            target = tuple(
                _validate_unicode_scalar(value)
                for value in _bounded_contract_tuple(
                    raw_target,
                    _MAX_TARGET_LENGTH,
                    "target rule",
                    reject_unordered=True,
                )
            )
            if not source:
                raise ValueError("empty Limbu source rule")
            if not target:
                raise ValueError(f"empty Limbu target rule for source: {source!r}")
            protected_source = next((value for value in source if value <= 0x20), None)
            if protected_source is not None and (
                source != (protected_source,) or target != (protected_source,)
            ):
                raise ValueError("Limbu C0 and SPACE sources must be singleton identity rules")
            protected_target = next((value for value in target if value <= 0x20), None)
            if protected_target is not None and (
                source != (protected_target,) or target != (protected_target,)
            ):
                raise ValueError("Limbu C0 and SPACE targets must be singleton identity rules")
            if source in seen:
                label = " ".join(f"0x{value:02X}" for value in source)
                raise ValueError(f"duplicate Limbu source rule: {label}")
            seen.add(source)
            normalized_rules.append((source, target))
        reorder_contract = _normalize_reorder_contract(_reorder_contract)
        # Longest source sequences first so multi-byte rules win.
        self._contract = _LimbuContract(
            rules=tuple(sorted(normalized_rules, key=lambda item: len(item[0]), reverse=True)),
            reorder=reorder_contract,
            precedence="longest-source-first-stable",
            source_domain="byte-scalars",
            pass_order=("byte_unicode", "unicode"),
        )

    @property
    def _rules(self) -> tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]:
        return self._contract.rules

    @classmethod
    def from_map_file(cls, path: str | Path) -> "LimbuConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"Limbu legacy map does not exist: {map_path}")
        with map_path.open("rb") as stream:
            map_bytes = stream.read(_MAX_MAP_FILE_BYTES + 1)
        if len(map_bytes) > _MAX_MAP_FILE_BYTES:
            raise ValueError(f"Limbu map exceeds {_MAX_MAP_FILE_BYTES} bytes")
        try:
            map_text = map_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError(f"invalid UTF-8 in Limbu map {map_path}") from error
        physical_lines = map_text.splitlines()
        if len(physical_lines) > _MAX_MAP_LINES:
            raise ValueError(f"Limbu map exceeds {_MAX_MAP_LINES} lines")
        if any(len(line) > _MAX_MAP_LINE_CODEPOINTS for line in physical_lines):
            raise ValueError(f"Limbu map line exceeds {_MAX_MAP_LINE_CODEPOINTS} codepoints")

        byte_classes: dict[str, tuple[int, ...]] = {}
        byte_pass_unicode_classes: dict[str, tuple[int, ...]] = {}
        reorder_classes: dict[str, tuple[int, ...]] = {}
        rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        current_pass = ""
        seen_passes: list[str] = []
        seen_defaults: set[str] = set()
        seen_headers: set[str] = set()
        byte_rule_lines: list[str] = []
        reorder_rule_lines: list[str] = []
        for raw_line in physical_lines:
            line = raw_line.split(";", 1)[0].strip()
            if not line:
                continue
            if _PASS_PREFIX_RE.match(line):
                pass_match = _PASS_RE.fullmatch(line)
                if pass_match is None:
                    raise ValueError(f"invalid Limbu pass declaration: {line!r}")
                pass_name = pass_match.group(1).casefold()
                if pass_name in seen_passes:
                    raise ValueError(f"duplicate Limbu pass declaration: {line!r}")
                if pass_name == "unicode" and seen_passes != ["byte_unicode"]:
                    raise ValueError("Limbu Byte_Unicode pass must precede Unicode pass")
                if pass_name == "byte_unicode" and seen_passes:
                    raise ValueError("Limbu Byte_Unicode pass must precede Unicode pass")
                seen_passes.append(pass_name)
                current_pass = pass_name
                continue

            if not current_pass:
                header_match = _HEADER_STRING_RE.fullmatch(line)
                if header_match is not None:
                    header_name = header_match.group(1)
                    if header_name in seen_headers:
                        raise ValueError(f"duplicate Limbu header: {header_name}")
                    seen_headers.add(header_name)
                    continue
                if _HEADER_PREFIX_RE.match(line):
                    raise ValueError(f"invalid Limbu header declaration: {line!r}")
                raise ValueError(f"unsupported Limbu pre-pass syntax: {line!r}")

            if current_pass == "byte_unicode":
                if _DEFAULT_PREFIX_RE.match(line):
                    if _BYTE_DEFAULT_RE.fullmatch(line) or _UNI_DEFAULT_RE.fullmatch(line):
                        default_name = line.split(None, 1)[0].casefold()
                        if default_name in seen_defaults:
                            raise ValueError(f"duplicate Limbu default declaration: {line!r}")
                        seen_defaults.add(default_name)
                        continue
                    raise ValueError(f"invalid Limbu default declaration: {line!r}")
                byte_match = _BYTECLASS_RE.fullmatch(line)
                if byte_match:
                    name = byte_match.group(1).strip()
                    if not name:
                        raise ValueError("empty Limbu byte class name")
                    if _CLASS_NAME_RE.fullmatch(name) is None:
                        raise ValueError(f"invalid Limbu byte class name: {name!r}")
                    if name in byte_classes:
                        raise ValueError(f"duplicate Limbu byte class: {name!r}")
                    if len(byte_classes) == _MAX_BYTE_CLASSES:
                        raise ValueError(f"Limbu byte classes exceed {_MAX_BYTE_CLASSES} entries")
                    byte_classes[name] = _expand_byte_tokens(byte_match.group(2))
                    continue
                unicode_match = _UNICLASS_RE.fullmatch(line)
                if unicode_match:
                    name = unicode_match.group(1).strip()
                    if not name:
                        raise ValueError("empty Limbu Unicode class name")
                    if _CLASS_NAME_RE.fullmatch(name) is None:
                        raise ValueError(f"invalid Limbu Unicode class name: {name!r}")
                    if name in byte_pass_unicode_classes:
                        raise ValueError(f"duplicate Limbu Unicode class: {name!r}")
                    if len(byte_pass_unicode_classes) == _MAX_UNICODE_CLASSES:
                        raise ValueError(
                            f"Limbu byte-pass Unicode classes exceed {_MAX_UNICODE_CLASSES} entries"
                        )
                    byte_pass_unicode_classes[name] = _expand_unicode_tokens(unicode_match.group(2))
                    continue
                if len(byte_rule_lines) == _MAX_BYTE_RULES:
                    raise ValueError(f"Limbu byte-rule sequence exceeds {_MAX_BYTE_RULES} entries")
                byte_rule_lines.append(line)
                continue

            if current_pass == "unicode":
                if _BYTECLASS_RE.fullmatch(line):
                    raise ValueError(f"unsupported Limbu Unicode-pass syntax: {line!r}")
                unicode_match = _UNICLASS_RE.fullmatch(line)
                if unicode_match:
                    if reorder_rule_lines:
                        raise ValueError("Limbu Unicode classes must precede the reorder rules")
                    name = unicode_match.group(1).strip()
                    if not name:
                        raise ValueError("empty Limbu reorder class name")
                    if _CLASS_NAME_RE.fullmatch(name) is None:
                        raise ValueError(f"invalid Limbu reorder class name: {name!r}")
                    if name in reorder_classes:
                        raise ValueError(f"duplicate Limbu reorder class: {name!r}")
                    if len(reorder_classes) == _MAX_UNICODE_CLASSES:
                        raise ValueError(
                            f"Limbu reorder classes exceed {_MAX_UNICODE_CLASSES} entries"
                        )
                    reorder_classes[name] = _expand_unicode_tokens(unicode_match.group(2))
                    continue
                if len(reorder_rule_lines) == 2:
                    raise ValueError("Limbu Unicode pass has more than two reorder rules")
                reorder_rule_lines.append(line)
                continue

            raise ValueError(f"unsupported Limbu active pass: {current_pass!r}")

        for line in byte_rule_lines:
            class_match = _CLASS_RULE_RE.fullmatch(line)
            if class_match:
                byte_name, unicode_name = (name.strip() for name in class_match.groups())
                if not byte_name or not unicode_name:
                    raise ValueError(f"empty Limbu class reference: {line!r}")
                if (
                    _CLASS_NAME_RE.fullmatch(byte_name) is None
                    or _CLASS_NAME_RE.fullmatch(unicode_name) is None
                ):
                    raise ValueError(f"invalid Limbu class reference: {line!r}")
                byte_values = byte_classes.get(byte_name)
                unicode_values = byte_pass_unicode_classes.get(unicode_name)
                if byte_values is None:
                    raise ValueError(
                        f"Limbu class rule references unknown byte class: {byte_name!r}"
                    )
                if unicode_values is None:
                    raise ValueError(
                        f"Limbu class rule references unknown Unicode class: {unicode_name!r}"
                    )
                if len(byte_values) != len(unicode_values):
                    raise ValueError(
                        f"Limbu class rule length mismatch for [{byte_name}]>[{unicode_name}]: "
                        f"{len(byte_values)} bytes vs {len(unicode_values)} codepoints"
                    )
                if len(rules) + len(byte_values) > _MAX_BYTE_RULES:
                    raise ValueError(f"Limbu byte-rule sequence exceeds {_MAX_BYTE_RULES} entries")
                rules.extend(
                    ((byte_value,), (codepoint,))
                    for byte_value, codepoint in zip(byte_values, unicode_values)
                )
                continue
            if len(rules) == _MAX_BYTE_RULES:
                raise ValueError(f"Limbu byte-rule sequence exceeds {_MAX_BYTE_RULES} entries")
            rules.append(_parse_explicit_rule(line))

        if "byte_unicode" not in seen_passes:
            raise ValueError("Limbu map is missing Pass(Byte_Unicode)")

        # Normalize and validate the byte contract before reporting a missing
        # later pass, so malformed byte rules retain their local context.
        byte_contract = cls(rules)
        if seen_passes != ["byte_unicode", "unicode"]:
            raise ValueError("Limbu map is missing Pass(Unicode)")
        if seen_defaults != {"bytedefault", "unidefault"}:
            raise ValueError("Limbu map requires the two canonical default declarations")
        reachable_targets = frozenset(
            codepoint for _source, target in byte_contract._rules for codepoint in target
        )
        reorder_contract = _parse_reorder_contract(
            reorder_classes,
            tuple(reorder_rule_lines),
            reachable_targets,
        )
        return cls(rules, _reorder_contract=reorder_contract)

    @classmethod
    def default(cls) -> "LimbuConverter":
        with resources.as_file(resources.files("nepal_ttf2utf.maps") / "Limbu.map") as p:
            return cls.from_map_file(p)

    def _byte_pass_with_provenance(self, text: str) -> tuple[str, tuple[bool, ...], int, list[str]]:
        output: list[str] = []
        derived: list[bool] = []
        unmapped: list[str] = []
        replacements = 0
        index = 0
        while index < len(text):
            code = ord(text[index])
            matched = False
            for source, target in self._rules:
                if self._matches(text, index, source):
                    output.extend(chr(value) for value in target)
                    derived.extend([True] * len(target))
                    replacements += 1
                    index += len(source)
                    matched = True
                    break
            if matched:
                continue
            output.append(text[index])
            derived.append(False)
            if text[index] not in _STRUCTURAL_TEXT and not _is_assigned_script_codepoint(
                code, "Limbu"
            ):
                unmapped.append(f"U+{code:04X}")
            index += 1
        return "".join(output), tuple(derived), replacements, unmapped

    def convert(self, text: str) -> LimbuConversion:
        require_text(text)
        mapped, derived, replacements, unmapped = self._byte_pass_with_provenance(text)
        converted = _reorder_limbu(mapped, derived, contract=self._contract.reorder)
        converted = unicodedata.normalize("NFC", converted)
        # SIL's CTL class preserves every C0 value. Keep that exact lenient
        # mapping/count behavior but diagnose values outside the allowlist.
        unmapped.extend(diagnostic_c0_codepoints(converted))
        return LimbuConversion(
            legacy_text=text,
            unicode_text=converted,
            limbu_char_count=len(_LIMBU_CODEPOINT_RE.findall(converted)),
            replacement_count=replacements,
            unmapped_codepoints=sorted(set(unmapped)),
        )

    @staticmethod
    def _matches(text: str, index: int, source: tuple[int, ...]) -> bool:
        if index + len(source) > len(text):
            return False
        return all(ord(text[index + offset]) == code for offset, code in enumerate(source))


def _reorder_limbu(
    text: str,
    derived: tuple[bool, ...] | None = None,
    *,
    contract: _LimbuReorderContract = _DEFAULT_REORDER_CONTRACT,
) -> str:
    if derived is None:
        derived = (True,) * len(text)
    if (
        type(derived) is not tuple
        or len(derived) != len(text)
        or any(type(value) is not bool for value in derived)
    ):
        raise ValueError("invalid Limbu reorder provenance")
    chars = list(text)
    provenance = list(derived)
    index = 0
    while index < len(chars) - 1:
        current = ord(chars[index])
        nxt = ord(chars[index + 1])
        if current in contract.vowels and nxt in contract.subjoined:
            if provenance[index] and provenance[index + 1]:
                chars[index], chars[index + 1] = chars[index + 1], chars[index]
                provenance[index], provenance[index + 1] = (
                    provenance[index + 1],
                    provenance[index],
                )
            index += 2
            continue
        if (
            index < len(chars) - 2
            and current in contract.vowels
            and ord(chars[index + 1]) == contract.kemphreng
            and ord(chars[index + 2]) in contract.subjoined
        ):
            if all(provenance[index : index + 3]):
                vowel = chars[index]
                subjoined = chars[index + 2]
                chars[index : index + 3] = [subjoined, vowel, chr(contract.kemphreng)]
                vowel_derived = provenance[index]
                subjoined_derived = provenance[index + 2]
                kemphreng_derived = provenance[index + 1]
                provenance[index : index + 3] = [
                    subjoined_derived,
                    vowel_derived,
                    kemphreng_derived,
                ]
            index += 3
            continue
        index += 1
    return "".join(chars)


_DEFAULT: LimbuConverter | None = None


def convert_limbu(text: str, *, strict: bool = False) -> str:
    """Convert Namdhinggo-legacy Limbu text to Unicode Limbu (NFC).

    The string return type is retained for compatibility. Use
    :meth:`LimbuConverter.convert` for counts and the unmapped-codepoint list.
    With ``strict=True``, input absent from the SIL map or the pinned assigned
    Limbu repertoire raises ``ValueError``.
    """
    require_boolean(strict, "strict")
    require_text(text)
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = LimbuConverter.default()
    result = _DEFAULT.convert(text)
    if strict and result.unmapped_codepoints:
        raise ValueError(
            "unmapped/leftover characters after Limbu conversion: "
            + " ".join(result.unmapped_codepoints)
        )
    return result.unicode_text
