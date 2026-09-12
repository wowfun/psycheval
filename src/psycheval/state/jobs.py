"""Read-only bridge from managed native runs into workspace source discovery."""

import re
from pathlib import Path

from psycheval.config import HarborMount
from psycheval.jobs.storage import (
    digest,
    read_json,
    read_object,
    safe_path,
    validate_state,
)


def records(workspace):
    try:
        root = safe_path(workspace, ".peval", "jobs")
    except (ValueError, OSError):
        return []
    if not root.exists():
        return []
    result = []
    for path in root.iterdir():
        if re.fullmatch(r"[a-f0-9]{32}", path.name):
            try:
                state = validate_state(
                    read_object(safe_path(root, path.name, "state.json")), path.name
                )
                if state.get("job_name"):
                    result.append((path, state))
            except (ValueError, OSError):
                continue
    return result


def managed_config(config, workspace):
    try:
        output = safe_path(workspace, "jobs")
        control = safe_path(workspace, ".peval", "jobs")
    except (ValueError, OSError):
        return config
    if not output.is_dir() or not control.is_dir():
        return config
    if any(Path(mount.path).resolve() == output for mount in config.harbor_mounts):
        return config
    if any(mount.id == "workspace-jobs" for mount in config.harbor_mounts):
        return config
    mount = HarborMount(
        id="workspace-jobs",
        path=str(output),
        dataset_ids=tuple(d.id for d in config.harbor_datasets),
    )
    return config.validated_update(harbor_mounts=(*config.harbor_mounts, mount))


def result_identity(workspace, config, state, result):
    return result_identity_resolver(workspace, config, state)(result)


def result_identity_resolver(workspace, config, state):
    if state["harness"] == "harbor":
        from .workspace_harbor import _harbor_trial_key

        effective = managed_config(config, workspace)
        root = workspace / "jobs"
        mount = next(
            (m for m in effective.harbor_mounts if Path(m.path).resolve() == root), None
        )
        if mount is None:
            return lambda result: None
        return lambda result: _harbor_trial_key(
            mount.id, state["job_name"], result["id"]
        )
    return lambda result: digest(
        ["harness-trial", state["harness"], state["id"], result["id"]]
    )


def variant_metadata(workspace, job_name, trial_name):
    for path, state in records(workspace):
        if state["job_name"] == job_name:
            try:
                variants = read_object(path / "variants.json", {})
                variant = variants.get(trial_name, {})
                if not isinstance(variant, dict):
                    return {}
            except (ValueError, OSError):
                return {}
            return {
                "run_id": state["id"],
                "variant_id": variant.get("id"),
                "variant_label": variant.get("label"),
            }
    return {}


def variant_index(workspace):
    """One bounded mapping read per run for a discovery pass."""
    result = {}
    for path, state in records(workspace):
        try:
            variants = read_object(path / "variants.json", {})
        except (ValueError, OSError):
            continue
        for trial, variant in variants.items():
            if (
                isinstance(variant, dict)
                and isinstance(variant.get("id"), str)
                and isinstance(variant.get("label"), (str, type(None)))
            ):
                result[(state["job_name"], trial)] = {
                    "run_id": state["id"],
                    "variant_id": variant.get("id"),
                    "variant_label": variant.get("label"),
                }
    return result


def plugin_candidates(workspace, *, run_id=None):
    from psycheval.jobs.service import JobsService
    from psycheval.state.workspace_source_models import SourceCandidate

    try:
        service = JobsService(workspace)
    except (ValueError, OSError):
        return []
    result = []
    if run_id is not None:
        state = validate_state(
            read_object(safe_path(service.root, run_id, "state.json")), run_id
        )
        retained = [(service.root / run_id, state)]
    else:
        retained = records(workspace)
    for _, state in retained:
        if state["harness"] == "harbor":
            continue
        try:
            detail = service.detail(state["id"])
        except (ValueError, OSError):
            continue
        for trial in detail["results"]:
            key = digest(["harness-trial", state["harness"], state["id"], trial["id"]])
            ref = f"runs/jobs/{state['harness']}/{state['id']}/{key}"
            result.append(
                SourceCandidate(
                    source_ref=ref,
                    source_key=key,
                    kind="harness-trial",
                    path=safe_path(workspace, "jobs", state["job_name"]),
                    fingerprint=digest(trial),
                    job_name=state["job_name"],
                    trial_name=trial["id"],
                    projection={
                        **trial,
                        "harness": state["harness"],
                        "run_id": state["id"],
                        "updated_at": state.get("heartbeat", 0),
                    },
                )
            )
    return result


def plugin_candidate_for_ref(workspace, ref):
    parts = ref.split("/")
    if (
        len(parts) != 5
        or parts[:2] != ["runs", "jobs"]
        or not re.fullmatch(r"[a-f0-9]{32}", parts[3])
    ):
        raise ValueError("invalid harness source reference")
    for candidate in plugin_candidates(workspace, run_id=parts[3]):
        if candidate.source_ref == ref:
            return candidate
    raise ValueError("unknown harness source reference")


def plugin_document(candidate):
    from psycheval.atif import validate_atif_trajectory
    from psycheval.state.workspace_source_models import SourceDocument

    trial = candidate.projection
    trajectory = None
    trajectory_error = None
    if trial.get("trajectory_path"):
        try:
            path = safe_path(candidate.path, *Path(trial["trajectory_path"]).parts)
            trajectory = read_json(path)
            validate_atif_trajectory(trajectory, str(path))
        except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
            trajectory = None
            trajectory_error = str(exc)
    source = {
        "kind": "harness-trial",
        "adapter": trial["harness"],
        "label": trial.get("task", trial["id"]),
        "session_id": trial["id"],
        "task_name": trial.get("task"),
        "job_name": candidate.job_name,
        "trial_name": trial["id"],
        "score": trial.get("score"),
        "score_source": trial.get("score_source"),
        "agent_name": trial.get("agent_name"),
        "model": trial.get("model"),
        "run_id": trial["run_id"],
        "variant_id": trial.get("variant_id"),
        "variant_label": trial.get("variant_label"),
        "display_alias": trial.get("task", trial["id"]),
        "display_tags": [],
        "source_tags": [],
        "verifier_evidence": {
            "score": trial.get("score"),
            "score_source": trial.get("score_source"),
            "status": "present" if trial.get("score") is not None else "missing",
        },
    }
    return SourceDocument(
        source_ref=candidate.source_ref,
        source_key=candidate.source_key,
        source=source,
        trajectory=trajectory,
        meta={
            "agent_name": trial.get("agent_name"),
            "model": trial.get("model"),
            "variant_id": trial.get("variant_id"),
            "variant_label": trial.get("variant_label"),
            "trajectory_available": trajectory is not None,
            "trajectory_error": trajectory_error,
            "score": trial.get("score"),
            "task_name": trial.get("task"),
            "trial_key": candidate.source_key,
            "source_key": candidate.source_key,
            "session_id": trial["id"],
            "adapter": trial["harness"],
            "status": trial.get("state"),
            "job_name": candidate.job_name,
            "verifier_evidence": source["verifier_evidence"],
        },
        fingerprint=candidate.fingerprint,
        updated_at_ms=int(trial["updated_at"] * 1000),
        input_bytes=0,
        readable=True,
        refreshable=False,
        snapshot=True,
        active=True,
        last_status="ok",
        last_error=None,
    )
