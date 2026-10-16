"""Windows desktop-bundled WorkBuddy ACP adapter and isolated inspection."""

from __future__ import annotations

import json
import logging
import math
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from harbor.models.task.config import EnvironmentConfig, TaskOS
from harbor.models.trial.paths import TrialPaths

from .acp_agent import HostACPAgent
from .acp_protocol import config_option_choices, validate_json_structure
from .environment import HostEnvironment
from .windows import open_read_descriptor

# Cumulative arguments need separate limits for stored bytes and decoding work.
DEFAULT_WORKBUDDY_MAX_EVIDENCE_BYTES = 512 * 1024 * 1024
DEFAULT_WORKBUDDY_MAX_DECODED_EVIDENCE_BYTES = 8 * 1024**3
MAX_WORKBUDDY_CONFIG_BYTES = 16 * 1024 * 1024
CUSTOM_MODEL_PREFIX = "custom-local:"


def _path(value, label):
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"WorkBuddy {label} must be absolute")
    for parent in (path, *path.parents):
        if parent.is_symlink() or parent.is_junction():
            raise ValueError(f"WorkBuddy {label} traverses a link")
    return path


def _read_seed(path):
    path = _path(path, "configuration")
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_WORKBUDDY_CONFIG_BYTES:
        raise ValueError("WorkBuddy configuration is not a bounded regular file")
    descriptor = open_read_descriptor(path)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        current = _path(path, "configuration").stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or getattr(opened, "st_file_attributes", 0) & 0x400
            or not os.path.samestat(before, opened)
            or not os.path.samestat(current, opened)
        ):
            raise ValueError("WorkBuddy configuration changed while opening")
        if opened.st_size > MAX_WORKBUDDY_CONFIG_BYTES:
            raise ValueError("WorkBuddy configuration exceeds its byte limit")
        content = stream.read(MAX_WORKBUDDY_CONFIG_BYTES + 1)
    if len(content) > MAX_WORKBUDDY_CONFIG_BYTES:
        raise ValueError("WorkBuddy configuration exceeds its byte limit")
    return content


def _decode_json(content):
    try:
        value = json.loads(content.decode("utf-8"))
        validate_json_structure(value)
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("Invalid WorkBuddy configuration") from None
    return value


def _json(path):
    value = _decode_json(_read_seed(path))
    if not isinstance(value, dict):
        raise ValueError("Invalid WorkBuddy configuration")
    return value


def _model_seed(path, model_id, *, inspection):
    models = _decode_json(_read_seed(path))
    if not isinstance(models, list) or any(
        not isinstance(model, dict) or not isinstance(model.get("id"), str)
        for model in models
    ):
        raise ValueError("Invalid WorkBuddy model configuration")
    if len({model["id"] for model in models}) != len(models):
        raise ValueError("Duplicate WorkBuddy model identities")
    if inspection:
        public = {
            "id",
            "name",
            "url",
            "vendor",
            "maxInputTokens",
            "maxOutputTokens",
            "onlyReasoning",
            "reasoning",
            "supportsImages",
            "supportsReasoning",
            "supportsToolCall",
            "useCustomProtocol",
        }
        models = [
            {key: value for key, value in model.items() if key in public}
            for model in models
        ]
        for model in models:
            model["apiKey"] = "peval-inspection-placeholder"
    else:
        models = [
            model for model in models if CUSTOM_MODEL_PREFIX + model["id"] == model_id
        ]
    return (json.dumps(models, ensure_ascii=False) + "\n").encode("utf-8")


def _field(document, *keys):
    for key in keys:
        document = document.get(key) if isinstance(document, dict) else None
    return document


def _version(value):
    if not isinstance(value, str) or not value or "\0" in value:
        raise ValueError("Invalid WorkBuddy version configuration")
    return value


def _authentication_id(document):
    value = _field(document, "authentication", "id")
    if (
        not isinstance(value, str)
        or not value
        or any(char in value for char in "/\\:\0")
    ):
        raise ValueError("Invalid WorkBuddy authentication identity")
    return value


@dataclass(frozen=True)
class WorkBuddyInspection:
    desktop_version: str
    cli_version: str
    available_models: tuple[dict, ...]
    current_model_id: str | None
    config_options: tuple[dict, ...]


class HostWorkBuddyAgent(HostACPAgent):
    _supports_skills = True

    def __init__(
        self,
        *args,
        installation_dir,
        profile_dir,
        auth_file,
        _inspection=False,
        **kwargs,
    ):
        self.installation_dir = _path(installation_dir, "installation_dir")
        self.profile_dir = _path(profile_dir, "profile_dir")
        self.auth_file = _path(auth_file, "auth_file")
        self.cli_dir = self.installation_dir / "resources/app.asar.unpacked/cli"
        product = _json(self.cli_dir / "product.json")
        package = _json(self.cli_dir / "package.json")
        self.desktop_version = _version(product.get("genieVersion"))
        self.cli_version = _version(
            _field(package, "publishConfig", "customPackage", "version")
        )
        _authentication_id(_json(self.profile_dir / "cache/acc-product-config-v3.json"))
        self._inspection = _inspection
        for path in (
            self.installation_dir / "WorkBuddy.exe",
            self.cli_dir / "bin/codebuddy",
            self.cli_dir / "dist/codebuddy-headless.js",
            self.auth_file,
        ):
            if not _path(path, "runtime file").is_file():
                raise FileNotFoundError(
                    "WorkBuddy runtime or authentication file is missing"
                )
        if any(
            key in kwargs
            for key in (
                "argv",
                "config_dir",
                "authenticate_method_id",
                "tool_result_format",
            )
        ):
            raise ValueError(
                "WorkBuddy owns CLI launch and authentication configuration"
            )
        options = dict(kwargs.pop("config_options", {}) or {})
        if "model" in options:
            raise ValueError("Use model_name for WorkBuddy model selection")
        self._requested_model = kwargs.get("model_name")
        if not _inspection and (
            not isinstance(self._requested_model, str)
            or not self._requested_model
            or "\0" in self._requested_model
        ):
            raise ValueError(
                "WorkBuddy model_name requires an exact advertised model ID"
            )
        options = (
            {}
            if _inspection
            else {
                "model": self._requested_model,
                "mode": "bypassPermissions",
                "multitask": False,
                **options,
            }
        )
        kwargs.setdefault("max_evidence_bytes", DEFAULT_WORKBUDDY_MAX_EVIDENCE_BYTES)
        kwargs.setdefault(
            "max_decoded_evidence_bytes", DEFAULT_WORKBUDDY_MAX_DECODED_EVIDENCE_BYTES
        )
        super().__init__(
            *args,
            argv=[
                str(self.installation_dir / "WorkBuddy.exe"),
                str(Path(__file__).with_name("workbuddy_bootstrap.cjs")),
                str(self.cli_dir / "bin/codebuddy"),
                "--acp",
                "--setting-sources",
                "none",
                "--no-plugin-management",
            ],
            config_options=options,
            tool_result_format="codebuddy",
            **kwargs,
        )
        self._profile_seeded = False
        self._agent_metadata = {
            "workbuddy_desktop_version": self.desktop_version,
            "workbuddy_cli_version": self.cli_version,
            "workbuddy_model_id": self._requested_model,
        }

    @staticmethod
    def name():
        return "workbuddy"

    @staticmethod
    def _host(environment):
        host = HostACPAgent._host(environment)
        if host.os != TaskOS.WINDOWS:
            raise TypeError("WorkBuddy ACP requires a native Windows Host")
        return host

    async def setup(self, environment):
        await super().setup(environment)
        if self._profile_seeded:
            return
        config = Path(self._child_env["XDG_CONFIG_HOME"])
        for name in (
            "models.json",
            "keyblob",
            "device-id",
            "cache/acc-product-config-v3.json",
        ):
            source = _path(self.profile_dir / name, "profile seed")
            try:
                content = (
                    _model_seed(
                        source, self._requested_model, inspection=self._inspection
                    )
                    if name == "models.json"
                    else _read_seed(source)
                )
            except FileNotFoundError:
                if name == "cache/acc-product-config-v3.json":
                    raise ValueError(
                        "WorkBuddy product configuration seed is missing"
                    ) from None
                continue
            else:
                destination = config / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
        product_path = config / "cache/acc-product-config-v3.json"
        auth_id = _authentication_id(_json(product_path))
        auth = (
            Path(self._child_env["LOCALAPPDATA"])
            / "CodeBuddyExtension/Data/Public/auth"
            / (auth_id + ".info")
        )
        auth.parent.mkdir(parents=True, exist_ok=True)
        auth.write_bytes(_read_seed(self.auth_file))
        self._child_env.update(
            PEVAL_WORKBUDDY_BOOTSTRAP_PYTHON=sys.executable,
            PEVAL_WORKBUDDY_BOOTSTRAP_TIMEOUT_MS=str(
                math.ceil(self.handshake_timeout_sec * 1000)
            ),
            CODEBUDDY_CONFIG_DIR=str(config),
            WORKBUDDY_CONFIG_DIR=str(config),
            ACC_PRODUCT_CONFIG_PATH=str(product_path),
            ELECTRON_RUN_AS_NODE="1",
            CODEBUDDY_FORCE_HEADLESS_BUNDLE="1",
            CODEBUDDY_FORCE_LITE_WB_BUNDLE="0",
            CODEBUDDY_DISABLE_COMPILE_CACHE="1",
            DISABLE_AUTOUPDATER="1",
            DISABLE_TELEMETRY="1",
            CODEBUDDY_DISABLE_CRON="1",
            CODEBUDDY_DISABLE_AUTO_MEMORY="1",
            CODEBUDDY_DISABLE_SESSION_HISTORY_CLEANUP="1",
            CODEBUDDY_HOST="workbuddy-desktop",
        )
        if self.skills_dir:
            self._child_env["CODEBUDDY_SESSION_SKILL_DIRS"] = str(
                environment.native_path(self.skills_dir)
            )
        self._profile_seeded = True

    def populate_context_post_run(self, context):
        super().populate_context_post_run(context)
        context.metadata.update(
            workbuddy_desktop_version=self.desktop_version,
            workbuddy_cli_version=self.cli_version,
            workbuddy_model_id=self._requested_model,
        )

    async def _run_invocation(self, action, instruction, environment):
        if self._inspection and action != "inspect":
            raise ValueError("WorkBuddy inspection cannot submit prompts")
        if action != "inspect":
            instruction = f"Workspace root on this native host: {environment.work_dir}. Any /workspace path in the task refers to this directory; use native paths when invoking tools.\n\n{instruction}"
        return await super()._run_invocation(action, instruction, environment)


async def inspect_workbuddy(
    *, installation_dir, profile_dir, auth_file, handshake_timeout_sec=60.0
):
    """Inspect a desktop profile through ACP without submitting model requests."""
    with tempfile.TemporaryDirectory(prefix="workbuddy-inspect-") as directory:
        root = Path(directory)
        environment_dir = root / "environment"
        environment_dir.mkdir()
        paths = TrialPaths(root / "trial")
        paths.mkdir()
        host = HostEnvironment(
            environment_dir=environment_dir,
            environment_name="workbuddy-inspect",
            session_id="inspection",
            trial_paths=paths,
            task_env_config=EnvironmentConfig(workdir="/workspace"),
            host_access={"filesystem": True, "process": True},
            workspace_baseline="none",
            workdir_root=root / "workspaces",
            logger=logging.getLogger(__name__),
        )
        agent = HostWorkBuddyAgent(
            installation_dir=installation_dir,
            profile_dir=profile_dir,
            auth_file=auth_file,
            _inspection=True,
            logs_dir=paths.agent_dir,
            handshake_timeout_sec=handshake_timeout_sec,
        )
        try:
            await host.start(False)
            await agent.setup(host)
            summary = await agent._invoke("inspect", "", host)
            options = summary.get("config_options", [])
            model = next((option for option in options if option["id"] == "model"), {})
            choices = config_option_choices(model)
            return WorkBuddyInspection(
                agent.desktop_version,
                agent.cli_version,
                tuple(
                    {
                        "modelId": choice["value"],
                        "name": choice["name"],
                        **(
                            {"description": choice["description"]}
                            if "description" in choice
                            else {}
                        ),
                    }
                    for choice in choices
                ),
                model.get("currentValue"),
                tuple(options),
            )
        finally:
            await host.stop(True)
