"""Public interface for installed evaluation harnesses (version 1)."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NotRequired, Protocol, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def validate_configuration(value):
    def visit(item, depth=0):
        if depth > 32:
            raise ValueError("Jobs configuration exceeds 32 levels")
        if isinstance(item, dict):
            for child in item.values():
                visit(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                visit(child, depth + 1)

    visit(value)
    if (
        len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        > 256 * 1024
    ):
        raise ValueError("Jobs configuration exceeds 256 KiB")
    return value


class Variant(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    agent: str = Field(min_length=1, max_length=1000)
    model: str | None = Field(default=None, max_length=1000)
    options: dict[str, Any] = Field(default_factory=dict)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    harness: str = "harbor"
    tasks: list[str] = Field(min_length=1, max_length=1000)
    variants: list[Variant] = Field(min_length=1, max_length=32)
    settings: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def bounded(cls, value):
        return validate_configuration(value)


@dataclass(frozen=True)
class HarnessContext:
    workspace: Path
    settings: dict[str, Any] = field(default_factory=dict)


class CatalogTask(TypedDict):
    id: str
    label: str
    available: NotRequired[bool]
    error: NotRequired[str | None]


class CatalogDataset(TypedDict):
    id: str
    label: str
    tasks: list[CatalogTask]
    error: NotRequired[str | None]


class NativeResult(TypedDict):
    id: str
    task: str
    state: str
    score: float | None
    score_source: str | None
    variant_id: str
    variant_label: NotRequired[str]
    agent_name: NotRequired[str]
    model: NotRequired[str | None]
    trajectory_path: NotRequired[str]


class ResultRecord(BaseModel):
    """Validate plugin output while retaining harness-owned JSON fields."""

    model_config = ConfigDict(extra="allow", strict=True, allow_inf_nan=False)
    id: str = Field(min_length=1, max_length=1000)
    task: str
    state: str
    score: float | int | None
    score_source: str | None
    variant_id: str | None = None
    variant_label: str | None = None
    trajectory_path: str | None = None
    agent_name: str | None = None
    model: str | None = None

    @model_validator(mode="before")
    @classmethod
    def serializable(cls, value):
        def visit(item, depth=0):
            if depth > 64:
                raise ValueError("harness result exceeds 64 levels")
            if isinstance(item, dict):
                if any(not isinstance(key, str) for key in item):
                    raise ValueError("harness result object keys must be strings")
                for child in item.values():
                    visit(child, depth + 1)
            elif isinstance(item, list):
                for child in item:
                    visit(child, depth + 1)
            elif item is not None and not isinstance(item, (str, bool, int, float)):
                raise ValueError("harness results must contain only JSON values")

        visit(value)
        json.dumps(value, allow_nan=False)
        return value

    @field_validator("score")
    @classmethod
    def finite_score(cls, value):
        try:
            if value is not None and not math.isfinite(value):
                raise ValueError("score must be finite")
        except OverflowError as exc:
            raise ValueError("score exceeds the supported numeric range") from exc
        return value


class RunControl(Protocol):
    run_id: str
    output_dir: Path
    control_dir: Path
    workspace: Path

    def report(self, **progress: Any) -> None: ...

    async def subprocess(self, argv: list[str], **options: Any) -> int:
        """Run a managed child; cancellation cleans up its descendants."""
        ...


class Harness(Protocol):
    """All returned objects must be JSON serializable; scores are native values.

    execute must propagate asyncio.CancelledError after awaiting cleanup. Its
    worker runs outside the web process. read_results must be read-only, and
    trajectory paths, when supplied, must remain inside output_dir. Trial ids
    must be unique within one Job and stable across reads. NativeResult.score
    is the harness's retained scalar authority, never a recomputed workspace score.
    """

    def describe(self, context: HarnessContext) -> dict[str, Any]: ...

    def catalog(self, context: HarnessContext) -> list[CatalogDataset]: ...

    def prepare(
        self, request: RunRequest, context: HarnessContext
    ) -> dict[str, Any]: ...

    async def execute(self, prepared: dict[str, Any], control: RunControl) -> None: ...

    def read_results(self, output_dir: Path) -> list[NativeResult]: ...
