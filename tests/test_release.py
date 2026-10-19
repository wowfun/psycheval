from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release", ROOT / "scripts/release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def test_partial_upload_only_accepts_matching_bytes():
    receipt = {"files": {"a.whl": "abc", "a.tar.gz": "def"}}
    assert release.missing_files(receipt, None) == ["a.tar.gz", "a.whl"]
    remote = {"urls": [{"filename": "a.whl", "digests": {"sha256": "abc"}}]}
    assert release.missing_files(receipt, remote) == ["a.tar.gz"]
    remote["urls"][0]["digests"]["sha256"] = "changed"
    with pytest.raises(ValueError, match="different SHA"):
        release.missing_files(receipt, remote)
    with pytest.raises(ValueError, match="unexpected"):
        release.missing_files({"files": {}}, remote)


def test_receipt_binds_commit_tag_and_payload(tmp_path):
    (tmp_path / "a.whl").write_bytes(b"wheel")
    receipt = {
        "tag": "v0.1.0rc1",
        "version": "0.1.0rc1",
        "commit": "abc",
        "files": {
            "a.whl": hashlib.sha256(b"wheel").hexdigest(),
        },
    }
    release.verify_receipt(tmp_path, receipt, "v0.1.0rc1", "abc")
    with pytest.raises(ValueError, match="tag and commit"):
        release.verify_receipt(tmp_path, receipt, "v0.1.0rc2", "abc")
    (tmp_path / "a.whl").write_bytes(b"different")
    with pytest.raises(ValueError, match="digest"):
        release.verify_receipt(tmp_path, receipt, "v0.1.0rc1", "abc")


def test_ci_gate_checks_exact_main_push_and_latest_attempt():
    run = {
        "head_sha": "abc",
        "event": "push",
        "head_branch": "main",
        "run_number": 1,
        "run_attempt": 1,
        "status": "completed",
        "conclusion": "success",
    }
    assert release.ci_succeeded([run], "abc")
    with pytest.raises(ValueError, match="No push/main"):
        release.ci_succeeded([{**run, "event": "pull_request"}], "abc")
    assert not release.ci_succeeded(
        [run, {**run, "run_attempt": 2, "status": "in_progress"}], "abc"
    )
    with pytest.raises(ValueError, match="did not succeed"):
        release.ci_succeeded([{**run, "conclusion": "cancelled"}], "abc")


def test_invalid_tag_never_queries_or_uploads(monkeypatch):
    monkeypatch.setattr(
        release.subprocess,
        "run",
        lambda *a, **k: pytest.fail("invalid tag reached git"),
    )
    with pytest.raises(ValueError, match="Release tags"):
        release.gate("main", "abc")


def test_index_wait_is_bounded(tmp_path, monkeypatch):
    import json
    import sys

    (tmp_path / "a.whl").write_bytes(b"wheel")
    receipt = {
        "tag": "v1.0.0",
        "version": "1.0.0",
        "commit": "abc",
        "files": {"a.whl": hashlib.sha256(b"wheel").hexdigest()},
    }
    (tmp_path / "receipt.json").write_text(json.dumps(receipt))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "release.py",
            "index",
            "--dist",
            str(tmp_path),
            "--tag",
            "v1.0.0",
            "--commit",
            "abc",
            "--index",
            "pypi",
        ],
    )
    monkeypatch.setattr(release, "get_json", lambda *a, **k: None)
    times = iter([0, 301])
    monkeypatch.setattr(release.time, "monotonic", lambda: next(times))
    with pytest.raises(TimeoutError, match="Index still lacks"):
        release.main()


@pytest.mark.parametrize("state", ["available", "expired", "missing_uploaded", "new"])
def test_recover_uses_only_current_run_and_never_rebuilds_uploaded_version(
    tmp_path, monkeypatch, state
):
    output = tmp_path / "output"
    for key, value in {
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_RUN_ID": "42",
        "GH_TOKEN": "fixture",
        "GITHUB_OUTPUT": str(output),
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(sys, "argv", ["release.py", "recover", "--tag", "v1.0.0"])
    queried = []

    def get_json(url, **kwargs):
        queried.append(url)
        if "api.github.com" in url:
            assert "/actions/runs/42/artifacts" in url
            return {
                "artifacts": []
                if state in {"new", "missing_uploaded"}
                else [{"name": "release-dist", "id": 9, "expired": state == "expired"}]
            }
        return {"urls": []} if state == "missing_uploaded" else None

    monkeypatch.setattr(release, "get_json", get_json)
    if state in {"expired", "missing_uploaded"}:
        with pytest.raises(ValueError, match="new version"):
            release.main()
        assert not output.exists()
    else:
        release.main()
        assert (output.read_text() if output.exists() else "") == (
            "artifact_id=9\n" if state == "available" else ""
        )
    if state == "available":
        assert len(queried) == 1


@pytest.mark.parametrize("scenario", ["stage", "download", "corrupt_download"])
def test_partial_upload_staging_and_index_download_use_receipt(
    tmp_path, monkeypatch, scenario
):
    action = "stage" if scenario == "stage" else "download"
    files = {"a.whl": b"wheel", "a.tar.gz": b"source"}
    receipt = {
        "tag": "v1.0.0",
        "version": "1.0.0",
        "commit": "abc",
        "files": {
            name: hashlib.sha256(data).hexdigest() for name, data in files.items()
        },
    }
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    (tmp_path / "receipt.json").write_text(json.dumps(receipt))
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "2")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "release.py",
            action,
            "--dist",
            str(tmp_path),
            "--tag",
            "v1.0.0",
            "--commit",
            "abc",
            "--index",
            "testpypi",
        ],
    )
    remote = {
        "urls": [
            {
                "filename": name,
                "digests": {"sha256": receipt["files"][name]},
                "url": f"https://files.example/{name}",
            }
            for name in files
            if action == "download" or name == "a.whl"
        ]
    }
    monkeypatch.setattr(release, "get_json", lambda *a, **kw: remote)
    monkeypatch.setattr(
        release.urllib.request,
        "urlopen",
        lambda url, **kw: io.BytesIO(
            b"corrupted"
            if scenario == "corrupt_download"
            else files[url.rsplit("/", 1)[1]]
        ),
    )
    if scenario == "corrupt_download":
        with pytest.raises(ValueError, match="Downloaded file has a different SHA"):
            release.main()
        assert not list((tmp_path / "download").iterdir())
        return
    release.main()
    if action == "stage":
        assert [p.name for p in (tmp_path / "upload").iterdir()] == ["a.tar.gz"]
        assert (tmp_path / "upload/a.tar.gz").read_bytes() == b"source"
        assert (
            tmp_path / "output"
        ).read_text() == "needed=true\nartifact_name=upload-testpypi-2\n"
    else:
        assert {
            p.name: p.read_bytes() for p in (tmp_path / "download").iterdir()
        } == files
