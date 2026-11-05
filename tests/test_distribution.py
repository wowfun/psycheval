from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from unittest.mock import Mock

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
    write_smoke_lock(tmp_path, integrity)

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


def write_smoke_lock(root, integrity):
    lock = {
        "lockfileVersion": "9.0",
        "importers": {
            ".": {
                "devDependencies": {
                    "echarts": {"specifier": "1.2.3", "version": "1.2.3"}
                }
            }
        },
        "packages": {
            "echarts@0.9.0": {
                "resolution": {"tarball": "https://fixture.invalid/wrong.tgz"}
            },
            "echarts@1.2.3": {
                "resolution": {
                    "tarball": "https://fixture.invalid/chart.tgz",
                    "integrity": integrity,
                }
            },
        },
    }
    (root / "pnpm-lock.yaml").write_text(yaml.safe_dump(lock), encoding="utf-8")
    return lock


@pytest.mark.parametrize("missing", ["importers", "package", "tarball", "integrity"])
def test_smoke_asset_rejects_missing_lock_information_before_fetching(
    tmp_path, monkeypatch, missing
):
    _, integrity = archive_fixture()
    lock = write_smoke_lock(tmp_path, integrity)
    if missing == "importers":
        del lock["importers"]
    elif missing == "package":
        del lock["packages"]["echarts@1.2.3"]
    else:
        del lock["packages"]["echarts@1.2.3"]["resolution"][missing]
    (tmp_path / "pnpm-lock.yaml").write_text(yaml.safe_dump(lock), encoding="utf-8")
    monkeypatch.setattr(
        smoke_asset,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("unexpected download"),
    )
    output = tmp_path / "echarts.min.js"
    with pytest.raises(ValueError, match="ECharts.*lock"):
        smoke_asset.prepare(tmp_path, output)
    assert not output.exists()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tarball", None),
        ("tarball", ""),
        ("tarball", "file:///tmp/chart.tgz"),
        ("tarball", "http://fixture.invalid/chart.tgz"),
        ("tarball", "https:///chart.tgz"),
        ("tarball", "https://["),
        ("integrity", None),
        ("integrity", "sha256-invalid"),
        ("integrity", "sha512-!!!"),
        ("integrity", "sha512-å"),
        ("integrity", "sha512-" + base64.b64encode(b"short").decode()),
    ],
)
def test_smoke_asset_rejects_invalid_download_information(
    tmp_path, monkeypatch, field, value
):
    _, integrity = archive_fixture()
    lock = write_smoke_lock(tmp_path, integrity)
    lock["packages"]["echarts@1.2.3"]["resolution"][field] = value
    (tmp_path / "pnpm-lock.yaml").write_text(yaml.safe_dump(lock), encoding="utf-8")
    monkeypatch.setattr(
        smoke_asset,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("unexpected download"),
    )
    with pytest.raises(ValueError, match="ECharts.*lock"):
        smoke_asset.prepare(tmp_path, tmp_path / "echarts.min.js")


@pytest.mark.parametrize("lock_text", [None, "importers: ["])
def test_smoke_asset_reports_unreadable_or_malformed_lock_before_fetching(
    tmp_path, monkeypatch, lock_text
):
    if lock_text is not None:
        (tmp_path / "pnpm-lock.yaml").write_text(lock_text, encoding="utf-8")
    monkeypatch.setattr(
        smoke_asset,
        "urlopen",
        lambda *args, **kwargs: pytest.fail("unexpected download"),
    )
    output = tmp_path / "echarts.min.js"
    with pytest.raises(ValueError, match="pnpm-lock.yaml"):
        smoke_asset.prepare(tmp_path, output)
    assert not output.exists()


def test_smoke_asset_resolves_the_real_lock_before_download(tmp_path, monkeypatch):
    version = json.loads((ROOT / "package.json").read_text())["devDependencies"][
        "echarts"
    ]

    class DownloadReached(Exception):
        pass

    def fetch(url, timeout):
        assert url == f"https://registry.npmjs.org/echarts/-/echarts-{version}.tgz"
        assert timeout == 30
        raise DownloadReached

    monkeypatch.setattr(smoke_asset, "urlopen", fetch)
    output = tmp_path / "echarts.min.js"
    with pytest.raises(DownloadReached):
        smoke_asset.prepare(ROOT, output)
    assert not output.exists()


def test_smoke_asset_does_not_replace_an_existing_asset_when_integrity_fails(
    tmp_path, monkeypatch
):
    archive, integrity = archive_fixture()
    write_smoke_lock(tmp_path, integrity)
    output = tmp_path / "echarts.min.js"
    output.write_bytes(b"retained asset")
    monkeypatch.setattr(
        smoke_asset,
        "urlopen",
        lambda *args, **kwargs: io.BytesIO(archive + b"tampered"),
    )
    with pytest.raises(ValueError, match="integrity"):
        smoke_asset.prepare(tmp_path, output)
    assert output.read_bytes() == b"retained asset"


def test_web_ci_initializes_pnpm_before_its_node_cache_and_uses_frozen_install():
    jobs = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())["jobs"]
    steps = jobs["web-and-source-tool"]["steps"]
    pnpm_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("uses", "").startswith("pnpm/action-setup@")
    )
    node_index = next(
        index
        for index, step in enumerate(steps)
        if step.get("uses", "").startswith("actions/setup-node@")
    )
    assert pnpm_index < node_index
    assert "version" not in steps[pnpm_index].get("with", {})
    assert steps[node_index]["with"]["cache"] == "pnpm"
    assert steps[node_index]["with"]["cache-dependency-path"] == "pnpm-lock.yaml"
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "pnpm install --frozen-lockfile" in commands
    assert "pnpm exec playwright install --with-deps chromium" in commands
    assert "pnpm run check" in commands
    assert "uv tool install -e ." in commands
    assert "scripts/smoke_source_tool.py" in commands
    assert "scripts/check_skill.py skills/peval" in commands


@pytest.mark.parametrize(
    ("workflow", "job"), [("ci.yml", "build-distribution"), ("publish.yml", "build")]
)
def test_smoke_asset_has_a_frozen_build_environment_even_on_release_recovery(
    workflow, job
):
    jobs = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text())["jobs"]
    steps = jobs[job]["steps"]
    prepare_index = next(
        index
        for index, step in enumerate(steps)
        if "scripts/prepare_smoke_asset.py" in step.get("run", "")
    )
    prepare = steps[prepare_index]
    assert "if" not in prepare
    assert "uv run --no-sync python scripts/prepare_smoke_asset.py" in prepare["run"]
    assert any(
        "if" not in step
        and "uv sync --frozen --only-group build" in step.get("run", "")
        for step in steps[:prepare_index]
    )


def test_ci_builds_once_and_consumers_share_prepared_inputs():
    jobs = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())["jobs"]
    build = jobs["build-distribution"]
    consumer = jobs["distribution"]
    assert "matrix" not in build.get("strategy", {})
    assert consumer["needs"] == "build-distribution"
    assert "scripts/check_distribution.py" in "\n".join(
        step.get("run", "") for step in build["steps"]
    )
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


@pytest.mark.parametrize("workflow", ["ci.yml", "publish.yml"])
def test_ci_uses_python_312_and_checks_installs_on_both_platforms(workflow):
    jobs = yaml.safe_load((ROOT / ".github/workflows" / workflow).read_text())["jobs"]
    consumer = jobs["distribution" if workflow == "ci.yml" else "accept"]
    assert consumer["strategy"]["matrix"] == {"os": ["ubuntu-latest", "windows-latest"]}
    for job in jobs.values():
        steps = job["steps"]
        setup = [
            step
            for step in steps
            if step.get("uses", "").startswith("astral-sh/setup-uv@")
        ]
        for step in setup:
            assert step["with"]["python-version"] == "3.12"
        for step in steps:
            if "scripts/validate_install.py" in step.get("run", ""):
                assert setup and '--python "$UV_PYTHON"' in step["run"]


def test_publish_only_requests_upload_permissions_for_missing_index_files():
    jobs = yaml.safe_load((ROOT / ".github/workflows/publish.yml").read_text())["jobs"]
    privileged = {
        name
        for name, job in jobs.items()
        if job.get("permissions", {}).get("id-token") == "write"
    }
    assert privileged == {"upload-testpypi", "upload-pypi"}
    for name in privileged:
        job = jobs[name]
        assert f"{job['needs']}.outputs.needed == 'true'" in job["if"]
        assert all(
            "uses" in step and not step["uses"].startswith("actions/checkout@")
            for step in job["steps"]
        )


def test_public_index_retries_install_but_fails_a_broken_wheel_immediately(
    tmp_path, monkeypatch
):
    validate = script("validate_install")
    asset = tmp_path / "echarts.min.js"
    asset.touch()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validate_install.py",
            "psycheval==1",
            "--python",
            "3.12",
            "--echarts",
            str(asset),
            "--retry-index",
        ],
    )
    error = subprocess.CalledProcessError(1, "smoke_installed.py")
    run = Mock(
        side_effect=[
            None,  # uv venv
            subprocess.CompletedProcess([], 1),
            subprocess.CompletedProcess([], 0),
            None,  # uv pip check
            error,
        ]
    )
    sleep = Mock()
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(validate.time, "sleep", sleep)
    with pytest.raises(subprocess.CalledProcessError) as failed:
        validate.main()
    assert failed.value is error
    sleep.assert_called_once_with(15)
    first, retry = run.call_args_list[1:3]
    assert first == retry and first.args[0][-2:] == ["--refresh-package", "psycheval"]
    assert run.call_args_list[-1].args[0][2].endswith("smoke_installed.py")
