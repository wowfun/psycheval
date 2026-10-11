"""Opt-in Linux execution-format adapter for container-path verifier plugins."""

from __future__ import annotations

import shutil
from pathlib import Path

from harbor.models.task.config import TaskOS

from .environment import HostEnvironment
from .paths import HostPathMapper
from .runtime_config import PEVAL_CONFIG_ENV


class NamespaceEnvironment:
    def __init__(self, host: HostEnvironment, task_root: Path, private: Path):
        if host.os != TaskOS.LINUX:
            raise ValueError("WorkBuddy linux_namespace requires a Linux Host")
        executable = shutil.which("bwrap")
        if executable is None:
            raise RuntimeError("WorkBuddy linux_namespace requires Bubblewrap")
        self.host = host
        for name in ("app", "tmp", "logs", "tests"):
            (private / name).mkdir(exist_ok=True)
        self.prefix = [
            executable,
            "--unshare-user",
            "--die-with-parent",
            "--tmpfs",
            "/",
        ]
        # A private root supplies absent container mountpoints without trying to
        # create /app or /workspace in the host's read-only root mount.
        for entry in sorted(Path("/").iterdir()):
            if entry.name in {
                "app",
                "workspace",
                "tests",
                "logs",
                "tmp",
                "dev",
                "proc",
            }:
                continue
            if entry.is_symlink():
                self.prefix.extend(["--symlink", str(entry.readlink()), str(entry)])
            else:
                self.prefix.extend(["--ro-bind", str(entry), str(entry)])
        self.prefix.extend(["--dev-bind", "/dev", "/dev", "--proc", "/proc"])
        self.tests = private / "tests"
        mounts = [
            (host.work_dir, "/workspace"),
            (private / "logs", "/logs"),
            (host.native_path("/logs/agent"), "/logs/agent"),
            (host.native_path("/logs/verifier"), "/logs/verifier"),
            (self.tests, "/tests"),
            (private / "app", "/app"),
            (private / "tmp", "/tmp"),
        ]
        self._paths = HostPathMapper(
            TaskOS.LINUX, {target: source for source, target in mounts}, "/workspace"
        )
        for source, target in mounts:
            source.mkdir(parents=True, exist_ok=True)
            self.prefix.extend(["--bind", str(source), target])
        self.prefix.extend(["--ro-bind", str(task_root), str(task_root)])

    def __getattr__(self, name):
        return getattr(self.host, name)

    @property
    def path_mapper(self):
        return self._paths

    async def upload_dir(self, source_dir, target_dir):
        return await self.host.upload_dir(source_dir, str(self.native_path(target_dir)))

    def native_path(self, path):
        return self._paths.translate(path)

    async def upload_file(self, source_path, target_path):
        return await self.host.upload_file(
            source_path, str(self.native_path(target_path))
        )

    async def download_file(self, source_path, target_path):
        return await self.host.download_file(
            str(self.native_path(source_path)), target_path
        )

    async def download_dir(self, source_dir, target_dir):
        return await self.host.download_dir(
            str(self.native_path(source_dir)), target_dir
        )

    async def download_dir_with_exclusions(self, *, source_dir, target_dir, exclude):
        return await self.host.download_dir_with_exclusions(
            source_dir=str(self.native_path(source_dir)),
            target_dir=target_dir,
            exclude=exclude,
        )

    async def download_dir_filtered(
        self, *, source_dir, target_dir, include=None, exclude=None, protect=None
    ):
        return await self.host.download_dir_filtered(
            source_dir=str(self.native_path(source_dir)),
            target_dir=target_dir,
            include=include,
            exclude=exclude,
            protect=protect,
        )

    async def ensure_dirs(self, dirs, *, chmod=True, virtual_workdir=False):
        if virtual_workdir:
            raise NotImplementedError("WorkBuddy namespace mounts are fixed")
        return await self.host.ensure_dirs(
            [self.native_path(path) for path in dirs], chmod=chmod
        )

    async def empty_dirs(self, dirs, *, chmod=True):
        return await self.host.empty_dirs(
            [self.native_path(path) for path in dirs], chmod=chmod
        )

    async def reset_dirs(self, *, remove_dirs, create_dirs, chmod_dirs=None):
        return await self.host.reset_dirs(
            remove_dirs=[self.native_path(path) for path in remove_dirs],
            create_dirs=[self.native_path(path) for path in create_dirs],
            chmod_dirs=[self.native_path(path) for path in (chmod_dirs or ())],
        )

    async def is_dir(self, path, user=None):
        return await self.host.is_dir(str(self.native_path(path)), user=user)

    async def is_file(self, path, user=None):
        return await self.host.is_file(str(self.native_path(path)), user=user)

    def runtime_config_env(self, **kwargs):
        raise NotImplementedError(
            "WorkBuddy namespace does not support Host runtime control"
        )

    async def exec(self, command, *, cwd=None, env=None, **kwargs):
        return await self.exec_argv(
            ["/bin/bash", "-c", command], cwd=cwd, env=env, **kwargs
        )

    async def exec_argv(self, argv, *, cwd=None, env=None, **kwargs):
        if (
            isinstance(argv, (str, bytes))
            or not argv
            or any(not isinstance(arg, str) or "\x00" in arg for arg in argv)
            or not argv[0]
        ):
            raise ValueError(
                "namespace argv must contain an executable and NUL-free strings"
            )
        # Keep logical paths in the command and its environment. Their meaning is
        # supplied by mounts, including literals hidden inside Python/JSON files.
        command = [*self.prefix, "--chdir", cwd or "/workspace"]
        merged_env = self.host._merge_env(env) or {}
        if PEVAL_CONFIG_ENV in merged_env:
            self.runtime_config_env()
        for key, value in merged_env.items():
            command.extend(["--setenv", key, value])
        command.extend(
            [
                "--setenv",
                "PYTHONDONTWRITEBYTECODE",
                "1",
                "--",
                *argv,
            ]
        )
        return await self.host.exec_argv(command, **kwargs)
