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

The files retain their source notices. This notice is informational and is not
legal advice.

## BDRC py-tiblegenc

`src/nepal_ttf2utf/maps/TibetanMachine.csv` is the TibetanMachine subset of
BDRC's [`py-tiblegenc`](https://github.com/buda-base/py-tiblegenc) UTFC mapping
table, revision `0c6372e44be7238b611261d981355d80f68f85b8`. It is distributed
under Apache License 2.0. The complete license is bundled beside the map as
`LICENSE.py-tiblegenc-APACHE-2.0.txt`.
