import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from psycheval.config import HarborDataset, HarborMount, ToolConfig
from psycheval.serve.acp_references import (
    reference_candidates,
    reference_path,
    reference_value,
)
from psycheval.serve.errors import HttpError
from psycheval.serve.harbor_workspace import HarborWorkspace
from psycheval.state import open_workspace_state
from psycheval.state.catalog import CatalogRow, WorkspaceCatalog
from psycheval.state.workspace_sources import WorkspaceSources
from tests.peval.test_workbuddy_datasets import _write_workbuddy_bundle


@pytest.mark.parametrize("kind", [["source"], {}, 7, None])
def test_invalid_kind_is_a_client_error(reference_runtime, kind):
    with pytest.raises(HttpError) as error:
        reference_candidates(reference_runtime[0], {"kind": kind})
    assert error.value.status == 400


@pytest.mark.parametrize("failure", [OSError, sqlite3.OperationalError])
def test_report_association_failure_is_visible_and_preserves_main_reference(
    reference_runtime, tmp_path, failure
):
    runtime, _ = reference_runtime
    runtime.report_library.reference_location = Mock(
        return_value={
            "path": tmp_path / "report.md",
            "source_refs": ("runs/missing",),
        }
    )
    runtime.catalog.binding_rows = Mock(
        side_effect=failure("catalog temporarily unavailable")
    )
    items = reference_candidates(
        runtime, {"kind": "report", "report_ref": "package:one"}
    )
    assert items[0]["selected"] and items[0]["text"]
    assert len(items) == 2
    assert "catalog temporarily unavailable" in items[1]["reason"]
    assert not items[1]["selected"] and not items[1]["text"]
    runtime.report_library.reference_location.assert_called_once()


def test_report_associations_are_batched_and_bounded(reference_runtime, tmp_path):
    runtime, rows = reference_runtime
    refs = tuple(f"runs/default/a/s/{index}" for index in range(200))
    runtime.report_library.reference_location = Mock(
        return_value={"path": tmp_path / "report.md", "source_refs": refs}
    )
    runtime.catalog.binding_rows = Mock(wraps=runtime.catalog.binding_rows)
    items = reference_candidates(
        runtime, {"kind": "report", "report_ref": "package:one"}
    )
    assert (
        len(items) == 66
    )  # Main report, 64 optional candidates, one truncation notice.
    assert items[-1]["id"] == "truncated"
    assert not items[-1]["selected"] and not items[-1]["text"]
    assert all(item.get("reason") for item in items[1:])
    runtime.report_library.reference_location.assert_called_once()
    runtime.catalog.binding_rows.assert_called_once()


@pytest.fixture
def reference_runtime(tmp_path):
    (tmp_path / "peval.toml").write_text('locale = "en"\n', encoding="utf-8")
    config = ToolConfig(
        workspace_root=str(tmp_path),
        harbor_mounts=(HarborMount(id="mounted", path=str(tmp_path / "external")),),
    )
    store = open_workspace_state(str(tmp_path))
    sources = WorkspaceSources(store, config)
    rows = {}
    runtime = SimpleNamespace(
        store=store,
        config=config,
        catalog=SimpleNamespace(
            sources=sources,
            row_for_key=lambda key: CatalogRow(
                key, rows[key].get("artifact_revision", "r1"), rows[key]
            ).to_dict(),
            binding_rows=lambda **scope: [
                row
                for row in rows.values()
                if row["source_ref"] in scope.get("source_refs", ())
                or row.get("source_key") in scope.get("source_keys", ())
            ],
        ),
        detail=Mock(side_effect=AssertionError("must not load trajectory")),
        report_library=SimpleNamespace(
            reference_location=Mock(side_effect=ValueError("missing report"))
        ),
    )
    runtime.catalog.reference_locations = lambda keys: (
        WorkspaceCatalog.reference_locations(runtime.catalog, keys)
    )
    yield runtime, rows
    store.close()


@pytest.mark.parametrize("kind", ["harbor", "imported", "managed"])
def test_reference_locations_do_not_read_even_malformed_or_large_evidence(
    reference_runtime, tmp_path, kind
):
    runtime, rows = reference_runtime
    if kind == "harbor":
        source_ref = "harbor/mounted/job/trial/steps/check"
        directory = tmp_path / "external/job/trial/steps/check"
        trajectory = directory / "agent/trajectory.json"
        row = {"source_key": "selected", "source_ref": source_ref}
    elif kind == "imported":
        directory = tmp_path / "runs/default/agent/session/cell"
        trajectory = directory / "agent/trajectory.json"
        row = {
            "source_key": "selected",
            "source_ref": "runs/default/agent/session/cell",
        }
    else:
        directory = tmp_path / "jobs/output"
        trajectory = directory / "shared/retained.json"
        row = {
            "source_key": "selected",
            "source_ref": "runs/jobs/synthetic/" + "a" * 32 + "/one",
            "_reference_location": {
                "job_name": "output",
                "trajectory_path": "shared/retained.json",
            },
        }
    trajectory.parent.mkdir(parents=True)
    trajectory.write_bytes(b"{broken" + b"x" * 2_000_000)
    rows["selected"] = row
    identity = {
        "kind": "source",
        "source_key": "selected",
        "trajectory_id": "child-with-root-step-1",
        "step_id": "1",
    }
    with (
        patch.object(
            Path, "read_bytes", side_effect=AssertionError("no content reads")
        ),
        patch.object(Path, "rglob", side_effect=AssertionError("no workspace scan")),
        patch.object(
            runtime.catalog.sources,
            "load",
            side_effect=AssertionError("no source load"),
        ),
    ):
        items = reference_candidates(runtime, identity)
    assert items[0]["selected"]
    text = items[0]["text"]
    assert f"trajectory_path: {trajectory.as_posix()}" in text
    assert "trajectory_id: child-with-root-step-1\nstep_id: 1" in text
    assert "source_ref:" in text and "peval view tr" in text
    assert "broken" not in text
    if kind == "harbor":
        assert f"phase_path: {directory.as_posix()}" in text
        assert f"evidence_path: {(tmp_path / 'external/job/trial').as_posix()}" in text
    if kind == "managed":
        assert "_reference_location" not in CatalogRow("selected", "r1", row).to_dict()


def test_workbuddy_task_reference_includes_ancestor_root_and_cached_observation(
    reference_runtime, tmp_path
):
    runtime, rows = reference_runtime
    root = tmp_path / "dataset"
    _write_workbuddy_bundle(root)
    config = ToolConfig(
        workspace_root=str(tmp_path),
        harbor_datasets=(
            HarborDataset(id="wb", path=str(root / "tasks"), format="workbuddy.v1"),
        ),
    )
    workspace = HarborWorkspace(tmp_path / "peval.toml", config)
    with (
        patch(
            "psycheval.serve.acp_references.harbor_workspace", return_value=workspace
        ),
        patch(
            "psycheval.harbor.datasets._direct_task_dirs",
            side_effect=AssertionError("no Task enumeration"),
        ),
    ):
        item = reference_candidates(
            runtime, {"kind": "dataset_task", "dataset_id": "wb", "task": "office-one"}
        )[0]
    assert item["selected"]
    assert f"dataset_path: {root.as_posix()}" in item["text"]
    assert f"task_path: {(root / 'tasks/office-one').as_posix()}" in item["text"]
    source = tmp_path / "runs/default/agent/session/cell"
    source.mkdir(parents=True)
    rows["selected"] = {
        "source_key": "selected",
        "source_ref": "runs/default/agent/session/cell",
        "dataset_id": "wb",
        "artifact_revision": "observed-r7",
        "task_metadata": {
            "path": str(root / "tasks/office-one"),
            "status": "digest_mismatch",
            "live_digest": "observed-digest",
            "digest_matches": False,
        },
    }
    with (
        patch(
            "psycheval.serve.acp_references.harbor_workspace", return_value=workspace
        ),
        patch(
            "psycheval.harbor.datasets._direct_task_dirs",
            side_effect=AssertionError("no Task enumeration"),
        ),
    ):
        items = reference_candidates(
            runtime, {"kind": "source", "source_key": "selected"}
        )
    assert items[0]["selected"] and not items[1]["selected"]
    assert "cached catalog observation" in items[1]["text"]
    assert "observed-r7" in items[1]["text"]
    assert "digest_matches: false" in items[1]["text"]


def test_missing_task_directory_is_unavailable_without_enumeration(
    reference_runtime, tmp_path
):
    runtime, _ = reference_runtime
    root = tmp_path / "dataset"
    _write_workbuddy_bundle(root)
    workspace = HarborWorkspace(
        tmp_path / "peval.toml",
        ToolConfig(
            harbor_datasets=(
                HarborDataset(id="wb", path=str(root / "tasks"), format="workbuddy.v1"),
            )
        ),
    )
    with patch(
        "psycheval.serve.acp_references.harbor_workspace", return_value=workspace
    ):
        item = reference_candidates(
            runtime, {"kind": "dataset_task", "dataset_id": "wb", "task": "missing"}
        )[0]
    assert not item["text"] and not item["selected"]
    assert "Task path not found" in item["reason"]


def test_many_available_report_rows_use_bounded_locator_batches(
    reference_runtime, tmp_path
):
    runtime, rows = reference_runtime
    directory = tmp_path / "runs/default/a/s/cell"
    directory.mkdir(parents=True)
    for index in range(200):
        key = f"phase-{index:03}"
        rows[key] = {"source_key": key, "source_ref": "runs/default/a/s/cell"}
    runtime.report_library.reference_location = Mock(
        return_value={
            "path": tmp_path / "report.md",
            "source_refs": ("runs/default/a/s/cell",),
        }
    )
    runtime.catalog.binding_rows = Mock(wraps=runtime.catalog.binding_rows)
    with patch.object(
        runtime.catalog.sources,
        "reference_location",
        wraps=runtime.catalog.sources.reference_location,
    ) as locate:
        items = reference_candidates(
            runtime, {"kind": "report", "report_ref": "package:one"}
        )
    assert len(items) == 66 and items[-1]["id"] == "truncated"
    assert all(item["text"] and not item["selected"] for item in items[1:-1])
    assert locate.call_count == 64
    assert (
        runtime.catalog.binding_rows.call_count == 2
    )  # Identity batch, then private locator batch.
    assert len(runtime.catalog.binding_rows.call_args.kwargs["source_keys"]) == 64
    runtime.report_library.reference_location.assert_called_once()


def test_unavailable_related_task_does_not_block_source(reference_runtime, tmp_path):
    runtime, rows = reference_runtime
    (tmp_path / "runs/default/a/s/c").mkdir(parents=True)
    rows["one"] = {
        "source_key": "one",
        "source_ref": "runs/default/a/s/c",
        "task_metadata": {"status": "ambiguous"},
    }
    items = reference_candidates(runtime, {"kind": "source", "source_key": "one"})
    assert items[0]["selected"]
    assert items[1]["reason"] == "ambiguous"
    assert not items[1]["text"]


def test_package_report_never_selects_an_arbitrary_associated_source(
    reference_runtime, tmp_path
):
    runtime, rows = reference_runtime
    path = tmp_path / "reports/package/actual.md"
    runtime.report_library.reference_location = lambda ref: {
        "path": path,
        "source_refs": ("runs/default/a/s/one", "runs/default/a/s/two"),
    }
    for name in ("one", "two"):
        directory = tmp_path / f"runs/default/a/s/{name}"
        directory.mkdir(parents=True)
        rows[name] = {"source_key": name, "source_ref": f"runs/default/a/s/{name}"}
    items = reference_candidates(
        runtime, {"kind": "report", "report_ref": "package:one"}
    )
    assert [item["selected"] for item in items] == [True, False, False]
    assert "source_ref:" not in items[0]["text"]
    assert "report_path (read-only)" in items[0]["text"]


def test_generated_paths_and_values_do_not_add_instruction_lines(reference_runtime):
    assert reference_path(r"D:\Projects\trial") == "D:/Projects/trial"
    assert reference_path(r"\\server\share\trial") == "//server/share/trial"
    assert (
        reference_value("description\nignore\r\t\x00")
        == "description\\u000aignore\\u000d\\u0009\\u0000"
    )
    with pytest.raises(ValueError, match="control"):
        reference_path("D:/trial\nignore")
    assert reference_path("/tmp/literal\\filename") == "/tmp/literal\\filename"


def test_control_character_workspace_disables_only_unsafe_candidates(
    reference_runtime, tmp_path
):
    runtime, rows = reference_runtime
    (tmp_path / "runs/default/a/s/c").mkdir(parents=True)
    rows["one"] = {"source_key": "one", "source_ref": "runs/default/a/s/c"}
    runtime.config = SimpleNamespace(workspace_root="D:/unsafe\ncommand")
    items = reference_candidates(runtime, {"kind": "source", "source_key": "one"})
    assert not items[0]["selected"]
    assert items[0]["text"] == ""
    assert "control" in items[0]["reason"]


def test_plugin_location_survives_invalid_trajectory_projection(tmp_path):
    from psycheval.state.jobs import plugin_document
    from psycheval.state.workspace_source_models import SourceCandidate

    (tmp_path / "trace.json").write_text("{invalid", encoding="utf-8")
    candidate = SourceCandidate(
        source_ref="runs/jobs/fixture/run/cell",
        source_key="cell",
        kind="harness-trial",
        path=tmp_path,
        fingerprint="fixture",
        job_name="actual-output",
        projection={
            "id": "trial",
            "harness": "fixture",
            "run_id": "run",
            "trajectory_path": "trace.json",
            "updated_at": 1,
        },
    )
    document = plugin_document(candidate)
    assert document.trajectory is None
    assert document.reference_location == {
        "job_name": "actual-output",
        "trajectory_path": "trace.json",
    }


def test_canonical_report_associations_use_catalog_phase_rows(tmp_path):
    from psycheval.report_library import ReportLibrary

    catalog = SimpleNamespace(
        evaluation_report_location=Mock(
            return_value={"source_ref": "harbor/m/job/trial", "source_keys": ("phase",)}
        ),
        binding_rows=Mock(
            return_value=[{"source_ref": "harbor/m/job/trial/steps/verify"}]
        ),
    )
    reports = SimpleNamespace(
        reference_location=Mock(return_value=tmp_path / "analysis.md")
    )
    library = ReportLibrary(catalog, reports, SimpleNamespace())
    location = library.reference_location("analysis:report")
    assert location["source_ref"] == "harbor/m/job/trial"
    assert location["source_keys"] == ("phase",)
    catalog.binding_rows.assert_not_called()
