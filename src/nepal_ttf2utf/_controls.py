"""Shared control-character policy for legacy converter diagnostics."""

from __future__ import annotations

from collections.abc import Iterable

STRUCTURAL_C0 = frozenset("\t\r\n")
DIAGNOSTIC_C0 = frozenset(chr(codepoint) for codepoint in range(0x20)) - STRUCTURAL_C0


def diagnostic_c0_codepoints(text: str) -> set[str]:
    """Return C0 values outside the structural allowlist as code-point labels."""
    return {f"U+{ord(char):04X}" for char in text if char in DIAGNOSTIC_C0}


def codepoint_labels(characters: Iterable[str]) -> list[str]:
    """Render unique characters as sorted, visible code-point labels."""
    return sorted({f"U+{ord(char):04X}" for char in characters})
