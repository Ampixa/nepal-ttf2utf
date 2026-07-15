#!/usr/bin/env python3
"""Verify distribution contents against the repository source tree."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import stat
import sys
import tarfile
import zipfile
from email.parser import Parser
from pathlib import Path, PurePosixPath

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SOURCE = REPOSITORY_ROOT / "src" / "nepal_ttf2utf"

EXPECTED_PACKAGE_FILES = {
    "__init__.py",
    "__main__.py",
    "_controls.py",
    "cli.py",
    "devanagari.py",
    "jg_lepcha.py",
    "kiratrai.py",
    "lepcha.py",
    "limbu.py",
    "magar_akkha.py",
    "maps/JGLepcha.map",
    "maps/LICENSE.magar-toolkit-MIT.txt",
    "maps/LICENSE.py-tiblegenc-APACHE-2.0.txt",
    "maps/LICENSE.unicode-data.txt",
    "maps/LICENSE.wsresources-MIT.txt",
    "maps/Limbu.map",
    "maps/TibetanMachine.csv",
    "maps/__init__.py",
    "maps/kiratraifontnew.map",
    "maps/olck_optimum.json",
    "maps/sikkim_herald_lepcha.json",
    "olchiki.py",
    "py.typed",
    "sunuwar.py",
    "tibetan.py",
    "tirhuta.py",
    "unicode_span.py",
    "videha.py",
}
PINNED_RESOURCE_HASHES = {
    "maps/JGLepcha.map": "179d172b4bd4223f40b1ddc1a0daeb6547b5ad97dc1be7df2b09f2bf45ff6b2d",
    "maps/Limbu.map": "2e9f6b8205a7facc0732f54c3dd4cc64f8344c7767acdbc12dd3c11cfb535f58",
    "maps/TibetanMachine.csv": ("eabcdd119ee7fa81ca221e3879745d3886ec4293b1bca72801a18498972cbc24"),
    "maps/kiratraifontnew.map": (
        "1750a51d4c40156ed49a57105d5d83905f263b7c084b7d7539ab7055a931a3c4"
    ),
    "maps/sikkim_herald_lepcha.json": (
        "29f55542cf67d230a6bb2f1474f85e6688b0e30e36271251a2f24af2f6d78bb1"
    ),
}
LICENSE_FILES = (
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "src/nepal_ttf2utf/maps/LICENSE.magar-toolkit-MIT.txt",
    "src/nepal_ttf2utf/maps/LICENSE.py-tiblegenc-APACHE-2.0.txt",
    "src/nepal_ttf2utf/maps/LICENSE.unicode-data.txt",
    "src/nepal_ttf2utf/maps/LICENSE.wsresources-MIT.txt",
)
REQUIRED_SDIST_FILES = (
    ".gitignore",
    "CHANGELOG.md",
    "LICENSE",
    "README.md",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
)
EXPECTED_SDIST_DIRECTORY_FILES = {
    "docs": {"EVIDENCE.md"},
    "scripts": {"smoke_installed.py", "verify_artifacts.py"},
    "tests": {
        "test_api.py",
        "test_artifacts.py",
        "test_cli.py",
        "test_controls.py",
        "test_devanagari.py",
        "test_jg_lepcha.py",
        "test_kiratrai.py",
        "test_lepcha.py",
        "test_limbu.py",
        "test_magar_akkha.py",
        "test_olchiki.py",
        "test_reserved_codepoints.py",
        "test_sunuwar.py",
        "test_tibetan.py",
        "test_tirhuta.py",
        "test_unicode_span.py",
        "test_videha.py",
    },
}
FORBIDDEN_COMPONENTS = {".pytest_cache", ".ruff_cache", "__pycache__"}
FORBIDDEN_FILENAMES = {".DS_Store", "BLOG_DRAFT.md"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _wheel_digest(data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii")
    return "sha256=" + digest.rstrip("=")


def _is_forbidden(name: str) -> bool:
    archive_name = name[:-1] if name.endswith("/") else name
    raw_parts = archive_name.split("/")
    path = PurePosixPath(name)
    return (
        not archive_name
        or "\\" in name
        or "\x00" in name
        or path.is_absolute()
        or (len(archive_name) >= 2 and archive_name[1] == ":")
        or any(part in {"", ".", ".."} for part in raw_parts)
        or ".." in path.parts
        or any(part.startswith("._") or part in FORBIDDEN_COMPONENTS for part in path.parts)
        or path.name in FORBIDDEN_FILENAMES
        or path.suffix == ".pyc"
    )


def _source_files(directory: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(directory).as_posix()
        if not _is_forbidden(relative):
            files[relative] = path.read_bytes()
    return files


def _require_equal(actual: object, expected: object, context: str) -> None:
    if actual != expected:
        raise AssertionError(f"{context}: expected {expected!r}, got {actual!r}")


def _require_clean(names: set[str], context: str) -> None:
    forbidden = sorted(name for name in names if _is_forbidden(name))
    if forbidden:
        raise AssertionError(f"{context} contains forbidden members: {forbidden}")


def _prefixed_files(members: dict[str, bytes], prefix: str) -> dict[str, bytes]:
    return {name[len(prefix) :]: data for name, data in members.items() if name.startswith(prefix)}


def _declared_license_files(metadata: str) -> set[str]:
    message = Parser().parsestr(metadata, headersonly=True)
    return set(message.get_all("License-File", ()))


def _verify_package_files(actual: dict[str, bytes], context: str) -> None:
    expected = _source_files(PACKAGE_SOURCE)
    _require_equal(set(expected), EXPECTED_PACKAGE_FILES, "repository package file inventory")
    _require_equal(set(actual), set(expected), f"{context} package file inventory")
    for name, source_data in expected.items():
        _require_equal(actual[name], source_data, f"{context} byte parity for {name}")
    for name, expected_hash in PINNED_RESOURCE_HASHES.items():
        _require_equal(_sha256(actual[name]), expected_hash, f"{context} SHA-256 for {name}")


def _verify_record(members: dict[str, bytes], dist_info: str) -> None:
    record_name = f"{dist_info}/RECORD"
    rows = list(csv.reader(io.StringIO(members[record_name].decode("utf-8"))))
    record = {name: (digest, size) for name, digest, size in rows}
    _require_equal(len(record), len(rows), "wheel RECORD unique path count")
    _require_equal(set(record), set(members), "wheel RECORD member inventory")
    for name, data in members.items():
        digest, size = record[name]
        if name == record_name:
            _require_equal((digest, size), ("", ""), "wheel RECORD self-entry")
            continue
        _require_equal(digest, _wheel_digest(data), f"wheel RECORD digest for {name}")
        _require_equal(size, str(len(data)), f"wheel RECORD size for {name}")


def verify_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [info.filename for info in entries]
        _require_equal(len(names), len(set(names)), "wheel unique member count")
        _require_clean(set(names), "wheel")
        special = []
        for info in entries:
            if info.is_dir():
                special.append(info.filename)
                continue
            file_type = stat.S_IFMT(info.external_attr >> 16)
            if file_type not in {0, stat.S_IFREG}:
                special.append(info.filename)
        if special:
            raise AssertionError(f"wheel contains non-regular members: {special}")
        members = {info.filename: archive.read(info) for info in entries if not info.is_dir()}

    _verify_package_files(_prefixed_files(members, "nepal_ttf2utf/"), "wheel")

    dist_infos = {name.split("/", 1)[0] for name in members if ".dist-info/" in name}
    _require_equal(len(dist_infos), 1, "wheel dist-info directory count")
    dist_info = next(iter(dist_infos))
    expected_members = {f"nepal_ttf2utf/{name}" for name in EXPECTED_PACKAGE_FILES}
    expected_members.update(
        {
            f"{dist_info}/METADATA",
            f"{dist_info}/RECORD",
            f"{dist_info}/WHEEL",
            f"{dist_info}/entry_points.txt",
            *(f"{dist_info}/licenses/{name}" for name in LICENSE_FILES),
        }
    )
    _require_equal(set(members), expected_members, "wheel complete member inventory")
    metadata_name = f"{dist_info}/METADATA"
    metadata = members[metadata_name].decode("utf-8")
    declared_licenses = _declared_license_files(metadata)
    _require_equal(declared_licenses, set(LICENSE_FILES), "wheel License-File metadata")
    for relative in LICENSE_FILES:
        member = f"{dist_info}/licenses/{relative}"
        _require_equal(members[member], (REPOSITORY_ROOT / relative).read_bytes(), member)

    entry_points = members[f"{dist_info}/entry_points.txt"].decode("utf-8")
    if "nepal-ttf2utf = nepal_ttf2utf.cli:main" not in entry_points:
        raise AssertionError("wheel console entry point is missing or incorrect")
    _verify_record(members, dist_info)


def verify_sdist(path: Path) -> None:
    with tarfile.open(path, "r:*") as archive:
        entries = archive.getmembers()
        names = [member.name for member in entries]
        _require_equal(len(names), len(set(names)), "sdist unique member count")
        _require_clean(set(names), "sdist")
        special = [member.name for member in entries if not member.isfile()]
        if special:
            raise AssertionError(f"sdist contains non-regular members: {special}")
        members: dict[str, bytes] = {}
        for member in entries:
            if not member.isfile():
                continue
            extracted = archive.extractfile(member)
            if extracted is None:
                raise AssertionError(f"cannot read sdist member {member.name}")
            members[member.name] = extracted.read()

    roots = {name.split("/", 1)[0] for name in members}
    _require_equal(len(roots), 1, "sdist top-level directory count")
    root = next(iter(roots))
    expected_directories = {}
    for directory, expected_names in EXPECTED_SDIST_DIRECTORY_FILES.items():
        source_files = _source_files(REPOSITORY_ROOT / directory)
        _require_equal(
            set(source_files),
            expected_names,
            f"repository sdist {directory} file inventory",
        )
        expected_directories[directory] = source_files
    expected_members = {
        f"{root}/PKG-INFO",
        *(f"{root}/{relative}" for relative in REQUIRED_SDIST_FILES),
        *(f"{root}/src/nepal_ttf2utf/{name}" for name in EXPECTED_PACKAGE_FILES),
        *(
            f"{root}/{directory}/{name}"
            for directory, files in expected_directories.items()
            for name in files
        ),
    }
    _require_equal(set(members), expected_members, "sdist complete member inventory")

    package_info = members[f"{root}/PKG-INFO"].decode("utf-8")
    _require_equal(
        _declared_license_files(package_info),
        set(LICENSE_FILES),
        "sdist License-File metadata",
    )
    package_files = _prefixed_files(members, f"{root}/src/nepal_ttf2utf/")
    _verify_package_files(package_files, "sdist")

    for relative in REQUIRED_SDIST_FILES:
        member = f"{root}/{relative}"
        _require_equal(members[member], (REPOSITORY_ROOT / relative).read_bytes(), member)
    for directory, expected in expected_directories.items():
        actual = _prefixed_files(members, f"{root}/{directory}/")
        _require_equal(set(actual), set(expected), f"sdist {directory} inventory")
        for name, source_data in expected.items():
            _require_equal(actual[name], source_data, f"sdist byte parity for {directory}/{name}")


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        raise SystemExit("usage: verify_artifacts.py DIST_DIRECTORY")
    dist_directory = Path(arguments[0])
    wheels = sorted(path for path in dist_directory.glob("*.whl") if not _is_forbidden(path.name))
    sdists = sorted(
        path for path in dist_directory.glob("*.tar.gz") if not _is_forbidden(path.name)
    )
    _require_equal(len(wheels), 1, "wheel count")
    _require_equal(len(sdists), 1, "sdist count")
    verify_wheel(wheels[0])
    verify_sdist(sdists[0])
    print(f"verified wheel and sdist integrity in {dist_directory}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
