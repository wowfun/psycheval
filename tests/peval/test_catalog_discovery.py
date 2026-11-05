from __future__ import annotations

import errno
import json
import os
import subprocess
import threading
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from psycheval.config import HarborDataset, HarborMount, ToolConfig
from psycheval.serve import ServeAccess, ServeRuntime
from psycheval.serve.api import create_app
from psycheval.state import (
    CatalogQuery,
    WorkspaceCatalog,
    harbor_evidence,
    open_workspace_state,
)
from tests.peval.serve_state_support import wait_catalog_operation
from tests.peval.test_harbor_evidence import write_evidence_trial, write_task
from tests.peval.test_harbor_trials import completed_result, write_trial


@pytest.fixture
def workspace(tmp_path):
    task = tmp_path / "dataset/task"
    write_task(task, "org/task")
    jobs = tmp_path / "jobs"
    for name in ("first", "second"):
        result = {**completed_result(), "trial_name": name, "task_name": "org/task"}
        write_evidence_trial(
            jobs / "job" / name,
            config_task={"name": "task", "source": "org"},
            result=result,
        )
    store = open_workspace_state(str(tmp_path / "workspace"))
    config = ToolConfig(
        workspace_root=str(store.paths.root),
        harbor_datasets=(HarborDataset(id="fixture", path=str(task.parent)),),
        harbor_mounts=(
            HarborMount(id="jobs", path=str(jobs), dataset_ids=("fixture",)),
        ),
    )
    yield store, config, jobs, task
    store.close()


def evidence_reads(catalog):
    paths = []
    original = harbor_evidence._read_bytes_no_follow

    def read(root, path):
        paths.append(path)
        return original(root, path)

    with patch.object(harbor_evidence, "_read_bytes_no_follow", side_effect=read):
        catalog.reconcile()
    return paths


def test_restart_reuses_trials_without_body_reads_and_shares_cold_job_reads(workspace):
    store, config, jobs, _task = workspace
    cold_reads = evidence_reads(WorkspaceCatalog(store, config))
    assert cold_reads.count(jobs / "job/config.json") == 1
    restarted = WorkspaceCatalog(store, config)
    from psycheval.state.workspace_sources import read_harbor_verifier_evidence

    with patch(
        "psycheval.state.workspace_sources.read_harbor_verifier_evidence",
        wraps=read_harbor_verifier_evidence,
    ) as verifier:
        assert evidence_reads(restarted) == []
        verifier.assert_not_called()
    page = restarted.query(CatalogQuery())
    assert page.total == 2
    assert {item.payload["dataset_id"] for item in page.items} == {"fixture"}


def test_only_missing_sources_need_separate_overlay_fingerprints(workspace):
    from psycheval.state import workspace_sources

    store, config, jobs, _task = workspace
    catalog = WorkspaceCatalog(store, config)
    overlay = catalog.sources.overlay_dir("harbor/jobs/job/first")
    overlay.mkdir(parents=True, exist_ok=True)
    (overlay / "notes.md").write_text("retained note", encoding="utf-8")
    catalog.reconcile()
    with patch.object(
        workspace_sources, "_fingerprint", wraps=workspace_sources._fingerprint
    ) as fingerprint:
        assert evidence_reads(catalog) == []
        assert all(call.args[0] != overlay for call in fingerprint.call_args_list)
        (jobs / "job/first").rename(jobs.parent / "absent")
        catalog.reconcile()
        assert any(call.args[0] == overlay for call in fingerprint.call_args_list)
    rows = catalog.query(CatalogQuery(include_unreadable=True)).items
    assert any(
        row.payload["source_ref"] == "harbor/jobs/job/first"
        and row.payload["last_status"] == "missing"
        for row in rows
    )


def test_restart_shares_directory_checks_within_each_trial(workspace):
    from collections import Counter

    from psycheval.state import catalog_discovery

    store, config, jobs, _task = workspace
    trial = jobs / "job/first"
    (trial / "agent/trajectory.json").unlink()
    write_trial(trial / "steps/one")
    write_trial(trial / "steps/two")
    catalog = WorkspaceCatalog(store, config)
    catalog.reconcile()
    observed = Counter()
    original = catalog_discovery.path_observation

    def count(path, *args):
        observed[path] += 1
        return original(path, *args)

    with patch.object(catalog_discovery, "path_observation", count):
        assert evidence_reads(WorkspaceCatalog(store, config)) == []
    assert observed[trial] == 1
    # The Job metadata probe and each sibling Trial independently check the Job.
    assert observed[jobs / "job"] == 3


def test_changed_trial_reads_only_its_own_body(workspace):
    store, config, jobs, _task = workspace
    catalog = WorkspaceCatalog(store, config)
    catalog.reconcile()
    result = jobs / "job/first/result.json"
    data = json.loads(result.read_text(encoding="utf-8"))
    data["verifier_result"]["rewards"]["reward"] = 0.25
    result.write_text(json.dumps(data), encoding="utf-8")
    reads = evidence_reads(WorkspaceCatalog(store, config))
    assert [path for path in reads if path.name == "trajectory.json"] == [
        jobs / "job/first/agent/trajectory.json"
    ]
    rows = catalog.query(CatalogQuery()).items
    assert (
        next(
            row.payload["score"] for row in rows if row.payload["trial_name"] == "first"
        )
        == 0.25
    )


def test_unrelated_dataset_directories_do_not_invalidate_trials(workspace):
    store, config, _jobs, task = workspace
    WorkspaceCatalog(store, config).reconcile()
    noise = task.parent / "unrelated/cache"
    noise.mkdir(parents=True)
    (noise / "log.txt").write_text("unrelated retained data", encoding="utf-8")
    assert evidence_reads(WorkspaceCatalog(store, config)) == []


def test_task_scratch_contents_do_not_reread_trials_but_unsafe_entries_invalidate(
    workspace,
):
    store, config, _jobs, task = workspace
    catalog = WorkspaceCatalog(store, config)
    catalog.reconcile()
    scratch = task / ".git/objects"
    scratch.mkdir(parents=True)
    (scratch / "object").write_text("ordinary data")
    assert evidence_reads(catalog) == []
    (scratch / "object").unlink()
    assert evidence_reads(catalog) == []
    try:
        (scratch / "link").symlink_to(task / "task.toml")
    except OSError:
        pytest.skip("symlink creation unavailable")
    assert any(p.name == "trajectory.json" for p in evidence_reads(catalog))


def test_linked_parent_invalidates_an_unchanged_leaf_and_blocks_traversal(tmp_path):
    from psycheval.state.catalog_discovery import (
        DirectoryChecks,
        observe_files,
        observe_tree,
    )

    parent = tmp_path / "agent"
    parent.mkdir()
    (parent / "subdir").mkdir()
    (parent / "trajectory.json").write_text("{}")
    names = ("agent/trajectory.json",)
    checks = DirectoryChecks()
    original = observe_files(tmp_path, names, checks)
    target = tmp_path / "moved"
    parent.rename(target)
    if os.name == "nt":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(parent), str(target)], check=True
        )
    else:
        parent.symlink_to(target, target_is_directory=True)
    assert observe_files(tmp_path, names) != original
    with patch(
        "os.scandir", side_effect=AssertionError("must not walk linked parents")
    ):
        assert observe_tree(parent / "subdir")[0][0] == str(parent)
        assert observe_tree(parent / "subdir", checks=checks)[0][0] == str(parent)
    with pytest.raises(ValueError, match="symlink"):
        harbor_evidence._read_bytes_no_follow(tmp_path, parent / "trajectory.json")


def test_directory_replaced_at_scandir_does_not_enumerate_target(tmp_path):
    from psycheval.state.catalog_discovery import observe_tree

    root = tmp_path / "task"
    target = tmp_path / "outside"
    root.mkdir()
    target.mkdir()
    (target / "instruction.md").touch()
    scandir = os.scandir

    def swap(path):
        root.rename(tmp_path / "original")
        if os.name == "nt":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(root), str(target)], check=True
            )
        else:
            root.symlink_to(target, target_is_directory=True)
        return scandir(path)

    with patch("os.scandir", swap):
        observations = observe_tree(root, task_package=True)
    assert {entry[0] for entry in observations} == {str(root)}
    assert observations[-1] != observations[0]


def test_unreadable_tree_and_empty_tree_have_different_manifests(tmp_path):
    from psycheval.state.catalog_discovery import observe_tree

    root = tmp_path / "empty"
    root.mkdir()
    empty = observe_tree(root)
    with patch("os.scandir", side_effect=PermissionError(errno.EACCES, "denied")):
        failed = observe_tree(root)
    assert failed == [*empty, [str(root), "enumeration-error", errno.EACCES]]


def test_source_io_holds_no_main_database_write_lock_even_after_first_projection(
    workspace,
):
    store, config, _jobs, _task = workspace
    catalog = WorkspaceCatalog(store, config)
    hydrate = catalog.sources.load
    checked = []

    def read(candidate):
        with catalog._connect() as probe:
            probe.execute("PRAGMA busy_timeout=0")
            probe.execute("BEGIN IMMEDIATE")
            probe.rollback()
        checked.append(candidate.source_ref)
        return hydrate(candidate)

    with patch.object(catalog.sources, "load", side_effect=read):
        catalog.reconcile()
    assert len(checked) == 2


@pytest.mark.parametrize(
    "dependency", ["job", "task", "verifier", "overlay", "telemetry"]
)
def test_dependencies_invalidate_the_affected_trials(workspace, dependency):
    store, config, jobs, task = workspace
    catalog = WorkspaceCatalog(store, config)
    catalog.reconcile()
    if dependency == "job":
        path = jobs / "job/config.json"
    elif dependency == "task":
        path = task / "instruction.md"
    elif dependency == "verifier":
        path = jobs / "job/first/verifier/score.json"
    elif dependency == "overlay":
        path = store.paths.root / "harbor/jobs/job/first/notes.md"
    else:
        path = jobs / "job/first/agent/hermes-session.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        data["changed"] = True
        path.write_text(json.dumps(data), encoding="utf-8")
    else:
        path.write_text("changed\n", encoding="utf-8")
    reads = evidence_reads(WorkspaceCatalog(store, config))
    roots = {
        path.parent.parent.name for path in reads if path.name == "trajectory.json"
    }
    assert roots == (
        {"first", "second"} if dependency in {"job", "task"} else {"first"}
    )


@pytest.mark.parametrize("cache", ["row", "metrics", "discovery", "dependencies"])
def test_bad_cache_is_reloaded_even_when_its_dependencies_match(workspace, cache):
    store, config, jobs, _task = workspace
    catalog = WorkspaceCatalog(store, config)
    catalog.reconcile()
    with catalog._connect() as connection:
        update = {
            "row": "UPDATE cells SET row_json = '{}'",
            "metrics": "UPDATE cells SET row_json = json_set(row_json, '$.metric_values', json_object('bad', 'junk'))",
            "discovery": "UPDATE source_scans SET candidates_json = '{}'",
            "dependencies": "UPDATE source_scans SET dependencies_json = '{}'",
        }[cache]
        connection.execute(update + " WHERE source_ref LIKE '%/first'")
        connection.commit()
    reads = evidence_reads(WorkspaceCatalog(store, config))
    assert [path for path in reads if path.name == "trajectory.json"] == [
        jobs / "job/first/agent/trajectory.json"
    ]
    assert catalog.query(CatalogQuery()).total == 2


def test_invalid_projected_metrics_preserve_previous_generation(workspace):
    store, config, jobs, _task = workspace
    catalog = WorkspaceCatalog(store, config)
    generation = catalog.reconcile()
    project = catalog._row_for_document
    (jobs / "job/first/analysis.md").write_text("changed", encoding="utf-8")

    def invalid_projection(document):
        row, readable, search_doc = project(document)
        row["metric_values"] = {"bad": "junk"}
        return row, readable, search_doc

    with patch.object(catalog, "_row_for_document", side_effect=invalid_projection):
        with pytest.raises(ValueError, match="metric"):
            catalog.reconcile()
    assert catalog.generation == generation
    with catalog._connect() as connection:
        assert not connection.execute(
            "SELECT 1 FROM metric_values WHERE metric_id = 'bad'"
        ).fetchone()


def test_unchanged_scan_preserves_metric_registry(workspace):
    store, config, _jobs, _task = workspace
    catalog = WorkspaceCatalog(store, config)
    catalog.reconcile()
    with catalog._connect() as connection:
        connection.execute("""CREATE TRIGGER check_registry BEFORE DELETE ON metric_registry
            BEGIN SELECT RAISE(ABORT, 'unchanged registry rewritten'); END""")
    catalog.reconcile()


def test_change_during_projection_cannot_be_hidden_by_the_discovery_cache(workspace):
    store, config, jobs, _task = workspace
    catalog = WorkspaceCatalog(store, config)
    original = catalog.sources.load

    def load(candidate):
        document = original(candidate)
        if candidate.trial_name == "first":
            path = jobs / "job/first/result.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["verifier_result"]["rewards"]["reward"] = 0.125
            path.write_text(json.dumps(data), encoding="utf-8")
        return document

    with patch.object(catalog.sources, "load", side_effect=load):
        catalog.reconcile()
    reads = evidence_reads(WorkspaceCatalog(store, config))
    assert [path for path in reads if path.name == "trajectory.json"] == [
        jobs / "job/first/agent/trajectory.json"
    ]
    assert (
        next(
            row.payload["score"]
            for row in catalog.query(CatalogQuery()).items
            if row.payload["trial_name"] == "first"
        )
        == 0.125
    )


@pytest.mark.parametrize("manifest", ["intact", "missing", "duplicate"])
def test_multistep_trial_counts_once_and_new_steps_invalidate_discovery(
    workspace, manifest
):
    store, config, jobs, _task = workspace
    trial = jobs / "job/first"
    (trial / "agent/trajectory.json").unlink()
    write_trial(trial / "steps/one")
    write_trial(trial / "steps/two")
    catalog = WorkspaceCatalog(store, config)
    catalog.reconcile()
    assert catalog.query(CatalogQuery()).total == 3
    assert catalog.scan_status()["completed"] == 2
    assert catalog.scan_status()["total"] == 2
    if manifest != "intact":
        with catalog._connect() as connection:
            records = json.loads(
                connection.execute(
                    "SELECT candidates_json FROM source_scans WHERE source_ref LIKE '%/first'"
                ).fetchone()[0]
            )
            damaged = records[:1] if manifest == "missing" else [records[0], records[0]]
            connection.execute(
                "UPDATE source_scans SET candidates_json = ? WHERE source_ref LIKE '%/first'",
                (json.dumps(damaged),),
            )
            connection.commit()
    reads = evidence_reads(WorkspaceCatalog(store, config))
    if manifest == "intact":
        assert reads == []
    assert catalog.query(CatalogQuery()).total == 3
    write_trial(trial / "steps/three")
    restarted = WorkspaceCatalog(store, config)
    evidence_reads(restarted)
    assert restarted.query(CatalogQuery()).total == 4
    assert restarted.scan_status()["total"] == 2


def test_removing_all_trial_evidence_drops_its_cached_identity(workspace):
    store, config, jobs, _task = workspace
    catalog = WorkspaceCatalog(store, config)
    catalog.reconcile()
    trial = jobs / "job/first"
    for path in trial.rglob("*"):
        if path.is_file():
            path.unlink()
    catalog.reconcile()
    remaining = catalog.query(CatalogQuery(include_unreadable=True))
    assert remaining.total == 1
    with catalog._connect(readonly=True) as connection:
        assert [
            row[0] for row in connection.execute("SELECT source_key FROM cell_search")
        ] == [remaining.items[0].source_key]
    assert evidence_reads(WorkspaceCatalog(store, config)) == []


def test_cold_status_is_nonblocking_and_counts_only_processed_trials(workspace):
    store, config, _jobs, _task = workspace
    runtime = ServeRuntime(store, config, initialize_snapshot=False)
    entered = threading.Event()
    release = threading.Event()
    original = runtime.catalog.sources._harbor_trial_candidates
    failures = []

    def hold(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)

    def reconcile():
        try:
            runtime.catalog.reconcile()
        except Exception as exc:
            failures.append(exc)

    try:
        with patch.object(
            runtime.catalog.sources, "_harbor_trial_candidates", side_effect=hold
        ):
            thread = threading.Thread(target=reconcile)
            thread.start()
            try:
                assert entered.wait(5)
                with TestClient(create_app(runtime, ServeAccess(None))) as client:
                    status = client.get("/api/catalog-status").json()
                    assert status["checking"] is True
                    assert (status["phase"], status["completed"], status["total"]) == (
                        "checking",
                        0,
                        2,
                    )
                    assert client.get("/api/catalog").json()["items"] == []
                    assert (
                        client.post(
                            "/api/source-discovery-operations", json={}
                        ).status_code
                        == 409
                    )
            finally:
                release.set()
                thread.join(5)
            assert not thread.is_alive()
            assert not failures
        assert runtime.catalog_status()["completed"] == 2
    finally:
        runtime.close()


def test_slow_status_meta_read_leaves_progress_and_runtime_locks_available(workspace):
    from concurrent.futures import ThreadPoolExecutor

    store, config, _jobs, _task = workspace
    runtime = ServeRuntime(store, config)
    entered = threading.Event()
    release = threading.Event()
    read_meta = runtime.catalog._meta_int

    def slow_read(*args):
        entered.set()
        assert release.wait(5)
        return read_meta(*args)

    try:
        with (
            patch.object(runtime.catalog, "_meta_int", slow_read),
            ThreadPoolExecutor(1) as pool,
        ):
            status = pool.submit(runtime.catalog_status)
            try:
                assert entered.wait(5)
                for lock in (runtime._lock, runtime.catalog._state_lock):
                    assert lock.acquire(blocking=False)
                    lock.release()
            finally:
                release.set()
            assert status.result()["generation"] > 0
    finally:
        runtime.close()


def test_startup_keeps_old_rows_and_guest_status_hides_errors(workspace):
    store, config, _jobs, _task = workspace
    runtime = ServeRuntime(store, config)
    try:
        runtime._loading = True
        runtime._ready.clear()
        with TestClient(create_app(runtime, ServeAccess(None))) as admin:
            page = admin.get("/api/catalog").json()
            assert page["checking"] and page["stale"]
            assert page["total"] == 2
            assert admin.get("/api/catalog-status").json()["checking"] is True
        runtime._loading = False
        runtime._load_error = "failed to read C:/private/trial"
        with TestClient(create_app(runtime, ServeAccess("fixture"))) as guest:
            status = guest.get("/api/catalog-status").json()
            assert status["generation"] > 0
            assert status["error"] == "internal server error"
            assert "operation_id" not in status
            assert "private" not in json.dumps(status)
    finally:
        runtime._ready.set()
        runtime.close()


def test_manual_refresh_discovers_once_and_failed_scan_keeps_generation(workspace):
    store, config, _jobs, _task = workspace
    runtime = ServeRuntime(store, config)
    original = runtime.catalog.sources.catalog_batches
    calls = []

    def batches(*args, **kwargs):
        calls.append(1)
        yield from original(*args, **kwargs)

    try:
        with TestClient(create_app(runtime, ServeAccess(None))) as client:
            with patch.object(
                runtime.catalog.sources, "catalog_batches", side_effect=batches
            ):
                response = client.post("/api/source-discovery-operations", json={})
                assert response.status_code == 202
                operation_id = response.json()["id"]
                wait_catalog_operation(runtime.catalog, operation_id)
                assert len(calls) == 1
                status = client.get(f"/api/operations/{operation_id}").json()[
                    "catalog_status"
                ]
                assert status["completed"] == status["total"] == 2
                assert status["operation_id"] == operation_id
                assert (
                    client.get("/api/catalog-status").json()["operation_id"]
                    == operation_id
                )
                with TestClient(create_app(runtime, ServeAccess("fixture"))) as guest:
                    assert "operation_id" not in guest.get("/api/catalog-status").json()
            generation = runtime.catalog.generation
            with patch.object(
                runtime.catalog.sources,
                "catalog_batches",
                side_effect=ValueError("fixture scan failed"),
            ):
                with pytest.raises(ValueError, match="fixture scan failed"):
                    runtime.catalog.reconcile()
            assert runtime.catalog.generation == generation
            assert client.get("/api/catalog").json()["total"] == 2
            assert (
                client.get("/api/catalog-status").json()["error"]
                == "fixture scan failed"
            )
    finally:
        runtime.close()
