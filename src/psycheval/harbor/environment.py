from __future__ import annotations

import asyncio
import getpass
import os
import platform
import re
import shlex
import shutil
import signal
import sys
import tempfile
from pathlib import Path

from harbor.environments.base import BaseEnvironment, ExecResult, OutputStream
from harbor.environments.capabilities import EnvironmentCapabilities
from harbor.models.task.config import TaskOS

_VIRTUAL_WORKDIR = "/app"
_VIRTUAL_TESTS = "/tests"
_VIRTUAL_SOLUTION = "/solution"
_VIRTUAL_LOGS = "/logs"
_VIRTUAL_AGENT_LOGS = "/logs/agent"
_VIRTUAL_VERIFIER_LOGS = "/logs/verifier"
_VIRTUAL_ARTIFACTS = "/logs/artifacts"


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


class HostEnvironment(BaseEnvironment):
    """Run a trusted Harbor Task as ordinary Linux host subprocesses."""

    def __init__(self, *args, allow_host_execution: object = False, **kwargs):
        self._allow_host_execution = _truthy(allow_host_execution)
        self._runtime_root: Path | None = None
        self._active_processes: set[asyncio.subprocess.Process] = set()
        super().__init__(*args, **kwargs)

    @staticmethod
    def type() -> str:
        return "psycheval-host"

    @property
    def capabilities(self) -> EnvironmentCapabilities:
        return EnvironmentCapabilities(mounted=True)

    def _validate_definition(self) -> None:
        if not self._allow_host_execution:
            raise ValueError(
                "HostEnvironment executes trusted code without isolation; pass "
                "--environment-kwarg allow_host_execution=true to opt in"
            )
        if platform.system() != "Linux":
            raise RuntimeError("HostEnvironment supports Linux hosts only")
        if self.task_env_config.os != TaskOS.LINUX:
            raise RuntimeError("HostEnvironment supports Linux Tasks only")
        if not self.environment_dir.is_dir():
            raise FileNotFoundError(
                f"Task environment directory not found: {self.environment_dir}"
            )
        if (self.environment_dir / "docker-compose.yaml").exists() or (
            self.environment_dir / "docker-compose.yml"
        ).exists():
            raise ValueError("HostEnvironment does not support Docker Compose Tasks")
        if self.task_env_config.workdir not in {None, _VIRTUAL_WORKDIR}:
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
        unsupported_mounts = sorted(
            str(mount.get("target"))
            for mount in self._mounts
            if mount.get("target") not in expected_mounts
        )
        if unsupported_mounts:
            raise ValueError(
                "HostEnvironment does not support extra mounts: "
                + ", ".join(unsupported_mounts)
            )
        seen_targets: set[str] = set()
        for mount in self._mounts:
            target = str(mount.get("target"))
            if target in seen_targets:
                raise ValueError(
                    f"HostEnvironment received duplicate mount target {target!r}"
                )
            seen_targets.add(target)
            if mount.get("type") != "bind":
                raise ValueError(
                    f"HostEnvironment mount {target!r} must have type='bind'"
                )
            if mount.get("read_only"):
                raise ValueError(f"HostEnvironment mount {target!r} must be writable")
            source = mount.get("source")
            expected_source = expected_mounts[target].resolve()
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
        mounted = {
            str(mount["target"]): Path(str(mount["source"]))
            for mount in self._mounts
            if mount.get("target") and mount.get("source")
        }
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
        for virtual in sorted(mappings, key=len, reverse=True):
            if raw == virtual:
                return mappings[virtual]
            if raw.startswith(f"{virtual}/"):
                return mappings[virtual] / raw[len(virtual) + 1 :]
        path = Path(raw)
        if path.is_absolute():
            raise ValueError(f"unsupported HostEnvironment path: {raw}")
        return mappings[_VIRTUAL_WORKDIR] / path

    def _translate_command(self, command: str) -> str:
        mappings = sorted(
            self._runtime_dirs().items(), key=lambda item: len(item[0]), reverse=True
        )

        def translate_literal(value: str) -> str | None:
            for virtual, host in mappings:
                if value == virtual:
                    return str(host)
                if value.startswith(f"{virtual}/"):
                    return str(host / value[len(virtual) + 1 :])
            return None

        def translate_unquoted(value: str) -> str:
            translated = value
            for virtual, host in mappings:
                pattern = re.compile(
                    rf"(?<![A-Za-z0-9_:/.-]){re.escape(virtual)}"
                    rf"(?=$|/|[\s;|&()<>])"
                )
                replacement = shlex.quote(str(host))
                translated = pattern.sub(
                    lambda _match, replacement=replacement: replacement,
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
            translated_literal = translate_literal(content)
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
        if resolved is None:
            return
        allowed: set[str] = {
            "root",
            str(os.getuid()),
            getpass.getuser(),
        }
        if str(resolved) not in allowed:
            raise ValueError(
                f"HostEnvironment cannot switch to user {resolved!r}; "
                "only root/current-user aliases are accepted"
            )

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
            "/bin/bash",
            "-lc",
            translated_command,
            cwd=translated_cwd,
            env=process_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
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
