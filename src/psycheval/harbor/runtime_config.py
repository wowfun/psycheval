from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

PEVAL_CONFIG_ENV = "PEVAL_CONFIG"
RUNTIME_SCHEMA_VERSION = 1
HARNESS_PROTOCOL_VERSION = 2
DEFAULT_WORKDIR_ROOT = "~/workspaces"


class RuntimeConfigError(ValueError):
    """Raised when a PEVAL configuration cannot satisfy its runtime contract."""


@dataclass(frozen=True)
class HostSettings:
    workdir_root: Path | None
    source_path: Path | None = None


@dataclass(frozen=True)
class RuntimePaths:
    workdir: str
    tests: str
    agent_logs: str
    verifier_logs: str
    artifacts: str


@dataclass(frozen=True)
class HarnessInvocation:
    action: Literal["run", "resume"]
    protocol_version: int = HARNESS_PROTOCOL_VERSION


@dataclass(frozen=True)
class EffectiveRuntimeConfig:
    paths: RuntimePaths
    workdir_root: str | None = None
    workspace: str | None = None
    python: str | None = None
    harness: HarnessInvocation | None = None

    def to_dict(self) -> dict[str, Any]:
        harbor: dict[str, Any] = {
            "host": {
                "workdir_root": self.workdir_root,
                "workspace": self.workspace,
            }
        }
        if self.harness is not None:
            harbor["harness"] = {
                "protocol_version": self.harness.protocol_version,
                "action": self.harness.action,
            }
        return {
            "schema_version": RUNTIME_SCHEMA_VERSION,
            "harbor": harbor,
            "paths": {
                "workdir": self.paths.workdir,
                "tests": self.paths.tests,
                "agent_logs": self.paths.agent_logs,
                "verifier_logs": self.paths.verifier_logs,
                "artifacts": self.paths.artifacts,
            },
            "executables": {"python": self.python},
        }


def load_host_settings(
    *,
    environ: dict[str, str] | os._Environ[str] | None = None,
    cwd: Path | None = None,
) -> HostSettings:
    values = os.environ if environ is None else environ
    configured = values.get(PEVAL_CONFIG_ENV)
    if configured is None:
        return HostSettings(
            workdir_root=_resolve_root(DEFAULT_WORKDIR_ROOT, Path.cwd())
        )

    base = Path.cwd() if cwd is None else cwd
    config_path = Path(configured).expanduser()
    if not config_path.is_absolute():
        config_path = base / config_path
    config_path = config_path.resolve()
    if not config_path.is_file():
        raise RuntimeConfigError(
            f"{PEVAL_CONFIG_ENV} must name a readable TOML file: {config_path}"
        )
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeConfigError(f"failed to read {config_path}: {exc}") from exc

    harbor = data.get("harbor", {})
    if not isinstance(harbor, dict):
        raise RuntimeConfigError("PEVAL config [harbor] must be a TOML table")
    host = harbor.get("host", {})
    if not isinstance(host, dict):
        raise RuntimeConfigError("PEVAL config [harbor.host] must be a TOML table")
    unknown = sorted(set(host) - {"workdir_root"})
    if unknown:
        raise RuntimeConfigError(
            f"unknown PEVAL config [harbor.host] field: {unknown[0]}"
        )
    raw_root = host.get("workdir_root", DEFAULT_WORKDIR_ROOT)
    if not isinstance(raw_root, str):
        raise RuntimeConfigError(
            "PEVAL config [harbor.host].workdir_root must be a string"
        )
    root = None if not raw_root.strip() else _resolve_root(raw_root, config_path.parent)
    return HostSettings(workdir_root=root, source_path=config_path)


def write_effective_runtime_config(path: Path, config: EffectiveRuntimeConfig) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        temporary.chmod(0o600)
        temporary.replace(path)
        path.chmod(0o600)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def load_effective_runtime_config(
    path: Path | str | None = None,
    *,
    environ: dict[str, str] | os._Environ[str] | None = None,
    require_harness: bool = False,
) -> EffectiveRuntimeConfig:
    values = os.environ if environ is None else environ
    configured = path if path is not None else values.get(PEVAL_CONFIG_ENV)
    if configured is None or not str(configured).strip():
        raise RuntimeConfigError(f"{PEVAL_CONFIG_ENV} is required")
    config_path = Path(configured)
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeConfigError(
            f"effective {PEVAL_CONFIG_ENV} file not found: {config_path}"
        ) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeConfigError(
            f"failed to read effective {PEVAL_CONFIG_ENV} JSON {config_path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeConfigError("effective PEVAL config must be a JSON object")
    if data.get("schema_version") != RUNTIME_SCHEMA_VERSION:
        raise RuntimeConfigError(
            "unsupported effective PEVAL config schema_version: "
            f"{data.get('schema_version')!r}"
        )
    _reject_unknown(data, {"schema_version", "harbor", "paths", "executables"}, "")

    raw_paths = _object(data.get("paths"), "paths")
    path_fields = {"workdir", "tests", "agent_logs", "verifier_logs", "artifacts"}
    _reject_unknown(raw_paths, path_fields, "paths")
    missing_paths = sorted(path_fields - set(raw_paths))
    if missing_paths:
        raise RuntimeConfigError(
            f"effective PEVAL config paths.{missing_paths[0]} is required"
        )
    paths = RuntimePaths(
        **{
            key: _nonempty_string(raw_paths.get(key), f"paths.{key}")
            for key in path_fields
        }
    )

    raw_harbor = _object(data.get("harbor"), "harbor")
    _reject_unknown(raw_harbor, {"host", "harness"}, "harbor")
    raw_host = _object(raw_harbor.get("host"), "harbor.host")
    _reject_unknown(raw_host, {"workdir_root", "workspace"}, "harbor.host")
    _require_fields(raw_host, {"workdir_root", "workspace"}, "harbor.host")
    workdir_root = _optional_string(
        raw_host.get("workdir_root"), "harbor.host.workdir_root"
    )
    workspace = _optional_string(raw_host.get("workspace"), "harbor.host.workspace")

    harness = None
    if "harness" in raw_harbor:
        raw_harness = _object(raw_harbor["harness"], "harbor.harness")
        _reject_unknown(raw_harness, {"protocol_version", "action"}, "harbor.harness")
        protocol_version = raw_harness.get("protocol_version")
        if protocol_version != HARNESS_PROTOCOL_VERSION:
            raise RuntimeConfigError(
                f"unsupported PEVAL harness protocol_version: {protocol_version!r}"
            )
        action = raw_harness.get("action")
        if action not in {"run", "resume"}:
            raise RuntimeConfigError(
                f"effective PEVAL config harbor.harness.action is invalid: {action!r}"
            )
        harness = HarnessInvocation(action=action)
    if require_harness and harness is None:
        raise RuntimeConfigError("effective PEVAL config harbor.harness is required")

    raw_executables = _object(data.get("executables"), "executables")
    _reject_unknown(raw_executables, {"python"}, "executables")
    _require_fields(raw_executables, {"python"}, "executables")
    python = _optional_string(raw_executables.get("python"), "executables.python")
    return EffectiveRuntimeConfig(
        paths=paths,
        workdir_root=workdir_root,
        workspace=workspace,
        python=python,
        harness=harness,
    )


def optional_effective_runtime_config(
    *, environ: dict[str, str] | os._Environ[str] | None = None
) -> EffectiveRuntimeConfig | None:
    values = os.environ if environ is None else environ
    if not values.get(PEVAL_CONFIG_ENV):
        return None
    return load_effective_runtime_config(environ=values)


def _resolve_root(raw: str, base: Path) -> Path:
    if "\x00" in raw:
        raise RuntimeConfigError("PEVAL config workdir_root contains NUL")
    root = Path(raw).expanduser()
    if not root.is_absolute():
        root = base / root
    return root.resolve()


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeConfigError(f"effective PEVAL config {field} must be an object")
    return value


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise RuntimeConfigError(
            f"effective PEVAL config {field} must be a non-empty string"
        )
    return value


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _nonempty_string(value, field)


def _reject_unknown(value: dict[str, Any], allowed: set[str], field: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        prefix = f"{field}." if field else ""
        raise RuntimeConfigError(
            f"unknown effective PEVAL config field: {prefix}{unknown[0]}"
        )


def _require_fields(value: dict[str, Any], required: set[str], field: str) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise RuntimeConfigError(
            f"effective PEVAL config {field}.{missing[0]} is required"
        )
