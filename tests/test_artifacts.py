from __future__ import annotations

import csv
import importlib.util
import io
import re
import stat
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

import nepal_ttf2utf

_VERIFIER_SPEC = importlib.util.spec_from_file_location(
    "verify_artifacts", Path(__file__).resolve().parents[1] / "scripts" / "verify_artifacts.py"
)
assert _VERIFIER_SPEC is not None and _VERIFIER_SPEC.loader is not None
verifier = importlib.util.module_from_spec(_VERIFIER_SPEC)
sys.modules[_VERIFIER_SPEC.name] = verifier
_VERIFIER_SPEC.loader.exec_module(verifier)

DIST_INFO = verifier.EXPECTED_DIST_INFO
SDIST_ROOT = verifier.EXPECTED_SDIST_ROOT


def _metadata(
    body: str | None = None,
    requires_dist: tuple[str, ...] = verifier.EXPECTED_REQUIRES_DIST,
    *,
    overrides: dict[str, str | None] | None = None,
    extra_headers: tuple[str, ...] = (),
    license_files: tuple[str, ...] = verifier.LICENSE_FILES,
    project_urls: tuple[str, ...] = tuple(sorted(verifier.EXPECTED_PROJECT_URLS)),
    classifiers: tuple[str, ...] = tuple(sorted(verifier.EXPECTED_CLASSIFIERS)),
    keywords: tuple[str, ...] = tuple(sorted(verifier.EXPECTED_KEYWORDS)),
    provides_extra: tuple[str, ...] = verifier.EXPECTED_PROVIDES_EXTRA,
) -> bytes:
    singleton_headers = {
        "Metadata-Version": verifier.EXPECTED_METADATA_VERSION,
        "Name": verifier.EXPECTED_PROJECT_NAME,
        "Version": verifier.EXPECTED_PROJECT_VERSION,
        "Summary": verifier.EXPECTED_PROJECT_SUMMARY,
        "Author": verifier.EXPECTED_PROJECT_AUTHOR,
        "License-Expression": verifier.EXPECTED_LICENSE_EXPRESSION,
        "Requires-Python": verifier.EXPECTED_REQUIRES_PYTHON,
        "Description-Content-Type": verifier.EXPECTED_DESCRIPTION_CONTENT_TYPE,
        "Keywords": ",".join(keywords),
    }
    singleton_headers.update(overrides or {})
    headers = [
        *(f"{name}: {value}" for name, value in singleton_headers.items() if value is not None),
        *(f"Project-URL: {value}" for value in project_urls),
        *(f"License-File: {name}" for name in license_files),
        *(f"Classifier: {value}" for value in classifiers),
        *(f"Requires-Dist: {requirement}" for requirement in requires_dist),
        *(f"Provides-Extra: {extra}" for extra in provides_extra),
        *extra_headers,
    ]
    if body is None:
        body = (verifier.REPOSITORY_ROOT / "README.md").read_text("utf-8")
    return ("\n".join(headers) + f"\n\n{body}").encode()


def _wheel_metadata(
    *,
    overrides: dict[str, str | None] | None = None,
    tags: tuple[str, ...] = (verifier.EXPECTED_WHEEL_TAG,),
    extra_headers: tuple[str, ...] = (),
) -> bytes:
    singleton_headers = {
        "Wheel-Version": "1.0",
        "Generator": "hatchling 1.0.0",
        "Root-Is-Purelib": "true",
    }
    singleton_headers.update(overrides or {})
    headers = [
        *(f"{name}: {value}" for name, value in singleton_headers.items() if value is not None),
        *(f"Tag: {tag}" for tag in tags),
        *extra_headers,
    ]
    return ("\n".join(headers) + "\n").encode()


def _wheel_members(
    metadata_body: str | None = None,
    requires_dist: tuple[str, ...] = verifier.EXPECTED_REQUIRES_DIST,
    *,
    metadata: bytes | None = None,
    wheel_metadata: bytes | None = None,
    entry_points: bytes | None = None,
    dist_info: str = DIST_INFO,
) -> dict[str, bytes]:
    members = {
        f"nepal_ttf2utf/{name}": data
        for name, data in verifier._source_files(verifier.PACKAGE_SOURCE).items()
    }
    members.update(
        {
            f"{dist_info}/METADATA": (
                metadata if metadata is not None else _metadata(metadata_body, requires_dist)
            ),
            f"{dist_info}/WHEEL": (
                wheel_metadata if wheel_metadata is not None else _wheel_metadata()
            ),
            f"{dist_info}/entry_points.txt": (
                entry_points
                if entry_points is not None
                else b"[console_scripts]\nnepal-ttf2utf = nepal_ttf2utf.cli:main\n"
            ),
            **{
                f"{dist_info}/licenses/{name}": (verifier.REPOSITORY_ROOT / name).read_bytes()
                for name in verifier.LICENSE_FILES
            },
        }
    )
    return members


def _record(members: dict[str, bytes], dist_info: str = DIST_INFO) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for name, data in sorted(members.items()):
        writer.writerow((name, verifier._wheel_digest(data), len(data)))
    writer.writerow((f"{dist_info}/RECORD", "", ""))
    return output.getvalue().encode()


def _write_wheel(
    path: Path,
    *,
    metadata_body: str | None = None,
    extra: tuple[str, bytes] | None = None,
    missing: str | None = None,
    duplicate: str | None = None,
    symlink: str | None = None,
    directory: str | None = None,
    requires_dist: tuple[str, ...] = verifier.EXPECTED_REQUIRES_DIST,
    metadata: bytes | None = None,
    wheel_metadata: bytes | None = None,
    entry_points: bytes | None = None,
    dist_info: str = DIST_INFO,
) -> None:
    members = _wheel_members(
        metadata_body,
        requires_dist,
        metadata=metadata,
        wheel_metadata=wheel_metadata,
        entry_points=entry_points,
        dist_info=dist_info,
    )
    if extra is not None:
        members[extra[0]] = extra[1]
    if missing != f"{dist_info}/RECORD":
        members[f"{dist_info}/RECORD"] = _record(members, dist_info)
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
    metadata_body: str | None = None,
    requires_dist: tuple[str, ...] = verifier.EXPECTED_REQUIRES_DIST,
    *,
    metadata: bytes | None = None,
    root: str = SDIST_ROOT,
) -> dict[str, bytes]:
    members = {
        f"{root}/PKG-INFO": (
            metadata if metadata is not None else _metadata(metadata_body, requires_dist)
        ),
        **{
            f"{root}/{name}": (verifier.REPOSITORY_ROOT / name).read_bytes()
            for name in verifier.REQUIRED_SDIST_FILES
        },
        **{
            f"{root}/src/nepal_ttf2utf/{name}": data
            for name, data in verifier._source_files(verifier.PACKAGE_SOURCE).items()
        },
    }
    for directory in ("docs", "scripts", "tests"):
        members.update(
            {
                f"{root}/{directory}/{name}": data
                for name, data in verifier._source_files(
                    verifier.REPOSITORY_ROOT / directory
                ).items()
            }
        )
    return members


def _write_sdist(
    path: Path,
    *,
    metadata_body: str | None = None,
    extra: tuple[str, bytes] | None = None,
    missing: str | None = None,
    duplicate: str | None = None,
    special: tuple[str, bytes] | None = None,
    requires_dist: tuple[str, ...] = verifier.EXPECTED_REQUIRES_DIST,
    metadata: bytes | None = None,
    root: str = SDIST_ROOT,
) -> None:
    members = _sdist_members(
        metadata_body,
        requires_dist,
        metadata=metadata,
        root=root,
    )
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
    wheel = tmp_path / verifier.EXPECTED_WHEEL_FILENAME
    sdist = tmp_path / verifier.EXPECTED_SDIST_FILENAME
    _write_wheel(wheel)
    _write_sdist(sdist)

    verifier.verify_wheel(wheel)
    verifier.verify_sdist(sdist)


def test_complete_inventory_rejects_extra_files(tmp_path: Path) -> None:
    wheel = tmp_path / verifier.EXPECTED_WHEEL_FILENAME
    sdist = tmp_path / verifier.EXPECTED_SDIST_FILENAME
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
    wheel = tmp_path / verifier.EXPECTED_WHEEL_FILENAME
    _write_wheel(wheel, extra=(name, b"unsafe"))

    with pytest.raises(AssertionError, match="forbidden members"):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    "name",
    [r"..\escape.txt", "C:/escape.txt", "directory/../escape.txt", "/escape.txt"],
)
def test_sdist_rejects_unsafe_member_names(tmp_path: Path, name: str) -> None:
    sdist = tmp_path / verifier.EXPECTED_SDIST_FILENAME
    _write_sdist(sdist, extra=(name, b"unsafe"))

    with pytest.raises(AssertionError, match="forbidden members"):
        verifier.verify_sdist(sdist)


def test_wheel_rejects_symlink(tmp_path: Path) -> None:
    wheel = tmp_path / verifier.EXPECTED_WHEEL_FILENAME
    _write_wheel(wheel, symlink="nepal_ttf2utf/maps/link")

    with pytest.raises(AssertionError, match="non-regular members"):
        verifier.verify_wheel(wheel)


def test_wheel_rejects_explicit_directory(tmp_path: Path) -> None:
    wheel = tmp_path / verifier.EXPECTED_WHEEL_FILENAME
    _write_wheel(wheel, directory="PRIVATE")

    with pytest.raises(AssertionError, match="non-regular members"):
        verifier.verify_wheel(wheel)


@pytest.mark.parametrize(
    "member_type", [tarfile.SYMTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.DIRTYPE]
)
def test_sdist_rejects_special_members(tmp_path: Path, member_type: bytes) -> None:
    sdist = tmp_path / verifier.EXPECTED_SDIST_FILENAME
    _write_sdist(sdist, special=(f"{SDIST_ROOT}/special", member_type))

    with pytest.raises(AssertionError, match="non-regular members"):
        verifier.verify_sdist(sdist)


def test_artifacts_reject_duplicate_members(tmp_path: Path) -> None:
    wheel = tmp_path / verifier.EXPECTED_WHEEL_FILENAME
    sdist = tmp_path / verifier.EXPECTED_SDIST_FILENAME
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
    wheel = tmp_path / verifier.EXPECTED_WHEEL_FILENAME
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
    sdist = tmp_path / verifier.EXPECTED_SDIST_FILENAME
    _write_sdist(sdist, missing=member)

    with pytest.raises(AssertionError, match="complete member inventory"):
        verifier.verify_sdist(sdist)


def _project_scalar(name: str) -> str:
    pyproject = (verifier.REPOSITORY_ROOT / "pyproject.toml").read_text("utf-8")
    project_sections = re.findall(
        r"(?ms)^\[project\][ \t]*\n(.*?)(?=^\[|\Z)",
        pyproject,
    )
    assert len(project_sections) == 1
    matches = re.findall(
        rf'(?m)^{re.escape(name)}[ \t]*=[ \t]*"([^"]*)"[ \t]*$',
        project_sections[0],
    )
    assert len(matches) == 1
    return matches[0]


def test_project_identity_constants_match_source_declarations() -> None:
    assert _project_scalar("name") == verifier.EXPECTED_PROJECT_NAME
    assert _project_scalar("version") == verifier.EXPECTED_PROJECT_VERSION
    assert _project_scalar("description") == verifier.EXPECTED_PROJECT_SUMMARY
    assert _project_scalar("requires-python") == verifier.EXPECTED_REQUIRES_PYTHON
    assert _project_scalar("license") == verifier.EXPECTED_LICENSE_EXPRESSION
    assert nepal_ttf2utf.__version__ == verifier.EXPECTED_PROJECT_VERSION
    assert verifier.EXPECTED_DIST_INFO == "nepal_ttf2utf-0.3.0.dist-info"
    assert verifier.EXPECTED_SDIST_ROOT == "nepal_ttf2utf-0.3.0"
    assert verifier.EXPECTED_WHEEL_FILENAME == "nepal_ttf2utf-0.3.0-py3-none-any.whl"
    assert verifier.EXPECTED_SDIST_FILENAME == "nepal_ttf2utf-0.3.0.tar.gz"


_SINGLETON_METADATA = {
    "Metadata-Version": (verifier.EXPECTED_METADATA_VERSION, "1.0"),
    "Name": (verifier.EXPECTED_PROJECT_NAME, "different-project"),
    "Version": (verifier.EXPECTED_PROJECT_VERSION, "9.9.9"),
    "Summary": (verifier.EXPECTED_PROJECT_SUMMARY, "different summary"),
    "Author": (verifier.EXPECTED_PROJECT_AUTHOR, "Different Author"),
    "License-Expression": (verifier.EXPECTED_LICENSE_EXPRESSION, "Apache-2.0"),
    "Requires-Python": (verifier.EXPECTED_REQUIRES_PYTHON, ">=3.8"),
    "Description-Content-Type": (verifier.EXPECTED_DESCRIPTION_CONTENT_TYPE, "text/plain"),
}


@pytest.mark.parametrize("context", ["wheel METADATA", "sdist PKG-INFO"])
@pytest.mark.parametrize(("name", "values"), _SINGLETON_METADATA.items())
@pytest.mark.parametrize(
    "mutation", ["missing", "wrong", "duplicate", "conflicting", "conflicting-first"]
)
def test_core_metadata_rejects_nonexact_singletons(context, name, values, mutation) -> None:
    expected, wrong = values
    overrides = {
        name: (
            None
            if mutation == "missing"
            else wrong
            if mutation in {"wrong", "conflicting-first"}
            else expected
        )
    }
    extra_headers = ()
    if mutation in {"duplicate", "conflicting", "conflicting-first"}:
        extra_headers = (
            f"{name}: {expected if mutation in {'duplicate', 'conflicting-first'} else wrong}",
        )
    with pytest.raises(AssertionError, match=re.escape(name)):
        verifier._verify_core_metadata(
            _metadata(overrides=overrides, extra_headers=extra_headers),
            context,
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (_metadata(license_files=verifier.LICENSE_FILES[:-1]), "License-File"),
        (
            _metadata(license_files=verifier.LICENSE_FILES + (verifier.LICENSE_FILES[0],)),
            "License-File",
        ),
        (_metadata(license_files=verifier.LICENSE_FILES + ("EXTRA-LICENSE",)), "License-File"),
        (
            _metadata(project_urls=tuple(sorted(verifier.EXPECTED_PROJECT_URLS))[:-1]),
            "Project-URL",
        ),
        (
            _metadata(
                project_urls=tuple(sorted(verifier.EXPECTED_PROJECT_URLS))
                + (next(iter(verifier.EXPECTED_PROJECT_URLS)),)
            ),
            "Project-URL",
        ),
        (
            _metadata(
                project_urls=tuple(sorted(verifier.EXPECTED_PROJECT_URLS))
                + ("Docs, https://example.invalid",)
            ),
            "Project-URL",
        ),
        (
            _metadata(classifiers=tuple(sorted(verifier.EXPECTED_CLASSIFIERS))[:-1]),
            "Classifier",
        ),
        (
            _metadata(
                classifiers=tuple(sorted(verifier.EXPECTED_CLASSIFIERS))
                + (next(iter(verifier.EXPECTED_CLASSIFIERS)),)
            ),
            "Classifier",
        ),
        (
            _metadata(
                classifiers=tuple(sorted(verifier.EXPECTED_CLASSIFIERS))
                + ("Programming Language :: Python :: 2",)
            ),
            "Classifier",
        ),
        (_metadata(requires_dist=verifier.EXPECTED_REQUIRES_DIST[:-1]), "Requires-Dist"),
        (
            _metadata(
                requires_dist=verifier.EXPECTED_REQUIRES_DIST
                + (verifier.EXPECTED_REQUIRES_DIST[0],)
            ),
            "Requires-Dist",
        ),
        (_metadata(provides_extra=()), "Provides-Extra"),
        (_metadata(provides_extra=("dev", "dev")), "Provides-Extra"),
        (_metadata(provides_extra=("dev", "backdoor")), "Provides-Extra"),
        (_metadata(keywords=tuple(sorted(verifier.EXPECTED_KEYWORDS))[:-1]), "Keywords"),
        (
            _metadata(
                keywords=tuple(sorted(verifier.EXPECTED_KEYWORDS))
                + (next(iter(verifier.EXPECTED_KEYWORDS)),)
            ),
            "Keywords",
        ),
        (
            _metadata(keywords=tuple(sorted(verifier.EXPECTED_KEYWORDS)) + ("unexpected",)),
            "Keywords",
        ),
    ],
)
def test_core_metadata_rejects_nonexact_repeatable_inventories(payload, message) -> None:
    with pytest.raises(AssertionError, match=message):
        verifier._verify_core_metadata(payload, "artifact metadata")


def test_core_metadata_accepts_reordered_repeatable_headers() -> None:
    verifier._verify_core_metadata(
        _metadata(
            requires_dist=tuple(reversed(verifier.EXPECTED_REQUIRES_DIST)),
            license_files=tuple(reversed(verifier.LICENSE_FILES)),
            project_urls=tuple(reversed(sorted(verifier.EXPECTED_PROJECT_URLS))),
            classifiers=tuple(reversed(sorted(verifier.EXPECTED_CLASSIFIERS))),
            keywords=tuple(reversed(sorted(verifier.EXPECTED_KEYWORDS))),
        ),
        "artifact metadata",
    )


@pytest.mark.parametrize(
    "header",
    [
        "Author-email",
        "Maintainer",
        "Maintainer-email",
        "Dynamic",
        "License",
        "Provides-Dist",
        "Obsoletes-Dist",
        "Requires-External",
        "X-Injected",
    ],
)
def test_core_metadata_rejects_unexpected_headers(header) -> None:
    with pytest.raises(AssertionError, match=header):
        verifier._verify_core_metadata(
            _metadata(extra_headers=(f"{header}: unexpected",)),
            "artifact metadata",
        )


def test_core_metadata_accepts_semantically_unchanged_header_folding() -> None:
    folded_summary = (
        "Legacy-font conversion and Unicode span validation\n for scripts of Nepal and Sikkim."
    )
    folded_homepage = "Homepage,\n https://github.com/Ampixa/nepal-ttf2utf"
    project_urls = tuple(
        folded_homepage if value.startswith("Homepage,") else value
        for value in sorted(verifier.EXPECTED_PROJECT_URLS)
    )
    verifier._verify_core_metadata(
        _metadata(overrides={"Summary": folded_summary}, project_urls=project_urls),
        "artifact metadata",
    )


def test_core_metadata_requires_the_exact_readme_body() -> None:
    verifier._verify_core_metadata(_metadata(), "artifact metadata")
    with pytest.raises(AssertionError, match="description body"):
        verifier._verify_core_metadata(_metadata(body="different body\n"), "artifact metadata")


def test_license_like_metadata_body_text_is_not_a_header() -> None:
    message = verifier._parse_headers(
        _metadata(body="License-File: body-text-is-not-metadata\n"),
        "artifact metadata",
    )
    assert "body-text-is-not-metadata" not in tuple(message.get_all("License-File", ()))
    assert message.get_payload() == "License-File: body-text-is-not-metadata\n"


def test_artifacts_reject_wrong_filenames_and_internal_identity(tmp_path: Path) -> None:
    wrong_wheel = tmp_path / "different-0.3.0-py3-none-any.whl"
    wrong_sdist = tmp_path / "different-0.3.0.tar.gz"
    _write_wheel(wrong_wheel)
    _write_sdist(wrong_sdist)
    with pytest.raises(AssertionError, match="wheel filename"):
        verifier.verify_wheel(wrong_wheel)
    with pytest.raises(AssertionError, match="sdist filename"):
        verifier.verify_sdist(wrong_sdist)

    wheel = tmp_path / verifier.EXPECTED_WHEEL_FILENAME
    sdist = tmp_path / verifier.EXPECTED_SDIST_FILENAME
    _write_wheel(wheel, dist_info="different-0.3.0.dist-info")
    _write_sdist(sdist, root="different-0.3.0")
    with pytest.raises(AssertionError, match="dist-info identity"):
        verifier.verify_wheel(wheel)
    with pytest.raises(AssertionError, match="root identity"):
        verifier.verify_sdist(sdist)


@pytest.mark.parametrize("name", ["Wheel-Version", "Root-Is-Purelib"])
@pytest.mark.parametrize(
    "mutation", ["missing", "wrong", "duplicate", "conflicting", "conflicting-first"]
)
def test_wheel_metadata_rejects_nonexact_singletons(name, mutation) -> None:
    expected = "1.0" if name == "Wheel-Version" else "true"
    wrong = "2.0" if name == "Wheel-Version" else "false"
    overrides = {
        name: (
            None
            if mutation == "missing"
            else wrong
            if mutation in {"wrong", "conflicting-first"}
            else expected
        )
    }
    extra_headers = ()
    if mutation in {"duplicate", "conflicting", "conflicting-first"}:
        extra_headers = (
            f"{name}: {expected if mutation in {'duplicate', 'conflicting-first'} else wrong}",
        )
    with pytest.raises(AssertionError, match=name):
        verifier._verify_wheel_metadata(
            _wheel_metadata(overrides=overrides, extra_headers=extra_headers)
        )


@pytest.mark.parametrize(
    "tags",
    [
        (),
        ("py2-none-any",),
        (verifier.EXPECTED_WHEEL_TAG,) * 2,
        (verifier.EXPECTED_WHEEL_TAG, "cp999-cp999-any"),
    ],
)
def test_wheel_metadata_rejects_nonexact_tags(tags) -> None:
    with pytest.raises(AssertionError, match="Tag"):
        verifier._verify_wheel_metadata(_wheel_metadata(tags=tags))


def test_wheel_metadata_pins_backend_family_but_not_generator_version() -> None:
    verifier._verify_wheel_metadata(_wheel_metadata(overrides={"Generator": "hatchling 999.0.0"}))
    for generator in (None, "different-backend 1.0", "hatchling ", "hatchling nonsense"):
        with pytest.raises(AssertionError, match="Generator"):
            verifier._verify_wheel_metadata(_wheel_metadata(overrides={"Generator": generator}))
    with pytest.raises(AssertionError, match="Generator"):
        verifier._verify_wheel_metadata(
            _wheel_metadata(extra_headers=("Generator: hatchling duplicate",))
        )
    with pytest.raises(AssertionError, match="Build"):
        verifier._verify_wheel_metadata(_wheel_metadata(extra_headers=("Build: 1",)))


@pytest.mark.parametrize("header", ["Wheel-Extension: example", "X-Injected: value"])
def test_wheel_metadata_rejects_unexpected_headers(header) -> None:
    with pytest.raises(AssertionError, match="header inventory"):
        verifier._verify_wheel_metadata(_wheel_metadata(extra_headers=(header,)))


def test_wheel_metadata_rejects_a_payload() -> None:
    with pytest.raises(AssertionError, match="payload"):
        verifier._verify_wheel_metadata(_wheel_metadata() + b"\nunexpected\n")


@pytest.mark.parametrize(
    "entry_points",
    [
        b"[other]\nnepal-ttf2utf = nepal_ttf2utf.cli:main\n",
        b"[console_scripts]\n# nepal-ttf2utf = nepal_ttf2utf.cli:main\n",
        b"[DEFAULT]\nnepal-ttf2utf = nepal_ttf2utf.cli:main\n[console_scripts]\n",
        b"[console_scripts]\nnepal-ttf2utf = nepal_ttf2utf.cli:main_evil\n",
        b"[console_scripts]\nnepal-ttf2utf = nepal_ttf2utf.cli:main\nbackdoor = evil:main\n",
        b"[console_scripts]\nnepal-ttf2utf = nepal_ttf2utf.cli:main\n[other]\nextra = evil:main\n",
        b"[console_scripts]\nnepal-ttf2utf = nepal_ttf2utf.cli:main\nnepal-ttf2utf = evil:main\n",
        b"[console_scripts]\nnepal-ttf2utf: nepal_ttf2utf.cli:main\n",
        b"\xff",
    ],
)
def test_entry_point_contract_rejects_ambiguous_or_extra_definitions(entry_points) -> None:
    with pytest.raises(AssertionError, match="entry_points"):
        verifier._verify_entry_points(entry_points)


@pytest.mark.parametrize(
    "entry_points",
    [
        b"[console_scripts]\nnepal-ttf2utf=nepal_ttf2utf.cli:main\n",
        b"# generated\r\n[console_scripts]\r\nnepal-ttf2utf  =  nepal_ttf2utf.cli:main\r\n",
    ],
)
def test_entry_point_contract_accepts_semantically_exact_formatting(entry_points) -> None:
    verifier._verify_entry_points(entry_points)


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
    wheel = tmp_path / verifier.EXPECTED_WHEEL_FILENAME
    sdist = tmp_path / verifier.EXPECTED_SDIST_FILENAME
    _write_wheel(wheel, requires_dist=requires_dist)
    _write_sdist(sdist, requires_dist=requires_dist)

    with pytest.raises(AssertionError, match="Requires-Dist"):
        verifier.verify_wheel(wheel)
    with pytest.raises(AssertionError, match="Requires-Dist"):
        verifier.verify_sdist(sdist)


def test_main_ignores_outer_appledouble_companions(tmp_path: Path) -> None:
    wheel = tmp_path / verifier.EXPECTED_WHEEL_FILENAME
    sdist = tmp_path / verifier.EXPECTED_SDIST_FILENAME
    _write_wheel(wheel)
    _write_sdist(sdist)
    (tmp_path / f"._{wheel.name}").write_bytes(b"AppleDouble")
    (tmp_path / f"._{sdist.name}").write_bytes(b"AppleDouble")

    assert verifier.main([str(tmp_path)]) == 0
