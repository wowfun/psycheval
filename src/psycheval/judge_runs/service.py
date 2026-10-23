"""Shared CLI/HTTP application service for independent rubric diagnostics."""

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from harbor.models.task.paths import TaskPaths
from harbor.models.task.task import strip_canary

from psycheval._harbor_trials import load_harbor_trial_bundle
from psycheval.config import load_config
from psycheval.harbor.runtime_config import VerifierInvocation
from psycheval.harbor.verifier import (
    parse_judge_config,
    prepare_judge,
    run_judge,
)
from psycheval.harbor.verifier._blocking import run_blocking
from psycheval.judge_runs.files import (
    contained,
    protected,
    read_json,
    read_text,
    retained_prompt,
)
from psycheval.state.paths import resolve_workspace_root
from psycheval.state.workspace_sources import WorkspaceSources


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def judge_metadata(score):
    return next(
        (
            group.get("metadata", {})
            for group in score.get("judges", [])
            if group.get("judge_name") == "llm_judge"
        ),
        {},
    )


@dataclass(frozen=True)
class JudgeSource:
    root: Path
    data: Path
    trial: Path
    identity: str
    step: str | None


class PreviewConflict(ValueError):
    """The inputs changed after preview; no execution took place."""


class JudgeService:
    def __init__(self, root: str | Path):
        self.root = resolve_workspace_root(str(root))

    def source(
        self, *, source_ref=None, path=None, step=None, _config=None
    ) -> JudgeSource:
        if bool(source_ref) == bool(path):
            raise ValueError("select exactly one source-ref or Trial path")
        config = (
            _config if _config is not None else load_config(workspace_root=self.root)
        )
        if source_ref:
            if step is not None:
                raise ValueError("source-ref already selects its step")
            # Reuse the mounted-source authority without allocating a catalog.
            from types import SimpleNamespace

            sources = WorkspaceSources(
                SimpleNamespace(paths=SimpleNamespace(root=self.root)), config
            )
            data, root = sources.verification_file_location(source_ref)
            parts = source_ref.split("/")
            step = parts[5] if len(parts) == 6 else None
            trial = data.parent.parent if step else data
            identity = source_ref
        else:
            trial = Path(os.path.abspath(Path(path).expanduser()))
            root, data = trial, trial
            contained(root, trial)
            if step is not None:
                if not re.fullmatch(r"[A-Za-z0-9_.-]+", step) or step in {".", ".."}:
                    raise ValueError("invalid step name")
                data = contained(root, trial / "steps" / step)
                if not data.is_dir():
                    raise ValueError("unknown Trial step")
            identity = "path:" + str(trial) + ("/steps/" + step if step else "")
            for mount in config.harbor_mounts:
                mount_root = Path(mount.path).expanduser().resolve()
                if (
                    trial.is_relative_to(mount_root)
                    and len(trial.relative_to(mount_root).parts) == 2
                ):
                    identity = (
                        "harbor/"
                        + mount.id
                        + "/"
                        + trial.relative_to(mount_root).as_posix()
                        + ("/steps/" + step if step else "")
                    )
                    break
        if (trial / "steps").is_dir() and step is None:
            raise ValueError("multi-step Trial requires an explicit step")
        # Recognition remains with the shared read-only Trial loader.
        bundle = load_harbor_trial_bundle(trial)
        if step is not None and step not in {
            entry.step_name for entry in bundle.entries
        }:
            raise ValueError("unknown Trial step")
        return JudgeSource(root, data, trial, identity, step)

    def inspect(self, **source_args):
        value = self._inspect(self.source(**source_args))
        if value["config"] is not None:
            value["config"] = parse_judge_config(json.dumps(value["config"])).to_dict()
        return value

    def _inspect(self, source):
        score = (
            read_json(source.root, source.data / "verifier/score.json", optional=True)
            or {}
        )
        metadata = judge_metadata(score)
        config = None
        baseline = []
        rubrics = []
        for item in score.get("verdicts", []):
            rubric = (
                item.get("metadata", {}).get("rubric")
                if isinstance(item, dict)
                else None
            )
            if item.get("judge_name") == "llm_judge" and isinstance(rubric, dict):
                rubrics.append(rubric)
                baseline.append(
                    {
                        "id": rubric["id"],
                        "status": item.get("status"),
                        "reason": item.get("reason"),
                        "rubric": rubric,
                    }
                )
        if rubrics:
            records = (
                score.get("diagnostics", {}).get("evidence", {}).get("records", [])
            )
            config = {
                "version": 1,
                "artifacts": [
                    {
                        "id": item["id"],
                        "path": item["uri"],
                        "type": item["type"],
                        "required": item.get("metadata", {}).get("required", True),
                    }
                    for item in records
                ],
                "llm_judge": {"method": "rubric_binary_mean", "rubrics": rubrics},
            }
            merge = score.get("metadata", {}).get("score_merge", {})
            if "rule_weight" in merge and "llm_weight" in merge:
                config["score_merge"] = {
                    "method": "weighted_sum",
                    "rule_weight": merge["rule_weight"],
                    "llm_weight": merge["llm_weight"],
                }
        rule_rewards = {}
        for group in score.get("judges", []):
            if group.get("judge_name") == "rule":
                scores = group.get("scores", {})
                rule_rewards = {
                    "reward": scores.get("overall", 0),
                    **{
                        key: value
                        for key, value in scores.items()
                        if key not in {"overall", "pass_rate"}
                    },
                }
        return protected(
            {
                "source": source.identity,
                "step": source.step,
                "supported": config is not None,
                "config": config,
                "baseline": baseline,
                "context": metadata.get("context"),
                "settings": metadata.get("settings"),
                "rule_rewards": rule_rewards,
                "input_origin": "retained_score",
                "missing": [] if metadata.get("context") else ["instruction"],
            }
        )

    def prompt(self, rubric_id, **source_args):
        source = self.source(**source_args)
        result = retained_prompt(source.root, source.data / "verifier/judge", rubric_id)
        score = (
            read_json(source.root, source.data / "verifier/score.json", optional=True)
            or {}
        )
        metadata = judge_metadata(score)
        if (
            result["status"] == "unavailable"
            and metadata.get("judge_status") == "disabled"
            and rubric_id
            in {
                item.get("metadata", {}).get("rubric", {}).get("id")
                for item in score.get("verdicts", [])
                if item.get("judge_name") == "llm_judge"
            }
        ):
            result["status"] = "not_requested"
        result.update(
            source=source.identity,
            settings=metadata.get("settings"),
        )
        result["redacted"] = True
        return protected(result)

    def _prepare(
        self,
        *,
        rubric_ids=None,
        all_rubrics=False,
        profile=None,
        judge_config=None,
        task=None,
        instruction=None,
        instruction_text=None,
        **source_args,
    ):
        if bool(rubric_ids) == bool(all_rubrics):
            raise ValueError("select rubric IDs or all rubrics")
        workspace = load_config(workspace_root=self.root)
        source = self.source(**source_args, _config=workspace)
        original = self._inspect(source)
        if not original["supported"]:
            raise ValueError("source is not a retained generic YAML Judge")
        # A terminal result is required even when the original Judge was disabled.
        result = (
            read_json(source.root, source.trial / "result.json", optional=True) or {}
        )
        step_result = (
            next(
                (
                    item
                    for item in result.get("step_results", [])
                    if isinstance(item, dict) and item.get("step_name") == source.step
                ),
                {},
            )
            if source.step
            else {}
        )
        verifier = step_result.get("verifier")
        finished_step = isinstance(verifier, dict) and verifier.get("finished_at")
        if not result.get("finished_at") and not finished_step:
            raise ValueError("Judge experiments require a finished Trial or step")
        config = json.dumps(original["config"])
        context = original["context"]
        if task:
            task_root = Path(os.path.abspath(Path(task).expanduser()))
            paths = TaskPaths(task_root)
            judge_path = (
                paths.step_tests_dir(source.step) / "judge.yaml"
                if source.step
                else paths.tests_dir / "judge.yaml"
            )
            if source.step and not judge_path.exists():
                judge_path = paths.tests_dir / "judge.yaml"
            config = read_text(task_root, judge_path, 1024 * 1024)
            instruction_path = (
                paths.step_instruction_path(source.step)
                if source.step
                else paths.instruction_path
            )
            context = {
                "instruction": strip_canary(read_text(task_root, instruction_path)),
                "step_name": source.step,
            }
        if judge_config is not None:
            config = judge_config
        if instruction and instruction_text is not None:
            raise ValueError("choose an instruction file or text")
        if instruction:
            path = Path(os.path.abspath(instruction))
            instruction_text = read_text(path.parent, path)
        if instruction_text is not None:
            if not instruction_text.strip():
                raise ValueError("instruction must not be empty")
            context = {"instruction": instruction_text, "step_name": source.step}
        if context is None:
            raise ValueError(
                "historical instruction missing; supply a Task or instruction"
            )
        selected_name, selected_profile = workspace.judge.select(profile)
        prepared = prepare_judge(
            parse_judge_config(config),
            evidence_root=source.data / "verifier",
            settings=selected_profile.settings(),
            context=VerifierInvocation(**context),
            rubric_ids=tuple(rubric_ids) if rubric_ids else None,
            rule_rewards=original["rule_rewards"],
        )
        payload = prepared.to_dict()
        metadata = {
            "source": source.identity,
            "step": source.step,
            "profile": selected_name,
            "settings": payload["settings"],
            "fingerprint": fingerprint(
                {
                    "source": source.identity,
                    "input": payload,
                    "profile": selected_profile.model_dump(),
                }
            ),
            "selected_ids": [
                item["id"] for item in payload["config"]["llm_judge"]["rubrics"]
            ],
        }
        return prepared, selected_profile, metadata, original["baseline"]

    def preview(self, **draft):
        prepared, _, metadata, _ = self._prepare(**draft)
        return protected(
            {"status": "unsent", "messages": prepared.to_dict()["messages"], **metadata}
        )

    async def run(self, *, expected_fingerprint=None, **draft):
        prepared, profile, metadata, baseline = await run_blocking(
            self._prepare, **draft
        )
        if (
            expected_fingerprint is not None
            and expected_fingerprint != metadata["fingerprint"]
        ):
            raise PreviewConflict("Judge inputs changed; preview again before running")
        diagnostics = {}

        def collect(name, value):
            if name.startswith("rubric-"):
                diagnostics[name] = {
                    key: value[key] for key in ("id", "messages", "result")
                }

        result = await run_judge(
            prepared, api_key=profile.credential(), on_diagnostic=collect
        )
        return protected(
            {
                **metadata,
                "state": result["status"],
                "checks": result["checks"],
                "errors": result.get("errors", {}),
                "reason": result["reason"],
                "elapsed_sec": result.get("elapsed_sec"),
                "diagnostics": diagnostics,
                "baseline": [
                    {key: item[key] for key in ("id", "status", "reason")}
                    for item in baseline
                    if item["id"] in metadata["selected_ids"]
                ],
            }
        )
