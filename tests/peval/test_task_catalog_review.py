import sqlite3
from threading import Event
from unittest.mock import patch

import pytest

from psycheval.serve.harbor_workspace import HarborWorkspace
from psycheval.serve.task_catalog import TaskInventory
from psycheval.state.task_catalog import TaskCatalog
from tests.peval.test_task_catalog import fixture


def test_nested_projection_scan_reuses_connection_and_hits_do_not_write(tmp_path):
    cache = TaskCatalog(tmp_path / "cache.sqlite3")
    statements = []
    real_connect = sqlite3.connect

    def connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    def scan():
        return [
            cache.project(str(index), signature=lambda: 1, load=lambda: index)
            for index in range(50)
        ]

    with patch(
        "psycheval.state.task_catalog.sqlite3.connect", side_effect=connect
    ) as opened:
        cache.project("all", signature=lambda: 1, load=scan)
        assert opened.call_count == 1
    statements.clear()
    with cache.session():
        cache._db.set_trace_callback(statements.append)
        scan()
    assert not any(
        sql.startswith(("UPDATE", "INSERT", "DELETE", "BEGIN", "COMMIT"))
        for sql in statements
    )
    assert cache._db is None  # A finished scan does not pin Windows file handles.
    cache.close()
    with pytest.raises(RuntimeError, match="closed"):
        cache.project("closed", signature=lambda: 1, load=lambda: None)


def test_publication_is_idempotent_and_scoped_reads_do_not_parse_other_datasets(
    tmp_path,
):
    cache = TaskCatalog(tmp_path / "cache.sqlite3")
    config = {"a": "a-config", "b": "b-config"}
    value = {
        "datasets": [
            {
                "id": "a",
                "tasks": [
                    {
                        "directory": "one",
                        "revision": "r",
                        "status": "conflict",
                        "diagnostics": ["duplicate"],
                    }
                ],
            },
            {"id": "b", "tasks": []},
        ]
    }
    cache.publish(config, value)
    generation = cache.snapshot(config)["generation"]
    cache.publish(config, value)
    assert cache.snapshot(config)["generation"] == generation
    with patch(
        "psycheval.state.task_catalog.json.loads", wraps=__import__("json").loads
    ) as decode:
        result = cache.snapshot(config, dataset_id="a")
        assert [row["id"] for row in result["datasets"]] == ["a"]
        assert not any(
            '"id": "b"' in str(call.args[0]) for call in decode.call_args_list
        )
    assert cache.conflict("a", "one", config["a"], "r")["status"] == "conflict"
    assert cache.conflict("a", "one", config["a"], "changed") is None
    assert [
        row["id"]
        for row in cache.snapshot({"a": "changed", "b": "b-config"})["datasets"]
    ] == ["b"]
    cache.close()


def test_epoch_only_invalidation_cannot_publish_a_pre_mutation_scan(tmp_path):
    config_path, config = fixture(tmp_path)
    inventory = TaskInventory(config_path, config)
    inventory.reconcile()
    before = inventory.snapshot()
    (tmp_path / "dataset/first/instruction.md").write_text(
        "Pre-mutation scan", encoding="utf-8"
    )
    entered, release = Event(), Event()
    original = HarborWorkspace.task_inventory

    def blocked(service, dataset_id):
        value = original(service, dataset_id)
        entered.set()
        assert release.wait(5)
        return value

    try:
        with patch.object(HarborWorkspace, "task_inventory", blocked):
            inventory.refresh()
            assert entered.wait(5)
            thread = inventory._thread
            inventory.begin_mutation()
            release.set()
            thread.join(5)
            assert not thread.is_alive()
            assert inventory.snapshot()["generation"] == before["generation"]
        with patch.object(inventory, "refresh") as refresh:
            inventory.end_mutation()
            refresh.assert_called_once()
    finally:
        release.set()
        inventory.close()


def test_batch_refreshes_once_after_writer_lease_even_with_partial_failure(tmp_path):
    from psycheval.serve.runtime import ServeRuntime
    from psycheval.state import open_workspace_state

    _, config = fixture(tmp_path)
    store = open_workspace_state(str(tmp_path))
    runtime = ServeRuntime(store, config)
    published = Event()
    writer_states = []
    calls = []

    def refresh():
        writer_states.append(runtime.catalog._writer_lock.locked())
        published.set()

    def mutate(item):
        assert runtime.task_inventory.status()["checking"]
        assert not published.is_set()
        calls.append(item)
        if item == 2:
            raise ValueError("Item failed")

    try:
        with patch.object(
            runtime.task_inventory, "refresh", side_effect=refresh
        ) as requested:
            operation = runtime.start_operation(
                "harbor-task-archive", [1, 2, 3], mutate
            )
            assert published.wait(5)
            # The completion hook runs before terminal status publication.
            from time import monotonic, sleep

            deadline = monotonic() + 5
            while (
                runtime.operation(operation.operation_id).state
                not in {"completed", "failed"}
                and monotonic() < deadline
            ):
                sleep(0.01)
            status = runtime.operation(operation.operation_id)
            assert status.state == "completed"
            assert status.completed == 3 and len(status.failures) == 1
            assert calls == [1, 2, 3] and writer_states == [False]
            requested.assert_called_once()
    finally:
        runtime.close()
        store.close()


def test_cache_path_guards_schema_reset_and_oversized_bypass(tmp_path):
    path = tmp_path / "cache.sqlite3"
    with patch.object(type(path), "is_junction", return_value=True):
        with pytest.raises(ValueError, match="links"):
            TaskCatalog(path)
    cache = TaskCatalog(path)
    loads = []
    for _ in range(2):
        assert (
            len(
                cache.project(
                    "large",
                    signature=lambda: 1,
                    load=lambda: loads.append(1) or "x" * (4 * 1024 * 1024),
                )
            )
            == 4 * 1024 * 1024
        )
    assert len(loads) == 2
    cache.publish({}, {"datasets": []})
    cache.close()
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=1")
    cache = TaskCatalog(path)
    assert cache.snapshot({}) == {"datasets": [], "generation": 0}
    cache.close()


def test_task_detail_uses_indexed_conflict_and_inventory_etag_tracks_content(tmp_path):
    from fastapi.testclient import TestClient

    from psycheval.serve.api import create_app
    from psycheval.serve.runtime import ServeRuntime
    from psycheval.state import open_workspace_state

    _, config = fixture(tmp_path)
    store = open_workspace_state(str(tmp_path))
    runtime = ServeRuntime(store, config)
    from psycheval.serve.access import ServeAccess

    client = TestClient(create_app(runtime, ServeAccess(None)))
    try:
        assert client.get("/api/harbor/datasets/missing/tasks").status_code == 404
        before = client.get("/api/harbor/datasets")
        assert "resources" not in before.json()["datasets"][0]["tasks"][0]
        snapshot = runtime.task_inventory.snapshot()
        selected = snapshot["datasets"][0]["tasks"][0]
        selected.update(status="conflict", diagnostics=["Duplicate Task identity"])
        runtime.task_inventory.cache.publish(
            runtime.task_inventory._configs,
            {
                key: value
                for key, value in snapshot.items()
                if key not in {"generation", "checking", "stale", "error"}
            },
        )
        after = client.get("/api/harbor/datasets")
        assert before.headers["ETag"] != after.headers["ETag"]
        with patch.object(
            runtime.task_inventory,
            "snapshot",
            side_effect=AssertionError("detail loaded inventory"),
        ):
            detail = client.get(
                f"/api/harbor/datasets/test/tasks/{selected['directory']}"
            )
            assert detail.status_code == 200
            assert detail.json()["task"]["status"] == "conflict"
            assert "resources" in detail.json()["task"]
    finally:
        runtime.close()
        store.close()


def test_repeated_refreshes_share_the_active_scan_without_queueing_another(tmp_path):
    config_path, config = fixture(tmp_path)
    inventory = TaskInventory(config_path, config)
    entered, release = Event(), Event()
    original = HarborWorkspace.task_inventory
    calls = []

    def blocked(service, dataset_id):
        calls.append(dataset_id)
        entered.set()
        assert release.wait(5)
        return original(service, dataset_id)

    try:
        with patch.object(HarborWorkspace, "task_inventory", blocked):
            inventory.refresh()
            assert entered.wait(5)
            thread = inventory._thread
            for _ in range(5):
                assert inventory.refresh()["checking"]
            release.set()
            thread.join(5)
            assert not thread.is_alive()
        assert calls == ["test"]
        assert not inventory.status()["checking"]
    finally:
        release.set()
        inventory.close()
