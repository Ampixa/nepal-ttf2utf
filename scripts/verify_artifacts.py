#!/usr/bin/env python3
"""Verify distribution contents against the repository source tree."""

from __future__ import annotations

import base64
import configparser
import csv
import hashlib
import io
import re
import stat
import sys
import tarfile
import zipfile
from email import policy
from email.parser import Parser
from pathlib import Path, PurePosixPath

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SOURCE = REPOSITORY_ROOT / "src" / "nepal_ttf2utf"

EXPECTED_PROJECT_NAME = "nepal-ttf2utf"
EXPECTED_PROJECT_VERSION = "0.3.0"
EXPECTED_REQUIRES_PYTHON = ">=3.9"
EXPECTED_METADATA_VERSION = "2.4"
EXPECTED_PROJECT_SUMMARY = (
    "Legacy-font conversion and Unicode span validation for scripts of Nepal and Sikkim."
)
EXPECTED_PROJECT_AUTHOR = "Ampixa"
EXPECTED_LICENSE_EXPRESSION = "MIT"
EXPECTED_DESCRIPTION_CONTENT_TYPE = "text/markdown"
EXPECTED_DIST_INFO = "nepal_ttf2utf-0.3.0.dist-info"
EXPECTED_SDIST_ROOT = "nepal_ttf2utf-0.3.0"
EXPECTED_WHEEL_FILENAME = "nepal_ttf2utf-0.3.0-py3-none-any.whl"
EXPECTED_SDIST_FILENAME = "nepal_ttf2utf-0.3.0.tar.gz"
EXPECTED_WHEEL_TAG = "py3-none-any"
EXPECTED_CONSOLE_ENTRY_POINTS = {"nepal-ttf2utf": "nepal_ttf2utf.cli:main"}
EXPECTED_PROJECT_URLS = {
    "Homepage, https://github.com/Ampixa/nepal-ttf2utf",
    "Repository, https://github.com/Ampixa/nepal-ttf2utf",
    "Issues, https://github.com/Ampixa/nepal-ttf2utf/issues",
}
EXPECTED_CLASSIFIERS = {
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Topic :: Text Processing :: Linguistic",
}
EXPECTED_KEYWORDS = {
    "brahmi",
    "devanagari",
    "gurung-khema",
    "kirat-rai",
    "legacy-font",
    "lepcha",
    "limbu",
    "magar-akkha",
    "nepal",
    "nepali",
    "newa",
    "ocr",
    "ol-chiki",
    "olcklatic",
    "preeti",
    "sikkim",
    "sirijonga",
    "sunuwar",
    "tibetan",
    "tirhuta",
    "unicode",
    "unicode-validation",
}
EXPECTED_CORE_METADATA_HEADERS = {
    "Metadata-Version",
    "Name",
    "Version",
    "Summary",
    "Project-URL",
    "Author",
    "License-Expression",
    "License-File",
    "Keywords",
    "Classifier",
    "Requires-Python",
    "Requires-Dist",
    "Provides-Extra",
    "Description-Content-Type",
}
EXPECTED_WHEEL_HEADERS = {
    "Wheel-Version",
    "Generator",
    "Root-Is-Purelib",
    "Tag",
}

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
    "maps/olck_optimum.json": ("ded27e2a142a04d086d6031b2583b8ae4306ed540f591aa8fac8a71a89e04ce7"),
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
        "unicode17_gurung_khema_kirat_rai_normalization.json",
    },
}
FORBIDDEN_COMPONENTS = {".pytest_cache", ".ruff_cache", "__pycache__"}
FORBIDDEN_FILENAMES = {".DS_Store", "BLOG_DRAFT.md"}
EXPECTED_REQUIRES_DIST = ("npttf2utf==0.3.7", "pytest>=7; extra == 'dev'")
EXPECTED_PROVIDES_EXTRA = ("dev",)


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


def _decode_utf8(data: bytes, context: str) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AssertionError(f"{context} is not valid UTF-8") from error


def _parse_headers(data: bytes, context: str):
    message = Parser(policy=policy.default).parsestr(_decode_utf8(data, context))
    if message.defects:
        raise AssertionError(f"{context} has malformed headers: {message.defects!r}")
    return message


def _single_header(message, name: str, context: str) -> str:
    values = tuple(message.get_all(name, ()))
    _require_equal(len(values), 1, f"{context} {name} count")
    return values[0]


def _verify_header_inventory(message, expected: set[str], context: str) -> None:
    actual_names = tuple(message.keys())
    expected_by_normalized = {name.casefold(): name for name in expected}
    actual_by_normalized = {name.casefold(): name for name in actual_names}
    missing = sorted(
        expected_by_normalized[name]
        for name in expected_by_normalized.keys() - actual_by_normalized.keys()
    )
    unexpected = sorted(
        actual_by_normalized[name]
        for name in actual_by_normalized.keys() - expected_by_normalized.keys()
    )
    if missing or unexpected:
        raise AssertionError(
            f"{context} header inventory: missing {missing!r}; unexpected {unexpected!r}"
        )


def _verify_core_metadata(data: bytes, context: str) -> None:
    message = _parse_headers(data, context)
    _verify_header_inventory(message, EXPECTED_CORE_METADATA_HEADERS, context)
    expected_singletons = {
        "Metadata-Version": EXPECTED_METADATA_VERSION,
        "Name": EXPECTED_PROJECT_NAME,
        "Version": EXPECTED_PROJECT_VERSION,
        "Summary": EXPECTED_PROJECT_SUMMARY,
        "Author": EXPECTED_PROJECT_AUTHOR,
        "License-Expression": EXPECTED_LICENSE_EXPRESSION,
        "Requires-Python": EXPECTED_REQUIRES_PYTHON,
        "Description-Content-Type": EXPECTED_DESCRIPTION_CONTENT_TYPE,
    }
    for name, expected in expected_singletons.items():
        _require_equal(_single_header(message, name, context), expected, f"{context} {name}")

    license_files = tuple(message.get_all("License-File", ()))
    _require_equal(
        len(license_files), len(set(license_files)), f"{context} License-File uniqueness"
    )
    _require_equal(set(license_files), set(LICENSE_FILES), f"{context} License-File metadata")
    requirements = tuple(message.get_all("Requires-Dist", ()))
    _require_equal(len(requirements), len(set(requirements)), f"{context} Requires-Dist uniqueness")
    _require_equal(
        set(requirements), set(EXPECTED_REQUIRES_DIST), f"{context} Requires-Dist metadata"
    )
    _require_equal(
        tuple(message.get_all("Provides-Extra", ())),
        EXPECTED_PROVIDES_EXTRA,
        f"{context} Provides-Extra metadata",
    )
    for name, expected in (
        ("Project-URL", EXPECTED_PROJECT_URLS),
        ("Classifier", EXPECTED_CLASSIFIERS),
    ):
        values = tuple(message.get_all(name, ()))
        _require_equal(len(values), len(set(values)), f"{context} {name} uniqueness")
        _require_equal(set(values), expected, f"{context} {name} metadata")

    serialized_keywords = _single_header(message, "Keywords", context)
    keywords = tuple(part.strip() for part in serialized_keywords.split(","))
    _require_equal(len(keywords), len(set(keywords)), f"{context} Keywords uniqueness")
    _require_equal(set(keywords), EXPECTED_KEYWORDS, f"{context} Keywords metadata")
    _require_equal(
        message.get_payload(),
        (REPOSITORY_ROOT / "README.md").read_text("utf-8"),
        f"{context} description body",
    )


def _verify_wheel_metadata(data: bytes) -> None:
    context = "wheel WHEEL metadata"
    message = _parse_headers(data, context)
    _verify_header_inventory(message, EXPECTED_WHEEL_HEADERS, context)
    _require_equal(
        _single_header(message, "Wheel-Version", context),
        "1.0",
        f"{context} Wheel-Version",
    )
    _require_equal(
        _single_header(message, "Root-Is-Purelib", context),
        "true",
        f"{context} Root-Is-Purelib",
    )
    _require_equal(
        tuple(message.get_all("Tag", ())),
        (EXPECTED_WHEEL_TAG,),
        f"{context} Tag",
    )
    generator = _single_header(message, "Generator", context)
    generator_version = generator.removeprefix("hatchling ")
    if (
        not generator.startswith("hatchling ")
        or re.fullmatch(
            r"\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?(?:\.post\d+)?(?:\.dev\d+)?"
            r"(?:\+[a-z0-9]+(?:[._-][a-z0-9]+)*)?",
            generator_version,
            flags=re.IGNORECASE,
        )
        is None
    ):
        raise AssertionError(f"{context} Generator is not a versioned hatchling identifier")
    _require_equal(message.get_payload(), "", f"{context} payload")


def _verify_entry_points(data: bytes) -> None:
    context = "wheel entry_points.txt"
    parser = configparser.ConfigParser(
        interpolation=None,
        strict=True,
        delimiters=("=",),
        allow_no_value=False,
        empty_lines_in_values=False,
    )
    parser.optionxform = str
    try:
        parser.read_string(_decode_utf8(data, context))
    except configparser.Error as error:
        raise AssertionError(f"{context} is malformed: {error}") from error
    _require_equal(parser.defaults(), {}, f"{context} defaults")
    _require_equal(parser.sections(), ["console_scripts"], f"{context} sections")
    _require_equal(
        dict(parser.items("console_scripts", raw=True)),
        EXPECTED_CONSOLE_ENTRY_POINTS,
        f"{context} console scripts",
    )


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
    _require_equal(path.name, EXPECTED_WHEEL_FILENAME, "wheel filename")
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
    _require_equal(dist_infos, {EXPECTED_DIST_INFO}, "wheel dist-info identity")
    dist_info = EXPECTED_DIST_INFO
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
    _verify_core_metadata(members[f"{dist_info}/METADATA"], "wheel METADATA")
    _verify_wheel_metadata(members[f"{dist_info}/WHEEL"])
    for relative in LICENSE_FILES:
        member = f"{dist_info}/licenses/{relative}"
        _require_equal(members[member], (REPOSITORY_ROOT / relative).read_bytes(), member)

    _verify_entry_points(members[f"{dist_info}/entry_points.txt"])
    _verify_record(members, dist_info)


def verify_sdist(path: Path) -> None:
    _require_equal(path.name, EXPECTED_SDIST_FILENAME, "sdist filename")
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
    _require_equal(roots, {EXPECTED_SDIST_ROOT}, "sdist root identity")
    root = EXPECTED_SDIST_ROOT
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

    _verify_core_metadata(members[f"{root}/PKG-INFO"], "sdist PKG-INFO")
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
