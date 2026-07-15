from __future__ import annotations

import csv
import importlib.util
import io
import stat
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

_VERIFIER_SPEC = importlib.util.spec_from_file_location(
    "verify_artifacts", Path(__file__).resolve().parents[1] / "scripts" / "verify_artifacts.py"
)
assert _VERIFIER_SPEC is not None and _VERIFIER_SPEC.loader is not None
verifier = importlib.util.module_from_spec(_VERIFIER_SPEC)
sys.modules[_VERIFIER_SPEC.name] = verifier
_VERIFIER_SPEC.loader.exec_module(verifier)

DIST_INFO = "nepal_ttf2utf-0.3.0.dist-info"
SDIST_ROOT = "nepal_ttf2utf-0.3.0"


def _metadata(
    body: str = "",
    requires_dist: tuple[str, ...] = verifier.EXPECTED_REQUIRES_DIST,
) -> bytes:
    headers = [
        "Metadata-Version: 2.4",
        "Name: nepal-ttf2utf",
        "Version: 0.3.0",
        *(f"License-File: {name}" for name in verifier.LICENSE_FILES),
        *(f"Requires-Dist: {requirement}" for requirement in requires_dist),
    ]
    return ("\n".join(headers) + f"\n\n{body}").encode()


def _wheel_members(
    metadata_body: str = "",
    requires_dist: tuple[str, ...] = verifier.EXPECTED_REQUIRES_DIST,
) -> dict[str, bytes]:
    members = {
        f"nepal_ttf2utf/{name}": data
        for name, data in verifier._source_files(verifier.PACKAGE_SOURCE).items()
    }
    members.update(
        {
            f"{DIST_INFO}/METADATA": _metadata(metadata_body, requires_dist),
            f"{DIST_INFO}/WHEEL": b"Wheel-Version: 1.0\nTag: py3-none-any\n",
            f"{DIST_INFO}/entry_points.txt": (
                b"[console_scripts]\nnepal-ttf2utf = nepal_ttf2utf.cli:main\n"
            ),
            **{
                f"{DIST_INFO}/licenses/{name}": (verifier.REPOSITORY_ROOT / name).read_bytes()
                for name in verifier.LICENSE_FILES
            },
        }
    )
    return members


def _record(members: dict[str, bytes]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for name, data in sorted(members.items()):
        writer.writerow((name, verifier._wheel_digest(data), len(data)))
    writer.writerow((f"{DIST_INFO}/RECORD", "", ""))
    return output.getvalue().encode()


def _write_wheel(
    path: Path,
    *,
    metadata_body: str = "",
    extra: tuple[str, bytes] | None = None,
    missing: str | None = None,
    duplicate: str | None = None,
    symlink: str | None = None,
    directory: str | None = None,
    requires_dist: tuple[str, ...] = verifier.EXPECTED_REQUIRES_DIST,
) -> None:
    members = _wheel_members(metadata_body, requires_dist)
    if extra is not None:
        members[extra[0]] = extra[1]
    if missing != f"{DIST_INFO}/RECORD":
        members[f"{DIST_INFO}/RECORD"] = _record(members)
    if missing is not None:
        members.pop(missing, None)

    with zipfile.ZipFile(path, "w") as archive:
        for name, data in members.items():
            archive.writestr(name, data)
        if duplicate is not None:
            archive.writestr(duplicate, members[duplicate])
        if symlink is not None:
            info = zipfile.ZipInfo(symlink)
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, b"target")
        if directory is not None:
            archive.writestr(directory.rstrip("/") + "/", b"payload")


def _sdist_members(
    metadata_body: str = "",
    requires_dist: tuple[str, ...] = verifier.EXPECTED_REQUIRES_DIST,
) -> dict[str, bytes]:
    members = {
        f"{SDIST_ROOT}/PKG-INFO": _metadata(metadata_body, requires_dist),
        **{
            f"{SDIST_ROOT}/{name}": (verifier.REPOSITORY_ROOT / name).read_bytes()
            for name in verifier.REQUIRED_SDIST_FILES
        },
        **{
            f"{SDIST_ROOT}/src/nepal_ttf2utf/{name}": data
            for name, data in verifier._source_files(verifier.PACKAGE_SOURCE).items()
        },
    }
    for directory in ("docs", "scripts", "tests"):
        members.update(
            {
                f"{SDIST_ROOT}/{directory}/{name}": data
                for name, data in verifier._source_files(
                    verifier.REPOSITORY_ROOT / directory
                ).items()
            }
        )
    return members


def _write_sdist(
    path: Path,
    *,
    metadata_body: str = "",
    extra: tuple[str, bytes] | None = None,
    missing: str | None = None,
    duplicate: str | None = None,
    special: tuple[str, bytes] | None = None,
    requires_dist: tuple[str, ...] = verifier.EXPECTED_REQUIRES_DIST,
) -> None:
    members = _sdist_members(metadata_body, requires_dist)
    if extra is not None:
        members[extra[0]] = extra[1]
    if missing is not None:
        members.pop(missing, None)

    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        if duplicate is not None:
            data = members[duplicate]
            info = tarfile.TarInfo(duplicate)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        if special is not None:
            info = tarfile.TarInfo(special[0])
            info.type = special[1]
            if info.issym():
                info.linkname = "target"
            archive.addfile(info)


def test_synthetic_artifacts_pass(tmp_path: Path) -> None:
    wheel = tmp_path / "package.whl"
    sdist = tmp_path / "package.tar.gz"
    _write_wheel(wheel)
    _write_sdist(sdist)

    verifier.verify_wheel(wheel)
    verifier.verify_sdist(sdist)


def test_complete_inventory_rejects_extra_files(tmp_path: Path) -> None:
    wheel = tmp_path / "package.whl"
    sdist = tmp_path / "package.tar.gz"
    _write_wheel(wheel, extra=("PRIVATE.txt", b"not distributable"))
    _write_sdist(sdist, extra=(f"{SDIST_ROOT}/PRIVATE.txt", b"not distributable"))

    with pytest.raises(AssertionError, match="complete member inventory"):
        verifier.verify_wheel(wheel)
    with pytest.raises(AssertionError, match="complete member inventory"):
        verifier.verify_sdist(sdist)


@pytest.mark.parametrize(
    "name",
    [r"..\escape.txt", "C:/escape.txt", "directory/../escape.txt", "/escape.txt"],
)
def test_wheel_rejects_unsafe_member_names(tmp_path: Path, name: str) -> None:
    wheel = tmp_path / "package.whl"
    _write_wheel(wheel, extra=(name, b"unsafe"))

    with pytest.raises(AssertionError, match="forbidden members"):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    "name",
    [r"..\escape.txt", "C:/escape.txt", "directory/../escape.txt", "/escape.txt"],
)
def test_sdist_rejects_unsafe_member_names(tmp_path: Path, name: str) -> None:
    sdist = tmp_path / "package.tar.gz"
    _write_sdist(sdist, extra=(name, b"unsafe"))

    with pytest.raises(AssertionError, match="forbidden members"):
        verifier.verify_sdist(sdist)


def test_wheel_rejects_symlink(tmp_path: Path) -> None:
    wheel = tmp_path / "package.whl"
    _write_wheel(wheel, symlink="nepal_ttf2utf/maps/link")

    with pytest.raises(AssertionError, match="non-regular members"):
        verifier.verify_wheel(wheel)


def test_wheel_rejects_explicit_directory(tmp_path: Path) -> None:
    wheel = tmp_path / "package.whl"
    _write_wheel(wheel, directory="PRIVATE")

    with pytest.raises(AssertionError, match="non-regular members"):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    "member_type", [tarfile.SYMTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.DIRTYPE]
)
def test_sdist_rejects_special_members(tmp_path: Path, member_type: bytes) -> None:
    sdist = tmp_path / "package.tar.gz"
    _write_sdist(sdist, special=(f"{SDIST_ROOT}/special", member_type))

    with pytest.raises(AssertionError, match="non-regular members"):
        verifier.verify_sdist(sdist)


def test_artifacts_reject_duplicate_members(tmp_path: Path) -> None:
    wheel = tmp_path / "package.whl"
    sdist = tmp_path / "package.tar.gz"
    wheel_member = "nepal_ttf2utf/maps/Limbu.map"
    sdist_member = f"{SDIST_ROOT}/src/nepal_ttf2utf/maps/Limbu.map"
    with pytest.warns(UserWarning, match="Duplicate name"):
        _write_wheel(wheel, duplicate=wheel_member)
    _write_sdist(sdist, duplicate=sdist_member)

    with pytest.raises(AssertionError, match="unique member count"):
        verifier.verify_wheel(wheel)
    with pytest.raises(AssertionError, match="unique member count"):
        verifier.verify_sdist(sdist)


@pytest.mark.parametrize(
    "member",
    [
        "nepal_ttf2utf/maps/Limbu.map",
        f"{DIST_INFO}/licenses/THIRD_PARTY_NOTICES.md",
        f"{DIST_INFO}/entry_points.txt",
        f"{DIST_INFO}/RECORD",
    ],
)
def test_wheel_rejects_missing_critical_member(tmp_path: Path, member: str) -> None:
    wheel = tmp_path / "package.whl"
    _write_wheel(wheel, missing=member)

    with pytest.raises(AssertionError):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    "member",
    [
        f"{SDIST_ROOT}/PKG-INFO",
        f"{SDIST_ROOT}/src/nepal_ttf2utf/maps/Limbu.map",
        f"{SDIST_ROOT}/THIRD_PARTY_NOTICES.md",
    ],
)
def test_sdist_rejects_missing_critical_member(tmp_path: Path, member: str) -> None:
    sdist = tmp_path / "package.tar.gz"
    _write_sdist(sdist, missing=member)

    with pytest.raises(AssertionError, match="complete member inventory"):
        verifier.verify_sdist(sdist)


def test_license_like_metadata_body_text_is_not_a_header(tmp_path: Path) -> None:
    wheel = tmp_path / "package.whl"
    sdist = tmp_path / "package.tar.gz"
    body = "License-File: body-text-is-not-metadata\n"
    _write_wheel(wheel, metadata_body=body)
    _write_sdist(sdist, metadata_body=body)

    verifier.verify_wheel(wheel)
    verifier.verify_sdist(sdist)


@pytest.mark.parametrize(
    "requires_dist",
    [
        ("pytest>=7; extra == 'dev'",),
        ("npttf2utf>=0.3,<0.4", "pytest>=7; extra == 'dev'"),
        ("npttf2utf==0.3.6", "pytest>=7; extra == 'dev'"),
        (
            'npttf2utf==0.3.7; python_version >= "3.9"',
            "pytest>=7; extra == 'dev'",
        ),
        (
            "npttf2utf==0.3.7",
            "npttf2utf==0.3.7",
            "pytest>=7; extra == 'dev'",
        ),
        (
            "npttf2utf==0.3.7",
            "requests==2.32.4",
            "pytest>=7; extra == 'dev'",
        ),
    ],
)
def test_artifacts_reject_nonexact_runtime_dependency_metadata(
    tmp_path: Path, requires_dist: tuple[str, ...]
) -> None:
    wheel = tmp_path / "package.whl"
    sdist = tmp_path / "package.tar.gz"
    _write_wheel(wheel, requires_dist=requires_dist)
    _write_sdist(sdist, requires_dist=requires_dist)

    with pytest.raises(AssertionError, match="Requires-Dist metadata"):
        verifier.verify_wheel(wheel)
    with pytest.raises(AssertionError, match="Requires-Dist metadata"):
        verifier.verify_sdist(sdist)


def test_main_ignores_outer_appledouble_companions(tmp_path: Path) -> None:
    wheel = tmp_path / "nepal_ttf2utf-0.3.0-py3-none-any.whl"
    sdist = tmp_path / "nepal_ttf2utf-0.3.0.tar.gz"
    _write_wheel(wheel)
    _write_sdist(sdist)
    (tmp_path / f"._{wheel.name}").write_bytes(b"AppleDouble")
    (tmp_path / f"._{sdist.name}").write_bytes(b"AppleDouble")

    assert verifier.main([str(tmp_path)]) == 0
