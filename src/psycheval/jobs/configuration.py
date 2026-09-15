"""Shared workspace configuration schema owned by Jobs."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from .protocol import Variant

HarnessId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]


class Defaults(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    tasks: list[str] = Field(default_factory=list, max_length=1000)
    variants: list[Variant] = Field(default_factory=list, max_length=32)
    settings: dict[str, Any] = Field(default_factory=dict)


class JobsDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    preferred_harness: HarnessId | None = None
    defaults: dict[HarnessId, Defaults] = Field(default_factory=dict)


class HarnessDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    harnesses: dict[HarnessId, dict[str, Any]] = Field(default_factory=dict)
