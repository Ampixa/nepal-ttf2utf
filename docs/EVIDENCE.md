# Mapping evidence

This document records the evidence threshold for mappings that are not already
defined by a public conversion table. Exact outline identity, labeled regional
glyphs, or native-reader evidence can establish a mapping. A nearest visual
match by itself cannot.

## Sikkim Herald Kirat Rai

SIL's public
[`kiratraifontnew.map`](https://github.com/silnrsi/wsresources/blob/master/scripts/Krai/legacy/kiratraifontnew/mappings/kiratraifontnew.map)
targets the canonical 2021 **kirat rai font new** encoding. The font embedded at
xref 536 in Unicode proposal
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
- one semantically unresolved extracted `Z`.

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

No new assignment passed the evidence threshold:

- `]` occurs 544 times. Its isolated shape weakly resembles U+1C2D, but its
  pre-base position and invalid double-vowel results contradict that mapping.
- `%` occurs 224 times, nearly always after the legacy nukta byte `\`; the
  companion glyph's identity remains unknown.
- `*`, `-`, `(`, `)`, `+`, and `/` lack enough font-specific evidence to call
  them either literal punctuation or script composites.

The machine-converted 132-line evaluation set excludes `]` and `%`; it is not a
native-reader transcription. JG Lepcha and Limbu use different encodings and
cannot supply these assignments. The original map records the exact unresolved
set in
[`sikkim_herald_lepcha.json`](../src/nepal_ttf2utf/maps/sikkim_herald_lepcha.json).
A native transcription of affected words or recovered original font evidence is
still required.

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
character. A hash-pinned companion audit recovered all 3,306 U+FFFD
occurrences across 164 glyph IDs:

- 162 glyph IDs, covering 3,293 occurrences, had one unique Devanagari source
  sequence that HarfBuzz shaped to the glyph in Janaki 1.000;
- the remaining 13 occurrences were the two explicit half forms `dN.half`
  and `dNn.half`, resolved by the font's GSUB evidence to `न्` and `ण्`;
- the existing semantic remap then produced 64,896 Tirhuta-block characters;
- 30,396 of 30,581 PyMuPDF trace fragments converted without residuals
  (99.395049%); the remaining fragments contain 183 U+25CC dotted-circle
  values, one literal `*`, and one literal `^`.

The embedded Janaki faces are accepted only at SHA-256
`b51da8d0c99bf8cc0e7ee85f18681272b0f57eb80f277838f4e2cdcaa5253755`
(Type0/Identity-H) and
`1e3da463c92b8563d4f22db4c0f31b366668988da5008dccdff68f96a44e3501`
(TrueType/WinAnsi). The reference Janaki 1.000 font has SHA-256
`f480331e6bb2a7cf76f95e346afda1d4eda6d64ac6597729cb5c988ea2c88694`;
its metadata credits Madan Puraskar Pustakalaya and states “All rights
reserved.” It is decode-only evidence and is not distributed by this package.
The functional map contains no font binary, glyph outline, cmap, or GSUB table.

These are aggregate text-fragment diagnostics, not audited line labels or an
OCR evaluation. The U+25CC cases still require pixel review or exclusion, and
only one issue is local, so no edition-disjoint evaluation split exists yet.

## TibetanMachine

The recovered Gorkhapatra manifests contain 81 unique pages across 41 PDFs; 44
pages include Tibetan-named fonts and 10 use TibetanMachine. One actual
TibetanMachine page converted through BDRC's
[`py-tiblegenc`](https://github.com/buda-base/py-tiblegenc) table to 13,623
characters, including 12,801 Tibetan-block characters and zero U+FFFD
replacements.

The package vendors only the 217-row TibetanMachine subset from BDRC revision
[`0c6372e`](https://github.com/buda-base/py-tiblegenc/commit/0c6372e44be7238b611261d981355d80f68f85b8),
under Apache-2.0. Every row is tested for exact output parity against that pinned
upstream revision, followed by the package's NFC normalization.

This is text-span conversion, not a PDF routing heuristic:

- TibetanMachine spans use the legacy converter.
- Monlam Unicode, Microsoft Himalaya, Qomolangma, and Jomolhari spans observed
  in the corpus already extract as Unicode Tibetan.
- Some Bhote and Sherpa pages are Devanagari despite Tibetan-looking font or
  language labels.

Production corpus conversion therefore still needs font-span segmentation,
source-vs-output render comparison, and representative Tibetan-reader review.
