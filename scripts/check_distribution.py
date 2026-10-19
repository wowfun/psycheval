"""Validate the built distribution against its tracked source payload."""

from __future__ import annotations

import argparse
import configparser
import email.parser
import re
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet


def tracked_payload(root: Path) -> dict[str, bytes]:
    names = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        .decode("utf-8")
        .split("\0")
    )
    return {
        name: (root / name).read_bytes()
        for name in names
        if (
            name in {"pyproject.toml", "README.md", "LICENSE", ".gitignore"}
            or name.startswith("src/psycheval/")
        )
        and (root / name).is_file()
    }


def metadata(raw: bytes, project: dict, version: str | None = None):
    value = email.parser.BytesParser().parsebytes(raw)
    assert value["Name"] == project["name"]
    assert value["Metadata-Version"] == "2.5"
    assert SpecifierSet(value["Requires-Python"]) == SpecifierSet(
        project["requires-python"]
    )
    assert value["License-Expression"] == project["license"]
    assert set(value.get_all("License-File")) == set(project["license-files"])
    assert {Requirement(item) for item in value.get_all("Requires-Dist", [])} == {
        Requirement(item) for item in project["dependencies"]
    }
    if version:
        assert value["Version"] == version
    description = value.get_payload()
    assert "$HFPR_" not in description
    for target in re.findall(r"\]\(([^)]+)\)", description):
        assert target.startswith(("https://", "http://", "#", "mailto:")), target
        if "github.com/wowfun/psycheval/blob/" in target:
            assert f"/blob/v{value['Version']}/" in target, target
    return value


def check(root: Path, dist: Path, tag: str | None = None) -> None:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    wheels, sdists = list(dist.glob("*.whl")), list(dist.glob("*.tar.gz"))
    assert len(wheels) == len(sdists) == 1, "Expected one wheel and one sdist"
    expected = tracked_payload(root)
    with tarfile.open(sdists[0]) as archive:
        actual = {}
        for member in archive.getmembers():
            if member.isdir():
                continue
            assert member.isfile(), member.name
            name = member.name.split("/", 1)[1]
            actual[name] = archive.extractfile(member).read()
    source_meta = actual.pop("PKG-INFO")
    assert actual.keys() == expected.keys(), (
        actual.keys() - expected.keys(),
        expected.keys() - actual.keys(),
    )
    assert all(actual[name] == content for name, content in expected.items()), (
        "sdist payload differs from checkout"
    )
    version = metadata(source_meta, project, tag.removeprefix("v") if tag else None)[
        "Version"
    ]
    with zipfile.ZipFile(wheels[0]) as archive:
        names = set(archive.namelist())
        info = next(
            name.rsplit("/", 1)[0]
            for name in names
            if name.endswith(".dist-info/METADATA")
        )
        wheel_meta = metadata(archive.read(f"{info}/METADATA"), project, version)
        assert (
            wheel_meta.get_payload()
            == email.parser.BytesParser().parsebytes(source_meta).get_payload()
        )
        runtime = {
            name[4:]: data for name, data in expected.items() if name.startswith("src/")
        }
        assert {
            name for name in names if not name.startswith(info + "/")
        } == runtime.keys()
        assert all(archive.read(name) == content for name, content in runtime.items())
        for license_file in project["license-files"]:
            assert (
                archive.read(f"{info}/licenses/{license_file}")
                == expected[license_file]
            )
        entries = configparser.ConfigParser()
        entries.read_string(archive.read(f"{info}/entry_points.txt").decode())
        assert dict(entries["console_scripts"]) == {"peval": "psycheval.cli:main"}
    print(f"Validated {wheels[0].name} and {sdists[0].name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    parser.add_argument("--tag")
    args = parser.parse_args()
    check(Path(__file__).resolve().parents[1], args.dist.resolve(), args.tag)
