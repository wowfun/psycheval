from __future__ import annotations

import os
from pathlib import Path

import pytest
from harbor.models.task.config import TaskConfig

from psycheval.harbor.tasks import (
    load_harbor_task,
    load_harbor_task_config,
    select_publishable_task_files,
)


@pytest.mark.parametrize(
    ("task_labels", "metadata_labels", "expected"),
    [
        ("", "", {}),
        ('difficulty = "easy"', "", {}),
        ("difficulty = 3\ncategory = false", "", {}),
        ("", 'category = "web-search"', {"category": "web-search"}),
        (
            'difficulty = "medium"\ncategory = "research"',
            "",
            {},
        ),
        (
            "",
            'difficulty = "custom-level"\ncategory = "custom-category"',
            {"difficulty": "custom-level", "category": "custom-category"},
        ),
        (
            'difficulty = "medium"',
            'difficulty = "easy"\ncategory = "research"',
            {"difficulty": "easy", "category": "research"},
        ),
        (
            'category = "browser-control"',
            'difficulty = "easy"\ncategory = "research"',
            {"difficulty": "easy", "category": "research"},
        ),
    ],
)
def test_optional_task_labels_are_read_only_from_metadata(
    tmp_path, task_labels, metadata_labels, expected
):
    source = (
        '[task]\nname = "local/test"\n'
        + task_labels
        + '\n[metadata]\nsource_case = "preserved"\n'
        + metadata_labels
        + "\n"
    ).encode("utf-8")
    path = tmp_path / "task.toml"
    path.write_bytes(source)
    loaded = load_harbor_task_config(tmp_path, read_bytes=Path.read_bytes)
    assert loaded.config == TaskConfig.model_validate_toml(source.decode("utf-8"))
    assert loaded.config.metadata == {"source_case": "preserved", **expected}
    assert loaded.config_bytes == source == path.read_bytes()


@pytest.mark.parametrize("field", ["difficulty", "category"])
@pytest.mark.parametrize("value", ['""', '"  "', "3", "true", "[]"])
def test_present_metadata_labels_require_nonempty_strings(tmp_path, field, value):
    source = '[task]\nname = "local/test"\n[metadata]\n'
    (tmp_path / "task.toml").write_text(source + f"{field} = {value}\n")
    with pytest.raises(ValueError, match=field):
        load_harbor_task_config(tmp_path, read_bytes=Path.read_bytes)


@pytest.mark.parametrize("multi_step", [False, True])
@pytest.mark.parametrize("spelling", ["absolute", "relative", "windows_short"])
def test_task_readers_and_file_selection_preserve_the_callers_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spelling: str, multi_step: bool
) -> None:
    root = tmp_path / "task-with-a-long-directory-name"
    root.mkdir()
    if spelling == "windows_short":
        if os.name != "nt":
            pytest.skip("Windows short directory names")
        import ctypes

        buffer = ctypes.create_unicode_buffer(32768)
        if not ctypes.windll.kernel32.GetShortPathNameW(str(root), buffer, len(buffer)):
            raise ctypes.WinError()
        root = Path(buffer.value)
        if root == root.resolve():
            pytest.skip("short directory names are disabled on this volume")
    elif spelling == "relative":
        monkeypatch.chdir(tmp_path)
        root = Path(root.name)
    lexical_root = root.absolute()
    (root / "task.toml").write_text('[task]\nname = "local/test"\n', encoding="utf-8")
    (root / "instruction.md").write_text("Do the task.\n", encoding="utf-8")
    if multi_step:
        (root / "task.toml").write_text(
            '[task]\nname = "local/test"\n[[steps]]\nname = "first"\n', encoding="utf-8"
        )
        (root / "steps/first").mkdir(parents=True)
        (root / "steps/first/instruction.md").write_text(
            "First step.", encoding="utf-8"
        )
    (root / "tests").mkdir()
    (root / "tests/test.sh").write_text("exit 0\n", encoding="utf-8")
    (root / ".gitignore").write_text("tests/ignored.txt\n", encoding="utf-8")
    (root / "tests/ignored.txt").write_text("ignored", encoding="utf-8")
    (root / "environment").mkdir()
    for script in ("environment/prepare.py", "tests/test_outputs.py"):
        (root / script).write_text("raise AssertionError('Task code was executed')")
    observed = []

    def read_bytes(path: Path) -> bytes:
        observed.append(path.relative_to(lexical_root).as_posix())
        return path.read_bytes()

    loaded = load_harbor_task(root, read_bytes=read_bytes)
    assert loaded.config.task.name == "local/test"
    assert observed == [
        "task.toml",
        "steps/first/instruction.md" if multi_step else "instruction.md",
        ".gitignore",
    ]
    selected = select_publishable_task_files(
        root,
        files=(path for path in root.rglob("*") if path.is_file()),
        read_bytes=read_bytes,
    )
    assert [path.relative_to(lexical_root).as_posix() for path in selected] == sorted(
        [
            "environment/prepare.py",
            "instruction.md",
            "task.toml",
            "tests/test.sh",
            "tests/test_outputs.py",
        ]
        + (["steps/first/instruction.md"] if multi_step else [])
    )
    with pytest.raises(ValueError):
        select_publishable_task_files(
            root, files=[tmp_path / "outside"], read_bytes=read_bytes
        )


def test_task_trajectory_participates_in_publication(tmp_path):
    trajectory = tmp_path / "trajectory.json"
    trajectory.write_text("{}", encoding="utf-8")
    assert select_publishable_task_files(
        tmp_path, files=[trajectory], read_bytes=Path.read_bytes
    ) == [trajectory]
