# Changelog

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
