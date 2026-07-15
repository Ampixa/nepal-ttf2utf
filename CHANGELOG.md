# Changelog

## Unreleased

- Preserve space, TAB, CR, and LF exactly across every legacy converter and
  through CLI file input/output, including strict mode and mixed line endings.
- Pin already-Unicode validation to the Unicode 17.0 assigned repertoire for
  all standardized output scripts plus Gurung Khema, independent of the Python
  runtime's older Unicode database.
- Add explicit modern Unicode font routes for Namdhinggo, Kanchenjunga, Noto
  Sans Sunuwar/Lepcha/Ol Chiki/Tirhuta/Gurung Khema, and SIL Mingzat while
  keeping similarly named legacy layouts separate.
- Report private-use, reserved, and cross-script values in Unicode spans and
  reject them in strict mode.
- Apply the Unicode 16 canonical compositions for Gurung Khema and Kirat Rai
  on older Python releases, and return canonical script names in diagnostics.

## 0.3.0 — 2026-07-15

- Add a separate OLCKLatic converter for the Normal, Bold, and UltraBlack
  layouts, including the Latic-specific `v`/`w` assignments and punctuation.
- Add two hash-pinned Videha Janaki profiles that recover evidenced U+FFFD
  characters from caller-supplied PyMuPDF glyph IDs and reject unknown profile
  metadata or glyph IDs.
- Resolve the final Sikkim Herald Kirat Rai corpus value: legacy `Z` selects a
  blank spacing glyph and now normalizes to U+0020.
- Resolve Sikkim Herald Lepcha `]` as final K, `%` as subjoined RA, and `-` as a
  literal hyphen, leaving five rare layout bytes deliberately unmapped.
- Add NFC normalization and expected-script validation routes for Unicode Newa,
  Tibetan, Devanagari, and Brahmi font spans, including the actual Devanagari
  and Newa encodings used by Nithya Ranjana DU and NU.
- Add proposal-aligned Magar Akkha Devanagari/Brahmi transliteration, with a
  lossless supported inventory by default and explicit optional lossy folding.
- Report TibetanMachine U+E010 and U+E013 separately as source-font `.notdef`
  selectors and reject them in strict mode.

## 0.2.0 — 2026-07-14

- Add conservative Janaki/Devanagari-coded Tirhuta conversion, including the
  observed pre-base-I and trailing-reph extraction repairs.
- Add native conversion for Jason Glavy's JG Lepcha encoding from SIL's
  complete two-pass TECkit map.
- Add a `nepal-ttf2utf` command-line interface with file, standard-input,
  encoding, strict-mode, and font-listing support.
- Make strict mode consistently report leftover ASCII bytes across script
  converters and preserve already-Unicode script text.
- Resolve the final observed Sunuwar byte, `|`, as the Sikkim regional form of
  U+11BC5 SUNUWAR LETTER UTTHI from labeled regional-glyph and corpus evidence.
- Add a distinct converter for the globally permuted Sikkim Herald Kirat Rai
  layout. Exact outline-and-width matching resolves 43,037 of 43,148 audited
  characters; only one extracted `Z` remains unresolved.
- Add TibetanMachine text-span conversion from BDRC/UTFC's Apache-2.0 mapping
  table; keep already-Unicode Tibetan font families outside the legacy path.
- Document evidence-backed coverage and remaining unresolved byte mappings.
- Add licensing notices, clean source/wheel packaging, and continuous
  verification across supported Python versions.
