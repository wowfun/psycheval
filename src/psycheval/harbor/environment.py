from __future__ import annotations

import asyncio
import getpass
import os
import platform
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

from harbor.environments.base import BaseEnvironment, ExecResult, OutputStream
from harbor.environments.capabilities import EnvironmentCapabilities
from harbor.models.task.config import TaskOS
from harbor.utils.scripts import quote_windows_shell_arg

_VIRTUAL_WORKDIR = "/app"
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


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _split_virtual_path(
    value: str, host_os: TaskOS
) -> tuple[str, tuple[str, ...]] | None:
    normalized = value.replace("\\", "/") if host_os == TaskOS.WINDOWS else value
    for virtual in _VIRTUAL_ROOTS:
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
    match = _split_virtual_path(value, host_os)
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
            for virtual in _VIRTUAL_ROOTS
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

    def __init__(self, *args, allow_host_execution: object = False, **kwargs):
        self._allow_host_execution = _truthy(allow_host_execution)
        self._runtime_root: Path | None = None
        self._active_processes: set[asyncio.subprocess.Process] = set()
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
        if (self.environment_dir / "docker-compose.yaml").exists() or (
            self.environment_dir / "docker-compose.yml"
        ).exists():
            raise ValueError("HostEnvironment does not support Docker Compose Tasks")
        workdir_match = (
            _split_virtual_path(self.task_env_config.workdir, self.os)
            if self.task_env_config.workdir is not None
            else (_VIRTUAL_WORKDIR, ())
        )
        if workdir_match != (_VIRTUAL_WORKDIR, ()):
            raise ValueError("HostEnvironment requires [environment].workdir = '/app'")
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
        normalized_mounts: list[tuple[dict, str | None]] = []
        for mount in self._mounts:
            target = str(mount.get("target"))
            target_match = _split_virtual_path(target, self.os)
            logical_target = (
                target_match[0]
                if target_match is not None and not target_match[1]
                else None
            )
            normalized_mounts.append((mount, logical_target))
        unsupported_mounts = sorted(
            str(mount.get("target"))
            for mount, logical_target in normalized_mounts
            if logical_target not in expected_mounts
        )
        if unsupported_mounts:
            raise ValueError(
                "HostEnvironment does not support extra mounts: "
                + ", ".join(unsupported_mounts)
            )
        seen_targets: set[str] = set()
        for mount, logical_target in normalized_mounts:
            assert logical_target is not None
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
        if self.os == TaskOS.WINDOWS:
            quote_windows_shell_arg(sys.executable)
            for path in self._runtime_dirs().values():
                quote_windows_shell_arg(path)
        for path in self._runtime_dirs().values():
            path.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            self.environment_dir,
            self._runtime_dirs()[_VIRTUAL_WORKDIR],
            dirs_exist_ok=True,
        )

    async def stop(self, delete: bool):
        for process in list(self._active_processes):
            await self._terminate_process(process)
        if delete and self._runtime_root is not None:
            shutil.rmtree(self._runtime_root)
            self._runtime_root = None

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
        return {
            _VIRTUAL_WORKDIR: self._runtime_root / "app",
            _VIRTUAL_TESTS: self._runtime_root / "tests",
            _VIRTUAL_SOLUTION: self._runtime_root / "solution",
            _VIRTUAL_LOGS: self._runtime_root / "logs",
            _VIRTUAL_AGENT_LOGS: mounted.get(
                _VIRTUAL_AGENT_LOGS, self.trial_paths.agent_dir
            ),
            _VIRTUAL_VERIFIER_LOGS: mounted.get(
                _VIRTUAL_VERIFIER_LOGS, self.trial_paths.verifier_dir
            ),
            _VIRTUAL_ARTIFACTS: mounted.get(
                _VIRTUAL_ARTIFACTS,
                self.trial_paths.artifacts_dir / "logs" / "artifacts",
            ),
        }

    def _translate_path(self, value: str | Path) -> Path:
        raw = str(value)
        mappings = self._runtime_dirs()
        virtual_match = _split_virtual_path(raw, self.os)
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
        return mappings[_VIRTUAL_WORKDIR].joinpath(
            *(part for part in relative.parts if part != ".")
        )

    def _translate_command(self, command: str) -> str:
        return self._process_adapter.translate_command(command, self._runtime_dirs())

    def _portable_env(self) -> dict[str, str]:
        paths = self._runtime_dirs()
        return {
            "PSYCHEVAL_WORKDIR": str(paths[_VIRTUAL_WORKDIR]),
            "PSYCHEVAL_TESTS_DIR": str(paths[_VIRTUAL_TESTS]),
            "PSYCHEVAL_AGENT_LOGS_DIR": str(paths[_VIRTUAL_AGENT_LOGS]),
            "PSYCHEVAL_VERIFIER_LOGS_DIR": str(paths[_VIRTUAL_VERIFIER_LOGS]),
            "PSYCHEVAL_ARTIFACTS_DIR": str(paths[_VIRTUAL_ARTIFACTS]),
            "PSYCHEVAL_HARBOR_PYTHON": sys.executable,
        }

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
        translated_command = self._translate_command(command)
        translated_cwd = (
            self._translate_path(cwd)
            if cwd is not None
            else self._runtime_dirs()[_VIRTUAL_WORKDIR]
        )
        translated_cwd.mkdir(parents=True, exist_ok=True)
        process_env = dict(os.environ)
        process_env.update(self._merge_env(env) or {})
        process_env.update(self._portable_env())
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
