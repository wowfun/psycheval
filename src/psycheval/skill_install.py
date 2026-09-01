from __future__ import annotations

import os
import re
import shutil
import stat
import tempfile
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKILL_RELATIVE_ROOT = Path(".agents/skills")
_SKILL_INSTALL_THREAD_LOCK = threading.Lock()


@dataclass(frozen=True)
class SkillInstallRequest:
    source: Path
    destination: Path


@dataclass(frozen=True)
class SkillInstallResult:
    path: Path
    action: str

    def to_jsonable(self) -> dict[str, str]:
        return {"path": str(self.path), "action": self.action}


def prepare_skill_install(
    workspace_root: Path, skill_dir: str | Path
) -> SkillInstallRequest:
    source = _validate_skill_source(Path(skill_dir).expanduser())
    resolved_workspace = workspace_root.resolve()
    destination = resolved_workspace / SKILL_RELATIVE_ROOT / source.name
    if (
        source == destination
        or source.is_relative_to(destination)
        or destination.is_relative_to(source)
    ):
        raise ValueError(
            f"Agent Skill source and workspace destination must not overlap: {source}"
        )
    _validate_existing_destination_parents(resolved_workspace)
    return SkillInstallRequest(source=source, destination=destination)


def install_skill(request: SkillInstallRequest) -> SkillInstallResult:
    destination = request.destination
    _ensure_destination_parent(destination)
    with _skill_install_lease(destination.parent):
        _recover_interrupted_replacement(destination)
        action = "replaced" if _path_exists(destination) else "installed"
        staged = Path(tempfile.mkdtemp(prefix=".peval-skill-", dir=destination.parent))
        backup = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.backup")
        moved_existing = False
        try:
            shutil.copytree(
                request.source,
                staged,
                dirs_exist_ok=True,
                copy_function=shutil.copy2,
                symlinks=True,
            )
            _validate_skill_source(staged, expected_name=request.source.name)
            if _path_exists(destination):
                _replace_path(destination, backup)
                _fsync_directory(destination.parent)
                moved_existing = True
            _replace_path(staged, destination)
            _fsync_directory(destination.parent)
            if moved_existing:
                _remove_path(backup)
                _fsync_directory(destination.parent)
            return SkillInstallResult(path=destination, action=action)
        except Exception:
            if moved_existing:
                if _path_exists(destination):
                    _remove_path(destination)
                if _path_exists(backup):
                    _replace_path(backup, destination)
                    _fsync_directory(destination.parent)
            raise
        finally:
            if _path_exists(staged):
                _remove_path(staged)


def load_skill_frontmatter(skill_file: Path) -> dict[str, Any]:
    try:
        lines = skill_file.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(
            f"Agent Skill SKILL.md must be readable UTF-8: {skill_file}"
        ) from exc
    if not lines or lines[0] != "---":
        raise ValueError("Agent Skill SKILL.md must start with YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("Agent Skill SKILL.md frontmatter is not closed") from exc
    try:
        values = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as exc:
        raise ValueError("Agent Skill SKILL.md frontmatter is invalid YAML") from exc
    if not isinstance(values, dict):
        raise ValueError("Agent Skill SKILL.md frontmatter must be a mapping")
    return values


def _validate_skill_source(
    candidate: Path, *, expected_name: str | None = None
) -> Path:
    if candidate.is_symlink():
        raise ValueError(f"Agent Skill source must not be a symlink: {candidate}")
    try:
        source = candidate.resolve(strict=True)
    except OSError as exc:
        raise ValueError(f"Agent Skill source does not exist: {candidate}") from exc
    if not source.is_dir():
        raise ValueError(f"Agent Skill source must be a directory: {candidate}")
    _validate_regular_tree(source)
    skill_file = source / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError(f"Agent Skill source is missing SKILL.md: {source}")
    values = load_skill_frontmatter(skill_file)
    name = values.get("name")
    description = values.get("description")
    required_name = expected_name or source.name
    if (
        not isinstance(name, str)
        or name != required_name
        or SKILL_NAME_RE.fullmatch(name) is None
    ):
        raise ValueError(
            "Agent Skill frontmatter name must equal the lowercase kebab-case "
            f"directory name: {required_name}"
        )
    if not isinstance(description, str) or not description.strip():
        raise ValueError("Agent Skill frontmatter description must be non-empty")
    return source


def _validate_regular_tree(root: Path) -> None:
    for directory, directory_names, filenames in os.walk(root, followlinks=False):
        parent = Path(directory)
        directory_names.sort()
        filenames.sort()
        for name in directory_names:
            path = parent / name
            if path.is_symlink():
                raise ValueError(
                    f"Agent Skill source must not contain symlinks: {path}"
                )
            mode = path.stat(follow_symlinks=False).st_mode
            if not stat.S_ISDIR(mode):
                raise ValueError(
                    f"Agent Skill source must contain directories and regular files only: {path}"
                )
        for name in filenames:
            path = parent / name
            if path.is_symlink():
                raise ValueError(
                    f"Agent Skill source must not contain symlinks: {path}"
                )
            mode = path.stat(follow_symlinks=False).st_mode
            if not stat.S_ISREG(mode):
                raise ValueError(
                    f"Agent Skill source must contain regular files only: {path}"
                )


def _validate_existing_destination_parents(workspace_root: Path) -> None:
    current = workspace_root
    for part in SKILL_RELATIVE_ROOT.parts:
        current /= part
        if not _path_exists(current):
            return
        if current.is_symlink() or not current.is_dir():
            raise ValueError(
                "Agent Skill destination parent must be a directory inside the "
                f"workspace: {current}"
            )


def _ensure_destination_parent(destination: Path) -> None:
    workspace_root = destination.parents[len(SKILL_RELATIVE_ROOT.parts)]
    _validate_existing_destination_parents(workspace_root)
    current = workspace_root
    for part in SKILL_RELATIVE_ROOT.parts:
        current /= part
        if not _path_exists(current):
            try:
                current.mkdir()
            except FileExistsError:
                pass
        if current.is_symlink() or not current.is_dir():
            raise ValueError(
                "Agent Skill destination parent must be a directory inside the "
                f"workspace: {current}"
            )


@contextmanager
def _skill_install_lease(directory: Path) -> Iterator[None]:
    lock_path = directory / ".peval-install.lock"
    with _SKILL_INSTALL_THREAD_LOCK:
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(lock_path, flags, 0o600)
        except OSError as exc:
            raise ValueError(
                f"Agent Skill install lock must be a regular file: {lock_path}"
            ) from exc
        handle = os.fdopen(descriptor, "r+b")
        lock_kind = "fcntl"
        try:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise ValueError(
                    f"Agent Skill install lock must be a regular file: {lock_path}"
                )
            try:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except ImportError:
                import msvcrt

                lock_kind = "msvcrt"
                if os.fstat(handle.fileno()).st_size == 0:
                    handle.write(b"0")
                    handle.flush()
                    os.fsync(handle.fileno())
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            yield
        finally:
            try:
                if lock_kind == "msvcrt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError, ValueError):
                pass
            handle.close()


def _fsync_directory(directory: Path) -> None:
    try:
        descriptor = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _recover_interrupted_replacement(destination: Path) -> None:
    prefix = f".{destination.name}."
    suffix = ".backup"
    backups = sorted(
        path
        for path in destination.parent.iterdir()
        if path.name.startswith(prefix)
        and path.name.endswith(suffix)
        and len(path.name.removeprefix(prefix).removesuffix(suffix)) == 32
        and all(
            character in "0123456789abcdef"
            for character in path.name.removeprefix(prefix).removesuffix(suffix)
        )
    )
    if not backups:
        return
    if _path_exists(destination):
        for backup in backups:
            _remove_path(backup)
        _fsync_directory(destination.parent)
        return
    if len(backups) != 1:
        raise ValueError(
            f"Agent Skill replacement has multiple recovery backups: {destination}"
        )
    backup = backups[0]
    _validate_skill_source(backup, expected_name=destination.name)
    _replace_path(backup, destination)
    _fsync_directory(destination.parent)


def _replace_path(source: Path, destination: Path) -> None:
    source.replace(destination)


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        try:
            path.unlink()
        except PermissionError as exc:
            _retry_remove_readonly(os.unlink, path, exc)
    else:
        shutil.rmtree(path, onexc=_retry_remove_readonly)


def _retry_remove_readonly(
    function: Any,
    raw_path: str | Path,
    error: BaseException,
) -> None:
    if not isinstance(error, PermissionError):
        raise error
    path = Path(raw_path)
    if path.is_symlink():
        path.unlink()
        return
    path.chmod(path.stat(follow_symlinks=False).st_mode | stat.S_IWRITE)
    function(raw_path)


def _path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()
