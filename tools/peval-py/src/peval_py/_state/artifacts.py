from __future__ import annotations

import hashlib
import json
import shutil
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_ANALYSIS_EVAL_SLUG = "default"
AGENT_DIR = "agent"
TRAJECTORY_FILENAME = "trajectory.json"
TRAJECTORY_META_FILENAME = "trajectory_meta.json"


@dataclass(frozen=True)
class TrialArtifacts:
    trajectory_path: Path
    meta_path: Path


def source_key_for_trial(
    eval_slug: str,
    source: dict[str, Any],
    trajectory: dict[str, Any],
    meta: dict[str, Any],
) -> str:
    payload = trial_cell_components(
        eval_slug=eval_slug,
        source=source,
        trajectory=trajectory,
        meta=meta,
    )
    return source_key_for_components(payload)


def source_key_for_components(components: dict[str, str]) -> str:
    return (
        "cell_"
        + hashlib.sha256(
            json.dumps(components, sort_keys=True).encode("utf-8")
        ).hexdigest()[:20]
    )


def trial_cell_components(
    *,
    eval_slug: str,
    source: dict[str, Any],
    trajectory: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, str]:
    agent = trajectory.get("agent")
    trajectory_agent = agent.get("name") if isinstance(agent, dict) else None
    return {
        "eval_slug": artifact_segment(eval_slug, DEFAULT_ANALYSIS_EVAL_SLUG),
        "agent_id": artifact_segment(
            source.get("artifact_agent_id")
            or source.get("agent_name")
            or trajectory_agent
            or meta.get("adapter")
            or source.get("adapter"),
            "unknown-agent",
        ),
        "session_id": artifact_segment(
            source.get("artifact_session_id")
            or trajectory.get("session_id")
            or source.get("session_id")
            or meta.get("trial_key"),
            "unknown-session",
        ),
        "cell_key": required_artifact_segment(meta.get("trial_key"), "trial_key"),
    }


def source_key_for_trial_cell_components(
    *,
    eval_slug: str,
    agent_id: str,
    session_id: str,
    cell_key: str,
) -> str:
    return source_key_for_components(
        {
            "eval_slug": artifact_segment(eval_slug, DEFAULT_ANALYSIS_EVAL_SLUG),
            "agent_id": artifact_segment(agent_id, "unknown-agent"),
            "session_id": artifact_segment(session_id, "unknown-session"),
            "cell_key": required_artifact_segment(cell_key, "trial_key"),
        }
    )


def normalized_optional_path(path: str | None) -> str | None:
    if not path:
        return None
    return str(Path(path).expanduser().resolve())


def workspace_analysis_eval_slug(paths: Any) -> str:
    if not paths.config_path.is_file():
        return DEFAULT_ANALYSIS_EVAL_SLUG
    try:
        data = tomllib.loads(paths.config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return DEFAULT_ANALYSIS_EVAL_SLUG
    value = data.get("analysis_eval_slug")
    return artifact_segment(value, DEFAULT_ANALYSIS_EVAL_SLUG)


def trial_cell_dir(
    root: Path,
    *,
    eval_slug: str,
    source: dict[str, Any],
    trajectory: dict[str, Any],
    meta: dict[str, Any],
) -> Path:
    components = trial_cell_components(
        eval_slug=eval_slug,
        source=source,
        trajectory=trajectory,
        meta=meta,
    )
    return (
        root
        / "runs"
        / components["eval_slug"]
        / components["agent_id"]
        / components["session_id"]
        / components["cell_key"]
    )


def trial_artifacts(artifact_dir: Path) -> TrialArtifacts:
    agent_dir = artifact_dir / AGENT_DIR
    return TrialArtifacts(
        trajectory_path=agent_dir / TRAJECTORY_FILENAME,
        meta_path=agent_dir / TRAJECTORY_META_FILENAME,
    )


def artifact_segment(value: Any, fallback: str) -> str:
    text = str(value or "").strip()
    safe = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text
    ).strip("._")
    return safe or fallback


def required_artifact_segment(value: Any, label: str) -> str:
    text = str(value or "").strip()
    safe = "".join(
        char if char.isalnum() or char in {"-", "_", "."} else "_" for char in text
    ).strip("._")
    if not safe:
        raise ValueError(f"{label} is required for Trial cell artifacts")
    return safe


def relative_to_root(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def write_json_file(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def write_json_files_atomically(values: list[tuple[Path, Any]]) -> None:
    """Stage a related JSON set before replacing any destination.

    Replacement is rolled back on an ordinary I/O failure, so callers never
    retain a newly written half of a Trial trajectory/meta pair.
    """

    write_files_atomically(
        [
            (
                path,
                (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode(
                    "utf-8"
                ),
            )
            for path, value in values
        ]
    )


def write_files_atomically(values: list[tuple[Path, bytes]]) -> None:
    """Atomically replace a related set of already-serialized files."""

    serialized = [(path, bytes(value)) for path, value in values]
    token = uuid.uuid4().hex
    staged: list[tuple[Path, Path]] = []
    originals: dict[Path, bytes | None] = {}
    replaced: list[Path] = []
    try:
        for path, content in serialized:
            path.parent.mkdir(parents=True, exist_ok=True)
            originals[path] = path.read_bytes() if path.is_file() else None
            temporary = path.with_name(f".{path.name}.{token}.tmp")
            temporary.write_bytes(content)
            staged.append((path, temporary))
        for path, temporary in staged:
            temporary.replace(path)
            replaced.append(path)
    except Exception:
        for path in reversed(replaced):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                rollback = path.with_name(f".{path.name}.{token}.rollback")
                rollback.write_bytes(original)
                rollback.replace(path)
        raise
    finally:
        for _, temporary in staged:
            temporary.unlink(missing_ok=True)


def write_text_file(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(value, encoding="utf-8")
    tmp.replace(path)


def read_json_object(path: Path) -> dict[str, Any]:
    return json_object(path.read_text(encoding="utf-8"), str(path))


def json_object(value: str, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"failed to parse {label}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return parsed


def remove_artifact_dir(root: Path, artifact_dir: Path) -> None:
    resolved_root = root.resolve()
    resolved_artifact = artifact_dir.resolve()
    if (
        resolved_artifact == resolved_root
        or resolved_root not in resolved_artifact.parents
    ):
        raise ValueError(
            f"refusing to remove artifact directory outside workspace: {artifact_dir}"
        )
    if resolved_artifact.is_dir():
        shutil.rmtree(resolved_artifact)
