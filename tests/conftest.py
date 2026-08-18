from __future__ import annotations

import os
from pathlib import Path

import pytest

# Root conftest loads before test modules import Harbor.
os.environ["HARBOR_TELEMETRY"] = "0"
os.environ.setdefault("PEVAL_FIXTURE_API_TOKEN", "fixture-secret")


_SENSITIVE_ENV_NAMES = {
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "HF_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "NPM_TOKEN",
    "PEVAL_CONFIG",
    "PSYCHEVO_DB",
}
_SENSITIVE_ENV_PREFIXES = (
    "ANTHROPIC_",
    "AWS_",
    "AZURE_",
    "DEEPSEEK_",
    "GEMINI_",
    "GOOGLE_",
    "GROQ_",
    "OPENAI_",
    "OPENCODE_",
    "OPENROUTER_",
    "PEVO_",
    "PSYCHEVO_",
    "XAI_",
)
_SENSITIVE_ENV_SUFFIXES = (
    "_API_KEY",
    "_API_TOKEN",
    "_ACCESS_TOKEN",
    "_AUTH_TOKEN",
    "_CREDENTIALS",
    "_PASSWORD",
    "_SECRET",
    "_SECRET_KEY",
)


@pytest.fixture(autouse=True)
def isolated_test_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for name in tuple(os.environ):
        if (
            name in _SENSITIVE_ENV_NAMES
            or name.startswith(_SENSITIVE_ENV_PREFIXES)
            or name.endswith(_SENSITIVE_ENV_SUFFIXES)
        ):
            monkeypatch.delenv(name, raising=False)

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    for name, leaf in (
        ("XDG_CONFIG_HOME", "config"),
        ("XDG_DATA_HOME", "data"),
        ("XDG_CACHE_HOME", "cache"),
        ("XDG_STATE_HOME", "state"),
    ):
        target = tmp_path / "xdg" / leaf
        target.mkdir(parents=True)
        monkeypatch.setenv(name, str(target))
    monkeypatch.setenv("HARBOR_TELEMETRY", "0")
