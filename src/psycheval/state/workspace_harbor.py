from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Iterator

from psycheval._state.annotations import optional_str
from psycheval._state.artifacts import (
    artifact_segment,
    read_json_object,
    source_key_for_components,
)
from psycheval.atif import (
    ATIF_VERSION,
    convert_db,
    convert_path,
    validate_atif_trajectory,
)
from psycheval.config import ToolConfig
from psycheval.report import project_meta_from_atif
from psycheval.report.builder import iso_timestamp_ms
from psycheval.report.metrics import final_metric
from psycheval.report.timing import step_meta_reports, trial_active_duration_ms
from psycheval.state.harbor_evidence import HarborEvidence
from psycheval.state.workspace_source_models import (
    HARBOR_ADAPTER,
    HARBOR_ANALYSIS_MD_FILE,
    HARBOR_HERMES_TELEMETRY_FILES,
    HARBOR_OPENCODE_TELEMETRY_FILES,
    HARBOR_PSYCHEVO_TELEMETRY_FILES,
    HARBOR_SOURCE_FILES,
    HARBOR_SOURCE_KIND,
    HarborTelemetry,
    SourceCandidate,
)

if TYPE_CHECKING:
    from psycheval._harbor_trials import HarborTrialBundle, HarborTrialEntry

HARBOR_ANALYSIS_MAX_BYTES = 20 * 1024 * 1024


def is_harbor_source(value: dict[str, Any]) -> bool:
    return value.get("kind") == HARBOR_SOURCE_KIND


def _direct_harbor_candidate(
    bundle: HarborTrialBundle,
    entry: HarborTrialEntry,
) -> SourceCandidate:
    identity = {
        "kind": HARBOR_SOURCE_KIND,
        "path": str(bundle.trial_dir),
        "step_name": entry.step_name,
    }
    source_key = source_key_for_components(identity)
    internal_ref = entry.source_ref or f"direct-harbor:{source_key}"
    analysis_relative_path = _harbor_analysis_relative_path(bundle.trial_dir)
    return SourceCandidate(
        source_ref=internal_ref,
        kind=HARBOR_SOURCE_KIND,
        path=bundle.trial_dir,
        data_path=entry.data_dir,
        fingerprint=bundle.evidence.revision,
        source_key=source_key,
        mount_id=entry.mount_id,
        job_name=bundle.trial_dir.parent.name,
        trial_name=bundle.trial_dir.name,
        multi_step=entry.step_name is not None,
        containment_root=bundle.jobs_root,
        task_paths=entry.task_paths,
        harbor_evidence=bundle.evidence,
        harbor_analysis_relative_path=analysis_relative_path,
        step_name=entry.step_name,
        step_index=entry.step_index,
        step_count=entry.step_count,
        step_result=entry.result,
        trial_result=entry.trial_result,
        entry_warnings=entry.warnings,
    )


def _harbor_source_key_payload(
    mount_id: str, job_name: str, trial_name: str, step_name: str | None = None
) -> dict[str, str]:
    payload = {
        "kind": HARBOR_SOURCE_KIND,
        "mount_id": mount_id,
        "job_name": job_name,
        "trial_name": trial_name,
    }
    if step_name is not None:
        payload["step_name"] = step_name
    return payload


def _harbor_trial_key(
    mount_id: str,
    job_name: str,
    trial_name: str,
    step_name: str | None = None,
) -> str:
    return source_key_for_components(
        _harbor_source_key_payload(mount_id, job_name, trial_name, step_name)
    )


def _compatible_harbor_trajectory(
    trajectory: dict[str, Any], path: Path
) -> tuple[dict[str, Any], str]:
    source_schema = str(trajectory.get("schema_version") or "")
    projected = deepcopy(trajectory)
    if source_schema != ATIF_VERSION:
        match = re.fullmatch(r"ATIF-v1\.(\d+)", source_schema)
        if match is None or int(match.group(1)) > 7:
            raise ValueError(
                f"{path}.schema_version is not a supported Harbor ATIF version: "
                f"{source_schema or '<missing>'}"
            )
        projected["schema_version"] = ATIF_VERSION
    validate_atif_trajectory(projected, str(path))
    return projected, source_schema


def _project_harbor_metrics(
    trajectory: dict[str, Any],
    result_json: dict[str, Any] | None,
    telemetry: HarborTelemetry | None,
) -> dict[str, Any]:
    projected = deepcopy(trajectory)
    existing = projected.get("final_metrics")
    metrics = deepcopy(existing) if isinstance(existing, dict) else {}
    supplemental = telemetry.final_metrics if telemetry is not None else {}
    result_metrics = _result_final_metrics(result_json)
    for key in (
        "total_prompt_tokens",
        "total_completion_tokens",
        "total_cached_tokens",
        "total_cost_usd",
    ):
        for source in (supplemental, result_metrics):
            if key not in metrics and source.get(key) is not None:
                metrics[key] = source[key]
    metrics.setdefault("total_steps", len(projected.get("steps") or []))

    extra = (
        deepcopy(metrics.get("extra")) if isinstance(metrics.get("extra"), dict) else {}
    )
    steps = [step for step in projected.get("steps") or [] if isinstance(step, dict)]
    derived = {
        "total_turns": sum(step.get("source") == "agent" for step in steps),
        "total_tool_calls": sum(len(step.get("tool_calls") or []) for step in steps),
        "total_tool_errors": _derived_tool_errors(steps),
    }
    for key, value in derived.items():
        if key in extra:
            continue
        supplemental_value = final_metric(supplemental, key)
        extra[key] = supplemental_value if supplemental_value is not None else value
    supplemental_extra = (
        supplemental.get("extra") if isinstance(supplemental.get("extra"), dict) else {}
    )
    for key, value in supplemental_extra.items():
        extra.setdefault(key, deepcopy(value))
    if extra:
        metrics["extra"] = extra
    projected["final_metrics"] = metrics
    validate_atif_trajectory(projected)
    return projected


def _derived_tool_errors(steps: list[dict[str, Any]]) -> int:
    error_call_ids: set[str] = set()
    anonymous_errors = 0
    for step in steps:
        for result in (step.get("observation") or {}).get("results") or []:
            if not isinstance(result, dict):
                continue
            extra = result.get("extra") if isinstance(result.get("extra"), dict) else {}
            status = str(extra.get("status") or "").lower()
            is_error = extra.get("is_error") is True or any(
                marker in status for marker in ("error", "fail")
            )
            if not is_error:
                continue
            call_id = optional_str(result.get("source_call_id"))
            if call_id:
                error_call_ids.add(call_id)
            else:
                anonymous_errors += 1
    return len(error_call_ids) + anonymous_errors


def _result_final_metrics(result_json: dict[str, Any] | None) -> dict[str, Any]:
    agent_result = (
        result_json.get("agent_result")
        if isinstance((result_json or {}).get("agent_result"), dict)
        else {}
    )
    metrics: dict[str, Any] = {}
    for source_key, target_key in (
        ("n_input_tokens", "total_prompt_tokens"),
        ("n_output_tokens", "total_completion_tokens"),
        ("n_cache_tokens", "total_cached_tokens"),
    ):
        value = agent_result.get(source_key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            metrics[target_key] = value
    cost = agent_result.get("cost_usd")
    if isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost >= 0:
        metrics["total_cost_usd"] = cost
    return metrics


def _harbor_telemetry(
    candidate: SourceCandidate,
    trajectory: dict[str, Any],
) -> tuple[HarborTelemetry | None, str | None]:
    agent = trajectory.get("agent") if isinstance(trajectory.get("agent"), dict) else {}
    adapter = str(agent.get("name") or "").lower()
    telemetry_files = {
        "opencode": HARBOR_OPENCODE_TELEMETRY_FILES,
        "psychevo": HARBOR_PSYCHEVO_TELEMETRY_FILES,
        "hermes": HARBOR_HERMES_TELEMETRY_FILES,
    }.get(adapter)
    if telemetry_files is None:
        return None, None
    session_id = optional_str(trajectory.get("session_id"))
    if not session_id:
        return None, None
    data_path = candidate.data_path or candidate.path
    primary = data_path / telemetry_files[0]
    try:
        primary_stat = primary.stat(follow_symlinks=False)
    except FileNotFoundError:
        return None, None
    except OSError as exc:
        return None, f"supplemental {adapter} telemetry ignored: {exc}"
    if not stat.S_ISREG(primary_stat.st_mode):
        return None, f"supplemental {adapter} telemetry ignored: not a regular file"
    try:
        files = telemetry_files
        if adapter == "psychevo":
            if (
                Path(session_id).name != session_id
                or "\\" in session_id
                or session_id in {".", ".."}
            ):
                raise ValueError(
                    "Psychevo telemetry session ID is not a safe path segment"
                )
            files = (
                *files,
                f"agent/sessions/{session_id}/events.jsonl",
            )
        contents, revision = _read_consistent_telemetry_files(
            data_path,
            candidate.containment_root or candidate.path,
            files,
        )
        conversion = _convert_harbor_telemetry(
            adapter,
            contents,
            session_id,
        )
        if not _telemetry_aligns(
            trajectory,
            conversion.trajectory,
            require_session_identity=adapter != "hermes",
        ):
            raise ValueError(f"{adapter} telemetry does not align with Harbor ATIF")
        started = conversion.started_at_ms or 0
        steps = step_meta_reports(
            conversion.steps_meta,
            started,
            conversion.timestamp_semantics,
        )
        return (
            HarborTelemetry(
                steps=steps,
                duration_ms=trial_active_duration_ms(conversion.steps_meta, steps),
                final_metrics=deepcopy(
                    conversion.trajectory.get("final_metrics") or {}
                ),
                revision=revision,
            ),
            None,
        )
    except Exception as exc:  # noqa: BLE001 - supplemental evidence is optional.
        return None, f"supplemental {adapter} telemetry ignored: {exc}"


def _convert_harbor_telemetry(
    adapter: str,
    contents: dict[str, bytes],
    session_id: str,
):
    with tempfile.TemporaryDirectory(prefix=f"peval-harbor-{adapter}-") as tmp:
        temporary_root = Path(tmp)
        if adapter == "hermes":
            export_path = temporary_root / "hermes-session.jsonl"
            export_path.write_bytes(contents[HARBOR_HERMES_TELEMETRY_FILES[0]])
            return convert_path(str(export_path), ToolConfig(adapter="hermes"))

        files = (
            HARBOR_OPENCODE_TELEMETRY_FILES
            if adapter == "opencode"
            else HARBOR_PSYCHEVO_TELEMETRY_FILES
        )
        database_name = Path(files[0]).name
        temporary_database = temporary_root / database_name
        for relative, content in contents.items():
            name = Path(relative).name
            if name.startswith(database_name):
                (temporary_root / name).write_bytes(content)
            elif adapter == "psychevo" and name == "events.jsonl":
                trace = temporary_root / "sessions" / session_id / name
                trace.parent.mkdir(parents=True)
                trace.write_bytes(content)
        return convert_db(
            str(temporary_database),
            session_id,
            ToolConfig(adapter=adapter),
        )


def _telemetry_aligns(
    trajectory: dict[str, Any],
    telemetry_trajectory: dict[str, Any],
    *,
    require_session_identity: bool = True,
) -> bool:
    source_session_id = optional_str(trajectory.get("session_id"))
    telemetry_session_id = optional_str(telemetry_trajectory.get("session_id"))
    if require_session_identity and (
        not source_session_id or source_session_id != telemetry_session_id
    ):
        return False
    source_steps = trajectory.get("steps")
    telemetry_steps = telemetry_trajectory.get("steps")
    if not isinstance(source_steps, list) or not isinstance(telemetry_steps, list):
        return False
    if len(source_steps) != len(telemetry_steps):
        return False
    for source, telemetry in zip(source_steps, telemetry_steps, strict=True):
        if not isinstance(source, dict) or not isinstance(telemetry, dict):
            return False
        if (source.get("step_id"), source.get("source")) != (
            telemetry.get("step_id"),
            telemetry.get("source"),
        ):
            return False
        source_calls = [
            call.get("tool_call_id")
            for call in source.get("tool_calls") or []
            if isinstance(call, dict)
        ]
        telemetry_calls = [
            call.get("tool_call_id")
            for call in telemetry.get("tool_calls") or []
            if isinstance(call, dict)
        ]
        if source_calls != telemetry_calls:
            return False
        if not _alignment_messages_match(
            source.get("message"), telemetry.get("message")
        ):
            return False
        source_call_shapes = [
            (
                call.get("tool_call_id"),
                call.get("function_name"),
                call.get("arguments"),
            )
            for call in source.get("tool_calls") or []
            if isinstance(call, dict)
        ]
        telemetry_call_shapes = [
            (
                call.get("tool_call_id"),
                call.get("function_name"),
                call.get("arguments"),
            )
            for call in telemetry.get("tool_calls") or []
            if isinstance(call, dict)
        ]
        if source_call_shapes != telemetry_call_shapes:
            return False
    return True


def _alignment_messages_match(left: Any, right: Any) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return left == right
    return bool(_alignment_message_variants(left) & _alignment_message_variants(right))


def _alignment_message_variants(value: str) -> set[str]:
    variants = {value}
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, str):
        variants.add(decoded)
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        inner = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        variants.add(inner)
    return variants


def _read_consistent_telemetry_files(
    trial_dir: Path,
    containment_root: Path,
    relative_files: Iterable[str],
) -> tuple[dict[str, bytes], str]:
    files = tuple(relative_files)
    last_error: Exception | None = None
    for _attempt in range(3):
        before = _file_signature(trial_dir, files)
        contents: dict[str, bytes] = {}
        try:
            for relative in files:
                path = trial_dir / relative
                try:
                    file_stat = path.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if not stat.S_ISREG(file_stat.st_mode):
                    raise ValueError(
                        f"Harbor telemetry file must be a regular file: {path}"
                    )
                contents[relative] = _read_bytes_no_follow(containment_root, path)
        except Exception as exc:  # noqa: BLE001 - retry only if inputs changed.
            last_error = exc
            if before != _file_signature(trial_dir, files):
                continue
            raise
        if before == _file_signature(trial_dir, files):
            if files[0] not in contents:
                raise ValueError(f"Harbor telemetry source not found: {trial_dir}")
            digest = hashlib.sha256()
            for relative, content in sorted(contents.items()):
                digest.update(relative.encode("utf-8") + b"\0" + content + b"\0")
            return contents, digest.hexdigest()
    if last_error is not None:
        raise last_error
    raise ValueError(f"Harbor telemetry changed while it was being read: {trial_dir}")


def _result_duration_ms(
    result_json: dict[str, Any] | None,
    nested_key: str | None = None,
) -> int | None:
    source: Any = result_json
    if nested_key is not None:
        source = (result_json or {}).get(nested_key)
    if not isinstance(source, dict):
        return None
    started = iso_timestamp_ms(source.get("started_at"))
    finished = iso_timestamp_ms(source.get("finished_at"))
    if started is None or finished is None:
        return None
    return max(0, finished - started)


def _result_only_meta(
    candidate: SourceCandidate,
    config_json: dict[str, Any] | None,
    lock_json: dict[str, Any] | None,
    result_json: dict[str, Any] | None,
    revision: str,
    evidence: HarborEvidence,
    *,
    trial_result_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evaluation = _evaluation(result_json)
    identity_hash = hashlib.sha256(candidate.source_ref.encode("utf-8")).hexdigest()[
        :10
    ]
    trial_key = (
        f"harbor-{artifact_segment(candidate.trial_name, 'trial')[:48]}-{identity_hash}"
    )
    trial_name = evidence.trial_name
    data_ref = {
        "kind": HARBOR_SOURCE_KIND,
        "label": f"{candidate.job_name}/{candidate.trial_name}",
        "path": str(candidate.path),
        "source_ref": candidate.source_ref if candidate.mount_id else None,
        "mount_id": candidate.mount_id,
        "source_revision": revision,
        "trial_name": trial_name,
        "task_name": evidence.task_name,
        "job_name": evidence.job_name,
    }
    data_ref.update(_data_ref_provenance(evidence.provenance))
    _apply_harbor_step_ref(data_ref, candidate)
    meta: dict[str, Any] = {
        "trial_key": trial_key,
        "adapter": HARBOR_ADAPTER,
        "conversion_status": "failed",
        "status": evaluation["status"],
        "failure_class": evaluation.get("failure_class") or "missing-trajectory",
        "score": evaluation.get("score"),
        "score_message": evaluation.get("score_message"),
        "warnings": [
            *candidate.entry_warnings,
            "Harbor Trial has no agent/trajectory.json",
        ],
        "data_ref": data_ref,
        "total_events": 0,
        "unmapped_events": 0,
        "prompt_unavailable": True,
        "evaluation": {
            **evaluation,
            "trial_name": trial_name,
            "task_name": evidence.task_name,
            "job_name": evidence.job_name,
            "phase_timing": (
                _phase_timing_for_result(result_json)
                if candidate.step_name is not None
                else evidence.phase_timing
            ),
        },
        "trajectory_available": False,
        "task_name": evidence.task_name,
        "job_name": evidence.job_name,
        "trial_name": trial_name,
        "model_provider": evidence.model_provider,
        "task_keywords": list(evidence.task_keywords),
        "rewards": evaluation["rewards"],
        "harbor_provenance": evidence.provenance,
        "task_metadata": evidence.task_metadata,
        "import_context": {
            "kind": HARBOR_SOURCE_KIND,
            "source_revision": revision,
            "config_available": config_json is not None,
            "lock_available": lock_json is not None,
            "result_available": result_json is not None,
        },
        "source_metrics": _result_final_metrics(result_json),
    }
    _apply_harbor_step_meta(meta, candidate, trial_result_json)
    active = _result_duration_ms(result_json, "agent_execution")
    wall = _result_duration_ms(result_json)
    if active is not None:
        meta["duration_ms"] = active
    if wall is not None:
        meta["wall_duration_ms"] = wall
    return meta


def _result_only_error(
    candidate: SourceCandidate,
    result_json: dict[str, Any] | None,
) -> str:
    exception = (result_json or {}).get("exception_info")
    if isinstance(exception, dict):
        exception_type = optional_str(exception.get("exception_type"))
        exception_message = optional_str(exception.get("exception_message"))
        if exception_type and exception_message:
            return f"{exception_type}: {exception_message}"
        if exception_type or exception_message:
            return exception_type or exception_message or "Harbor Trial failed"
    data_path = candidate.data_path or candidate.path
    return f"Harbor Trial has no agent/trajectory.json: {data_path}"


def _harbor_source(
    candidate: SourceCandidate,
    overlay: dict[str, Any],
    *,
    trajectory: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    config_json: dict[str, Any] | None = None,
    result_json: dict[str, Any] | None = None,
    trial_result_json: dict[str, Any] | None = None,
    evidence: HarborEvidence | None = None,
) -> dict[str, Any]:
    agent = (
        trajectory.get("agent")
        if isinstance((trajectory or {}).get("agent"), dict)
        else {}
    )
    result_agent = (
        trial_result_json.get("agent_info")
        if isinstance((trial_result_json or {}).get("agent_info"), dict)
        else {}
    )
    config_agent = (
        config_json.get("agent")
        if isinstance((config_json or {}).get("agent"), dict)
        else {}
    )
    label = (
        "/".join(
            str(value)
            for value in (
                candidate.job_name,
                candidate.trial_name,
                candidate.step_name,
            )
            if value
        )
        if candidate.job_name and candidate.trial_name
        else f"Harbor mount: {candidate.mount_id}"
    )
    source_alias = optional_str(overlay.get("source_alias"))
    source_tags = _normalized_tags(overlay.get("source_tags"))
    task_keywords = list(evidence.task_keywords) if evidence is not None else []
    task_name = evidence.task_name if evidence is not None else None
    return {
        "kind": candidate.kind,
        "adapter": HARBOR_ADAPTER,
        "label": label,
        "input_path": None,
        "db_path": None,
        "session_id": optional_str((trajectory or {}).get("session_id")),
        "source_alias": source_alias,
        "source_category": optional_str(overlay.get("source_category")),
        "source_tags": source_tags,
        "display_alias": source_alias or task_name,
        "display_tags": _merged_display_tags(task_keywords, source_tags),
        "task_name": task_name,
        "job_name": evidence.job_name if evidence is not None else candidate.job_name,
        "trial_name": evidence.trial_name
        if evidence is not None
        else candidate.trial_name,
        "model_provider": evidence.model_provider if evidence is not None else None,
        "task_keywords": task_keywords,
        "rewards": _evaluation(result_json)["rewards"],
        "step_name": candidate.step_name,
        "step_index": candidate.step_index,
        "step_count": candidate.step_count,
        "harbor_trial_evaluation": (
            _evaluation(trial_result_json) if candidate.step_name is not None else None
        ),
        "harbor_provenance": evidence.provenance if evidence is not None else {},
        "task_metadata": evidence.task_metadata if evidence is not None else {},
        "agent_name": optional_str(agent.get("name") or result_agent.get("name")),
        "agent_version": optional_str(
            agent.get("version") or result_agent.get("version")
        ),
        "model": optional_str(
            agent.get("model_name") or config_agent.get("model_name")
        ),
        "trial_key": (meta or {}).get("trial_key"),
    }


def _trajectory_meta(
    candidate: SourceCandidate,
    trajectory: dict[str, Any],
    config_json: dict[str, Any] | None,
    lock_json: dict[str, Any] | None,
    result_json: dict[str, Any] | None,
    revision: str,
    *,
    source_schema: str,
    telemetry: HarborTelemetry | None,
    telemetry_warning: str | None,
    evidence: HarborEvidence,
    trial_result_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evaluation = _evaluation(result_json)
    result_active = _result_duration_ms(result_json, "agent_execution")
    active_duration = (
        telemetry.duration_ms
        if telemetry is not None and telemetry.duration_ms is not None
        else result_active
    )
    wall_duration = _result_duration_ms(result_json)
    agent = trajectory.get("agent") if isinstance(trajectory.get("agent"), dict) else {}
    trial_name = evidence.trial_name
    task_name = evidence.task_name
    job_id = optional_str((config_json or {}).get("job_id"))
    result_id = optional_str((trial_result_json or result_json or {}).get("id"))
    identity_hash = hashlib.sha256(candidate.source_ref.encode("utf-8")).hexdigest()[
        :10
    ]
    trial_key = (
        f"harbor-{artifact_segment(candidate.trial_name, 'trial')[:48]}-{identity_hash}"
    )
    data_ref: dict[str, Any] = {
        "kind": HARBOR_SOURCE_KIND,
        "label": f"{candidate.job_name}/{candidate.trial_name}",
        "path": str(candidate.path),
        "source_ref": candidate.source_ref if candidate.mount_id else None,
        "mount_id": candidate.mount_id,
        "source_revision": revision,
        "trial_name": trial_name,
        "job_name": evidence.job_name,
    }
    data_ref.update(_data_ref_provenance(evidence.provenance))
    _apply_harbor_step_ref(data_ref, candidate)
    for key, value in (
        ("job_id", job_id),
        ("result_id", result_id),
        ("task_name", task_name),
    ):
        if value is not None:
            data_ref[key] = value
    meta: dict[str, Any] = {
        "trial_key": trial_key,
        "adapter": HARBOR_ADAPTER,
        "conversion_status": "passed",
        "status": evaluation["status"],
        "failure_class": evaluation.get("failure_class"),
        "score": evaluation.get("score"),
        "score_message": evaluation.get("score_message"),
        "warnings": [
            *candidate.entry_warnings,
            *([telemetry_warning] if telemetry_warning else []),
        ],
        "data_ref": data_ref,
        "total_events": len(trajectory.get("steps") or []),
        "unmapped_events": 0,
        "prompt_unavailable": not any(
            isinstance(step, dict) and step.get("source") == "user"
            for step in trajectory.get("steps") or []
        ),
        "evaluation": {
            **evaluation,
            "trial_name": trial_name,
            "job_name": evidence.job_name,
            **({"task_name": task_name} if task_name else {}),
            **({"job_id": job_id} if job_id else {}),
            **({"result_id": result_id} if result_id else {}),
            "phase_timing": (
                _phase_timing_for_result(result_json)
                if candidate.step_name is not None
                else evidence.phase_timing
            ),
        },
        "trajectory_available": True,
        "task_name": task_name,
        "job_name": evidence.job_name,
        "trial_name": trial_name,
        "model_provider": evidence.model_provider,
        "task_keywords": list(evidence.task_keywords),
        "rewards": evaluation["rewards"],
        "harbor_provenance": evidence.provenance,
        "task_metadata": evidence.task_metadata,
        "import_context": {
            "kind": HARBOR_SOURCE_KIND,
            "source_revision": revision,
            "config_available": config_json is not None,
            "lock_available": lock_json is not None,
            "result_available": result_json is not None,
            "agent_name": optional_str(agent.get("name")),
            "source_atif_schema_version": source_schema,
            "supplemental_telemetry": telemetry is not None,
            "source_timing": {
                **(
                    {"duration_ms": active_duration}
                    if active_duration is not None
                    else {}
                ),
                **(
                    {"wall_duration_ms": wall_duration}
                    if wall_duration is not None
                    else {}
                ),
            },
        },
    }
    if telemetry is not None:
        meta["steps"] = telemetry.steps
    _apply_harbor_step_meta(meta, candidate, trial_result_json)
    if lock_json is not None:
        data_ref["lock_available"] = True
    projected = project_meta_from_atif(trajectory, meta)
    return projected


def _data_ref_provenance(provenance: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "mount_id",
        "job_id",
        "result_id",
        "harbor_version",
        "task_digest",
        "task_digest_source",
        "task_source",
        "task_version",
        "task_checksum",
        "regrade",
    }
    return {key: value for key, value in provenance.items() if key in allowed}


def _apply_harbor_step_ref(
    data_ref: dict[str, Any], candidate: SourceCandidate
) -> None:
    if candidate.step_name is None:
        return
    data_ref["step_name"] = candidate.step_name
    data_ref["step_index"] = candidate.step_index
    data_ref["step_count"] = candidate.step_count
    data_ref["label"] = (
        f"{candidate.job_name}/{candidate.trial_name}/{candidate.step_name}"
    )


def _apply_harbor_step_meta(
    meta: dict[str, Any],
    candidate: SourceCandidate,
    trial_result_json: dict[str, Any] | None,
) -> None:
    if candidate.step_name is None:
        return
    meta["harbor_step"] = {
        "name": candidate.step_name,
        "index": candidate.step_index,
        "count": candidate.step_count,
    }
    trial_evaluation = _evaluation(trial_result_json)
    trial_evaluation["phase_timing"] = _phase_timing_for_result(trial_result_json)
    meta["harbor_trial_evaluation"] = trial_evaluation


def _phase_timing_for_result(result: dict[str, Any] | None) -> dict[str, Any]:
    phases: dict[str, Any] = {}
    if not isinstance(result, dict):
        return phases
    for source_key, output_key in (
        (None, "overall"),
        ("environment_setup", "environment_setup"),
        ("agent_setup", "agent_setup"),
        ("agent_execution", "agent_execution"),
        ("verifier", "verifier"),
    ):
        source = result if source_key is None else result.get(source_key)
        if not isinstance(source, dict):
            continue
        started = optional_str(source.get("started_at"))
        finished = optional_str(source.get("finished_at"))
        value: dict[str, Any] = {}
        if started:
            value["started_at"] = started
        if finished:
            value["finished_at"] = finished
        duration_ms = _result_duration_ms(result, source_key)
        if duration_ms is not None:
            value["duration_ms"] = duration_ms
        if value:
            phases[output_key] = value
    return phases


def _merged_display_tags(*values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for tags in values:
        for raw_tag in tags:
            tag = str(raw_tag).strip()
            folded = tag.casefold()
            if not tag or folded in seen:
                continue
            seen.add(folded)
            result.append(tag)
    return result


def _evaluation(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": "running",
            "score": None,
            "score_message": "Harbor Trial has no result.json yet",
            "rewards": {},
        }
    exception = result.get("exception_info")
    status = "errored" if isinstance(exception, dict) else "completed"
    rewards: dict[str, int | float] = {}
    verifier = result.get("verifier_result")
    if isinstance(verifier, dict) and isinstance(verifier.get("rewards"), dict):
        rewards = {
            str(key): value
            for key, value in verifier["rewards"].items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
    score: int | float | None = None
    score_message = "Harbor Trial completed without a numeric reward"
    if "reward" in rewards:
        score = rewards["reward"]
        score_message = "Harbor verifier reward"
    elif len(rewards) == 1:
        key, score = next(iter(rewards.items()))
        score_message = f"Harbor verifier reward: {key}"
    elif len(rewards) > 1:
        score_message = "Harbor verifier returned multiple reward dimensions"
    payload: dict[str, Any] = {
        "status": status,
        "score": score,
        "score_message": score_message,
        "rewards": rewards,
        "started_at": result.get("started_at"),
        "finished_at": result.get("finished_at"),
    }
    if isinstance(exception, dict):
        payload["failure_class"] = (
            optional_str(exception.get("exception_type")) or "harbor-trial"
        )
        payload["exception"] = exception
    return payload


def _read_bytes_no_follow(
    containment_root: Path,
    path: Path,
    *,
    max_bytes: int | None = None,
    label: str = "Harbor source",
) -> bytes:
    _assert_safe_descendant(containment_root, path, label=label)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"cannot read {label} file {path}: {exc}") from exc
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"{label} file must be a regular file: {path}")
        if max_bytes is not None and opened_stat.st_size > max_bytes:
            raise ValueError(f"{label} file exceeds {max_bytes} bytes: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read() if max_bytes is None else handle.read(max_bytes + 1)
        if max_bytes is not None and len(content) > max_bytes:
            raise ValueError(f"{label} file exceeds {max_bytes} bytes: {path}")
    finally:
        os.close(descriptor)
    _assert_safe_descendant(containment_root, path, label=label)
    return content


def _read_harbor_analysis_markdown(candidate: SourceCandidate) -> str | None:
    relative_path = candidate.harbor_analysis_relative_path
    if relative_path is None:
        return None
    path = candidate.path / relative_path
    try:
        file_stat = path.stat(follow_symlinks=False)
    except OSError:
        return None
    if not stat.S_ISREG(file_stat.st_mode):
        return None
    if file_stat.st_size > HARBOR_ANALYSIS_MAX_BYTES:
        return None
    try:
        content = _read_bytes_no_follow(
            candidate.containment_root or candidate.path,
            path,
            max_bytes=HARBOR_ANALYSIS_MAX_BYTES,
        )
        markdown = content.decode("utf-8")
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return markdown if markdown.strip() else None


def _harbor_analysis_relative_path(trial_dir: Path) -> str | None:
    canonical = trial_dir / HARBOR_ANALYSIS_MD_FILE
    try:
        canonical.stat(follow_symlinks=False)
    except FileNotFoundError:
        pass
    except OSError:
        return HARBOR_ANALYSIS_MD_FILE
    else:
        return HARBOR_ANALYSIS_MD_FILE

    return None


def _assert_safe_descendant(root: Path, path: Path, *, label: str) -> None:
    lexical_root = Path(os.path.abspath(root))
    lexical_path = Path(os.path.abspath(path))
    try:
        relative = lexical_path.relative_to(lexical_root)
    except ValueError as exc:
        raise ValueError(f"{label} escapes its root: {path}") from exc
    current = lexical_root
    for part in ("", *relative.parts):
        if part:
            current /= part
        try:
            if current.is_symlink():
                raise ValueError(f"{label} traverses a symlink: {current}")
        except OSError as exc:
            raise ValueError(f"cannot inspect {label} path {current}: {exc}") from exc


def _looks_like_trial(path: Path) -> bool:
    try:
        (path / "agent" / "trajectory.json").stat(follow_symlinks=False)
        return True
    except FileNotFoundError:
        pass
    except OSError:
        return True
    config_path = path / "config.json"
    if _regular_file(config_path):
        try:
            config = read_json_object(config_path)
        except ValueError:
            config = {}
        if any(key in config for key in ("trial_name", "job_id", "trials_dir")):
            return True
    result_path = path / "result.json"
    if _regular_file(result_path):
        try:
            result = read_json_object(result_path)
        except ValueError:
            result = {}
        if any(key in result for key in ("trial_name", "trial_uri", "step_results")):
            return True
    lock_path = path / "lock.json"
    if _regular_file(lock_path):
        try:
            lock = read_json_object(lock_path)
        except ValueError:
            lock = {}
        if any(key in lock for key in ("task", "agent", "environment", "verifier")):
            return True
    steps = path / "steps"
    return (
        any(
            (step / "agent" / "trajectory.json").exists() for step in _child_dirs(steps)
        )
        if steps.is_dir() and not steps.is_symlink()
        else False
    )


def _looks_like_job(path: Path) -> bool:
    config_path = path / "config.json"
    if _regular_file(config_path):
        try:
            config = read_json_object(config_path)
        except ValueError:
            config = {}
        if any(key in config for key in ("job_name", "jobs_dir", "tasks", "agents")):
            return True
    return any(_looks_like_trial(child) for child in _child_dirs(path))


def _is_multi_step_trial(path: Path) -> bool:
    steps = path / "steps"
    if (
        steps.is_dir()
        and not steps.is_symlink()
        and any(True for _ in _child_dirs(steps))
    ):
        return True
    result_path = path / "result.json"
    if not _regular_file(result_path):
        return False
    try:
        result = read_json_object(result_path)
    except ValueError:
        return False
    step_results = result.get("step_results")
    return isinstance(step_results, list) and bool(step_results)


def _child_dirs(root: Path) -> Iterator[Path]:
    try:
        with os.scandir(root) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
    except OSError:
        return
    for entry in ordered:
        try:
            if entry.is_dir(follow_symlinks=False):
                yield Path(entry.path)
        except OSError:
            continue


def _reject_linked_directories(root: Path, kind: str) -> None:
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                if entry.is_symlink() and entry.is_dir(follow_symlinks=True):
                    raise ValueError(
                        f"Harbor {kind} directory must not be a symlink: {entry.path}"
                    )
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError(f"cannot scan Harbor directory {root}: {exc}") from exc


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink() and not path.parent.is_symlink()


def _path_has_symlink(path: Path) -> bool:
    current = path
    while True:
        try:
            if current.is_symlink():
                return True
        except OSError:
            return True
        if current.parent == current:
            return False
        current = current.parent


def _harbor_source_files(
    trial_dir: Path,
    harbor_analysis_relative_path: str | None,
) -> tuple[str, ...]:
    """Include safe supplemental Trial state in the rebuildable fingerprint."""

    relative_sessions = "agent/sessions"
    files = [*HARBOR_SOURCE_FILES, relative_sessions]
    if harbor_analysis_relative_path is not None:
        files.append(harbor_analysis_relative_path)
    sessions = trial_dir / relative_sessions
    try:
        sessions_stat = sessions.stat(follow_symlinks=False)
    except OSError:
        return tuple(files)
    if not stat.S_ISDIR(sessions_stat.st_mode):
        return tuple(files)
    try:
        with os.scandir(sessions) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
    except OSError:
        return tuple(files)
    for entry in ordered:
        relative_session = f"{relative_sessions}/{entry.name}"
        files.append(relative_session)
        try:
            if entry.is_dir(follow_symlinks=False):
                files.append(f"{relative_session}/events.jsonl")
        except OSError:
            continue
    return tuple(files)


def _harbor_entry_source_files(
    entry: HarborTrialEntry,
    harbor_analysis_relative_path: str | None,
) -> tuple[str, ...]:
    relative_root = entry.data_dir.relative_to(entry.trial_dir)
    prefix = "" if relative_root == Path(".") else f"{relative_root.as_posix()}/"
    data_files = tuple(
        f"{prefix}{relative}"
        for relative in _harbor_source_files(
            entry.data_dir,
            harbor_analysis_relative_path,
        )
    )
    if not prefix:
        return data_files
    return ("config.json", "lock.json", "result.json", *data_files)


def _harbor_candidate_source_files(candidate: SourceCandidate) -> tuple[str, ...]:
    data_path = candidate.data_path or candidate.path
    relative_root = data_path.relative_to(candidate.path)
    prefix = "" if relative_root == Path(".") else f"{relative_root.as_posix()}/"
    data_files = tuple(
        f"{prefix}{relative}"
        for relative in _harbor_source_files(
            data_path,
            None,
        )
    )
    if not prefix:
        return data_files
    return ("config.json", "lock.json", "result.json", *data_files)


def _read_harbor_entry_trajectory(
    candidate: SourceCandidate,
) -> dict[str, Any] | None:
    data_path = candidate.data_path or candidate.path
    path = data_path / "agent" / "trajectory.json"
    try:
        content = _read_bytes_no_follow(
            candidate.containment_root or candidate.path,
            path,
        )
    except FileNotFoundError:
        return None
    except ValueError as exc:
        if not path.exists():
            return None
        raise exc
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"failed to parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _fingerprint(
    root: Path,
    relative_files: Iterable[str],
    *,
    extra_root: Path | None = None,
    extra_files: Iterable[str] = (),
) -> str:
    parts = _signature_parts(root, relative_files)
    if extra_root is not None:
        parts.extend(_signature_parts(extra_root, extra_files, prefix="overlay/"))
    return _text_fingerprint("\n".join(parts))


def _combined_revision(*values: str) -> str:
    return _text_fingerprint("\0".join(values))


def _file_signature(root: Path, relative_files: Iterable[str]) -> tuple[str, ...]:
    return tuple(_signature_parts(root, relative_files))


def _signature_parts(
    root: Path, relative_files: Iterable[str], *, prefix: str = ""
) -> list[str]:
    parts: list[str] = []
    for relative in relative_files:
        path = root / relative
        try:
            stat = path.stat(follow_symlinks=False)
            parts.append(
                f"{prefix}{relative}:{stat.st_size}:{stat.st_mtime_ns}:"
                f"{stat.st_ctime_ns}:{stat.st_ino}:{stat.st_mode}"
            )
        except FileNotFoundError:
            parts.append(f"{prefix}{relative}:-")
        except OSError as exc:
            parts.append(f"{prefix}{relative}:error:{exc.errno}")
    return parts


def _text_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _updated_at_ms(root: Path, relative_files: Iterable[str]) -> int:
    values: list[int] = []
    for relative in relative_files:
        try:
            values.append(
                (root / relative).stat(follow_symlinks=False).st_mtime_ns // 1_000_000
            )
        except OSError:
            continue
    return max(values) if values else 0


def _input_bytes(root: Path, relative_files: Iterable[str]) -> int:
    total = 0
    for relative in relative_files:
        try:
            file_stat = (root / relative).stat(follow_symlinks=False)
            if stat.S_ISREG(file_stat.st_mode):
                total += file_stat.st_size
        except OSError:
            continue
    return total


def _normalized_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    tags: list[str] = []
    seen: set[str] = set()
    for raw in value:
        text = str(raw or "").strip()
        folded = text.casefold()
        if text and folded not in seen:
            seen.add(folded)
            tags.append(text)
    return tags


def _nested_string(value: dict[str, Any] | None, *keys: str) -> str | None:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return optional_str(current)
