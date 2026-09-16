"""Static, non-executing contract for ordinary Task text judges."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

MAX_CONFIG_BYTES = 1024 * 1024


class _UniqueLoader(yaml.SafeLoader):
    pass


def _mapping(loader: _UniqueLoader, node: yaml.MappingNode) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if not isinstance(key, str):
            raise ValueError("judge.yaml mapping keys must be strings")
        if key in result:
            raise ValueError(f"duplicate judge.yaml key: {key}")
        result[key] = loader.construct_object(value_node, deep=True)
    return result


_UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


@dataclass(frozen=True)
class JudgeArtifact:
    id: str
    path: str
    required: bool
    type: str
    source: str = "workdir"


@dataclass(frozen=True)
class Rubric:
    id: str
    question: str
    artifact_refs: tuple[str, ...]
    pass_criteria: tuple[str, ...]
    fail_criteria: tuple[str, ...]
    scope_limits: tuple[str, ...] = ()


@dataclass(frozen=True)
class JudgeConfig:
    artifacts: tuple[JudgeArtifact, ...]
    rubrics: tuple[Rubric, ...]
    rule_weight: float = 0.8
    llm_weight: float = 0.2

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "artifacts": [asdict(item) for item in self.artifacts],
            "llm_judge": {
                "method": "rubric_binary_mean",
                "rubrics": [asdict(item) for item in self.rubrics],
            },
            "score_merge": {
                "method": "weighted_sum",
                "rule_weight": self.rule_weight,
                "llm_weight": self.llm_weight,
            },
        }


def _object(value: Any, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise ValueError("judge.yaml expected a mapping")
    if required - value.keys() or value.keys() - required - optional:
        raise ValueError(
            f"invalid judge.yaml fields: expected {sorted(required | optional)}"
        )
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError("judge.yaml expected a nonempty string")
    return value


def _id(value: Any) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", _text(value)):
        raise ValueError("judge.yaml IDs must contain only letters, digits, _, . or -")
    return value


def _list(value: Any, *, nonempty: bool = True, maximum: int | None = None) -> list:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(
            "judge.yaml expected a nonempty list"
            if nonempty
            else "judge.yaml expected a list"
        )
    if maximum is not None and len(value) > maximum:
        raise ValueError(f"judge.yaml list exceeds {maximum} entries")
    return value


def _weight(value: Any) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("judge.yaml weights must be finite nonnegative numbers")
    return float(value)


def load_judge_config(path: Path) -> JudgeConfig:
    with path.open("rb") as stream:
        return parse_judge_config(stream.read(MAX_CONFIG_BYTES + 1))


def parse_judge_config(content: str | bytes) -> JudgeConfig:
    """Validate YAML without reading evidence or executing Task/model code."""
    if len(content) > MAX_CONFIG_BYTES or (
        isinstance(content, str) and len(content.encode("utf-8")) > MAX_CONFIG_BYTES
    ):
        raise ValueError("judge.yaml exceeds 1 MiB")
    if isinstance(content, bytes):
        content = content.decode("utf-8")
    try:
        value = yaml.load(content, Loader=_UniqueLoader)
    except yaml.YAMLError as exc:
        raise ValueError("invalid judge.yaml syntax") from exc
    value = _object(value, {"version", "artifacts", "llm_judge"}, {"score_merge"})
    if type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("unsupported judge.yaml version")
    artifacts = []
    for item in _list(value["artifacts"], maximum=32):
        item = _object(item, {"id", "path", "required", "type"}, {"source"})
        path = _text(item["path"])
        if any(part in {"", ".", ".."} for part in path.split("/")) or any(
            char in path for char in "\\:\x00"
        ):
            raise ValueError(
                "judge artifact path must be a contained relative POSIX path"
            )
        if type(item["required"]) is not bool:
            raise ValueError("judge artifact required must be boolean")
        source = _text(item.get("source", "workdir"))
        if source not in {
            "workdir",
            "tests",
            "artifacts",
            "agent_logs",
            "verifier_logs",
        }:
            raise ValueError(f"unknown judge artifact source: {source}")
        kind = _text(item["type"])
        if kind not in {"txt", "md", "json", "yaml", "csv", "html"}:
            raise ValueError(f"unsupported judge text type: {kind}")
        artifacts.append(
            JudgeArtifact(_id(item["id"]), path, item["required"], kind, source)
        )
    artifact_ids = {item.id for item in artifacts}
    if len(artifact_ids) != len(artifacts):
        raise ValueError("duplicate judge artifact ID")
    judge = _object(value["llm_judge"], {"method", "rubrics"})
    if judge["method"] != "rubric_binary_mean":
        raise ValueError("unknown llm_judge method")
    rubrics = []
    for item in _list(judge["rubrics"], maximum=32):
        item = _object(
            item,
            {"id", "question", "artifact_refs", "pass_criteria", "fail_criteria"},
            {"scope_limits"},
        )
        refs = tuple(_id(ref) for ref in _list(item["artifact_refs"], maximum=8))
        if len(set(refs)) != len(refs) or set(refs) - artifact_ids:
            raise ValueError("unknown or duplicate judge artifact reference")
        rubrics.append(
            Rubric(
                _id(item["id"]),
                _text(item["question"]),
                refs,
                tuple(_text(text) for text in _list(item["pass_criteria"])),
                tuple(_text(text) for text in _list(item["fail_criteria"])),
                tuple(
                    _text(text)
                    for text in _list(item.get("scope_limits", []), nonempty=False)
                ),
            )
        )
    if len({item.id for item in rubrics}) != len(rubrics):
        raise ValueError("duplicate judge rubric ID")
    merge = _object(
        value.get("score_merge", {"method": "weighted_sum"}),
        {"method"},
        {"rule_weight", "llm_weight"},
    )
    if merge["method"] != "weighted_sum":
        raise ValueError("unknown score_merge method")
    rule, llm = (
        _weight(merge.get("rule_weight", 0.8)),
        _weight(merge.get("llm_weight", 0.2)),
    )
    if rule + llm <= 0 or not math.isfinite(rule + llm):
        raise ValueError("judge total weight must be finite and positive")
    return JudgeConfig(tuple(artifacts), tuple(rubrics), rule, llm)
