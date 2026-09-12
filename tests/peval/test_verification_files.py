from __future__ import annotations

import http.client
import json
import os
import threading
from unittest.mock import patch

import pytest

from psycheval.config import HarborDataset, HarborMount, ToolConfig
from psycheval.serve import ServeAccess, ServeRuntime
from psycheval.state import CatalogQuery, WorkspaceSources, open_workspace_state
from psycheval.state.harbor_verifier_evidence import ARTIFACT_DOWNLOAD_MAX_BYTES
from psycheval.state.verification_files import (
    TEXT_PREVIEW_LIMIT,
    read_verification_file,
    verification_file_tree,
)
from tests.peval.asgi_server import LocalHTTPServer, make_handler
from tests.peval.test_harbor_evidence import write_evidence_trial


def test_tree_is_metadata_only_and_reads_are_bounded(tmp_path):
    trial = tmp_path / "trial"
    (trial / "verifier").mkdir(parents=True)
    (trial / "agent").mkdir()
    (trial / "agent/private.txt").write_text("not verification")
    (trial / "config.json").write_text("not verification")
    (trial / "result.json").mkdir()
    (trial / "result.json/private.txt").write_text("not a result file")
    (trial / "verifier/result.xml").write_text("<testsuites/>")
    (trial / "verifier/report.markdown").write_text("# Preview")
    (trial / "verifier/large.txt").write_bytes(
        b"x" * (TEXT_PREVIEW_LIMIT - 1) + "中文".encode()
    )
    (trial / "verifier/unknown.bin").write_bytes(b"\xff")
    with patch(
        "psycheval.state.verification_files._open_regular",
        side_effect=AssertionError("listing read a body"),
    ):
        tree = verification_file_tree(trial, tmp_path)
    entries = {row["path"]: row for row in tree}
    assert "agent/private.txt" not in entries
    assert "config.json" not in entries
    assert "result.json/private.txt" not in entries
    assert entries["verifier/result.xml"]["previewable"]
    assert entries["verifier/report.markdown"]["preview_kind"] == "text"
    assert not entries["verifier/unknown.bin"]["previewable"]
    large = read_verification_file(trial, tmp_path, entries["verifier/large.txt"]["id"])
    assert large["truncated"] is True
    assert large["content"] == "x" * (TEXT_PREVIEW_LIMIT - 1)
    with pytest.raises(ValueError, match="unknown verification file"):
        read_verification_file(trial, tmp_path, "../config.json")
    stream = read_verification_file(
        trial, tmp_path, entries["verifier/unknown.bin"]["id"], download=True
    )
    with (trial / "verifier/unknown.bin").open("ab") as handle:
        handle.write(b"appended after opening")
    assert b"".join(stream.chunks) == b"\xff"


def test_link_replacement_cannot_reuse_a_file_id(tmp_path):
    trial = tmp_path / "trial"
    (trial / "verifier").mkdir(parents=True)
    file = trial / "verifier/log.txt"
    file.write_text("owned")
    file_id = verification_file_tree(trial, tmp_path)[1]["id"]
    external = tmp_path / "secret.txt"
    external.write_text("external")
    file.unlink()
    try:
        file.symlink_to(external)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(ValueError, match="unknown verification file"):
        read_verification_file(trial, tmp_path, file_id)


def test_raster_previews_and_download_limits_are_explicit(tmp_path):
    trial = tmp_path / "trial"
    (trial / "artifacts").mkdir(parents=True)
    (trial / "artifacts/image.png").write_bytes(b"\x89PNG\r\n")
    (trial / "artifacts/page.svg").write_text('<svg onload="unsafe()"/>')
    with (trial / "artifacts/large.xlsx").open("wb") as handle:
        handle.truncate(ARTIFACT_DOWNLOAD_MAX_BYTES + 1)
    rows = {row["path"]: row for row in verification_file_tree(trial, tmp_path)}
    raster = rows["artifacts/image.png"]
    image = read_verification_file(trial, tmp_path, raster["id"])
    assert image.media_type == "image/png"
    assert image.content == b"\x89PNG\r\n"
    svg = rows["artifacts/page.svg"]
    assert svg["preview_kind"] == "text"
    assert read_verification_file(trial, tmp_path, svg["id"])["content"].startswith(
        "<svg"
    )
    binary = rows["artifacts/large.xlsx"]
    assert not binary["previewable"] and not binary["downloadable"]
    with pytest.raises(ValueError, match="exceeds"):
        read_verification_file(trial, tmp_path, binary["id"], download=True)


@pytest.mark.skipif(os.name != "nt", reason="Windows junction")
def test_junction_is_not_traversed(tmp_path):
    import subprocess

    trial = tmp_path / "trial"
    trial.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (external / "secret.txt").write_text("external")
    junction = trial / "verifier"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(external)],
        check=True,
        capture_output=True,
    )
    try:
        assert verification_file_tree(trial, tmp_path) == []
    finally:
        junction.rmdir()
    assert (external / "secret.txt").read_text() == "external"


def test_trial_location_does_not_resolve_datasets_and_keeps_step_scope(tmp_path):
    trial = tmp_path / "jobs/job/trial"
    write_evidence_trial(trial)
    step = trial / "steps/collect"
    (step / "verifier").mkdir(parents=True)
    (step / "verifier/reward.txt").write_text("0")
    (trial / "steps/other/verifier").mkdir(parents=True)
    (trial / "steps/other/verifier/reward.txt").write_text("1")
    (trial / "verifier").mkdir()
    (trial / "verifier/reward.txt").write_text("2")
    store = open_workspace_state(str(tmp_path / "workspace"))
    config = ToolConfig(
        harbor_mounts=(
            HarborMount(
                id="jobs", path=str(tmp_path / "jobs"), dataset_ids=("missing",)
            ),
        ),
        harbor_datasets=(
            HarborDataset(
                id="missing", path=str(tmp_path / "deleted"), format="workbuddy.v1"
            ),
        ),
    )
    try:
        with patch(
            "psycheval.state.workspace_sources.resolve_harbor_datasets_for_mount",
            side_effect=AssertionError("resolved a Task"),
        ):
            location = WorkspaceSources(store, config).verification_file_location(
                "harbor/jobs/job/trial/steps/collect"
            )
        assert location == (step, tmp_path / "jobs")
        tree = verification_file_tree(*location)
        assert [row["path"] for row in tree] == ["verifier", "verifier/reward.txt"]
        assert read_verification_file(*location, tree[1]["id"])["content"] == "0"
    finally:
        store.close()


@pytest.mark.parametrize("password", [None, "secret"])
def test_guest_and_admin_http_read_share_the_same_files(
    tmp_path, password, monkeypatch
):
    import io
    import zipfile

    trial = tmp_path / "jobs/job/trial"
    write_evidence_trial(trial, result={"verifier_result": {"rewards": {"reward": 0}}})
    (trial / "verifier").mkdir()
    (trial / "verifier/reward.json").write_text('{"reward":0}')
    (trial / "exception.txt").write_text("Recorded failure details")
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        zipped.writestr("content", b"plain text" * 100)
    damaged = bytearray(archive.getvalue())
    damaged[30 + len("content")] = 7
    (trial / "verifier/damaged.xlsx").write_bytes(damaged)
    monkeypatch.setenv("FIXTURE_API_KEY", "known-credential-12345")
    secret = "sk-abcdefghijklmnop1234"
    (trial / "verifier/private.json").write_text(
        json.dumps(
            {
                "reward": 0,
                "apiKey": "arbitrary-password",
                "log": f"{secret} Bearer abc-def known-credential-12345",
            }
        )
    )
    store = open_workspace_state(str(tmp_path / "workspace"))
    runtime = ServeRuntime(
        store,
        ToolConfig(
            workspace_root=str(tmp_path / "workspace"),
            harbor_mounts=(HarborMount(id="jobs", path=str(tmp_path / "jobs")),),
        ),
    )
    runtime.catalog.reconcile()
    key = runtime.catalog.query(CatalogQuery()).items[0].source_key
    server = LocalHTTPServer(
        ("127.0.0.1", 0), make_handler(runtime, access=ServeAccess(password))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(path, method="GET"):
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    try:
        status, _, body = request(f"/api/verification-files/{key}")
        assert status == 200
        tree = json.loads(body)["tree"]
        damaged_row = next(
            row for row in tree if row["path"] == "verifier/damaged.xlsx"
        )
        failed, _, message = request(
            f"/api/verification-files/{key}/{damaged_row['id']}?download=true"
        )
        assert failed == 404
        assert b"cannot be inspected" in message
        assert (trial / "verifier/damaged.xlsx").read_bytes() == damaged
        row = next(row for row in tree if row["path"] == "verifier/reward.json")
        path = f"/api/verification-files/{key}/{row['id']}"
        status, _, body = request(path)
        assert status == 200
        assert json.loads(body)["content"] == '{"reward":0}'
        status, headers, body = request(path + "?download=true")
        assert status == 200 and body == b'{"reward":0}'
        assert headers["content-security-policy"] == "sandbox"
        assert request(path, "PUT")[0] == 405
        assert request(f"/api/verification-files/{key}/{'0' * 24}")[0] == 404
        protected = next(row for row in tree if row["path"] == "verifier/private.json")
        for suffix in ("", "?download=true"):
            status, _, body = request(
                f"/api/verification-files/{key}/{protected['id']}{suffix}"
            )
            assert status == 200
            assert all(
                value.encode() not in body
                for value in (
                    secret,
                    "arbitrary-password",
                    "abc-def",
                    "known-credential-12345",
                )
            )
        assert secret in (trial / "verifier/private.json").read_text()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        runtime.close()
        store.close()
