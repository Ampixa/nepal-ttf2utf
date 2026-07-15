"""Hash-pinned recovery for broken Videha Janaki PDF text layers.

The audited PDFs expose U+FFFD for some Janaki conjunct glyphs while PyMuPDF's
text trace retains their glyph IDs. This module expands those IDs to the unique
Devanagari sequences established by Janaki 1.000 shaping evidence, then applies
the package's ordinary Devanagari-to-Tirhuta conversion.

Every recovery call compares complete caller-supplied profile metadata with
pinned values. Unsupported profile names, mismatched PDF/font/page metadata,
and unknown replacement glyph IDs fail closed; the caller remains responsible
for authenticating the supplied file metadata and trace tuples.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import islice
from types import MappingProxyType

from .tirhuta import convert_tirhuta
from .unicode_span import _is_assigned_script_codepoint

VIDEHA_ISSUE_001 = "videha-issue-001"
VIDEHA_2008_04_15 = "videha-2008-04-15"
_MAX_GLYPH_ID = 0xFFFF
_MAX_TRACE_CHARACTERS = 1_000_000
_MAX_TRACE_FIELDS = 16
_SHA256_HEX = frozenset("0123456789abcdefABCDEF")


class VidehaProfileError(ValueError):
    """Raised when input does not exactly match an audited Videha profile."""


class UnknownJanakiGlyphError(VidehaProfileError):
    """Raised when U+FFFD is paired with an unaudited Janaki glyph ID."""


def _freeze_gid_map(entries: Mapping[int, str], *, label: str) -> Mapping[int, str]:
    snapshot: dict[int, str] = {}
    for gid, target in entries.items():
        if type(gid) is not int or not (0 <= gid <= _MAX_GLYPH_ID):
            raise ValueError(f"invalid {label} glyph ID: {gid!r}")
        if type(target) is not str or not target:
            raise ValueError(f"invalid {label} target for glyph ID {gid}")
        if unicodedata.normalize("NFC", target) != target or any(
            not _is_assigned_script_codepoint(ord(character), "Devanagari") for character in target
        ):
            raise ValueError(f"invalid {label} Devanagari target for glyph ID {gid}")
        try:
            convert_tirhuta(target, strict=True)
        except ValueError as error:
            raise ValueError(f"unconvertible {label} target for glyph ID {gid}") from error
        snapshot[gid] = target
    if not snapshot or len(snapshot) != len(entries):
        raise ValueError(f"invalid or duplicate {label} glyph-ID entries")
    return MappingProxyType(snapshot)


JANAKI_GID_TO_DEVANAGARI: Mapping[int, str] = _freeze_gid_map(
    {
        56: "ट्ट",
        57: "ट्ठ",
        58: "ट्य",
        60: "ठ्य",
        63: "द्म",
        64: "द्य",
        65: "ह्ण",
        66: "ह्न",
        67: "ह्म",
        68: "ह्य",
        69: "ह्व",
        70: "क्ष्म",
        71: "क्ष्य",
        74: "स्थ्य",
        75: "क्ख",
        76: "क्च",
        77: "क्ट",
        78: "क्त",
        81: "क्म",
        82: "क्ल",
        83: "क्व",
        84: "क्श",
        85: "ख्न",
        86: "ख्य",
        88: "ग्न",
        89: "च्च",
        90: "च्य",
        92: "ज्व",
        94: "त्क",
        96: "त्थ",
        97: "त्न",
        98: "त्प",
        100: "त्म",
        101: "त्य",
        102: "त्व",
        103: "त्स",
        105: "ध्य",
        107: "न्ध",
        108: "न्य",
        109: "न्स",
        113: "फ्ल",
        114: "ब्य",
        116: "भ्य",
        118: "म्य",
        120: "म्स",
        121: "म्ह",
        122: "ल्द",
        123: "ल्प",
        124: "ल्ब",
        126: "ल्म",
        127: "ल्य",
        128: "ल्व",
        129: "ल्स",
        130: "ल्ह",
        131: "व्य",
        134: "श्च",
        135: "श्व",
        136: "ष्क",
        137: "ष्ट",
        138: "ष्ठ",
        139: "ष्ण",
        140: "ष्प",
        142: "ष्म",
        143: "ष्य",
        146: "स्क",
        147: "स्ख",
        148: "स्न",
        149: "स्म",
        150: "स्य",
        151: "स्ल",
        152: "स्व",
        153: "स्स",
        156: "रु",
        157: "रू",
        167: "ण्",
        172: "न्",
        213: "क्र",
        214: "ङ्ग",
        216: "ह्ल",
        217: "क्य",
        218: "क्स",
        219: "घ्न",
        221: "च्छ",
        222: "ज्ज",
        223: "ज्य",
        224: "ञ्च",
        230: "ग्र",
        231: "घ्र",
        237: "ट्र",
        239: "ड्र",
        241: "त्र",
        243: "ध्र",
        245: "प्र",
        246: "फ्र",
        247: "ब्र",
        248: "भ्र",
        249: "म्र",
        250: "व्र",
        251: "श्र",
        252: "स्र",
        253: "ह्र",
        258: "तृ",
        260: "हृ",
        263: "क्क",
        264: "क्न",
        266: "ग्य",
        271: "ड्ड",
        272: "ण्ट",
        274: "ण्ड",
        276: "ण्ण",
        277: "त्त",
        278: "थ्य",
        279: "थ्व",
        282: "द्द",
        283: "द्ध",
        285: "द्भ",
        286: "द्व",
        287: "ध्व",
        289: "न्ग",
        290: "न्त",
        291: "न्द",
        292: "न्न",
        293: "न्म",
        295: "न्ह",
        296: "प्त",
        297: "प्न",
        298: "प्प",
        299: "प्ल",
        304: "ब्द",
        305: "ब्ध",
        309: "म्ब",
        310: "म्भ",
        311: "म्म",
        313: "ल्क",
        315: "ल्ल",
        317: "श्न",
        318: "श्म",
        319: "श्य",
        320: "स्ट",
        321: "स्त",
        322: "स्थ",
        323: "स्प",
        340: "ग्ध",
        351: "ण्य",
        352: "ण्व",
        367: "म्प",
        369: "म्ल",
        370: "य्य",
        373: "श्ल",
        404: "र्ग",
        419: "णे",
        424: "ने",
        457: "नै",
        481: "णो",
        486: "नो",
        519: "नौ",
        533: "क्षे",
        541: "नु",
        593: "द्र",
        596: "ग्रे",
        603: "ट्रे",
        607: "त्रे",
        611: "प्रे",
        617: "श्रे",
    },
    label="Videha issue 001",
)

JANAKI_GID_EXTENSION_2008_04_15: Mapping[int, str] = _freeze_gid_map(
    {
        51: "ङ्क",
        53: "ङ्घ",
        106: "न्थ",
        111: "प्य",
        119: "म्व",
        155: "त्र्",
        215: "ड्य",
        220: "घ्य",
        226: "ञ्ज",
        235: "ज्र",
        244: "न्र",
        259: "भृ",
        267: "ग्व",
        273: "ण्ठ",
        281: "द्घ",
        294: "न्व",
        301: "प्स",
        303: "ब्ज",
        306: "ब्ब",
        308: "म्न",
        312: "य्व",
        314: "ल्ग",
        316: "श्छ",
        324: "स्फ",
        332: "ग्ग",
        344: "ग्ल",
        345: "ङ्म",
        355: "न्ख",
        359: "न्फ",
        388: "त्म्य",
        414: "ञे",
        539: "णु",
        612: "फ्रे",
        613: "ब्रे",
    },
    label="Videha 2008-04-15 extension",
)

if set(JANAKI_GID_TO_DEVANAGARI).intersection(JANAKI_GID_EXTENSION_2008_04_15):
    raise ValueError("Videha base and 2008-04-15 extension glyph IDs overlap")

JANAKI_GID_TO_DEVANAGARI_2008_04_15: Mapping[int, str] = _freeze_gid_map(
    {
        **JANAKI_GID_TO_DEVANAGARI,
        **JANAKI_GID_EXTENSION_2008_04_15,
    },
    label="Videha 2008-04-15 combined",
)


@dataclass(frozen=True)
class _VidehaProfile:
    pdf_sha256: str
    page_count: int
    janaki_font_sha256: frozenset[str]
    gid_map: Mapping[int, str]


def _normalize_sha256(value: object, *, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in _SHA256_HEX for character in value)
    ):
        raise VidehaProfileError(
            f"invalid {label}; expected exactly 64 ASCII hexadecimal characters"
        )
    return value.lower()


def _freeze_profiles(
    profiles: Mapping[str, _VidehaProfile],
) -> Mapping[str, _VidehaProfile]:
    snapshot: dict[str, _VidehaProfile] = {}
    for name, profile in profiles.items():
        if type(name) is not str or not name:
            raise ValueError(f"invalid Videha profile name: {name!r}")
        try:
            normalized_pdf = _normalize_sha256(profile.pdf_sha256, label="PDF SHA-256")
            normalized_fonts = frozenset(
                _normalize_sha256(value, label="Janaki font SHA-256")
                for value in profile.janaki_font_sha256
            )
        except VidehaProfileError as error:
            raise ValueError(f"invalid pinned metadata for Videha profile {name}") from error
        if normalized_pdf != profile.pdf_sha256:
            raise ValueError(f"non-canonical PDF SHA-256 for Videha profile {name}")
        if normalized_fonts != profile.janaki_font_sha256 or len(normalized_fonts) != 2:
            raise ValueError(f"invalid Janaki font set for Videha profile {name}")
        if type(profile.page_count) is not int or profile.page_count <= 0:
            raise ValueError(f"invalid page count for Videha profile {name}")
        snapshot[name] = profile
    if not snapshot or len(snapshot) != len(profiles):
        raise ValueError("invalid or duplicate Videha profiles")
    return MappingProxyType(snapshot)


_PROFILES: Mapping[str, _VidehaProfile] = _freeze_profiles(
    {
        VIDEHA_ISSUE_001: _VidehaProfile(
            pdf_sha256="91ec43fdc5ccd22cf449457f94e159650b944fea5cf35c7baec89a695d146722",
            page_count=152,
            janaki_font_sha256=frozenset(
                {
                    "b51da8d0c99bf8cc0e7ee85f18681272b0f57eb80f277838f4e2cdcaa5253755",
                    "1e3da463c92b8563d4f22db4c0f31b366668988da5008dccdff68f96a44e3501",
                }
            ),
            gid_map=JANAKI_GID_TO_DEVANAGARI,
        ),
        VIDEHA_2008_04_15: _VidehaProfile(
            pdf_sha256="740782ecf5bfa9466727029bcb7733d9c8b046c36d848b598ddc60efc1c51bd2",
            page_count=300,
            janaki_font_sha256=frozenset(
                {
                    "c64600a4edc0fa153717d66d2524c1665562eee47dd489848578e3cec1c56861",
                    "d8863d057541d5cecb862fd43e93114a9a20c6d5de519fc30f3c990962a8b18b",
                }
            ),
            gid_map=JANAKI_GID_TO_DEVANAGARI_2008_04_15,
        ),
    }
)


@dataclass(frozen=True)
class VidehaJanakiRecovery:
    """Recovered text and conversion diagnostics for one trace sequence."""

    profile: str
    devanagari_text: str
    unicode_text: str
    replacement_count: int
    recovered_gids: tuple[int, ...]
    tirhuta_char_count: int
    unmapped_codepoints: list[str]


def _profile_for_name(profile: object) -> _VidehaProfile:
    if type(profile) is not str:
        raise VidehaProfileError(
            f"invalid Videha profile name type; expected one of {sorted(_PROFILES)}"
        )
    try:
        return _PROFILES[profile]
    except KeyError as error:
        raise VidehaProfileError(
            f"unsupported Videha profile {profile!r}; expected one of {sorted(_PROFILES)}"
        ) from error


def _bounded_iterable(values: object, *, limit: int, label: str) -> tuple[object, ...]:
    if isinstance(values, (str, bytes, bytearray, Mapping)):
        raise VidehaProfileError(f"invalid {label}; expected a finite iterable")
    try:
        snapshot = tuple(islice(iter(values), limit + 1))  # type: ignore[arg-type]
    except Exception as error:
        raise VidehaProfileError(f"invalid {label}; expected a finite iterable") from error
    if len(snapshot) > limit:
        raise VidehaProfileError(f"{label} exceeds {limit} values")
    return snapshot


def _bounded_sequence(values: object, *, limit: int, label: str) -> tuple[object, ...]:
    if isinstance(values, (str, bytes, bytearray, Mapping)) or not isinstance(values, Sequence):
        raise VidehaProfileError(f"invalid {label}; expected a finite ordered sequence")
    try:
        declared_length = len(values)
    except Exception as error:
        raise VidehaProfileError(f"invalid {label}; expected a finite ordered sequence") from error
    if declared_length > limit:
        raise VidehaProfileError(f"{label} exceeds {limit} values")
    try:
        snapshot = tuple(islice(iter(values), limit + 1))
    except Exception as error:
        raise VidehaProfileError(f"invalid {label}; expected a finite ordered sequence") from error
    if len(snapshot) > limit:
        raise VidehaProfileError(f"{label} exceeds {limit} values")
    if len(snapshot) != declared_length:
        raise VidehaProfileError(f"invalid {label}; sequence length changed during validation")
    return snapshot


def _validated_font_fingerprints(values: object) -> frozenset[str]:
    snapshot = _bounded_iterable(values, limit=2, label="Janaki font fingerprint set")
    if len(snapshot) != 2:
        raise VidehaProfileError("Janaki font fingerprint set must contain exactly 2 values")
    normalized = frozenset(
        _normalize_sha256(value, label="Janaki font SHA-256") for value in snapshot
    )
    if len(normalized) != 2:
        raise VidehaProfileError("Janaki font fingerprint set must contain 2 unique values")
    return normalized


def janaki_gid_map_sha256(profile: str) -> str:
    """Return the canonical digest of one profile's functional GID map."""
    mapping = _profile_for_name(profile).gid_map
    payload = json.dumps(
        {str(gid): text for gid, text in sorted(mapping.items())},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validated_profile(
    profile: str,
    *,
    pdf_sha256: str,
    janaki_font_sha256: Iterable[str],
    page_count: int,
) -> _VidehaProfile:
    expected = _profile_for_name(profile)

    actual_pdf = _normalize_sha256(pdf_sha256, label="PDF SHA-256")
    if actual_pdf != expected.pdf_sha256:
        raise VidehaProfileError(
            f"unsupported PDF SHA-256 for {profile}: {actual_pdf}; expected {expected.pdf_sha256}"
        )
    actual_fonts = _validated_font_fingerprints(janaki_font_sha256)
    if actual_fonts != expected.janaki_font_sha256:
        raise VidehaProfileError(
            f"unsupported Janaki font fingerprint set for {profile}: "
            f"{sorted(actual_fonts)}; expected {sorted(expected.janaki_font_sha256)}"
        )
    if type(page_count) is not int:
        raise VidehaProfileError(f"invalid page count for {profile}; expected an integer")
    if page_count != expected.page_count:
        raise VidehaProfileError(
            f"unsupported page count for {profile}: {page_count}; expected {expected.page_count}"
        )
    return expected


def recover_videha_janaki_trace(
    chars: Sequence[Sequence[object]],
    *,
    profile: str,
    pdf_sha256: str,
    janaki_font_sha256: Iterable[str],
    page_count: int,
    strict: bool = False,
) -> VidehaJanakiRecovery:
    """Recover and convert one PyMuPDF Janaki get_texttrace sequence.

    Each trace character must begin with (unicode_codepoint, glyph_id, ...).
    Ordinary Unicode values pass through. U+FFFD is replaced only when its glyph
    ID is in the selected profile after caller-supplied metadata matches its
    pinned values. With ``strict=True``, downstream Tirhuta conversion raises if
    any residual codepoint remains. The trace must contain at most 1,000,000
    characters, and each character sequence must contain at most 16 fields.
    """
    expected = _validated_profile(
        profile,
        pdf_sha256=pdf_sha256,
        janaki_font_sha256=janaki_font_sha256,
        page_count=page_count,
    )
    if type(strict) is not bool:
        raise VidehaProfileError("Videha strict flag must be a Boolean")
    trace = _bounded_sequence(
        chars,
        limit=_MAX_TRACE_CHARACTERS,
        label="Videha trace character sequence",
    )
    output: list[str] = []
    recovered_gids: list[int] = []

    for index, trace_char in enumerate(trace):
        fields = _bounded_sequence(
            trace_char,
            limit=_MAX_TRACE_FIELDS,
            label=f"trace character {index} field sequence",
        )
        if len(fields) < 2:
            raise VidehaProfileError(f"trace character {index} has fewer than two fields")
        codepoint, gid = fields[:2]
        if type(codepoint) is not int or type(gid) is not int:
            raise VidehaProfileError(f"trace character {index} has invalid codepoint/GID")
        if not (0 <= codepoint <= 0x10FFFF) or 0xD800 <= codepoint <= 0xDFFF:
            raise VidehaProfileError(
                f"trace character {index} has invalid Unicode codepoint {codepoint}"
            )
        if not (0 <= gid <= _MAX_GLYPH_ID):
            raise VidehaProfileError(f"trace character {index} has invalid glyph ID {gid}")

        if codepoint != 0xFFFD:
            output.append(chr(codepoint))
            continue

        recovered = expected.gid_map.get(gid)
        if recovered is None:
            raise UnknownJanakiGlyphError(
                f"unaudited Janaki replacement glyph ID {gid} "
                f"at trace character {index} for {profile}"
            )
        output.append(recovered)
        recovered_gids.append(gid)

    devanagari_text = "".join(output)
    conversion = convert_tirhuta(devanagari_text, strict=strict)
    return VidehaJanakiRecovery(
        profile=profile,
        devanagari_text=devanagari_text,
        unicode_text=conversion.unicode_text,
        replacement_count=len(recovered_gids),
        recovered_gids=tuple(recovered_gids),
        tirhuta_char_count=conversion.tirhuta_char_count,
        unmapped_codepoints=conversion.unmapped_codepoints,
    )
