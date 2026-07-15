#!/usr/bin/env python3
"""Smoke resource-backed routes from an installed wheel, outside the source tree."""

from __future__ import annotations

import subprocess
from importlib import metadata, resources
from pathlib import Path

import nepal_ttf2utf
from nepal_ttf2utf import (
    VIDEHA_2008_04_15,
    VIDEHA_ISSUE_001,
    convert_devanagari,
    convert_jg_lepcha,
    convert_kiratrai,
    convert_lepcha,
    convert_limbu,
    convert_olchiki,
    convert_olchiki_latic,
    convert_sunuwar,
    convert_tibetanmachine,
    janaki_gid_map_sha256,
    recover_videha_janaki_trace,
    transliterate_magar_akkha,
)

EXPECTED_RESOURCES = {
    "JGLepcha.map",
    "LICENSE.magar-toolkit-MIT.txt",
    "LICENSE.py-tiblegenc-APACHE-2.0.txt",
    "LICENSE.unicode-data.txt",
    "LICENSE.wsresources-MIT.txt",
    "Limbu.map",
    "TibetanMachine.csv",
    "__init__.py",
    "kiratraifontnew.map",
    "olck_optimum.json",
    "sikkim_herald_lepcha.json",
}
EXPECTED_LICENSE_FILES = {
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "src/nepal_ttf2utf/maps/LICENSE.magar-toolkit-MIT.txt",
    "src/nepal_ttf2utf/maps/LICENSE.py-tiblegenc-APACHE-2.0.txt",
    "src/nepal_ttf2utf/maps/LICENSE.unicode-data.txt",
    "src/nepal_ttf2utf/maps/LICENSE.wsresources-MIT.txt",
}


def main() -> int:
    repository_source = Path(__file__).resolve().parents[1] / "src"
    imported_from = Path(nepal_ttf2utf.__file__).resolve()
    try:
        imported_from.relative_to(repository_source)
    except ValueError:
        pass
    else:
        raise AssertionError(f"smoke imported the source checkout: {imported_from}")

    map_package = resources.files("nepal_ttf2utf.maps")
    actual_resources = {entry.name for entry in map_package.iterdir() if entry.is_file()}
    assert actual_resources == EXPECTED_RESOURCES
    for name in EXPECTED_RESOURCES:
        assert (map_package / name).read_bytes()

    assert convert_limbu("k", strict=True) == "ᤐ"
    assert convert_kiratrai("a", strict=True).unicode_text == "𖵃"
    assert convert_jg_lepcha("k", strict=True).unicode_text == "ᰀ"
    assert convert_tibetanmachine("!", strict=True).unicode_text == "ཀ"
    assert nepal_ttf2utf.convert("!", font="tibetan-machine", strict=True) == "ཀ"
    try:
        convert_tibetanmachine("Ž", strict=True)
    except ValueError as error:
        assert "U+017D" in str(error)
    else:
        raise AssertionError("strict TibetanMachine conversion accepted defined-empty input")
    assert convert_olchiki("a", strict=True).unicode_text == "ᱟ"
    assert convert_olchiki_latic(".", strict=True).unicode_text == "ᱹ"
    assert convert_sunuwar("A", strict=True).unicode_text == "𑯖"
    assert nepal_ttf2utf.convert("A", font="kirat1", strict=True) == "𑯖"
    magar_akkha = transliterate_magar_akkha("कि", strict=True).unicode_text
    assert magar_akkha == "\U00011013\U0001103a"
    assert nepal_ttf2utf.convert(magar_akkha, font="akkha-brahmi", strict=True) == magar_akkha
    assert janaki_gid_map_sha256(VIDEHA_ISSUE_001) == (
        "ef23c410aeb6f75dedb3dffd255f00ba9da7ab66e9d4c76bc7b5ccf1af9cb963"
    )
    videha_issue = recover_videha_janaki_trace(
        ((0xFFFD, 245),),
        profile=VIDEHA_ISSUE_001,
        pdf_sha256="91ec43fdc5ccd22cf449457f94e159650b944fea5cf35c7baec89a695d146722",
        janaki_font_sha256={
            "b51da8d0c99bf8cc0e7ee85f18681272b0f57eb80f277838f4e2cdcaa5253755",
            "1e3da463c92b8563d4f22db4c0f31b366668988da5008dccdff68f96a44e3501",
        },
        page_count=152,
        strict=True,
    )
    assert videha_issue.devanagari_text == "प्र"
    videha_april = recover_videha_janaki_trace(
        ((0xFFFD, 612),),
        profile=VIDEHA_2008_04_15,
        pdf_sha256="740782ecf5bfa9466727029bcb7733d9c8b046c36d848b598ddc60efc1c51bd2",
        janaki_font_sha256={
            "c64600a4edc0fa153717d66d2524c1665562eee47dd489848578e3cec1c56861",
            "d8863d057541d5cecb862fd43e93114a9a20c6d5de519fc30f3c990962a8b18b",
        },
        page_count=300,
        strict=True,
    )
    assert videha_april.devanagari_text == "फ्रे"
    assert convert_lepcha("A", strict=True).unicode_text == "ᰀ"
    assert convert_devanagari("g]kfn", strict=True).unicode_text == "नेपाल"
    assigned_devanagari = "\u0903\U00011b00"
    assert convert_devanagari(assigned_devanagari, strict=True).unicode_text == (
        assigned_devanagari
    )
    try:
        convert_devanagari(r"s\fs", strict=True)
    except ValueError as error:
        assert "U+005C" in str(error)
        assert "U+0066" in str(error)
    else:
        raise AssertionError("strict Devanagari conversion accepted deleted input")

    package_metadata = metadata.metadata("nepal-ttf2utf")
    assert set(package_metadata.get_all("License-File") or ()) == EXPECTED_LICENSE_FILES
    completed = subprocess.run(
        ["nepal-ttf2utf", "--font", "jg-lepcha", "k"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == "ᰀ"
    assert completed.stderr == ""
    print(f"installed-wheel smoke passed from {imported_from}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
