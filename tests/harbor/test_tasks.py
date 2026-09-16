from __future__ import annotations

import os
from pathlib import Path

import pytest

from psycheval.harbor.tasks import load_harbor_task, select_publishable_task_files


@pytest.mark.parametrize("spelling", ["absolute", "relative", "windows_short"])
def test_task_readers_and_file_selection_preserve_the_callers_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, spelling: str
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
    assert observed == ["task.toml", "instruction.md", ".gitignore"]
    selected = select_publishable_task_files(
        root,
        files=(path for path in root.rglob("*") if path.is_file()),
        read_bytes=read_bytes,
    )
    assert [path.relative_to(lexical_root).as_posix() for path in selected] == [
        "environment/prepare.py",
        "instruction.md",
        "task.toml",
        "tests/test.sh",
        "tests/test_outputs.py",
    ]
    with pytest.raises(ValueError):
        select_publishable_task_files(
            root, files=[tmp_path / "outside"], read_bytes=read_bytes
        )
