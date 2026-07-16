"""Legacy Kirat Rai fonts -> Unicode Kirat Rai (U+16D40-U+16D7F).

SIL publishes a TECkit map for the canonical 2021 ``kirat rai font new`` encoding;
the vendored copy lives at ``maps/kiratraifontnew.map``. Four audited Sikkim Herald
PDF subsets use a different, older layout hidden behind per-PDF CIDs and ASCII
ToUnicode values. The package's frozen Herald routing snapshot applies the observed
38-entry old-to-new premap before the SIL rules. The source PDFs and intermediate
outline-comparison artifacts are not distributed; ``docs/EVIDENCE.md`` records the
derivation boundary.

That map is expressed with TECkit ``ByteClass`` / ``UniClass`` declarations plus a
handful of explicit multi-byte ligature rules. A ``[class] > [class]`` rule maps the
byte at position *n* of the byte class to the codepoint at position *n* of the paired
Unicode class. This module reads the map natively (no ``teckit_compile`` dependency)
and applies the forward Legacy->Unicode pass, longest-match-first so the multi-byte
ligature rules win over the single-byte class rules.

The two layouts must not be auto-detected from text: even old-layout strings without
the formerly conspicuous ``f R x F I L`` bytes are globally permuted. Callers must
select the canonical-new or Herald alias explicitly. The sole extracted Herald ``Z``
is a blank spacing glyph and is normalized to an ordinary space.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from importlib import resources
from itertools import islice
from pathlib import Path
from types import MappingProxyType

from ._controls import diagnostic_c0_codepoints, require_boolean, require_text
from .unicode_span import _is_assigned_script_codepoint, _normalize_nfc

_KIRATRAI_CODEPOINT_RE = re.compile(r"[\U00016D40-\U00016D7F]")
_MAX_MAP_FILE_BYTES = 1_000_000
_MAX_BYTE_RULES = 512
_MAX_BYTE_CLASSES = 128
_MAX_UNICODE_CLASSES = 128
_MAX_BYTE_CLASS_MEMBERS = 256
_MAX_UNICODE_CLASS_MEMBERS = 1024
_MAX_SOURCE_LENGTH = 16
_MAX_TARGET_LENGTH = 32

_BYTE_TOKEN_RE = re.compile(r"0x([0-9A-Fa-f]{2})")
_UNI_TOKEN_RE = re.compile(r"U\+([0-9A-Fa-f]{4,6})")
_CLASS_NAME_RE = re.compile(r"[A-Za-z]\w*")
_BYTECLASS_RE = re.compile(r"^ByteClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_UNICLASS_RE = re.compile(r"^UniClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_CLASS_RULE_RE = re.compile(r"^\[([^\]]+)\]\s*<?>\s*\[([^\]]+)\]\s*$")
_PASS_RE = re.compile(r"^Pass\(\s*(Byte_Unicode|Unicode)\s*\)$", re.IGNORECASE)
_PASS_PREFIX_RE = re.compile(r"^Pass\b", re.IGNORECASE)
_HEADER_STRING_RE = re.compile(
    r"^(EncodingName|DescriptiveName|Version|Contact|RegistrationAuthority|"
    r'RegistrationName|Copyright)\s+"[^"]*"$'
)
_HEADER_PREFIX_RE = re.compile(
    r"^(?:EncodingName|DescriptiveName|Version|Contact|RegistrationAuthority|"
    r"RegistrationName|Copyright|RHSFlags)\b"
)
_RHS_FLAGS_RE = re.compile(r"^RHSFlags\s+\(ExpectsNFD\)$")
_EXPLICIT_RULE_RE = re.compile(
    r"^(?P<source>0x[0-9A-Fa-f]{2}(?:\s+0x[0-9A-Fa-f]{2})*)\s*"
    r"(?:<>|>)\s*"
    r"(?P<target>U\+[0-9A-Fa-f]{4,6}(?:\s+U\+[0-9A-Fa-f]{4,6})*)$"
)

_KIRATRAI_LO, _KIRATRAI_HI = 0x16D40, 0x16D7F

# Historical seven-value subset absent from SIL's canonical-new map. Kept as a
# public compatibility constant; it is not the complete absent-byte inventory.
# In Herald PDFs these values belong to the separate permuted layout below.
KIRATRAI_UNMAPPED_BYTES: frozenset[str] = frozenset("fRxFIL\\")

# Sikkim Herald extracted ASCII -> canonical ``kiratraifontnew`` byte. The
# project-derived values are the complete distributed premap observed across the
# four audited PDF subsets; they do not claim a universal Herald encoding.
KIRATRAI_HERALD_PREMAP: Mapping[str, str] = MappingProxyType(
    {
        "D": "q",
        "F": "g",
        "G": "P",
        "H": "j",
        "I": "W",
        "J": "J",
        "K": "Q",
        "L": "$",
        "O": "O",
        "R": "w",
        "S": "G",
        "U": "o",
        "a": "k",
        "b": "A",
        "c": "D",
        "d": "K",
        "e": "m",
        "f": "N",
        "g": "s",
        "h": "a",
        "i": "v",
        "j": "b",
        "k": "r",
        "l": "i",
        "m": "c",
        "n": "p",
        "o": "n",
        "p": "t",
        "q": "d",
        "r": "e",
        "s": "C",
        "t": "h",
        "u": "u",
        "v": "B",
        "w": "l",
        "x": "T",
        "y": "y",
        "z": "z",
    }
)

# Values forwarded unchanged to the canonical map. Digits and slash consequently
# become Kirat Rai characters; the remaining values stay literal. Backslash and
# Herald ``Z`` are separate blank glyphs normalized to ordinary spaces. Canonical
# ``kiratraifontnew`` Z remains U+16D6C and is unaffected.
KIRATRAI_HERALD_PASSTHROUGH: frozenset[str] = frozenset(" \t\r\n0123456789(),-/.;")
KIRATRAI_HERALD_BLANKS: frozenset[str] = frozenset("\\Z")


def _tokens(body: str) -> list[str]:
    body = re.sub(r"\s*\.\.\s*", " .. ", body)
    return [token for token in body.split() if token]


def _validate_unicode_scalar(codepoint: int) -> int:
    if (
        isinstance(codepoint, bool)
        or not isinstance(codepoint, int)
        or not (0 <= codepoint <= 0x10FFFF)
        or 0xD800 <= codepoint <= 0xDFFF
    ):
        raise ValueError(f"invalid Unicode scalar in Kirat Rai map: {codepoint!r}")
    return codepoint


def _validate_byte(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= 0xFF):
        raise ValueError(f"invalid Kirat Rai source byte: {value!r}")
    return value


def _bounded_tuple(
    values: object, limit: int, label: str, *, reject_unordered: bool = False
) -> tuple[object, ...]:
    if isinstance(values, (str, bytes, Mapping)) or (reject_unordered and isinstance(values, Set)):
        raise ValueError(f"invalid Kirat Rai {label}")
    try:
        result = tuple(islice(iter(values), limit + 1))  # type: ignore[arg-type]
    except TypeError as error:
        raise ValueError(f"invalid Kirat Rai {label}") from error
    if len(result) > limit:
        raise ValueError(f"Kirat Rai {label} exceeds {limit} entries")
    return result


def _expand_byte_tokens(body: str) -> tuple[int, ...]:
    """Expand a TECkit byte-class body into ordered byte values (``0xNN`` or ``0xNN .. 0xMM``)."""
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
                    f"invalid byte range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            start = int(start_match.group(1), 16)
            end = int(end_match.group(1), 16)
            if end < start:
                raise ValueError(
                    f"invalid byte range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            if len(values) + end - start + 1 > _MAX_BYTE_CLASS_MEMBERS:
                raise ValueError(f"Kirat Rai byte class exceeds {_MAX_BYTE_CLASS_MEMBERS} members")
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _BYTE_TOKEN_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable byte token in Kirat Rai map: {token!r}")
        if len(values) == _MAX_BYTE_CLASS_MEMBERS:
            raise ValueError(f"Kirat Rai byte class exceeds {_MAX_BYTE_CLASS_MEMBERS} members")
        values.append(int(match.group(1), 16))
        index += 1
    if not values:
        raise ValueError("empty byte class in Kirat Rai map")
    if len(values) != len(set(values)):
        raise ValueError("duplicate member in Kirat Rai byte class")
    return tuple(values)


def _expand_uni_tokens(body: str) -> tuple[int, ...]:
    """Expand a TECkit Unicode-class body into ordered codepoints (``U+NNNN`` or ranges)."""
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
                    f"unparseable unicode range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            start = _validate_unicode_scalar(int(start_match.group(1), 16))
            end = _validate_unicode_scalar(int(end_match.group(1), 16))
            if end < start:
                raise ValueError(
                    f"invalid unicode range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            if start <= 0xDFFF and end >= 0xD800:
                raise ValueError(
                    f"invalid Unicode scalar range in Kirat Rai map: {token}..{tokens[index + 2]}"
                )
            if len(values) + end - start + 1 > _MAX_UNICODE_CLASS_MEMBERS:
                raise ValueError(
                    f"Kirat Rai Unicode class exceeds {_MAX_UNICODE_CLASS_MEMBERS} members"
                )
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _UNI_TOKEN_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable unicode token in Kirat Rai map: {token!r}")
        if len(values) == _MAX_UNICODE_CLASS_MEMBERS:
            raise ValueError(
                f"Kirat Rai Unicode class exceeds {_MAX_UNICODE_CLASS_MEMBERS} members"
            )
        values.append(_validate_unicode_scalar(int(match.group(1), 16)))
        index += 1
    if not values:
        raise ValueError("empty Unicode class in Kirat Rai map")
    return tuple(values)


def _parse_explicit_rule(line: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    match = _EXPLICIT_RULE_RE.fullmatch(line)
    if match is None:
        raise ValueError(f"invalid explicit Kirat Rai rule: {line!r}")
    source = tuple(
        _validate_byte(value)
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
class _KiratRaiContract:
    rules: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]
    precedence: str
    source_domain: str


@dataclass(frozen=True)
class KiratRaiConversion:
    legacy_text: str
    unicode_text: str
    kiratrai_char_count: int
    replacement_count: int
    unmapped_codepoints: list[str]


class KiratRaiConverter:
    """Native reader/applier for SIL's ``kiratraifontnew.map`` TECkit mapping.

    Rules are flattened to ``(source_bytes, target_codepoints)`` pairs and applied
    longest-match-first so explicit multi-byte ligature rules (e.g. ``//`` -> double
    danda) take precedence over the single-byte class rules.
    """

    def __init__(self, rules: Iterable[tuple[Iterable[int], Iterable[int]]]) -> None:
        raw_rules = _bounded_tuple(
            rules, _MAX_BYTE_RULES, "byte-rule sequence", reject_unordered=True
        )
        if not raw_rules:
            raise ValueError("KiratRaiConverter requires at least one mapping rule")
        normalized_rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        seen: set[tuple[int, ...]] = set()
        for raw_rule in raw_rules:
            if isinstance(raw_rule, (str, bytes, Mapping, Set)):
                raise ValueError(f"invalid Kirat Rai byte rule: {raw_rule!r}")
            raw_parts = _bounded_tuple(raw_rule, 2, "byte rule", reject_unordered=True)
            if len(raw_parts) != 2:
                raise ValueError(f"invalid Kirat Rai byte rule: {raw_rule!r}")
            raw_source, raw_target = raw_parts
            source = tuple(
                _validate_byte(value)
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
                raise ValueError("empty Kirat Rai source rule")
            if not target:
                raise ValueError(f"empty Kirat Rai target rule for source: {source!r}")
            protected_source = next((value for value in source if value <= 0x20), None)
            if protected_source is not None and (
                source != (protected_source,) or target != (protected_source,)
            ):
                raise ValueError("Kirat Rai C0 and SPACE sources must be singleton identity rules")
            protected_target = next((value for value in target if value <= 0x20), None)
            if protected_target is not None and (
                source != (protected_target,) or target != (protected_target,)
            ):
                raise ValueError("Kirat Rai C0 and SPACE targets must be singleton identity rules")
            if source in seen:
                label = " ".join(f"0x{value:02X}" for value in source)
                raise ValueError(f"duplicate Kirat Rai source rule: {label}")
            seen.add(source)
            normalized_rules.append((source, target))
        self._contract = _KiratRaiContract(
            rules=tuple(sorted(normalized_rules, key=lambda item: len(item[0]), reverse=True)),
            precedence="longest-source-first-stable",
            source_domain="byte-scalars",
        )

    @property
    def _rules(self) -> tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]:
        return self._contract.rules

    @classmethod
    def from_map_file(cls, path: str | Path) -> "KiratRaiConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"Kirat Rai legacy map does not exist: {map_path}")
        with map_path.open("rb") as stream:
            map_bytes = stream.read(_MAX_MAP_FILE_BYTES + 1)
        if len(map_bytes) > _MAX_MAP_FILE_BYTES:
            raise ValueError(f"Kirat Rai map exceeds {_MAX_MAP_FILE_BYTES} bytes")
        try:
            map_text = map_bytes.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise ValueError(f"invalid UTF-8 in Kirat Rai map {map_path}") from error

        byte_classes: dict[str, tuple[int, ...]] = {}
        uni_classes: dict[str, tuple[int, ...]] = {}
        rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        current_pass = ""
        seen_passes: set[str] = set()
        seen_headers: set[str] = set()
        # First parse class declarations; collect rule lines for a second pass so class
        # rules can reference classes regardless of declaration order.
        rule_lines: list[str] = []
        for raw_line in map_text.splitlines():
            line = raw_line.split(";", 1)[0].strip()
            if not line:
                continue
            if _PASS_PREFIX_RE.match(line):
                pass_match = _PASS_RE.fullmatch(line)
                if pass_match is None:
                    raise ValueError(f"invalid Kirat Rai pass declaration: {line!r}")
                pass_name = pass_match.group(1).casefold()
                if pass_name in seen_passes:
                    raise ValueError(f"duplicate Kirat Rai pass declaration: {line!r}")
                if pass_name == "byte_unicode" and "unicode" in seen_passes:
                    raise ValueError("Kirat Rai Byte_Unicode pass must precede Unicode pass")
                seen_passes.add(pass_name)
                current_pass = pass_name
                continue

            if not current_pass:
                header_match = _HEADER_STRING_RE.fullmatch(line)
                if header_match is not None:
                    header_name = header_match.group(1)
                    if header_name in seen_headers:
                        raise ValueError(f"duplicate Kirat Rai header: {header_name}")
                    seen_headers.add(header_name)
                    continue
                if _RHS_FLAGS_RE.fullmatch(line):
                    if "RHSFlags" in seen_headers:
                        raise ValueError("duplicate Kirat Rai header: RHSFlags")
                    seen_headers.add("RHSFlags")
                    continue
                if _HEADER_PREFIX_RE.match(line):
                    raise ValueError(f"invalid Kirat Rai header declaration: {line!r}")
                raise ValueError(f"unsupported Kirat Rai pre-pass syntax: {line!r}")

            if current_pass == "unicode":
                raise ValueError(f"unsupported Kirat Rai Unicode-pass syntax: {line!r}")

            if current_pass != "byte_unicode":
                raise ValueError(f"unsupported Kirat Rai active pass: {current_pass!r}")

            byte_match = _BYTECLASS_RE.fullmatch(line)
            if byte_match:
                name = byte_match.group(1).strip()
                if not name:
                    raise ValueError("empty Kirat Rai byte class name")
                if _CLASS_NAME_RE.fullmatch(name) is None:
                    raise ValueError(f"invalid Kirat Rai byte class name: {name!r}")
                if name in byte_classes:
                    raise ValueError(f"duplicate Kirat Rai byte class: {name!r}")
                if len(byte_classes) == _MAX_BYTE_CLASSES:
                    raise ValueError(f"Kirat Rai byte classes exceed {_MAX_BYTE_CLASSES} entries")
                byte_classes[name] = _expand_byte_tokens(byte_match.group(2))
                continue
            uni_match = _UNICLASS_RE.fullmatch(line)
            if uni_match:
                name = uni_match.group(1).strip()
                if not name:
                    raise ValueError("empty Kirat Rai Unicode class name")
                if _CLASS_NAME_RE.fullmatch(name) is None:
                    raise ValueError(f"invalid Kirat Rai Unicode class name: {name!r}")
                if name in uni_classes:
                    raise ValueError(f"duplicate Kirat Rai Unicode class: {name!r}")
                if len(uni_classes) == _MAX_UNICODE_CLASSES:
                    raise ValueError(
                        f"Kirat Rai Unicode classes exceed {_MAX_UNICODE_CLASSES} entries"
                    )
                uni_classes[name] = _expand_uni_tokens(uni_match.group(2))
                continue
            if len(rule_lines) == _MAX_BYTE_RULES:
                raise ValueError(f"Kirat Rai byte-rule sequence exceeds {_MAX_BYTE_RULES} entries")
            rule_lines.append(line)

        if "byte_unicode" not in seen_passes:
            raise ValueError("Kirat Rai map is missing Pass(Byte_Unicode)")

        for line in rule_lines:
            class_rule = _CLASS_RULE_RE.fullmatch(line)
            if class_rule:
                left_name = class_rule.group(1).strip()
                right_name = class_rule.group(2).strip()
                if not left_name or not right_name:
                    raise ValueError(f"empty Kirat Rai class reference: {line!r}")
                if (
                    _CLASS_NAME_RE.fullmatch(left_name) is None
                    or _CLASS_NAME_RE.fullmatch(right_name) is None
                ):
                    raise ValueError(f"invalid Kirat Rai class reference: {line!r}")
                left = byte_classes.get(left_name)
                right = uni_classes.get(right_name)
                if left is None:
                    raise ValueError(
                        f"Kirat Rai class rule references unknown byte class: {left_name!r}"
                    )
                if right is None:
                    raise ValueError(
                        f"Kirat Rai class rule references unknown unicode class: {right_name!r}"
                    )
                if len(left) != len(right):
                    raise ValueError(
                        f"Kirat Rai class rule length mismatch for [{left_name}]>[{right_name}]: "
                        f"{len(left)} bytes vs {len(right)} codepoints"
                    )
                if len(rules) + len(left) > _MAX_BYTE_RULES:
                    raise ValueError(
                        f"Kirat Rai byte-rule sequence exceeds {_MAX_BYTE_RULES} entries"
                    )
                for byte_value, codepoint in zip(left, right):
                    rules.append(((byte_value,), (codepoint,)))
                continue
            if len(rules) == _MAX_BYTE_RULES:
                raise ValueError(f"Kirat Rai byte-rule sequence exceeds {_MAX_BYTE_RULES} entries")
            rules.append(_parse_explicit_rule(line))
        return cls(rules)

    @classmethod
    def default(cls) -> "KiratRaiConverter":
        with resources.as_file(resources.files("nepal_ttf2utf.maps") / "kiratraifontnew.map") as p:
            return cls.from_map_file(p)

    def convert(self, text: str) -> KiratRaiConversion:
        require_text(text)
        output: list[str] = []
        unmapped: list[str] = []
        replacements = 0
        index = 0
        length = len(text)
        while index < length:
            matched = False
            for source, target in self._rules:
                if self._matches(text, index, source):
                    output.extend(chr(value) for value in target)
                    replacements += 1
                    index += len(source)
                    matched = True
                    break
            if matched:
                continue
            char = text[index]
            output.append(char)
            code = ord(char)
            if not _is_assigned_script_codepoint(code, "Kirat Rai"):
                unmapped.append(f"U+{code:04X}")
            index += 1
        converted = _normalize_nfc("".join(output))
        # SIL's CTL class preserves every C0 value. Keep that exact lenient
        # mapping/count behavior but diagnose values outside the allowlist.
        unmapped.extend(diagnostic_c0_codepoints(converted))
        return KiratRaiConversion(
            legacy_text=text,
            unicode_text=converted,
            kiratrai_char_count=len(_KIRATRAI_CODEPOINT_RE.findall(converted)),
            replacement_count=replacements,
            unmapped_codepoints=sorted(set(unmapped)),
        )

    @staticmethod
    def _matches(text: str, index: int, source: tuple[int, ...]) -> bool:
        if index + len(source) > len(text):
            return False
        return all(ord(text[index + offset]) == code for offset, code in enumerate(source))


def _freeze_herald_contract() -> tuple[Mapping[str, str], frozenset[str], frozenset[str]]:
    """Validate and snapshot the fixed four-PDF Herald routing contract."""
    if not isinstance(KIRATRAI_HERALD_PREMAP, Mapping):
        raise ValueError("invalid Kirat Rai Herald premap")
    premap = dict(KIRATRAI_HERALD_PREMAP)
    passthrough = frozenset(KIRATRAI_HERALD_PASSTHROUGH)
    blanks = frozenset(KIRATRAI_HERALD_BLANKS)

    if len(premap) != 38:
        raise ValueError("Kirat Rai Herald premap must contain exactly 38 entries")
    if len(passthrough) != 21:
        raise ValueError("Kirat Rai Herald passthrough must contain exactly 21 values")
    if len(blanks) != 2:
        raise ValueError("Kirat Rai Herald blanks must contain exactly two values")

    for source, target in premap.items():
        if (
            type(source) is not str
            or len(source) != 1
            or ord(source) > 0xFF
            or type(target) is not str
            or len(target) != 1
            or ord(target) > 0xFF
        ):
            raise ValueError(f"invalid Kirat Rai Herald premap entry: {source!r}: {target!r}")
    if len(set(premap.values())) != len(premap):
        raise ValueError("Kirat Rai Herald premap targets must be one-to-one")

    for label, values in (("passthrough", passthrough), ("blank", blanks)):
        if any(type(value) is not str or len(value) != 1 or ord(value) > 0xFF for value in values):
            raise ValueError(f"invalid Kirat Rai Herald {label} value")

    source_sets = (set(premap), set(passthrough), set(blanks))
    if any(source_sets[left] & source_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("Kirat Rai Herald routing sources overlap")

    canonical = KiratRaiConverter.default()
    singleton_sources = {source[0] for source, _target in canonical._rules if len(source) == 1}
    unsupported_targets = sorted(
        target for target in premap.values() if ord(target) not in singleton_sources
    )
    if unsupported_targets:
        labels = " ".join(f"U+{ord(target):04X}" for target in unsupported_targets)
        raise ValueError(f"unsupported Kirat Rai Herald canonical target: {labels}")

    for value in set(premap.values()) | set(passthrough) | {" "}:
        result = canonical.convert(value)
        if result.replacement_count != 1 or result.unmapped_codepoints:
            raise ValueError(f"unclean Kirat Rai Herald canonical projection: {value!r}")

    return MappingProxyType(premap), passthrough, blanks


(
    _DEFAULT_HERALD_PREMAP,
    _DEFAULT_HERALD_PASSTHROUGH,
    _DEFAULT_HERALD_BLANKS,
) = _freeze_herald_contract()


class KiratRaiHeraldConverter:
    """Convert the frozen four-PDF Herald layout through a canonical SIL snapshot."""

    def __init__(self, canonical: KiratRaiConverter) -> None:
        if not isinstance(canonical, KiratRaiConverter):
            raise ValueError("KiratRaiHeraldConverter requires a KiratRaiConverter")
        self._canonical = KiratRaiConverter(canonical._rules)
        self._premap = _DEFAULT_HERALD_PREMAP
        self._passthrough = _DEFAULT_HERALD_PASSTHROUGH
        self._blanks = _DEFAULT_HERALD_BLANKS

    @classmethod
    def default(cls) -> "KiratRaiHeraldConverter":
        return cls(KiratRaiConverter.default())

    def convert(self, text: str) -> KiratRaiConversion:
        require_text(text)
        output: list[str] = []
        canonical_run: list[str] = []
        unmapped: set[str] = set()
        replacements = 0

        def flush() -> None:
            nonlocal replacements
            if not canonical_run:
                return
            result = self._canonical.convert("".join(canonical_run))
            output.append(result.unicode_text)
            replacements += result.replacement_count
            unmapped.update(result.unmapped_codepoints)
            canonical_run.clear()

        for char in text:
            remapped = self._premap.get(char)
            if remapped is not None:
                canonical_run.append(remapped)
                continue
            if char in self._blanks:
                canonical_run.append(" ")
                continue
            if char in self._passthrough:
                canonical_run.append(char)
                continue
            if _is_assigned_script_codepoint(ord(char), "Kirat Rai"):
                flush()
                output.append(char)
                continue
            flush()
            output.append(char)
            unmapped.add(f"U+{ord(char):04X}")
        flush()

        converted = _normalize_nfc("".join(output))
        return KiratRaiConversion(
            legacy_text=text,
            unicode_text=converted,
            kiratrai_char_count=len(_KIRATRAI_CODEPOINT_RE.findall(converted)),
            replacement_count=replacements,
            unmapped_codepoints=sorted(unmapped),
        )


_DEFAULT: KiratRaiConverter | None = None
_HERALD_DEFAULT: KiratRaiHeraldConverter | None = None


def convert_kiratrai(text: str, *, strict: bool = False) -> KiratRaiConversion:
    """Convert canonical ``kiratraifontnew`` text to Unicode Kirat Rai (NFC).

    This function applies SIL's map directly. Use :func:`convert_kiratrai_herald` for
    text extracted from the older/permuted Sikkim Herald PDF font.
    """
    require_boolean(strict, "strict")
    require_text(text)
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = KiratRaiConverter.default()
    result = _DEFAULT.convert(text)
    if strict and result.unmapped_codepoints:
        raise ValueError(
            "unmapped/leftover characters after Kirat Rai conversion: "
            + " ".join(result.unmapped_codepoints)
        )
    return result


def convert_kiratrai_herald(text: str, *, strict: bool = False) -> KiratRaiConversion:
    """Convert Sikkim Herald's permuted Kirat Rai PDF text to Unicode (NFC)."""
    require_boolean(strict, "strict")
    require_text(text)
    global _HERALD_DEFAULT
    if _HERALD_DEFAULT is None:
        _HERALD_DEFAULT = KiratRaiHeraldConverter.default()
    result = _HERALD_DEFAULT.convert(text)
    if strict and result.unmapped_codepoints:
        raise ValueError(
            "unmapped/leftover characters after Herald Kirat Rai conversion: "
            + " ".join(result.unmapped_codepoints)
        )
    return result
