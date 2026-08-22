from __future__ import annotations

import json
import os
import re
import secrets
import stat
import tempfile
import tomllib
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable

from psycheval.i18n import normalize_locale

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
HARBOR_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$")
ACP_AGENT_ID_RE = HARBOR_ID_RE
DEFAULT_DB_PATH_RE = re.compile(r"^\s*default_db_path\s*=")
TABLE_HEADER_RE = re.compile(r"^\s*\[([^\]\n]+)\]\s*(?:#.*)?$")
HARBOR_MOUNT_HEADER_RE = re.compile(r"^\s*\[\[\s*harbor\.mounts\s*\]\]\s*(?:#.*)?$")
HARBOR_DATASET_HEADER_RE = re.compile(r"^\s*\[\[\s*harbor\.datasets\s*\]\]\s*(?:#.*)?$")
ACP_AGENT_HEADER_RE = re.compile(r"^\s*\[\[\s*acp\.agents\s*\]\]\s*(?:#.*)?$")
PEVAL_CONFIG_FILENAME = "peval.toml"
WINDOWS_DRIVE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
WINDOWS_DRIVE_MOUNT_ROOT = Path("/mnt")
DEFAULT_ADAPTER_DB_PATHS = {
    "psychevo": "~/.psychevo/state.db",
    "opencode": "~/.local/share/opencode/opencode.db",
    "hermes": "~/.hermes/state.db",
}


@dataclass(frozen=True)
class DbMapping:
    messages_table: str = "messages"
    session_id_column: str = "session_id"
    sequence_column: str = "session_seq"
    message_column: str = "message_json"
    usage_column: str = "usage_json"
    metadata_column: str = "metadata_json"


@dataclass(frozen=True)
class HarborDataset:
    id: str
    path: str


@dataclass(frozen=True)
class HarborMount:
    id: str
    path: str
    dataset_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class AcpAgent:
    id: str
    title: str
    command: str
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolConfig:
    adapter: str = "psychevo"
    locale: str = "en"
    workspace_root: str | None = None
    description: str | None = None
    analysis_eval_slug: str = "default"
    agent_name: str | None = None
    agent_version: str = "0.1.0"
    model: str | None = None
    max_content_chars: int = 128 * 1024
    max_content_chars_explicit: bool = dataclass_field(default=False, repr=False)
    redact: bool = True
    db: DbMapping = DbMapping()
    adapter_options: dict[str, Any] = dataclass_field(default_factory=dict)
    adapter_options_by_id: dict[str, dict[str, Any]] = dataclass_field(
        default_factory=dict,
        repr=False,
    )
    adapter_default_db_paths: dict[str, str] = dataclass_field(
        default_factory=dict, repr=False
    )
    harbor_datasets: tuple[HarborDataset, ...] = ()
    harbor_mounts: tuple[HarborMount, ...] = ()
    acp_agents: tuple[AcpAgent, ...] = ()


def default_workspace_config_text() -> str:
    lines: list[str] = []
    for adapter_id, default_db_path in DEFAULT_ADAPTER_DB_PATHS.items():
        if lines:
            lines.append("\n")
        lines.extend(
            [
                f"[{_adapter_table_key(adapter_id)}]\n",
                f"default_db_path = {json.dumps(default_db_path)}\n",
            ]
        )
    return "".join(lines)


def load_config(path: str | None, *, workspace_root: str | None = None) -> ToolConfig:
    config = ToolConfig()
    workspace_config = discover_peval_config(workspace_root)
    if workspace_config is not None:
        data = tomllib.loads(workspace_config.read_text(encoding="utf-8"))
        config = replace(config, workspace_root=str(workspace_config.parent))
        config = apply_toml_config(
            config,
            data,
            top_level_locale=True,
            base_dir=workspace_config.parent,
        )
    if path:
        config_path = Path(path).expanduser()
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        config = apply_toml_config(
            config,
            data,
            top_level_locale=True,
            base_dir=config_path.parent,
        )
    return config


def discover_peval_config(workspace_root: str | None = None) -> Path | None:
    if workspace_root:
        candidate = Path(workspace_root).expanduser() / PEVAL_CONFIG_FILENAME
        return candidate.resolve() if candidate.is_file() else None
    current = Path.cwd().resolve()
    while True:
        candidate = current / PEVAL_CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def apply_toml_config(
    config: ToolConfig,
    data: dict[str, Any],
    *,
    top_level_locale: bool = False,
    base_dir: Path | None = None,
) -> ToolConfig:
    if top_level_locale and "locale" in data:
        config = replace(config, locale=normalize_locale(data["locale"]))
    if "description" in data:
        raw_description = data["description"]
        if not isinstance(raw_description, str):
            raise ValueError("description must be a string")
        config = replace(config, description=raw_description.strip() or None)
    if "acp" in data:
        config = replace(config, acp_agents=_acp_agents(data["acp"]))
    if "analysis_eval_slug" in data:
        config = replace(
            config,
            analysis_eval_slug=_safe_path_segment(data["analysis_eval_slug"]),
        )
    if "harbor" in data:
        harbor = data.get("harbor")
        if not isinstance(harbor, dict):
            raise ValueError("harbor config must be a TOML table")
        if "roots" in harbor:
            raise ValueError(
                "legacy [harbor].roots is unsupported; initialize a new workspace "
                "and configure [[harbor.mounts]] with id and path"
            )
        # The Harbor runtime owns [harbor.host]. Peval accepts the sibling
        # section without interpreting or copying its fields.
        unknown = sorted(set(harbor) - {"datasets", "host", "mounts"})
        if unknown:
            raise ValueError(f"unknown harbor config field: {unknown[0]}")
        raw_datasets = harbor.get("datasets")
        datasets = list(config.harbor_datasets)
        if raw_datasets is not None:
            if not isinstance(raw_datasets, list):
                raise ValueError("harbor.datasets must be an array of tables")
            datasets = []
            seen_dataset_ids: set[str] = set()
            seen_dataset_paths: set[str] = set()
            for index, raw_dataset in enumerate(raw_datasets):
                if not isinstance(raw_dataset, dict):
                    raise ValueError(f"harbor.datasets[{index}] must be a TOML table")
                dataset_unknown = sorted(set(raw_dataset) - {"id", "path"})
                if dataset_unknown:
                    raise ValueError(
                        f"unknown harbor dataset field: {dataset_unknown[0]}"
                    )
                dataset_id = _harbor_id(raw_dataset.get("id"), kind="dataset")
                raw_path = raw_dataset.get("path")
                if not isinstance(raw_path, str) or not raw_path.strip():
                    raise ValueError("harbor dataset path must be a non-empty string")
                dataset_path = _lexical_config_path(raw_path, base_dir=base_dir)
                path_identity = os.path.normcase(os.path.normpath(dataset_path))
                if dataset_id in seen_dataset_ids:
                    raise ValueError(f"duplicate harbor dataset id: {dataset_id}")
                if path_identity in seen_dataset_paths:
                    raise ValueError(f"duplicate harbor dataset path: {dataset_path}")
                seen_dataset_ids.add(dataset_id)
                seen_dataset_paths.add(path_identity)
                datasets.append(HarborDataset(id=dataset_id, path=dataset_path))

        raw_mounts = harbor.get("mounts")
        if raw_mounts is None:
            raw_mounts = [
                {"id": mount.id, "path": mount.path, "dataset_ids": mount.dataset_ids}
                for mount in config.harbor_mounts
            ]
        if not isinstance(raw_mounts, list):
            raise ValueError("harbor.mounts must be an array of tables")
        mounts: list[HarborMount] = []
        seen_ids: set[str] = set()
        seen_paths: set[str] = set()
        dataset_id_set = {dataset.id for dataset in datasets}
        for index, raw_mount in enumerate(raw_mounts):
            if not isinstance(raw_mount, dict):
                raise ValueError(f"harbor.mounts[{index}] must be a TOML table")
            if "task_paths" in raw_mount:
                raise ValueError(
                    "harbor.mounts.task_paths is no longer supported; register each "
                    "Dataset with [[harbor.datasets]] id/path, then reference it with "
                    'dataset_ids = ["dataset-id"] in [[harbor.mounts]]'
                )
            mount_unknown = sorted(set(raw_mount) - {"id", "path", "dataset_ids"})
            if mount_unknown:
                raise ValueError(f"unknown harbor mount field: {mount_unknown[0]}")
            mount_id = _harbor_id(raw_mount.get("id"), kind="mount")
            raw_path = raw_mount.get("path")
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError("harbor mount path must be a non-empty string")
            mount_path = _lexical_config_path(raw_path, base_dir=base_dir)
            path_identity = os.path.normcase(os.path.normpath(mount_path))
            raw_dataset_ids = raw_mount.get("dataset_ids", [])
            if not isinstance(raw_dataset_ids, (list, tuple)):
                raise ValueError(
                    f"harbor.mounts[{index}].dataset_ids must be an array of strings"
                )
            dataset_ids: list[str] = []
            seen_mount_dataset_ids: set[str] = set()
            for raw_dataset_id in raw_dataset_ids:
                dataset_id = _harbor_id(raw_dataset_id, kind="dataset")
                if dataset_id in seen_mount_dataset_ids:
                    raise ValueError(
                        f"duplicate dataset id {dataset_id} in harbor mount {mount_id}"
                    )
                if dataset_id not in dataset_id_set:
                    raise ValueError(
                        f"harbor mount {mount_id} references unknown dataset id: "
                        f"{dataset_id}"
                    )
                seen_mount_dataset_ids.add(dataset_id)
                dataset_ids.append(dataset_id)
            if mount_id in seen_ids:
                raise ValueError(f"duplicate harbor mount id: {mount_id}")
            if path_identity in seen_paths:
                raise ValueError(f"duplicate harbor mount path: {mount_path}")
            seen_ids.add(mount_id)
            seen_paths.add(path_identity)
            mounts.append(
                HarborMount(
                    id=mount_id,
                    path=mount_path,
                    dataset_ids=tuple(dataset_ids),
                )
            )
        config = replace(
            config,
            harbor_datasets=tuple(datasets),
            harbor_mounts=tuple(mounts),
        )
    defaults = data.get("defaults", {})
    if defaults:
        if not isinstance(defaults, dict):
            raise ValueError("defaults config must be a TOML table")
        updates: dict[str, Any] = {}
        if "adapter" in defaults or "agent" in defaults:
            updates["adapter"] = str(
                defaults.get(
                    "adapter",
                    defaults.get("agent", config.adapter),
                )
            )
        if "agent_name" in defaults:
            updates["agent_name"] = _optional_string(defaults.get("agent_name"))
        if "agent_version" in defaults:
            updates["agent_version"] = str(defaults.get("agent_version"))
        if "locale" in defaults:
            updates["locale"] = normalize_locale(defaults.get("locale"))
        if "model" in defaults:
            updates["model"] = _optional_string(defaults.get("model"))
        if "max_content_chars" in defaults:
            updates["max_content_chars"] = int(defaults.get("max_content_chars"))
            updates["max_content_chars_explicit"] = True
        if "redact" in defaults:
            updates["redact"] = bool(defaults.get("redact"))
        config = replace(
            config,
            **updates,
        )
    db = data.get("db", {})
    if db:
        if not isinstance(db, dict):
            raise ValueError("db config must be a TOML table")
        db_updates: dict[str, str] = {}
        for key in [
            "messages_table",
            "session_id_column",
            "sequence_column",
            "message_column",
            "usage_column",
            "metadata_column",
        ]:
            if key in db:
                db_updates[key] = _safe_identifier(db[key])
        if db_updates:
            config = replace(config, db=replace(config.db, **db_updates))
    adapter_options_by_id, adapter_default_db_paths = _adapter_config_by_id(
        data.get("adapters", {}),
        base_dir=base_dir,
    )
    if adapter_default_db_paths:
        merged_default_db_paths = dict(config.adapter_default_db_paths)
        merged_default_db_paths.update(adapter_default_db_paths)
        config = replace(config, adapter_default_db_paths=merged_default_db_paths)
    if adapter_options_by_id:
        merged_options = {
            key: dict(value) for key, value in config.adapter_options_by_id.items()
        }
        for adapter_id, options in adapter_options_by_id.items():
            merged = dict(merged_options.get(adapter_id, {}))
            merged.update(options)
            merged_options[adapter_id] = merged
        config = replace(
            config,
            adapter_options_by_id=merged_options,
            adapter_options=_adapter_options_for(config.adapter, merged_options),
        )
    return config


def _acp_agents(value: Any) -> tuple[AcpAgent, ...]:
    if not isinstance(value, dict):
        raise ValueError("acp config must be a TOML table")
    unknown = sorted(set(value) - {"agents"})
    if unknown:
        raise ValueError(f"unknown acp config field: {unknown[0]}")
    raw_agents = value.get("agents", [])
    if not isinstance(raw_agents, list):
        raise ValueError("acp.agents must be an array of tables")
    agents: list[AcpAgent] = []
    seen: set[str] = set()
    for index, raw_agent in enumerate(raw_agents):
        if not isinstance(raw_agent, dict):
            raise ValueError(f"acp.agents[{index}] must be a TOML table")
        agent_unknown = sorted(set(raw_agent) - {"id", "title", "command", "args"})
        if agent_unknown:
            raise ValueError(f"unknown acp agent field: {agent_unknown[0]}")
        agent_id = raw_agent.get("id")
        if not isinstance(agent_id, str) or not ACP_AGENT_ID_RE.fullmatch(agent_id):
            raise ValueError(
                "acp agent id must be 1-64 lowercase letters, numbers, '.', '_' or '-'"
            )
        if agent_id in seen:
            raise ValueError(f"duplicate acp agent id: {agent_id}")
        title = raw_agent.get("title")
        command = raw_agent.get("command")
        raw_args = raw_agent.get("args", [])
        if not isinstance(title, str) or not title.strip():
            raise ValueError("acp agent title must be a non-empty string")
        if not isinstance(command, str) or not command.strip():
            raise ValueError("acp agent command must be a non-empty string")
        if not isinstance(raw_args, list) or not all(
            isinstance(item, str) for item in raw_args
        ):
            raise ValueError("acp agent args must be an array of strings")
        seen.add(agent_id)
        agents.append(
            AcpAgent(
                id=agent_id,
                title=title.strip(),
                command=command.strip(),
                args=tuple(raw_args),
            )
        )
    return tuple(agents)


def apply_overrides(config: ToolConfig, args: Any) -> ToolConfig:
    updates: dict[str, Any] = {}
    adapter = _adapter_override(getattr(args, "adapter", None))
    if adapter is not None:
        updates["adapter"] = adapter
    for field in [
        "agent_name",
        "agent_version",
        "model",
        "max_content_chars",
    ]:
        value = getattr(args, field, None)
        if value is not None:
            updates[field] = value
            if field == "max_content_chars":
                updates["max_content_chars_explicit"] = True
    if getattr(args, "no_redact", False):
        updates["redact"] = False
    adapter = str(updates.get("adapter", config.adapter))
    if updates or config.adapter_options_by_id:
        updates["adapter_options"] = _adapter_options_for(
            adapter,
            config.adapter_options_by_id,
        )
    return replace(config, **updates)


def config_for_adapter(config: ToolConfig, adapter: object) -> ToolConfig:
    adapter_id = _normalize_adapter_id(adapter)
    return replace(
        config,
        adapter=adapter_id,
        adapter_options=_adapter_options_for(adapter_id, config.adapter_options_by_id),
    )


def write_workspace_locale(config_path: Path, locale: str) -> None:
    normalized = normalize_locale(locale)
    path = config_path.expanduser()
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines(keepends=True)
    locale_line = f"locale = {json.dumps(normalized)}\n"
    first_table_index = next(
        (index for index, line in enumerate(lines) if line.lstrip().startswith("[")),
        len(lines),
    )
    for index, line in enumerate(lines[:first_table_index]):
        if line.lstrip().startswith("locale") and "=" in line:
            lines[index] = locale_line
            path.write_text("".join(lines), encoding="utf-8")
            return
    lines.insert(first_table_index, locale_line)
    path.write_text("".join(lines), encoding="utf-8")


def write_workspace_harbor_mounts(
    config_path: Path,
    mounts: tuple[HarborMount, ...],
) -> tuple[HarborMount, ...]:
    path = config_path.expanduser()
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    current = apply_toml_config(
        ToolConfig(workspace_root=str(path.parent)),
        data,
        top_level_locale=True,
        base_dir=path.parent,
    )
    _, validated_mounts = write_workspace_harbor_config(
        config_path,
        current.harbor_datasets,
        mounts,
    )
    return validated_mounts


def write_workspace_acp_agents(
    config_path: Path,
    agents: tuple[AcpAgent, ...],
) -> tuple[AcpAgent, ...]:
    path = config_path.expanduser()
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines(keepends=True)
    for start, end in reversed(_acp_table_ranges(lines)):
        del lines[start:end]
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += "\n"
    if agents:
        if lines:
            lines.append("\n")
        for index, agent in enumerate(agents):
            if index:
                lines.append("\n")
            lines.extend(
                [
                    "[[acp.agents]]\n",
                    f"id = {json.dumps(agent.id)}\n",
                    f"title = {json.dumps(agent.title, ensure_ascii=False)}\n",
                    f"command = {json.dumps(agent.command, ensure_ascii=False)}\n",
                ]
            )
            if agent.args:
                lines.append(
                    f"args = {json.dumps(list(agent.args), ensure_ascii=False)}\n"
                )
    rendered = "".join(lines)
    data = tomllib.loads(rendered) if rendered.strip() else {}
    validated_config = apply_toml_config(
        ToolConfig(workspace_root=str(path.parent)),
        data,
        top_level_locale=True,
        base_dir=path.parent,
    )
    _atomic_write_text(path, rendered)
    return validated_config.acp_agents


def write_workspace_harbor_config(
    config_path: Path,
    datasets: tuple[HarborDataset, ...],
    mounts: tuple[HarborMount, ...],
) -> tuple[tuple[HarborDataset, ...], tuple[HarborMount, ...]]:
    path = config_path.expanduser()
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines(keepends=True)
    for start, end in reversed(_harbor_table_ranges(lines)):
        del lines[start:end]
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and not lines[-1].endswith(("\n", "\r")):
        lines[-1] += "\n"
    if datasets or mounts:
        if lines:
            lines.append("\n")
        for index, dataset in enumerate(datasets):
            if index:
                lines.append("\n")
            lines.extend(
                [
                    "[[harbor.datasets]]\n",
                    f"id = {json.dumps(dataset.id)}\n",
                    f"path = {json.dumps(_stored_harbor_path(dataset.path, path.parent))}\n",
                ]
            )
        if datasets and mounts:
            lines.append("\n")
        for index, mount in enumerate(mounts):
            if index:
                lines.append("\n")
            lines.extend(
                [
                    "[[harbor.mounts]]\n",
                    f"id = {json.dumps(mount.id)}\n",
                    f"path = {json.dumps(_stored_harbor_path(mount.path, path.parent))}\n",
                ]
            )
            if mount.dataset_ids:
                lines.append(
                    "dataset_ids = "
                    f"{json.dumps(list(mount.dataset_ids), ensure_ascii=False)}\n"
                )
    rendered = "".join(lines)
    data = tomllib.loads(rendered) if rendered.strip() else {}
    validated_config = apply_toml_config(
        ToolConfig(workspace_root=str(path.parent)),
        data,
        top_level_locale=True,
        base_dir=path.parent,
    )
    validate_harbor_mount_paths(
        validated_config.harbor_mounts,
        validated_config.harbor_datasets,
    )
    _atomic_write_text(path, rendered)
    return validated_config.harbor_datasets, validated_config.harbor_mounts


def write_workspace_harbor_datasets(
    config_path: Path,
    datasets: tuple[HarborDataset, ...],
    mounts: tuple[HarborMount, ...],
) -> tuple[HarborDataset, ...]:
    validated_datasets, _ = write_workspace_harbor_config(
        config_path,
        datasets,
        mounts,
    )
    return validated_datasets


def validate_harbor_mount_paths(
    mounts: tuple[HarborMount, ...],
    datasets: tuple[HarborDataset, ...] = (),
) -> None:
    datasets_by_id = {dataset.id: dataset for dataset in datasets}
    seen_dataset_paths: set[str] = set()
    for dataset in datasets:
        identity = os.path.normcase(os.path.normpath(dataset.path))
        if identity in seen_dataset_paths:
            raise ValueError(f"duplicate harbor dataset path: {dataset.path}")
        seen_dataset_paths.add(identity)
        _validate_harbor_dataset_directory(dataset)
    for mount in mounts:
        _validate_existing_unlinked_directory(
            mount.path,
            label=f"Harbor Jobs path for {mount.id}",
        )
        for dataset_id in mount.dataset_ids:
            if dataset_id not in datasets_by_id:
                raise ValueError(
                    f"harbor mount {mount.id} references unknown dataset id: "
                    f"{dataset_id}"
                )


def harbor_dataset_paths_for_mount(
    config: ToolConfig,
    mount: HarborMount,
) -> tuple[str, ...]:
    datasets_by_id = {dataset.id: dataset.path for dataset in config.harbor_datasets}
    return tuple(datasets_by_id[dataset_id] for dataset_id in mount.dataset_ids)


def _validate_harbor_dataset_directory(dataset: HarborDataset) -> None:
    _validate_existing_unlinked_directory(
        dataset.path,
        label=f"Harbor Dataset path for {dataset.id}",
    )


def _validate_existing_unlinked_directory(value: str, *, label: str) -> Path:
    path = Path(value).expanduser()
    current = path
    while True:
        try:
            if current.is_symlink():
                raise ValueError(f"{label} traverses a symlink: {current}")
        except OSError as exc:
            raise ValueError(f"cannot inspect {label} {current}: {exc}") from exc
        if current.parent == current:
            break
        current = current.parent
    if not path.is_dir():
        raise ValueError(f"{label} not found: {path}")
    return path


def _harbor_table_ranges(lines: list[str]) -> list[tuple[int, int]]:
    starts = [
        index
        for index, line in enumerate(lines)
        if HARBOR_MOUNT_HEADER_RE.match(line) or HARBOR_DATASET_HEADER_RE.match(line)
    ]
    ranges: list[tuple[int, int]] = []
    for start in starts:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if lines[index].lstrip().startswith("["):
                end = index
                break
        ranges.append((start, end))
    return ranges


def _acp_table_ranges(lines: list[str]) -> list[tuple[int, int]]:
    starts = [
        index for index, line in enumerate(lines) if ACP_AGENT_HEADER_RE.match(line)
    ]
    ranges: list[tuple[int, int]] = []
    for start in starts:
        end = len(lines)
        for index in range(start + 1, len(lines)):
            if lines[index].lstrip().startswith("["):
                end = index
                break
        ranges.append((start, end))
    return ranges


def _harbor_id(value: object, *, kind: str) -> str:
    identifier = str(value or "").strip()
    if HARBOR_ID_RE.fullmatch(identifier) is None:
        raise ValueError(f"harbor {kind} id must be a lowercase path-safe identifier")
    return identifier


def unique_harbor_id_from_path(
    value: object,
    *,
    fallback: str,
    existing_ids: Iterable[str],
    base_dir: Path | None = None,
) -> str:
    text = _lexical_config_path(value, base_dir=base_dir).rstrip("/\\")
    basename = (
        PureWindowsPath(text).name
        if is_windows_absolute_like_path(text)
        else Path(text).name
    )
    occupied = set(existing_ids)
    if HARBOR_ID_RE.fullmatch(basename) is not None and basename not in occupied:
        return basename

    base = basename if HARBOR_ID_RE.fullmatch(basename) is not None else fallback
    while True:
        suffix = secrets.token_hex(3)
        prefix = base[: 63 - len(suffix)].rstrip("_-")
        candidate = f"{prefix}-{suffix}"
        if candidate not in occupied:
            return candidate


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("workspace config must not be a symbolic link")
    if path.exists() and not stat.S_ISREG(path.stat(follow_symlinks=False).st_mode):
        raise ValueError("workspace config must be a regular file")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _stored_harbor_path(value: str, base_dir: Path) -> str:
    text = str(value).strip()
    if is_windows_absolute_like_path(text):
        return text
    try:
        return os.path.relpath(Path(text), base_dir)
    except ValueError:
        return text


def write_workspace_adapter_default_db(
    config_path: Path,
    adapter: object,
    default_db_path: str | None,
) -> str | None:
    adapter_id = _normalize_adapter_id(adapter)
    raw_path = str(default_db_path or "").strip()
    path = config_path.expanduser()
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines(keepends=True)
    table_range = _adapter_table_range(lines, adapter_id)

    if not raw_path:
        if table_range is not None:
            start, end = table_range
            existing = _default_db_path_line_index(lines, start + 1, end)
            if existing is not None:
                del lines[existing]
                path.write_text("".join(lines), encoding="utf-8")
        return None

    stored_path = display_config_path(raw_path, base_dir=path.parent)
    config_line = f"default_db_path = {json.dumps(stored_path)}\n"
    if table_range is None:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] = lines[-1] + "\n"
        if lines and "".join(lines).strip():
            lines.append("\n")
        lines.extend([f"[{_adapter_table_key(adapter_id)}]\n", config_line])
    else:
        start, end = table_range
        existing = _default_db_path_line_index(lines, start + 1, end)
        if existing is None:
            lines.insert(start + 1, config_line)
        else:
            lines[existing] = config_line
    path.write_text("".join(lines), encoding="utf-8")
    return _resolve_config_path(stored_path, base_dir=path.parent)


def _adapter_table_range(
    lines: list[str],
    adapter_id: str,
) -> tuple[int, int] | None:
    for index, line in enumerate(lines):
        if not _is_adapter_table_header(line, adapter_id):
            continue
        end = next(
            (
                candidate
                for candidate in range(index + 1, len(lines))
                if _is_table_header(lines[candidate])
            ),
            len(lines),
        )
        return index, end
    return None


def _default_db_path_line_index(
    lines: list[str],
    start: int,
    end: int,
) -> int | None:
    for index in range(start, end):
        if DEFAULT_DB_PATH_RE.match(lines[index]):
            return index
    return None


def _is_table_header(line: str) -> bool:
    return bool(TABLE_HEADER_RE.match(line))


def _is_adapter_table_header(line: str, adapter_id: str) -> bool:
    match = TABLE_HEADER_RE.match(line)
    if not match:
        return False
    header = match.group(1).strip()
    try:
        parsed = tomllib.loads(f"[{header}]\n__peval_marker = true\n")
    except tomllib.TOMLDecodeError:
        return False
    adapters = parsed.get("adapters")
    if not isinstance(adapters, dict):
        return False
    adapter_config = adapters.get(adapter_id)
    return (
        isinstance(adapter_config, dict)
        and adapter_config.get("__peval_marker") is True
    )


def _adapter_table_key(adapter_id: str) -> str:
    if IDENTIFIER_RE.match(adapter_id):
        return f"adapters.{adapter_id}"
    return f"adapters.{json.dumps(adapter_id)}"


def _adapter_override(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        adapter = None
        for item in value:
            text = str(item)
            if "=" in text:
                continue
            adapter = text
        return _normalize_adapter_id(adapter) if adapter is not None else None
    return _normalize_adapter_id(value)


def _adapter_config_by_id(
    value: object,
    *,
    base_dir: Path | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    if not value:
        return {}, {}
    if not isinstance(value, dict):
        raise ValueError("adapters config must be a TOML table")
    options: dict[str, dict[str, Any]] = {}
    default_db_paths: dict[str, str] = {}
    for key, raw_options in value.items():
        if not isinstance(raw_options, dict):
            raise ValueError(f"adapter options for {key} must be a TOML table")
        adapter_id = str(key).strip().lower()
        adapter_options = dict(raw_options)
        if "default_db_path" in adapter_options:
            default_db_paths[adapter_id] = _resolve_config_path(
                adapter_options.pop("default_db_path"),
                base_dir=base_dir,
            )
        options[adapter_id] = adapter_options
    return options, default_db_paths


def _resolve_config_path(value: object, *, base_dir: Path | None = None) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("default_db_path must not be empty")
    if is_windows_absolute_like_path(text):
        return resolve_windows_absolute_like_path(text)
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = (base_dir or Path.cwd()) / path
    return str(path.resolve())


def _lexical_config_path(value: object, *, base_dir: Path | None = None) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("harbor root must not be empty")
    if is_windows_absolute_like_path(text):
        return lexical_windows_absolute_like_path(text)
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = (base_dir or Path.cwd()) / path
    return os.path.abspath(path)


def display_config_path(value: object, *, base_dir: Path | None = None) -> str:
    text = str(value).strip()
    if not text:
        return text
    if text.startswith("~"):
        return text
    if is_windows_absolute_like_path(text):
        return text
    path = Path(text).expanduser()
    if not path.is_absolute():
        return text
    home = Path.home().resolve()
    try:
        relative = path.resolve().relative_to(home)
    except ValueError:
        return text
    return "~" if not relative.parts else "~/" + relative.as_posix()


def is_windows_absolute_like_path(path: str) -> bool:
    return (
        bool(WINDOWS_DRIVE_PATH_RE.match(path))
        or path.startswith("\\\\")
        or path.startswith("//")
    )


def resolve_windows_absolute_like_path(
    raw_path: str,
    *,
    windows_mount_root: Path | None = None,
) -> str:
    if os.name == "nt":
        return str(Path(raw_path).expanduser())
    original = Path(raw_path).expanduser()
    if original.exists():
        return str(original.resolve())
    mapped = windows_drive_mount_path(
        raw_path,
        windows_mount_root or WINDOWS_DRIVE_MOUNT_ROOT,
    )
    if mapped is not None and mapped.exists():
        return str(mapped.resolve())
    return raw_path


def lexical_windows_absolute_like_path(
    raw_path: str,
    *,
    windows_mount_root: Path | None = None,
) -> str:
    """Map an existing Windows drive path without resolving symbolic links."""

    if os.name == "nt":
        return os.path.abspath(Path(raw_path).expanduser())
    mapped = windows_drive_mount_path(
        raw_path,
        windows_mount_root or WINDOWS_DRIVE_MOUNT_ROOT,
    )
    if mapped is not None and mapped.exists():
        return os.path.abspath(mapped)
    original = Path(raw_path).expanduser()
    if original.exists():
        return os.path.abspath(original)
    return raw_path


def windows_drive_mount_path(raw_path: str, mount_root: Path) -> Path | None:
    if not WINDOWS_DRIVE_PATH_RE.match(raw_path):
        return None
    drive = raw_path[0].lower()
    rest = raw_path[2:].lstrip("\\/")
    parts = [part for part in re.split(r"[\\/]+", rest) if part]
    return Path(mount_root) / drive / Path(*parts)


def _adapter_options_for(
    adapter: str,
    adapter_options_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return dict(adapter_options_by_id.get(str(adapter).strip().lower(), {}))


def _normalize_adapter_id(adapter: object) -> str:
    text = str(adapter or "").strip().lower()
    if not text:
        raise ValueError("adapter id is required")
    return text


def _safe_identifier(value: object) -> str:
    text = str(value)
    if not IDENTIFIER_RE.match(text):
        raise ValueError(f"unsafe SQL identifier: {text}")
    return text


def _safe_path_segment(value: object) -> str:
    text = str(value).strip()
    if not text or text in {".", ".."} or "/" in text or "\\" in text:
        raise ValueError(f"unsafe path segment: {text}")
    return text


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
