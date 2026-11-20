from threading import Event
from unittest.mock import patch

import pytest

from psycheval.config import HarborDataset, ToolConfig
from psycheval.serve.harbor_workspace import HarborWorkspace
from psycheval.serve.task_catalog import TaskInventory
from psycheval.state.task_catalog import TaskCatalog
from tests.harbor.test_task_scoring import task, write


def test_persistent_cache_rechecks_safety_and_stable_reads(tmp_path):
    path = tmp_path / "cache.sqlite3"
    cache = TaskCatalog(path)
    stamp, calls, unsafe = 1, [], False

    def signature():
        if unsafe:
            raise ValueError("Unsafe path")
        return stamp

    def load():
        calls.append(1)
        return {"items": [stamp]}

    first = cache.project("task", signature=signature, load=load)
    first["items"].clear()
    cache.publish({"one": "config"}, {"datasets": [{"id": "one"}]})
    cache.close()
    cache = TaskCatalog(path)
    assert cache.snapshot({"one": "config"})["generation"] == 1
    assert cache.snapshot({"one": "other"})["generation"] == 0
    assert cache.project("task", signature=signature, load=load) == {"items": [1]}
    assert len(calls) == 1
    unsafe = True
    with pytest.raises(ValueError, match="Unsafe"):
        cache.project("task", signature=signature, load=load)
    unsafe, stamp = False, 2

    def unstable():
        nonlocal stamp
        stamp += 1
        return load()

    with pytest.raises(ValueError, match="changed"):
        cache.project("task", signature=signature, load=unstable)
    assert cache.project("task", signature=signature, load=load) == {"items": [3]}
    assert len(calls) == 3
    cache.close()


def fixture(tmp_path):
    config_path = tmp_path / "peval.toml"
    config_path.write_text("", encoding="utf-8")
    for name in ("first", "second"):
        task(tmp_path / "dataset" / name)
        write(
            tmp_path / "dataset" / name,
            "tests/grader.json",
            '{"custom_checks":["answer"]}',
        )
    config = ToolConfig(
        workspace_root=str(tmp_path),
        harbor_datasets=(HarborDataset(id="test", path=str(tmp_path / "dataset")),),
    )
    return config_path, config


def test_incremental_scan_and_selected_detail_do_not_read_other_tasks(tmp_path):
    from psycheval.serve.harbor_workspace import (
        _read_regular_file,
        _regular_file_chunks,
    )

    config_path, config = fixture(tmp_path)
    service = HarborWorkspace(config_path, config)
    initial = service.inventory()
    with (
        patch(
            "psycheval.serve.harbor_workspace._read_regular_file",
            wraps=_read_regular_file,
        ) as read,
        patch(
            "psycheval.serve.harbor_workspace._regular_file_chunks",
            wraps=_regular_file_chunks,
        ) as chunks,
    ):
        assert service.inventory() == initial
        assert chunks.call_count == 0
        assert all(call.args[0] == config_path for call in read.call_args_list)
        write(tmp_path / "dataset/first", "instruction.md", "Changed")
        updated = service.inventory()
        assert updated["datasets"][0]["tasks"][0]["instruction"] == "Changed"
        for call in [*read.call_args_list, *chunks.call_args_list]:
            assert "second" not in call.args[0].parts
        read.reset_mock()
        chunks.reset_mock()
        service.task_detail("test", "first")
        for call in [*read.call_args_list, *chunks.call_args_list]:
            assert "second" not in call.args[0].parts


def test_refresh_is_single_flight_retains_previous_and_discards_obsolete_scan(tmp_path):
    config_path, config = fixture(tmp_path)
    inventory = TaskInventory(config_path, config)
    inventory.reconcile()
    initial = inventory.snapshot()
    entered, release = Event(), Event()
    original = HarborWorkspace.task_inventory

    def blocked(service, dataset_id):
        entered.set()
        assert release.wait(5)
        return original(service, dataset_id)

    try:
        with patch.object(HarborWorkspace, "task_inventory", blocked):
            inventory.refresh()
            assert entered.wait(5)
            thread = inventory._thread
            inventory.refresh()
            assert inventory._thread is thread
            assert inventory.snapshot()["datasets"] == initial["datasets"]
            assert inventory.status()["checking"]
            inventory.configure(config.validated_update(harbor_datasets=()))
            release.set()
            thread.join(5)
        assert inventory.snapshot()["datasets"] == []
        assert not inventory.status()["checking"]
    finally:
        release.set()
        inventory.close()


def test_failed_scan_keeps_last_good_dataset_and_totals(tmp_path):
    config_path, config = fixture(tmp_path)
    inventory = TaskInventory(config_path, config)
    try:
        inventory.reconcile()
        first = inventory.snapshot()["datasets"][0]
        assert first["rule_count"] == 2
        with patch.object(
            HarborWorkspace, "task_inventory", side_effect=OSError("Unavailable")
        ):
            inventory.reconcile()
        failed = inventory.snapshot()["datasets"][0]
        assert failed["tasks"] == first["tasks"]
        assert failed["rule_count"] == 2
        assert failed["error"] == "Unavailable"
        inventory.reconcile()
        assert "error" not in inventory.snapshot()["datasets"][0]
    finally:
        inventory.close()


def test_invalid_custom_check_id_is_a_task_diagnostic(tmp_path):
    config_path, config = fixture(tmp_path)
    grader = tmp_path / "dataset/first/tests/grader.json"
    inventory = TaskInventory(config_path, config)
    try:
        inventory.reconcile()
        grader.write_text(r'{"custom_checks":["\ud800"]}', encoding="utf-8")
        inventory.reconcile()
        snapshot = inventory.snapshot()
        assert not snapshot["error"]
        tasks = {row["directory"]: row for row in snapshot["datasets"][0]["tasks"]}
        assert tasks["first"]["rule_count"] is None
        assert "custom_checks" in tasks["first"]["scoring_diagnostics"][0]
        assert tasks["second"]["rule_count"] == 1

        grader.write_text(r'{"custom_checks":["\ud83d\udccb"]}', encoding="utf-8")
        inventory.reconcile()
        tasks = inventory.snapshot()["datasets"][0]["tasks"]
        first = next(row for row in tasks if row["directory"] == "first")
        assert first["scoring_diagnostics"] == []
        assert first["scoring_items"][0]["id"] == "custom:📋"
    finally:
        inventory.close()


def test_corrupt_disposable_cache_is_rebuilt(tmp_path):
    path = tmp_path / "cache.sqlite3"
    path.write_bytes(b"broken sqlite")
    cache = TaskCatalog(path)
    assert cache.snapshot({})["generation"] == 0
    cache.close()


def test_projection_budget_prunes_old_entries_after_publication():
    for cache in (TaskCatalog(max_entries=1), TaskCatalog(max_bytes=1)):
        loads = []

        def get(key):
            value = cache.project(
                key,
                signature=lambda: 1,
                load=lambda: loads.append(key) or {"text": key},
            )
            cache.publish({}, {"datasets": []})
            return value

        get("first")
        get("second")
        get("first")
        assert loads == ["first", "second", "first"]
        cache.close()


def test_guest_refresh_is_cache_only_and_status_never_scans(tmp_path):
    from fastapi.testclient import TestClient

    from psycheval.serve.access import ServeAccess
    from psycheval.serve.api import create_app
    from psycheval.serve.runtime import ServeRuntime
    from psycheval.state import open_workspace_state

    config_path, config = fixture(tmp_path)
    store = open_workspace_state(str(tmp_path))
    runtime = ServeRuntime(store, config)
    try:
        client = TestClient(create_app(runtime, ServeAccess("secret")))
        before = config_path.read_bytes()
        with patch.object(
            HarborWorkspace,
            "task_inventory",
            side_effect=AssertionError("status scanned sources"),
        ):
            assert client.get("/api/collections/datasets/status").status_code == 200
            value = client.get("/api/collections/datasets").json()
            assert value["datasets"][0]["rule_count"] == 2
            assert str(tmp_path) not in str(value)
        response = client.post(
            "/api/collections/datasets/refresh",
            json={},
            headers={"Origin": "http://testserver"},
        )
        assert response.status_code == 200
        assert config_path.read_bytes() == before
    finally:
        runtime.close()
        store.close()
