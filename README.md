# nepal-ttf2utf

Convert text stored with legacy fonts into real Unicode for scripts used in
Nepal, Sikkim, and adjacent language communities.

The package handles seven Unicode scripts and keeps unresolved input visible.
It does not infer a mapping where the source font or corpus does not provide
enough evidence.

```python
from nepal_ttf2utf import convert

convert("g]kfn", font="preeti")              # नेपाल
convert("k|sflzt", font="nayanepal")        # प्रकाशित
convert("kfMG g'", font="namdhinggo")       # Unicode Limbu
convert("k", font="jg-lepcha")              # ᰀ
convert("मैथिली", font="janaki")            # 𑒧𑒻𑒟𑒱𑒪𑒲
```

## Coverage

| Output script | Legacy font keys | Evidence and current limits |
|---|---|---|
| Devanagari | `preeti`, `kantipur`, `sagarmatha`, `pcs-nepali`, `fontasy-himali` | Delegates to the tested `npttf2utf` maps. |
| Devanagari | `nayanepal`, `gorkhapatra` | Preeti-family map plus the two observed newspaper extension glyphs. |
| Limbu / Sirijonga | `namdhinggo`, `namdhinggosill`, `sirijonga`, `limbu` | Native reader for SIL's bundled [`Limbu.map`](src/nepal_ttf2utf/maps/Limbu.map), including Unicode-order repair. The source map leaves `#` undefined. |
| Kirat Rai | `kiratrai`, `kiratraifont`, `akrs` | Native reader for SIL's [`kiratraifontnew.map`](src/nepal_ttf2utf/maps/kiratraifontnew.map). Seven corpus bytes—`f R x F I L \`—remain unresolved. |
| Sunuwar / Jenticha | `sunuwar`, `jenticha`, `koits`, `kirat1` | Glyph- and corpus-derived map. Byte `\|` remains uncertain between two characters and is not applied by default. |
| Lepcha / Róng | `jg-lepcha`, `jglepcha`, `lepcha-jg` | Complete native forward reader for SIL's two-pass [`JGLepcha.map`](src/nepal_ttf2utf/maps/JGLepcha.map). |
| Lepcha / Róng | `lepcha-sikkimherald`, `lepcha`, `sikkimherald-lepcha` | Corpus-derived Sikkim Herald layout. `]`, `%`, and six rare punctuation bytes remain unresolved. |
| Ol Chiki | `olck-optimum`, `olchiki-optimum`, `olchiki`, `aale-chhatka` | All observed letter, mark, digit, and `\|` punctuation bytes in the Optimum layout are confirmed. `OLCKLatic-*` is a different, unsupported layout. |
| Tirhuta / Mithilakshar | `janaki`, `tirhuta`, `mithilakshar` | Conservative Janaki conversion from semantically corresponding Devanagari codepoints, with observed visual-order repairs. In the validation corpus, 4,467 of 6,391 spans converted without leftovers; broken PDF replacement characters remain unrecoverable. |

The result of `supported_fonts()` is the authoritative list of accepted keys.
Font names are case-insensitive.

### Formats not mapped

- The Newa material examined for this project already contains true Unicode
  Newa; it does not establish a legacy-byte mapping.
- The remaining Tibetan corpus needs its source font/encoding identified before
  a converter can be selected or derived.
- Ranjana and Magar Akkha do not yet have standardized Unicode encodings, so a
  Unicode converter cannot be provided.

These are evidence gaps, not placeholder mappings. A short native-reader
transcription containing the unresolved Kirat Rai, Sunuwar, or Herald Lepcha
bytes would be enough to continue those derivations.

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
from nepal_ttf2utf import convert_kiratrai, convert_tirhuta

result = convert_kiratrai(legacy_text)
print(result.unicode_text, result.unmapped_codepoints)

result = convert_tirhuta(janaki_text)
print(result.prebase_i_moves, result.reph_moves, result.unmapped_codepoints)
```

Available detailed entry points are `convert_devanagari`, `convert_limbu`,
`convert_kiratrai`, `convert_sunuwar`, `convert_lepcha`, `convert_jg_lepcha`,
`convert_olchiki`, and `convert_tirhuta`. `convert_limbu` retains its original
string return type; use `LimbuConverter.convert()` for its detailed result.

The low-level Sunuwar converter has an `apply_uncertain=True` research option
for byte `\|`. It is intentionally off by default.

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
input. Output goes to standard output unless `--output-file` is supplied.
Use `python -m nepal_ttf2utf` if the console script is not on `PATH`.

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
reordering, strict-mode failures, already-Unicode passthrough, CLI behavior, and
mapping-resource validation.

## Licenses

The original package source is MIT licensed; see [`LICENSE`](LICENSE). The SIL
mapping resources are MIT licensed and retain their notices. Devanagari support
depends on GPL-3.0-licensed `npttf2utf`. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for the distribution details.
