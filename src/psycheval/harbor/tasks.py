from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pathspec
from harbor.models.task.config import TaskConfig
from harbor.models.task.paths import TaskPaths
from harbor.models.task.task import Task

TaskFileReader = Callable[[Path], bytes]
DEFAULT_TASK_IGNORES = (
    "__pycache__/",
    "*.pyc",
    ".DS_Store",
    "*.swp",
    "*.swo",
    "*~",
)
PUBLISHABLE_TASK_FILES = frozenset(("task.toml", "instruction.md", "README.md"))
PUBLISHABLE_TASK_DIRECTORIES = ("environment/", "tests/", "solution/", "steps/")


@dataclass(frozen=True)
class LoadedHarborTask:
    config: TaskConfig
    config_bytes: bytes


def load_harbor_task(
    task_dir: Path,
    *,
    read_bytes: TaskFileReader,
) -> LoadedHarborTask:
    """Load one Task through strict text and pinned Harbor validation."""

    paths = TaskPaths(task_dir)
    loaded_task = load_harbor_task_config(task_dir, read_bytes=read_bytes)
    config = loaded_task.config

    # Harbor exposes no config-aware validator that accepts already-decoded text.
    # Keep its structural and verifier rules authoritative behind this one seam.
    Task._validate_tests(config, paths)

    instruction_paths = (
        tuple(paths.step_instruction_path(step.name) for step in config.steps)
        if config.steps
        else (paths.instruction_path,)
    )
    for path in instruction_paths:
        _decode_task_text(paths, path, read_bytes(path))
    try:
        gitignore_bytes = read_bytes(paths.gitignore_path)
    except FileNotFoundError:
        pass
    else:
        _decode_task_text(paths, paths.gitignore_path, gitignore_bytes)

    return loaded_task


def load_harbor_task_config(
    task_dir: Path,
    *,
    read_bytes: TaskFileReader,
) -> LoadedHarborTask:
    """Parse one Task configuration through the shared strict UTF-8 seam."""

    paths = TaskPaths(task_dir)
    config_bytes = read_bytes(paths.config_path)
    config = TaskConfig.model_validate_toml(
        _decode_task_text(paths, paths.config_path, config_bytes)
    )
    return LoadedHarborTask(config=config, config_bytes=config_bytes)


def select_publishable_task_files(
    task_dir: Path,
    *,
    files: Iterable[Path],
    read_bytes: TaskFileReader,
) -> list[Path]:
    """Select contained files using Harbor's package layout and UTF-8 ignores.

    Callers supply safely discovered paths. Relative paths are cwd-relative;
    paths outside task_dir raise ValueError before any file is read.
    """

    paths = TaskPaths(task_dir)
    by_relative: dict[str, Path] = {}
    for path in files:
        absolute_path = Path(os.path.abspath(path))
        relative = absolute_path.relative_to(paths.task_dir).as_posix()
        by_relative[relative] = absolute_path

    gitignore = by_relative.get(".gitignore")
    patterns = (
        _decode_task_text(paths, gitignore, read_bytes(gitignore)).splitlines()
        if gitignore is not None
        else DEFAULT_TASK_IGNORES
    )
    spec = pathspec.PathSpec.from_lines("gitignore", patterns)
    selected = [
        path
        for relative, path in by_relative.items()
        if (
            relative in PUBLISHABLE_TASK_FILES
            or relative.startswith(PUBLISHABLE_TASK_DIRECTORIES)
        )
        and not spec.match_file(relative)
    ]
    selected.sort(key=lambda path: path.relative_to(paths.task_dir).as_posix())
    return selected


def _decode_task_text(paths: TaskPaths, path: Path, content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        relative = path.relative_to(paths.task_dir).as_posix()
        raise ValueError(f"Harbor Task text must be UTF-8: {relative}") from exc
