from __future__ import annotations

import asyncio
import copy
import os
from types import SimpleNamespace

import pytest

from psycheval.jobs.harbor import HarborHarness, task_revision
from psycheval.jobs.storage import digest
from psycheval.jobs.worker import WorkerControl
from psycheval.state.jobs import (
    plugin_candidate_for_ref,
    plugin_candidates,
    plugin_document,
)
from tests.peval.test_jobs import jobs as jobs
from tests.peval.test_jobs import request, retained_run


def native(**updates):
    return {
        "id": "one",
        "task": "task",
        "state": "completed",
        "score": 0,
        "score_source": "fixture",
        **updates,
    }


@pytest.mark.parametrize(
    "invalid",
    [
        {"task": "x"},
        None,
        float("nan"),
        {"id": "x", "score": float("nan")},
        {"id": "x", "extra": {1, 2}},
        native(agent_name={"bad": "type"}),
        native(model=["bad"]),
        native(extra={1: "not a JSON object key"}),
        native(extra=("sk-abcdefghijklmnop1234",)),
        native(score=10**400),
    ],
)
def test_plugin_invalid_sibling_does_not_hide_result(jobs, monkeypatch, invalid):
    path = retained_run(jobs, job_name="2026-09-11__10-00-00")
    monkeypatch.setattr(
        jobs.registry["fixture"], "read_results", lambda _: [invalid, native()]
    )
    detail = jobs.detail(path.name)
    assert [row["id"] for row in detail["results"]] == ["one"]
    assert "Trial 1" in detail["result_error"]
    monkeypatch.setattr("psycheval.jobs.service.harnesses", lambda: jobs.registry)
    assert len(plugin_candidates(jobs.workspace)) == 1


def test_plugin_exception_is_local_diagnostic(jobs, monkeypatch):
    path = retained_run(jobs, job_name="2026-09-11__10-00-00")

    def broken(_):
        raise TypeError("plugin failed")

    monkeypatch.setattr(jobs.registry["fixture"], "read_results", broken)
    assert jobs.detail(path.name)["result_error"] == "plugin failed"
    assert len(jobs.list()) == 1


def test_deep_plugin_result_is_rejected_independently(jobs, monkeypatch):
    path = retained_run(jobs, job_name="2026-09-11__10-00-00")
    nested = "leaf"
    for _ in range(65):
        nested = [nested]
    monkeypatch.setattr(
        jobs.registry["fixture"],
        "read_results",
        lambda _: [native(extra=nested), native()],
    )
    detail = jobs.detail(path.name)
    assert len(detail["results"]) == 1
    assert "64 levels" in detail["result_error"]


@pytest.mark.parametrize(
    "name,body", [("missing.json", None), ("bad.json", "[]"), ("../escape.json", "{}")]
)
def test_optional_trajectory_failure_preserves_native_result(
    jobs, monkeypatch, name, body
):
    retained_run(jobs, job_name="2026-09-11__10-00-00")
    output = jobs.workspace / "jobs/2026-09-11__10-00-00"
    output.mkdir(parents=True)
    if body is not None:
        (output / name).write_text(body, encoding="utf-8")
    monkeypatch.setattr(
        jobs.registry["fixture"],
        "read_results",
        lambda _: [native(trajectory_path=name)],
    )
    monkeypatch.setattr("psycheval.jobs.service.harnesses", lambda: jobs.registry)
    candidate = plugin_candidates(jobs.workspace)[0]
    document = plugin_document(candidate)
    assert document.trajectory is None
    assert document.meta["score"] == 0
    assert document.meta["trajectory_error"]
    monkeypatch.setattr(
        "psycheval.state.jobs.records",
        lambda _: pytest.fail("direct read scanned other runs"),
    )
    assert (
        plugin_candidate_for_ref(jobs.workspace, candidate.source_ref).source_key
        == candidate.source_key
    )


@pytest.mark.parametrize(
    "progress",
    [
        {"id": "forged"},
        {"state": "completed"},
        {"job_name": "outside"},
        {"trials_total": '<img src=x onerror="x()">'},
        {"trials_started": -1},
        {"trials_completed": True},
    ],
)
def test_progress_cannot_spoof_worker_identity_or_counts(jobs, progress):
    path = retained_run(jobs)
    control = WorkerControl(jobs, path.name)
    before = copy.deepcopy(control.state)
    with pytest.raises(ValueError):
        control.report(**progress)
    assert control.state == before
    control.report(trials_completed=0, current_trial="one")
    assert control.state["trials_completed"] == 0


@pytest.mark.parametrize("identity", ['bad"', "bad\n", "bad]", "bad.dot"])
def test_defaults_reject_invalid_harness_identity_before_write(jobs, identity):
    before = (jobs.workspace / "peval.toml").read_bytes()
    with pytest.raises(ValueError, match="harness identity"):
        jobs.save_defaults(identity, {}, jobs.configuration()[1])
    assert (jobs.workspace / "peval.toml").read_bytes() == before


def test_unknown_defaults_subtable_is_rejected_without_loss(jobs):
    path = jobs.workspace / "peval.toml"
    with path.open("a", encoding="utf-8") as stream:
        stream.write('[jobs.defaults.fixture.extra]\nkeep="retained"\n')
    before = path.read_bytes()
    with pytest.raises(ValueError):
        jobs.save_defaults("fixture", {}, "unused")
    assert path.read_bytes() == before


def test_logs_redact_recognized_keys_and_environment_for_every_reader(
    jobs, monkeypatch
):
    path = retained_run(jobs)
    monkeypatch.setenv("FIXTURE_API_KEY", "known-credential-12345")
    secrets = ["sk-abcdefghijklmnop12345", "bearer-value-123", "known-credential-12345"]
    (path / "worker.log").write_text(
        f"{secrets[0]} Bearer {secrets[1]} {secrets[2]}", encoding="utf-8"
    )
    entries = jobs.logs(path.name)["entries"]
    assert entries
    assert all(secret not in entry["text"] for entry in entries for secret in secrets)


def test_shared_revision_budget_caches_shared_files(tmp_path):
    task, shared = tmp_path / "task", tmp_path / "shared"
    task.mkdir()
    shared.mkdir()
    (task / "task.txt").write_text("task")
    (shared / "shared.txt").write_text("shared")
    budget, cache = {"entries": 0, "bytes": 0}, {}
    first = task_revision(task, shared, budget=budget, cache=cache)
    assert budget == {"entries": 2, "bytes": 10}
    assert task_revision(task, shared, budget=budget, cache=cache) == first
    assert budget == {"entries": 2, "bytes": 10}
    with pytest.raises(ValueError, match="100000"):
        task_revision(task, budget={"entries": 100000, "bytes": 0})


def test_worker_rejects_unregistered_retained_path_before_hashing(jobs, monkeypatch):
    task = jobs.workspace / "dataset/one"
    (task / "tests").mkdir(parents=True)
    (task / "task.toml").write_text('version="1.0"\n')
    (task / "instruction.md").write_text("task")
    (task / "tests/test.sh").write_text("true")
    with (jobs.workspace / "peval.toml").open("a", encoding="utf-8") as stream:
        stream.write('[[harbor.datasets]]\nid="native"\npath="dataset"\n')
    payload = request()
    payload.update(harness="harbor", tasks=["native/one"])
    payload["variants"][0].update(agent="nop", model="")
    prepared = jobs.preview(payload)["prepared"]
    prepared["selection"][0]["path"] = str(jobs.workspace.parent)
    prepared["config"]["tasks"][0]["path"] = str(jobs.workspace.parent)
    monkeypatch.setattr(
        "psycheval.jobs.harbor.task_revision",
        lambda *a, **k: pytest.fail("unregistered path was hashed"),
    )
    with pytest.raises(ValueError, match="registered"):
        asyncio.run(
            HarborHarness().execute(prepared, SimpleNamespace(workspace=jobs.workspace))
        )


def test_nan_cannot_be_used_in_identity_digest():
    with pytest.raises(ValueError):
        digest({"score": float("nan")})


def test_malformed_variant_mapping_is_not_projected(jobs):
    from psycheval.jobs.storage import write_json
    from psycheval.state.jobs import variant_index

    path = retained_run(jobs, job_name="2026-09-11__10-00-00")
    write_json(
        path / "variants.json",
        {
            "bad": {"id": ["bad"], "label": "bad"},
            "good": {"id": "a", "label": "A"},
        },
    )
    index = variant_index(jobs.workspace)
    assert ("2026-09-11__10-00-00", "bad") not in index
    assert index[("2026-09-11__10-00-00", "good")]["variant_id"] == "a"


def test_broken_plugin_description_is_local(jobs, monkeypatch):
    def broken(_):
        raise TypeError("unavailable description")

    monkeypatch.setattr(jobs.registry["fixture"], "describe", broken)
    description = jobs.options()["harnesses"][0]
    assert description["available"] is False
    assert description["error"] == "unavailable description"


def test_registry_caches_and_isolates_failed_entry_points(monkeypatch):
    import psycheval.jobs as module

    calls = []

    def broken():
        calls.append(1)
        raise ImportError("missing dependency")

    module._registered_harnesses.cache_clear()
    monkeypatch.setattr(
        module,
        "entry_points",
        lambda **_: [SimpleNamespace(name="broken", load=broken)],
    )
    try:
        assert "harbor" in module.harnesses()
        assert module.harnesses()["broken"].describe(None)["available"] is False
        assert len(calls) == 1
    finally:
        module._registered_harnesses.cache_clear()


def test_preparation_conflict_releases_lock(jobs):
    from psycheval.jobs.storage import JobsConflict

    jobs._prepare_lock.acquire()
    try:
        with pytest.raises(JobsConflict):
            jobs.preview(request())
    finally:
        jobs._prepare_lock.release()
    assert jobs.preview(request())["preview_id"]


def test_managed_junction_does_not_hide_unrelated_sources(jobs):
    import subprocess

    from psycheval.config import ToolConfig
    from psycheval.state.jobs import managed_config, records

    if os.name != "nt":
        pytest.skip("native Windows junction")
    outside = jobs.workspace / "outside"
    outside.mkdir()
    jobs.root.mkdir(parents=True)
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(jobs.workspace / "jobs"), str(outside)],
        check=True,
        capture_output=True,
    )
    config = ToolConfig()
    assert managed_config(config, jobs.workspace) is config
    assert records(jobs.workspace) == []
