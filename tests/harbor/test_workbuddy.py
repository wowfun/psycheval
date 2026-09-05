from __future__ import annotations

import io
import json
import os
import stat
import tarfile
import weakref
from pathlib import Path

import pytest

from psycheval.harbor import workbuddy
from tests.fixtures.workbuddy import SPECIAL_TASK, write_office_bundle


@pytest.fixture
def plan_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.chdir(tmp_path)
    bundle = tmp_path / "bundle"
    write_office_bundle(bundle)
    base = tmp_path / "base.yaml"
    base.write_text(
        "agents:\n  - name: opencode\n    model_name: fixture/model\n", encoding="utf-8"
    )
    monkeypatch.setattr(
        workbuddy, "validate_workbuddy_runtime", lambda: {"version": "fixture"}
    )
    for name in (*workbuddy.LLM_REQUIRED_ENV, workbuddy.LLM_OPTIONAL_ENV):
        monkeypatch.delenv(name, raising=False)
    return {
        "output_root": tmp_path / "output",
        "dataset_id": "office",
        "dataset_path": bundle,
        "base_config": base,
    }


@pytest.mark.parametrize("directory", ["harbor-plans", "harbor-jobs"])
def test_prepare_rejects_linked_output_directories(
    plan_inputs: dict, tmp_path: Path, directory: str
) -> None:
    output = plan_inputs["output_root"]
    output.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (output / directory).symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    with pytest.raises(workbuddy.WorkBuddyPlanError, match="symbolic link"):
        workbuddy.prepare_workbuddy_plan(**plan_inputs)
    assert list(outside.iterdir()) == []


def test_summary_rejects_a_linked_plan_directory(
    plan_inputs: dict, tmp_path: Path
) -> None:
    plan = workbuddy.prepare_workbuddy_plan(**plan_inputs)
    plan_dir = plan_inputs["output_root"] / "harbor-plans" / plan["plan_id"]
    outside = tmp_path / "outside"
    plan_dir.rename(outside)
    try:
        plan_dir.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable")
    with pytest.raises(workbuddy.WorkBuddyPlanError, match="symbolic link"):
        workbuddy.summarize_workbuddy_plan(
            output_root=plan_inputs["output_root"],
            plan_id=plan["plan_id"],
            provisional=True,
        )
    assert not (outside / "workbuddy-summary.json").exists()


def test_prepare_uses_the_validated_dataset_identity(plan_inputs: dict) -> None:
    plan_inputs["dataset_id"] = " office "
    plan = workbuddy.prepare_workbuddy_plan(**plan_inputs)
    assert plan["dataset_id"] == "office"
    stored = (
        plan_inputs["output_root"]
        / "harbor-plans"
        / plan["plan_id"]
        / "workbuddy-run-plan.json"
    )
    assert json.loads(stored.read_text(encoding="utf-8"))["dataset_id"] == "office"


@pytest.mark.parametrize("output_root", ["", " \t"])
def test_prepare_requires_a_nonempty_output_root(
    plan_inputs: dict, output_root: str
) -> None:
    plan_inputs["output_root"] = output_root
    with pytest.raises(workbuddy.WorkBuddyPlanError, match="output root"):
        workbuddy.prepare_workbuddy_plan(**plan_inputs)


@pytest.mark.parametrize("output_root", [".", Path("."), Path("")])
def test_prepare_accepts_an_explicit_current_directory(
    plan_inputs: dict, tmp_path: Path, output_root: str | Path
) -> None:
    plan_inputs["output_root"] = output_root
    plan = workbuddy.prepare_workbuddy_plan(**plan_inputs)
    assert Path(plan["jobs_root"]).parent == tmp_path / "harbor-jobs"


@pytest.mark.parametrize(
    "directory",
    ["harbor-plans", "harbor-jobs", "harbor-plans/fixed", "harbor-jobs/fixed"],
)
def test_prepare_rechecks_directories_after_creation(
    plan_inputs: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, directory: str
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    replaced = plan_inputs["output_root"] / directory
    real_mkdir = Path.mkdir
    swapped = False
    monkeypatch.setattr(workbuddy, "_new_plan_id", lambda: "fixed")

    def swap_after_creation(path: Path, *args, **kwargs):
        nonlocal swapped
        result = real_mkdir(path, *args, **kwargs)
        if path == replaced and not swapped:
            swapped = True
            path.rmdir()
            try:
                path.symlink_to(outside, target_is_directory=True)
            except OSError:
                pytest.skip("directory symlinks are unavailable")
        return result

    monkeypatch.setattr(Path, "mkdir", swap_after_creation)
    with pytest.raises(workbuddy.WorkBuddyPlanError, match="symbolic link"):
        workbuddy.prepare_workbuddy_plan(**plan_inputs)
    assert swapped
    assert list(outside.iterdir()) == []


def _replace_skill_archive(
    plan_inputs: dict, members: list[tuple[str, bytes | None, int]]
) -> None:
    archive = (
        plan_inputs["dataset_path"]
        / "tasks"
        / SPECIAL_TASK
        / "environment/workspace.tar.gz"
    )
    with tarfile.open(archive, "w:gz") as stream:
        for name, content, mode in members:
            info = tarfile.TarInfo(f"agent_pack/skills/recruiting_search/{name}")
            info.mode = mode
            if content is None:
                info.type = tarfile.DIRTYPE
                stream.addfile(info)
            else:
                info.size = len(content)
                stream.addfile(info, io.BytesIO(content))


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
@pytest.mark.parametrize(
    "mode, expected", [(0o777, 0o755), (0o666, 0o644), (0o700, 0o700)]
)
def test_extracted_skill_files_are_not_group_or_world_writable(
    plan_inputs: dict, mode: int, expected: int
) -> None:
    _replace_skill_archive(plan_inputs, [("SKILL.md", b"# Local skill\n", mode)])
    plan = workbuddy.prepare_workbuddy_plan(**plan_inputs)
    skill = Path(plan["skill_dir"]) / "SKILL.md"
    assert stat.S_IMODE(skill.stat().st_mode) == expected


@pytest.mark.parametrize("name", [".GIT/config", ".GiT/hooks/run", "."])
def test_skill_extraction_rejects_git_paths_and_a_regular_root_entry(
    plan_inputs: dict, name: str
) -> None:
    _replace_skill_archive(
        plan_inputs,
        [("SKILL.md", b"# Local skill\n", 0o644), (name, b"unexpected", 0o644)],
    )
    with pytest.raises(workbuddy.WorkBuddyPlanError, match="path is unsafe"):
        workbuddy.prepare_workbuddy_plan(**plan_inputs)


def test_skill_extraction_accepts_a_root_directory_entry(plan_inputs: dict) -> None:
    content = b"# Local skill\n"
    _replace_skill_archive(
        plan_inputs, [(".", None, 0o755), ("SKILL.md", content, 0o644)]
    )
    plan = workbuddy.prepare_workbuddy_plan(**plan_inputs)
    assert (Path(plan["skill_dir"]) / "SKILL.md").read_bytes() == content


def test_skill_extraction_compares_original_duplicate_modes(plan_inputs: dict) -> None:
    _replace_skill_archive(
        plan_inputs,
        [("SKILL.md", b"same", 0o666), ("SKILL.md", b"same", 0o644)],
    )
    with pytest.raises(workbuddy.WorkBuddyPlanError, match="conflicting duplicate"):
        workbuddy.prepare_workbuddy_plan(**plan_inputs)


@pytest.mark.parametrize(
    "writer", [workbuddy._write_yaml, workbuddy._atomic_write_json]
)
def test_output_writes_preserve_destination_and_clean_up_after_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writer
) -> None:
    destination = tmp_path / "document"
    destination.write_text("original", encoding="utf-8")
    before = set(tmp_path.iterdir())

    def fail_sync(descriptor: int) -> None:
        raise OSError("injected write failure")

    monkeypatch.setattr(os, "fsync", fail_sync)
    with pytest.raises(workbuddy.WorkBuddyPlanError, match="cannot write"):
        writer(destination, {"new": "value"})
    assert destination.read_text(encoding="utf-8") == "original"
    assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize(
    "writer", [workbuddy._write_yaml, workbuddy._atomic_write_json]
)
def test_output_writes_reject_destination_symlinks(tmp_path: Path, writer) -> None:
    original = tmp_path / "original"
    original.write_text("keep", encoding="utf-8")
    destination = tmp_path / "destination"
    try:
        destination.symlink_to(original)
    except OSError:
        pytest.skip("file symlinks are unavailable")
    with pytest.raises(workbuddy.WorkBuddyPlanError, match="symbolic link"):
        writer(destination, {"new": "value"})
    assert original.read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize(
    "writer", [workbuddy._write_yaml, workbuddy._atomic_write_json]
)
def test_output_temporary_files_are_created_exclusively(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writer
) -> None:
    real_open = os.open
    writes = []

    def record_open(path, flags, *args, **kwargs):
        if flags & os.O_CREAT and Path(path).parent == tmp_path:
            writes.append(flags)
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", record_open)
    writer(tmp_path / "document", {"key": "value"})
    assert writes and all(flags & os.O_EXCL for flags in writes)


def test_summary_discovery_bounds_retained_entries_without_changing_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plans_root = tmp_path / "harbor-plans"
    plans_root.mkdir()
    live = weakref.WeakSet()
    peak = 0
    closed = False

    class Entry:
        def __init__(self, index: int):
            self.name = f"plan-{index:04d}"
            self.path = str(plans_root / self.name)

        def is_symlink(self):
            return False

        def is_dir(self, *, follow_symlinks):
            return True

    class DirectoryScan:
        def __iter__(self):
            nonlocal peak
            for index in reversed(range(600)):
                entry = Entry(index)
                live.add(entry)
                peak = max(peak, len(live))
                yield entry

        def __enter__(self):
            return self

        def __exit__(self, *args):
            nonlocal closed
            closed = True

    real_scandir = os.scandir
    monkeypatch.setattr(
        os,
        "scandir",
        lambda path: (
            DirectoryScan() if Path(path) == plans_root else real_scandir(path)
        ),
    )
    monkeypatch.setattr(
        workbuddy,
        "_read_plan",
        lambda path: {"plan_id": path.parent.name, "dataset_id": "office"},
    )
    monkeypatch.setattr(
        workbuddy,
        "_read_summary",
        lambda path: {
            "plan_id": path.parent.name,
            "metrics": {"reward": 1, "pass_rate": 1, "n_tasks": 1, "n_trials": 1},
        },
    )
    summaries = workbuddy.discover_workbuddy_summaries(tmp_path, {"office"})
    assert [item["plan_id"] for item in summaries] == [
        f"plan-{index:04d}" for index in range(256)
    ]
    assert peak <= 258
    assert closed
