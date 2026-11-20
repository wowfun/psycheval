import io
import json
import tomllib
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from psycheval.config import (
    HarborDataset,
    load_config,
    write_workspace_harbor_config,
)
from psycheval.serve.harbor_workspace import (
    HarborConflictError,
    HarborWorkspace,
    config_revision,
)
from psycheval.serve.task_tables import (
    TaskExport,
    TaskRowRef,
    build_task_export,
    task_export_rows,
    task_summary,
)
from tests.fixtures.judge_task import YAML
from tests.peval.test_workbuddy_datasets import _write_workbuddy_bundle


@pytest.fixture
def office(tmp_path):
    bundle = _write_workbuddy_bundle(tmp_path / "bundle")
    task = bundle / "tasks/office-one"
    (task / "tests/judge.yaml").write_text(
        YAML + "\nactivation_policy: {enabled: optional}\n", encoding="utf-8"
    )
    config_path = tmp_path / "peval.toml"
    config_path.write_text('locale = "en"\n', encoding="utf-8")
    dataset = HarborDataset(id="office", path=str(bundle), format="workbuddy.v1")
    write_workspace_harbor_config(config_path, (dataset,), ())
    return config_path, bundle


def library(path):
    return HarborWorkspace(path, load_config(workspace_root=path.parent))


def test_scoring_cache_reuses_reads_and_tracks_changed_inputs(office):
    from psycheval.harbor.task_scoring import task_scoring_inventory

    config_path, bundle = office
    service = library(config_path)
    with patch(
        "psycheval.serve.harbor_workspace.task_scoring_inventory",
        wraps=task_scoring_inventory,
    ) as parse:
        first = service.inventory()["datasets"][0]["tasks"][0]
        first["scoring_items"].clear()
        assert len(service.inventory()["datasets"][0]["tasks"][0]["scoring_items"]) == 1
        assert parse.call_count == 1
        source = bundle / "tasks/office-one/tests/judge.yaml"
        source.write_text(YAML.replace("fidelity", "updated"), encoding="utf-8")
        assert (
            service.inventory()["datasets"][0]["tasks"][0]["scoring_items"][0]["id"]
            == "updated"
        )
        assert parse.call_count == 2
        instruction = bundle / "tasks/office-one/instruction.md"
        instruction.write_text("Changed instruction", encoding="utf-8")
        assert (
            service.inventory()["datasets"][0]["tasks"][0]["instruction"]
            == "Changed instruction"
        )
        assert parse.call_count == 3


def test_counted_office_tasks_cannot_be_renamed(office):
    config_path, bundle = office
    service = library(config_path)
    service.set_task_rule_count(
        "office", "office-one", 7, expected_revision=config_revision(config_path)
    )
    before = config_path.read_bytes()
    with pytest.raises(ValueError, match="read-only"):
        library(config_path).rename_task(
            dataset_id="office",
            task="office-one",
            new_directory="renamed",
            expected_revision="unused",
        )
    with pytest.raises(ValueError, match="read-only"):
        library(config_path).trash_task(
            dataset_id="office", task="office-one", expected_revision="unused"
        )
    with pytest.raises(ValueError, match="read-only"):
        library(config_path).restore_task(
            dataset_id="office",
            entry_id="unused",
            directory="renamed",
            expected_revision="unused",
        )
    assert config_path.read_bytes() == before
    assert (bundle / "tasks/office-one").is_dir()


def test_scoring_cache_tracks_missing_step_overrides_and_config_versions(office):
    from tests.harbor.test_task_scoring import task, write

    config_path, bundle = office
    root = bundle / "tasks/office-one"
    task(root, ("one", "two"))
    service = library(config_path)
    assert service.task_scoring("office", "office-one")["rubric_count"] == 2
    override = root / "steps/one/tests/judge.yaml"
    write(root, "steps/one/tests/judge.yaml", YAML.replace("fidelity", "override"))
    assert (
        service.task_scoring("office", "office-one")["scoring_items"][0]["id"]
        == "override"
    )
    override.unlink()
    assert (
        service.task_scoring("office", "office-one")["scoring_items"][0]["id"]
        == "fidelity"
    )
    service.set_task_rule_count(
        "office", "office-one", 0, expected_revision=config_revision(config_path)
    )
    another = HarborWorkspace(
        config_path,
        load_config(workspace_root=config_path.parent),
        task_catalog=service.task_catalog,
    )
    assert another.task_scoring("office", "office-one")["scoring_item_count"] == 2
    assert service.task_scoring("office", "office-one")["rule_count"] is None
    write(root, "task.toml", 'schema_version = "1.3"\n[task]\nname = "suite/example"\n')
    assert another.task_scoring("office", "office-one")["rubric_count"] == 1


def test_unsaved_scoring_preview_never_creates_files(office):
    config_path, bundle = office
    service = library(config_path)
    preview = service.preview_file("office", "office-one", "new/tests/judge.yaml", YAML)
    assert preview["preview"]["items"][0]["id"] == "fidelity"
    assert not (bundle / "tasks/office-one/new").exists()
    with pytest.raises(ValueError):
        service.preview_file("office", "office-one", "../judge.yaml", YAML)


def test_manual_count_roundtrip_zero_clear_and_conflict_preserves_source(office):
    config_path, bundle = office
    before = {p: p.read_bytes() for p in bundle.rglob("*") if p.is_file()}
    service = library(config_path)
    original = config_revision(config_path)
    with (
        patch(
            "psycheval.serve.harbor_workspace._directory_revision",
            side_effect=AssertionError("inventory must not hash WorkBuddy trees"),
        ),
        patch(
            "psycheval.serve.harbor_workspace._validate_task",
            side_effect=AssertionError("inventory must not validate WorkBuddy trees"),
        ),
    ):
        row = service.inventory()["datasets"][0]["tasks"][0]
    assert row["rule_count"] is None and row["rubric_count"] == 1
    service.set_task_rule_count("office", "office-one", 0, expected_revision=original)
    row = library(config_path).inventory()["datasets"][0]["tasks"][0]
    assert row["rule_count"] == 0 and row["scoring_item_count"] == 1
    assert row["rule_count_source"] == "manual"
    assert tomllib.loads(config_path.read_text())["harbor"]["datasets"][0][
        "task_rule_counts"
    ] == {"office-one": 0}
    with pytest.raises(HarborConflictError):
        library(config_path).set_task_rule_count(
            "office", "office-one", 5, expected_revision=original
        )
    library(config_path).set_task_rule_count(
        "office", "office-one", None, expected_revision=config_revision(config_path)
    )
    assert (
        library(config_path).inventory()["datasets"][0]["tasks"][0]["rule_count"]
        is None
    )
    assert before == {p: p.read_bytes() for p in bundle.rglob("*") if p.is_file()}


@pytest.mark.parametrize("value", [-1, 1.2, True, "2"])
def test_manual_count_config_rejects_invalid_numbers(value):
    with pytest.raises(ValueError):
        HarborDataset(
            id="office",
            path="/tmp",
            format="workbuddy.v1",
            task_rule_counts={"task": value},
        )


def test_rename_preserves_counts_and_source_change_clears_them(office, tmp_path):
    config_path, bundle = office
    library(config_path).set_task_rule_count(
        "office", "office-one", 12, expected_revision=config_revision(config_path)
    )
    library(config_path).update_dataset(
        dataset_id="office",
        new_id="renamed",
        path=str(bundle),
        mount_ids=[],
        expected_revision=config_revision(config_path),
    )
    assert library(config_path).config.harbor_datasets[0].task_rule_counts == {
        "office-one": 12
    }
    other = _write_workbuddy_bundle(tmp_path / "other")
    library(config_path).update_dataset(
        dataset_id="renamed",
        new_id="renamed",
        path=str(other),
        mount_ids=[],
        expected_revision=config_revision(config_path),
    )
    assert library(config_path).config.harbor_datasets[0].task_rule_counts == {}


def test_unrelated_config_writes_preserve_counts_and_unregister_removes_them(office):
    from psycheval.config import (
        write_workspace_harbor_mounts,
        write_workspace_locale,
        write_workspace_timezone,
    )

    config_path, _ = office
    library(config_path).set_task_rule_count(
        "office", "office-one", 9, expected_revision=config_revision(config_path)
    )
    write_workspace_locale(config_path, "zh-CN")
    write_workspace_timezone(config_path, "Asia/Shanghai")
    write_workspace_harbor_mounts(config_path, ())
    assert library(config_path).config.harbor_datasets[0].task_rule_counts == {
        "office-one": 9
    }
    library(config_path).remove_datasets(
        dataset_ids=["office"], expected_revision=config_revision(config_path)
    )
    assert library(config_path).config.harbor_datasets == ()
    assert "task_rule_counts" not in config_path.read_text(encoding="utf-8")


def test_export_uses_declared_items_and_manual_totals_without_synthetic_rules(office):
    config_path, _ = office
    library(config_path).set_task_rule_count(
        "office", "office-one", 12, expected_revision=config_revision(config_path)
    )
    service = library(config_path)
    ref = TaskRowRef(dataset_id="office", task="office-one")
    request = TaskExport(
        kind="json",
        mode="tasks",
        rows=[ref],
        columns=[
            "task",
            "rule_count",
            "rubric_count",
            "scoring_item_count",
            "instruction",
        ],
    )
    rows = task_export_rows(service, request, "guest")
    content, _, _ = build_task_export(rows, request, "en")
    assert json.loads(content)[0]["scoring_item_count"] == 13
    assert "package_name" not in json.loads(content)[0]
    assert task_summary(rows, "overall")[0]["rule_count"] == 12
    item = service.inventory()["datasets"][0]["tasks"][0]["scoring_items"][0]
    flat = TaskExport(
        kind="xlsx",
        mode="items",
        rows=[ref.model_copy(update={"item_key": item["key"]})],
    )
    flat_rows = task_export_rows(service, flat, "guest")
    assert len(flat_rows) == 1 and flat_rows[0]["type"] == "rubric"
    assert flat_rows[0]["artifact_refs"] == ["report"]
    content, _, _ = build_task_export(flat_rows, flat, "zh-CN")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        text = archive.read("xl/sharedStrings.xml").decode()
        assert "fidelity" in text and "report" in text and "中文" in text


def test_rule_description_refreshes_and_exports_in_the_question_column(tmp_path):
    from tests.harbor.test_task_scoring import task, write

    config_path = tmp_path / "peval.toml"
    config_path.write_text("", encoding="utf-8")
    task_dir = tmp_path / "dataset" / "example"
    task(task_dir)
    config = {"custom_checks": ["values"]}
    path = "tests/grader.json"
    write(task_dir, path, json.dumps(config))
    dataset = HarborDataset(id="native", path=str(task_dir.parent))
    write_workspace_harbor_config(config_path, (dataset,), ())

    service = library(config_path)
    initial = service.task_scoring("native", "example")["scoring_items"][0]
    assert "question" not in initial
    description = "核对值是否与输入一致。"
    config["scoring"] = {"descriptions": {"custom:values": description}}
    write(task_dir, path, json.dumps(config))

    request = TaskExport(
        kind="xlsx",
        mode="items",
        rows=[TaskRowRef(dataset_id="native", task="example", item_key=initial["key"])],
        columns=["question"],
    )
    rows = task_export_rows(service, request, "guest")
    assert rows[0]["question"] == description
    content, _, _ = build_task_export(rows, request, "zh-CN")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        assert description in archive.read("xl/sharedStrings.xml").decode("utf-8")


def test_unknown_summary_is_not_silently_zero():
    rows = [
        {
            "dataset": "office",
            "rule_count": None,
            "rubric_count": 4,
            "scoring_item_count": None,
        },
        {
            "dataset": "office",
            "rule_count": 2,
            "rubric_count": 3,
            "scoring_item_count": 5,
        },
    ]
    assert task_summary(rows, "dataset") == [
        {
            "group": "office",
            "task_count": 2,
            "rule_count": None,
            "rubric_count": 7,
            "scoring_item_count": None,
            "missing_rule_count": 1,
            "missing_rubric_count": 0,
            "missing_scoring_item_count": 1,
        }
    ]


def test_summary_matches_shared_browser_and_export_contract():
    fixture = json.loads(
        (Path(__file__).parents[1] / "fixtures/task_summary.json").read_text(
            encoding="utf-8"
        )
    )
    for group_by in ("overall", "dataset", "category", "difficulty", "tags"):
        assert task_summary(fixture["tasks"], group_by) == fixture[group_by]


def test_summary_export_respects_nullable_groups_and_metric_order(office):
    config_path, _ = office
    request = TaskExport(
        kind="json",
        mode="summary",
        group_by="category",
        comparison_groups=[None],
        rows=[TaskRowRef(dataset_id="office", task="office-one")] * 2,
        columns=["group", "rubric_count", "task_count", "missing_rubric_count"],
    )
    service = library(config_path)
    rows = task_export_rows(service, request, "guest")
    assert len(rows) == 1 and rows[0]["task_count"] == 1
    payload = json.loads(build_task_export(rows, request, "en")[0])
    assert list(payload[0]) == request.columns
    assert payload[0] == {
        "group": None,
        "rubric_count": 1,
        "task_count": 1,
        "missing_rubric_count": 0,
    }
    request.comparison_groups = []
    assert task_export_rows(service, request, "guest") == []
    request.comparison_groups = ["outside-current-results"]
    assert task_export_rows(service, request, "guest") == []


def test_flat_export_indexes_items_once_per_task():
    class Items(list):
        visits = 0

        def __iter__(self):
            self.visits += 1
            return super().__iter__()

    items = Items({"key": str(i), "id": str(i), "type": "rubric"} for i in range(300))
    service = SimpleNamespace(
        task_inventory=lambda _: {
            "datasets": [{"tasks": [{"directory": "task", "scoring_items": items}]}]
        }
    )
    request = TaskExport(
        kind="json",
        mode="items",
        rows=[
            TaskRowRef(dataset_id="dataset", task="task", item_key=str(i))
            for i in reversed(range(300))
        ],
    )
    assert [row["id"] for row in task_export_rows(service, request, "admin")] == [
        str(i) for i in reversed(range(300))
    ]
    assert items.visits == 1


def test_http_count_permissions_conflicts_preview_and_exports(office):
    from fastapi.testclient import TestClient

    from psycheval.serve.access import ServeAccess
    from psycheval.serve.api import create_app
    from psycheval.serve.runtime import ServeRuntime
    from psycheval.state import open_workspace_state
    from tests.peval.serve_state_support import wait_catalog_operation

    config_path, bundle = office
    store = open_workspace_state(str(config_path.parent))
    runtime = ServeRuntime(store, load_config(workspace_root=config_path.parent))
    try:
        admin = TestClient(create_app(runtime, ServeAccess(None)))
        guest = TestClient(create_app(runtime, ServeAccess("secret")))
        url = "/api/harbor/datasets/office/tasks/office-one"
        initial = admin.get("/api/config")
        from psycheval.harbor.task_scoring import task_scoring_inventory

        with patch(
            "psycheval.serve.harbor_workspace.task_scoring_inventory",
            wraps=task_scoring_inventory,
        ) as parse:
            assert admin.get("/api/collections/datasets").status_code == 200
            assert guest.get("/api/collections/datasets").status_code == 200
            assert parse.call_count == 0  # Both roles read the published snapshot.
        headers = {"If-Match": initial.headers["ETag"]}
        assert (
            guest.put(
                url + "/rule-count", json={"count": 2}, headers=headers
            ).status_code
            == 403
        )
        for value in (-1, 1.5, True, "2"):
            assert (
                admin.put(
                    url + "/rule-count", json={"count": value}, headers=headers
                ).status_code
                == 422
            )
        assert admin.put(url + "/rule-count", json={"count": 0}).status_code == 428
        saved = admin.put(url + "/rule-count", json={"count": 0}, headers=headers)
        assert saved.status_code == 202, saved.text
        assert saved.json()["task"]["scoring_item_count"] == 1
        assert saved.json()["task"]["rule_count_source"] == "manual"
        wait_catalog_operation(runtime.catalog, saved.json()["id"])
        conflict = admin.put(url + "/rule-count", json={"count": 7}, headers=headers)
        assert conflict.status_code == 412
        assert conflict.headers["ETag"] != headers["If-Match"]
        config = admin.get("/api/config")
        assert config.json()["datasets"][0]["task_rule_counts"] == {"office-one": 0}
        assert guest.get(url).json()["task"]["scoring_item_count"] == 1
        source = bundle / "tasks/office-one/tests/judge.yaml"
        before = source.read_bytes()
        draft = guest.post(
            url + "/preview",
            json={
                "path": "tests/judge.yaml",
                "content": YAML.replace("fidelity", "draft-id"),
            },
        )
        assert (
            draft.status_code == 200
            and draft.json()["preview"]["items"][0]["id"] == "draft-id"
        )
        bad = guest.post(
            url + "/preview", json={"path": "tests/judge.yaml", "content": "[bad"}
        )
        assert bad.json()["preview"] is None and bad.json()["preview_error"]
        assert source.read_bytes() == before
        export = guest.post(
            "/api/harbor/task-exports",
            json={
                "kind": "json",
                "mode": "tasks",
                "rows": [{"dataset_id": "office", "task": "office-one"}],
            },
        )
        assert export.status_code == 200 and export.json()[0]["scoring_item_count"] == 1
        cleared = admin.put(
            url + "/rule-count",
            json={"count": None},
            headers={"If-Match": config.headers["ETag"]},
        )
        assert cleared.status_code == 202, cleared.text
        wait_catalog_operation(runtime.catalog, cleared.json()["id"])
        assert (
            library(config_path).inventory()["datasets"][0]["tasks"][0]["rule_count"]
            is None
        )
    finally:
        runtime.close()
        store.close()
