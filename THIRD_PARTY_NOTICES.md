# Third-party notices

The original `nepal-ttf2utf` source is licensed under the MIT License in
[`LICENSE`](LICENSE).

## npttf2utf

Devanagari conversion delegates to
[`npttf2utf`](https://pypi.org/project/npttf2utf/), which is distributed under
the GNU General Public License v3.0. It is installed as a runtime dependency,
not copied into this repository. Distributors should assess the GPL's terms for
their use and distribution of the combined environment.

## SIL writing-system resources

The following mapping resources originate in
[`silnrsi/wsresources`](https://github.com/silnrsi/wsresources), which is
licensed under the MIT License:

- `src/nepal_ttf2utf/maps/Limbu.map` — copyright 2007 SIL International.
- `src/nepal_ttf2utf/maps/kiratraifontnew.map` — copyright 2021 SIL International.
- `src/nepal_ttf2utf/maps/JGLepcha.map` — SIL's JG Lepcha conversion map, version 1.1.

The files retain their source notices. The complete upstream license is bundled
as `src/nepal_ttf2utf/maps/LICENSE.wsresources-MIT.txt`. This notice is
informational and is not legal advice.

## BDRC py-tiblegenc

`src/nepal_ttf2utf/maps/TibetanMachine.csv` is the TibetanMachine subset of
BDRC's [`py-tiblegenc`](https://github.com/buda-base/py-tiblegenc) UTFC mapping
table, revision `0c6372e44be7238b611261d981355d80f68f85b8`. It is distributed
under Apache License 2.0. The complete license is bundled beside the map as
`LICENSE.py-tiblegenc-APACHE-2.0.txt`.

## Ampixa magar-toolkit

The functional Devanagari/Brahmi mapping in
`src/nepal_ttf2utf/magar_akkha.py` is adapted from Ampixa's
[`magar-toolkit`](https://github.com/Ampixa/magar-toolkit), revision
`1384258068422fe7a44ad84ecf5d3c3b4f5ecedd`. The upstream work is distributed
under the MIT License, copyright 2026 Ampixa / magar-toolkit contributors. The
complete upstream license is bundled as
`src/nepal_ttf2utf/maps/LICENSE.magar-toolkit-MIT.txt`.

## Unicode Character Database

The assigned ranges, Script-property ranges, block boundaries, and canonical
compositions are derived from Unicode 17.0 `DerivedAge.txt`, `Scripts.txt`,
`Blocks.txt`, and `UnicodeData.txt`. The Script_Extensions policy documented in
`docs/EVIDENCE.md` was reviewed against Unicode 17.0 `ScriptExtensions.txt` and
UAX #24. Copyright © 1991-2026 Unicode, Inc. The complete Unicode License V3 is
bundled as `src/nepal_ttf2utf/maps/LICENSE.unicode-data.txt`.
