import io
import tarfile

import pytest

from psycheval.harbor.task_resources import task_resource_inventory, task_totals
from tests.harbor.test_task_scoring import task, write


def inventory(root, **kwargs):
    tree = [
        {
            "kind": "file",
            "path": path.relative_to(root).as_posix(),
            "size": path.stat().st_size,
        }
        for path in root.rglob("*")
        if path.is_file()
    ]
    return task_resource_inventory(
        root, read_bytes=lambda p, limit: p.read_bytes(), tree=tree, **kwargs
    )


def test_native_inputs_exclude_skill_packages_and_controls(tmp_path):
    task(tmp_path)
    with (tmp_path / "task.toml").open("a", encoding="utf-8") as source:
        source.write('\n[environment]\nworkdir="/app"\nskills_dir="/app/skills"\n')
    write(tmp_path, "environment/data/skills/helper/SKILL.md", "Skill")
    write(
        tmp_path, "environment/data/skills/helper/scripts/a.py", "raise AssertionError"
    )
    write(tmp_path, "environment/data/report.csv", "Data")
    write(
        tmp_path, "environment/prepare.py", "raise AssertionError('must not execute')"
    )
    write(tmp_path, "tests/test.sh", "grader")
    result = inventory(tmp_path)
    assert (
        result["skill_count"],
        result["input_file_count"],
        result["has_prepare"],
    ) == (1, 1, True)
    assert result["resources"]["files"][0]["name"] == "report.csv"
    assert result["resources"]["skills"][0]["path"].endswith("SKILL.md")
    (tmp_path / "environment/data/skills/helper/SKILL.md").unlink()
    assert inventory(tmp_path)["skill_count"] is None


@pytest.mark.parametrize("unsafe", [None, "../escape", "link"])
def test_workbuddy_lists_archive_metadata_without_extraction(tmp_path, unsafe):
    task(tmp_path)
    path = tmp_path / "environment/workspace.tar.gz"
    path.parent.mkdir()
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo(unsafe or "inputs/document.txt")
        if unsafe == "link":
            member.type = tarfile.SYMTYPE
            member.linkname = "outside"
        else:
            member.size = 4
        archive.addfile(member, io.BytesIO(b"data"))
    write(tmp_path, "environment/prepare.py", "raise AssertionError")
    result = inventory(tmp_path, format="workbuddy.v1")
    assert result["has_prepare"] is False
    assert not (tmp_path / "inputs").exists()
    if unsafe:
        assert result["input_file_count"] is None
        assert result["resource_diagnostics"]
    else:
        assert result["input_file_count"] == 1
        assert result["resources"]["files"] == [
            {
                "name": "inputs/document.txt",
                "size": 4,
                "archive": "environment/workspace.tar.gz",
            }
        ]


def test_totals_preserve_zero_and_unknown():
    assert task_totals([])["rule_count"] == 0
    assert task_totals([{"rule_count": 0}, {"rule_count": None}])["rule_count"] is None


def test_unresolvable_skills_are_unknown_and_do_not_hide_input_files(tmp_path):
    task(tmp_path)
    with (tmp_path / "task.toml").open("a", encoding="utf-8") as source:
        source.write('\n[environment]\nworkdir="/app"\nskills_dir="/app/../outside"\n')
    write(tmp_path, "environment/data/input.txt", "data")
    value = inventory(tmp_path)
    assert value["skill_count"] is None
    assert value["input_file_count"] == 1
    assert value["resource_diagnostics"]


def test_archive_metadata_inspection_bounds_decompressed_bytes(tmp_path, monkeypatch):
    from psycheval.harbor import task_resources

    task(tmp_path)
    path = tmp_path / "environment/workspace.tar.gz"
    path.parent.mkdir()
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo("large.txt")
        member.size = 8192
        archive.addfile(member, io.BytesIO(b"x" * member.size))
    monkeypatch.setattr(task_resources, "_WORKBUDDY_ARCHIVE_TOTAL_LIMIT", 4096)
    result = inventory(tmp_path, format="workbuddy.v1")
    assert result["input_file_count"] is None
    assert "limits" in result["resource_diagnostics"][0]
