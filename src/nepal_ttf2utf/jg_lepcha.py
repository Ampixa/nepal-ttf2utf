"""Jason Glavy's ``JG Lepcha`` legacy font -> Unicode Lepcha.

This converter applies SIL's two-pass TECkit map without requiring a TECkit
runtime. The byte pass handles classes, composite glyphs, and conjunct glyphs;
the Unicode pass reorders the font's visual-order vowel/final signs into Lepcha
logical order.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

LEPCHA_LO, LEPCHA_HI = 0x1C00, 0x1C4F

_BYTE_TOKEN_RE = re.compile(r"0x([0-9A-Fa-f]{2})")
_UNI_TOKEN_RE = re.compile(r"U\+([0-9A-Fa-f]{4,6})")
_BYTECLASS_RE = re.compile(r"^ByteClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_UNICLASS_RE = re.compile(r"^UniClass\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_PLAINCLASS_RE = re.compile(r"^Class\s*\[([^\]]+)\]\s*=\s*\((.*)\)\s*$")
_CLASS_RULE_RE = re.compile(r"^\[([^\]]+)\]\s*<?>\s*\[([^\]]+)\]\s*$")
_BOUND_CLASS_RE = re.compile(r"\[([^\]]+)\]\s*=\s*([A-Za-z]\w*)")
_VAR_REF_RE = re.compile(r"@([A-Za-z]\w*)")
_CONTEXT_RULE_RE = re.compile(
    r"^0x([0-9A-Fa-f]{2})\s*/\s*\^\s*\[([^\]]+)\]\s*_\s*>\s*"
    r"U\+([0-9A-Fa-f]{4,6})\s*$"
)


def _tokens(body: str) -> list[str]:
    body = re.sub(r"\s*\.\.\s*", " .. ", body)
    return [token for token in body.split() if token]


def _expand_byte_tokens(body: str) -> tuple[int, ...]:
    values: list[int] = []
    tokens = _tokens(body)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 2 < len(tokens) and tokens[index + 1] == "..":
            start = int(token, 16)
            end = int(tokens[index + 2], 16)
            if end < start:
                raise ValueError(
                    f"invalid byte range in JG Lepcha map: {token}..{tokens[index + 2]}"
                )
            values.extend(range(start, end + 1))
            index += 3
            continue
        if _BYTE_TOKEN_RE.fullmatch(token) is None:
            raise ValueError(f"unparseable byte token in JG Lepcha map: {token!r}")
        values.append(int(token, 16))
        index += 1
    return tuple(values)


def _expand_uni_tokens(body: str) -> tuple[int, ...]:
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
            if end < start:
                raise ValueError(
                    f"invalid Unicode range in JG Lepcha map: {token}..{tokens[index + 2]}"
                )
            values.extend(range(start, end + 1))
            index += 3
            continue
        match = _UNI_TOKEN_RE.fullmatch(token)
        if match is None:
            raise ValueError(f"unparseable Unicode token in JG Lepcha map: {token!r}")
        values.append(int(match.group(1), 16))
        index += 1
    return tuple(values)


@dataclass(frozen=True)
class _ReorderRule:
    slots: tuple[tuple[str, str], ...]
    output_vars: tuple[str, ...]


@dataclass(frozen=True)
class JGLepchaConversion:
    legacy_text: str
    unicode_text: str
    lepcha_char_count: int
    replacement_count: int
    unmapped_codepoints: list[str]


class JGLepchaConverter:
    """Native forward reader for SIL's ``JGLepcha.map``."""

    def __init__(
        self,
        byte_rules: list[tuple[tuple[int, ...], tuple[int, ...]]],
        reorder_rules: list[_ReorderRule],
        unicode_classes: dict[str, frozenset[int]],
        context_rule: tuple[int, frozenset[int], int] | None,
    ) -> None:
        if not byte_rules:
            raise ValueError("JGLepchaConverter requires at least one byte rule")
        seen: set[tuple[int, ...]] = set()
        ordered: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        for source, target in sorted(byte_rules, key=lambda item: len(item[0]), reverse=True):
            if source not in seen:
                seen.add(source)
                ordered.append((source, target))
        self._byte_rules = ordered
        self._reorder_rules = sorted(reorder_rules, key=lambda rule: len(rule.slots), reverse=True)
        self._unicode_classes = unicode_classes
        self._context_rule = context_rule

    @classmethod
    def from_map_file(cls, path: str | Path) -> "JGLepchaConverter":
        map_path = Path(path)
        if not map_path.is_file():
            raise FileNotFoundError(f"JG Lepcha map does not exist: {map_path}")
        raw = re.sub(r"\\\s*\n", " ", map_path.read_text(encoding="utf-8-sig"))

        byte_classes: dict[str, tuple[int, ...]] = {}
        unicode_classes_ordered: dict[str, tuple[int, ...]] = {}
        unicode_classes: dict[str, frozenset[int]] = {}
        byte_rule_lines: list[str] = []
        reorder_rules: list[_ReorderRule] = []
        current_pass = ""

        for raw_line in raw.splitlines():
            line = raw_line.split(";", 1)[0].strip()
            if not line:
                continue
            lowered = line.lower()
            if lowered.startswith("pass("):
                current_pass = lowered
                continue
            if current_pass == "pass(byte_unicode)":
                byte_match = _BYTECLASS_RE.match(line)
                if byte_match:
                    byte_classes[byte_match.group(1).strip()] = _expand_byte_tokens(
                        byte_match.group(2)
                    )
                    continue
                unicode_match = _UNICLASS_RE.match(line)
                if unicode_match:
                    unicode_classes_ordered[unicode_match.group(1).strip()] = _expand_uni_tokens(
                        unicode_match.group(2)
                    )
                    continue
                byte_rule_lines.append(line)
                continue
            if current_pass == "pass(unicode)":
                plain_match = _PLAINCLASS_RE.match(line)
                if plain_match:
                    unicode_classes[plain_match.group(1).strip()] = frozenset(
                        _expand_uni_tokens(plain_match.group(2))
                    )
                    continue
                rule = cls._parse_reorder_rule(line)
                if rule is not None:
                    reorder_rules.append(rule)

        byte_rules: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
        context_rule: tuple[int, frozenset[int], int] | None = None
        for line in byte_rule_lines:
            context_match = _CONTEXT_RULE_RE.match(line)
            if context_match:
                class_name = context_match.group(2).strip()
                previous_bytes = byte_classes.get(class_name)
                if previous_bytes is None:
                    raise ValueError(f"context rule references unknown byte class: {class_name!r}")
                # ^[class] means a concrete preceding input byte NOT in class.
                context_rule = (
                    int(context_match.group(1), 16),
                    frozenset(previous_bytes),
                    int(context_match.group(3), 16),
                )
                continue

            class_match = _CLASS_RULE_RE.match(line)
            if class_match:
                left_name, right_name = (part.strip() for part in class_match.groups())
                left = byte_classes.get(left_name)
                right = unicode_classes_ordered.get(right_name)
                if left is None or right is None:
                    raise ValueError(
                        f"unknown class in JG Lepcha rule: [{left_name}] <> [{right_name}]"
                    )
                if len(left) != len(right):
                    raise ValueError(
                        f"JG Lepcha class length mismatch: [{left_name}] has {len(left)}, "
                        f"[{right_name}] has {len(right)}"
                    )
                byte_rules.extend(((byte,), (codepoint,)) for byte, codepoint in zip(left, right))
                continue

            if "<>" in line or ">" in line:
                left_text, right_text = line.split("<>", 1) if "<>" in line else line.split(">", 1)
                source = tuple(int(value, 16) for value in _BYTE_TOKEN_RE.findall(left_text))
                target = tuple(int(value, 16) for value in _UNI_TOKEN_RE.findall(right_text))
                if source and target:
                    byte_rules.append((source, target))

        return cls(byte_rules, reorder_rules, unicode_classes, context_rule)

    @classmethod
    def default(cls) -> "JGLepchaConverter":
        with resources.as_file(resources.files("nepal_ttf2utf.maps") / "JGLepcha.map") as path:
            return cls.from_map_file(path)

    @staticmethod
    def _parse_reorder_rule(line: str) -> _ReorderRule | None:
        if "<>" not in line:
            return None
        left, right = line.split("<>", 1)
        slots = tuple(
            (name.strip(), variable.strip()) for name, variable in _BOUND_CLASS_RE.findall(left)
        )
        output_vars = tuple(_VAR_REF_RE.findall(right))
        bound = {variable for _, variable in slots}
        if not slots or not output_vars or any(variable not in bound for variable in output_vars):
            return None
        return _ReorderRule(slots, output_vars)

    @staticmethod
    def _matches(text: str, index: int, source: tuple[int, ...]) -> bool:
        return index + len(source) <= len(text) and all(
            ord(text[index + offset]) == codepoint for offset, codepoint in enumerate(source)
        )

    def _byte_pass(self, text: str) -> tuple[str, int, list[str]]:
        output: list[str] = []
        unmapped: set[str] = set()
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
                    replacements += 1
                    index += 1
                    continue

            for source, target in self._byte_rules:
                if self._matches(text, index, source):
                    output.extend(chr(codepoint) for codepoint in target)
                    replacements += 1
                    index += len(source)
                    break
            else:
                char = text[index]
                output.append(char)
                codepoint = ord(char)
                if not (LEPCHA_LO <= codepoint <= LEPCHA_HI):
                    unmapped.add(f"U+{codepoint:04X}")
                index += 1
        return "".join(output), replacements, sorted(unmapped)

    def _reorder_pass(self, text: str) -> str:
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
                    output.extend(bound[variable] for variable in rule.output_vars)
                    index += len(rule.slots)
                    break
            else:
                output.append(text[index])
                index += 1
        return "".join(output)

    def convert(self, text: str) -> JGLepchaConversion:
        mapped, replacements, unmapped = self._byte_pass(text)
        converted = unicodedata.normalize("NFC", self._reorder_pass(mapped))
        return JGLepchaConversion(
            legacy_text=text,
            unicode_text=converted,
            lepcha_char_count=sum(LEPCHA_LO <= ord(char) <= LEPCHA_HI for char in converted),
            replacement_count=replacements,
            unmapped_codepoints=unmapped,
        )


_DEFAULT: JGLepchaConverter | None = None


def convert_jg_lepcha(text: str, *, strict: bool = False) -> JGLepchaConversion:
    """Convert JG-Lepcha-encoded text to Unicode Lepcha (NFC)."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = JGLepchaConverter.default()
    result = _DEFAULT.convert(text)
    if strict and result.unmapped_codepoints:
        raise ValueError(
            "unmapped/leftover characters after JG Lepcha conversion: "
            + " ".join(result.unmapped_codepoints)
        )
    return result
