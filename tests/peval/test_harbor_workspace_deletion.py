import importlib
import os
import shutil
import subprocess
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from psycheval.config import ToolConfig
from psycheval.serve.harbor_workspace import HarborWorkspace, config_revision


@pytest.fixture
def library(tmp_path):
    config_path = tmp_path / "peval.toml"
    config_path.write_text("", encoding="utf-8")
    config = HarborWorkspace(
        config_path, ToolConfig(workspace_root=str(tmp_path))
    ).create_dataset(
        dataset_id="tasks",
        path="dataset",
        package_name="local/tasks",
        expected_revision=config_revision(config_path),
    )
    workspace = HarborWorkspace(config_path, config)
    workspace.create_task(
        dataset_id="tasks",
        directory="hello",
        package_name="local/hello",
        steps=0,
        expected_revision=workspace.inventory()["datasets"][0]["revision"],
    )
    return workspace


@pytest.mark.parametrize("kind", ["symlink", "junction"])
@pytest.mark.parametrize("location", ["root", "child"])
def test_delete_does_not_follow_directory_link_replaced_after_validation(
    tmp_path,
    monkeypatch,
    library,
    kind,
    location,
):
    if kind == "junction" and os.name != "nt":
        pytest.skip("junctions require Windows")
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "retain.txt"
    sentinel.write_bytes(b"retain")
    target = tmp_path / "dataset" / "hello" / "remove"
    target.mkdir()
    link = target if location == "root" else target / "child"
    probe = tmp_path / "link-probe"

    def make_link(path):
        if kind == "junction":
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(path), str(outside)],
                check=True,
                capture_output=True,
            )
        else:
            path.symlink_to(outside, target_is_directory=True)

    def remove_link(path):
        if kind == "junction":
            path.rmdir()
        else:
            path.unlink()

    try:
        make_link(probe)
    except OSError as exc:
        pytest.skip(f"directory links unavailable: {exc}")
    remove_link(probe)
    revision = library.task_detail("tasks", "hello")["task"]["revision"]
    rmtree = shutil.rmtree
    called = []

    def replace_then_delete(path):
        assert path == target
        called.append(path)
        if location == "root":
            path.rmdir()
        make_link(link)
        return rmtree(path)

    with monkeypatch.context() as patch:
        patch.setattr(shutil, "rmtree", replace_then_delete)
        try:
            library.mutate_file(
                "delete",
                {
                    "dataset_id": "tasks",
                    "task": "hello",
                    "path": "remove",
                    "expected_revision": revision,
                },
            )
        except OSError:
            # A root link may be refused rather than removed by the platform.
            assert location == "root"
        finally:
            if link.is_symlink() or link.is_junction():
                remove_link(link)
    assert called == [target]
    assert sentinel.read_bytes() == b"retain"
    assert sorted(path.name for path in outside.iterdir()) == ["retain.txt"]


def test_archive_identity_and_metadata_share_one_timestamp(monkeypatch, library):
    clock = Mock(wraps=datetime)
    clock.now.side_effect = [
        datetime(2026, 1, 1, 23, 59, 59, tzinfo=UTC),
        datetime(2026, 1, 2, tzinfo=UTC),
    ]
    monkeypatch.setattr(
        importlib.import_module("psycheval.serve.harbor_workspace"), "datetime", clock
    )
    archived = library.trash_task(
        dataset_id="tasks",
        task="hello",
        expected_revision=library.task_detail("tasks", "hello")["task"]["revision"],
    )
    assert archived["entry_id"].startswith("20260101T235959Z-")
    assert archived["deleted_at"] == "2026-01-01T23:59:59+00:00"
    clock.now.assert_called_once_with(UTC)
