# Changelog

## Unreleased

- Declare the third-party notice and bundled license texts in wheel metadata;
  verify source, wheel, and sdist package bytes, reject draft/AppleDouble/cache
  leakage, validate wheel metadata/`RECORD`, and smoke installed resource-backed
  routes.
- Reject unknown generic-dispatcher font keys with a package-level error that
  reports the normalized key and directs discovery to `supported_fonts()` or
  `--list-fonts`; document the exact font-key normalization rules.
- Make `OLChikiLaticConverter.from_map_file()` apply the same evidenced Latic
  `v`/`w` and punctuation layer as default construction, with fixed Latic
  assignments taking precedence over base-map uncertainty; both Ol Chiki map
  factories now reject malformed JSON shapes with contextual `ValueError`s.
- Restore SIL's exact pinned JG Lepcha map and report its three explicitly
  uncertain U+25CC placeholder mappings without changing lenient output or
  replacement counts; strict conversion now rejects those source glyphs.
- Expand the positional C0 class in SIL's Limbu TECkit map so detailed
  replacement counts reflect all matched control rules while strict mode still
  diagnoses the 29 non-structural C0 values; pin the map's upstream provenance
  and include the upstream MIT license in built packages.
- Route the exact LTK `Madan2` family name through already-Unicode Devanagari
  validation without bundling the font or applying a legacy byte map.
- Apply the pinned Unicode 17 assigned repertoire to native-script passthrough
  in legacy converters, diagnosing 103 reserved positions across six output
  scripts without changing lenient text or existing count fields.
- Diagnose all 29 C0 values outside the structural allowlist across every
  legacy route and reject them in strict mode without changing lenient output.
- Add an opt-in strict residual gate to hash-pinned Videha Janaki trace
  recovery while retaining lenient residual diagnostics by default.
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
- Apply the Unicode 16 canonical compositions across Unicode validation and
  both legacy Kirat Rai layouts on older Python releases, and return canonical
  script names in diagnostics.

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
