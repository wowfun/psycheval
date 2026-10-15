import http.client
import json
import os
import threading
from contextlib import contextmanager, nullcontext
from functools import partial
from unittest.mock import patch

import pytest

from psycheval.report_library import ReportNotFound
from psycheval.serve.access import ServeAccess
from psycheval.serve.api_support import acp_context_items
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import CatalogQuery, open_workspace_state
from psycheval.workspace_reports import (
    ReportDeletionCommittedError,
    WorkspaceReportLibrary,
    WorkspaceReportNotFound,
)
from tests.peval.cli_inputs_support import write_trial_cell_artifacts
from tests.peval.serve_state_support import LocalHTTPServer, make_handler
from tests.peval.test_report_library_associations import library_at, save


@pytest.mark.parametrize("origin", ["imported", "evaluation"])
def test_management_snapshot_keeps_state_and_timestamp_from_the_same_file(
    tmp_path, origin
):
    with library_at(tmp_path) as runtime:
        library = runtime.workspace_reports
        if origin == "imported":
            ref, _ = imported_report(runtime, tmp_path)
            path = library._package_dir(ref.removeprefix("package:")) / "state.json"
        else:
            ref = next(
                item["report_ref"]
                for item in runtime.report_library.query()["items"]
                if item["origin"] == "evaluation"
            )
            library.set_archived(ref, True)
            path = library._association_path(ref)
        before = path.stat().st_mtime_ns
        replacement = tmp_path / "replacement-state.json"
        replacement.write_text('{"source_refs":[],"archived":true}', encoding="utf-8")
        os.utime(replacement, ns=(before + 10_000_000_000,) * 2)
        # Replace immediately after parsing: the snapshot must not acquire the
        # timestamp of the next atomic publication.
        validate = library._validate_state

        def replaced(payload, label):
            state = validate(payload, label)
            replacement.replace(path)
            return state

        with patch.object(library, "_validate_state", side_effect=replaced):
            state, updated_at_ms = library.management_state(ref)
        assert state.archived is (origin == "evaluation")
        assert updated_at_ms == before // 1_000_000


@pytest.mark.parametrize("target", ["body", "state"])
def test_report_read_rejects_file_changed_to_symlink_before_open(
    tmp_path, monkeypatch, target
):
    from pathlib import Path

    with library_at(tmp_path) as runtime:
        ref, _ = imported_report(runtime, tmp_path)
        library = runtime.workspace_reports
        package = library._package_dir(ref.removeprefix("package:"))
        path = package / ("import.md" if target == "body" else "state.json")
        outside = tmp_path / ("outside.md" if target == "body" else "outside.json")
        outside.write_text(
            "private body"
            if target == "body"
            else '{"source_refs":[],"archived":true}',
            encoding="utf-8",
        )
        probe = tmp_path / "symlink-probe"
        try:
            probe.symlink_to(outside)
            probe.unlink()
        except OSError:
            pytest.skip("symlink creation unavailable")
        original = Path.is_file
        swapped = False

        def checked(candidate):
            nonlocal swapped
            result = original(candidate)
            if candidate == path and not swapped:
                path.unlink()
                path.symlink_to(outside)
                swapped = True
            return result

        monkeypatch.setattr(Path, "is_file", checked)
        if target == "body":
            # resolve() is a second preflight; swap after it instead.
            monkeypatch.setattr(Path, "is_file", original)
            metadata = library._read_package_metadata

            def metadata_then_swap(report_id):
                result = metadata(report_id)
                path.unlink()
                path.symlink_to(outside)
                return result

            monkeypatch.setattr(library, "_read_package_metadata", metadata_then_swap)
            with pytest.raises((OSError, ValueError)):
                library.read(ref.removeprefix("package:"))
        else:
            report = library.metadata(ref.removeprefix("package:"))[0]
            assert not report.associations_available
            assert not report.archived


def imported_report(runtime, root):
    path = root / "import.md"
    path.write_bytes(b"# Imported\n")
    source = runtime.report_library.targets(kind="session")["items"][0]
    report_id = runtime.workspace_reports.import_file(path, [source["key"]])
    return "package:" + report_id, path


def test_missing_imported_metadata_returns_domain_not_found(tmp_path):
    with library_at(tmp_path) as runtime:
        ref, _ = imported_report(runtime, tmp_path)
        report_id = ref.removeprefix("package:")
        runtime.workspace_reports.delete(report_id)
        with pytest.raises(WorkspaceReportNotFound):
            runtime.workspace_reports.metadata(report_id)


@pytest.mark.parametrize("damage", ["corrupt", "missing"])
def test_canonical_report_can_be_deleted_after_source_evidence_becomes_unreadable(
    tmp_path, damage
):
    with library_at(tmp_path) as runtime:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        row = runtime.catalog.evaluation_report_location(ref)
        cell = tmp_path / row["source_ref"]
        for name in ("agent/trajectory.json", "agent/trajectory_meta.json"):
            path = cell / name
            if damage == "missing":
                path.unlink()
            else:
                path.write_text("{corrupt", encoding="utf-8")
        runtime.catalog.reconcile()
        assert runtime.report_library.metadata(ref)["report_ref"] == ref
        assert runtime.report_library.read(ref).content
        draft = tmp_path / "replacement.md"
        draft.write_text("# Replacement", encoding="utf-8")
        with pytest.raises(ValueError):
            runtime.evaluation_reports.publish(row["source_ref"], draft)
        runtime.report_library.delete(ref)
        assert not (cell / "analysis.md").exists()
        assert runtime.report_library.query(state="all")["total"] == 0


def test_committed_delete_failure_advances_catalog_generation(tmp_path):
    with library_at(tmp_path) as runtime:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        before = runtime.catalog.query(CatalogQuery()).generation
        with patch.object(
            WorkspaceReportLibrary,
            "clear_management_state",
            side_effect=OSError("fixture cleanup failed"),
        ):
            with pytest.raises(ReportDeletionCommittedError):
                runtime.report_library.delete(ref)
        after = runtime.catalog.query(CatalogQuery()).generation
        assert after > before
        assert runtime.catalog.evaluation_report_rows(ref) == []


@pytest.mark.parametrize("operation", ["delete", "publish"])
def test_management_cleanup_does_not_hold_catalog_writer(tmp_path, operation):
    with library_at(tmp_path) as runtime:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        source = runtime.catalog.evaluation_report_location(ref)["source_ref"]
        cleanup = WorkspaceReportLibrary.clear_management_state

        def checked(library, report_ref, **kwargs):
            # A distinct catalog must be able to write while this source waits
            # for its report-specific management lock.
            runtime.catalog.mutate(lambda: None)
            return cleanup(library, report_ref, **kwargs)

        if operation == "publish":
            runtime.report_library.delete(ref)
            draft = tmp_path / "draft.md"
            draft.write_text("# Fresh", encoding="utf-8")
        with patch.object(WorkspaceReportLibrary, "clear_management_state", checked):
            if operation == "delete":
                runtime.report_library.delete(ref)
            else:
                runtime.evaluation_reports.publish(source, draft)


def test_degraded_harbor_report_presence_tracks_addition_replacement_and_deletion(
    tmp_path,
):
    from psycheval.config import HarborMount
    from tests.peval.test_harbor_evidence import write_evidence_trial

    with library_at(tmp_path) as runtime:
        jobs = tmp_path / "external-jobs"
        trial = jobs / "run/trial"
        write_evidence_trial(trial)
        (trial / "config.json").write_text("{broken", encoding="utf-8")
        runtime.set_config(
            runtime.config.validated_update(
                harbor_mounts=(HarborMount(id="external", path=str(jobs)),)
            )
        )
        runtime.catalog.reconcile()
        original = runtime.report_library.query(state="all")["total"]
        body = trial / "analysis.md"
        body.write_text("# Present", encoding="utf-8")
        runtime.catalog.reconcile()
        items = runtime.report_library.query(state="all")["items"]
        assert len(items) == original + 1
        report = next(
            item
            for item in items
            if runtime.catalog.evaluation_report_location(item["report_ref"])[
                "source_ref"
            ].startswith("harbor/")
        )
        ref = report["report_ref"]
        body.write_text("   ", encoding="utf-8")
        runtime.catalog.reconcile()
        assert runtime.catalog.evaluation_report_rows(ref) == []
        body.write_text("# Restored", encoding="utf-8")
        runtime.catalog.reconcile()
        assert runtime.report_library.read(ref).content == b"# Restored"
        runtime.report_library.delete(ref)
        runtime.catalog.reconcile()
        assert not body.exists()
        assert runtime.catalog.evaluation_report_rows(ref) == []
        assert runtime.report_library.query(state="all")["total"] == original


@pytest.mark.parametrize("damage", ["oversized", "missing", "extra", "non_utf8"])
def test_damaged_imported_report_remains_discoverable_and_deletable(
    tmp_path, monkeypatch, damage
):
    from psycheval import workspace_reports

    with library_at(tmp_path) as runtime:
        ref, original = imported_report(runtime, tmp_path)
        package = runtime.workspace_reports._package_dir(ref.removeprefix("package:"))
        body = package / original.name
        if damage == "oversized":
            monkeypatch.setattr(workspace_reports, "REPORT_MAX_BYTES", 16)
            body.write_bytes(b"x" * 17)
        elif damage == "missing":
            body.unlink()
        elif damage == "extra":
            (package / "unexpected.txt").write_bytes(b"extra")
        else:
            body.write_bytes(b"\xff")
        assert ref in {
            item["report_ref"]
            for item in runtime.report_library.query(state="all")["items"]
        }
        assert runtime.report_library.metadata(ref)["report_ref"] == ref
        with pytest.raises(ReportNotFound):
            runtime.report_library.read(ref)
        runtime.report_library.delete(ref)
        assert not package.exists()


def test_management_file_limit_keeps_body_readable_and_rejects_oversized_writes(
    tmp_path, monkeypatch
):
    from psycheval import workspace_reports

    with library_at(tmp_path) as runtime:
        ref, original = imported_report(runtime, tmp_path)
        library = runtime.workspace_reports
        path = library._package_dir(ref.removeprefix("package:")) / "state.json"
        before = path.read_bytes()
        monkeypatch.setattr(workspace_reports, "REPORT_STATE_MAX_BYTES", 8)
        report = library.metadata(ref.removeprefix("package:"))[0]
        assert not report.associations_available
        assert library.read(report.report_id).content == original.read_bytes()
        with pytest.raises(ValueError, match="byte limit"):
            library._write_state(tmp_path / "new-state.json", [])
        assert path.read_bytes() == before
        assert not (tmp_path / "new-state.json").exists()


@pytest.mark.parametrize("target", ["body", "state"])
def test_report_file_replacement_during_open_is_rejected(tmp_path, monkeypatch, target):
    from psycheval import workspace_reports

    with library_at(tmp_path) as runtime:
        ref, _ = imported_report(runtime, tmp_path)
        library = runtime.workspace_reports
        package = library._package_dir(ref.removeprefix("package:"))
        path = package / ("import.md" if target == "body" else "state.json")
        replacement = tmp_path / "replacement"
        replacement.write_text(
            "private body"
            if target == "body"
            else '{"source_refs":[],"archived":true}',
            encoding="utf-8",
        )
        open_descriptor = workspace_reports.open_read_descriptor

        def changed(candidate):
            if candidate == path:
                replacement.replace(path)
            return open_descriptor(candidate)

        monkeypatch.setattr(workspace_reports, "open_read_descriptor", changed)
        if target == "body":
            with pytest.raises(ValueError, match="changed while opening"):
                library.read(ref.removeprefix("package:"))
        else:
            report = library.metadata(ref.removeprefix("package:"))[0]
            assert not report.associations_available
            assert not report.archived


@pytest.mark.parametrize("mutation", ["archive", "bindings"])
def test_imported_report_stays_readable_during_state_replacement(tmp_path, mutation):
    with library_at(tmp_path) as runtime:
        ref, original = imported_report(runtime, tmp_path)
        write = runtime.workspace_reports._write_state

        def staged(path, **kwargs):
            write(path, **kwargs)
            assert runtime.report_library.read(ref).content == original.read_bytes()
            assert any(
                item["report_ref"] == ref
                for item in runtime.report_library.query(state="all")["items"]
            )
            assert any(
                item["report_ref"] == ref
                for item in runtime.workspace_reports.catalog(
                    runtime.catalog.binding_rows()
                )
            )

        with patch.object(
            runtime.workspace_reports, "_write_state", side_effect=staged
        ):
            if mutation == "archive":
                runtime.report_library.set_archived(ref, True)
            else:
                save(runtime, ref, [{"kind": "dataset", "key": "empty"}])


@pytest.mark.parametrize("origin", ["evaluation", "imported"])
def test_single_report_management_does_not_enumerate_other_reports(tmp_path, origin):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        ref = library.query()["items"][0]["report_ref"]
        if origin == "imported":
            ref, _ = imported_report(runtime, tmp_path)
        binding_rows = runtime.catalog.binding_rows

        def scoped_binding_rows(**scope):
            assert scope, "single-report reads must not enumerate all source bindings"
            return binding_rows(**scope)

        with (
            patch.object(
                runtime.catalog, "binding_rows", side_effect=scoped_binding_rows
            ),
            patch.object(
                runtime.workspace_reports,
                "metadata",
                wraps=runtime.workspace_reports.metadata,
            ) as packages,
            patch.object(
                runtime.catalog,
                "evaluation_report_rows",
                wraps=runtime.catalog.evaluation_report_rows,
            ) as canonical,
        ):
            assert library.metadata(ref)["report_ref"] == ref
            assert library.set_archived(ref, True)["archived"]
            assert library.read(ref).content
        assert all(
            call.args == (ref.removeprefix("package:"),)
            for call in packages.call_args_list
        )
        assert all(call.args == (ref,) for call in canonical.call_args_list)


@pytest.mark.parametrize("ref", [None, "", False])
def test_metadata_requires_an_explicit_report_reference(tmp_path, ref):
    with library_at(tmp_path) as runtime:
        with pytest.raises(ReportNotFound):
            runtime.report_library.metadata(ref)


def test_archive_revalidates_existence_after_waiting_for_management_lease(tmp_path):
    with library_at(tmp_path) as runtime:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        lease = runtime.workspace_reports._management_state_lease
        deleting = False

        @contextmanager
        def delete_before_lease(report_ref):
            nonlocal deleting
            if not deleting:
                deleting = True
                runtime.report_library.delete(ref)
            with lease(report_ref):
                yield

        with patch.object(
            runtime.workspace_reports,
            "_management_state_lease",
            side_effect=delete_before_lease,
        ):
            with pytest.raises(ReportNotFound):
                runtime.report_library.set_archived(ref, True)
        assert not runtime.workspace_reports._association_path(ref).exists()


def test_concurrent_management_updates_preserve_both_fields(tmp_path):
    with library_at(tmp_path) as runtime:
        ref, _ = imported_report(runtime, tmp_path)
        archiving = threading.Event()
        release = threading.Event()
        binding_done = threading.Event()
        original = runtime.workspace_reports._write_state
        errors = []

        def write(*args, **kwargs):
            if kwargs.get("archived") and not archiving.is_set():
                archiving.set()
                assert release.wait(3)
            return original(*args, **kwargs)

        def archive():
            try:
                runtime.workspace_reports.set_archived(ref, True)
            except Exception as exc:
                errors.append(exc)

        def bind():
            try:
                # A distinct library must share the report's coordination lease.
                WorkspaceReportLibrary(tmp_path, lambda: []).replace_bindings(
                    ref,
                    lambda current: {
                        "source_refs": [],
                        "dataset_ids": ["empty"],
                        "job_refs": [],
                    },
                )
            except Exception as exc:
                errors.append(exc)
            finally:
                binding_done.set()

        with patch.object(runtime.workspace_reports, "_write_state", side_effect=write):
            first = threading.Thread(target=archive)
            second = threading.Thread(target=bind)
            first.start()
            try:
                assert archiving.wait(3)
                second.start()
                binding_done.wait(0.3)
            finally:
                release.set()
                first.join(3)
                if second.ident is not None:
                    second.join(3)
        assert not first.is_alive() and not second.is_alive()
        assert not errors
        state, _ = runtime.workspace_reports.management_state(ref)
        assert state.archived and state.dataset_ids == ("empty",)


@pytest.mark.parametrize("origin", ["evaluation", "imported"])
def test_archival_preserves_body_bindings_and_survives_rebuild_and_restart(
    tmp_path, origin
):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        ref = library.query()["items"][0]["report_ref"]
        if origin == "imported":
            ref, _ = imported_report(runtime, tmp_path)
        original = library.read(ref).content
        save(runtime, ref, [{"kind": "dataset", "key": "empty"}])
        bindings = library.metadata(ref)["bindings"]
        assert library.metadata(ref)["archived"] is False
        archived = library.set_archived(ref, True)
        assert archived["archived"] is True
        assert library.read(ref).content == original
        assert library.query(
            state="archived",
            datasets=["empty"],
            search=archived["title"],
            page=10,
            page_size=1,
        )["items"] == [archived]
        assert ref not in {item["report_ref"] for item in library.query()["items"]}
        assert library.query(state="all")["total"] == 1 + (origin == "imported")
        assert runtime.workspace_report_catalog() == []
        _, updated_at = runtime.workspace_reports.management_state(ref)
        library.set_archived(ref, True)
        assert runtime.workspace_reports.management_state(ref)[1] == updated_at
        context = acp_context_items(
            runtime.store,
            runtime,
            [{"kind": "report", "report_ref": ref}],
            embedded_context=True,
        )
        assert (
            original.decode().strip()
            in json.loads(context[0]["content"][0]["resource"]["text"])["value"][
                "evidence"
            ]["content"]
        )
        save(runtime, ref, [])
        assert library.metadata(ref)["archived"] is True
        runtime.catalog.reconcile()
        second_store = open_workspace_state(str(tmp_path))
        second = ServeRuntime(second_store, runtime.config)
        try:
            assert second.report_library.metadata(ref)["archived"] is True
            assert second.report_library.read(ref).content == original
        finally:
            second.close()
            second_store.close()
        library.set_archived(ref, False)
        assert library.metadata(ref)["archived"] is False
        assert library.query(state="archived")["total"] == 0
        assert library.read(ref).content == original
        assert bindings
        with pytest.raises(ValueError, match="state"):
            library.query(state="invalid")


def test_archived_packages_retain_source_bindings_and_home_restores_them(tmp_path):
    with library_at(tmp_path) as runtime:
        ref, _ = imported_report(runtime, tmp_path)
        before = runtime.workspace_reports.bound_source_refs()
        assert before
        runtime.report_library.set_archived(ref, True)
        assert runtime.workspace_reports.bound_source_refs() == before
        assert runtime.workspace_report_catalog() == []
        assert runtime.report_library.read(ref).content == b"# Imported\n"
        runtime.report_library.set_archived(ref, False)
        assert runtime.workspace_report_catalog()[0]["source_keys"]


@pytest.mark.parametrize("origin", ["evaluation", "imported"])
@pytest.mark.parametrize("content", ["{broken", '{"source_refs":[],"archived":"true"}'])
def test_damaged_management_metadata_keeps_preview_and_allows_explicit_deletion(
    tmp_path, origin, content
):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        ref = library.query()["items"][0]["report_ref"]
        save(runtime, ref, [{"kind": "dataset", "key": "empty"}])
        state = next((tmp_path / "reports/.associations").glob("*.json"))
        original = None
        if origin == "imported":
            ref, original = imported_report(runtime, tmp_path)
            state = tmp_path / "reports" / ref.removeprefix("package:") / "state.json"
        body = library.read(ref).content
        state.write_text(content, encoding="utf-8")
        assert library.metadata(ref)["associations_available"] is False
        assert library.read(ref).content == body
        with pytest.raises(ValueError):
            library.set_archived(ref, True)
        with pytest.raises(ValueError):
            save(runtime, ref, [])
        assert state.read_text(encoding="utf-8") == content
        library.delete(ref)
        with pytest.raises(ReportNotFound):
            library.read(ref)
        assert not state.exists()
        if original:
            assert original.read_bytes() == body
        assert runtime.catalog.binding_rows()


@pytest.mark.parametrize("origin", ["evaluation", "imported"])
def test_corrupt_archival_state_stays_discoverable_until_repaired(tmp_path, origin):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        ref = library.query()["items"][0]["report_ref"]
        if origin == "imported":
            ref, _ = imported_report(runtime, tmp_path)
        library.set_archived(ref, True)
        path = (
            tmp_path / "reports" / ref.removeprefix("package:") / "state.json"
            if origin == "imported"
            else next((tmp_path / "reports/.associations").glob("*.json"))
        )
        retained = path.read_bytes()
        body = library.read(ref).content
        path.write_bytes(b"{broken")
        metadata = library.metadata(ref)
        assert metadata["archived"] is False
        assert metadata["associations_available"] is False
        for state in ("active", "all"):
            assert ref in {
                item["report_ref"] for item in library.query(state=state)["items"]
            }
        assert ref not in {
            item["report_ref"] for item in library.query(state="archived")["items"]
        }
        assert library.read(ref).content == body
        with pytest.raises(ValueError):
            library.set_archived(ref, False)
        assert path.read_bytes() == b"{broken"
        path.write_bytes(retained)
        assert library.metadata(ref)["archived"] is True
        assert ref not in {item["report_ref"] for item in library.query()["items"]}
        assert ref in {
            item["report_ref"] for item in library.query(state="archived")["items"]
        }
        assert library.read(ref).content == body


@pytest.mark.parametrize("malformation", ["extra_file", "oversized_body"])
def test_explicit_delete_removes_invalid_owned_package_only(tmp_path, malformation):
    with library_at(tmp_path) as runtime:
        ref, original = imported_report(runtime, tmp_path)
        package = tmp_path / "reports" / ref.removeprefix("package:")
        if malformation == "extra_file":
            (package / "unexpected.txt").write_bytes(b"retained extra")
        limit = (
            patch("psycheval.workspace_reports.REPORT_MAX_BYTES", 1)
            if malformation == "oversized_body"
            else nullcontext()
        )
        with limit:
            with pytest.raises(ReportNotFound):
                runtime.report_library.read(ref)
            runtime.report_library.delete(ref)
        assert not package.exists()
        assert original.read_bytes() == b"# Imported\n"
        assert runtime.report_library.query()["total"] == 1


def test_delete_clears_canonical_metadata_and_republication_starts_active(tmp_path):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        ref = library.query()["items"][0]["report_ref"]
        source_ref = runtime.catalog.evaluation_report_location(ref)["source_ref"]
        cell = tmp_path / source_ref
        evidence = {
            path.name: path.read_bytes()
            for path in cell.iterdir()
            if path.is_file() and path.name != "analysis.md"
        }
        save(runtime, ref, [{"kind": "dataset", "key": "empty"}])
        library.set_archived(ref, True)
        draft = tmp_path / "draft.md"
        draft.write_bytes(b"# Updated\n")
        runtime.evaluation_reports.publish(source_ref, draft)
        assert library.metadata(ref)["archived"] is True
        library.delete(ref)
        assert library.query(state="all")["total"] == 0
        assert not (cell / "analysis.md").exists()
        for name, content in evidence.items():
            assert (cell / name).read_bytes() == content
        runtime.evaluation_reports.publish(source_ref, draft)
        assert library.metadata(ref)["archived"] is False
        assert library.metadata(ref)["bindings"] == []
        assert library.read(ref).content == draft.read_bytes()


@pytest.mark.parametrize("failure", ["cleanup", "reconcile"])
def test_committed_canonical_deletion_reports_remaining_work(tmp_path, failure):
    with library_at(tmp_path) as runtime:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        save(runtime, ref, [{"kind": "dataset", "key": "empty"}])
        target = (
            (WorkspaceReportLibrary, "clear_management_state")
            if failure == "cleanup"
            else (runtime.catalog, "_reconcile_locked")
        )
        with patch.object(*target, side_effect=RuntimeError("finalization failed")):
            with pytest.raises(ReportDeletionCommittedError) as caught:
                runtime.report_library.delete(ref)
        assert caught.value.metadata_cleared is (failure == "reconcile")
        assert caught.value.catalog_reconciled is (failure == "cleanup")
        assert not (tmp_path / "runs/default/agent/session/trial/analysis.md").exists()
        assert runtime.report_library.query(state="all")["total"] == 0
        runtime.catalog.reconcile()
        assert runtime.report_library.query(state="all")["total"] == 0


def test_deletion_preserves_reconcile_failure_when_cleanup_also_fails(tmp_path):
    with library_at(tmp_path) as runtime:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        with (
            patch.object(
                runtime.catalog,
                "_reconcile_locked",
                side_effect=RuntimeError("reconcile failed"),
            ),
            patch.object(
                WorkspaceReportLibrary,
                "clear_management_state",
                side_effect=RuntimeError("cleanup failed"),
            ),
        ):
            with pytest.raises(ReportDeletionCommittedError) as caught:
                runtime.report_library.delete(ref)
        assert not caught.value.catalog_reconciled
        assert not caught.value.metadata_cleared
        assert str(caught.value.__cause__) == "reconcile failed"
        assert "cleanup failed" in caught.value.__cause__.__notes__[0]
        assert runtime.catalog.evaluation_report_rows(ref) == []


@pytest.mark.parametrize("writer", ["publish", "markdown", "snapshot", "sidecar"])
@pytest.mark.parametrize("deleted", [True, False])
def test_canonical_writers_preserve_existing_state_and_clear_deleted_state(
    tmp_path, writer, deleted
):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        ref = library.query()["items"][0]["report_ref"]
        source_ref = runtime.catalog.evaluation_report_location(ref)["source_ref"]
        save(runtime, ref, [{"kind": "dataset", "key": "empty"}])
        library.set_archived(ref, True)
        bindings = library.metadata(ref)["bindings"]
        if deleted:
            with patch.object(
                WorkspaceReportLibrary,
                "clear_management_state",
                side_effect=RuntimeError("interrupted cleanup"),
            ):
                with pytest.raises(ReportDeletionCommittedError):
                    library.delete(ref)
        assert runtime.workspace_reports.management_state(ref)[0].archived
        draft = tmp_path / "new-report.md"
        draft.write_bytes(b"# Fresh report\n")
        if writer == "publish":
            runtime.evaluation_reports.publish(source_ref, draft)
        elif writer == "markdown":
            from psycheval.analysis.imports import import_analysis_artifacts

            import_analysis_artifacts(
                workspace_root=tmp_path, source_ref=source_ref, input_paths=[str(draft)]
            )
        elif writer == "snapshot":
            runtime.store.materialize_snapshot_annotations(
                {
                    "annotations": {
                        "analysis": [
                            {"trial_key": "trial", "md_report": draft.read_text()}
                        ]
                    }
                },
                {"trial_key": "trial"},
                source_ref,
            )
        else:
            source = tmp_path / "sidecar"
            source.mkdir()
            (source / "analysis.md").write_bytes(draft.read_bytes())
            runtime.store.copy_trial_sidecars(source, source_ref)
        runtime.catalog.reconcile()
        metadata = library.metadata(ref)
        assert metadata["archived"] is (not deleted)
        assert metadata["bindings"] == ([] if deleted else bindings)
        assert library.read(ref).content == draft.read_bytes()
        runtime.catalog.reconcile()
        assert library.metadata(ref)["archived"] is (not deleted)


@pytest.mark.parametrize("held", ["source", "management"])
def test_ingest_report_writer_never_waits_inside_catalog(tmp_path, held):
    from psycheval.evaluation_reports import (
        _evaluation_report_lease,
        evaluation_report_writer,
    )
    from psycheval.file_access import FileLeaseTimeout

    with library_at(tmp_path) as runtime:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        source = runtime.catalog.evaluation_report_location(ref)["source_ref"]
        directory = tmp_path / source
        runtime.report_library.delete(ref)
        lease = (
            _evaluation_report_lease(directory)
            if held == "source"
            else runtime.workspace_reports._management_state_lease(ref)
        )
        # Taking either lease again in this thread cannot wait for its owner.
        with lease, runtime.catalog.workspace_write_guard():
            with pytest.raises(FileLeaseTimeout):
                with evaluation_report_writer(
                    tmp_path, source, directory, blocking=False
                ) as write:
                    write("# Not committed")
        assert not (directory / "analysis.md").exists()


def test_missing_package_state_keeps_preview_but_blocks_edits(tmp_path):
    with library_at(tmp_path) as runtime:
        ref, original = imported_report(runtime, tmp_path)
        state = tmp_path / "reports" / ref.removeprefix("package:") / "state.json"
        state.unlink()
        assert runtime.report_library.read(ref).content == original.read_bytes()
        assert runtime.report_library.metadata(ref)["associations_available"] is False
        with pytest.raises(ValueError):
            runtime.report_library.set_archived(ref, True)
        runtime.report_library.delete(ref)
        assert original.is_file()


def test_failed_body_removal_preserves_report_and_management_state(tmp_path):
    with library_at(tmp_path) as runtime:
        library = runtime.report_library
        ref = library.query()["items"][0]["report_ref"]
        library.set_archived(ref, True)
        before = library.read(ref).content
        path = tmp_path / "runs/default/agent/session/trial/analysis.md"
        with patch.object(
            type(path), "unlink", side_effect=PermissionError("body is locked")
        ):
            with pytest.raises(PermissionError):
                library.delete(ref)
        assert library.read(ref).content == before
        assert library.metadata(ref)["archived"] is True


def test_imported_cleanup_failure_commits_removal_and_invalidates_bindings(tmp_path):
    with library_at(tmp_path) as runtime:
        ref, original = imported_report(runtime, tmp_path)
        assert runtime.workspace_reports.bound_source_refs()
        with patch(
            "psycheval.workspace_reports.shutil.rmtree",
            side_effect=PermissionError("cleanup is locked"),
        ):
            with pytest.raises(ReportDeletionCommittedError) as caught:
                runtime.report_library.delete(ref)
        assert caught.value.metadata_cleared is True
        assert caught.value.catalog_reconciled is True
        assert runtime.workspace_reports.bound_source_refs() == set()
        with pytest.raises(ReportNotFound):
            runtime.report_library.read(ref)
        assert original.is_file()
        detached = list(
            (tmp_path / "reports").glob(f".delete-{ref.removeprefix('package:')}-*")
        )
        assert len(detached) == 1
        assert (detached[0] / original.name).read_bytes() == original.read_bytes()
        assert all(
            item["report_ref"] != ref
            for item in runtime.report_library.query(state="all")["items"]
        )


def test_delete_rejects_nonregular_canonical_target_and_escaped_package(tmp_path):
    with library_at(tmp_path) as runtime:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        path = tmp_path / "runs/default/agent/session/trial/analysis.md"
        path.unlink()
        path.mkdir()
        with pytest.raises(ValueError):
            runtime.report_library.delete(ref)
        assert path.is_dir()
        with pytest.raises(ValueError):
            runtime.report_library.delete("package:../runs")
        assert runtime.catalog.binding_rows()


@contextmanager
def report_server(runtime, password=None):
    server = LocalHTTPServer(
        ("127.0.0.1", 0), make_handler(runtime, access=ServeAccess(password))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"

    def send(method, path, payload=None, headers=None):
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_port, timeout=10
        )
        try:
            connection.request(
                method,
                path,
                json.dumps(payload) if payload is not None else None,
                headers={
                    "Origin": origin,
                    "Content-Type": "application/json",
                    **(headers or {}),
                },
            )
            response = connection.getresponse()
            body = response.read()
            value = (
                json.loads(body)
                if body and "json" in response.getheader("Content-Type", "")
                else body
            )
            return response.status, dict(response.getheaders()), value
        finally:
            connection.close()

    try:
        yield send
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize("origin", ["imported", "evaluation"])
@pytest.mark.parametrize("operation", ["archive", "bindings", "delete"])
def test_http_management_lease_deadline_preserves_commit_state(
    tmp_path, monkeypatch, origin, operation
):
    from psycheval import file_access, workspace_reports

    monkeypatch.setattr(
        workspace_reports,
        "blocking_file_lease",
        partial(file_access.blocking_file_lease, timeout_sec=0.05),
    )
    with library_at(tmp_path) as runtime, report_server(runtime) as send:
        ref = (
            imported_report(runtime, tmp_path)[0]
            if origin == "imported"
            else runtime.report_library.query()["items"][0]["report_ref"]
        )
        before = runtime.report_library.read(ref).content
        path = "/api/report-library/" + ref
        method, suffix, body = {
            "archive": ("PUT", "/state", {"archived": True}),
            "bindings": ("PUT", "/bindings", {"bindings": []}),
            "delete": ("DELETE", "", None),
        }[operation]
        with runtime.workspace_reports._management_state_lease(ref):
            status, headers, problem = send(method, path + suffix, body)
        if origin == "evaluation" and operation == "delete":
            assert status == 500
            assert problem["committed"] is True
            assert problem["metadata_cleared"] is False
            assert problem["catalog_reconciled"] is True
            assert {key.lower(): value for key, value in headers.items()}[
                "x-peval-invalidations"
            ] == "reports,catalog"
            assert send("GET", path)[0] == 404
        else:
            assert status == 409
            assert "acquisition timed out" in problem["detail"]
            assert not problem.get("committed")
            assert runtime.report_library.read(ref).content == before
            assert not runtime.report_library.metadata(ref)["archived"]
            assert send(method, path + suffix, body)[0] == (
                204 if operation == "delete" else 200
            )


@pytest.mark.parametrize("operation", ["archive", "bindings", "delete"])
def test_http_report_management_wait_does_not_hold_catalog_writer(tmp_path, operation):
    from concurrent.futures import ThreadPoolExecutor

    with library_at(tmp_path) as runtime, report_server(runtime) as send:
        ref, _ = imported_report(runtime, tmp_path)
        entered = threading.Event()
        lease = runtime.workspace_reports._management_state_lease

        @contextmanager
        def observed_lease(report_ref):
            entered.set()
            with lease(report_ref):
                yield

        method, suffix, body = {
            "archive": ("PUT", "/state", {"archived": True}),
            "bindings": ("PUT", "/bindings", {"bindings": []}),
            "delete": ("DELETE", "", None),
        }[operation]
        with ThreadPoolExecutor() as pool:
            with (
                lease(ref),
                patch.object(
                    runtime.workspace_reports, "_management_state_lease", observed_lease
                ),
            ):
                pending = pool.submit(
                    send, method, "/api/report-library/" + ref + suffix, body
                )
                assert entered.wait(3)
                # Independent writes must proceed while this accepted request waits.
                with runtime.catalog.workspace_write_guard():
                    pass
            assert pending.result(timeout=5)[0] == (
                204 if operation == "delete" else 200
            )


def test_http_source_lease_timeout_does_not_delete_canonical_report(
    tmp_path, monkeypatch
):
    from psycheval import evaluation_reports, file_access

    monkeypatch.setattr(
        evaluation_reports,
        "blocking_file_lease",
        partial(file_access.blocking_file_lease, timeout_sec=0.05),
    )
    with library_at(tmp_path) as runtime, report_server(runtime) as send:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        report_dir = tmp_path / "runs/default/agent/session/trial"
        with evaluation_reports._evaluation_report_lease(report_dir):
            status, _, problem = send("DELETE", "/api/report-library/" + ref)
        assert status == 409
        assert "acquisition timed out" in problem["detail"]
        assert (report_dir / "analysis.md").is_file()
        assert send("DELETE", "/api/report-library/" + ref)[0] == 204


def test_http_archival_validation_reads_busy_guard_and_unified_deletion(tmp_path):
    with library_at(tmp_path) as runtime, report_server(runtime) as send:
        canonical = runtime.report_library.query()["items"][0]["report_ref"]
        package, original = imported_report(runtime, tmp_path)
        for ref in [canonical, package]:
            path = f"/api/report-library/{ref}"
            for payload in [
                {},
                {"archived": "true"},
                {"archived": 1},
                {"archived": True, "extra": 1},
            ]:
                assert send("PUT", path + "/state", payload)[0] == 422
            assert (
                send(
                    "PUT",
                    path + "/state",
                    {"archived": True},
                    {"Origin": "http://foreign.invalid"},
                )[0]
                == 403
            )
            with runtime.catalog.workspace_write_guard():
                assert send("PUT", path + "/state", {"archived": True})[0] == 200
                if ref == canonical:
                    assert send("DELETE", path)[0] == 409
            status, _, metadata = send("PUT", path + "/state", {"archived": True})
            assert status == 200 and metadata["archived"] is True
            assert send("GET", path)[0] == 200
            assert send("GET", path + "/preview")[0] == 200
            assert send("PUT", path + "/state", {"archived": False})[0] == 200
            assert send("DELETE", path)[0] == 204
            assert send("DELETE", path)[0] == 404
            assert send("GET", path + "/preview")[0] == 404
        assert original.read_bytes() == b"# Imported\n"
        assert send("GET", "/api/report-library?state=invalid")[0] == 400
        assert (
            send(
                "PUT", "/api/report-library/analysis:missing/state", {"archived": True}
            )[0]
            == 404
        )


def test_guest_reads_archived_reports_but_cannot_mutate(tmp_path):
    with library_at(tmp_path) as runtime:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        runtime.report_library.set_archived(ref, True)
        with report_server(runtime, password="isolated-test") as send:
            assert send("GET", "/api/report-library")[2]["total"] == 0
            assert send("GET", "/api/report-library?state=archived")[2]["total"] == 1
            assert send("GET", f"/api/report-library/{ref}/preview")[0] == 200
            assert (
                send("PUT", f"/api/report-library/{ref}/state", {"archived": False})[0]
                == 403
            )
            assert send("DELETE", f"/api/report-library/{ref}")[0] == 403


def test_http_committed_delete_failure_has_explicit_flags(tmp_path):
    with library_at(tmp_path) as runtime, report_server(runtime) as send:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        with patch.object(
            runtime.catalog,
            "_reconcile_locked",
            side_effect=RuntimeError("projection failed"),
        ):
            status, headers, problem = send("DELETE", f"/api/report-library/{ref}")
        assert status == 500
        assert problem["committed"] is True
        assert problem["metadata_cleared"] is True
        assert problem["catalog_reconciled"] is False
        assert {key.lower(): value for key, value in headers.items()}[
            "x-peval-invalidations"
        ] == "reports,catalog"


def test_http_imported_delete_cleanup_failure_keeps_the_committed_deletion(tmp_path):
    with library_at(tmp_path) as runtime, report_server(runtime) as send:
        ref, original = imported_report(runtime, tmp_path)
        package = runtime.workspace_reports._package_dir(ref.removeprefix("package:"))
        with patch(
            "psycheval.workspace_reports.shutil.rmtree",
            side_effect=OSError("fixture cleanup failed"),
        ):
            status, headers, problem = send("DELETE", f"/api/report-library/{ref}")
        assert status == 500
        assert problem["committed"] is True
        assert problem["metadata_cleared"] is True
        assert problem["catalog_reconciled"] is True
        assert {key.lower(): value for key, value in headers.items()}[
            "x-peval-invalidations"
        ] == "reports"
        assert not package.exists()
        assert send("GET", f"/api/report-library/{ref}")[0] == 404
        assert original.read_bytes() == b"# Imported\n"


def test_file_lease_preserves_operating_system_error_details(tmp_path):
    from psycheval.file_access import blocking_file_lease

    error = PermissionError(13, "permission denied", str(tmp_path / "lease"))
    with patch("psycheval.file_access._open_lease_descriptor", side_effect=error):
        with pytest.raises(PermissionError) as failure:
            with blocking_file_lease(tmp_path / "lease", label="Report lease"):
                pass
    assert failure.value is error


@pytest.mark.parametrize("origin", ["evaluation", "imported"])
def test_http_delete_declares_its_owner_invalidations(tmp_path, origin):
    with library_at(tmp_path) as runtime, report_server(runtime) as send:
        ref = runtime.report_library.query()["items"][0]["report_ref"]
        if origin == "imported":
            ref, _ = imported_report(runtime, tmp_path)
        status, headers, _ = send("DELETE", f"/api/report-library/{ref}")
        assert status == 204
        assert {key.lower(): value for key, value in headers.items()}[
            "x-peval-invalidations"
        ] == ("reports" if origin == "imported" else "reports,catalog")


def test_source_binding_scope_is_bounded_deduplicated_and_preserves_ref_resolution(
    tmp_path,
):
    with library_at(tmp_path) as runtime:
        write_trial_cell_artifacts(
            tmp_path / "runs/default/agent/other/other_trial",
            session_id="other",
            trial_key="other_trial",
        )
        runtime.catalog.reconcile()
        first, second = runtime.catalog.binding_rows()
        assert runtime.catalog.binding_rows(source_keys=[]) == []
        assert runtime.catalog.binding_rows(source_refs=[first["source_ref"]]) == [
            first
        ]
        assert runtime.catalog.binding_rows(
            source_keys=[
                *(f"missing-{index}" for index in range(501)),
                first["source_key"],
                first["source_key"],
            ],
        ) == [first]
        assert runtime.catalog.binding_rows(
            source_keys=[first["source_key"]],
            source_refs=[first["source_ref"], second["source_ref"]],
        ) == [first, second]
