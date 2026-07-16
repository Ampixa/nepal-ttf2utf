# Changelog

## Unreleased

- Reject every JSON numeric token in caller-supplied Sikkim Herald Lepcha and
  Ol Chiki Optimum/Latic maps before Python integer or float materialization.
  Integers, decimals, exponents, `NaN`, and infinities now produce stable,
  path-bearing validation errors across supported Python versions. Malformed
  JSON, duplicate keys, recursion, numeric-looking strings, valid maps, bundled
  resources, outputs, diagnostics, precedence, and routing are unchanged.
- Bound caller-supplied Ol Chiki Optimum and Latic JSON maps to 64 container-
  nesting levels with a string-aware scan before JSON decoding. Depth 64
  reaches normal JSON and schema validation, and valid exact 1,000,000-byte
  inputs remain accepted. Over-limit input now fails with the same deterministic
  contextual error across supported Python versions. The bundled resource, map
  schema, effective layouts, outputs, diagnostics, precedence, and routing are
  unchanged.
- Require exact built-in strings for caller-supplied JG Lepcha Unicode-class
  names and reorder identifiers and for Ol Chiki passthrough members. String
  subclasses and coercible proxies now fail before converter-side length,
  regular-expression, classification, hashing, equality, representation, or
  storage hooks. Default contracts, parsed digests, outputs, diagnostics,
  precedence, and routing are unchanged.
- Require exact built-in integers for every caller-supplied byte and Unicode
  scalar in the Kirat Rai, Limbu, JG Lepcha, Herald Lepcha, and Ol Chiki custom
  converter contracts. Integer subclasses and numeric proxies now fail before
  scalar comparison, hashing, formatting, coercion, or storage; TibetanMachine
  source-type errors follow the same hook-safe path. Default resources,
  functional digests, outputs, diagnostics, precedence, and routing are unchanged.
- Bound the canonical SIL Kirat Rai source reader to 4,096 physical lines and
  4,096 decoded codepoints per line, closing source-structure gaps within the
  existing 1,000,000-byte limit. Exact boundaries remain accepted, and the
  vendored map, functional digest, outputs, diagnostics, and routing are unchanged.
- Complete the exact built-in-string contract for public format and script
  selectors. Dispatcher and direct Devanagari fonts now share an explicit
  `TypeError`, and Unicode script names fail likewise before user-overridable
  normalization hooks. Existing built-in selector normalization, aliases,
  routes, outputs, Magar target errors, and Videha profile errors are unchanged.
- Require exact built-in strings for every public conversion and Unicode-
  validation text input, including exported converter methods. Non-string
  iterables and string subclasses now fail before routing, normalization,
  resource loading, or conversion instead of being consumed as character
  sequences. Built-in-string output, counts, diagnostics, and normalization
  are unchanged.
- Require the built-in `False` or `True` values for every public conversion and
  Unicode-validation Boolean option. Truthy and falsy substitutes now fail
  before font routing, normalization, map parsing, or resource access. Valid
  Boolean behavior, conversion output, diagnostics, and Videha's specialized
  profile-first error contract are unchanged.
- Complete the Sikkim Herald Lepcha custom-map boundary: cap mapping item
  streams, reject malformed entries and duplicate semantic source bytes,
  and normalize excessive JSON nesting to contextual validation errors. The
  bundled map, conversion output, reordering, and diagnostics are unchanged.
- Bind built artifacts to the complete 0.3.0 distribution identity: exact wheel
  and sdist names and roots, duplicate-free core metadata, Python requirement,
  README description, pure-Python wheel tag, Hatchling generator family, and a
  single structurally parsed console entry point. Installed-wheel smoke now
  checks metadata/runtime version parity and the installed entry-point set.
- Unify TibetanMachine custom construction and CSV loading so every decoded
  CP1252 source gains the same non-conflicting raw-byte alias. Replace the
  check-before-read size gate with a bounded binary read and contextual UTF-8
  validation. The vendored 217 rows, 244-entry default snapshot, outputs, and
  diagnostics are unchanged.
- Freeze the Unicode repertoire and the dispatcher's 22 route groups; reject
  non-normalized or overlapping aliases and pin all 146 supported keys, the 100
  Unicode-validation aliases, and the eleven supported script names without
  changing their contents or routing. `supported_fonts()` continues to return a
  fresh mutable copy. The inventory fingerprints describe software routing
  metadata, not font availability or independent font evidence.
- Bound the SIL JG Lepcha source reader by file, physical-line, and continued
  logical-line size; require the byte-to-Unicode pass before a nonempty Unicode
  pass; and reject unreachable reorder classes. Record immutable context-first
  and stable longest-match precedence, byte-scalar input, pass order, and
  legacy-derived reorder provenance. The vendored map, parsed digest, legacy
  output, diagnostics, and three upstream U+25CC placeholders are unchanged.
- Harden the pinned SIL Limbu two-pass parser and runtime contract: require the
  canonical defaults and pass order, validate the two supported Unicode reorder
  forms, bound map and direct-constructor structures, protect C0 and SPACE
  identity rules, and record stable longest-source-first byte-scalar matching
  with immutable per-file reorder state. The vendored map, functional and
  reorder digests, legacy output, diagnostics, and unresolved `#` and `X` are
  unchanged.
- Pin the five legacy Devanagari maps to the exact `npttf2utf` 0.3.7 raw and
  functional contracts, load them into immutable snapshots, and bound source
  and mapped post-rule segments to 4,096 codepoints. NayaNepal and Gorkhapatra
  extension glyphs now enter Preeti processing before reordering and deletion,
  correcting extension behavior while retaining the actual source in diagnostics.
- Bound and freeze the canonical SIL Kirat Rai forward-map parser and runtime
  contract, make its longest-source-first precedence explicit, exhaustively
  classify all 256 byte values, and pin the ordered byte-domain aggregate.
  The vendored map, 115-rule functional digest, legacy output, and byte
  assignments are unchanged.
- Make the Sikkim Herald Lepcha reorder contract immutable and
  provenance-safe. Assigned Lepcha punctuation and digits now end legacy
  clusters, preventing dependent signs from moving across digit boundaries;
  exhaustive interaction tests cover the unchanged 65-entry map.
- Complete the Unicode-16 NFC fallback for Gurung Khema and Kirat Rai: pin
  U+1612F's canonical combining class and the eleven immediate canonical
  decompositions, apply canonical ordering and blocked composition closure, and
  exhaust all 290 NFC equalities in the relevant Unicode 17 normalization rows.
- Restrict SIL Limbu visual-order repair to complete windows wholly emitted by
  the legacy byte pass, preserving native Limbu and mixed-provenance windows.
  Freeze and pin the parsed rules, reorder state, and dispatcher alias sets
  without changing the SIL resource, legacy-only output, counts, diagnostics,
  or unresolved legacy inputs.
- Restrict JG Lepcha visual-order repair to output wholly derived from the legacy
  byte pass, preserving genuine Unicode Lepcha and mixed-provenance match windows.
  Store the parsed byte, reorder, and class state as immutable snapshots without
  changing SIL's pinned map contract, legacy-only output, or diagnostics.
- Correct and pin the project-defined Janaki core crosswalk: reject Devanagari
  independent SHORT E/O because Tirhuta has no corresponding independent forms,
  freeze the remaining 90 mappings and 49 passthrough values, and restrict visual-order
  repair to Devanagari-derived output so genuine Unicode Tirhuta is not reordered.
  This adds no Janaki glyph assignment, recovery profile, or corpus-completeness claim.
- Freeze and pin the four-PDF Sikkim Herald Kirat Rai routing contract;
  exhaust all byte values, supported pairs, and premap triples, isolate converter
  state from public-name and canonical-rule mutation, and state the external
  derivation boundary without adding legacy assignments.
- Freeze and pin the complete distributed two-profile Videha recovery contract;
  reject coercible metadata, codepoints, glyph IDs, flags, malformed containers,
  and unbounded inputs without adding profiles or semantic glyph assignments.
- Correct eight Magar Akkha dependent-vowel targets to the semantically matching
  Brahmi characters; pin and freeze the 69-pair reversible project contract and
  its eight explicit lossy folds. Earlier generated dependent-vowel output may
  be ambiguous and should be regenerated from known source text where possible.
- Pin and exhaust the 38-source Sunuwar project contract; freeze its public and
  effective tables, require a Boolean compatibility flag, add installed-wheel
  coverage, and state the non-distributed derivation boundary explicitly.
- Pin and exhaust the 63-source OLCKOptimum and derived 67-source OLCKLatic
  contracts; harden custom constructors and JSON parsing, align dispatch aliases
  with evidenced font weights, and correct the public evidence scope.
- Pin and exhaust SIL's complete JG Lepcha forward and reorder contract; reject
  zero-progress, deleting, malformed, ambiguous, or unsupported custom rules
  without changing the three upstream U+25CC placeholder assignments.
- Pin the 65-entry Sikkim Herald Lepcha resource and its functional mapping,
  exhaustively classify every byte, and reject unsafe or ambiguous custom maps
  without assigning the five observed unresolved glyph values.
- Pin the complete Unicode 17 validator contract across all eleven scripts,
  exhaustively covering assigned, Common/Inherited, reserved, cross-script,
  control, surrogate, noncharacter, and fallback-normalization behavior.
- Exhaustively verify SIL's 131-rule Limbu map contract and reject malformed
  forward-pass syntax, invalid Unicode scalars, empty or duplicate classes,
  ambiguous sources, and unsafe direct-constructor rules.
- Pin SIL's canonical Kirat Rai map and exhaustively verify its 115 unique
  source rules; reject malformed tokens, invalid Unicode scalars, duplicate
  classes or sources, and unsupported active-pass syntax in custom maps.
- Close the complete distributed TibetanMachine contract: pin the exact 217-row
  resource and 244-entry post-alias lookup snapshot, freeze and bound custom
  tables, reject invalid sources, targets, and CP1252 alias conflicts, and
  exhaust every byte class and ordered two-entry NFC boundary without changing
  default output.
- Preserve the pinned assigned Devanagari repertoire when Unicode characters
  are mixed into legacy spans, reject all 91 reserved extension positions, and
  make explicit empty mappings and fully consumed deleting-rule inputs visible
  to strict conversion while retaining dependency-compatible legacy-byte output.
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
- Add explicit project Magar Akkha Devanagari/Brahmi transliteration, with a
  reversible supported inventory by default and explicit optional lossy folding.
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
- Set the built-in project mapping for the Sunuwar byte `|` to U+11BC5
  SUNUWAR LETTER UTTHI from project derivation informed by public regional-form
  references; the underlying legacy corpus artifacts are not distributed.
- Add a distinct converter for the globally permuted Sikkim Herald Kirat Rai
  layout. Exact outline-and-width matching resolves 43,037 of 43,148 audited
  characters; only one extracted `Z` remains unresolved.
- Add TibetanMachine text-span conversion from BDRC/UTFC's Apache-2.0 mapping
  table; keep already-Unicode Tibetan font families outside the legacy path.
- Document evidence-backed coverage and remaining unresolved byte mappings.
- Add licensing notices, clean source/wheel packaging, and continuous
  verification across supported Python versions.
