"""Run a preinstalled OpenCode CLI on a native HostEnvironment."""

from __future__ import annotations

import copy
import json
import shutil
import sys
from typing import override

from harbor.agents.installed.base import NonZeroAgentExitCodeError
from harbor.agents.installed.opencode import OpenCode
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.utils.trajectory_utils import format_trajectory_json

from .environment import HostEnvironment
from .inference_telemetry import populate_context_from_trajectory

_STDIN_LAUNCHER = (
    "import subprocess,sys; "
    "f=open(sys.argv[1],'rb'); "
    "sys.exit(subprocess.call(sys.argv[2:],stdin=f))"
)


class HostOpenCodeAgent(OpenCode):
    """Reuse Harbor's OpenCode trajectory conversion without its Bash installer."""

    SUPPORTS_WINDOWS = True
    SUPPORTS_RESUME = False
    SUPPORTS_LOAD_NATIVE_TRAJECTORY = False
    SUPPORTS_LOAD_ATIF_TRAJECTORY = False

    def __init__(
        self,
        *args,
        executable: str = "opencode",
        opencode_config: dict | None = None,
        **kwargs,
    ):
        if opencode_config is not None:
            if not isinstance(opencode_config, dict):
                raise ValueError("opencode_config must be an object")
            for section in ("skills", "mcp", "provider"):
                if section in opencode_config and not isinstance(
                    opencode_config[section], dict
                ):
                    raise ValueError(f"opencode_config.{section} must be an object")
            paths = opencode_config.get("skills", {}).get("paths", [])
            if not isinstance(paths, list) or any(
                not isinstance(path, str) for path in paths
            ):
                raise ValueError(
                    "opencode_config.skills.paths must be a list of strings"
                )
        super().__init__(*args, opencode_config=opencode_config, **kwargs)
        if not self.model_name or "/" not in self.model_name:
            raise ValueError("Model name must be in the format provider/model_name")
        if not executable or "\x00" in executable:
            raise ValueError("OpenCode executable must be nonempty and NUL-free")
        self.executable = executable

    @staticmethod
    def _host(environment: BaseEnvironment) -> HostEnvironment:
        if not isinstance(environment, HostEnvironment):
            raise TypeError("HostOpenCodeAgent requires HostEnvironment")
        return environment

    @override
    async def setup(self, environment: BaseEnvironment) -> None:
        host = self._host(environment)
        executable = shutil.which(self.executable)
        if executable is None:
            raise FileNotFoundError(f"Install OpenCode first: {self.executable}")
        self.executable = executable
        env = self._runtime_env(host)
        with (self.logs_dir / "opencode-setup.log").open("w", encoding="utf-8") as log:

            async def capture(text: str, stream: str) -> None:
                log.write(text)
                log.flush()

            try:
                with (
                    host.scoped_exec_env(env),
                    host.scoped_output_callback(capture),
                ):
                    result = await host.exec_argv(
                        [executable, "--version"], env=env, timeout_sec=30
                    )
            except TimeoutError as exc:
                raise RuntimeError(
                    "OpenCode version probe exceeded its 30-second timeout; "
                    "see opencode-setup.log"
                ) from exc
        if result.return_code != 0 or not (result.stdout or "").strip():
            raise RuntimeError("OpenCode version probe failed")
        installed = (result.stdout or "").strip()
        if self._version is not None and self._version != installed:
            raise RuntimeError(
                f"OpenCode version mismatch: expected {self._version}, got {installed}"
            )
        self._version = installed

    def _runtime_env(self, host: HostEnvironment) -> dict[str, str]:
        root = self.logs_dir.resolve() / "opencode"
        connection = self.model_connection
        env = {**connection.env, **self.extra_env}
        for key, child in (
            ("HOME", "home"),
            ("USERPROFILE", "home"),
            ("XDG_CONFIG_HOME", "config"),
            ("XDG_DATA_HOME", "data"),
            ("XDG_STATE_HOME", "state"),
            ("XDG_CACHE_HOME", "cache"),
            ("OPENCODE_CONFIG_DIR", "config/opencode"),
        ):
            path = root / child
            path.mkdir(parents=True, exist_ok=True)
            env[key] = str(path)
        config_path = root / "config/opencode/opencode.json"
        config_path.write_text("{}\n", encoding="utf-8")
        env["OPENCODE_CONFIG"] = str(config_path)
        provider, model = self.model_name.split("/", 1)
        provider_config = {"models": {model: {}}}
        if connection.configured_base_url and provider in {"openai", "anthropic"}:
            provider_config["options"] = {"baseURL": connection.configured_base_url}
        config = {
            "autoupdate": False,
            "share": "disabled",
            "snapshot": False,
            "permission": "allow",
            "provider": {provider: provider_config},
        }
        for server in self.mcp_servers:
            if server.transport == "stdio":
                value = {
                    "type": "local",
                    "command": [server.command, *server.args],
                }
            else:
                value = {"type": "remote", "url": server.url}
            config.setdefault("mcp", {})[server.name] = value
        self._deep_merge(config, copy.deepcopy(self._opencode_config))
        if self.skills_dir:
            config.setdefault("skills", {}).setdefault("paths", []).append(
                str(host.native_path(self.skills_dir))
            )
        env["OPENCODE_CONFIG_CONTENT"] = json.dumps(config, ensure_ascii=False)
        return env

    @override
    def _parse_stdout(self) -> list[dict]:
        path = self.logs_dir / "opencode.txt"
        if not path.is_file():
            return []
        events = []
        with path.open(encoding="utf-8") as output:
            for line in output:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    events.append(event)
        return events

    @override
    def populate_context_post_run(self, context: AgentContext) -> None:
        trajectory = self._convert_events_to_trajectory(self._parse_stdout())
        if trajectory is None:
            return
        data = trajectory.to_json_dict()
        (self.logs_dir / "trajectory.json").write_text(
            format_trajectory_json(data), encoding="utf-8"
        )
        populate_context_from_trajectory(context, data)
        if trajectory.final_metrics is not None:
            context.cost_usd = trajectory.final_metrics.total_cost_usd

    @override
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        del context
        host = self._host(environment)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._instruction = self.render_instruction(instruction)
        instruction_path = self.logs_dir.resolve() / "instruction.txt"
        instruction_path.write_bytes(self._instruction.encode("utf-8"))
        (self.logs_dir / "trajectory.json").unlink(missing_ok=True)
        argv = [
            sys.executable,
            "-c",
            _STDIN_LAUNCHER,
            str(instruction_path),
            self.executable,
            "run",
            "--format=json",
            "--model",
            self.model_name,
            "--thinking",
        ]
        if variant := self._resolved_flags.get("variant"):
            argv.extend(["--variant", str(variant)])
        with (
            (self.logs_dir / "opencode.txt").open("w", encoding="utf-8") as stdout,
            (self.logs_dir / "opencode.stderr.log").open(
                "w", encoding="utf-8"
            ) as stderr,
        ):

            async def capture(text: str, stream: str) -> None:
                handle = stdout if stream == "stdout" else stderr
                handle.write(text)
                handle.flush()

            env = self._runtime_env(host)
            with host.scoped_exec_env(env), host.scoped_output_callback(capture):
                result = await host.exec_argv(argv, env=env)
        if result.return_code != 0:
            raise NonZeroAgentExitCodeError(
                f"OpenCode exited with {result.return_code}; see opencode.stderr.log"
            )
        events = self._parse_stdout()
        if any(event.get("type") == "error" for event in events):
            raise NonZeroAgentExitCodeError(
                "OpenCode emitted error events; see opencode.txt"
            )
        if not any(event.get("type") == "step_finish" for event in events):
            raise RuntimeError("OpenCode emitted no completed step; see Agent logs")

    @override
    async def resume(self, *args, **kwargs) -> None:
        raise NotImplementedError("HostOpenCodeAgent supports fresh runs only")
