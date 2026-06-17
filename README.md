# nepal-ttf2utf

**Legacy ASCII-font → Unicode for the scripts of Nepal and its diaspora.**

Nepal's languages still live in pre-Unicode, ASCII-mapped fonts (newspapers,
government docs, textbooks). Existing converters such as
[`npttf2utf`](https://github.com/casualsnek/npttf2utf) cover a handful of **Nepali
Devanagari** fonts and silently drop the special characters that minority languages
depend on. `nepal-ttf2utf` aims to cover **every script our Nepal-language corpus
actually touches**, correctly — and it builds on `npttf2utf` rather than replacing it.

```python
from nepal_ttf2utf import convert

convert("g]kfn", font="preeti")               # 'नेपाल'
convert("k|sflzt", font="nayanepal")          # 'प्रकाशित'  (Gorkhapatra newspaper font)
convert(namdhinggo_bytes, font="namdhinggo")  # Unicode Limbu/Sirijonga (U+1900–194F)
convert(kiratrai_bytes, font="kiratrai")      # Unicode Kirat Rai   (U+16D40–16D7F)
convert(koits_bytes, font="sunuwar")          # Unicode Sunuwar     (U+11BC0–11BFF)
convert(herald_bytes, font="lepcha-sikkimherald")  # Unicode Lepcha (U+1C00–1C4F)
```

## Why it exists

- **Newspaper fonts**: `nayanepal`/`Gorkhapatra` aren't in any open converter. We
  derived + validated the extensions against real Gorkhapatra pages (97–99% clean
  Devanagari; anchors गोरखापत्रद्वारा / प्रकाशित / नेपाल / मगर correct).
- **A different script entirely**: Limbu/Sirijonga (its own Unicode block) — `npttf2utf`
  can't touch it. We bundle the SIL Namdhinggo map + the vowel/subjoined reordering.
- **Sikkim Herald minority fonts**: Kirat Rai, Sunuwar and Lepcha each ship in a legacy
  byte-encoded font with no (or only a partial) public byte→Unicode table. The maps here
  were derived from SIL's TECkit table and/or by glyph-shape identity + round-trip
  rendering against real Sikkim Herald pages. Coverage is **partial and honest** (see the
  matrix); the few unresolved bytes are surfaced, never guessed.
- **No silent drops**: `strict=True` surfaces leftover bytes (reph, conjuncts, nukta,
  the Kiranti glottal stop, and the still-unresolved Sikkim Herald bytes) instead of
  dropping them.

## Coverage

| Script | Fonts | Status |
|---|---|---|
| **Devanagari** | preeti, kantipur, sagarmatha, pcs-nepali, fontasy-himali | via tested `npttf2utf` maps |
| **Devanagari** | **nayanepal, gorkhapatra** | ✅ added + validated on real pages |
| **Limbu / Sirijonga** | **namdhinggo, sirijonga** (Namdhinggo SIL encoding) | ✅ bundled SIL map + reordering |
| **Kirat Rai** (U+16D40) | **kiratrai** (`kiratraifont` / AKRS) | ⚠️ ~93% — SIL TECkit map; 6 bytes pending |
| **Sunuwar / Jenticha** (U+11BC0) | **sunuwar** (`koits` / `kirat1`) | ⚠️ ~89% — shape-derived; 1 byte (`\|`) pending a native reader |
| **Lepcha / Róng** (U+1C00) | **lepcha-sikkimherald** (Sikkim Herald live-text font) | ⚠️ partial — shape-derived + pre-base reorder; 2 bytes (`]`, `%`) pending |
| Newa / Prachalit (U+11400) | 8-bit hack fonts | 🔜 greenfield — no public converter exists |
| Tirhuta / Mithilakshar (U+11480) | legacy fonts | 🔜 planned (small corpus) |
| Tibetan / Tamyig | — | ↪ wrap existing tools (pyewts, etc.) |
| Gurung Khema, Ol Onal | — | Unicode-native (2024) — no legacy conversion needed |
| Ranjana, Magar Akkha | — | not yet in Unicode — cannot convert |

The Kirat Rai / Sunuwar / Lepcha converters came out of real Sikkim Herald OCR work:
their legacy fonts have no published byte→Unicode table (Sunuwar, Lepcha) or only a
partial one (Kirat Rai), so the maps were derived from SIL's TECkit table and/or by
glyph-shape identity against the Unicode reference glyphs and round-trip rendering. The
coverage is honestly partial — the still-unresolved bytes are **surfaced**, not guessed:
`convert(..., strict=True)` raises on them, and `convert_kiratrai` / `convert_sunuwar` /
`convert_lepcha` return them flagged (`unmapped_codepoints` / `uncertain_bytes` /
`unmapped_bytes`). The single uncertain Sunuwar byte (`|`) needs a native-reader
transcription to settle; it is never applied by default.

## Special-character notes

- **Kiranti/Rai glottal stop** `ॽ` (U+097D): no legacy ASCII Devanagari font predating
  2005 can encode it; texts used approximations. `convert_devanagari(...,
  normalize_glottal_stop=True)` maps the common approximation to U+097D (opt-in).
- **Limbu glottal** in native script is `᤹` (U+1939 MUKPHRENG), handled by the Limbu map.

## Install / test

```bash
pip install -e .
pytest
```

## License

MIT. Bundled `Limbu.map` is SIL's (see `maps/Limbu.map.README.txt`).
