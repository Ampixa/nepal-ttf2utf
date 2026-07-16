"""Shared control-character policy for legacy converter diagnostics."""

from __future__ import annotations

from collections.abc import Iterable

STRUCTURAL_C0 = frozenset("\t\r\n")
DIAGNOSTIC_C0 = frozenset(chr(codepoint) for codepoint in range(0x20)) - STRUCTURAL_C0


def require_boolean(value: object, name: str) -> None:
    """Reject truthy and falsy substitutes for a public Boolean option."""
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")


def require_string(value: object, name: str) -> None:
    """Reject non-string and string-subclass scalar input without coercion."""
    if type(value) is not str:
        raise TypeError(f"{name} must be a string")


def require_text(value: object) -> None:
    """Reject non-string and string-subclass conversion input."""
    require_string(value, "text")


def require_integer(value: object, name: str) -> int:
    """Reject non-integers and integer subclasses without numeric coercion."""
    if type(value) is not int:
        raise ValueError(f"{name} must be an int")
    return value


def diagnostic_c0_codepoints(text: str) -> set[str]:
    """Return C0 values outside the structural allowlist as code-point labels."""
    return {f"U+{ord(char):04X}" for char in text if char in DIAGNOSTIC_C0}


def codepoint_labels(characters: Iterable[str]) -> list[str]:
    """Render unique characters as sorted, visible code-point labels."""
    return sorted({f"U+{ord(char):04X}" for char in characters})
