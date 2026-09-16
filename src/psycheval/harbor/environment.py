from __future__ import annotations

import asyncio
import codecs
import fnmatch
import getpass
import hashlib
import os
import platform
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, replace
from pathlib import Path, PurePath, PurePosixPath
from typing import Literal, Protocol
from uuid import uuid4

from harbor.environments.base import BaseEnvironment, ExecResult, OutputStream
from harbor.environments.capabilities import EnvironmentCapabilities
from harbor.models.task.config import TaskOS
from harbor.utils.scripts import quote_windows_shell_arg

from . import windows
from .paths import HostPathMapper, split_virtual_path, trial_short_uuid
from .runtime_config import (
    DEFAULT_WORKDIR_ROOT,
    PEVAL_CONFIG_ENV,
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
    _resolve_host_path,
    load_effective_runtime_config,
    resolve_workdir_root,
    write_effective_runtime_config,
)

_VIRTUAL_WORKDIR = "/app"
_VIRTUAL_TESTS = "/tests"
_VIRTUAL_SOLUTION = "/solution"
_VIRTUAL_LOGS = "/logs"
_VIRTUAL_AGENT_LOGS = "/logs/agent"
_VIRTUAL_VERIFIER_LOGS = "/logs/verifier"
_VIRTUAL_ARTIFACTS = "/logs/artifacts"
_VIRTUAL_SKILLS = "/harbor/skills"
_VIRTUAL_ROOTS = (
    _VIRTUAL_VERIFIER_LOGS,
    _VIRTUAL_ARTIFACTS,
    _VIRTUAL_AGENT_LOGS,
    _VIRTUAL_SKILLS,
    _VIRTUAL_SOLUTION,
    _VIRTUAL_WORKDIR,
    _VIRTUAL_TESTS,
    _VIRTUAL_LOGS,
)
_WORKSPACE_RESERVED_ROOTS = (
    _VIRTUAL_SKILLS,
    _VIRTUAL_LOGS,
    _VIRTUAL_TESTS,
    _VIRTUAL_SOLUTION,
)
_LEGACY_RUNTIME_ENV_PREFIX = "PSYCHEVAL_"
_DEFAULT_ROOT = object()
_WORKBUDDY_ARCHIVE_FILE_LIMIT = 64 * 1024 * 1024
_WORKBUDDY_ARCHIVE_TOTAL_LIMIT = 256 * 1024 * 1024
_WORKBUDDY_ARCHIVE_ENTRY_LIMIT = 100_000
_PREPARATION_OUTPUT_LIMIT = 8 * 1024 * 1024


async def _await_owned_task(task: asyncio.Task, *, on_cancel=None):
    """Do not release owned resources while an operation is still using them."""
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError as cancelled:
        if on_cancel is not None:
            on_cancel()
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if not task.cancelled() and (error := task.exception()):
            cancelled.add_note(f"owned operation failed: {error}")
        raise


def _check_filesystem_cancel(cancel: threading.Event | None) -> None:
    if cancel is not None and cancel.is_set():
        raise asyncio.CancelledError("Host filesystem operation cancelled")


def _read_regular_nofollow(path: Path, *, max_bytes: int) -> bytes:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError("file is not regular")
        if opened.st_size > max_bytes:
            raise ValueError(f"file exceeds {max_bytes} bytes")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ValueError(f"file exceeds {max_bytes} bytes")
        return content
    finally:
        os.close(descriptor)


@contextmanager
def _open_workspace_archive(archive: Path) -> Iterator[tarfile.TarFile]:
    descriptor = -1
    try:
        before = archive.stat(follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("WorkBuddy workspace archive cannot be extracted")
        flags = (
            os.O_RDONLY
            | getattr(os, "O_BINARY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(archive, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or (
            before.st_ino
            and opened.st_ino
            and (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise ValueError("WorkBuddy workspace archive cannot be extracted")
        raw = os.fdopen(descriptor, "rb")
        descriptor = -1
        with raw:
            try:
                stream = tarfile.open(fileobj=raw, mode="r:gz")
            except (OSError, tarfile.TarError) as exc:
                raise ValueError(
                    "WorkBuddy workspace archive cannot be extracted"
                ) from exc
            with stream:
                yield stream
    except OSError as exc:
        raise ValueError("WorkBuddy workspace archive cannot be extracted") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _extract_workspace_archive(
    archive: Path, destination: Path, *, cancel: threading.Event | None = None
) -> None:
    total = 0
    seen: dict[PurePosixPath, tuple[str, int, int, bytes]] = {}
    try:
        with _open_workspace_archive(archive) as stream:
            for index, member in enumerate(stream, start=1):
                _check_filesystem_cancel(cancel)
                if index > _WORKBUDDY_ARCHIVE_ENTRY_LIMIT:
                    raise ValueError(
                        "WorkBuddy workspace archive exceeds 100000 entries"
                    )
                relative = PurePosixPath(member.name)
                if member.isdir() and member.name in {".", "./"}:
                    continue
                if (
                    relative.is_absolute()
                    or "\\" in member.name
                    or ":" in member.name
                    or not relative.parts
                    or any(
                        part.endswith((" ", ".")) or part.lower() == ".git"
                        for part in relative.parts
                    )
                ):
                    raise ValueError("WorkBuddy workspace archive path is unsafe")
                if (
                    member.issym()
                    or member.islnk()
                    or not (member.isdir() or member.isfile())
                ):
                    raise ValueError("WorkBuddy workspace archive has unsafe entries")
                target = destination.joinpath(*relative.parts)
                if member.isdir():
                    identity = ("directory", member.mode & 0o777, 0, b"")
                    previous = seen.get(relative)
                    if previous is not None and previous != identity:
                        raise ValueError(
                            "WorkBuddy workspace archive has conflicting duplicate paths"
                        )
                    seen[relative] = identity
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                if member.size > _WORKBUDDY_ARCHIVE_FILE_LIMIT:
                    raise ValueError("WorkBuddy workspace archive file exceeds 64 MiB")
                total += member.size
                if total > _WORKBUDDY_ARCHIVE_TOTAL_LIMIT:
                    raise ValueError("WorkBuddy workspace archive exceeds 256 MiB")
                target.parent.mkdir(parents=True, exist_ok=True)
                source = stream.extractfile(member)
                if source is None:
                    raise ValueError("WorkBuddy workspace archive file cannot be read")
                content = source.read(_WORKBUDDY_ARCHIVE_FILE_LIMIT + 1)
                if len(content) != member.size:
                    raise ValueError("WorkBuddy workspace archive file is truncated")
                identity = (
                    "file",
                    member.mode & 0o777,
                    member.size,
                    hashlib.sha256(content).digest(),
                )
                previous = seen.get(relative)
                if previous is not None:
                    if previous != identity:
                        raise ValueError(
                            "WorkBuddy workspace archive has conflicting duplicate paths"
                        )
                    continue
                seen[relative] = identity
                _check_filesystem_cancel(cancel)
                try:
                    with target.open("xb") as output:
                        output.write(content)
                except FileExistsError as exc:
                    raise ValueError(
                        "WorkBuddy workspace archive has conflicting duplicate paths"
                    ) from exc
                target.chmod(member.mode & 0o777)
    except (OSError, tarfile.TarError) as exc:
        raise ValueError("WorkBuddy workspace archive cannot be extracted") from exc


def _initialize_git_baseline(
    workspace: Path, *, project: bool = False, cancel: threading.Event | None = None
) -> None:
    commands = (
        ("init", "-q", "-b", "main"),
        ("config", "user.email", "dev@project"),
        ("config", "user.name", "Developer"),
        ("add", "-A", *(("--force",) if project else ())),
        ("commit", "--allow-empty", "--no-verify", "-q", "-m", "initial setup"),
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    for arguments in commands:
        _check_filesystem_cancel(cancel)
        try:
            result = subprocess.run(
                [
                    "git",
                    "-c",
                    "core.hooksPath=" + os.devnull,
                    "-c",
                    "commit.gpgSign=false",
                    "-C",
                    str(workspace),
                    *arguments,
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError(
                "Host workspace could not create its Git baseline"
            ) from exc
        if result.returncode != 0:
            diagnostic = (result.stderr or result.stdout).strip()
            raise ValueError(
                "Host workspace could not create its Git baseline"
                + (f": {diagnostic}" if diagnostic else "")
            )


def _workspace_entry_info(path: Path) -> os.stat_result:
    info = path.stat(follow_symlinks=False)
    if _is_link_info(info):
        raise ValueError(f"workspace source contains a link or junction: {path}")
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise ValueError(f"workspace source contains a special file: {path}")
    return info


def _is_link_info(info: os.stat_result) -> bool:
    return bool(
        stat.S_ISLNK(info.st_mode)
        or getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _is_native_link(path: Path) -> bool:
    try:
        return _is_link_info(path.stat(follow_symlinks=False))
    except FileNotFoundError:
        return False


def _native_regular_file_info(path: Path) -> os.stat_result:
    try:
        info = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError(f"native filesystem source is not readable: {path}") from exc
    if _is_link_info(info) or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"native filesystem source is not a regular file: {path}")
    return info


def _copy_native_file(
    source: Path, target: Path, *, cancel: threading.Event | None = None
) -> None:
    """Copy one regular file from an already checked native path safely."""

    _check_filesystem_cancel(cancel)
    before = _native_regular_file_info(source)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    descriptor = os.open(source, flags)
    try:
        opened = os.fstat(descriptor)
        if (
            _is_link_info(opened)
            or not stat.S_ISREG(opened.st_mode)
            or not os.path.samestat(before, opened)
        ):
            raise ValueError(
                f"native filesystem source changed while copying: {source}"
            )
        # Harbor collects mounted artifacts onto their existing host files.
        # Preserve the file and every hardlink alias in that case.
        if target.exists() and os.path.samestat(opened, target.stat()):
            return
        with os.fdopen(descriptor, "rb") as incoming:
            descriptor = -1
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary_fd, temporary_name = tempfile.mkstemp(
                prefix=".peval-copy-", dir=target.parent
            )
            temporary = Path(temporary_name)
            try:
                with os.fdopen(temporary_fd, "wb") as outgoing:
                    while True:
                        _check_filesystem_cancel(cancel)
                        chunk = incoming.read(1024 * 1024)
                        _check_filesystem_cancel(cancel)
                        if not chunk:
                            break
                        outgoing.write(chunk)
                temporary.chmod(stat.S_IMODE(opened.st_mode))
                os.utime(temporary, ns=(opened.st_atime_ns, opened.st_mtime_ns))
                _check_filesystem_cancel(cancel)
                temporary.replace(target)
            finally:
                try:
                    temporary.unlink(missing_ok=True)
                except PermissionError as exc:
                    windows.retry_readonly_removal(os.unlink, str(temporary), exc)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _copy_project_tree(
    source: Path, destination: Path, *, cancel: threading.Event | None = None
) -> None:
    _check_filesystem_cancel(cancel)
    if not stat.S_ISDIR(_workspace_entry_info(source).st_mode):
        raise ValueError(f"workspace source must be a directory: {source}")
    pending = [(source.iterdir(), destination)]
    while pending:
        _check_filesystem_cancel(cancel)
        entries, current_destination = pending[-1]
        entry = next(entries, None)
        if entry is None:
            pending.pop()
            continue
        if entry.name.lower() == ".git":
            continue
        info = _workspace_entry_info(entry)
        target = current_destination / entry.name
        if os.path.lexists(target):
            _workspace_entry_info(target)
        if stat.S_ISDIR(info.st_mode):
            if target.exists() and not target.is_dir():
                raise ValueError(f"workspace merge conflict: {target}")
            target.mkdir(exist_ok=True)
            pending.append((entry.iterdir(), target))
        else:
            if target.exists():
                raise ValueError(f"workspace merge conflict: {target}")
            flags = (
                os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            )
            flags |= getattr(os, "O_NONBLOCK", 0)
            with os.fdopen(os.open(entry, flags), "rb") as incoming:
                opened = os.fstat(incoming.fileno())
                if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(
                    info, opened
                ):
                    raise ValueError(f"workspace source changed while copying: {entry}")
                try:
                    with target.open("xb") as outgoing:
                        while True:
                            _check_filesystem_cancel(cancel)
                            chunk = incoming.read(1024 * 1024)
                            _check_filesystem_cancel(cancel)
                            if not chunk:
                                break
                            outgoing.write(chunk)
                except FileExistsError as exc:
                    raise ValueError(f"workspace merge conflict: {target}") from exc
            target.chmod(stat.S_IMODE(info.st_mode))


def _validate_project_directory(source: Path) -> None:
    source = source.expanduser().absolute()
    try:
        for ancestor in (source, *source.parents):
            if not stat.S_ISDIR(_workspace_entry_info(ancestor).st_mode):
                raise ValueError(f"workspace source must be a directory: {source}")
    except OSError as exc:
        raise ValueError(f"cannot access workspace source directory: {source}") from exc


@dataclass(frozen=True)
class _Workspace:
    path: Path
    virtual_path: str
    owned: bool


def _translate_posix_command(command: str, mappings: dict[str, Path]) -> str:
    ordered_mappings = sorted(
        mappings.items(), key=lambda item: len(item[0]), reverse=True
    )
    mapper = HostPathMapper(
        host_os=TaskOS.LINUX,
        mappings=mappings,
        task_workdir=_VIRTUAL_WORKDIR,
    )

    def translate_unquoted(value: str) -> str:
        translated = value
        for virtual, host in ordered_mappings:
            pattern = re.compile(
                rf"(?P<prefix>^|[\s;|&(<>=]){re.escape(virtual)}"
                rf"(?=$|/|[\s;|&()<>])"
            )
            replacement = shlex.quote(str(host))
            translated = pattern.sub(
                lambda match, replacement=replacement: (
                    match.group("prefix") + replacement
                ),
                translated,
            )
        return translated

    pieces: list[str] = []
    unquoted_start = 0
    index = 0
    while index < len(command):
        quote = command[index]
        if quote not in {"'", '"'}:
            if quote == "\\":
                index += 2
            else:
                index += 1
            continue
        pieces.append(translate_unquoted(command[unquoted_start:index]))
        end = index + 1
        while end < len(command):
            if command[end] == quote:
                break
            if quote == '"' and command[end] == "\\":
                end += 2
            else:
                end += 1
        if end >= len(command):
            pieces.append(command[index:])
            return "".join(pieces)
        content = command[index + 1 : end]
        translated_literal = mapper.translate_literal(content)
        if translated_literal is not None and not (
            quote == '"' and any(char in content for char in ("$", "`", "\\"))
        ):
            if quote not in translated_literal and not (
                quote == '"'
                and any(char in translated_literal for char in ("$", "`", "\\"))
            ):
                pieces.append(f"{quote}{translated_literal}{quote}")
            else:
                pieces.append(shlex.quote(translated_literal))
        else:
            pieces.append(command[index : end + 1])
        index = end + 1
        unquoted_start = index
    pieces.append(translate_unquoted(command[unquoted_start:]))
    return "".join(pieces)


def _canonical_virtual_path(value: str, host_os: TaskOS, *, label: str) -> str:
    if host_os == TaskOS.WINDOWS:
        return windows.normalize_environment_path(value, label=label)
    if "\x00" in value:
        raise ValueError(f"{label} contains NUL")
    normalized = value
    if not normalized.startswith("/") or normalized.startswith("//"):
        raise ValueError(f"{label} must be a non-root absolute environment path")
    if ".." in normalized.split("/"):
        raise ValueError(f"{label} cannot traverse a parent")
    canonical = PurePosixPath(normalized).as_posix()
    if canonical == "/":
        raise ValueError(f"{label} must be a non-root absolute environment path")
    return canonical


def _same_or_descendant(path: str, root: str) -> bool:
    return path == root or path.startswith(f"{root}/")


def _paths_overlap(left: str, right: str) -> bool:
    return _same_or_descendant(left, right) or _same_or_descendant(right, left)


class _HostProcessAdapter(Protocol):
    os: TaskOS

    def translate_command(self, command: str, mappings: dict[str, Path]) -> str: ...

    def shell_argv(self, command: str) -> tuple[str, ...]: ...

    def process_kwargs(self) -> dict[str, object]: ...

    def validate_user(self, resolved_user: str | int | None) -> None: ...

    async def terminate(self, process: asyncio.subprocess.Process) -> None: ...

    async def spawn(
        self, argv: Sequence[str], **kwargs
    ) -> asyncio.subprocess.Process: ...

    def release(self, process: asyncio.subprocess.Process) -> None: ...


@dataclass(frozen=True, slots=True)
class HostAccessPolicy:
    """Explicit permissions for Host filesystem and process operations."""

    filesystem: bool = False
    process: bool = False

    def __post_init__(self) -> None:
        invalid = [
            (name, value)
            for name, value in (
                ("filesystem", self.filesystem),
                ("process", self.process),
            )
            if type(value) is not bool
        ]
        if invalid:
            details = ", ".join(
                f"{name}={value!r} ({type(value).__name__})" for name, value in invalid
            )
            raise ValueError(
                "HostAccessPolicy fields must be booleans; invalid " + details
            )
        if self.process and not self.filesystem:
            raise ValueError(
                "HostAccessPolicy.process requires HostAccessPolicy.filesystem"
            )

    @classmethod
    def from_value(cls, value: object) -> HostAccessPolicy:
        """Parse a Python or Job-config representation of the policy."""

        if value is None:
            return cls()
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise ValueError(
                "HostEnvironment host_access must be an object; got "
                f"{type(value).__name__}"
            )
        allowed = {"filesystem", "process"}
        for key in value:
            if not isinstance(key, str) or key not in allowed:
                raise ValueError(
                    f"HostEnvironment host_access has unknown field: {key}"
                )
        filesystem = value.get("filesystem", False)
        process = value.get("process", False)
        return cls(filesystem=filesystem, process=process)


class HostFilesystemAccessError(PermissionError):
    """Raised when a Host filesystem operation is not enabled."""


class HostProcessAccessError(PermissionError):
    """Raised when local Host process execution is not enabled."""


class _LinuxProcessAdapter:
    os = TaskOS.LINUX

    async def spawn(self, argv: Sequence[str], **kwargs) -> asyncio.subprocess.Process:
        return await asyncio.create_subprocess_exec(
            *argv, **kwargs, **self.process_kwargs()
        )

    def release(self, process: asyncio.subprocess.Process) -> None:
        return None

    def translate_command(self, command: str, mappings: dict[str, Path]) -> str:
        return _translate_posix_command(command, mappings)

    def shell_argv(self, command: str) -> tuple[str, ...]:
        return "/bin/bash", "-lc", command

    def process_kwargs(self) -> dict[str, object]:
        return {"start_new_session": True}

    def validate_user(self, resolved_user: str | int | None) -> None:
        if resolved_user is None:
            return
        allowed = {"root", str(os.getuid()), getpass.getuser()}
        if str(resolved_user) not in allowed:
            raise ValueError(
                f"HostEnvironment cannot switch to user {resolved_user!r}; "
                "only root/current-user aliases are accepted"
            )

    async def terminate(self, process: asyncio.subprocess.Process) -> None:
        # Descendants may still own the group and output pipes after the leader exits.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except asyncio.TimeoutError:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        await process.wait()


class HostEnvironment(BaseEnvironment):
    """Provide trusted native filesystem and optional process access for a Task."""

    def __init__(
        self,
        *args,
        host_access: HostAccessPolicy | Mapping[str, object] | None = None,
        workspace_baseline: Literal["git", "none"] = "git",
        workdir_root: str | Path | object = _DEFAULT_ROOT,
        workspace_source: str | Path | None = None,
        **kwargs,
    ):
        if "allow_host_execution" in kwargs:
            raise TypeError(
                "HostEnvironment.allow_host_execution was replaced by "
                "host_access={filesystem, process}"
            )
        if "bootstrap_workbuddy_workspace" in kwargs:
            raise TypeError(
                "use WorkBuddyHostEnvironment for WorkBuddy workspace preparation"
            )
        self._workdir_root = resolve_workdir_root(
            Path(DEFAULT_WORKDIR_ROOT).expanduser()
            if workdir_root is _DEFAULT_ROOT
            else workdir_root
        )
        self._workspace_source = _resolve_host_path(
            workspace_source, base=Path.cwd(), label="HostEnvironment workspace_source"
        )
        if workspace_source is not None:
            _validate_project_directory(Path(workspace_source))
        self._host_access = HostAccessPolicy.from_value(host_access)
        if not isinstance(workspace_baseline, str) or workspace_baseline not in {
            "git",
            "none",
        }:
            raise ValueError(
                "HostEnvironment workspace_baseline must be 'git' or 'none'"
            )
        self._workspace_baseline = workspace_baseline
        self._runtime_root: Path | None = None
        self._workspace: _Workspace | None = None
        self._started = False
        self._stopping = False
        self._initialization_cancel = threading.Event()
        self._initialization_task: asyncio.Task | None = None
        self._lifecycle_lock = asyncio.Lock()
        self._launch_lock = asyncio.Lock()
        self._active_processes: dict[
            asyncio.subprocess.Process, asyncio.Future[None]
        ] = {}
        self._active_filesystem: dict[asyncio.Task, threading.Event] = {}
        self._filesystem_slots = asyncio.Semaphore(4)
        self._callback_command: ContextVar[asyncio.Future[None] | None] = ContextVar(
            "host_callback_command", default=None
        )
        self._task_workdir = _VIRTUAL_WORKDIR
        self._transient_workdirs: dict[str, Path] = {}
        host_system = platform.system()
        if host_system == "Linux":
            self._process_adapter: _HostProcessAdapter = _LinuxProcessAdapter()
        elif host_system == "Windows":
            self._process_adapter = windows.WindowsProcessAdapter()
        else:
            raise RuntimeError(
                "HostEnvironment supports native Linux and Windows hosts only; "
                f"received {host_system!r}"
            )
        super().__init__(*args, **kwargs)

    @staticmethod
    def type() -> str:
        return "psycheval-host"

    @property
    def capabilities(self) -> EnvironmentCapabilities:
        return EnvironmentCapabilities(
            mounted=True, windows=self._process_adapter.os == TaskOS.WINDOWS
        )

    @property
    def os(self) -> TaskOS:
        return self._process_adapter.os

    @property
    def host_access(self) -> HostAccessPolicy:
        """The immutable permissions configured for this Host instance."""

        return self._host_access

    def _require_filesystem_access(self) -> None:
        if not self._host_access.filesystem:
            raise HostFilesystemAccessError(
                "HostEnvironment filesystem access is disabled; set "
                "host_access.filesystem=true"
            )

    def _require_process_access(self) -> None:
        if not self._host_access.process:
            raise HostProcessAccessError(
                "HostEnvironment process execution is disabled; set "
                "host_access.process=true"
            )

    def _require_filesystem_ready(self) -> None:
        self._require_filesystem_access()
        if not self._started:
            raise RuntimeError("HostEnvironment has not started")
        if self._stopping:
            raise RuntimeError("HostEnvironment is stopping")

    async def _run_filesystem(
        self, operation: Callable, *args, cancellable: bool = False, **kwargs
    ):
        self._require_filesystem_ready()
        cancel = threading.Event()

        async def run():
            async with self._filesystem_slots:
                _check_filesystem_cancel(cancel)
                return await asyncio.to_thread(
                    operation,
                    *args,
                    **kwargs,
                    **({"cancel": cancel} if cancellable else {}),
                )

        # No await separates the readiness check and registration, so stop sees
        # every admitted operation, including those waiting for an executor slot.
        worker = asyncio.create_task(run())
        self._active_filesystem[worker] = cancel
        try:
            return await _await_owned_task(worker, on_cancel=cancel.set)
        finally:
            self._active_filesystem.pop(worker, None)

    def _chmod_directory(self, path: Path, *, chmod: bool) -> None:
        if chmod and self.os != TaskOS.WINDOWS:
            path.chmod(0o777)

    def _validate_definition(self) -> None:
        self._require_filesystem_access()
        if self._workspace_baseline == "git" and not self._host_access.process:
            raise ValueError(
                "workspace_baseline='git' requires host_access.process=true"
            )
        self._validate_task_environment()
        self._validate_mounts()

    def _validate_task_environment(self) -> None:
        if self._workspace_source is not None:
            _validate_project_directory(self.environment_dir)
        if (
            self.task_env_config.os == TaskOS.WINDOWS
            and self._process_adapter.os != TaskOS.WINDOWS
        ):
            raise RuntimeError(
                "A Windows-targeted Task requires a native Windows HostEnvironment"
            )
        if not self.environment_dir.is_dir():
            raise FileNotFoundError(
                f"Task environment directory not found: {self.environment_dir}"
            )
        self._validate_build_context()
        self._task_workdir = _canonical_virtual_path(
            self.task_env_config.workdir or _VIRTUAL_WORKDIR,
            self.os,
            label="HostEnvironment [environment].workdir",
        )
        requested_resources = {
            "cpus": self.task_env_config.cpus,
            "memory_mb": self.task_env_config.memory_mb,
            "storage_mb": self.task_env_config.storage_mb,
            "gpus": self.task_env_config.gpus,
            "tpu": self.task_env_config.tpu,
        }
        requested = [
            key
            for key, value in requested_resources.items()
            if value is not None and value != 0
        ]
        if self.task_env_config.gpu_types:
            requested.append("gpu_types")
        if requested:
            raise ValueError(
                "HostEnvironment cannot enforce Task resources: "
                + ", ".join(sorted(requested))
            )

    def _validate_build_context(self) -> None:
        if any(
            os.path.lexists(self.environment_dir / name)
            for name in ("docker-compose.yaml", "docker-compose.yml")
        ):
            raise ValueError("HostEnvironment does not support Docker Compose Tasks")

    def _validate_mounts(self) -> None:
        expected_mounts = {
            _VIRTUAL_AGENT_LOGS: self.trial_paths.agent_dir,
            _VIRTUAL_VERIFIER_LOGS: self.trial_paths.verifier_dir,
            _VIRTUAL_ARTIFACTS: (self.trial_paths.artifacts_dir / "logs" / "artifacts"),
        }
        managed_mounts: list[tuple[dict, str]] = []
        workspace_mounts: list[tuple[str, Path]] = []
        for mount in self._mounts:
            target = str(mount.get("target"))
            target_match = split_virtual_path(target, self.os, _VIRTUAL_ROOTS)
            logical_target = (
                target_match[0]
                if target_match is not None and not target_match[1]
                else None
            )
            if logical_target in expected_mounts:
                managed_mounts.append((mount, logical_target))
                continue
            if mount.get("type") != "bind":
                raise ValueError(
                    f"HostEnvironment workspace mount {target!r} must have type='bind'"
                )
            if mount.get("read_only"):
                raise ValueError(
                    f"HostEnvironment workspace mount {target!r} must be writable"
                )
            workspace_target = _canonical_virtual_path(
                target,
                self.os,
                label="HostEnvironment workspace mount target",
            )
            reserved = next(
                (
                    root
                    for root in _WORKSPACE_RESERVED_ROOTS
                    if _paths_overlap(workspace_target, root)
                ),
                None,
            )
            if reserved is not None:
                raise ValueError(
                    "HostEnvironment workspace mount target "
                    f"{target!r} overlaps reserved path {reserved!r}"
                )
            source = mount.get("source")
            if not isinstance(source, str):
                raise ValueError(
                    f"HostEnvironment workspace mount {target!r} requires a source"
                )
            workspace_source = Path(source).expanduser().resolve()
            if not workspace_source.is_dir():
                raise ValueError(
                    "HostEnvironment workspace mount source must be an existing "
                    f"directory: {str(workspace_source)!r}"
                )
            workspace_mounts.append((workspace_target, workspace_source))
        if len(workspace_mounts) > 1:
            raise ValueError("HostEnvironment supports only one workspace mount")
        if self._workspace_source is not None and workspace_mounts:
            raise ValueError(
                "workspace_source cannot be combined with a workspace mount"
            )
        if workspace_mounts:
            target, source = workspace_mounts[0]
            self._workspace = _Workspace(source, target, owned=False)
        seen_targets: set[str] = set()
        for mount, logical_target in managed_mounts:
            target = str(mount.get("target"))
            if logical_target in seen_targets:
                raise ValueError(
                    f"HostEnvironment received duplicate mount target {target!r}"
                )
            seen_targets.add(logical_target)
            if mount.get("type") != "bind":
                raise ValueError(
                    f"HostEnvironment mount {target!r} must have type='bind'"
                )
            if mount.get("read_only"):
                raise ValueError(f"HostEnvironment mount {target!r} must be writable")
            source = mount.get("source")
            expected_source = expected_mounts[logical_target].resolve()
            if not isinstance(source, str) or Path(source).resolve() != expected_source:
                raise ValueError(
                    f"HostEnvironment mount {target!r} must use Harbor's Trial source "
                    f"{str(expected_source)!r}"
                )

    async def start(self, force_build: bool) -> None:
        self._require_lifecycle_caller()
        if force_build:
            raise ValueError("HostEnvironment does not build Docker images")
        self._require_filesystem_access()
        async with self._lifecycle_lock:
            if self._started:
                return
            if self._runtime_root is not None or (
                self._workspace is not None and self._workspace.owned
            ):
                await self._delete_owned_runtime()
            self._initialization_cancel.clear()
            self._runtime_root = Path(tempfile.mkdtemp(prefix="session-"))
            self._initialization_task = asyncio.create_task(self._initialize())
            try:
                await _await_owned_task(
                    self._initialization_task, on_cancel=self._cancel_initialization
                )
            except BaseException as error:
                try:
                    await self._delete_owned_runtime()
                except OSError as cleanup_error:
                    error.add_note(f"workspace cleanup failed: {cleanup_error}")
                raise
            finally:
                self._initialization_task = None
            self._started = True

    def _cancel_initialization(self) -> None:
        self._initialization_cancel.set()
        if self._initialization_task is not None:
            self._initialization_task.cancel()

    async def _initialize(self) -> None:
        await _await_owned_task(
            asyncio.create_task(asyncio.to_thread(self._initialize_context)),
            on_cancel=self._initialization_cancel.set,
        )
        _check_filesystem_cancel(self._initialization_cancel)
        await self._run_input_preparation()
        if not self._is_separate_verifier() and (
            self._workspace is None or self._workspace.owned
        ):
            await _await_owned_task(
                asyncio.create_task(
                    asyncio.to_thread(
                        self._initialize_workspace_baseline,
                        self._context_target(self._runtime_dirs()),
                        project=self._workspace_source is not None,
                        cancel=self._initialization_cancel,
                    )
                ),
                on_cancel=self._initialization_cancel.set,
            )
        _check_filesystem_cancel(self._initialization_cancel)

    async def _run_input_preparation(self) -> None:
        if self._is_separate_verifier():
            return
        assert self._runtime_root is not None
        script = self._runtime_root / "preparation" / "prepare.py"
        if not script.is_file():
            return
        self._require_process_access()
        workdir = self._context_target(self._runtime_dirs())
        log_path = self.trial_paths.trial_dir / "prepare.log"
        with log_path.open("w", encoding="utf-8", errors="backslashreplace") as log:

            async def record(text: str, stream: OutputStream) -> None:
                log.write(text)
                log.flush()

            try:
                with self.scoped_output_callback(record):
                    result = await self._exec_process(
                        [
                            sys.executable,
                            "-B",
                            str(Path(__file__).with_name("_prepare.py")),
                            str(script),
                            str(workdir),
                        ],
                        cwd=str(workdir),
                        env={"PYTHONIOENCODING": "utf-8"},
                        timeout_sec=None,
                        user=None,
                        initializing=True,
                    )
                if result.return_code != 0:
                    raise RuntimeError(
                        f"Task preparation failed with exit code {result.return_code}; "
                        f"see {log_path}"
                    )
            except BaseException as error:
                log.write(f"\n{type(error).__name__}: {error}\n")
                raise

    def _initialize_context(self) -> None:
        cancel = self._initialization_cancel
        _check_filesystem_cancel(cancel)
        self._prepare_automatic_workspace()
        mappings = self._create_runtime_directories()
        context_target = self._context_target(mappings)
        self._materialize_context(context_target, cancel=cancel)
        _check_filesystem_cancel(cancel)

    def _create_runtime_directories(self) -> dict[str, Path]:
        mappings = self._runtime_dirs()
        if self.os == TaskOS.WINDOWS:
            quote_windows_shell_arg(sys.executable)
            for path in set(mappings.values()):
                quote_windows_shell_arg(path)
        for path in set(mappings.values()):
            path.mkdir(parents=True, exist_ok=True)
        return mappings

    def _context_target(self, mappings: Mapping[str, Path]) -> Path:
        separate_verifier = self._is_separate_verifier()
        context_target = (
            mappings[_VIRTUAL_TESTS]
            if separate_verifier
            else self._translate_path(self._task_workdir)
        ).resolve()
        return context_target

    def _materialize_context(
        self, context_target: Path, *, cancel: threading.Event
    ) -> None:
        if self._is_separate_verifier():
            self._copy_environment_context(context_target, cancel=cancel)
            return
        source_root = self.environment_dir.resolve()
        if context_target.is_relative_to(source_root) or source_root.is_relative_to(
            context_target
        ):
            raise ValueError("Task environment and workspace destination overlap")
        if self._workspace_source is not None:
            _copy_project_tree(self._workspace_source, context_target, cancel=cancel)
        if os.path.lexists(self.environment_dir / "prepare.py"):
            self._require_process_access()
            assert self._runtime_root is not None
            stage = self._runtime_root / "preparation"
            stage.mkdir()
            _copy_project_tree(self.environment_dir, stage, cancel=cancel)
            if not (stage / "prepare.py").is_file():
                raise ValueError("environment/prepare.py must be a regular file")
        elif os.path.lexists(self.environment_dir / "data"):
            source = self.environment_dir / "data"
            if source.resolve().is_relative_to(
                context_target
            ) or context_target.is_relative_to(source.resolve()):
                raise ValueError("workspace data source and destination overlap")
            _copy_project_tree(source, context_target, cancel=cancel)

    def _copy_environment_context(
        self, context_target: Path, *, cancel: threading.Event
    ) -> None:
        """Materialize environment-owned contexts (WorkBuddy or verifier tests)."""
        separate_verifier = self._is_separate_verifier()
        environment_source = self.environment_dir.resolve()
        project = self._workspace_source is not None and not separate_verifier
        if project:
            _copy_project_tree(self._workspace_source, context_target, cancel=cancel)
            _copy_project_tree(environment_source, context_target, cancel=cancel)
        elif context_target != environment_source:
            if context_target.is_relative_to(environment_source):
                raise ValueError(
                    "HostEnvironment workspace context target cannot be inside "
                    f"the Task environment directory: {str(context_target)!r}"
                )
            if self._workspace is not None and self._workspace.owned:
                _copy_project_tree(environment_source, context_target, cancel=cancel)
            else:
                shutil.copytree(environment_source, context_target, dirs_exist_ok=True)

    def _initialize_workspace_baseline(
        self,
        context_target: Path,
        *,
        project: bool = False,
        cancel: threading.Event | None = None,
    ) -> None:
        if self._workspace_baseline == "git":
            if os.path.lexists(context_target / ".git"):
                raise ValueError(
                    "Host workspace baseline cannot reuse inherited .git metadata"
                )
            _initialize_git_baseline(context_target, project=project, cancel=cancel)

    def _prepare_automatic_workspace(self) -> None:
        if self._workspace is not None or self._is_separate_verifier():
            return
        root = self._workdir_root
        assert root is not None
        workspace = root / f"task_{trial_short_uuid(self.trial_paths.trial_dir.name)}"
        sources = [self.environment_dir.resolve()]
        if self._workspace_source is not None:
            sources.append(self._workspace_source)
        for source in sources:
            if workspace.is_relative_to(source) or source.is_relative_to(workspace):
                raise ValueError(f"workspace source and destination overlap: {source}")
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise ValueError(
                f"HostEnvironment workdir_root is not a directory: {str(root)!r}"
            )
        try:
            workspace.mkdir()
        except FileExistsError as exc:
            raise FileExistsError(
                "HostEnvironment automatic workspace already exists; refusing to "
                f"reuse stale state: {str(workspace)!r}"
            ) from exc
        self._workspace = _Workspace(workspace, self._task_workdir, owned=True)

    def _is_separate_verifier(self) -> bool:
        logical_targets = {
            match[0]
            for mount in self._mounts
            if mount.get("target")
            and (
                match := split_virtual_path(
                    str(mount["target"]), self.os, _VIRTUAL_ROOTS
                )
            )
            is not None
            and not match[1]
        }
        return (
            _VIRTUAL_VERIFIER_LOGS in logical_targets
            and _VIRTUAL_AGENT_LOGS not in logical_targets
        )

    async def stop(self, delete: bool):
        self._require_lifecycle_caller()
        if not self._started:
            self._cancel_initialization()
        async with self._lifecycle_lock:
            self._stopping = True
            try:
                await _await_owned_task(
                    asyncio.create_task(self._stop_commands(delete))
                )
            finally:
                self._stopping = False

    def _require_lifecycle_caller(self) -> None:
        command = self._callback_command.get()
        if command is not None and not command.done():
            raise RuntimeError(
                "HostEnvironment lifecycle operations cannot run from an active "
                "output callback"
            )

    async def _stop_commands(self, delete: bool) -> None:
        for cancel in self._active_filesystem.values():
            cancel.set()
        async with self._launch_lock:
            commands = list(self._active_processes.items())
        for process, _ in commands:
            await self._terminate_process(process)
        if commands:
            await asyncio.gather(*(done for _, done in commands))
        if self._active_filesystem:
            await asyncio.gather(*self._active_filesystem, return_exceptions=True)
        if delete:
            await self._delete_owned_runtime()

    async def _delete_owned_runtime(self) -> None:
        self._started = False
        await _await_owned_task(
            asyncio.create_task(asyncio.to_thread(self._remove_owned_runtime))
        )

    def _remove_owned_runtime(self) -> None:
        errors: list[OSError] = []
        if self._workspace is not None and self._workspace.owned:
            try:
                shutil.rmtree(
                    self._workspace.path,
                    ignore_errors=False,
                    onexc=windows.retry_readonly_removal,
                )
            except FileNotFoundError:
                self._workspace = None
            except OSError as exc:
                errors.append(exc)
            else:
                self._workspace = None
        if self._runtime_root is not None:
            try:
                shutil.rmtree(
                    self._runtime_root,
                    ignore_errors=False,
                    onexc=windows.retry_readonly_removal,
                )
            except FileNotFoundError:
                self._runtime_root = None
            except OSError as exc:
                errors.append(exc)
            else:
                self._runtime_root = None
        self._transient_workdirs.clear()
        if errors:
            for additional in errors[1:]:
                errors[0].add_note(f"additional cleanup failure: {additional}")
            raise errors[0]

    def _runtime_dirs(self) -> dict[str, Path]:
        if self._runtime_root is None:
            raise RuntimeError("HostEnvironment has not started")
        mounted: dict[str, Path] = {}
        for mount in self._mounts:
            if not mount.get("target") or not mount.get("source"):
                continue
            target_match = split_virtual_path(
                str(mount["target"]), self.os, _VIRTUAL_ROOTS
            )
            if target_match is not None and not target_match[1]:
                mounted[target_match[0]] = Path(str(mount["source"]))
        separate_verifier = self._is_separate_verifier()
        default_agent_logs = (
            self._runtime_root / "logs" / "agent"
            if separate_verifier
            else self.trial_paths.agent_dir
        )
        default_artifacts = (
            self._runtime_root / "logs" / "artifacts"
            if separate_verifier
            else self.trial_paths.artifacts_dir / "logs" / "artifacts"
        )
        mappings = {
            _VIRTUAL_WORKDIR: self._runtime_root / "app",
            _VIRTUAL_TESTS: self._runtime_root / "tests",
            _VIRTUAL_SOLUTION: self._runtime_root / "solution",
            _VIRTUAL_SKILLS: self._runtime_root / "skills",
            _VIRTUAL_LOGS: self._runtime_root / "logs",
            _VIRTUAL_AGENT_LOGS: mounted.get(_VIRTUAL_AGENT_LOGS, default_agent_logs),
            _VIRTUAL_VERIFIER_LOGS: mounted.get(
                _VIRTUAL_VERIFIER_LOGS, self.trial_paths.verifier_dir
            ),
            _VIRTUAL_ARTIFACTS: mounted.get(
                _VIRTUAL_ARTIFACTS,
                default_artifacts,
            ),
        }
        if self._task_workdir != _VIRTUAL_WORKDIR and not (
            self._workspace is not None
            and _same_or_descendant(self._task_workdir, self._workspace.virtual_path)
        ):
            mappings[self._task_workdir] = self._transient_path(self._task_workdir)
        if self._workspace is not None:
            mappings[self._workspace.virtual_path] = self._workspace.path
        mappings.update(self._transient_workdirs)
        return mappings

    def _transient_path(self, virtual: str) -> Path:
        if self._runtime_root is None:
            raise RuntimeError("HostEnvironment has not started")
        parts = tuple(part for part in PurePosixPath(virtual).parts if part != "/")
        return self._runtime_root.joinpath("workdirs", *parts)

    def _register_virtual_workdir(self, value: str | PurePath) -> str:
        canonical = _canonical_virtual_path(
            str(value), self.os, label="HostEnvironment workdir"
        )
        if self._workspace is not None and not self._workspace.owned:
            workspace_target = self._workspace.virtual_path
            if not _same_or_descendant(canonical, workspace_target):
                raise ValueError(
                    "HostEnvironment workdir must equal the workspace mount target "
                    f"or be its descendant: {workspace_target!r}"
                )
        if split_virtual_path(canonical, self.os, tuple(self._runtime_dirs())) is None:
            self._transient_workdirs[canonical] = (
                self._workspace.path
                if self._workspace is not None and self._workspace.owned
                else self._transient_path(canonical)
            )
        return canonical

    async def ensure_dirs(
        self,
        dirs: Sequence[str | PurePath],
        *,
        chmod: bool = True,
        virtual_workdir: bool = False,
    ) -> ExecResult | None:
        self._require_filesystem_ready()
        paths = (
            [self._register_virtual_workdir(path) for path in dirs]
            if virtual_workdir
            else dirs
        )
        mapper = self._path_mapper()
        native_paths = [mapper.translate(path) for path in paths]
        await self._run_filesystem(self._ensure_native_dirs, native_paths, chmod=chmod)
        return None

    def _ensure_native_dirs(self, paths: Sequence[Path], *, chmod: bool) -> None:
        for native in paths:
            native.mkdir(parents=True, exist_ok=True)
            self._chmod_directory(native, chmod=chmod)

    @staticmethod
    def _remove_native_path(path: Path) -> None:
        if not os.path.lexists(path):
            return
        info = path.stat(follow_symlinks=False)
        if _is_link_info(info) and stat.S_ISDIR(info.st_mode):
            path.rmdir()
        elif stat.S_ISDIR(info.st_mode):
            shutil.rmtree(path, onexc=windows.retry_readonly_removal)
        else:
            try:
                path.unlink()
            except PermissionError as exc:
                windows.retry_readonly_removal(os.unlink, str(path), exc)

    def _empty_native_directory(self, path: Path) -> None:
        if path.is_dir() and not _is_native_link(path):
            for child in path.iterdir():
                self._remove_native_path(child)
            return
        self._remove_native_path(path)
        path.mkdir(parents=True, exist_ok=True)

    async def empty_dirs(
        self,
        dirs: Sequence[str | PurePath],
        *,
        chmod: bool = True,
    ) -> ExecResult | None:
        self._require_filesystem_ready()
        mapper = self._path_mapper()
        native_paths = [mapper.translate(path) for path in dirs]
        await self._run_filesystem(self._empty_native_dirs, native_paths, chmod=chmod)
        return None

    def _empty_native_dirs(self, paths: Sequence[Path], *, chmod: bool) -> None:
        for native in paths:
            self._empty_native_directory(native)
            self._chmod_directory(native, chmod=chmod)

    async def reset_dirs(
        self,
        *,
        remove_dirs: Sequence[str | PurePath],
        create_dirs: Sequence[str | PurePath],
        chmod_dirs: Sequence[str | PurePath] | None = None,
    ) -> ExecResult:
        self._require_filesystem_ready()
        mapper = self._path_mapper()
        await self._run_filesystem(
            self._reset_native_dirs,
            [mapper.translate(path) for path in remove_dirs],
            [mapper.translate(path) for path in create_dirs],
            [mapper.translate(path) for path in (chmod_dirs or ())],
        )
        return ExecResult(return_code=0)

    def _reset_native_dirs(
        self, remove: Sequence[Path], create: Sequence[Path], chmod: Sequence[Path]
    ) -> None:
        for path in remove:
            self._remove_native_path(path)
        for native in create:
            native.mkdir(parents=True, exist_ok=True)
        for path in chmod:
            self._chmod_directory(path, chmod=True)

    async def is_dir(self, path: str, user: str | int | None = None) -> bool:
        self._require_filesystem_ready()
        self._validate_user(user)
        native = self._translate_path(path)
        return await self._run_filesystem(
            lambda: native.is_dir() and not _is_native_link(native)
        )

    async def is_file(self, path: str, user: str | int | None = None) -> bool:
        self._require_filesystem_ready()
        self._validate_user(user)
        native = self._translate_path(path)
        return await self._run_filesystem(
            lambda: native.is_file() and not _is_native_link(native)
        )

    def _translate_path(self, value: str | Path) -> Path:
        return self._path_mapper().translate(value)

    def _path_mapper(self) -> HostPathMapper:
        return HostPathMapper(
            host_os=self.os,
            mappings=self._runtime_dirs(),
            task_workdir=self._task_workdir,
        )

    @property
    def path_mapper(self) -> HostPathMapper:
        """Return the current native path mapper after successful startup."""

        if not self._started:
            raise RuntimeError("HostEnvironment has not started")
        self._require_filesystem_access()
        return self._path_mapper()

    def _translate_command(self, command: str) -> str:
        return self._process_adapter.translate_command(command, self._runtime_dirs())

    def _translate_env(self, env: dict[str, str] | None) -> dict[str, str]:
        return self._path_mapper().translate_environment(env or {})

    def _effective_runtime_config(
        self,
        *,
        workdir: Path,
        requested_config: str | None,
    ) -> EffectiveRuntimeConfig:
        harness = None
        verifier = None
        agent_logs = None
        if requested_config:
            requested_path = self._translate_path(requested_config)
            requested = load_effective_runtime_config(requested_path)
            harness = requested.harness
            verifier = requested.verifier
            agent_logs = self._translate_path(requested.paths.agent_logs)
        paths = self._runtime_dirs()
        workspace = self._workspace.path if self._workspace is not None else None
        root = (
            self._workdir_root
            if self._workspace is not None and self._workspace.owned
            else None
        )
        return EffectiveRuntimeConfig(
            paths=RuntimePaths(
                workdir=str(workdir),
                tests=str(paths[_VIRTUAL_TESTS]),
                agent_logs=str(agent_logs or paths[_VIRTUAL_AGENT_LOGS]),
                verifier_logs=str(paths[_VIRTUAL_VERIFIER_LOGS]),
                artifacts=str(paths[_VIRTUAL_ARTIFACTS]),
            ),
            workdir_root=str(root) if root is not None else None,
            workspace=str(workspace) if workspace is not None else None,
            python=sys.executable,
            harness=harness,
            verifier=verifier,
        )

    def _write_runtime_config(self, config: EffectiveRuntimeConfig) -> Path:
        if self._runtime_root is None:
            raise RuntimeError("HostEnvironment has not started")
        directory = self._runtime_root / "configs" / uuid4().hex
        return write_effective_runtime_config(directory / "peval.json", config)

    def runtime_directory(self, name: str) -> Path:
        """Return owned neutral storage outside the Task workspace and Job paths."""
        self._require_filesystem_ready()
        if not name or re.fullmatch(r"[A-Za-z0-9_-]+", name) is None:
            raise ValueError("runtime directory name must be one plain component")
        assert self._runtime_root is not None
        path = self._runtime_root / "state" / name
        if any(
            _is_native_link(part) for part in (self._runtime_root, path.parent, path)
        ):
            raise ValueError("runtime directory traverses a link or junction")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def runtime_config_env(
        self, *, verifier: VerifierInvocation | None = None
    ) -> dict[str, str]:
        """Explicitly supply path configuration to a trusted control process."""
        self._require_filesystem_ready()
        config = self._effective_runtime_config(
            workdir=self._translate_path(self._task_workdir), requested_config=None
        )
        config = replace(config, verifier=verifier)
        return {PEVAL_CONFIG_ENV: str(self._write_runtime_config(config))}

    async def upload_file(self, source_path: Path | str, target_path: str):
        self._require_filesystem_ready()
        source = Path(source_path)
        target = self._translate_path(target_path)
        await self._run_filesystem(_copy_native_file, source, target, cancellable=True)

    async def upload_dir(self, source_dir: Path | str, target_dir: str):
        self._require_filesystem_ready()
        source = Path(source_dir)
        target = self._translate_path(target_dir)
        await self._run_filesystem(
            self._download_native_dir, source, target, [], cancellable=True
        )

    async def download_file(self, source_path: str, target_path: Path | str):
        self._require_filesystem_ready()
        source = self._translate_path(source_path)
        target = Path(target_path)
        await self._run_filesystem(_copy_native_file, source, target, cancellable=True)

    async def download_dir(self, source_dir: str, target_dir: Path | str):
        await self.download_dir_with_exclusions(
            source_dir=source_dir, target_dir=target_dir, exclude=[]
        )

    def _native_download_entries(
        self,
        source: Path,
        *,
        exclude: Sequence[str] = (),
        cancel: threading.Event | None = None,
    ) -> Iterator[tuple[Path, os.stat_result | None]]:
        """Visit files incrementally and directories after their children."""
        pending = [(source, False)]
        skipped_links = 0
        try:
            while pending:
                _check_filesystem_cancel(cancel)
                current, visited = pending.pop()
                if visited:
                    yield current, None
                    continue
                pending.append((current, True))
                # Close each directory's scan before descending into its children.
                with os.scandir(current) as entries:
                    for entry in entries:
                        _check_filesystem_cancel(cancel)
                        info = entry.stat(follow_symlinks=False)
                        path = Path(entry.path)
                        if self._matches_download_exclusion(
                            path.relative_to(source).as_posix(), exclude
                        ):
                            continue
                        if _is_link_info(info):
                            skipped_links += 1
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            pending.append((path, False))
                        else:
                            yield path, info
        finally:
            if skipped_links:
                self.logger.warning(
                    "Directory transfer omitted %d linked entries in %s",
                    skipped_links,
                    source,
                )

    async def download_dir_with_exclusions(
        self,
        *,
        source_dir: str,
        target_dir: Path | str,
        exclude: list[str],
    ) -> None:
        self._require_filesystem_ready()
        source = self._translate_path(source_dir)
        await self._run_filesystem(
            self._download_native_dir,
            source,
            Path(target_dir),
            exclude,
            cancellable=True,
        )

    def _download_native_dir(
        self,
        source: Path,
        target: Path,
        exclude: Sequence[str],
        *,
        cancel: threading.Event | None = None,
    ) -> None:
        self._validate_native_download_directory(source, target)
        target.mkdir(parents=True, exist_ok=True)
        for path, info in self._native_download_entries(
            source, exclude=exclude, cancel=cancel
        ):
            destination = target / path.relative_to(source)
            if info is None:
                destination.mkdir(parents=True, exist_ok=True)
                if not os.path.samefile(path, destination):
                    shutil.copystat(path, destination)
            else:
                _copy_native_file(path, destination, cancel=cancel)

    @staticmethod
    def _validate_native_download_directory(source: Path, target: Path) -> None:
        if _is_native_link(source) or not source.is_dir():
            raise NotADirectoryError(source)
        resolved_source, resolved_target = source.resolve(), target.resolve()
        if resolved_target != resolved_source and resolved_target.is_relative_to(
            resolved_source
        ):
            raise ValueError("download target cannot be inside its source directory")

    @staticmethod
    def _matches_download_exclusion(relative: str, patterns: Sequence[str]) -> bool:
        return any(
            fnmatch.fnmatch(relative, pattern)
            or fnmatch.fnmatch(Path(relative).name, pattern)
            for pattern in patterns
        )

    async def download_dir_filtered(
        self,
        *,
        source_dir: str,
        target_dir: Path | str,
        include: Sequence[str] | None = None,
        exclude: Sequence[str] | None = None,
        protect: Sequence[str] | None = None,
    ) -> None:
        self._require_filesystem_ready()
        source = self._translate_path(source_dir)
        await self._run_filesystem(
            self._download_native_dir_filtered,
            source,
            Path(target_dir),
            include=include,
            exclude=exclude,
            protect=protect,
            cancellable=True,
        )

    def _download_native_dir_filtered(
        self,
        source: Path,
        target: Path,
        *,
        include: Sequence[str] | None,
        exclude: Sequence[str] | None,
        protect: Sequence[str] | None,
        cancel: threading.Event | None = None,
    ) -> None:
        self._validate_native_download_directory(source, target)
        target.mkdir(parents=True, exist_ok=True)
        protected = set(protect or ())  # Harbor protect entries are exact paths.
        copied = False
        for path, info in self._native_download_entries(source, cancel=cancel):
            if info is None or not stat.S_ISREG(info.st_mode):
                continue
            relative = path.relative_to(source).as_posix()
            if relative not in protected:
                if include and not any(fnmatch.fnmatch(relative, p) for p in include):
                    continue
                if exclude and any(fnmatch.fnmatch(relative, p) for p in exclude):
                    continue
            _copy_native_file(path, target / path.relative_to(source), cancel=cancel)
            copied = True
        if not copied:
            self.logger.warning(
                f"No files in {str(source)!r} matched include={include} "
                f"exclude={exclude}; downloading nothing"
            )

    def _validate_user(self, user: str | int | None) -> None:
        resolved = self._resolve_user(user)
        self._process_adapter.validate_user(resolved)

    async def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: float | None = None,
        user: str | int | None = None,
    ) -> ExecResult:
        return await self._exec_process(
            command, cwd=cwd, env=env, timeout_sec=timeout_sec, user=user
        )

    def native_path(self, value: str | Path) -> Path:
        """Resolve an environment path to its native host path after start."""
        if not self._started:
            raise RuntimeError("HostEnvironment has not started")
        self._require_filesystem_access()
        return self._translate_path(value)

    @property
    def work_dir(self) -> Path:
        """The native Task working directory after successful startup."""
        return self.native_path(".")

    async def exec_argv(
        self,
        argv: Sequence[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: float | None = None,
        user: str | int | None = None,
    ) -> ExecResult:
        """Execute literal argv/per-call env; map declared environment paths."""
        if (
            isinstance(argv, (str, bytes))
            or not argv
            or any(not isinstance(arg, str) or "\x00" in arg for arg in argv)
            or not argv[0]
        ):
            raise ValueError(
                "HostEnvironment argv must contain an executable and NUL-free string arguments"
            )
        return await self._exec_process(
            argv, cwd=cwd, env=env, timeout_sec=timeout_sec, user=user
        )

    async def _spawn_process(
        self,
        command: str | Sequence[str],
        *,
        cwd: str | None,
        env: dict[str, str] | None,
        user: str | int | None,
        initializing: bool = False,
    ) -> asyncio.subprocess.Process:
        self._validate_user(user)
        effective_cwd = self._task_workdir if cwd is None else cwd
        translated_cwd = self._translate_path(effective_cwd)
        translated_cwd.mkdir(parents=True, exist_ok=True)
        merged_env = dict(self._merge_env(env) or {})
        requested_config = merged_env.pop(PEVAL_CONFIG_ENV, None)
        merged_env = {
            key: value
            for key, value in merged_env.items()
            if not key.startswith(_LEGACY_RUNTIME_ENV_PREFIX)
        }
        runtime_config_path = None
        if requested_config:
            runtime_config = self._effective_runtime_config(
                workdir=translated_cwd, requested_config=requested_config
            )
            runtime_config_path = await _await_owned_task(
                asyncio.create_task(
                    asyncio.to_thread(self._write_runtime_config, runtime_config)
                )
            )
        process_env = {
            key: value
            for key, value in os.environ.items()
            if key != PEVAL_CONFIG_ENV
            and not key.startswith(_LEGACY_RUNTIME_ENV_PREFIX)
        }
        if "HOME" in merged_env and "NVM_DIR" not in merged_env:
            process_env.pop("NVM_DIR", None)
        literal_keys = set(env or {}) if not isinstance(command, str) else set()
        # Harbor scopes override per-call values, so their paths remain logical.
        for scoped_env in self._exec_env_overlays.get():
            literal_keys.difference_update(scoped_env)
        process_env.update(
            self._translate_env(
                {
                    key: value
                    for key, value in merged_env.items()
                    if key not in literal_keys
                }
            )
        )
        process_env.update(
            {key: value for key, value in merged_env.items() if key in literal_keys}
        )
        python_dir = str(Path(sys.executable).parent)
        inherited_path = process_env.get("PATH", "")
        process_env["PATH"] = (
            python_dir
            if not inherited_path
            else python_dir + os.pathsep + inherited_path
        )
        if runtime_config_path is not None:
            process_env[PEVAL_CONFIG_ENV] = str(runtime_config_path)
        if initializing:
            process_env = {
                key: value
                for key, value in process_env.items()
                if not key.upper().startswith("PEVAL_JUDGE_")
            }
        argv = (
            self._process_adapter.shell_argv(self._translate_command(command))
            if isinstance(command, str)
            else command
        )
        return await self._process_adapter.spawn(
            argv,
            cwd=translated_cwd,
            env=process_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def _exec_process(
        self,
        command: str | Sequence[str],
        *,
        cwd: str | None,
        env: dict[str, str] | None,
        timeout_sec: float | None,
        user: str | int | None,
        initializing: bool = False,
    ) -> ExecResult:
        self._require_process_access()
        # Fail promptly during startup/stop, then recheck after waiting for the lock.
        self._require_command_ready(initializing=initializing)
        async with self._launch_lock:
            self._require_command_ready(initializing=initializing)
            process = await self._spawn_process(
                command, cwd=cwd, env=env, user=user, initializing=initializing
            )
            done = asyncio.get_running_loop().create_future()
            self._active_processes[process] = done
        callback = self._output_callback()
        output_bytes = 0

        async def read_stream(
            stream: asyncio.StreamReader | None, stream_name: OutputStream
        ) -> str:
            nonlocal output_bytes
            if stream is None:
                return ""
            chunks: list[str] = []
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            token = self._callback_command.set(done)
            try:
                while chunk := await stream.read(4096):
                    output_bytes += len(chunk)
                    if initializing and output_bytes > _PREPARATION_OUTPUT_LIMIT:
                        raise RuntimeError("Task preparation output exceeds 8 MiB")
                    text = decoder.decode(chunk)
                    chunks.append(text)
                    if callback is not None:
                        await callback(text, stream_name)
                tail = decoder.decode(b"", final=True)
                chunks.append(tail)
                if tail and callback is not None:
                    await callback(tail, stream_name)
                return "".join(chunks)
            finally:
                self._callback_command.reset(token)

        stdout_task = asyncio.create_task(read_stream(process.stdout, "stdout"))
        stderr_task = asyncio.create_task(read_stream(process.stderr, "stderr"))
        command_error: BaseException | None = None
        try:
            async with asyncio.timeout(timeout_sec):
                _, stdout, stderr = await asyncio.gather(
                    process.wait(), stdout_task, stderr_task
                )
        except BaseException as error:
            command_error = error

            async def cleanup(primary_error: BaseException):
                stdout_task.cancel()
                stderr_task.cancel()
                await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
                outcomes = await asyncio.gather(
                    self._terminate_process(process),
                    process.communicate(),
                    return_exceptions=True,
                )
                for outcome in outcomes:
                    if isinstance(outcome, BaseException):
                        primary_error.add_note(
                            f"command cleanup failed: {type(outcome).__name__}: {outcome}"
                        )

            try:
                await _await_owned_task(asyncio.create_task(cleanup(error)))
            except BaseException as cleanup_error:
                error.add_note(
                    "command cleanup interrupted: "
                    f"{type(cleanup_error).__name__}: {cleanup_error}"
                )
            raise
        finally:
            try:
                self._process_adapter.release(process)
            except BaseException as release_error:
                if command_error is None:
                    raise
                command_error.add_note(
                    "process release failed: "
                    f"{type(release_error).__name__}: {release_error}"
                )
            finally:
                self._active_processes.pop(process, None)
                if not done.done():
                    done.set_result(None)
        return ExecResult(
            stdout=stdout,
            stderr=stderr,
            return_code=process.returncode if process.returncode is not None else 1,
        )

    def _require_command_ready(self, *, initializing: bool = False) -> None:
        if initializing:
            if asyncio.current_task() is not self._initialization_task:
                raise RuntimeError("startup commands require the initialization task")
            _check_filesystem_cancel(self._initialization_cancel)
            return
        if not self._started:
            raise RuntimeError("HostEnvironment has not started")
        if self._stopping:
            raise RuntimeError("HostEnvironment is stopping")

    async def _terminate_process(self, process: asyncio.subprocess.Process) -> None:
        await self._process_adapter.terminate(process)
