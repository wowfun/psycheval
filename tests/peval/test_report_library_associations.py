import http.client
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from psycheval.config import HarborDataset, HarborMount, ToolConfig
from psycheval.report_targets import ReportTargets
from psycheval.serve.api_support import acp_context_items
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import open_workspace_state
from psycheval.state.catalog import replace_evaluation_report_projection
from tests.peval.cli_inputs_support import write_trial_cell_artifacts
from tests.peval.serve_state_support import (
    LocalHTTPServer,
    make_handler,
    peval_workspace,
    request_bytes,
    request_json,
)


@contextmanager
def library_at(tmp_path):
    root = peval_workspace(tmp_path)
    (root / "dataset").mkdir()
    cell = root / "runs/default/agent/session/trial"
    write_trial_cell_artifacts(cell, session_id="session", trial_key="trial")
    (cell / "analysis.md").write_text("# Canonical\n", encoding="utf-8")
    config = ToolConfig(
        workspace_root=str(root),
        harbor_datasets=(HarborDataset(id="empty", path=str(root / "dataset")),),
    )
    store = open_workspace_state(str(root))
    runtime = ServeRuntime(store, config)
    try:
        yield runtime
    finally:
        runtime.close()
        store.close()


def save(runtime, ref, bindings):
    state = runtime.report_library.validate_bindings(bindings, report_ref=ref)
    runtime.workspace_reports.replace_bindings(ref, **state)
    return runtime.report_library.metadata(ref)


def test_independent_import_mixed_bindings_clear_and_legacy_state(tmp_path):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        path = tmp_path / "independent.md"
        path.write_text("# private body needle", encoding="utf-8")
        report_id = runtime.workspace_reports.import_file(path, [])
        ref = "package:" + report_id
        assert library.metadata(ref)["associations"] == []
        source = library.targets(kind="session")["items"][0]
        dataset = library.targets(kind="dataset")["items"][0]
        assert dataset["key"] == "empty"
        updated = save(runtime, ref, [source, dataset])
        assert len(updated["bindings"]) == 2
        assert runtime.workspace_report_catalog()[0]["source_keys"] == [source["key"]]
        save(runtime, ref, [dataset])
        assert runtime.workspace_report_catalog()[0]["source_keys"] == []
        assert runtime.workspace_reports.bound_source_refs() == set()
        assert library.query(datasets=["empty"])["total"] == 1
        assert library.query(search="private body needle")["total"] == 0
        save(runtime, ref, [])
        state_path = tmp_path / "reports" / report_id / "state.json"
        legacy = state_path.read_bytes()
        assert library.metadata(ref)["bindings"] == []
        assert state_path.read_bytes() == legacy
        assert library.query(kinds=["unassociated"])["total"] == 1


def test_canonical_associations_do_not_change_body_or_original_source(tmp_path):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        original = library.query()["items"][0]
        ref = original["report_ref"]
        before = library.read(ref).content
        result = save(runtime, ref, [{"kind": "dataset", "key": "empty"}])
        assert library.read(ref).content == before
        assert result["source_keys"] == original["source_keys"]
        assert {a["origins"][0] for a in result["associations"]} == {"manual", "source"}
        association_path = next((tmp_path / "reports/.associations").glob("*.json"))
        retained = association_path.read_bytes()
        with patch.object(runtime.catalog, "evaluation_report_rows", return_value=[]):
            assert library.query()["items"] == []
            assert association_path.read_bytes() == retained
        assert library.metadata(ref)["bindings"] == result["bindings"]
        with pytest.raises(ValueError, match="cannot be edited"):
            save(runtime, ref, [{"kind": "session", "key": original["source_keys"][0]}])
        save(runtime, ref, [])
        assert library.metadata(ref)["associations"] == original["associations"]
        assert list((tmp_path / "reports/.associations").glob("*.json"))


@pytest.mark.parametrize(
    "content",
    ["{broken", '{"source_refs":[],"dataset_ids":[" "]}', '{"source_refs":["."]}'],
)
def test_corrupt_canonical_associations_are_isolated_and_cannot_be_overwritten(
    tmp_path, content
):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        canonical = library.query()["items"][0]
        ref = canonical["report_ref"]
        save(runtime, ref, [{"kind": "dataset", "key": "empty"}])
        association_path = next((tmp_path / "reports/.associations").glob("*.json"))
        association_path.write_text(content, encoding="utf-8")
        path = tmp_path / "good.md"
        path.write_text("# Good", encoding="utf-8")
        report_id = runtime.workspace_reports.import_file(path, [])
        assert library.query()["total"] == 2
        metadata = library.metadata(ref)
        assert metadata["associations_available"] is False
        assert metadata["source_keys"] == canonical["source_keys"]
        assert str(tmp_path) not in json.dumps(metadata)
        assert library.read(ref).content == b"# Canonical\n"
        save(runtime, "package:" + report_id, [{"kind": "dataset", "key": "empty"}])
        with pytest.raises(ValueError):
            save(runtime, ref, [])
        assert association_path.read_text(encoding="utf-8") == content


@pytest.mark.parametrize("field", ["dataset_ids", "job_refs"])
@pytest.mark.parametrize("value", [[" "], [None], "not-an-array"])
def test_invalid_import_associations_never_publish_a_package(tmp_path, field, value):
    with library_at(tmp_path) as runtime:
        path = tmp_path / "bad.md"
        path.write_text("# Report", encoding="utf-8")
        with pytest.raises(ValueError):
            runtime.workspace_reports.import_file(path, [], **{field: value})
        assert runtime.workspace_reports.metadata() == []
        assert not list((tmp_path / "reports").glob("*/state.json"))
        report_id = runtime.workspace_reports.import_file(path, [])
        state_path = tmp_path / "reports" / report_id / "state.json"
        before = state_path.read_bytes()
        bindings = {"source_refs": [], "dataset_ids": [], "job_refs": [], field: value}
        with pytest.raises(ValueError):
            runtime.workspace_reports.replace_bindings(
                "package:" + report_id, **bindings
            )
        assert state_path.read_bytes() == before


def test_report_query_rejects_unknown_association_kinds(tmp_path):
    with library_at(tmp_path) as runtime:
        with pytest.raises(ValueError, match="association kind"):
            runtime.report_library.query(kinds=["dataset", "bogus"])


def test_unified_metadata_only_query_filters_before_pagination(tmp_path):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        canonical = library.query()["items"][0]
        save(runtime, canonical["report_ref"], [{"kind": "dataset", "key": "empty"}])
        for name in ("first.md", "second.html"):
            path = tmp_path / name
            path.write_text("body", encoding="utf-8")
            runtime.workspace_reports.import_file(path, [], dataset_ids=["empty"])
        with (
            patch.object(
                runtime.evaluation_reports,
                "read",
                side_effect=AssertionError("body read"),
            ),
            patch.object(
                runtime.workspace_reports,
                "_read_content",
                side_effect=AssertionError("body read"),
            ),
        ):
            pages = [library.query(page=page, page_size=1) for page in range(1, 4)]
            assert all(page["total"] == 3 for page in pages)
            assert len({page["items"][0]["report_ref"] for page in pages}) == 3
            assert {page["items"][0]["origin"] for page in pages} == {
                "imported",
                "evaluation",
            }
            assert (
                library.query(
                    search="empty",
                    datasets=["empty"],
                    kinds=["dataset"],
                    page_size=1,
                )["total"]
                == 3
            )
            assert library.query(datasets=["empty"], kinds=["session"])["total"] == 1
            assert library.query(datasets=["empty", "other"])["total"] == 3
            last = library.query(page=99, page_size=1)
            assert (last["page"], last["total"], len(last["items"])) == (3, 3, 1)
            empty = library.query(page=99, search="no such report")
            assert (empty["page"], empty["items"]) == (1, [])


def test_report_query_retains_committed_rows_during_catalog_reconciliation(tmp_path):
    with library_at(tmp_path) as runtime:
        before = runtime.report_library.query()
        assert before["total"] == 1
        entered, release = threading.Event(), threading.Event()

        def blocked_projection(connection):
            connection.execute("DELETE FROM evaluation_reports")
            entered.set()
            assert release.wait(5)
            replace_evaluation_report_projection(connection)

        with ThreadPoolExecutor(max_workers=1) as executor:
            with patch(
                "psycheval.state.catalog.replace_evaluation_report_projection",
                side_effect=blocked_projection,
            ):
                rebuilding = executor.submit(runtime.catalog.reconcile)
                try:
                    assert entered.wait(5)
                    assert runtime.catalog.checking
                    assert runtime.report_library.query() == before
                finally:
                    release.set()
                rebuilding.result(timeout=5)
        assert runtime.report_library.query() == before


def test_missing_bindings_remain_removable_but_cannot_be_added(tmp_path):
    with library_at(tmp_path) as runtime:
        path = tmp_path / "import.md"
        path.write_text("report", encoding="utf-8")
        source = runtime.report_library.targets(kind="session")["items"][0]
        report_id = runtime.workspace_reports.import_file(
            path, [source["key"]], dataset_ids=["deleted"], job_refs=["managed:missing"]
        )
        ref = "package:" + report_id
        with patch.object(runtime.catalog, "binding_rows", return_value=[]):
            old = runtime.report_library.metadata(ref)
            assert len(old["bindings"]) == 3
            assert all(not item["available"] for item in old["bindings"])
            save(runtime, ref, old["bindings"])
            save(runtime, ref, old["bindings"][1:])
            with pytest.raises(ValueError, match="unavailable"):
                save(runtime, ref, old["bindings"])
            save(runtime, ref, [])


def test_jobs_deduplicate_by_actual_run_and_keep_same_names_separate(tmp_path):
    (tmp_path / "elsewhere/same").mkdir(parents=True)
    mounts = [
        HarborMount(id="managed", path=str(tmp_path / "jobs")),
        HarborMount(id="external", path=str(tmp_path / "elsewhere")),
    ]
    config = ToolConfig(
        workspace_root=str(tmp_path),
        harbor_mounts=tuple(mounts),
        harbor_datasets=(HarborDataset(id="data", path=str(tmp_path / "data")),),
    )
    rows = [
        {
            "source_key": mount.id,
            "source_ref": f"harbor/{mount.id}/same/trial",
            "dataset_id": "data",
            "readable": True,
        }
        for mount in mounts
    ]
    states = [
        (tmp_path, {"id": "a" * 32, "job_name": "same", "harness": "harbor"}),
        (tmp_path, {"id": "b" * 32, "job_name": "no-trials", "harness": "harbor"}),
    ]
    with patch("psycheval.report_targets.records", return_value=states):
        targets = ReportTargets(tmp_path, config, rows)
    jobs = [target for target in targets.items.values() if target["kind"] == "job"]
    assert len(jobs) == 3
    bindings = targets.bindings(
        {
            "source_refs": [],
            "dataset_ids": ["data"],
            "job_refs": ["harbor:managed/same", "managed:" + "a" * 32],
        }
    )
    associations = targets.associations(["managed"], bindings)
    dataset = next(item for item in associations if item["kind"] == "dataset")
    job = next(item for item in associations if item["kind"] == "job")
    assert dataset["origins"] == ["manual", "inherited"]
    assert job["origins"] == ["manual", "inherited"]
    assert job["key"] == "managed:" + "a" * 32
    assert targets.resolve("job", "harbor:external/same")["key"] != job["key"]


def test_managed_run_without_trials_is_resolved_from_retained_jobs_record(tmp_path):
    with library_at(tmp_path) as runtime:
        run_id = "b" * 32
        path = tmp_path / ".peval/jobs" / run_id
        path.mkdir(parents=True)
        (path / "state.json").write_text(
            json.dumps(
                {
                    "id": run_id,
                    "harness": "harbor",
                    "state": "completed",
                    "job_name": "2026-09-18__10-00-00",
                    "submitted_at": "2026-09-18T10:00:00Z",
                }
            ),
            encoding="utf-8",
        )
        jobs = runtime.report_library.targets(kind="job")["items"]
        assert [job["key"] for job in jobs] == ["managed:" + run_id]
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        save(runtime, ref, jobs)
        assert runtime.report_library.query(jobs=["managed:" + run_id])["total"] == 1
        assert runtime.report_library.query(jobs=["managed:missing"])["total"] == 0


def test_http_typed_associations_and_copilot_read_both_origins(tmp_path):
    with library_at(tmp_path) as runtime:
        source = runtime.report_library.targets(kind="session")["items"][0]
        path = tmp_path / "import.md"
        path.write_text("# Imported context\n", encoding="utf-8")
        server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_port
        origin = f"http://127.0.0.1:{port}"
        try:

            def send(method, url, body):
                return request_json(port, method, url, body, origin=origin)

            status, headers, imported = send(
                "POST", "/api/reports", {"path": str(path)}
            )
            assert status == 201
            read_status, _, read_body = request_bytes(port, headers["location"])
            assert read_status == 200
            assert json.loads(read_body)["report_ref"] == imported["report_ref"]
            assert imported["bindings"] == []
            ref = imported["report_ref"]
            bindings = [
                {"kind": "session", "key": source["key"]},
                {"kind": "dataset", "key": "empty"},
            ]
            status, _, updated = send(
                "PUT", f"/api/report-library/{ref}/bindings", {"bindings": bindings}
            )
            assert status == 200
            assert len(updated["bindings"]) == 2
            canonical = next(
                item
                for item in runtime.report_library.query()["items"]
                if item["report_ref"].startswith("analysis:")
            )
            status, _, _ = send(
                "PUT",
                f"/api/report-library/{canonical['report_ref']}/bindings",
                {"bindings": bindings},
            )
            assert status == 400
            assert (
                send(
                    "PUT",
                    "/api/report-library/analysis:missing/bindings",
                    {"bindings": []},
                )[0]
                == 404
            )
            assert (
                send(
                    "PUT",
                    f"/api/reports/{imported['report_id']}/bindings",
                    {"bindings": []},
                )[0]
                == 404
            )
            assert request_bytes(port, "/api/evaluation-reports")[0] == 404
            assert request_bytes(port, "/api/report-library?kind=bogus")[0] == 400
            assert request_bytes(port, "/api/report-library?page=bogus")[0] == 422
            assert (
                request_bytes(
                    port,
                    "/api/report-library/targets?kind=dataset&search=empty&page_size=1",
                )[0]
                == 200
            )
            assert (
                send(
                    "PUT",
                    f"/api/report-library/{ref}/bindings",
                    {"bindings": [{"kind": "job", "key": "missing"}]},
                )[0]
                == 400
            )
            assert (
                runtime.report_library.metadata(ref)["bindings"] == updated["bindings"]
            )
            for report_ref, expected in [
                (ref, "Imported context"),
                (canonical["report_ref"], "Canonical"),
            ]:
                context = acp_context_items(
                    runtime.store,
                    runtime,
                    [{"kind": "report", "report_ref": report_ref}],
                    embedded_context=True,
                )[0]
                payload = json.loads(context["content"][0]["resource"]["text"])
                assert expected in payload["value"]["evidence"]["content"]
                assert payload["reference"]["report_ref"] == report_ref
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            try:
                connection.request(
                    "DELETE",
                    f"/api/reports/{imported['report_id']}",
                    headers={"Origin": origin},
                )
                deleted = connection.getresponse()
                assert deleted.status == 204
                assert deleted.read() == b""
            finally:
                connection.close()
            assert request_bytes(port, f"/api/report-library/{ref}")[0] == 404
            assert not (tmp_path / "reports" / imported["report_id"]).exists()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
