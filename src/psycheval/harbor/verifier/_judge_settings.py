"""Native Judge settings and the connection values shared with verifier adapters."""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from urllib.parse import urlsplit


class _InvalidSetting(ValueError):
    def __init__(self, name: str, requirement: str):
        self.name = name
        self.requirement = requirement
        super().__init__(f"Judge {name} {requirement}")


@dataclass(frozen=True)
class _JudgeConnection:
    enabled: bool = False
    base_url: str = ""
    model: str = ""
    api_key: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise _InvalidSetting("enabled", "must be boolean")
        for name in ("base_url", "model", "api_key"):
            if not isinstance(getattr(self, name), str):
                raise _InvalidSetting(name, "must be a string")
        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))
        object.__setattr__(self, "model", self.model.strip())

    @classmethod
    def from_mapping(cls, env: Mapping[str, str]) -> _JudgeConnection:
        enabled = env.get("PEVAL_JUDGE_ENABLED", "false").lower()
        if enabled not in {"true", "false", "1", "0"}:
            raise ValueError("PEVAL_JUDGE_ENABLED must be true or false")
        if enabled in {"false", "0"}:
            return cls()
        return cls(
            enabled=True,
            base_url=env.get("PEVAL_JUDGE_BASE_URL", ""),
            model=env.get("PEVAL_JUDGE_MODEL", ""),
            api_key=env.get("PEVAL_JUDGE_API_KEY", ""),
        )


@dataclass(frozen=True)
class JudgeSettings(_JudgeConnection):
    concurrency: int = 4
    request_timeout: float = 30
    total_timeout: float = 120
    max_evidence_bytes: int = 1024 * 1024
    system_prompt: str | None = field(default=None, kw_only=True)
    user_prompt_template: str | None = field(default=None, kw_only=True)
    reasoning_effort: str | None = field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        super().__post_init__()
        for name in ("system_prompt", "user_prompt_template", "reasoning_effort"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise _InvalidSetting(name, "must be a nonempty string or None")
        if (
            self.user_prompt_template is not None
            and self.user_prompt_template.count("{context}") != 1
        ):
            raise _InvalidSetting(
                "user_prompt_template", "must contain exactly one {context} marker"
            )
        if self.reasoning_effort is not None:
            object.__setattr__(self, "reasoning_effort", self.reasoning_effort.strip())
        for name in ("concurrency", "max_evidence_bytes"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise _InvalidSetting(name, "must be a positive integer")
        for name in ("request_timeout", "total_timeout"):
            value = getattr(self, name)
            try:
                valid = (
                    type(value) in {int, float} and math.isfinite(value) and value > 0
                )
            except OverflowError:
                valid = False
            if not valid:
                raise _InvalidSetting(name, "must be finite and positive")
        if self.enabled:
            try:
                parsed = urlsplit(self.base_url)
                valid = (
                    parsed.scheme in {"http", "https"}
                    and parsed.hostname
                    and parsed.username is None
                    and parsed.password is None
                    and not parsed.query
                    and not parsed.fragment
                )
                _ = parsed.port
            except ValueError:
                valid = False
            if not valid:
                raise _InvalidSetting(
                    "base_url",
                    "must be an HTTP(S) API base URL without credentials or query",
                )
            if not self.model:
                raise _InvalidSetting("model", "is required")

    @classmethod
    def from_env(cls) -> JudgeSettings:
        connection = _JudgeConnection.from_mapping(os.environ)
        if not connection.enabled:
            return cls()

        def number(name: str, default: int | float, kind: type):
            try:
                return kind(os.environ.get("PEVAL_JUDGE_" + name, str(default)))
            except (ValueError, OverflowError) as exc:
                raise ValueError(
                    f"PEVAL_JUDGE_{name} must be a positive {kind.__name__}"
                ) from exc

        try:
            return cls(
                **asdict(connection),
                reasoning_effort=os.environ.get("PEVAL_JUDGE_REASONING_EFFORT"),
                concurrency=number("CONCURRENCY", 4, int),
                request_timeout=number("REQUEST_TIMEOUT_SEC", 30, float),
                total_timeout=number("TOTAL_TIMEOUT_SEC", 120, float),
                max_evidence_bytes=number("MAX_EVIDENCE_BYTES", 1024 * 1024, int),
            )
        except _InvalidSetting as exc:
            suffix = {
                "request_timeout": "REQUEST_TIMEOUT_SEC",
                "total_timeout": "TOTAL_TIMEOUT_SEC",
            }.get(exc.name, exc.name.upper())
            raise ValueError(f"PEVAL_JUDGE_{suffix} {exc.requirement}") from exc
