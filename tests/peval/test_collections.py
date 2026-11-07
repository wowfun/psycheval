import json
from unittest.mock import patch

import pytest

from psycheval.config import HarborDataset, HarborMount, ToolConfig
from psycheval.serve.collections import WorkspaceCollections
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import CatalogQuery, open_workspace_state
from psycheval.state.collections import NOTE_LIMIT, CollectionConflict, CollectionStore
from tests.peval.serve_state_support import peval_workspace
from tests.peval.test_harbor_trials import completed_result, write_trial


def test_notes_preserve_markdown_and_reject_stale_edits(tmp_path):
    store = CollectionStore(tmp_path)
    source = tmp_path / "outside"
    before = store.read("dataset", source)
    note = "# 中文\n\n- first\n- second\n"
    saved = store.save_note("dataset", source, note, before["revision"])
    assert (store.root("dataset", source) / "notes.md").read_bytes() == note.encode()
    with pytest.raises(CollectionConflict):
        store.save_note("dataset", source, "stale", before["revision"])
    assert store.read("dataset", source) == saved
    with pytest.raises(ValueError, match="64 KiB"):
        store.save_note("dataset", source, "文" * NOTE_LIMIT, saved["revision"])
    store.save_note("dataset", source, "", saved["revision"])
    assert not (store.root("dataset", source) / "notes.md").exists()
    assert not source.exists()


def test_archive_and_note_share_revision_without_overwriting_each_other(tmp_path):
    store = CollectionStore(tmp_path)
    source = tmp_path / "job"
    old = store.read("job", source)
    archived = store.set_archived(source, True, 4, old["revision"])
    with pytest.raises(CollectionConflict):
        store.save_note("job", source, "stale", old["revision"])
    saved = store.save_note("job", source, "note", archived["revision"])
    assert saved["archived"] and saved["trial_count"] == 4
    assert store.set_archived(source, False, None, saved["revision"])["note"] == "note"


@pytest.fixture
def collection_runtime(tmp_path):
    workspace = peval_workspace(tmp_path)
    jobs = workspace / "external"
    trial = jobs / "ended" / "trial"
    write_trial(trial, result=completed_result())
    (trial.parent / "result.json").write_text(
        json.dumps({"finished_at": "2026-11-07T00:00:00Z"})
    )
    dataset = workspace / "dataset"
    dataset.mkdir()
    config = ToolConfig(
        workspace_root=str(workspace),
        harbor_mounts=(HarborMount(id="external", path=str(jobs)),),
        harbor_datasets=(HarborDataset(id="dataset", path=str(dataset)),),
    )
    store = open_workspace_state(str(workspace))
    runtime = ServeRuntime(store, config)
    runtime.ensure_ready()
    try:
        yield runtime, trial
    finally:
        runtime.close()
        store.close()


def test_collection_jobs_counts_and_guest_projection(collection_runtime):
    runtime, trial = collection_runtime
    service = WorkspaceCollections(runtime)
    admin = service.jobs("admin")["items"][0]
    guest = service.jobs("guest")["items"][0]
    assert admin["trial_count"] == 1 and admin["can_archive"]
    assert admin["path"] == str(trial.parent)
    assert (
        not {"path", "mount_ids", "collection_revision", "archived", "can_archive"}
        & guest.keys()
    )
    assert service.detail(admin["id"], "guest", 0)["result_count"] == 1
    assert service.detail(admin["id"], "guest", 0)["results"][0]["score"] == 0.75


def test_archive_skips_trial_reads_and_retained_overlays_then_restores(
    collection_runtime,
):
    runtime, trial = collection_runtime
    service = WorkspaceCollections(runtime)
    item = service.jobs("admin")["items"][0]
    overlay = runtime.catalog.sources.overlay_dir("harbor/external/ended/trial")
    overlay.mkdir(parents=True, exist_ok=True)
    (overlay / "notes.md").write_text("retained note")
    state = service.store.set_archived(
        trial.parent, True, 1, item["collection_revision"]
    )
    from psycheval.state.workspace_sources import _child_dirs

    def no_trials(path):
        assert path != trial.parent, "archived Job was scanned"
        return _child_dirs(path)

    with patch("psycheval.state.workspace_sources._child_dirs", side_effect=no_trials):
        runtime.catalog.reconcile()
    assert runtime.catalog.query(CatalogQuery(state="all")).total == 0
    assert (
        runtime.catalog.summarize_query(CatalogQuery(), name="All", group_by="overall")[
            "summary"
        ]["matched_count"]
        == 0
    )
    assert service.jobs("guest", "all")["items"] == []
    archived = service.jobs("admin", "archived")["items"][0]
    assert archived["trial_count"] == 1 and archived["count_retained"]
    service.store.set_archived(trial.parent, False, None, state["revision"])
    runtime.catalog.reconcile()
    assert runtime.catalog.query(CatalogQuery()).total == 1
    assert (overlay / "notes.md").read_text() == "retained note"


def test_unknown_completion_is_not_archivable(collection_runtime):
    runtime, trial = collection_runtime
    (trial.parent / "result.json").unlink()
    assert not WorkspaceCollections(runtime).jobs("admin")["items"][0]["can_archive"]


@pytest.mark.parametrize(
    "content", [b"{bad", b'{"archived": true, "trial_count": 1.5}']
)
def test_corrupt_job_state_is_isolated_and_explicitly_repairable(
    collection_runtime, content
):
    runtime, trial = collection_runtime
    service = WorkspaceCollections(runtime)
    state = service.store.root("job", trial.parent) / "state.json"
    state.parent.mkdir(parents=True)
    state.write_bytes(content)
    write_trial(trial.parent.parent / "healthy" / "trial", result=completed_result())
    runtime.catalog.reconcile()
    assert runtime.catalog.query(CatalogQuery()).total == 1
    assert [row["name"] for row in service.jobs("guest")["items"]] == ["healthy"]
    row = service.jobs("admin", "archived")["items"][0]
    assert row["state_error"] and row["trial_count"] is None
    assert state.read_bytes() == content
    service.store.set_archived(trial.parent, False, None, row["collection_revision"])
    runtime.catalog.reconcile()
    assert runtime.catalog.query(CatalogQuery()).total == 2


def test_notes_coordinate_concurrent_writers(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    store = CollectionStore(tmp_path)
    source = tmp_path / "source"
    revision = store.read("dataset", source)["revision"]

    def save(note):
        try:
            return store.save_note("dataset", source, note, revision)["note"]
        except CollectionConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(save, ["one", "two"]))
    assert results.count("conflict") == 1
    assert store.read("dataset", source)["note"] in {"one", "two"}


def test_notes_reject_linked_overlay_directory(tmp_path):
    import os

    store = CollectionStore(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / ".peval" / "collections" / "dataset"
    link.parent.mkdir(parents=True)
    if os.name == "nt":
        import _winapi

        _winapi.CreateJunction(str(outside), str(link))
    else:
        link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError):
        store.read("dataset", tmp_path / "source")
    assert not list(outside.iterdir())


def test_archived_plugin_job_does_not_read_retained_results(tmp_path):
    from psycheval.state.jobs import plugin_candidates

    store = CollectionStore(tmp_path)
    path = tmp_path / "jobs" / "2026-11-07__01-00-00"
    state = {"id": "a" * 32, "harness": "fixture", "job_name": path.name}
    store.set_archived(path, True, 3, store.read("job", path)["revision"])
    with (
        patch("psycheval.state.jobs.records", return_value=[(tmp_path, state)]),
        patch("psycheval.jobs.service.JobsService") as service,
    ):
        assert plugin_candidates(tmp_path) == []
        service.return_value.detail.assert_not_called()


def test_count_deduplicates_mount_aliases_and_step_projections(collection_runtime):
    runtime, trial = collection_runtime
    service = WorkspaceCollections(runtime)
    job = service._jobs()[0]
    job["job_refs"].append("harbor/alias/ended/")
    rows = [
        {"source_ref": ref}
        for ref in (
            "harbor/external/ended/trial",
            "harbor/external/ended/trial/step-1",
            "harbor/alias/ended/trial",
            "harbor/external/ended/second/step-1",
            "harbor/external/ended/second/step-2",
            "runs/jobs/fixture/run/first",
            "runs/jobs/fixture/run/second",
            "runs/jobs/fixture/other/third",
        )
    ]
    groups = service._trial_groups(rows)
    assert len(service._trials(job, groups)) == 2
    assert service._trials(job, groups)[0]["source_ref"].endswith("/trial")
    assert (
        len(
            service._trials(
                {"job_refs": [], "run_id": "run", "harness": "fixture"}, groups
            )
        )
        == 2
    )


def test_http_permissions_revisions_archive_and_restore(collection_runtime):
    from fastapi.testclient import TestClient

    from psycheval.serve.access import ServeAccess
    from psycheval.serve.api import create_app
    from tests.peval.serve_state_support import wait_catalog_operation

    runtime, trial = collection_runtime
    admin = TestClient(create_app(runtime, ServeAccess(None)))
    guest = TestClient(create_app(runtime, ServeAccess("secret")))
    job = admin.get("/api/collections/jobs").json()["items"][0]
    identity = job["id"]
    note_url = f"/api/collections/job/{identity}/note"
    body = {"note": "中文\n\nline two", "revision": job["collection_revision"]}
    assert guest.put(note_url, json=body).status_code == 403
    assert (
        guest.post("/api/collections/job-state-operations", json={}).status_code == 403
    )
    assert admin.put(note_url, json=body).status_code == 200
    assert admin.put(note_url, json=body).status_code == 409
    assert admin.put("/api/collections/job/unknown/note", json=body).status_code == 404
    latest = admin.get("/api/collections/jobs").json()["items"][0]
    assert latest["note"] == body["note"]
    before = runtime.catalog.generation

    def archive(value):
        response = admin.post(
            "/api/collections/job-state-operations",
            json={
                "archived": value,
                "items": [{"id": identity, "revision": latest["collection_revision"]}],
            },
        )
        assert response.status_code == 202, response.text
        return wait_catalog_operation(runtime.catalog, response.json()["id"])

    # A failed task is not evidence that its Job ended.
    (trial.parent / "result.json").write_text(json.dumps({"started_at": "2026-11-07"}))
    assert (
        admin.get("/api/collections/jobs").json()["items"][0]["state"] == "unfinished"
    )
    assert archive(True).failures
    assert runtime.catalog.query(CatalogQuery()).total == 1
    (trial.parent / "result.json").write_text(
        json.dumps({"finished_at": "2026-11-07T01:00:00Z"})
    )
    assert not archive(True).failures
    assert runtime.catalog.generation > before
    assert admin.get("/api/catalog").json()["total"] == 0
    from io import BytesIO
    from zipfile import ZipFile

    exported = admin.post("/api/exports", json={"kind": "xlsx", "query": {}})
    assert exported.status_code == 200
    with ZipFile(BytesIO(exported.content)) as workbook:
        assert workbook.read("xl/worksheets/sheet1.xml").count(b"<row ") == 1
    assert guest.get(f"/api/collections/jobs/{identity}").status_code == 404
    assert guest.get("/api/collections/jobs?state=all").json()["items"] == []
    latest = admin.get("/api/collections/jobs?state=archived").json()["items"][0]
    assert latest["trial_count"] == 1 and latest["count_retained"]
    assert not archive(False).failures
    assert admin.get("/api/catalog").json()["total"] == 1


def test_dataset_missing_is_not_zero_and_public_fields_are_trimmed(collection_runtime):
    runtime, _trial = collection_runtime
    service = WorkspaceCollections(runtime)
    public = service.datasets("guest")["datasets"][0]
    assert public["task_count"] == 0
    assert not {"path", "mount_ids", "collection_revision"} & public.keys()
    from pathlib import Path

    Path(runtime.config.harbor_datasets[0].path).rmdir()
    public = service.datasets("guest")["datasets"][0]
    assert public["task_count"] is None and public["error"] == "Dataset unavailable"


def test_reports_count_matches_filtered_library_and_deduplicates_associations(
    collection_runtime,
):
    runtime, trial = collection_runtime
    canonical = trial / "analysis.md"
    canonical.write_bytes(b"# Native report\n")
    runtime.catalog.reconcile()
    source = runtime.catalog.query(CatalogQuery()).items[0].to_dict()["source_key"]
    report = trial.parent / "report.md"
    report.write_text("# Report")
    report_id = runtime.workspace_reports.import_file(
        report, [source], dataset_ids=["dataset"], job_refs=["harbor:external/ended"]
    )
    service = WorkspaceCollections(runtime)
    # Only the imported report has a Dataset binding in this fixture.
    assert service.datasets("admin")["datasets"][0]["report_count"] == 1
    job = service.jobs("admin")["items"][0]
    assert (
        job["report_count"]
        == runtime.report_library.query(jobs=[job["report_ref"]])["total"]
        == 2
    )
    saved = service.store.set_archived(
        trial.parent, True, 1, job["collection_revision"]
    )
    runtime.catalog.reconcile()
    assert service.jobs("admin", "archived")["items"][0]["report_count"] == 1
    assert runtime.report_library.query(datasets=["dataset"])["total"] == 1
    assert canonical.read_bytes() == b"# Native report\n"
    assert saved["archived"]
    runtime.report_library.set_archived("package:" + report_id, True)
    assert service.jobs("admin", "archived")["items"][0]["report_count"] == 0
    assert service.datasets("admin")["datasets"][0]["report_count"] == 0


def test_pending_runs_are_listed_without_inventing_directory_identity(
    collection_runtime,
):
    runtime, _trial = collection_runtime
    row = WorkspaceCollections(runtime).jobs(
        "admin",
        runs=[
            {
                "id": "pending",
                "state": "preparing",
                "harness": "fixture",
            }
        ],
    )["items"][0]
    assert row["run_id"] == "pending" and row["path"] is None
    assert row["collection_revision"] is None and not row["can_archive"]
    assert row["trial_count"] == 0


def test_managed_and_mounted_results_share_job_and_report_associations(
    collection_runtime,
):
    from psycheval.jobs.storage import write_json

    runtime, _trial = collection_runtime
    root = runtime.store.paths.root
    name, run_id = "2026-11-07__01-00-00", "a" * 32
    trial = root / "jobs" / name / "trial"
    write_trial(trial, result=completed_result())
    (root / ".peval" / "jobs" / run_id).mkdir(parents=True)
    write_json(
        root / ".peval" / "jobs" / run_id / "state.json",
        {
            "id": run_id,
            "harness": "harbor",
            "state": "completed",
            "submitted_at": "2026-11-07T01:00:00Z",
            "job_name": name,
        },
    )
    runtime.set_config(
        runtime.config.validated_update(
            harbor_mounts=(
                *runtime.config.harbor_mounts,
                HarborMount(id="managed", path=str(root / "jobs")),
            )
        )
    )
    runtime.catalog.reconcile()
    report = trial.parent / "report.md"
    report.write_text("# Report")
    runtime.workspace_reports.import_file(
        report, [], job_refs=[f"harbor:managed/{name}", f"managed:{run_id}"]
    )
    items = WorkspaceCollections(runtime).jobs("admin")["items"]
    assert len(items) == 2
    job = next(row for row in items if row["run_id"] == run_id)
    assert job["trial_count"] == 1 and job["report_count"] == 1
    assert runtime.report_library.query(jobs=[job["report_ref"]])["total"] == 1
