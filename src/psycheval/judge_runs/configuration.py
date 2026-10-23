"""Workspace-owned Judge profiles, separate from normal verifier settings."""

import os
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from psycheval.harbor.identifiers import validate_harbor_id
from psycheval.harbor.verifier import JudgeSettings


class JudgeProfile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, hide_input_in_errors=True
    )

    title: str = ""
    base_url: str
    model: str
    api_key: str = ""
    reasoning_effort: str | None = None
    system_prompt: str | None = None
    user_prompt_template: str | None = None
    concurrency: int = 4
    request_timeout: float = 30
    total_timeout: float = 120
    max_evidence_bytes: int = 1024 * 1024

    @field_validator("api_key")
    @classmethod
    def credential_reference(cls, value):
        if value and not re.fullmatch(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}", value):
            raise ValueError("Judge API keys must be ${ENV_VAR} references")
        return value

    @model_validator(mode="after")
    def validate_settings(self):
        self.settings()
        return self

    def settings(self) -> JudgeSettings:
        return JudgeSettings(
            enabled=True, **self.model_dump(exclude={"title", "api_key"})
        )

    def credential(self) -> str:
        if not self.api_key:
            return ""
        value = os.environ.get(self.api_key[2:-1])
        if not value:
            raise ValueError("Judge credential environment variable is unavailable")
        return value


class JudgeProfiles(BaseModel):
    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, hide_input_in_errors=True
    )

    default_profile: str | None = None
    profiles: dict[str, JudgeProfile] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_names(self):
        for key in self.profiles:
            validate_harbor_id(key, kind="Judge profile")
        if (
            self.default_profile is not None
            and self.default_profile not in self.profiles
        ):
            raise ValueError("default Judge profile does not exist")
        return self

    def select(self, name: str | None) -> tuple[str, JudgeProfile]:
        key = name or self.default_profile
        if not key or key not in self.profiles:
            raise ValueError("select an existing Judge profile")
        return key, self.profiles[key]
