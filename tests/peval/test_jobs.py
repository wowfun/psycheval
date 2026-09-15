from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from pathlib import Path

import pytest

from psycheval.jobs.harbor import HarborHarness, task_revision
from psycheval.jobs.service import JobsConflict, JobsService
from psycheval.jobs.storage import (
    owned_process,
    process_identity,
    read_json,
    safe_path,
    write_json,
)
from tests.peval.jobs_fixture_plugin import FixtureHarness


def install_fixture_plugin(path):
    info = path / "jobs_fixture-1.0.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: jobs-fixture\nVersion: 1.0\n", encoding="utf-8"
    )
    (info / "entry_points.txt").write_text(
        "[psycheval.harnesses]\nfixture = tests.peval.jobs_fixture_plugin:FixtureHarness\n",
        encoding="utf-8",
    )


@pytest.fixture
def jobs(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "peval.toml").write_text(
        'locale = "en"\n# Keep this comment\n', encoding="utf-8"
    )
    install_fixture_plugin(tmp_path)
    monkeypatch.setenv("PYTHONPATH", os.pathsep.join([str(tmp_path), str(Path.cwd())]))
    service = JobsService(
        workspace, registry={"fixture": FixtureHarness(), "harbor": HarborHarness()}
    )
    yield service
    for state in service.list():
        if state["state"] in {"preparing", "running", "stopping"}:
            service.stop(state["id"])
            wait_for(service, state["id"], terminal=True)


def request(**settings):
    return {
        "harness": "fixture",
        "tasks": ["fixture/one"],
        "variants": [
            {
                "id": "a",
                "label": "A",
                "agent": "fixture",
                "model": "model-a",
                "options": {},
            }
        ],
        "settings": {"n_attempts": 1, **settings},
    }


def wait_for(service, run_id, *, terminal=False):
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        detail = service.detail(run_id)
        if terminal and detail["state"] not in {"preparing", "running", "stopping"}:
            return detail
        if not terminal and detail["state"] == "running":
            return detail
        time.sleep(0.1)
    raise AssertionError((service.detail(run_id), service.logs(run_id)))


def launch(service, payload=None, request_id="request-fixture-1"):
    payload = payload or request()
    prepared = service.preview(payload)
    return service.start(payload, prepared["preview_id"], request_id)


def test_preview_is_read_only_and_rejects_identical_variants(jobs):
    payload = request()
    before = copy.deepcopy(payload)
    preview = jobs.preview(payload)
    assert preview["prepared"]["trial_count"] == 1
    assert payload == before
    assert not jobs.root.exists()
    payload["variants"].append({**payload["variants"][0], "id": "b", "label": "B"})
    with pytest.raises(ValueError, match="identical"):
        jobs.preview(payload)
    payload["variants"][1]["options"] = {"temperature": 0}
    assert jobs.preview(payload)["prepared"]["trial_count"] == 2


def retained_run(jobs, run_id="a" * 32, **updates):
    path = jobs.root / run_id
    path.mkdir(parents=True)
    state = {
        "id": run_id,
        "harness": "fixture",
        "state": "completed",
        "submitted_at": "2026-09-11T10:00:00+08:00",
        **updates,
    }
    write_json(path / "state.json", state)
    write_json(path / "request.json", {"request": {}, "prepared": {}})
    return path


@pytest.mark.parametrize("value", [{}, [], {"state": "running"}, "broken"])
def test_corrupt_run_isolated_from_listing_and_discovery(jobs, value):
    from psycheval.state.jobs import records

    good = retained_run(jobs, job_name="2026-09-11__10-00-00")
    broken = retained_run(jobs, "b" * 32)
    write_json(broken / "state.json", value)
    items = jobs.list()
    assert len(items) == 2
    assert (
        next(item for item in items if item["id"] == broken.name)["state"] == "invalid"
    )
    assert [path for path, _ in records(jobs.workspace)] == [good]


@pytest.mark.parametrize(
    "name", ["a/b", "..", "2026-99-11__10-00-00", "2026-09-11__10-00-00/other"]
)
def test_invalid_output_timestamp_never_reaches_result_reader(jobs, name, monkeypatch):
    path = retained_run(jobs, job_name=name)
    monkeypatch.setattr(
        jobs.registry["fixture"],
        "read_results",
        lambda _: pytest.fail("unsafe result lookup"),
    )
    with pytest.raises(ValueError):
        jobs.detail(path.name)


def test_corrupt_request_and_variant_mapping_are_diagnostics(jobs):
    path = retained_run(jobs, job_name="2026-09-11__10-00-00")
    write_json(path / "request.json", [])
    assert jobs.list()[0]["state"] == "invalid"
    write_json(path / "request.json", {"request": {}, "prepared": {}})
    write_json(path / "variants.json", [])
    assert "invalid Jobs object" in jobs.detail(path.name)["result_error"]


def test_missing_output_has_no_catalog_link(jobs):
    from psycheval.config import ToolConfig
    from psycheval.state.jobs import result_identity

    assert (
        result_identity(
            jobs.workspace,
            ToolConfig(),
            {"harness": "harbor", "job_name": "2026-09-11__10-00-00"},
            {"id": "trial"},
        )
        is None
    )


@pytest.mark.parametrize(
    "secret",
    [{"HF_TOKEN": 1234}, {"token": "literal"}, {"MYVAR": "sk-abcdefghijklmnop1234"}],
)
def test_literal_credentials_rejected_before_preparation(jobs, secret):
    payload = request()
    payload["variants"][0]["options"] = {"env": secret}
    with pytest.raises(ValueError, match="references"):
        jobs.preview(payload)
    assert not jobs.root.exists()


def test_provider_name_containing_token_is_not_a_credential(jobs):
    payload = request()
    options = {
        "kwargs": {
            "opencode_config": {
                "provider": {
                    "xiaomi-token-plan-cn": {
                        "options": {"apiKey": "{env:XIAOMI_API_KEY}"}
                    }
                }
            }
        }
    }
    payload["variants"][0]["options"] = options
    assert jobs.preview(payload)["request"]["variants"][0]["options"] == options


@pytest.mark.parametrize(
    "content",
    ["NaN", "Infinity", "[" * 70 + "0" + "]" * 70, "[" * 2000 + "0" + "]" * 2000],
)
def test_corrupt_json_limits_return_validation_errors(tmp_path, content):
    path = tmp_path / "bad.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        read_json(path)


def test_request_limits_before_plugin_prepare(jobs):
    payload = request()
    payload["tasks"] = [str(i) for i in range(1001)]
    with pytest.raises(ValueError):
        jobs.preview(payload)
    payload = request(value="a" * (256 * 1024))
    with pytest.raises(ValueError, match="256 KiB"):
        jobs.preview(payload)


def test_wrong_configuration_table_type_is_a_validation_error(jobs):
    (jobs.workspace / "peval.toml").write_text('jobs = "broken"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="configuration table"):
        jobs.options()


def test_spaced_and_quoted_defaults_header_preserved_correctly(jobs):
    config = jobs.workspace / "peval.toml"
    with config.open("a", encoding="utf-8") as stream:
        stream.write('[ "jobs" . "defaults" . fixture ]\nsettings = { value = 1 }\n')
    jobs.save_defaults(
        "fixture", {"settings": {"value": 2}}, jobs.options()["revision"]
    )
    assert jobs.options()["harnesses"][0]["saved_defaults"]["settings"] == {"value": 2}


def test_task_revision_survives_relocation(tmp_path):
    import shutil

    first = tmp_path / "one"
    first.mkdir()
    (first / "instruction.md").write_text("task", encoding="utf-8")
    second = tmp_path / "two"
    shutil.copytree(first, second)
    assert task_revision(first) == task_revision(second)


def test_config_and_log_reads_reject_nonregular_files(jobs):
    from psycheval.jobs.storage import read_bytes

    path = retained_run(jobs)
    (path / "worker.log").mkdir()
    with pytest.raises(ValueError, match="regular"):
        jobs.logs(path.name)
    with pytest.raises(ValueError, match="oversized"):
        read_bytes(jobs.workspace / "peval.toml", 1)


def test_actual_read_is_bounded_when_file_grows(tmp_path, monkeypatch):
    from contextlib import contextmanager

    from psycheval.jobs import storage

    path = tmp_path / "growing.json"
    path.write_bytes(b"{}")
    original = storage.os.fstat

    def grow(fd):
        info = original(fd)
        path.write_bytes(b"x" * 100)
        return info

    @contextmanager
    def opened(_):
        with path.open("rb") as stream:
            yield stream

    monkeypatch.setattr(storage, "open_regular", opened)
    monkeypatch.setattr(storage.os, "fstat", grow)
    with pytest.raises(ValueError, match="oversized"):
        storage.read_bytes(path, 10)


def test_launch_metadata_failure_cleans_worker(jobs, monkeypatch):
    from psycheval.jobs import service

    original = service.write_json

    def write(path, value):
        if path.name == "launcher.json":
            raise OSError("launcher metadata unavailable")
        return original(path, value)

    monkeypatch.setattr(service, "write_json", write)
    with pytest.raises(OSError, match="launcher metadata"):
        launch(jobs, request(delay=0.1))
    state = jobs.list()[0]
    assert state["state"] == "failed"
    saved = read_json(jobs.root / state["id"] / "state.json")
    assert not owned_process(saved.get("worker"))


def test_lock_contention_is_retryable(jobs):
    from psycheval.jobs.storage import locked

    with locked(jobs.root):
        with pytest.raises(JobsConflict, match="busy"):
            with locked(jobs.root):
                pytest.fail("second writer acquired lock")


def test_task_revision_detects_same_size_edit_and_shared_verifier_changes(tmp_path):
    task, shared = tmp_path / "task", tmp_path / "shared"
    task.mkdir()
    shared.mkdir()
    file = task / "instruction.md"
    file.write_text("first", encoding="utf-8")
    stamp = file.stat()
    before = task_revision(task, shared)
    file.write_text("other", encoding="utf-8")
    os.utime(file, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert task_revision(task, shared) != before
    before = task_revision(task, shared)
    (shared / "verifier.py").write_text("retained contract", encoding="utf-8")
    assert task_revision(task, shared) != before


def test_control_read_survives_concurrent_atomic_updates(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    path = tmp_path / "state.json"
    write_json(path, {"revision": 0})

    def update():
        for revision in range(1, 101):
            write_json(path, {"revision": revision})

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(update)
        while not future.done():
            assert 0 <= read_json(path)["revision"] <= 100
        future.result()
    assert read_json(path) == {"revision": 100}


def test_invalid_start_and_unrepresentable_defaults_do_not_write(jobs):
    with pytest.raises(ValueError, match="identity"):
        jobs.start({}, None, None)
    original = (jobs.workspace / "peval.toml").read_bytes()
    with pytest.raises(ValueError, match="null"):
        jobs.save_defaults(
            "fixture", {"settings": {"nullable": None}}, jobs.options()["revision"]
        )
    assert (jobs.workspace / "peval.toml").read_bytes() == original


def test_defaults_round_trip_preserves_false_zero_and_unrelated_text(jobs):
    defaults = {
        "settings": {
            "zero": 0,
            "enabled": False,
            "list": [],
            "value": "中文",
            "nested": {"a": 3},
        },
        "tasks": [],
    }
    options = jobs.save_defaults("fixture", defaults, jobs.options()["revision"])
    assert options["harnesses"][0]["saved_defaults"] == defaults
    assert "# Keep this comment" in (jobs.workspace / "peval.toml").read_text(
        encoding="utf-8"
    )
    with pytest.raises(JobsConflict):
        jobs.save_defaults("fixture", {}, "stale")
    jobs.save_defaults("fixture", {}, options["revision"])
    assert jobs.options()["harnesses"][0]["saved_defaults"] == {}


@pytest.mark.parametrize(
    "configuration",
    [
        "",
        '[jobs]\npreferred_harness = "harbor" # Remember\n',
        'jobs = { preferred_harness = "harbor", defaults = {} }\n',
        'jobs = { preferred_harness = "harbor" }\n',
        'jobs.preferred_harness = "harbor"\n',
        '["jobs".defaults.fixture.settings]\nzero = 0\nenabled = false\n',
    ],
)
def test_preferred_harness_persists_and_preserves_defaults(jobs, configuration):
    path = jobs.workspace / "peval.toml"
    unrelated = 'locale = "en"\n# Keep this comment\n'
    path.write_text(unrelated + configuration, encoding="utf-8")
    before, revision = jobs.configuration()
    options = jobs.save_preferred_harness("fixture", revision)
    after = tomllib.loads(path.read_text(encoding="utf-8"))
    before.setdefault("jobs", {})["preferred_harness"] = "fixture"
    assert after == before
    assert unrelated in path.read_text(encoding="utf-8")
    assert options["preferred_harness"] == "fixture"
    assert (
        JobsService(jobs.workspace, registry=jobs.registry).options()[
            "preferred_harness"
        ]
        == "fixture"
    )
    jobs.save_defaults("fixture", {"settings": {"zero": 0}}, options["revision"])
    assert jobs.options()["preferred_harness"] == "fixture"
    jobs.save_preferred_harness("harbor", jobs.options()["revision"])
    assert jobs.options()["harnesses"][0]["saved_defaults"] == {"settings": {"zero": 0}}


def test_preferred_harness_rejects_stale_and_invalid_writes(jobs):
    path = jobs.workspace / "peval.toml"
    before = path.read_bytes()
    with pytest.raises(JobsConflict):
        jobs.save_preferred_harness("fixture", "stale")
    for value in (None, "missing", "bad.id", [], 42):
        with pytest.raises(ValueError):
            jobs.save_preferred_harness(value, jobs.options()["revision"])
    assert path.read_bytes() == before


def test_direct_start_validates_before_allocation_and_deduplicates(jobs):
    payload = request()
    payload["tasks"] = []
    with pytest.raises(ValueError):
        jobs.start(payload, None, "direct-invalid")
    assert not list(jobs.root.glob("*/state.json"))
    payload = request()
    run = jobs.start(payload, None, "direct-start")
    assert jobs.start(payload, None, "direct-start")["id"] == run["id"]
    assert wait_for(jobs, run["id"], terminal=True)["state"] == "completed"


def test_secret_references_and_stale_preview(jobs):
    payload = request()
    payload["variants"][0]["options"] = {"env": {"API_KEY": "literal-secret"}}
    with pytest.raises(ValueError, match="references"):
        jobs.preview(payload)
    payload["variants"][0]["options"]["env"]["API_KEY"] = "${API_KEY}"
    preview = jobs.preview(payload)
    (jobs.workspace / "peval.toml").write_text('locale="zh-CN"\n', encoding="utf-8")
    with pytest.raises(JobsConflict):
        jobs.start(payload, preview["preview_id"], "stale-preview")
    assert not list(jobs.root.glob("*/state.json"))


def test_worker_survives_new_service_and_deduplicates_start(jobs):
    payload = request(delay=1)
    preview = jobs.preview(payload)
    run = jobs.start(payload, preview["preview_id"], "same-request")
    second = JobsService(jobs.workspace, registry=jobs.registry)
    assert (
        second.start(payload, preview["preview_id"], "same-request")["id"] == run["id"]
    )
    detail = wait_for(second, run["id"], terminal=True)
    assert detail["state"] == "completed", second.logs(run["id"])
    assert detail["results"][0]["score"] == 0
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}", detail["job_name"])
    assert (
        jobs.workspace / "jobs" / detail["job_name"] / "native-results.data"
    ).is_file()
    assert "fixture run finished" in second.logs(run["id"])
    assert len(second.list()) == 1
    with pytest.raises(JobsConflict):
        second.start(request(delay=2), preview["preview_id"], "same-request")


def test_cancel_cleans_up_native_child_and_is_idempotent(jobs):
    run = launch(jobs, request(child=True))
    wait_for(jobs, run["id"])
    identity = json.loads((jobs.root / run["id"] / "state.json").read_text())["worker"]
    owner = owned_process(identity)
    deadline = time.monotonic() + 10
    children = []
    while not children and time.monotonic() < deadline:
        children = owner.children(recursive=True)
        time.sleep(0.1)
    assert children
    jobs.stop(run["id"])
    result = wait_for(jobs, run["id"], terminal=True)
    assert result["state"] == "cancelled"
    assert jobs.stop(run["id"])["state"] == "cancelled"
    assert all(not p.is_running() for p in children), [
        (p.pid, p.cmdline()) for p in children if p.is_running()
    ]


def test_failure_and_missing_process_are_not_completed(jobs):
    run = launch(jobs, request(fail=True))
    assert wait_for(jobs, run["id"], terminal=True)["state"] == "failed"
    path = jobs.root / run["id"] / "state.json"
    state = json.loads(path.read_text())
    state.update(
        state="running", heartbeat=0, worker={"pid": os.getpid(), "created": -1}
    )
    write_json(path, state)
    assert jobs.detail(run["id"])["state"] == "interrupted"
    assert owned_process({"pid": os.getpid(), "created": -1}) is None
    assert owned_process(process_identity(os.getpid())) is not None


def test_same_second_jobs_never_overwrite_each_other(jobs):
    first = launch(jobs, request(delay=0.2), "first-request")
    second = launch(jobs, request(delay=0.2), "second-request")
    first = wait_for(jobs, first["id"], terminal=True)
    second = wait_for(jobs, second["id"], terminal=True)
    assert first["state"] == second["state"] == "completed"
    assert first["job_name"] != second["job_name"]


def test_noncooperative_plugin_can_be_stopped(jobs):
    run = launch(jobs, request(block=True), "blocking-plugin")
    wait_for(jobs, run["id"])
    jobs.stop(run["id"])
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        detail = jobs.detail(run["id"])
        if detail["state"] == "cancelled":
            assert "30 seconds" in detail["error"]
            break
        time.sleep(0.2)
    else:
        pytest.fail("blocking plugin ignored stop")


def test_http_server_restart_preserves_running_worker(jobs, tmp_path):
    import urllib.request

    script = """
import json, os, sys
from pathlib import Path
from psycheval.config import load_config
from psycheval.state import open_workspace_state
from psycheval.serve import ServeRuntime
from psycheval.jobs.storage import process_identity
from tests.peval.asgi_server import LocalHTTPServer, make_handler
root = Path(sys.argv[1])
store = open_workspace_state(str(root))
runtime = ServeRuntime(store, load_config(workspace_root=root))
server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
Path(sys.argv[2]).write_text(json.dumps({"origin": "http://127.0.0.1:" + str(server.server_port), "process": process_identity(os.getpid())}), encoding="utf-8")
server.serve_forever()
"""
    processes = []

    def server(index):
        ready = tmp_path / f"server-{index}.json"
        process = subprocess.Popen(
            [sys.executable, "-c", script, str(jobs.workspace), str(ready)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(process)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if ready.exists():
                return json.loads(ready.read_text(encoding="utf-8"))
            assert process.poll() is None
            time.sleep(0.05)
        pytest.fail("server did not start")

    def get(origin, path):
        with urllib.request.urlopen(origin + path, timeout=5) as response:
            assert response.headers["Cache-Control"] == "no-store"
            return json.load(response)

    servers = []
    try:
        first = server(1)
        servers.append(first)
        run = launch(jobs, request(delay=8), "http-restart")
        wait_for(jobs, run["id"])
        assert get(first["origin"], f"/api/jobs/{run['id']}")["state"] == "running"
        identity = json.loads((jobs.root / run["id"] / "state.json").read_text())[
            "worker"
        ]
        owned_process(first["process"]).kill()
        second = server(2)
        servers.append(second)
        observed = get(second["origin"], f"/api/jobs/{run['id']}")
        assert observed["id"] == run["id"]
        assert owned_process(identity)
        assert len(get(second["origin"], "/api/jobs")["items"]) == 1
        assert wait_for(jobs, run["id"], terminal=True)["state"] == "completed"
    finally:
        for item in servers:
            process = owned_process(item["process"])
            if process:
                process.kill()
        for process in processes:
            process.wait(timeout=10)


def test_native_windows_junction_and_traversal_rejected(tmp_path):
    with pytest.raises(ValueError):
        safe_path(tmp_path, "..", "outside")
    if os.name != "nt":
        pytest.skip("native Windows junction test")
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "junction"
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
        check=True,
        capture_output=True,
    )
    with pytest.raises(ValueError, match="linked"):
        safe_path(tmp_path, "junction", "result.json")


def test_harbor_corrupt_result_does_not_hide_healthy_sibling(tmp_path):
    for name, value in (
        ("broken", []),
        ("healthy", {"task_name": "one", "finished_at": "2026-09-11T10:00:00Z"}),
    ):
        path = tmp_path / name
        path.mkdir()
        write_json(path / "result.json", value)
    results = HarborHarness().read_results(tmp_path)
    assert len(results) == 2
    assert {item["state"] for item in results} == {"invalid", "completed"}
    assert all(item["score"] is None for item in results)


def test_result_without_trajectory_does_not_invent_usage():
    from psycheval.report.builder import build_report_from_snapshots
    from psycheval.state.catalog import _catalog_summary

    report = build_report_from_snapshots([None], [{"score": 0, "status": "completed"}])
    meta = report["trajectory_meta"][0]
    assert meta["trajectory_available"] is False
    row = _catalog_summary(report["trajectory"][0], meta, 0)
    assert row["score"] == 0
    for key in ("turns", "tokens", "cost_usd", "total_tool_calls"):
        assert row[key] is None


def test_jobs_poll_does_not_block_on_catalog_refresh(jobs, monkeypatch):
    from threading import Event

    from psycheval.config import ToolConfig
    from psycheval.serve.runtime import ServeRuntime
    from psycheval.state import open_workspace_state

    store = open_workspace_state(str(jobs.workspace))
    runtime = ServeRuntime(store, ToolConfig(), initialize_snapshot=False)
    entered, release = Event(), Event()

    def slow():
        entered.set()
        assert release.wait(5)

    monkeypatch.setattr(runtime.catalog, "reconcile", slow)
    try:
        assert runtime.jobs_list() == []
        assert entered.wait(2)
        assert runtime.jobs_list() == []
    finally:
        release.set()
        runtime.close()
        store.close()


def test_harbor_selection_and_config_are_authoritative(tmp_path):
    dataset = tmp_path / "dataset"
    task = dataset / "one"
    (task / "tests").mkdir(parents=True)
    (task / "tests/test.sh").write_text("echo 1", encoding="utf-8")
    (task / "instruction.md").write_text("# 中文", encoding="utf-8")
    (task / "task.toml").write_text('version = "1.0"\n', encoding="utf-8")
    (tmp_path / "peval.toml").write_text(
        '[[harbor.datasets]]\nid="d"\npath="dataset"\n', encoding="utf-8"
    )
    service = JobsService(tmp_path)
    payload = {
        "harness": "harbor",
        "tasks": ["d/one"],
        "variants": [
            {
                "id": "a",
                "label": "A",
                "agent": "oracle",
                "model": "",
                "options": {"kwargs": {"zero": 0}},
            }
        ],
        "settings": {"n_attempts": 2},
    }
    preview = service.preview(payload)
    assert preview["prepared"]["trial_count"] == 2
    assert preview["prepared"]["config"]["agents"][0]["kwargs"]["zero"] == 0
    (task / "instruction.md").write_text("Changed", encoding="utf-8")
    with pytest.raises(JobsConflict):
        service.start(payload, preview["preview_id"], "changed-task")
    payload["settings"]["typo"] = True
    with pytest.raises(ValueError, match="unknown field"):
        service.preview(payload)
    payload["settings"] = {"jobs_dir": "outside"}
    with pytest.raises(ValueError, match="managed"):
        service.preview(payload)


@pytest.mark.parametrize("variant_count", [1, 2])
def test_native_harbor_job_lifecycle_and_mapping(jobs, variant_count):
    task = jobs.workspace / "dataset/one"
    (task / "tests").mkdir(parents=True)
    (task / "environment").mkdir()
    (task / "tests/test.sh").write_text("echo 1", encoding="utf-8")
    (task / "instruction.md").write_text(
        "A deterministic nop fixture.", encoding="utf-8"
    )
    (task / "task.toml").write_text('version="1.0"\n', encoding="utf-8")
    with (jobs.workspace / "peval.toml").open("a", encoding="utf-8") as stream:
        stream.write('[[harbor.datasets]]\nid="native"\npath="dataset"\n')
    payload = {
        "harness": "harbor",
        "tasks": ["native/one"],
        "variants": [
            {"id": "a", "label": "A", "agent": "nop", "model": "", "options": {}}
        ],
        "settings": {
            "n_attempts": 1,
            "verifier": {"disable": True},
            "environment": {
                "import_path": "psycheval.harbor.environment:HostEnvironment",
                "force_build": False,
                "override_cpus": 0,
                "override_memory_mb": 0,
                "override_storage_mb": 0,
                "override_gpus": 0,
                "kwargs": {
                    "host_access": {"filesystem": True, "process": True},
                    "workdir_root": str(jobs.workspace / "workdirs"),
                },
            },
        },
    }
    if variant_count == 2:
        payload["variants"].append(
            {
                "id": "b",
                "label": "B",
                "agent": "nop",
                "model": "",
                "options": {"env": {"VARIANT": "b"}},
            }
        )
    run = launch(jobs, payload, "native-harbor")
    detail = wait_for(jobs, run["id"], terminal=True)
    assert detail["state"] == "completed", jobs.logs(run["id"])
    assert detail["trials_completed"] == variant_count
    assert {item["variant_id"] for item in detail["results"]} == set(
        "ab"[:variant_count]
    )
    assert all(item["exception"] is None for item in detail["results"])
    assert (jobs.root / run["id"] / "job.yaml").is_file()
    from psycheval.config import load_config
    from psycheval.serve.runtime import ServeRuntime
    from psycheval.state import CatalogQuery, open_workspace_state

    store = open_workspace_state(str(jobs.workspace))
    runtime = ServeRuntime(store, load_config(workspace_root=jobs.workspace))
    try:
        rows = runtime.catalog.query(CatalogQuery()).to_dict()["items"]
        assert len(rows) == variant_count
        assert {row["dataset_id"] for row in rows} == {"native"}
        assert {row["variant_id"] for row in rows} == set("ab"[:variant_count])
        from psycheval.state.jobs import result_identity

        assert {row["source_key"] for row in rows} == {
            result_identity(jobs.workspace, runtime.config, detail, item)
            for item in detail["results"]
        }
        report = runtime.catalog.load_detail(rows[0]["source_key"]).report
        assert report["trajectory_meta"][0]["task_metadata"]["task_ref"] == {
            "dataset_id": "native",
            "task": "one",
        }
    finally:
        runtime.close()
        store.close()
