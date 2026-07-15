# Mapping evidence

This document records the evidence threshold for mappings that are not already
defined by a public conversion table. Exact outline identity, labeled regional
glyphs, or native-reader evidence can establish a mapping. A nearest visual
match by itself cannot.

## Structural whitespace invariant

ASCII space, TAB, CR, and LF delimit words, columns, and lines; they are not
script-font glyph assignments. Every legacy route therefore preserves those
four characters byte-for-codepoint and in their original order. This includes
mixed LF, CRLF, and lone-CR input, and strict conversion does not report them as
unresolved.

The invariant is tested through the public dispatcher for all eleven legacy
routes: Devanagari, Limbu, canonical and Herald Kirat Rai, Sunuwar, Herald and
JG Lepcha, Ol Chiki Optimum and Latic, Janaki Tirhuta, and TibetanMachine.
Detailed-result tests additionally require empty unresolved diagnostics for
the routes that previously rejected a structural separator. CLI file tests use
byte-level assertions because text-mode file APIs may apply universal-newline
translation before conversion or platform newline translation afterward.

The 29 C0 values outside the package's TAB/LF/CR structural allowlist are
diagnostics under the policy for the currently evidenced legacy routes. Every
legacy route reports them and rejects them in strict mode. Most routes preserve
the source value in lenient output. Legacy Devanagari conversion retains its
established lenient removal of those controls for corpus compatibility but
records each unique removed value in `leftover`, so the result is no longer
marked clean. The Limbu, canonical Kirat Rai, and JG Lepcha source tables
contain positional identity rules for the full C0 range; those rules determine
lenient output and contribute one matched rule to `replacement_count` per
control, while the package reports all 29 diagnostic values after conversion.
Unicode format controls outside the C0 range are not reclassified by this
policy.

Legacy Devanagari conversion also audits data removed by the installed
`npttf2utf` rule set. Assigned Unicode 17 Devanagari characters are protected
through character mapping and post-rule evaluation: dependency rules may move
them through backreferences, but may not replace or delete them. This preserves
word-level context for mixed input before NFC normalization.

Legacy-only output remains byte-inventory compatible with the dependency.
Explicit empty character-map entries and deleting-rule matches whose
participating source values make no surviving contribution appear in
`DevanagariConversion.leftover` and fail strict conversion. A match remains
clean when any participating source value contributes to surviving output,
such as the half-form-plus-AA rule used to produce a full consonant. Tests
derive all current empty entries and single- or double-source deleting-rule
cases from the installed maps, cover embedded deletion cases, pin valid
nonempty transformations and mixed word context, and exercise direct,
dispatcher, and CLI strict failures.

An exhaustive dispatcher regression covers all 29 values across the eleven
legacy routes. Detailed-result tests separately pin Preeti cleanup diagnostics
and Limbu/Kirat Rai/JG Lepcha identity output and TAB/CR/LF map counts.

The bundled `Limbu.map` has SHA-256
`2e9f6b8205a7facc0732f54c3dd4cc64f8344c7767acdbc12dd3c11cfb535f58`
and matches
[`scripts/Limb/legacy/limbu-dc/mappings/Limbu.map`](https://github.com/silnrsi/wsresources/blob/2a39449d20420fe7259f9ce5231c347432840075/scripts/Limb/legacy/limbu-dc/mappings/Limbu.map)
at SIL `wsresources` revision
`2a39449d20420fe7259f9ce5231c347432840075`. The byte-identical 5,981-byte
vendored file has 146 lines. Its forward byte pass contains 99 literal rules
and a positional 32-member C0 class, producing 131 unique flattened rules after
class expansion: 129 single-byte sources and two double-byte sources. Tests
exercise every flattened rule through Unicode-order repair and NFC.

The native reader requires exact pass, default-directive, token, and rule
syntax; valid Unicode scalar targets; and nonempty, unique class names and
source sequences in the supported forward `Byte_Unicode` subset. Pass and
default declarations must also be unique. Malformed or ambiguous rules in that
subset fail closed. The two default-substitution
directives are recognized but deliberately not applied, so undefined legacy
input retains the package's preserve-and-diagnose behavior. The map's two
Unicode reorder patterns remain implemented directly rather than interpreted
as a general `Pass(Unicode)` grammar. Reverse conversion is not implemented.

The functional-digest payload is an outer JSON array of
`[source-byte-array, target-codepoint-array]` pairs, sorted lexicographically by
source and target, serialized with separators `(",", ":")`, and encoded as
ASCII. The resulting 1,741-byte payload has SHA-256
`31c47c252d2c82e9ab0d05619e80e1e0d1897a2b55f581edf8f987897e97956e`.

## Sikkim Herald Kirat Rai

SIL's public
[`kiratraifontnew.map`](https://github.com/silnrsi/wsresources/blob/2a39449d20420fe7259f9ce5231c347432840075/scripts/Krai/legacy/kiratraifontnew/mappings/kiratraifontnew.map)
at `wsresources` revision `2a39449d20420fe7259f9ce5231c347432840075`
targets the canonical 2021 **kirat rai font new** encoding. The byte-identical
vendored map has SHA-256
`1750a51d4c40156ed49a57105d5d83905f263b7c084b7d7539ab7055a931a3c4`.
It defines eight byte classes and eight Unicode classes, which flatten to 110
single-byte rules, four double-byte rules, and one triple-byte rule with 115
unique source sequences. Tests exercise every flattened rule. The native reader
requires exact tokens and pass syntax, valid Unicode scalar targets, and unique,
nonempty class names and source sequences in the supported forward
`Byte_Unicode` subset; malformed or ambiguous rules in that subset fail closed.
The functional-digest payload is an outer JSON array of
`[source-byte-array, target-codepoint-array]` pairs, sorted lexicographically by
source and target, serialized with separators `(",", ":")`, and encoded as
ASCII. The resulting 1,592-byte payload has SHA-256
`d83310902ddacc1a04ed11c10d8b8f5ebf3af374745ca2f3c23fe9f1c49c0a8a`.

The font embedded at xref 536 in Unicode proposal
[`L2/22-043R`](https://www.unicode.org/L2/L2022/22043r-kirat-rai.pdf)
has SHA-256
`bab945f8a5fe51f9401dc2a55a54ac99f3ba2b5071ac72324a05e7ff82cb4149`.

Four recovered Sikkim Herald PDFs instead contain independent `CIDFont+F2`
subsets of an older, globally permuted layout. Their ToUnicode tables expose
ASCII values that are not the canonical font's byte assignments. Matching each
subset glyph to the proposal font by its exact FontTools `RecordingPen` command
stream **and advance width** produced:

- 43,148 extracted characters;
- 43,037 exact source-outline matches (99.7427%);
- one stable 38-letter premap shared by all four subsets;
- 108 literal `)`, `-`, `.`, or `;` characters;
- two blank backslash glyphs, normalized to spaces;
- one extracted `Z` whose embedded glyph is also blank, normalized to a space.

The `Z` occurs once in `kiratrai_issue-027.pdf`, whose SHA-256 is
`0d9fc6b9de4e781e09efb5e42d3d8f8580d8af051299fbb9c8bdb208af088747`.
It is on page 4, block 8, line 12, in extracted span `guaSlhl hr/ Z` at bounding
box `(530.0920, 588.2530, 538.6570, 603.9227)`.
The extracted font has SHA-256
`055ee4b5c8510788eff71b5019cfb4523df6a1675f62d43e11b12adec64f0213`;
its `Z` is CID/GID 61 with zero outline commands and a nonzero advance width of
1,251 font units. Treating this corpus byte as a space is therefore a rendering
fact, not a semantic assignment to the canonical font's nonblank `Z`.

The complete premap is
[`KIRATRAI_HERALD_PREMAP`](../src/nepal_ttf2utf/kiratrai.py). Six bytes that
previously looked like gaps resolve as follows:

| Herald byte | Canonical byte | Unicode | Four-PDF occurrences |
|---|---|---:|---:|
| `f` | `N` | U+16D48 NGA | 2,032 |
| `R` | `w` | U+16D50 DDA | 210 |
| `x` | `T` | U+16D53 THA | 121 |
| `F` | `g` | U+16D46 GA | 82 |
| `I` | `W` | U+16D51 DDHA | 53 |
| `L` | `$` | U+16D6D YUPI | 1 |

The layouts must remain separate. Applying the SIL map directly to Herald text
can produce valid Kirat Rai codepoints with the wrong semantics, even when none
of those six bytes occurs. The regression string `udzdle` demonstrates the
full-layout premap in the test suite.

## Sunuwar UTTHI

The final uncertain `kirat1` byte, `|`, occurs 2,748 times across eight distinct
PDFs: 1,886 medial, 780 final, 75 initial, and 7 standalone.

Richard Ishida's reviewed
[Sunuwar orthography notes](https://r12a.github.io/scripts/sunu/suz.html#writingstyles)
label separate Sikkim Herald forms for
[UTTHI](https://r12a.github.io/scripts/sunu/suz/sk-utthi.png) and
[SHYELE](https://r12a.github.io/scripts/sunu/suz/sk-shyeli.png). A 600-dpi crop
of legacy `|` from `sunuwar_01348c63.pdf`, page 1, bounding box
`(94.0076, 229.58, 100.5176, 245.204)`, is the same flowing open-2 form as
Sikkim UTTHI.

Normalized largest-component raster comparison (height 160 on a 240-pixel
canvas, grayscale threshold below 180, best translation within ±15 pixels):

| Reference | IoU |
|---|---:|
| Sikkim UTTHI | 0.7395 |
| Sikkim SHYELE | 0.3681 |
| Nepal UTTHI | 0.5399 |
| Nepal SHYELE | 0.4084 |

The regional difference is documented in Unicode
[`L2/24-022`](https://www.unicode.org/L2/L2024/24022-sunuwar-font-comp.pdf).
The character proposal
[`L2/21-157R`](https://www.unicode.org/L2/L2021/21157r-sunuwar.pdf)
confirms UTTHI `/u/`, SHYELE `/s/`, and SHYER `/ʃ/`. Corpus form `t|v|`, with
independently confirmed `t→MA` and `v→REU`, consequently reads `m-u-r-u`.
Together these establish `| → U+11BC5 SUNUWAR LETTER UTTHI`.

## Sikkim Herald Lepcha

Three formerly unresolved values now have font-specific structural evidence:

- `]`, seen 544 times, is U+1C2D LEPCHA CONSONANT SIGN K. The legacy layout
  stores the glyph visually before the following base, so conversion moves it
  into that base's logical Unicode cluster after any vowel sign.
- `%`, seen 224 times, is U+1C25 LEPCHA SUBJOINED LETTER RA. Its placement after
  the legacy nukta byte is consistent with the documented nukta-plus-RA
  retroflex sequences, and conversion emits canonical base, nukta, subjoined
  order.
- `-` has the font's literal ASCII hyphen outline and passes through as U+002D.

The remaining observed unresolved glyph values are `*`, `(`, `)`, `+`, and
`/`. The `*` glyph is a possible contextual form of U+1C24 LEPCHA SUBJOINED
LETTER YA, but it does not yet have sufficiently independent evidence for a
public mapping. JG Lepcha and Limbu use different encodings and cannot supply
these assignments. The map records this exact observed unresolved set in
[`sikkim_herald_lepcha.json`](../src/nepal_ttf2utf/maps/sikkim_herald_lepcha.json).

That 2,571-byte, 79-line resource has SHA-256
`29f55542cf67d230a6bb2f1474f85e6688b0e30e36271251a2f24af2f6d78bb1`.
It contains 65 unique source bytes mapped to 65 unique assigned Lepcha
codepoints; every bundled target is a singleton. The targets comprise 36
letters, ten nonspacing marks, nine spacing marks, and ten digits. Tests pin
every mapping's exact isolated output and classify all 256 single-byte inputs,
including structural whitespace, literal hyphen passthrough, and unsupported
input. The custom-map reader rejects duplicate or noncanonical keys, unknown
fields, empty or non-list targets, unsafe source bytes, and targets outside
the pinned assigned Lepcha repertoire.

The functional-digest payload is an outer JSON array of
`[source-byte, target-codepoint-array]` pairs sorted by source byte, serialized
with separators `(",", ":")`, and encoded as ASCII. The resulting 796-byte
payload has SHA-256
`ae61a37f712694d6e1b8541c0e9854ab3e1d2b8a5ffb4213f231bca86e029d60`.

## JG Lepcha placeholders

The package vendors SIL's exact
[`JGLepcha.map`](https://github.com/silnrsi/wsresources/blob/2a39449d20420fe7259f9ce5231c347432840075/scripts/Lepc/legacy/jg-lepcha/mappings/JGLepcha.map)
from `wsresources` revision
`2a39449d20420fe7259f9ce5231c347432840075`. The file is version 1.1, contains
272 lines, and has SHA-256
`179d172b4bd4223f40b1ddc1a0daeb6547b5ad97dc1be7df2b09f2bf45ff6b2d`.
It parses to 160 flattened byte-table rules, one contextual byte rule, 72
Unicode reorder rules, and 11 Unicode reorder classes.

All 160 byte sources are singletons. Their targets comprise 105 singleton, 47
double, and eight triple sequences. The contextual rule selects U+1C26 for
legacy `0x61` at the start of text or after any byte outside its seven-member
dependent-vowel class; the ordinary rule otherwise selects U+1C28. The 72
reorder rules contain 68 distinct patterns and four byte-identical upstream
redundancies. Their input lengths are five two-slot, 20 three-slot, 28
four-slot, 16 five-slot, and three six-slot rules.

The parsed-structure contract is a compact ASCII JSON object with sorted
keys `byte_rules`, `context_rule`, `reorder_rules`, `uncertain_sources`, and
`unicode_classes`. Byte rules are `[source-byte-array,
target-codepoint-array]` pairs in converter precedence order. The context value
is `[trigger-byte, sorted-excluded-byte-array, target-codepoint]`. Each reorder
entry contains its ordered `[class-name, variable-name]` slots and output
variable order; classes are sorted `[name, sorted-codepoint-array]` pairs.
Serialization uses sorted keys and separators `(",", ":")`. The resulting
8,730-byte payload has SHA-256
`18b020ec8f679ae35f00b0354610a8f41391e5da19d5fbcc6ab727c041bfc2a1`.

Tests execute every flattened byte rule and every declared reorder rule, exhaust
all 256 possible preceding bytes for the contextual rule, and classify every
single-byte input. The classification is 128 mapped and strict-clean values,
29 mapped C0 diagnostics, three mapped-but-uncertain placeholders, and 96
preserved unmapped values. The public constructor freezes finite rule and
class inputs and rejects empty, deleting, invalid-scalar, duplicate,
prefix-conflicting, or ambiguous rules. The source reader accepts only the
implemented forward and reorder grammar and fails closed on unsupported active
syntax rather than silently discarding it.

Three forward rules map legacy `0x3C`, `0x3D`, and `0x3E` to U+25CC DOTTED
CIRCLE. SIL annotates their source glyphs as uncertain circled `v`, `c`, and
`cv` forms. The generic placeholder does not establish semantic Unicode
assignments for those distinct glyphs. Lenient conversion therefore preserves
the source table's U+25CC output and replacement counts while recording the
source values in `uncertain_codepoints`; strict conversion rejects them. No
replacement mapping is inferred.

## OLCKOptimum Ol Chiki

The public source is [*AALE CHHATKA Pdf
e-Magazine-2023*](https://archive.org/details/aale-chhatka-pdf-e-magazine-2023),
archive filename `AALE CHHATKA Pdf e-Magazine-2023.pdf`, exact PDF SHA-256
`7588dae38adb5533e5692bf6cf6148cb5e411afa32c4f24dfe7cd1db1b9ec9b8`.
The Internet Archive item carries a publisher/uploader-applied
[Creative Commons Public Domain Mark
1.0](https://creativecommons.org/publicdomain/mark/1.0/); the mark is not CC0
and is not itself a license.

The embedded OLCKOptimum-Medium and OLCKOptimum-ExtraBlack fonts have
SHA-256 `6261843567686c67d83a508388c59e7cc4e812b8ac512cf5aace8406b5f7fd43`
and `ac77c7a64137699cafb16018e09da691439841c849033f35823cb8b133f19a04`.
Their ASCII-keyed glyph outlines, script structure, and corpus context
establish the bundled mapping. Supporting derivation artifacts are not
distributed by this package; the resulting project mapping is not presented
as an upstream encoding standard.

The 2,707-byte, 76-line
[`olck_optimum.json`](../src/nepal_ttf2utf/maps/olck_optimum.json) resource has
SHA-256
`ded27e2a142a04d086d6031b2583b8ae4306ed540f591aa8fac8a71a89e04ce7`.
It contains 63 confirmed singleton mappings and no uncertain mapping: 52
letter or modifier sources, ten digit sources, and one punctuation source.
The table has 43 unique targets; its twenty repeated targets are the documented
uppercase/lowercase outline-identical pairs.

The Optimum effective-map payload is a compact ASCII JSON array of sorted
`[source-byte, [target-codepoint]]` rows. Its 781 bytes have SHA-256
`91355469f4c726923f5b4618aaced072cf6589b0a9ee59733400b52874fcbda3`.
The corresponding 67-row Latic effective map is 830 bytes with SHA-256
`3f0337524ddf766289416bd303725e797d3a14a99c3beddb5af4c3dd56fd81c4`.
A combined sorted-key contract records the nine declared Latic overrides and,
for each layout, its sorted confirmed and uncertain pairs plus passthrough
codepoints. Compact separators `(",", ":")` produce a 1,675-byte ASCII payload
with SHA-256
`0b7aa84e70c42100fcbc517ea238038e2c4f670684cf0148152cda89fd99a3ef`.

Tests execute every effective mapping, classify all 256 byte values for both
layouts, and verify strict passthrough of all 48 assigned Unicode Ol Chiki
characters. Optimum classifies 63 mapped, four structural-whitespace, 13
byte-range passthrough, and 176 unmapped values. Latic classifies 67 mapped,
four structural-whitespace, nine byte-range passthrough, and 176 unmapped
values. Custom constructors and JSON files fail closed on unsafe sources,
unassigned targets, ambiguous confirmed/uncertain state, noncanonical or
duplicate keys, inconsistent uncertainty metadata, and unbounded iterables.

## OLCKLatic Ol Chiki

OLCKLatic is a distinct legacy layout, not an alias for OLCKOptimum. The public
2023 source contains three embedded family members:

| Embedded family | Font SHA-256 |
|---|---|
| OLCKLatic-UltraBlack | `990b5e578674ec80b3fd541d45b2b3519871a27ce362320cf31e45b9aa49ac7b` |
| OLCKLatic-Normal | `7289595f7cfce81ade5063d9e668bf9517ae2fc216c7e065b24f8421a92485e2` |
| OLCKLatic-Bold | `43c138a8ed911b3e9cd8b09dc87b676341495715a4d99a31ee8cc142385cf6c0` |

Comparison of their ASCII-keyed and Unicode-keyed glyph outlines, rather than
cmap aliases alone, establishes the crosswalk. Exact outline-plus-metric
equality covers 45 of 67 UltraBlack pairs and 55 of 67 Normal and Bold pairs;
normalized outline comparison covers the remaining correspondences. The
intermediate comparison artifacts and normalization script are not distributed,
so these counts document project derivation evidence rather than a reproducible
upstream crosswalk.

Most letters and digits retain the Optimum semantics. Latic swaps the Optimum
`v`/`V` and `w`/`W` assignments: `v` maps to U+1C76 and `w` maps to U+1C63.
Its punctuation layer maps `.`, `-`, `:`, `~`, and `|` to U+1C79, U+1C7C,
U+1C7A, U+1C7B, and U+1C7E respectively.

Using PyMuPDF `page.get_text("dict")`, selecting spans whose `font` value starts
with `OLCKLatic-`, and summing `len(span["text"])` produces 111 spans and 980
characters: 30 UltraBlack, 129 Normal, and 821 Bold. The separate Latic converter
accepts that observed set without an unmapped value. Evidence currently
establishes only the UltraBlack, Normal, and Bold weight names.

## Videha Janaki Tirhuta

The audited source is the 152-page Videha issue
`videha_01_01_08_tirhuta.pdf` from Internet Archive item
[`videha_15_04_2008_tirhuta`](https://archive.org/details/videha_15_04_2008_tirhuta),
whose metadata marks the item
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The PDF has
SHA-256
`91ec43fdc5ccd22cf449457f94e159650b944fea5cf35c7baec89a695d146722`.

Its Janaki text layer uses semantically corresponding Devanagari codepoints for
Tirhuta glyphs, but the Type0 font's incomplete `ToUnicode` table emits U+FFFD
for many precomposed conjuncts. PyMuPDF retains the glyph ID for each failed
character. The `videha-issue-001` profile in
[`videha.py`](../src/nepal_ttf2utf/videha.py) compares caller-supplied PDF hash,
page count, and complete embedded-font hash set with pinned values before
recovering a glyph. The profile recovered all 3,306 U+FFFD occurrences across
164 glyph IDs:

- 162 glyph IDs, covering 3,293 occurrences, had one unique Devanagari source
  sequence that HarfBuzz shaped to the glyph in Janaki 1.000;
- the remaining 13 occurrences were the two explicit half forms `dN.half`
  and `dNn.half`, resolved by the font's GSUB evidence to `न्` and `ण्`;
- the existing semantic remap then produced 64,896 Tirhuta-block characters;
- 30,396 of 30,581 PyMuPDF trace fragments converted without residuals
  (99.395049%); the remainder comprises 183 fragments containing U+25CC, one
  containing literal `*`, and one containing literal `^`. These are affected
  fragment counts, not established character-occurrence counts.

The embedded Janaki faces are accepted only at SHA-256
`b51da8d0c99bf8cc0e7ee85f18681272b0f57eb80f277838f4e2cdcaa5253755`
(Type0/Identity-H) and
`1e3da463c92b8563d4f22db4c0f31b366668988da5008dccdff68f96a44e3501`
(TrueType/WinAnsi). The reference Janaki 1.000 font has SHA-256
`f480331e6bb2a7cf76f95e346afda1d4eda6d64ac6597729cb5c988ea2c88694`;
its metadata credits Madan Puraskar Pustakalaya and states “All rights
reserved.” It is decode-only evidence and is not distributed by this package.
The functional map contains no font binary, glyph outline, cmap, or GSUB table.

The profile's canonical functional-map digest is
`ef23c410aeb6f75dedb3dffd255f00ba9da7ab66e9d4c76bc7b5ccf1af9cb963`.
The independent 300-page `videha-2008-04-15` profile is pinned to PDF SHA-256
`740782ecf5bfa9466727029bcb7733d9c8b046c36d848b598ddc60efc1c51bd2`
and embedded-font SHA-256 values
`c64600a4edc0fa153717d66d2524c1665562eee47dd489848578e3cec1c56861`
and `d8863d057541d5cecb862fd43e93114a9a20c6d5de519fc30f3c990962a8b18b`.
It contributes 34 additional evidenced glyph IDs for a 198-entry combined map,
whose digest is
`28ad7cf9b34f5da6c0d3d2cd03d2af2fbd159fdc1bd46dee905f2ccfe50ba326`.

`recover_videha_janaki_trace()` accepts PyMuPDF character tuples only after all
supplied profile metadata matches. Callers are responsible for securely
computing that metadata; the function does not open or hash the PDF. An unknown
PDF hash, incomplete font hash set, wrong page count, or unknown replacement
glyph ID raises a profile error. Raw U+FFFD strings without their glyph-ID
sidecar remain unrecoverable. The API does not authenticate that caller-supplied
tuples came from the named file or span. By default it preserves downstream
Tirhuta residuals and returns their sorted unique values in
`unmapped_codepoints`; `strict=True` raises `ValueError` if any residual remains.
This gate adds no glyph recovery and does not establish whole-document or
linguistic completeness.

These are aggregate text-fragment diagnostics, not audited line labels or an
OCR evaluation. The U+25CC cases still require pixel review or exclusion.

## TibetanMachine

The aligned Gorkhapatra corpus contains 95 unique pages (101 raw page hits) with
relevant Tibetan, Bhote, Mugal, Lhomi, Sherpa, or Hyolmo material. Ten pages
contain 2,380 TibetanMachine spans and 86,206 extracted characters. Conversion
uses BDRC's [`py-tiblegenc`](https://github.com/buda-base/py-tiblegenc) table.

The package vendors only the 217-row TibetanMachine subset from BDRC revision
[`0c6372e`](https://github.com/buda-base/py-tiblegenc/commit/0c6372e44be7238b611261d981355d80f68f85b8),
under Apache-2.0. The exact local subset is pinned to SHA-256
`eabcdd119ee7fa81ca221e3879745d3886ec4293b1bca72801a18498972cbc24`.
Tests verify the hash, unique 217-source inventory, every vendored source's NFC
output, and all 27 non-conflicting raw CP1252 aliases added by the parser.

Twelve vendored rows have empty targets. U+00A0 follows upstream preprocessing
and becomes an ordinary space. The other eleven source values, plus raw-byte
U+008E and U+009E aliases for U+017D and U+017E, produce empty output and are
reported through `empty_codepoints`; all thirteen effective inputs fail strict
conversion. Parser tests pin rejection of invalid or duplicate sources, missing
targets, empty tables, structurally invalid CSV, and non-Tibetan or unassigned
target values.

This is text-span conversion, not a PDF routing heuristic:

- TibetanMachine spans use the legacy converter.
- U+E010 occurs 180 times on six pages and U+E013 occurs twice on two pages.
  Both values select GID 0, the source font's visible `.notdef` placeholder,
  rather than recoverable Tibetan glyphs. The converter reports them through
  `missing_glyph_codepoints`, and strict conversion raises an error.
- Monlam Unicode, Microsoft Himalaya, Qomolangma, Jomolhari, and CTRC-HT spans
  observed in the corpus already extract as Unicode Tibetan. Their routes
  normalize NFC and validate the Tibetan block; they do not apply the
  TibetanMachine byte table.
- AnnapurnaSILNepal spans contain Unicode Devanagari. Across the aligned pages,
  201,095 characters include 155,997 Devanagari-block characters.

Production corpus conversion therefore still needs font-span segmentation,
source-vs-output render comparison, and representative Tibetan-reader review.

## Version-stable Unicode font routing

Unicode span validation is derived from Unicode 17.0
[`DerivedAge.txt`](https://www.unicode.org/Public/17.0.0/ucd/DerivedAge.txt),
[`Scripts.txt`](https://www.unicode.org/Public/17.0.0/ucd/Scripts.txt), and
[`UnicodeData.txt`](https://www.unicode.org/Public/17.0.0/ucd/UnicodeData.txt).
Unicode 17
[`ScriptExtensions.txt`](https://www.unicode.org/Public/17.0.0/ucd/ScriptExtensions.txt)
was also reviewed against
[`UAX #24`](https://www.unicode.org/reports/tr24/), which defines the property
as common script associations rather than exclusive ownership. This project
treats Script_Extensions as advisory: the validator does not use it as a
negative allowlist or a native script anchor. Common or Inherited combining
marks and punctuation remain compatible with embedded text, while only the
primary Script property contributes to `script_char_count`.

Assigned-repertoire membership is independent of Python's bundled Unicode
database: Python 3.9 predates the Unicode 16 encoding of Gurung Khema, Sunuwar,
and Kirat Rai, but it can still validate their assigned codepoints without
treating reserved positions as characters.

The eleven validator blocks contain 1,312 positions: 1,068 are assigned in the
pinned repertoire and 244 are reserved. The primary Script-property sets
contain 1,015 positions. The remaining 53 assigned positions are Common or
Inherited values in the Devanagari and Tibetan blocks; they are accepted beside
a native-script anchor but do not supply that anchor themselves. Exhaustive
tests require exact normalized output and diagnostics for every assigned and
reserved position, and exercise all 10,150 combinations of a primary-Script
position routed through one of the other ten script validators. Eight assigned
Devanagari values and 17 assigned Tibetan values expand to two script-specific
characters under NFC, so `script_char_count` is checked after normalization.

The functional-contract payload is a JSON object with keys `version`,
`assigned`, `scripts`, `blocks`, and `nfc`. The three range objects map each
script name to arrays of inclusive `[start, end]` integer pairs. Each `nfc`
entry is `[decomposed-codepoint-array, composed-codepoint-array]`. Serialization
uses sorted keys, separators `(",", ":")`, and ASCII encoding. The resulting
1,836-byte payload has SHA-256
`b3afd8d2313f3f7b03975dcbd1ae058dc4f1a9977dba2d665f380a1fbb92404b`.

Invalid-value coverage includes all 29 nonstructural C0 controls, DEL, all 32
C1 controls, all 2,048 surrogate values, all 66 Unicode noncharacters, and the
boundaries of all three private-use ranges. TAB, LF, and CR remain valid
structural whitespace.

For the seven output scripts listed below, the same pinned membership determines
whether native-script Unicode can pass through a legacy converter without a
diagnostic. This check is deliberately narrower than full Unicode-span
validation: it does not impose a native-script anchor or reclassify mixed text
after conversion. It only reports a codepoint inside the declared output block
when that position is not assigned in Unicode 17. Lenient output, replacement
counts, movement counts, and block-character counts remain unchanged.

| Output script | Unicode 17 reserved positions | Legacy route variants |
|---|---|---|
| Devanagari | U+1CFB–U+1CFF, U+11B0A–U+11B5F | all seven `npttf2utf`-backed font keys |
| Limbu | U+191F, U+192C–U+192F, U+193C–U+193F, U+1941–U+1943 | Namdhinggo |
| Kirat Rai | U+16D7A–U+16D7F | canonical and Sikkim Herald |
| Sunuwar | U+11BE2–U+11BEF, U+11BFA–U+11BFF | Koĩts/Kirat1 |
| Lepcha | U+1C38–U+1C3A, U+1C4A–U+1C4C | Sikkim Herald and JG Lepcha |
| Tirhuta | U+114C8–U+114CF, U+114DA–U+114DF | Janaki, including strict Videha recovery |
| Tibetan | U+0F48, U+0F6D–U+0F70, U+0F98, U+0FBD, U+0FCD, U+0FDB–U+0FFF | TibetanMachine |

These ranges contain 194 distinct reserved positions and produce 752
route/codepoint combinations across the fifteen route variants. Exhaustive tests
require each reserved value to remain codepoint-for-codepoint identical in
lenient output, appear in the established detailed diagnostic field, and fail
direct and dispatcher strict gates with a visible `U+XXXX` label. A
representative CLI test requires the same visible diagnostic. Every assigned
position in the same seven repertoires is also exhaustively tested as valid
passthrough, including assigned Common or Inherited block values.

Fifteen decomposition inputs producing eleven canonical compositions introduced
with Gurung Khema and Kirat Rai are also pinned so validator output and both
legacy Kirat Rai layouts have stable NFC output on older Python releases.
Outside the eleven pinned script blocks, unassigned-codepoint detection
continues to use the host Python Unicode database.

The validator covers Brahmi, Devanagari, Gurung Khema, Kirat Rai, Lepcha,
Limbu, Newa, Ol Chiki, Sunuwar, Tibetan, and Tirhuta. It normalizes NFC and
reports four distinct routing failures:

- U+FFFD, private-use values, surrogates, reserved positions inside the pinned
  blocks, runtime-unassigned values, and non-text controls are invalid;
- a character with another supported Unicode Script property is reported as an
  unexpected script value; Common and Inherited marks are not assigned to one
  script merely because of their block location;
- strict mode rejects a nonempty span with no script-specific character from
  its declared script;
- Latin text, ordinary punctuation, whitespace, and ASCII digits may remain
  embedded in a valid native-script span.

Modern font-family aliases are based on cmap inventory, not visual inference.
Selected reference binaries are listed below; no font is distributed by this
package:

| Font reference | Script / assigned cmap | SHA-256 |
|---|---|---|
| [LTK Madan2](https://ltk.org.np/downloads.php) | 72 Devanagari cmap entries; family, full, and PostScript names are exactly `Madan2` | `2321a8e7ef1e87e628e115c8e34a56120b108db37f6195c6496ce9012f5042bb` |
| [SIL Namdhinggo 3.100 Regular](https://github.com/silnrsi/font-namdhinggo/releases/tag/v3.100) | Assigned Limbu characters within U+1900–U+194F | `1b46b16277e4b6784bd19306a9474281888b656e9c57233b4e7dc63bd1229d6c` |
| [Kanchenjunga Regular](https://github.com/google/fonts/tree/main/ofl/kanchenjunga) | Kirat Rai U+16D40–U+16D79 | `45609f8cc90d4733d3d1665346d359afc1a659def340d0f369121af034322ef9` |
| [Noto Sans Sunuwar Regular](https://github.com/notofonts/sunuwar) | Sunuwar U+11BC0–U+11BE1 and U+11BF0–U+11BF9 | `332bbbcbb64c42ccc0a1b79dfd557b47aa3bd88a8ffab1417dd2f6989ad67f4d` |
| [SIL Mingzat Regular](https://software.sil.org/mingzat/) | Lepcha assigned repertoire | `c1507a565a1d263c6473a2b36944d5244bfa5b6e6f6af023a3dc8c7234fedd05` |
| [Noto Sans Lepcha Regular](https://github.com/google/fonts/tree/main/ofl/notosanslepcha) | Lepcha assigned repertoire | `9624931ae8f9a8a2a45233e5486fac1a80f333a0b3a25f84d0e2484363914f84` |
| [Noto Sans Ol Chiki Variable](https://github.com/google/fonts/tree/main/ofl/notosansolchiki) | Ol Chiki U+1C50–U+1C7F | `c9c31988656f49eccec9588825ab3b5045099c2f850ef98f356f976e8a596b4d` |
| [Noto Sans Tirhuta Regular](https://github.com/google/fonts/tree/main/ofl/notosanstirhuta) | Tirhuta assigned repertoire | `ad7123ee63118b83ed2f723591e5e861baad8dd157508b8339362850c6036efe` |
| [Noto Sans Gurung Khema Regular](https://github.com/notofonts/gurung-khema) | Gurung Khema U+16100–U+16139 | `bc6f0f510c020c05aea09b170b91ebe1f48981fc3973dce4f98ba5174266692d` |

LTK labels its official [`fonts.zip`](https://ltk.org.np/downloads/fonts.zip)
archive as “Nepali Unicode Fonts” and separately distinguishes legacy Preeti,
Kantipur, JagHimali, Kanchan, and Himali input from Unicode-compatible Madan
output in the [`Conversion Tools`](https://ltk.org.np/download2.php)
description. The inspected archive has SHA-256
`0c325228d16ea798ff5b2a2ebc685fcca0237ea23f08e9336ad98905a4dc9e3e`.
Its `madan.ttf` member has the Madan2 hash and names recorded above, 112 Unicode
cmap entries in total, 72 Devanagari entries within U+0900–U+097F, and no
private-use mapping. This establishes already-Unicode Devanagari storage, not
a legacy conversion table, complete glyph coverage, rendering quality, or
corpus occurrence. The exact `madan2` route performs NFC normalization and
Unicode 17 Devanagari validation; no broader filename or weight alias is
inferred.

Madan2 is an inspected reference only. The font metadata says that its OpenType
rules and Nepali glyph sets were released under GPL, while a separate name
record carries an all-rights-reserved Madan Puraskar Pustakalaya copyright
notice; the archive contains no standalone GPL license. No font binary, glyph
data, cmap, or shaping table is distributed by this package, and the project
makes no redistribution claim.

Bare `namdhinggo` remains the legacy NamdhinggoSILL route for compatibility.
The modern Unicode family uses explicit `namdhinggo-regular` or
`namdhinggo-unicode` keys. Equivalent explicit separation applies to the
legacy and Unicode routes for Kirat Rai, Sunuwar, Lepcha, Ol Chiki, and
Tirhuta.

The Gurung Khema font confirms cmap coverage for all 58 characters assigned in
Unicode 17.0. It does not establish linguistic sample text or a mapping for the
separate Sikkim Herald `khema 2019` legacy layout. That layout remains deferred
until its semantic font audit and independent source-page reviews are complete.

## Already-Unicode Newa and Nithya Ranjana

The audited Transkribus Newa archive has SHA-256
`c2cbab1c49a9022e17982ccc957ecc3021b3eea405309ea548e4c793d650c0b1`.
Its 886 PAGE XML files contain 3,759 Unicode elements and 393,009 characters,
including 299,539 Newa-block and 82,538 Devanagari-block characters. No U+FFFD
or private-use value occurs. This establishes Unicode-span normalization and
validation; it does not establish a legacy Newa byte map.

Ek Type's [Nithya Ranjana](https://github.com/EkType/Nithya-Ranjana#readme)
provides two encoding variants. DU stores Devanagari codepoints and NU stores
Newa codepoints while both display Ranjana forms. The inspected
`NithyaRanjanaDU-Regular.otf` has SHA-256
`8a2ebe626740270ac62c52815f2237326cdc0ed137041e833b6d404f9771b92b` and
contains 78 Devanagari cmap entries, 27 ASCII entries, and no private-use
mapping. The package routes DU as Devanagari and NU as Newa. Neither route
claims a standardized Ranjana encoding; Unicode lists Ranjana among
[scripts not yet encoded](https://www.unicode.org/standard/unsupported.html).

## Magar Akkha as Unicode Brahmi

Anshuman Pandey's individual contribution
[`L2/11-144`](https://www.unicode.org/wg2/docs/n4036.pdf), submitted for WG2 and
UTC consideration, recommends unifying Magar Akkha with Brahmi unless evidence
establishes distinct characters or behavior. No evidenced legacy Akkha font,
keyboard layout, or running legacy corpus is part of this repository. A
legacy-byte map would therefore be speculative.

`transliterate_magar_akkha()` instead provides an explicit Unicode
Devanagari-to-Brahmi mapping and its reverse. The 69-entry reversible table
preserves every supported distinction by default; it includes the 67 entries
from Ampixa's MIT-licensed
[`magar-toolkit`](https://github.com/Ampixa/magar-toolkit) plus danda and double
danda. Optional minimal-inventory folding merges selected retroflex and
sibilant distinctions and is marked as lossy. The `magar-akkha-brahmi` font key
only validates text that is already encoded in the Brahmi block.
