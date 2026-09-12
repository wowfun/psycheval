"""First-class Harbor execution using its public Job model and lifecycle."""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path

from harbor.models.job.config import JobConfig
from harbor.models.trial.config import AgentConfig
from pydantic.json_schema import GenerateJsonSchema

from psycheval.config import load_config
from psycheval.harbor.datasets import resolve_harbor_dataset
from psycheval.harbor.tasks import load_harbor_task

from .protocol import HarnessContext, RunRequest
from .storage import (
    digest,
    open_regular,
    read_bytes,
    read_json,
    safe_path,
    write_json,
    write_text,
)


def job_values(config):
    value = config.model_dump(mode="json", context={"redact_sensitive_env": False})
    value["environment"]["env"] = dict(config.environment.env)
    value["verifier"]["env"] = dict(config.verifier.env)
    return value


def check_fields(value, model, label="settings"):
    unknown = set(value) - set(model.model_fields)
    if unknown:
        raise ValueError(f"{label}: unknown field {sorted(unknown)[0]}")
    for key, item in value.items():
        if isinstance(item, dict):
            nested = model.model_fields[key].annotation
            if hasattr(nested, "model_fields"):
                check_fields(item, nested, f"{label}.{key}")


class HarborSchema(GenerateJsonSchema):
    def encode_default(self, value):
        return str(value) if isinstance(value, Path) else super().encode_default(value)


def task_revision(
    path: Path, shared: Path | None = None, *, budget=None, cache=None
) -> str:
    budget = budget if budget is not None else {"entries": 0, "bytes": 0}
    cache = cache if cache is not None else {}
    entries = []

    def walk_error(error):
        raise error

    for label, root in (("task", path), ("shared", shared)):
        if root is None:
            continue
        safe_path(root)
        if root not in cache:
            files_for_root = []
            for parent, directories, files in os.walk(
                root, followlinks=False, onerror=walk_error
            ):
                for name in directories + files:
                    budget["entries"] += 1
                    if budget["entries"] > 100_000:
                        raise ValueError("Task revision exceeds 100000 entries")
                    item = safe_path(root, *Path(parent).relative_to(root).parts, name)
                    if name in directories:
                        continue
                    checksum = hashlib.sha256()
                    with open_regular(item) as stream:
                        while chunk := stream.read(1024 * 1024):
                            budget["bytes"] += len(chunk)
                            if budget["bytes"] > 1024**3:
                                raise ValueError("Task revision exceeds 1 GiB")
                            checksum.update(chunk)
                    files_for_root.append(
                        (item.relative_to(root).as_posix(), checksum.hexdigest())
                    )
            cache[root] = files_for_root
        entries.extend((label, name, checksum) for name, checksum in cache[root])
    return digest(sorted(entries))


def resolve_selection(refs, workspace):
    config = load_config(workspace_root=workspace)
    datasets = {d.id: d for d in config.harbor_datasets}
    resolved_datasets = {}
    selected = []
    for ref in refs:
        dataset_id, separator, name = ref.partition("/")
        if not separator or dataset_id not in datasets:
            raise ValueError(f"Task is not registered: {ref}")
        dataset = datasets[dataset_id]
        if dataset_id not in resolved_datasets:
            resolved_datasets[dataset_id] = resolve_harbor_dataset(
                dataset_id=dataset.id,
                path=dataset.path,
                format=dataset.format,
                allow_partial=dataset.allow_partial,
            )
        resolved = resolved_datasets[dataset_id]
        if name not in resolved.task_names:
            raise ValueError(f"Task is unavailable: {ref}")
        path = safe_path(resolved.task_root, name)
        shared = (
            resolved.task_root.parent / "shared"
            if dataset.format == "workbuddy.v1"
            else None
        )
        selected.append(
            {
                "id": ref,
                "path": str(path),
                "shared": str(shared) if shared else None,
                "format": dataset.format,
            }
        )
    return selected


def read_task_file(path: Path) -> bytes:
    return read_bytes(path, 2 * 1024 * 1024)


class HarborHarness:
    def describe(self, context):
        from harbor.models.agent.name import AgentName

        return {
            "label": "Harbor",
            "version": 1,
            "agents": [name.value for name in AgentName],
            "models": [],
            "capabilities": ["variants", "stop", "trajectory", "verification"],
            "defaults": {
                "settings": {
                    "n_attempts": 1,
                    "n_concurrent_trials": 4,
                    "timeout_multiplier": 1.0,
                },
                "variants": [
                    {
                        "id": "a",
                        "label": "A",
                        "agent": "opencode",
                        "model": "",
                        "options": {},
                    }
                ],
            },
            "settings_schema": JobConfig.model_json_schema(
                schema_generator=HarborSchema
            ),
            "variant_schema": AgentConfig.model_json_schema(
                schema_generator=HarborSchema
            ),
        }

    def catalog(self, context: HarnessContext):
        config = load_config(workspace_root=context.workspace)
        result = []
        for dataset in config.harbor_datasets:
            try:
                resolved = resolve_harbor_dataset(
                    dataset_id=dataset.id,
                    path=dataset.path,
                    format=dataset.format,
                    allow_partial=dataset.allow_partial,
                )
                tasks = []
                for name in resolved.task_names:
                    path = safe_path(resolved.task_root, name)
                    error = None
                    try:
                        load_harbor_task(path, read_bytes=read_task_file)
                    except (OSError, ValueError) as exc:
                        error = str(exc)
                    tasks.append(
                        {
                            "id": f"{dataset.id}/{name}",
                            "label": name,
                            "available": error is None,
                            "error": error,
                        }
                    )
                result.append(
                    {
                        "id": dataset.id,
                        "label": dataset.id,
                        "format": dataset.format,
                        "tasks": tasks,
                    }
                )
            except (ValueError, OSError) as exc:
                result.append(
                    {
                        "id": dataset.id,
                        "label": dataset.id,
                        "tasks": [],
                        "error": str(exc),
                    }
                )
        return result

    def prepare(self, request: RunRequest, context: HarnessContext):
        from psycheval.harbor.runtime_config import load_host_settings
        from psycheval.harbor.workbuddy import prepare_workbuddy_job

        settings = copy.deepcopy(request.settings)
        managed = {"job_name", "jobs_dir", "agents", "datasets", "tasks", "source_jobs"}
        if managed.intersection(settings):
            raise ValueError(
                "Task selection, variants and output identity are managed by Jobs"
            )
        check_fields(settings, JobConfig)
        selected, formats = [], set()
        budget, cache = {"entries": 0, "bytes": 0}, {}
        for item in resolve_selection(request.tasks, context.workspace):
            formats.add(item.pop("format"))
            path = Path(item["path"])
            shared = Path(item["shared"]) if item["shared"] else None
            load_harbor_task(path, read_bytes=read_task_file)
            selected.append(
                {
                    **item,
                    "revision": task_revision(path, shared, budget=budget, cache=cache),
                }
            )
        if len(formats) != 1:
            raise ValueError(
                "These Datasets require different verifiers; use separate Jobs"
            )
        agents = []
        native_host = settings.get("environment", {}).get("import_path") in {
            "psycheval.harbor.environment:HostEnvironment",
            "psycheval.harbor.workbuddy_environment:WorkBuddyHostEnvironment",
        }
        for variant in request.variants:
            options = copy.deepcopy(variant.options)
            if {"name", "import_path", "model_name"}.intersection(options):
                raise ValueError("Agent and Model must be set on the variant")
            check_fields(options, AgentConfig, f"variant {variant.label}")
            agent = variant.agent
            if agent == "opencode" and native_host:
                agent = "psycheval.harbor.opencode:HostOpenCodeAgent"
            agents.append(
                {
                    ("import_path" if ":" in agent else "name"): agent,
                    "model_name": variant.model or None,
                    **options,
                }
            )
        settings.update(
            agents=agents,
            tasks=[{"path": item["path"]} for item in selected],
            job_name="preview",
            jobs_dir=str(context.workspace / "jobs"),
        )
        job = JobConfig.model_validate(settings)
        if (
            job.n_attempts > 100
            or len(selected) * len(agents) * job.n_attempts > 10_000
        ):
            raise ValueError("Harbor Jobs allow at most 100 repeats and 10000 Trials")
        if job.n_attempts < 1 or job.timeout_multiplier <= 0:
            raise ValueError("Repeat count and timeout multiplier must be positive")
        if formats == {"workbuddy.v1"}:
            job = prepare_workbuddy_job(
                job, host_settings=load_host_settings(context.workspace / "peval.toml")
            )
        job.validate_agent_concurrency_limits()
        native = job_values(job)
        return {
            "config": native,
            "selection": selected,
            "variants": [v.model_dump() for v in request.variants],
            "trial_count": len(selected) * len(agents) * job.n_attempts,
        }

    async def execute(self, prepared, control):
        import yaml
        from harbor.environments.factory import EnvironmentFactory
        from harbor.job import Job

        value = copy.deepcopy(prepared["config"])
        current = resolve_selection(
            [item["id"] for item in prepared["selection"]], control.workspace
        )
        if [str(item.get("path")) for item in value["tasks"]] != [
            item["path"] for item in current
        ]:
            raise ValueError("Prepared Task selection does not match registered Tasks")
        for task, authorized in zip(prepared["selection"], current, strict=True):
            if any(task.get(key) != authorized.get(key) for key in ("path", "shared")):
                raise ValueError("Retained Task path is not the registered Task")
        budget, cache = {"entries": 0, "bytes": 0}, {}
        for task in current:
            retained = next(
                item for item in prepared["selection"] if item["id"] == task["id"]
            )
            if (
                task_revision(
                    Path(task["path"]),
                    Path(task["shared"]) if task["shared"] else None,
                    budget=budget,
                    cache=cache,
                )
                != retained["revision"]
            ):
                raise ValueError(f"Task changed after preview: {task['id']}")
        value.update(
            job_name=control.output_dir.name,
            jobs_dir=str(control.output_dir.parent),
            quiet=True,
        )
        config = JobConfig.model_validate(value)
        EnvironmentFactory.run_preflight(
            type=config.environment.type, import_path=config.environment.import_path
        )
        write_text(
            control.control_dir / "job.yaml",
            yaml.safe_dump(value, allow_unicode=True, sort_keys=False),
        )
        job = await Job.create(config)
        variant_map = {
            digest(agent.model_dump(mode="json")): variant
            for agent, variant in zip(config.agents, prepared["variants"], strict=True)
        }
        mapping = {}
        completed = set()

        async def started(event):
            variant = variant_map[digest(event.config.agent.model_dump(mode="json"))]
            mapping[event.config.trial_name] = variant
            write_json(
                control.control_dir / "variants.json",
                {str(k): v for k, v in mapping.items()},
            )
            control.report(
                trials_started=len({k for k in mapping if isinstance(k, str)}),
                current_trial=event.config.trial_name,
            )

        async def finished(event):
            completed.add(event.config.trial_name)
            control.report(trials_completed=len(completed))

        job.on_trial_started(started)
        job.on_trial_ended(finished)
        control.report(trials_total=prepared["trial_count"])
        await job.run()

    def read_results(self, output_dir):
        from psycheval.state.harbor_verifier_evidence import (
            read_harbor_verifier_evidence,
        )

        results = []
        if not output_dir.exists():
            return results
        for path in sorted(output_dir.iterdir()):
            if not path.is_dir():
                continue
            try:
                safe_path(output_dir, path.name)
                result = read_json(path / "result.json")
                if result is None:
                    continue
                if not isinstance(result, dict) or not result:
                    raise ValueError("invalid Harbor result document")
                # The workspace's existing evidence reader remains the score authority.
                config = read_json(path / "config.json", {})
                rewards = (result.get("verifier_result") or {}).get("rewards") or {}
                reward = rewards.get("reward")
                if reward is None and len(rewards) == 1:
                    reward = next(iter(rewards.values()))
                if not isinstance(reward, (int, float)):
                    reward = None
                workbuddy = "workbuddy" in (
                    config.get("verifier", {}).get("import_path") or ""
                ) and not config.get("verifier", {}).get("disable")
                evidence = read_harbor_verifier_evidence(
                    path,
                    containment_root=output_dir,
                    dataset_format="workbuddy.v1" if workbuddy else "harbor",
                    harbor_reward=reward,
                )
                results.append(
                    {
                        "id": path.name,
                        "task": result.get("task_name")
                        or Path(config.get("task", {}).get("path", "")).name,
                        "state": "failed"
                        if result.get("exception_info")
                        else "completed"
                        if result.get("finished_at")
                        else "running",
                        "score": evidence.score,
                        "score_source": evidence.score_source,
                        "agent": config.get("agent", {}),
                        "exception": result.get("exception_info"),
                    }
                )
            except (ValueError, OSError, TypeError, AttributeError) as exc:
                results.append(
                    {
                        "id": path.name,
                        "task": path.name,
                        "state": "invalid",
                        "score": None,
                        "score_source": None,
                        "error": str(exc),
                    }
                )
        return results
