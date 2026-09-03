from __future__ import annotations

import asyncio
import getpass
import hashlib
import os
import platform
import re
import secrets
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path, PurePath, PurePosixPath
from uuid import uuid4

import yaml
from harbor.environments.base import BaseEnvironment, ExecResult, OutputStream
from harbor.environments.capabilities import EnvironmentCapabilities
from harbor.models.task.config import TaskOS
from harbor.utils.scripts import quote_windows_shell_arg

from psycheval.harbor.runtime_config import (
    PEVAL_CONFIG_ENV,
    EffectiveRuntimeConfig,
    HostSettings,
    RuntimePaths,
    load_effective_runtime_config,
    load_host_settings,
    write_effective_runtime_config,
)

_VIRTUAL_WORKDIR = "/app"
_WORKBUDDY_VIRTUAL_WORKDIR = "/workspace"
_VIRTUAL_TESTS = "/tests"
_VIRTUAL_SOLUTION = "/solution"
_VIRTUAL_LOGS = "/logs"
_VIRTUAL_AGENT_LOGS = "/logs/agent"
_VIRTUAL_VERIFIER_LOGS = "/logs/verifier"
_VIRTUAL_ARTIFACTS = "/logs/artifacts"
_VIRTUAL_ROOTS = (
    _VIRTUAL_VERIFIER_LOGS,
    _VIRTUAL_ARTIFACTS,
    _VIRTUAL_AGENT_LOGS,
    _VIRTUAL_SOLUTION,
    _VIRTUAL_WORKDIR,
    _VIRTUAL_TESTS,
    _VIRTUAL_LOGS,
)
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")
_WORKSPACE_RESERVED_ROOTS = (
    _VIRTUAL_LOGS,
    _VIRTUAL_TESTS,
    _VIRTUAL_SOLUTION,
)
_SHORTUUID_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_SHORTUUID_LENGTH = 7
_LEGACY_RUNTIME_ENV_PREFIX = "PSYCHEVAL_"
_WORKBUDDY_COMPOSE_METADATA = {
    "services": {
        "main": {"extra_hosts": ["host.docker.internal:host-gateway"]},
    },
}
_WORKBUDDY_COMPOSE_LIMIT = 64 * 1024
_WORKBUDDY_ARCHIVE_FILE_LIMIT = 64 * 1024 * 1024
_WORKBUDDY_ARCHIVE_TOTAL_LIMIT = 256 * 1024 * 1024
_WORKBUDDY_ARCHIVE_ENTRY_LIMIT = 100_000


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


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
def _open_workbuddy_archive(archive: Path) -> Iterator[tarfile.TarFile]:
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


def _extract_workbuddy_workspace(archive: Path, destination: Path) -> None:
    total = 0
    seen: dict[PurePosixPath, tuple[str, int, int, bytes]] = {}
    try:
        with _open_workbuddy_archive(archive) as stream:
            for index, member in enumerate(stream, start=1):
                if index > _WORKBUDDY_ARCHIVE_ENTRY_LIMIT:
                    raise ValueError(
                        "WorkBuddy workspace archive exceeds 100000 entries"
                    )
                relative = PurePosixPath(member.name)
                if (
                    relative.is_absolute()
                    or "\\" in member.name
                    or not relative.parts
                    or any(part in {"", ".", ".."} for part in relative.parts)
                    or ".git" in relative.parts
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
                target.write_bytes(content)
                target.chmod(member.mode & 0o777)
    except (OSError, tarfile.TarError) as exc:
        raise ValueError("WorkBuddy workspace archive cannot be extracted") from exc


def _initialize_workbuddy_git(workspace: Path) -> None:
    commands = (
        ("init", "-q", "-b", "main"),
        ("config", "user.email", "dev@project"),
        ("config", "user.name", "Developer"),
        ("add", "-A"),
        ("commit", "--no-verify", "-q", "-m", "initial setup"),
    )
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    for arguments in commands:
        try:
            result = subprocess.run(
                [
                    "git",
                    "-c",
                    "core.hooksPath=/dev/null",
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
                "WorkBuddy host bootstrap could not create its Git baseline"
            ) from exc
        if result.returncode != 0:
            diagnostic = (result.stderr or result.stdout).strip()
            raise ValueError(
                "WorkBuddy host bootstrap could not create its Git baseline"
                + (f": {diagnostic}" if diagnostic else "")
            )


def _split_virtual_path(
    value: str,
    host_os: TaskOS,
    virtual_roots: Sequence[str] = _VIRTUAL_ROOTS,
) -> tuple[str, tuple[str, ...]] | None:
    normalized = value.replace("\\", "/") if host_os == TaskOS.WINDOWS else value
    for virtual in sorted(set(virtual_roots), key=len, reverse=True):
        aliases = (virtual, f"C:{virtual}") if host_os == TaskOS.WINDOWS else (virtual,)
        for alias in aliases:
            windows_alias = alias.startswith("C:")
            candidate = normalized.lower() if windows_alias else normalized
            alias_comparison = alias.lower() if windows_alias else alias
            if candidate == alias_comparison:
                return virtual, ()
            prefix = f"{alias_comparison}/"
            if candidate.startswith(prefix):
                suffix = normalized[len(alias) + 1 :]
                parts = PurePosixPath(suffix).parts
                if ".." in parts:
                    raise ValueError(f"unsupported HostEnvironment path: {value}")
                return virtual, tuple(part for part in parts if part != ".")
    return None


def _translate_literal(
    value: str, mappings: dict[str, Path], host_os: TaskOS
) -> str | None:
    match = _split_virtual_path(value, host_os, tuple(mappings))
    if match is None:
        return None
    virtual, suffix = match
    return str(mappings[virtual].joinpath(*suffix))


def _translate_posix_command(command: str, mappings: dict[str, Path]) -> str:
    ordered_mappings = sorted(
        mappings.items(), key=lambda item: len(item[0]), reverse=True
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
        translated_literal = _translate_literal(content, mappings, TaskOS.LINUX)
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


def _translate_windows_command(command: str, mappings: dict[str, Path]) -> str:
    aliases = sorted(
        {
            alias
            for virtual in mappings
            for alias in (
                virtual,
                f"C:{virtual}",
                f"C:{virtual}".replace("/", "\\"),
            )
        },
        key=len,
        reverse=True,
    )
    alias_pattern = "|".join(re.escape(alias) for alias in aliases)
    path_pattern = re.compile(
        rf"(?<![A-Za-z0-9_:/\\.-])"
        rf"(?P<path>(?:{alias_pattern})(?:[/\\][^\s;|&()<>\"']*)?)"
        rf"(?=$|[\s;|&()<>])",
        flags=re.IGNORECASE,
    )

    def translate_unquoted(value: str) -> str:
        def replacement(match: re.Match[str]) -> str:
            translated = _translate_literal(
                match.group("path"), mappings, TaskOS.WINDOWS
            )
            if translated is None:
                return match.group(0)
            return quote_windows_shell_arg(translated)

        return path_pattern.sub(replacement, value)

    pieces: list[str] = []
    unquoted_start = 0
    index = 0
    while index < len(command):
        if command[index] != '"':
            index += 1
            continue
        pieces.append(translate_unquoted(command[unquoted_start:index]))
        end = command.find('"', index + 1)
        if end < 0:
            pieces.append(command[index:])
            return "".join(pieces)
        content = command[index + 1 : end]
        translated_literal = _translate_literal(content, mappings, TaskOS.WINDOWS)
        if translated_literal is None:
            pieces.append(command[index : end + 1])
        else:
            pieces.append(quote_windows_shell_arg(translated_literal))
        index = end + 1
        unquoted_start = index
    pieces.append(translate_unquoted(command[unquoted_start:]))
    return "".join(pieces)


def _canonical_virtual_path(value: str, host_os: TaskOS, *, label: str) -> str:
    if "\x00" in value:
        raise ValueError(f"{label} contains NUL")
    normalized = value.replace("\\", "/") if host_os == TaskOS.WINDOWS else value
    if host_os == TaskOS.WINDOWS and _WINDOWS_ABSOLUTE.match(normalized):
        if normalized[0].lower() != "c":
            raise ValueError(f"{label} must use the C: environment drive")
        normalized = normalized[2:]
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


class _HostProcessAdapter:
    os: TaskOS

    def translate_command(self, command: str, mappings: dict[str, Path]) -> str:
        raise NotImplementedError

    def shell_argv(self, command: str) -> tuple[str, ...]:
        raise NotImplementedError

    def process_kwargs(self) -> dict[str, object]:
        raise NotImplementedError

    def validate_user(self, resolved_user: str | int | None) -> None:
        raise NotImplementedError

    async def terminate(self, process: asyncio.subprocess.Process) -> None:
        raise NotImplementedError


class _LinuxProcessAdapter(_HostProcessAdapter):
    os = TaskOS.LINUX

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
        if process.returncode is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
            return
        except asyncio.TimeoutError:
            pass
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        await process.wait()


class _WindowsProcessAdapter(_HostProcessAdapter):
    os = TaskOS.WINDOWS

    def translate_command(self, command: str, mappings: dict[str, Path]) -> str:
        return _translate_windows_command(command, mappings)

    def shell_argv(self, command: str) -> tuple[str, ...]:
        shell_command = f'"{command}"' if command.lstrip().startswith('"') else command
        return (
            os.environ.get("COMSPEC", "cmd.exe"),
            "/D",
            "/S",
            "/C",
            shell_command,
        )

    def process_kwargs(self) -> dict[str, object]:
        return {
            "creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        }

    def validate_user(self, resolved_user: str | int | None) -> None:
        if resolved_user is not None:
            raise ValueError(
                "HostEnvironment on Windows does not support user switching; "
                f"received {resolved_user!r}"
            )

    async def terminate(self, process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        taskkill = await asyncio.create_subprocess_exec(
            "taskkill",
            "/PID",
            str(process.pid),
            "/T",
            "/F",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await taskkill.communicate()
        if process.returncode is not None:
            return
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()


class HostEnvironment(BaseEnvironment):
    """Run a trusted Harbor Task as native Linux or Windows host subprocesses."""

    def __init__(
        self,
        *args,
        allow_host_execution: object = False,
        bootstrap_workbuddy_workspace: object = False,
        **kwargs,
    ):
        if "workdir_root" in kwargs:
            raise ValueError(
                "HostEnvironment workdir_root is configured through PEVAL_CONFIG, "
                "not an Environment kwarg"
            )
        self._allow_host_execution = _truthy(allow_host_execution)
        self._bootstrap_workbuddy_workspace = _truthy(bootstrap_workbuddy_workspace)
        self._runtime_root: Path | None = None
        self._automatic_workspace: Path | None = None
        self._host_settings: HostSettings | None = None
        self._active_processes: set[asyncio.subprocess.Process] = set()
        self._task_workdir = _VIRTUAL_WORKDIR
        self._workspace_mount: tuple[str, Path] | None = None
        self._transient_workdirs: dict[str, Path] = {}
        host_system = platform.system()
        if host_system == "Linux":
            self._process_adapter: _HostProcessAdapter = _LinuxProcessAdapter()
        elif host_system == "Windows":
            self._process_adapter = _WindowsProcessAdapter()
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

    def _validate_definition(self) -> None:
        if not self._allow_host_execution:
            raise ValueError(
                "HostEnvironment executes trusted code without isolation; pass "
                "--environment-kwarg allow_host_execution=true to opt in"
            )
        self._host_settings = load_host_settings()
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
        compose_paths = tuple(
            path
            for path in (
                self.environment_dir / "docker-compose.yaml",
                self.environment_dir / "docker-compose.yml",
            )
            if os.path.lexists(path)
        )
        if compose_paths:
            if not self._bootstrap_workbuddy_workspace:
                raise ValueError(
                    "HostEnvironment does not support Docker Compose Tasks"
                )
            if len(compose_paths) != 1:
                raise ValueError("WorkBuddy Compose metadata is ambiguous")
            try:
                compose_bytes = _read_regular_nofollow(
                    compose_paths[0], max_bytes=_WORKBUDDY_COMPOSE_LIMIT
                )
                compose = yaml.safe_load(compose_bytes.decode("utf-8"))
            except (OSError, UnicodeError, yaml.YAMLError, ValueError) as exc:
                raise ValueError("WorkBuddy Compose metadata is not readable") from exc
            if compose != _WORKBUDDY_COMPOSE_METADATA:
                raise ValueError(
                    "HostEnvironment accepts only the inert WorkBuddy Compose metadata"
                )
        if self._bootstrap_workbuddy_workspace:
            archive = self.environment_dir / "workspace.tar.gz"
            try:
                archive_info = archive.stat(follow_symlinks=False)
            except OSError as exc:
                raise ValueError("WorkBuddy workspace archive is missing") from exc
            if not stat.S_ISREG(archive_info.st_mode):
                raise ValueError("WorkBuddy workspace archive must be a regular file")
        self._task_workdir = _canonical_virtual_path(
            (
                _WORKBUDDY_VIRTUAL_WORKDIR
                if self._bootstrap_workbuddy_workspace
                else self.task_env_config.workdir or _VIRTUAL_WORKDIR
            ),
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
        expected_mounts = {
            _VIRTUAL_AGENT_LOGS: self.trial_paths.agent_dir,
            _VIRTUAL_VERIFIER_LOGS: self.trial_paths.verifier_dir,
            _VIRTUAL_ARTIFACTS: (self.trial_paths.artifacts_dir / "logs" / "artifacts"),
        }
        managed_mounts: list[tuple[dict, str]] = []
        workspace_mounts: list[tuple[str, Path]] = []
        for mount in self._mounts:
            target = str(mount.get("target"))
            target_match = _split_virtual_path(target, self.os)
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
        if self._bootstrap_workbuddy_workspace and workspace_mounts:
            raise ValueError(
                "WorkBuddy host bootstrap does not accept an external workspace mount"
            )
        self._workspace_mount = workspace_mounts[0] if workspace_mounts else None
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
        if force_build:
            raise ValueError("HostEnvironment does not build Docker images")
        if self._runtime_root is not None:
            return
        self._runtime_root = Path(tempfile.mkdtemp(prefix="psycheval-harbor-"))
        try:
            self._prepare_automatic_workspace()
            if self.os == TaskOS.WINDOWS:
                quote_windows_shell_arg(sys.executable)
                for path in set(self._runtime_dirs().values()):
                    quote_windows_shell_arg(path)
            for path in set(self._runtime_dirs().values()):
                path.mkdir(parents=True, exist_ok=True)
            context_target = (
                self._runtime_dirs()[_VIRTUAL_TESTS]
                if self._is_separate_verifier()
                else self._translate_path(self._task_workdir)
            )
            environment_source = self.environment_dir.resolve()
            context_target = context_target.resolve()
            if self._bootstrap_workbuddy_workspace:
                await asyncio.to_thread(
                    _extract_workbuddy_workspace,
                    environment_source / "workspace.tar.gz",
                    context_target,
                )
                await asyncio.to_thread(_initialize_workbuddy_git, context_target)
            elif context_target != environment_source:
                if context_target.is_relative_to(environment_source):
                    raise ValueError(
                        "HostEnvironment workspace context target cannot be inside "
                        f"the Task environment directory: {str(context_target)!r}"
                    )
                shutil.copytree(
                    environment_source,
                    context_target,
                    dirs_exist_ok=True,
                )
        except Exception:
            self._delete_owned_runtime()
            raise

    def _prepare_automatic_workspace(self) -> None:
        if (
            self._host_settings is None
            or self._host_settings.workdir_root is None
            or self._workspace_mount is not None
            or self._is_separate_verifier()
        ):
            return
        root = self._host_settings.workdir_root
        root.mkdir(parents=True, exist_ok=True)
        if not root.is_dir():
            raise ValueError(
                f"HostEnvironment workdir_root is not a directory: {str(root)!r}"
            )
        workspace = root / self._trial_short_uuid()
        try:
            workspace.mkdir()
        except FileExistsError as exc:
            raise FileExistsError(
                "HostEnvironment automatic workspace already exists; refusing to "
                f"reuse stale state: {str(workspace)!r}"
            ) from exc
        self._automatic_workspace = workspace

    def _trial_short_uuid(self) -> str:
        trial_name = self.trial_paths.trial_dir.name
        candidate = trial_name.rsplit("__", 1)[-1]
        if len(candidate) == _SHORTUUID_LENGTH and all(
            char in _SHORTUUID_ALPHABET for char in candidate
        ):
            return candidate
        return "".join(
            secrets.choice(_SHORTUUID_ALPHABET) for _ in range(_SHORTUUID_LENGTH)
        )

    def _is_separate_verifier(self) -> bool:
        logical_targets = {
            match[0]
            for mount in self._mounts
            if mount.get("target")
            and (match := _split_virtual_path(str(mount["target"]), self.os))
            is not None
            and not match[1]
        }
        return (
            _VIRTUAL_VERIFIER_LOGS in logical_targets
            and _VIRTUAL_AGENT_LOGS not in logical_targets
        )

    async def stop(self, delete: bool):
        for process in list(self._active_processes):
            await self._terminate_process(process)
        if delete:
            self._delete_owned_runtime()

    def _delete_owned_runtime(self) -> None:
        errors: list[OSError] = []
        if self._automatic_workspace is not None:
            try:
                shutil.rmtree(self._automatic_workspace, ignore_errors=False)
            except OSError as exc:
                errors.append(exc)
            else:
                self._automatic_workspace = None
        if self._runtime_root is not None:
            try:
                shutil.rmtree(self._runtime_root, ignore_errors=False)
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
            target_match = _split_virtual_path(str(mount["target"]), self.os)
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
            _VIRTUAL_WORKDIR: (
                self._automatic_workspace
                if self._task_workdir == _VIRTUAL_WORKDIR
                and self._automatic_workspace is not None
                else self._runtime_root / "app"
            ),
            _VIRTUAL_TESTS: self._runtime_root / "tests",
            _VIRTUAL_SOLUTION: self._runtime_root / "solution",
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
            self._workspace_mount is not None
            and _same_or_descendant(self._task_workdir, self._workspace_mount[0])
        ):
            mappings[self._task_workdir] = (
                self._automatic_workspace
                if self._automatic_workspace is not None
                else self._transient_path(self._task_workdir)
            )
        if self._workspace_mount is not None:
            target, source = self._workspace_mount
            mappings[target] = source
        mappings.update(self._transient_workdirs)
        return mappings

    def _transient_path(self, virtual: str) -> Path:
        if self._runtime_root is None:
            raise RuntimeError("HostEnvironment has not started")
        parts = tuple(part for part in PurePosixPath(virtual).parts if part != "/")
        return self._runtime_root.joinpath("workdirs", *parts)

    def _register_workdir(
        self, value: str | PurePath, *, require_workspace: bool
    ) -> str:
        canonical = _canonical_virtual_path(
            str(value), self.os, label="HostEnvironment workdir"
        )
        if require_workspace and self._workspace_mount is not None:
            workspace_target = self._workspace_mount[0]
            if not _same_or_descendant(canonical, workspace_target):
                raise ValueError(
                    "HostEnvironment workdir must equal the workspace mount target "
                    f"or be its descendant: {workspace_target!r}"
                )
        mappings = self._runtime_dirs()
        if _split_virtual_path(canonical, self.os, tuple(mappings)) is None:
            self._transient_workdirs[canonical] = (
                self._automatic_workspace
                if require_workspace and self._automatic_workspace is not None
                else self._transient_path(canonical)
            )
        return canonical

    async def ensure_dirs(
        self,
        dirs: Sequence[str | PurePath],
        *,
        chmod: bool = True,
    ) -> ExecResult | None:
        for path in dirs:
            self._register_workdir(path, require_workspace=True)
        return await super().ensure_dirs(dirs, chmod=chmod)

    def _translate_path(self, value: str | Path) -> Path:
        raw = str(value)
        mappings = self._runtime_dirs()
        virtual_match = _split_virtual_path(raw, self.os, tuple(mappings))
        if virtual_match is not None:
            virtual, suffix = virtual_match
            return mappings[virtual].joinpath(*suffix)
        if raw.startswith("/") or (
            self.os == TaskOS.WINDOWS
            and (_WINDOWS_ABSOLUTE.match(raw) or raw.startswith("\\\\"))
        ):
            raise ValueError(f"unsupported HostEnvironment path: {raw}")
        relative = PurePosixPath(
            raw.replace("\\", "/") if self.os == TaskOS.WINDOWS else raw
        )
        if ".." in relative.parts:
            raise ValueError(f"unsupported HostEnvironment path: {raw}")
        return self._translate_path(self._task_workdir).joinpath(
            *(part for part in relative.parts if part != ".")
        )

    def _translate_command(self, command: str) -> str:
        return self._process_adapter.translate_command(command, self._runtime_dirs())

    def _translate_env(self, env: dict[str, str] | None) -> dict[str, str]:
        translated: dict[str, str] = {}
        for key, value in (env or {}).items():
            mapped = _translate_literal(value, self._runtime_dirs(), self.os)
            translated[key] = mapped if mapped is not None else value
        return translated

    def _effective_runtime_config(
        self,
        *,
        workdir: Path,
        requested_config: str | None,
    ) -> EffectiveRuntimeConfig:
        harness = None
        if requested_config:
            requested_path = self._translate_path(requested_config)
            harness = load_effective_runtime_config(requested_path).harness
        paths = self._runtime_dirs()
        workspace = (
            self._automatic_workspace
            if self._automatic_workspace is not None
            else self._workspace_mount[1]
            if self._workspace_mount is not None
            else None
        )
        root = self._host_settings.workdir_root if self._host_settings else None
        return EffectiveRuntimeConfig(
            paths=RuntimePaths(
                workdir=str(workdir),
                tests=str(paths[_VIRTUAL_TESTS]),
                agent_logs=str(paths[_VIRTUAL_AGENT_LOGS]),
                verifier_logs=str(paths[_VIRTUAL_VERIFIER_LOGS]),
                artifacts=str(paths[_VIRTUAL_ARTIFACTS]),
            ),
            workdir_root=str(root) if root is not None else None,
            workspace=str(workspace) if workspace is not None else None,
            python=sys.executable,
            harness=harness,
        )

    def _write_runtime_config(self, config: EffectiveRuntimeConfig) -> Path:
        if self._runtime_root is None:
            raise RuntimeError("HostEnvironment has not started")
        directory = self._runtime_root / "configs" / uuid4().hex
        return write_effective_runtime_config(directory / "peval.json", config)

    async def upload_file(self, source_path: Path | str, target_path: str):
        source = Path(source_path)
        target = self._translate_path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    async def upload_dir(self, source_dir: Path | str, target_dir: str):
        source = Path(source_dir)
        target = self._translate_path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)

    async def download_file(self, source_path: str, target_path: Path | str):
        source = self._translate_path(source_path)
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    async def download_dir(self, source_dir: str, target_dir: Path | str):
        source = self._translate_path(source_dir)
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, dirs_exist_ok=True)

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
        self._validate_user(user)
        effective_cwd = self._task_workdir if cwd is None else cwd
        if cwd is not None:
            self._register_workdir(cwd, require_workspace=False)
        translated_cwd = self._translate_path(effective_cwd)
        translated_cwd.mkdir(parents=True, exist_ok=True)
        translated_command = self._translate_command(command)
        merged_env = dict(self._merge_env(env) or {})
        requested_config = merged_env.pop(PEVAL_CONFIG_ENV, None)
        merged_env = {
            key: value
            for key, value in merged_env.items()
            if not key.startswith(_LEGACY_RUNTIME_ENV_PREFIX)
        }
        runtime_config = self._effective_runtime_config(
            workdir=translated_cwd,
            requested_config=requested_config,
        )
        runtime_config_path = self._write_runtime_config(runtime_config)
        process_env = {
            key: value
            for key, value in os.environ.items()
            if key != PEVAL_CONFIG_ENV
            and not key.startswith(_LEGACY_RUNTIME_ENV_PREFIX)
        }
        if "HOME" in merged_env and "NVM_DIR" not in merged_env:
            process_env.pop("NVM_DIR", None)
        process_env.update(self._translate_env(merged_env))
        python_dir = str(Path(sys.executable).parent)
        inherited_path = process_env.get("PATH", "")
        process_env["PATH"] = (
            python_dir
            if not inherited_path
            else python_dir + os.pathsep + inherited_path
        )
        process_env[PEVAL_CONFIG_ENV] = str(runtime_config_path)
        process = await asyncio.create_subprocess_exec(
            *self._process_adapter.shell_argv(translated_command),
            cwd=translated_cwd,
            env=process_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **self._process_adapter.process_kwargs(),
        )
        self._active_processes.add(process)
        callback = self._output_callback()

        async def read_stream(
            stream: asyncio.StreamReader | None, stream_name: OutputStream
        ) -> str:
            if stream is None:
                return ""
            chunks: list[str] = []
            while chunk := await stream.read(4096):
                text = chunk.decode("utf-8", errors="replace")
                chunks.append(text)
                if callback is not None:
                    await callback(text, stream_name)
            return "".join(chunks)

        stdout_task = asyncio.create_task(read_stream(process.stdout, "stdout"))
        stderr_task = asyncio.create_task(read_stream(process.stderr, "stderr"))
        try:
            await asyncio.wait_for(process.wait(), timeout=timeout_sec)
            stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            await self._terminate_process(process)
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            raise
        finally:
            self._active_processes.discard(process)
        return ExecResult(
            stdout=stdout,
            stderr=stderr,
            return_code=process.returncode if process.returncode is not None else 1,
        )

    async def _terminate_process(self, process: asyncio.subprocess.Process) -> None:
        await self._process_adapter.terminate(process)
