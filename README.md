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
| Devanagari | `preeti`, `kantipur`, `sagarmatha`, `pcs-nepali`, `fontasy-himali` | Delegates to the tested `npttf2utf` maps. Strict diagnostics include explicit empty mappings and fully consumed deleting-rule inputs, and assigned Unicode Devanagari is preserved in mixed spans. |
| Devanagari | `nayanepal`, `gorkhapatra` | Preeti-family map plus two observed newspaper extension glyphs. |
| Devanagari | `madan2`, `annapurnasilnepal`, Noto Sans/Serif Devanagari, `nithyaranjanadu` and aliases | NFC normalization and assigned-repertoire validation for text that is already Unicode. `madan2` is the exact internal name in Language Technology Kendra's Unicode-font archive; Nithya Ranjana DU displays Ranjana glyphs over Devanagari codepoints. |
| Limbu / Sirijonga | `namdhinggo`, `namdhinggosill`, `sirijonga`, `limbu` | Native reader for SIL's bundled [`Limbu.map`](src/nepal_ttf2utf/maps/Limbu.map), including positional class rules and Unicode-order repair. The source map explicitly leaves legacy `#` undefined. |
| Limbu / Sirijonga | `namdhinggo-regular`, `namdhinggo-unicode`, Noto Sans Limbu and aliases | Unicode Limbu validation for modern Namdhinggo 3.100 and Noto fonts. Bare `namdhinggo` remains the legacy route for compatibility. |
| Kirat Rai | `kiratrai`, `kiratrai-new`, `kiratraifontnew`, `akrs`, `akrs-new` | Native reader for SIL's hash-pinned canonical 2021 [`kiratraifontnew.map`](src/nepal_ttf2utf/maps/kiratraifontnew.map). Its supported forward `Byte_Unicode` subset fails closed on malformed or ambiguous rules. |
| Kirat Rai | `kiratrai-herald`, `kiratraifont`, `sikkimherald-kiratrai` | Complete premap for the older, globally permuted Sikkim Herald layout. The only unmatched corpus glyph, legacy `Z`, is an empty glyph and normalizes to a space. |
| Kirat Rai | Kanchenjunga family and `kirat-rai-unicode` | Unicode Kirat Rai validation for the modern Unicode font family. |
| Sunuwar / Jenticha | `sunuwar`, `jenticha`, `koits`, `kirat1` | All observed script bytes are confirmed. The final `\|` byte is the Sikkim regional form of U+11BC5 UTTHI. |
| Sunuwar / Jenticha | Noto Sans Sunuwar and `sunuwar-unicode` | Unicode Sunuwar validation, independent of the older `kirat1` layout. |
| Lepcha / Róng | `jg-lepcha`, `jglepcha`, `lepcha-jg` | Native forward reader for SIL's exact two-pass [`JGLepcha.map`](src/nepal_ttf2utf/maps/JGLepcha.map). Legacy `<`, `=`, and `>` have only upstream U+25CC placeholders, so they remain uncertain and fail strict conversion. |
| Lepcha / Róng | `lepcha-sikkimherald`, `lepcha`, `sikkimherald-lepcha` | Corpus-derived Sikkim Herald layout. Legacy `]`, `%`, and `-` are resolved; only `*`, `(`, `)`, `+`, and `/` remain unmapped. |
| Lepcha / Róng | Mingzat, Noto Sans Lepcha and `lepcha-unicode` | Unicode Lepcha assigned-repertoire validation; it does not apply either legacy layout. |
| Ol Chiki | `olck-optimum`, `olchiki-optimum`, `olchiki`, `aale-chhatka` | Complete observed Optimum letter, mark, digit, and punctuation map. |
| Ol Chiki | `olck-latic`, `olcklatic`, `olchiki-latic`, and `olcklatic-` followed by `black`, `bold`, `extrablack`, `medium`, `normal`, or `ultrablack` | Separate OLCKLatic mapping, including its swapped `v`/`w` assignments and distinct punctuation. All 2,089 audited characters converted without an unmapped value. |
| Ol Chiki | Noto Sans Ol Chiki and `ol-chiki-unicode` | Unicode Ol Chiki validation without a legacy-byte pass. |
| Tirhuta / Mithilakshar | `janaki`, `tirhuta`, `mithilakshar` | Conservative Janaki conversion from semantically corresponding Devanagari codepoints, with observed visual-order repairs. Hash-pinned Videha profiles can also recover broken U+FFFD text from PyMuPDF glyph IDs. |
| Tirhuta / Mithilakshar | Noto Sans Tirhuta and `tirhuta-unicode` | Unicode Tirhuta validation, kept separate from Janaki's Devanagari-coded layout. |
| Tibetan | `tibetanmachine`, `tibetan-machine` | BDRC/UTFC's hash-pinned 217-row Apache-2.0 TibetanMachine table. Every source row and raw CP1252 alias is checked. Thirteen effective empty inputs and two source PUA `.notdef` selectors fail strict conversion. |
| Tibetan | Monlam Unicode, Microsoft Himalaya, Qomolangma, Jomolhari, CTRC-HT and aliases | NFC normalization and assigned Tibetan-repertoire validation for already-Unicode spans. |
| Newa | `newa`, `newa-unicode`, `noto-sans-newa`, `nithyaranjananu` and aliases | NFC normalization and assigned Newa-repertoire validation. Nithya Ranjana NU displays Ranjana glyphs over Newa codepoints. |
| Brahmi representation for Magar Akkha | `transliterate_magar_akkha()`; `magar-akkha-brahmi` and `akkha-brahmi` | Devanagari/Brahmi transliteration is lossless over its supported inventory, and already-Brahmi text can be validated. Optional minimal-inventory folding is explicit and lossy. This is not a legacy-font converter. |
| Gurung Khema | Noto Sans Gurung Khema and `gurung-khema-unicode` | Validation covers the 58 characters assigned in Unicode 17.0, U+16100–U+16139. No legacy-font mapping or linguistic corpus claim is made. |

The result of `supported_fonts()` is the authoritative list of normalized
routing keys. Input matching is case-insensitive, ignores surrounding
whitespace, treats `_` as `-`, and removes a leading six-letter PDF subset tag
such as `ABCDEF+`. No other family or weight names are inferred. Unknown keys
raise `ValueError`; the command-line interface exits with status 2 and points
to `--list-fonts`. The measurements and source links behind derived mappings
are recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

Already-Unicode routes use an assigned repertoire pinned to Unicode 17.0
rather than the host Python's Unicode database. This keeps Unicode 16 scripts
such as Gurung Khema, Sunuwar, and Kirat Rai valid on Python 3.9 while still
reporting reserved positions, private-use values, and characters assigned to a
different supported script. `supported_unicode_scripts()` lists all eleven
accepted validator names.

The Devanagari, Limbu, Kirat Rai, Sunuwar, Lepcha, Tirhuta, and Tibetan legacy
converters use the same pinned repertoire when native-script Unicode is mixed
into a legacy span. Assigned characters remain valid passthrough text. The 194
reserved positions in those output blocks are preserved in lenient output but
reported and rejected in strict mode. Both legacy Kirat Rai layouts also apply
the package's pinned Unicode 16 compositions, keeping NFC output stable on
older supported Python releases.

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
  Videha PDF/font fingerprint profile.
- The Gurung Khema Unicode route validates encoded characters only. The
  inventoried legacy `khema 2019` layout still lacks the completed semantic font
  audit and independent page review required for a byte converter.

The deliberately unresolved inputs are the legacy Limbu `#`, JG Lepcha `<`,
`=`, and `>` placeholders, five rare Sikkim Herald Lepcha bytes, unknown legacy
Ranjana or Magar Akkha fonts, unknown Janaki glyph IDs, the Gurung Khema legacy
layout, and two TibetanMachine `.notdef` selectors. Existing legacy converters
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
They also retain dependency-compatible legacy-byte output while recording
explicit empty mappings and deleting-rule inputs whose participating source
values make no surviving contribution in `leftover`; strict mode cannot report
those lossy cases as clean.

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
functional-map digest for reproducibility.

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
depends on GPL-3.0-licensed `npttf2utf`; the Magar Akkha transliteration map is
adapted from MIT-licensed `magar-toolkit`. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for distribution details.
The main license, third-party notice, and bundled third-party license texts are
also declared as wheel metadata license files.
