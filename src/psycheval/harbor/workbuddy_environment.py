"""WorkBuddy workspace preparation on the trusted native Host."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import yaml

from .datasets import _read_toml, _regular_file, _required_relative
from .environment import (
    HostEnvironment,
    _extract_workspace_archive,
    _read_regular_nofollow,
)

_INERT_COMPOSE = {
    "services": {"main": {"extra_hosts": ["host.docker.internal:host-gateway"]}}
}


class WorkBuddyHostEnvironment(HostEnvironment):
    """Prepare declared workspace inputs without interpreting container builds."""

    def _validate_build_context(self) -> None:
        if self._is_separate_verifier():
            self._workspace_archive = None
            super()._validate_build_context()
            return
        task = self.environment_dir.resolve().parent
        manifest = next(
            (
                p / "dataset.toml"
                for p in (task, *task.parents)
                if (p / "dataset.toml").exists()
            ),
            None,
        )
        layout = _read_toml(manifest).get("layout", {}) if manifest else {}
        archive = None
        if "workspace_archive" in layout:
            archive = _regular_file(
                task, _required_relative(layout, "workspace_archive")
            )
        elif os.path.lexists(self.environment_dir / "workspace.tar.gz"):
            archive = _regular_file(task, Path("environment/workspace.tar.gz"))
        self._workspace_archive = archive
        if archive is not None:
            if self._workspace_source is not None:
                raise ValueError("WorkBuddy archive cannot use workspace_source")
            self.task_env_config.workdir = self.task_env_config.workdir or "/workspace"
        elif (
            self._workspace_source is None
            and (self.environment_dir / "Dockerfile").exists()
        ):
            raise ValueError(
                "WorkBuddy Host cannot execute a Docker build; supply a native workspace or use Docker"
            )
        compose = [
            self.environment_dir / name
            for name in ("docker-compose.yaml", "docker-compose.yml")
            if os.path.lexists(self.environment_dir / name)
        ]
        if compose:
            if archive is None or len(compose) != 1:
                raise ValueError(
                    "WorkBuddy Host does not support Docker Compose services"
                )
            value = yaml.safe_load(
                _read_regular_nofollow(compose[0], max_bytes=64 * 1024)
            )
            if value != _INERT_COMPOSE:
                raise ValueError(
                    "WorkBuddy Host accepts only inert WorkBuddy Compose metadata"
                )
        # Harbor consults this private Task copy when uploading Skills.
        self.task_env_config.os = self.os

    def _validate_mounts(self) -> None:
        super()._validate_mounts()
        if self._workspace_archive is not None and self._workspace is not None:
            raise ValueError("WorkBuddy archive cannot use an external workspace mount")

    def _materialize_context(
        self, context_target: Path, *, cancel: threading.Event
    ) -> None:
        if self._workspace_archive is None or self._is_separate_verifier():
            super()._materialize_context(context_target, cancel=cancel)
            return
        _extract_workspace_archive(
            self._workspace_archive, context_target, cancel=cancel
        )
        self._initialize_workspace_baseline(context_target, cancel=cancel)
