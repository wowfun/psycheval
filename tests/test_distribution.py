from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import tarfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


distribution = script("check_distribution")
smoke_asset = script("prepare_smoke_asset")


def test_metadata_checks_current_project_requirements_instead_of_a_version_literal():
    project = {
        "name": "psycheval",
        "license": "MIT",
        "license-files": ["LICENSE"],
        "requires-python": ">=3.13,<3.16",
        "dependencies": ["Harbor>=0.25,<0.26"],
    }
    raw = b"""Metadata-Version: 2.5
Name: psycheval
Version: 0.2
Requires-Python: <3.16,>=3.13
License-Expression: MIT
License-File: LICENSE
Requires-Dist: harbor<0.26,>=0.25

Description.
"""
    assert distribution.metadata(raw, project)["Version"] == "0.2"
    project["dependencies"] = ["harbor==0.24.0"]
    with pytest.raises(AssertionError):
        distribution.metadata(raw, project)
    project["dependencies"] = ["harbor<0.26,>=0.25", "extra-dependency>=1"]
    with pytest.raises(AssertionError):
        distribution.metadata(raw, project)


@pytest.mark.parametrize("extra", ["pdf", "pptx", "xlsx", "docx", "documents"])
def test_wheel_metadata_validates_optional_dependencies(extra):
    import tomllib

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    rows = [
        "Metadata-Version: 2.5",
        "Name: psycheval",
        "Version: 0.1.0rc1",
        f"Requires-Python: {project['requires-python']}",
        f"License-Expression: {project['license']}",
        *(f"License-File: {name}" for name in project["license-files"]),
    ]
    rows += [f"Requires-Dist: {item}" for item in project["dependencies"]]
    for name, dependencies in project["optional-dependencies"].items():
        rows.append(f"Provides-Extra: {name}")
        rows += [f'Requires-Dist: {item}; extra == "{name}"' for item in dependencies]
    raw = ("\n".join(rows) + "\n\nDescription.\n").encode()
    distribution.metadata(raw, project)
    broken = [
        row
        for row in rows
        if not (
            row.startswith("Requires-Dist:") and row.endswith(f'extra == "{extra}"')
        )
    ]
    with pytest.raises(AssertionError):
        distribution.metadata(
            ("\n".join(broken) + "\n\nDescription.").encode(), project
        )


def archive_fixture(kind=tarfile.REGTYPE):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        item = tarfile.TarInfo("package/dist/echarts.min.js")
        item.type = kind
        data = b"// fixture chart"
        item.size = len(data) if kind == tarfile.REGTYPE else 0
        item.linkname = "../../outside"
        archive.addfile(item, io.BytesIO(data))
    archive = buffer.getvalue()
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(archive).digest()).decode()
    return archive, integrity


def test_smoke_asset_fetches_locked_archive_and_extracts_only_verified_regular_file(
    tmp_path, monkeypatch
):
    archive, integrity = archive_fixture()
    (tmp_path / "package-lock.json").write_text(
        json.dumps(
            {
                "packages": {
                    "node_modules/echarts": {
                        "resolved": "https://fixture.invalid/chart.tgz",
                        "integrity": integrity,
                    }
                }
            }
        )
    )

    def fetch(url, timeout):
        assert url == "https://fixture.invalid/chart.tgz" and timeout == 30
        return io.BytesIO(archive)

    monkeypatch.setattr(smoke_asset, "urlopen", fetch)
    output = tmp_path / "nested/echarts.min.js"
    smoke_asset.prepare(tmp_path, output)
    assert output.read_bytes() == b"// fixture chart"
    with pytest.raises(ValueError, match="integrity"):
        smoke_asset.extract_asset(archive + b"tampered", integrity)
    linked, link_integrity = archive_fixture(tarfile.SYMTYPE)
    with pytest.raises(ValueError, match="regular file"):
        smoke_asset.extract_asset(linked, link_integrity)
    monkeypatch.setattr(smoke_asset, "MAX_ARCHIVE_BYTES", 1)
    with pytest.raises(ValueError, match="size limit"):
        smoke_asset.prepare(tmp_path, output)


def test_ci_builds_once_and_consumers_share_prepared_inputs():
    jobs = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())["jobs"]
    build = jobs["build-distribution"]
    consumer = jobs["distribution"]
    assert "matrix" not in build.get("strategy", {})
    assert consumer["needs"] == "build-distribution"
    assert len(consumer["strategy"]["matrix"]["os"]) == 2
    assert len(consumer["strategy"]["matrix"]["python"]) == 3
    commands = "\n".join(step.get("run", "") for step in consumer["steps"])
    assert "uv build" not in commands and "npm" not in commands
    assert "--constraints" in commands and "--echarts" in commands
    assert any(
        step.get("with", {}).get("name") == "distribution-check"
        for step in consumer["steps"]
    )
    jobs = yaml.safe_load((ROOT / ".github/workflows/publish.yml").read_text())["jobs"]
    for name in ("accept", "stage-pypi", "verify-pypi"):
        commands = "\n".join(step.get("run", "") for step in jobs[name]["steps"])
        assert "npm" not in commands and "--echarts" in commands
        assert "--constraints" not in commands
        assert any(
            step.get("with", {}).get("name") == "smoke-asset"
            for step in jobs[name]["steps"]
        )
