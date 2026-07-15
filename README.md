# nepal-ttf2utf

Convert legacy-font text to real Unicode and safely route font spans that are
already Unicode. The package covers scripts used in Nepal, Sikkim, and adjacent
language communities without inventing mappings for unsupported fonts.

```python
from nepal_ttf2utf import convert

convert("g]kfn", font="preeti")              # नेपाल
convert("k|sflzt", font="nayanepal")        # प्रकाशित
convert("kfMG g'", font="namdhinggo")       # Unicode Limbu
convert("k", font="jg-lepcha")              # ᰀ
convert("मैथिली", font="janaki")            # 𑒧𑒻𑒟𑒱𑒪𑒲
convert('!"#$', font="tibetanmachine")       # ཀཁགང
```

## Coverage

| Output script | Font keys or API | Evidence and current limits |
|---|---|---|
| Devanagari | `preeti`, `kantipur`, `sagarmatha`, `pcs-nepali`, `fontasy-himali` | Exact `npttf2utf` 0.3.7 map bytes and functional content are validated before immutable runtime snapshots are built. Strict diagnostics include explicit empty mappings and fully consumed deleting-rule inputs, and assigned Unicode Devanagari is preserved in mixed spans. |
| Devanagari | `nayanepal`, `gorkhapatra` | Preeti-family map plus the project `ƒ`→र and `†`→् extension mappings. Extensions enter the character-map stage before Preeti's shared post-rules. |
| Devanagari | `madan2`, `annapurnasilnepal`, Noto Sans/Serif Devanagari, `nithyaranjanadu` and aliases | NFC normalization and assigned-repertoire validation for text that is already Unicode. `madan2` is the exact internal name in Language Technology Kendra's Unicode-font archive; Nithya Ranjana DU displays Ranjana glyphs over Devanagari codepoints. |
| Limbu / Sirijonga | `namdhinggo`, `namdhinggosill`, `sirijonga`, `limbu` | Bounded two-pass reader for SIL's hash-pinned [`Limbu.map`](src/nepal_ttf2utf/maps/Limbu.map), including positional byte-class rules and the map's two exact Unicode-order forms. Canonical defaults and pass order are required; malformed, ambiguous, unsupported, or over-limit maps fail closed. Longest-source-first byte matching is stable, and C0 plus SPACE mappings must remain singleton identities. Reordering applies only to complete windows emitted by the legacy byte pass; native and mixed-provenance windows are not custom reordered. The source map explicitly leaves legacy `#` and `X` undefined. |
| Limbu / Sirijonga | `namdhinggo-regular`, `namdhinggo-unicode`, Noto Sans Limbu and aliases | Unicode Limbu validation for modern Namdhinggo 3.100 and Noto fonts. Bare `namdhinggo` remains the legacy route for compatibility. |
| Kirat Rai | `kiratrai`, `kiratrai-new`, `kiratraifontnew`, `akrs`, `akrs-new` | Bounded native reader for SIL's hash-pinned canonical 2021 [`kiratraifontnew.map`](src/nepal_ttf2utf/maps/kiratraifontnew.map). Its supported forward `Byte_Unicode` subset fails closed on malformed, ambiguous, or over-limit rules; bytes absent from the map are preserved and diagnosed. |
| Kirat Rai | `kiratrai-herald`, `kiratraifont`, `sikkimherald-kiratrai` | Pinned four-PDF routing contract for the older, globally permuted Sikkim Herald subsets: 38 premap entries, 21 values forwarded to the canonical map, and two observed blank glyph inputs normalized to spaces. Unsupported bytes are preserved and diagnosed. |
| Kirat Rai | Kanchenjunga family and `kirat-rai-unicode` | Unicode Kirat Rai validation for the modern Unicode font family. |
| Sunuwar / Jenticha | `sunuwar`, `jenticha`, `koits`, `kirat1` | Pinned 38-source project contract: 28 letters, ten digits, 20 literal passthrough characters, and no uncertain mapping entries. The built-in map assigns `\|` to U+11BC5 UTTHI; it is project-derived, not a published upstream byte standard. |
| Sunuwar / Jenticha | Noto Sans Sunuwar and `sunuwar-unicode` | Unicode Sunuwar validation, independent of the older `kirat1` layout. |
| Lepcha / Róng | `jg-lepcha`, `jglepcha`, `lepcha-jg` | Bounded native reader for SIL's hash-pinned two-pass [`JGLepcha.map`](src/nepal_ttf2utf/maps/JGLepcha.map), with an independently pinned parsed contract and a fail-closed supported grammar. The byte-to-Unicode pass must precede a nonempty Unicode pass; malformed, ambiguous, unsupported, or over-limit maps are rejected. Contextual byte rules take precedence over stable longest-source matching, and Unicode reorder rules use stable longest-slot matching. Visual-order repair is limited to output wholly derived from the legacy byte pass, so genuine Unicode Lepcha and mixed-provenance windows are not custom reordered. Legacy `<`, `=`, and `>` have only upstream U+25CC placeholders, so they remain uncertain and fail strict conversion. |
| Lepcha / Róng | `lepcha-sikkimherald`, `lepcha`, `sikkimherald-lepcha` | Hash-pinned, corpus-derived Sikkim Herald layout. Legacy `]`, `%`, and `-` are resolved. Visual-order repair is limited to legacy-derived runs and cannot cross assigned Lepcha punctuation, digits, native text, or preserved input. The observed unresolved glyph bytes are `*`, `(`, `)`, `+`, and `/`; any other unsupported byte is also diagnosed. Custom maps are bounded and fail closed on malformed or ambiguous schemas. |
| Lepcha / Róng | Mingzat, Noto Sans Lepcha and `lepcha-unicode` | Unicode Lepcha assigned-repertoire validation; it does not apply either legacy layout. |
| Ol Chiki | `olck-optimum`, `olchiki-optimum`, `olchiki`, `aale-chhatka`, and the evidenced `olckoptimum-` names `extrablack` and `medium` | Hash-pinned Optimum letter, modifier, digit, and punctuation map with a fail-closed custom-map schema. |
| Ol Chiki | `olck-latic`, `olcklatic`, `olchiki-latic`, and the evidenced `olcklatic-` names `bold`, `normal`, and `ultrablack` | Separate OLCKLatic mapping, including its swapped `v`/`w` assignments and distinct punctuation. The [public 2023 source](docs/EVIDENCE.md#olckoptimum-ol-chiki), whose Public Domain Mark status is documented with the evidence, contributes 980 strictly converted characters across 111 spans. |
| Ol Chiki | Noto Sans Ol Chiki and `ol-chiki-unicode` | Unicode Ol Chiki validation without a legacy-byte pass. |
| Tirhuta / Mithilakshar | `janaki`, `tirhuta`, `mithilakshar` | Project-defined 90-source crosswalk for Devanagari-coded text from audited Janaki/Videha spans, plus a 49-character literal/structural allowlist. Pre-base-I and trailing-reph repair is limited to Devanagari-derived output. This is not a published Janaki encoding table; U+FFFD recovery requires one of the two fingerprint-gated Videha profiles. |
| Tirhuta / Mithilakshar | Noto Sans Tirhuta and `tirhuta-unicode` | Unicode Tirhuta validation, kept separate from Janaki's Devanagari-coded layout. |
| Tibetan | `tibetanmachine`, `tibetan-machine` | BDRC/UTFC's hash-pinned 217-row Apache-2.0 TibetanMachine table expands to a pinned 244-entry post-alias lookup snapshot. Custom tables are bounded to a 250-value project-permitted raw-byte and CP1252 source domain and assigned Tibetan targets. Every byte class and ordered two-entry NFC boundary is checked; thirteen effective empty inputs and two corpus-observed source PUA `.notdef` selectors fail strict conversion. |
| Tibetan | Monlam Unicode, Microsoft Himalaya, Qomolangma, Jomolhari, CTRC-HT and aliases | NFC normalization and assigned Tibetan-repertoire validation for already-Unicode spans. |
| Newa | `newa`, `newa-unicode`, `noto-sans-newa`, `nithyaranjananu` and aliases | NFC normalization and assigned Newa-repertoire validation. Nithya Ranjana NU displays Ranjana glyphs over Newa codepoints. |
| Brahmi representation for Magar Akkha | `transliterate_magar_akkha()`; `magar-akkha-brahmi` and `akkha-brahmi` | Pinned 69-pair reversible project transliteration to semantically corresponding Brahmi characters. The optional project-defined eight-pair fold is explicit and lossy. The font keys validate already-Brahmi text; this is neither a standardized Magar Akkha encoding nor a legacy-font converter. |
| Gurung Khema | Noto Sans Gurung Khema and `gurung-khema-unicode` | Validation covers the 58 characters assigned in Unicode 17.0, U+16100–U+16139. No legacy-font mapping or linguistic corpus claim is made. |

The result of `supported_fonts()` is the authoritative list of normalized
routing keys. Internally, 22 immutable route groups contain 146 collision-free
keys; 100 select Unicode validation and 46 select legacy conversion. Every key
is already a fixed point under the normalization rules and belongs to exactly
one group. `supported_fonts()` returns a fresh mutable dictionary, so caller
changes cannot alter the internal registry. Input matching is case-insensitive,
ignores surrounding whitespace, treats `_` as `-`, and removes a leading
six-letter PDF subset tag such as `ABCDEF+`. No other family or weight names are
inferred. Unknown keys raise `ValueError`; the command-line interface exits with
status 2 and points to `--list-fonts`. These inventories describe software
routing metadata; they do not assert that a font is installed or independently
establish evidence for every alias. The available measurements and source links
behind derived mappings are recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

Already-Unicode routes use an assigned repertoire pinned to Unicode 17.0
rather than the host Python's Unicode database. This keeps Unicode 16 scripts
such as Gurung Khema, Sunuwar, and Kirat Rai valid on Python 3.9 while still
reporting reserved positions, private-use values, and characters assigned to a
different supported script. `supported_unicode_scripts()` lists all eleven
accepted validator names. The pinned contract exhaustively covers all 1,068
assigned positions, 244 reserved positions, and 10,150 cross-script cases.
The Unicode-16 normalization delta is checked against all 290 NFC equalities in
the 58 Unicode 17 normalization-test rows involving Gurung Khema or Kirat Rai,
including U+1612F canonical ordering and composition closure.

The Devanagari, Limbu, Kirat Rai, Sunuwar, Lepcha, Tirhuta, and Tibetan legacy
converters use the same pinned repertoire when native-script Unicode is mixed
into a legacy span. Assigned characters remain valid passthrough text. The 194
reserved positions in those output blocks are preserved in lenient output but
reported and rejected in strict mode. Both legacy Kirat Rai layouts also apply
the package's pinned Unicode 16 normalization delta, keeping NFC output stable
on older supported Python releases.

### Encoding boundaries

- Ranjana does not have a standardized Unicode block. Nithya Ranjana DU and NU
  are supported according to the actual Devanagari or Newa codepoints stored in
  the text, so the output must not be labeled as encoded Unicode Ranjana.
- An individual script proposal for Magar Akkha recommends treating it as a
  Brahmi variant unless evidence establishes distinct encoded behavior. The
  package therefore offers explicit Brahmi transliteration, but no mapping for
  an unidentified legacy Akkha font.
- Font and language labels do not determine the output script. Some Bhote and
  Sherpa material uses Unicode Devanagari despite Tibetan-looking font or
  language labels. Conversion pipelines should route individual font spans by
  their actual encoding.
- Raw U+FFFD text extracted from a broken Janaki PDF cannot be reconstructed by
  `convert_tirhuta()`. Recovery requires PyMuPDF glyph IDs and an exact built-in
  Videha PDF/font fingerprint profile. Devanagari independent SHORT E and SHORT
  O have no corresponding independent Tirhuta forms, so U+090E and U+0912 are
  preserved and diagnosed rather than approximated.
- The Gurung Khema Unicode route validates encoded characters only. The
  inventoried legacy `khema 2019` layout still lacks the completed semantic font
  audit and independent page review required for a byte converter.

The deliberately unresolved inputs are the legacy Limbu `#` and `X`, JG Lepcha
`<`, `=`, and `>` placeholders, five observed Sikkim Herald Lepcha glyph bytes,
Janaki U+090E/U+0912 and unknown glyph IDs, unknown legacy Ranjana or Magar
Akkha fonts, the Gurung Khema legacy layout, and two TibetanMachine `.notdef`
selectors. Existing legacy converters
preserve unresolved input or emit the documented placeholder in lenient mode,
then reject the case in strict mode. TibetanMachine also has thirteen effective
defined-empty inputs: lenient mode records their deletion, while strict mode
rejects them. Unknown legacy formats have no conversion route; unknown Janaki
glyph IDs fail profile-gated recovery in both modes.

## Python API

The common API returns only the converted string:

```python
from nepal_ttf2utf import convert, supported_fonts

unicode_text = convert(legacy_text, font="kiratrai")
unicode_text = convert(legacy_text, font="kiratrai", strict=True)
fonts_by_script = supported_fonts()
```

Lenient mode generally preserves unresolved input. `strict=True` raises
`ValueError` if anything remains unresolved, making it suitable as a
corpus-cleanliness gate. The legacy Devanagari control-cleanup exception is
described below.
Every converter preserves ASCII space, TAB, CR, and LF exactly, including CRLF
and lone-CR input. CLI file conversion decodes and encodes bytes explicitly so
the host language runtime cannot normalize line endings during I/O.
The other 29 C0 control values are always diagnostics and fail strict legacy
conversion. Most routes preserve them in lenient output. Legacy Devanagari
routes retain their established lenient cleanup but now include every removed
control in `DevanagariConversion.leftover` instead of reporting a clean result.
The five base routes retain dependency-compatible legacy-byte output while
recording explicit empty mappings and deleting-rule inputs whose participating
source values make no surviving contribution in `leftover`; strict mode cannot
report those lossy cases as clean. NayaNepal and Gorkhapatra apply their two
project extension mappings before the same Preeti post-rules, so extension
glyphs participate in reordering and deletion exactly like their canonical
Preeti counterparts.

Devanagari post-rules run only when both the whitespace-free source segment
after C0 cleanup and its mapped token stream contain at most 4,096 codepoints.
Longer segments raise `ValueError` in lenient and strict modes. The bound resets
at whitespace and prevents adversarial near-miss inputs from driving unbounded
dependency-regex work.

Detailed converters expose counts and unresolved values:

```python
from nepal_ttf2utf import (
    convert_kiratrai,
    convert_olchiki_latic,
    convert_tirhuta,
    supported_unicode_scripts,
    transliterate_magar_akkha,
    validate_unicode_span,
)

result = convert_kiratrai(legacy_text)
print(result.unicode_text, result.unmapped_codepoints)

result = convert_olchiki_latic(latic_text, strict=True)
print(result.unicode_text)

result = convert_tirhuta(janaki_text)
print(result.prebase_i_moves, result.reph_moves, result.unmapped_codepoints)

result = transliterate_magar_akkha(devanagari_text, target="brahmi", strict=True)
print(result.unicode_text)

result = validate_unicode_span(newa_text, script="Newa", strict=True)
print(result.script_char_count)

print(supported_unicode_scripts())
```

`JGLepchaConversion.uncertain_codepoints` lists source values whose SIL map
contains an explicitly uncertain U+25CC placeholder rather than an established
Unicode assignment. These values retain the upstream lenient output but fail
strict conversion.

`recover_videha_janaki_trace()` is the profile-gated companion API for PyMuPDF
`get_texttrace()` character tuples. Callers must securely compute and supply a
built-in profile name, the exact PDF SHA-256, the complete embedded Janaki font
SHA-256 set, and the page count. The API compares that metadata with the pinned
profile; it does not open or hash the PDF or authenticate the provenance of the
supplied tuples. Lenient mode preserves downstream Tirhuta residuals and lists
their unique values in `unmapped_codepoints`. `strict=True` raises `ValueError`
when any such residual remains. Profile mismatches and unknown replacement
glyph IDs fail in both modes. `janaki_gid_map_sha256()` exposes the canonical
functional-map digest for reproducibility. Metadata and trace fields require
their documented built-in types: hashes are 64 hexadecimal characters, page
counts, Unicode scalars, and glyph IDs are exact integers, and `strict` is a
Boolean. Font fingerprints are bounded to exactly two unique values. Trace
input is a finite ordered sequence of at most 1,000,000 characters, with two to
16 fields per character; generators, mappings, unordered containers,
surrogates, and numeric coercion are rejected.

Available detailed entry points are `convert_devanagari`, `convert_limbu`,
`convert_kiratrai`, `convert_kiratrai_herald`, `convert_sunuwar`,
`convert_lepcha`, `convert_jg_lepcha`, `convert_olchiki`,
`convert_olchiki_latic`, `convert_tirhuta`, `convert_tibetanmachine`,
`validate_unicode_span`, `supported_unicode_scripts`,
`recover_videha_janaki_trace`, and `transliterate_magar_akkha`.
`UNICODE_REPERTOIRE_VERSION` identifies the pinned validation data.
`convert_limbu` retains its original string return type; use
`LimbuConverter.convert()` for its detailed result.

## Command line

```console
$ nepal-ttf2utf --font preeti 'g]kfn'
नेपाल
$ nepal-ttf2utf --list-fonts
akrs    Kirat Rai
...
$ nepal-ttf2utf --font jg-lepcha --input-file legacy.txt --input-encoding cp1252 --output-file unicode.txt --strict
```

With neither a positional string nor `--input-file`, the command reads standard
input. Output goes to standard output unless `--output-file` is supplied. Use
`python -m nepal_ttf2utf` if the console script is not on `PATH`.

## Development

```bash
uv sync --all-extras --dev
uv run pytest
uvx ruff check .
uvx ruff format --check .
uv build
uvx twine check dist/*
uv run --no-project python scripts/verify_artifacts.py dist
```

The tests and artifact checks cover known mappings, multi-byte rules,
visual-to-logical reordering, strict-mode failures, already-Unicode routing,
hash-pinned glyph-ID
recovery, version-stable assigned-repertoire validation, cross-script routing,
exact structural-whitespace preservation, exhaustive diagnostic C0 and
reserved-position rejection, CLI behavior, mapping-resource validation,
source-to-wheel/sdist byte parity, and isolated installed-wheel resource
loading.

## Licenses

The original package source is MIT licensed; see [`LICENSE`](LICENSE). The SIL
mapping resources are MIT licensed and retain their notices. Devanagari support
depends on GPL-3.0-licensed `npttf2utf` 0.3.7; the Magar Akkha transliteration map is
derived from MIT-licensed `magar-toolkit` with dependent-vowel targets corrected
to their Unicode character identities. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for distribution details.
The main license, third-party notice, and bundled third-party license texts are
also declared as wheel metadata license files.
