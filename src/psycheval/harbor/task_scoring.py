"""Non-executing Task scoring inventory and file previews."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from .tasks import TaskFileReader, load_harbor_task_config
from .verifier import build_scoring_plan, parse_judge_config

SCORING_TEXT_LIMIT = 2 * 1024 * 1024
MAX_OFFICE_RUBRICS = 1024
RUBRIC_FIELDS = (
    "question",
    "pass_criteria",
    "fail_criteria",
    "scope_limits",
    "artifact_refs",
)


def _office_judge(content: str) -> dict[str, Any]:
    """Read Office metadata without loading its executable verifier plugin."""
    try:
        data = yaml.safe_load(content)
        # Bound expanded aliases as well as the source; reject recursive or
        # non-JSON metadata before publishing it to the browser.
        chunks, size = [], 0
        for chunk in json.JSONEncoder(ensure_ascii=False, allow_nan=False).iterencode(
            data
        ):
            size += len(chunk.encode("utf-8"))
            if size > SCORING_TEXT_LIMIT:
                raise ValueError(
                    "Expanded Judge metadata exceeds the preview size limit"
                )
            chunks.append(chunk)
        data = json.loads("".join(chunks))
    except (yaml.YAMLError, TypeError, ValueError, RecursionError) as exc:
        raise ValueError("Invalid WorkBuddy Judge metadata") from exc
    if not isinstance(data, dict):
        raise ValueError("judge.yaml must contain a mapping")
    judge = data.get("llm_judge") or {}
    if not isinstance(judge, dict):
        raise ValueError("llm_judge must contain a mapping")
    rubrics = judge.get("rubrics", [])
    if not isinstance(rubrics, list):
        raise ValueError("llm_judge.rubrics must be a list")
    if len(rubrics) > MAX_OFFICE_RUBRICS:
        raise ValueError(f"Office Judge metadata exceeds {MAX_OFFICE_RUBRICS} rubrics")
    seen = set()
    for rubric in rubrics:
        if not isinstance(rubric, dict):
            raise ValueError("Each rubric must be a mapping")
        identity = rubric.get("id")
        if not isinstance(identity, str) or not identity.strip() or identity in seen:
            raise ValueError("Rubric IDs must be nonempty and unique")
        seen.add(identity)
        if not isinstance(rubric.get("question"), str):
            raise ValueError("Rubric question must be text")
        for field in RUBRIC_FIELDS[1:]:
            if not isinstance(rubric.get(field, []), list):
                raise ValueError(f"Rubric {field} must be a list")
    return data


def scoring_file_preview(
    path: str, content: str, *, format: str = "harbor"
) -> dict[str, Any] | None:
    """Parse a saved file or draft; never read files or execute Task code."""
    name = Path(path).name
    if name not in {"grader.json", "judge.yaml"}:
        return None
    limit = 1024 * 1024 if name == "judge.yaml" else SCORING_TEXT_LIMIT
    if len(content.encode("utf-8")) > limit:
        raise ValueError(f"{name} exceeds the preview size limit")
    if name == "grader.json":
        config = json.loads(content)
        plan = build_scoring_plan(config)
        return {
            "kind": "grader",
            "config": config,
            "items": [asdict(item) for item in plan.items],
        }
    config = (
        _office_judge(content)
        if format == "workbuddy.v1"
        else parse_judge_config(content).to_dict()
    )
    return {
        "kind": "judge",
        "config": config,
        "items": (config.get("llm_judge") or {}).get("rubrics", []),
    }


def task_scoring_inventory(
    task_dir: Path,
    *,
    read_bytes: TaskFileReader,
    format: str = "harbor",
    manual_rule_count: int | None = None,
) -> dict[str, Any]:
    """Project declared scoring files using each step's effective test overlay."""
    office = format == "workbuddy.v1"
    result: dict[str, Any] = {
        "tags": [],
        "category": None,
        "difficulty": None,
        "instruction": None,
        "instruction_path": "instruction.md",
        "rule_count": manual_rule_count if office else 0,
        "rubric_count": 0,
        "scoring_item_count": None,
        "rule_count_source": ("unknown" if manual_rule_count is None else "manual")
        if office
        else "declared",
        "scoring_items": [],
        "scoring_paths": {},
        "scoring_diagnostics": [],
    }

    def diagnostic(path: str, exc: Exception) -> None:
        detail = str(exc).replace(str(task_dir), "<task>")
        result["scoring_diagnostics"].append(f"{path}: {detail}")

    def read(path: str) -> str:
        content = read_bytes(task_dir / path)
        if len(content) > SCORING_TEXT_LIMIT:
            raise ValueError("Task text exceeds the preview size limit")
        return content.decode("utf-8")

    try:
        config = load_harbor_task_config(task_dir, read_bytes=read_bytes).config
    except (OSError, ValueError) as exc:
        diagnostic("task.toml", exc)
        result["rubric_count"] = None
        if not office:
            result.update(rule_count=None, rule_count_source="unknown")
        return result
    result["tags"] = list(config.task.keywords or []) if config.task else []
    for field in ("category", "difficulty"):
        result[field] = config.metadata.get(field)
    steps = [step.name for step in config.steps] if config.steps else [""]
    if steps[0]:
        result["instruction_path"] = f"steps/{steps[0]}/instruction.md"
    try:
        result["instruction"] = read(result["instruction_path"])
    except (OSError, ValueError) as exc:
        diagnostic(result["instruction_path"], exc)

    # Shared files may serve several steps; parse each physical file only once.
    cache: dict[str, dict[str, Any] | Exception | None] = {}
    for step in steps:
        for kind, name in (("rule", "grader.json"), ("rubric", "judge.yaml")):
            paths = ([f"steps/{step}/tests/{name}"] if step else []) + [f"tests/{name}"]
            for path in paths:
                if path not in cache:
                    try:
                        text = read(path)
                    except FileNotFoundError:
                        cache[path] = None
                    except (OSError, ValueError) as exc:
                        cache[path] = exc
                    else:
                        try:
                            cache[path] = (
                                {"items": []}
                                if office and kind == "rule"
                                else scoring_file_preview(path, text, format=format)
                            )
                        except (ValueError, RecursionError) as exc:
                            cache[path] = exc
                parsed = cache[path]
                if parsed is None:
                    continue
                result["scoring_paths"].setdefault(kind, path)
                if office and kind == "rule":
                    break
                if isinstance(parsed, Exception):
                    diagnostic(path, parsed)
                    result[f"{kind}_count"] = None
                    if kind == "rule":
                        result["rule_count_source"] = "unknown"
                    break
                items = parsed["items"]
                if result[f"{kind}_count"] is not None:
                    result[f"{kind}_count"] += len(items)
                for item in items:
                    row = {
                        "key": json.dumps(
                            [step, kind, item["id"]],
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                        "id": item["id"],
                        "type": kind,
                        "step": step,
                        "path": path,
                    }
                    if kind == "rubric":
                        row.update(
                            {
                                key: item.get(key, [] if key != "question" else "")
                                for key in RUBRIC_FIELDS
                            }
                        )
                    elif item["description"] is not None:
                        row["question"] = item["description"]
                    result["scoring_items"].append(row)
                break
    if result["rule_count"] is not None and result["rubric_count"] is not None:
        result["scoring_item_count"] = result["rule_count"] + result["rubric_count"]
    return result
