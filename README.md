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
| Devanagari | `preeti`, `kantipur`, `sagarmatha`, `pcs-nepali`, `fontasy-himali` | Delegates to the tested `npttf2utf` maps. |
| Devanagari | `nayanepal`, `gorkhapatra` | Preeti-family map plus two observed newspaper extension glyphs. |
| Devanagari | `annapurnasilnepal`, `nithyaranjanadu` and aliases | NFC normalization and script validation for text that is already Unicode. Nithya Ranjana DU displays Ranjana glyphs over Devanagari codepoints. |
| Limbu / Sirijonga | `namdhinggo`, `namdhinggosill`, `sirijonga`, `limbu` | Native reader for SIL's bundled [`Limbu.map`](src/nepal_ttf2utf/maps/Limbu.map), including Unicode-order repair. The source map explicitly leaves legacy `#` undefined. |
| Kirat Rai | `kiratrai`, `kiratrai-new`, `kiratraifontnew`, `akrs`, `akrs-new` | Native reader for SIL's canonical 2021 [`kiratraifontnew.map`](src/nepal_ttf2utf/maps/kiratraifontnew.map). |
| Kirat Rai | `kiratrai-herald`, `kiratraifont`, `sikkimherald-kiratrai` | Complete premap for the older, globally permuted Sikkim Herald layout. The only unmatched corpus glyph, legacy `Z`, is an empty glyph and normalizes to a space. |
| Sunuwar / Jenticha | `sunuwar`, `jenticha`, `koits`, `kirat1` | All observed script bytes are confirmed. The final `\|` byte is the Sikkim regional form of U+11BC5 UTTHI. |
| Lepcha / Róng | `jg-lepcha`, `jglepcha`, `lepcha-jg` | Complete native forward reader for SIL's two-pass [`JGLepcha.map`](src/nepal_ttf2utf/maps/JGLepcha.map). |
| Lepcha / Róng | `lepcha-sikkimherald`, `lepcha`, `sikkimherald-lepcha` | Corpus-derived Sikkim Herald layout. Legacy `]`, `%`, and `-` are resolved; only `*`, `(`, `)`, `+`, and `/` remain unmapped. |
| Ol Chiki | `olck-optimum`, `olchiki-optimum`, `olchiki`, `aale-chhatka` | Complete observed Optimum letter, mark, digit, and punctuation map. |
| Ol Chiki | `olck-latic`, `olcklatic-*`, `olchiki-latic` | Separate OLCKLatic mapping, including its swapped `v`/`w` assignments and distinct punctuation. All 2,089 audited characters converted without an unmapped value. |
| Tirhuta / Mithilakshar | `janaki`, `tirhuta`, `mithilakshar` | Conservative Janaki conversion from semantically corresponding Devanagari codepoints, with observed visual-order repairs. Hash-pinned Videha profiles can also recover broken U+FFFD text from PyMuPDF glyph IDs. |
| Tibetan | `tibetanmachine`, `tibetan-machine` | BDRC/UTFC's Apache-2.0 TibetanMachine table. The audited spans contain 86,206 extracted characters; two source PUA values select the font's visible `.notdef` glyph and fail strict conversion. |
| Tibetan | Monlam Unicode, Microsoft Himalaya, Qomolangma, Jomolhari, CTRC-HT and aliases | NFC normalization and Tibetan-script validation for already-Unicode spans. |
| Newa | `newa`, `newa-unicode`, `noto-sans-newa`, `nithyaranjananu` and aliases | NFC normalization and Newa-script validation. Nithya Ranjana NU displays Ranjana glyphs over Newa codepoints. |
| Brahmi representation for Magar Akkha | `transliterate_magar_akkha()`; `magar-akkha-brahmi` and `akkha-brahmi` | Devanagari/Brahmi transliteration is lossless over its supported inventory, and already-Brahmi text can be validated. Optional minimal-inventory folding is explicit and lossy. This is not a legacy-font converter. |

The result of `supported_fonts()` is the authoritative list of accepted font
keys. Font names are case-insensitive, and six-letter PDF subset prefixes such
as `ABCDEF+` are ignored. The measurements and source links behind derived
mappings are recorded in [`docs/EVIDENCE.md`](docs/EVIDENCE.md).

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

The deliberately unresolved inputs are the legacy Limbu `#`, five rare Sikkim
Herald Lepcha bytes, unknown legacy Ranjana or Magar Akkha fonts, unknown Janaki
glyph IDs, and the two TibetanMachine `.notdef` selectors. Lenient conversion
preserves them; strict conversion reports them.

## Python API

The common API returns only the converted string:

```python
from nepal_ttf2utf import convert, supported_fonts

unicode_text = convert(legacy_text, font="kiratrai")
unicode_text = convert(legacy_text, font="kiratrai", strict=True)
fonts_by_script = supported_fonts()
```

Lenient mode preserves unresolved input. `strict=True` raises `ValueError` if
anything remains unresolved, making it suitable as a corpus-cleanliness gate.

Detailed converters expose counts and unresolved values:

```python
from nepal_ttf2utf import (
    convert_kiratrai,
    convert_olchiki_latic,
    convert_tirhuta,
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
```

`recover_videha_janaki_trace()` is the fail-closed companion API for PyMuPDF
`get_texttrace()` character tuples. Callers must securely compute and supply a
built-in profile name, the exact PDF SHA-256, the complete embedded Janaki font
SHA-256 set, and the page count. The API compares that metadata with the pinned
profile; it does not open or hash the PDF. `janaki_gid_map_sha256()` exposes the
canonical functional-map digest for reproducibility.

Available detailed entry points are `convert_devanagari`, `convert_limbu`,
`convert_kiratrai`, `convert_kiratrai_herald`, `convert_sunuwar`,
`convert_lepcha`, `convert_jg_lepcha`, `convert_olchiki`,
`convert_olchiki_latic`, `convert_tirhuta`, `convert_tibetanmachine`,
`validate_unicode_span`, `recover_videha_janaki_trace`, and
`transliterate_magar_akkha`. `convert_limbu` retains its original string return
type; use `LimbuConverter.convert()` for its detailed result.

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
```

The test suite checks known mappings, multi-byte rules, visual-to-logical
reordering, strict-mode failures, already-Unicode routing, hash-pinned glyph-ID
recovery, CLI behavior, and mapping-resource validation.

## Licenses

The original package source is MIT licensed; see [`LICENSE`](LICENSE). The SIL
mapping resources are MIT licensed and retain their notices. Devanagari support
depends on GPL-3.0-licensed `npttf2utf`; the Magar Akkha transliteration map is
adapted from MIT-licensed `magar-toolkit`. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for distribution details.
