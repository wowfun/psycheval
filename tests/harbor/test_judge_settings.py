from __future__ import annotations

import os
from dataclasses import FrozenInstanceError

import pytest

from psycheval.harbor.verifier import JudgeSettings
from psycheval.harbor.verifier._judge_settings import _JudgeConnection


@pytest.mark.parametrize("flag", [None, "false", "FALSE", "0", "true", "TRUE", "1"])
def test_connection_mapping_parses_native_enable_flag(flag):
    env = {} if flag is None else {"PEVAL_JUDGE_ENABLED": flag}
    connection = _JudgeConnection.from_mapping(env)
    assert connection.enabled is (flag in {"true", "TRUE", "1"})
    assert connection.base_url == connection.model == connection.api_key == ""


@pytest.mark.parametrize("flag", ["", "yes", " true ", "2"])
def test_connection_mapping_rejects_invalid_enable_flags(flag):
    with pytest.raises(ValueError, match="PEVAL_JUDGE_ENABLED must be true or false"):
        _JudgeConnection.from_mapping({"PEVAL_JUDGE_ENABLED": flag})


def test_connection_mapping_is_isolated_normalized_and_redacted(monkeypatch):
    monkeypatch.setenv("PEVAL_JUDGE_ENABLED", "true")
    monkeypatch.setenv("PEVAL_JUDGE_MODEL", "ambient-model")
    monkeypatch.setenv("PEVAL_JUDGE_API_KEY", "ambient-secret")
    env = {
        "PEVAL_JUDGE_ENABLED": "1",
        "PEVAL_JUDGE_BASE_URL": "https://fixture.invalid/v1///",
        "PEVAL_JUDGE_MODEL": " fixture-model \t",
        "PEVAL_JUDGE_API_KEY": " fixture-private-key ",
        "PEVAL_JUDGE_CONCURRENCY": "invalid-unused-setting",
    }
    original = dict(env)
    process = dict(os.environ)
    connection = _JudgeConnection.from_mapping(env)
    assert connection == _JudgeConnection(
        True, "https://fixture.invalid/v1", "fixture-model", " fixture-private-key "
    )
    assert "fixture-private-key" not in repr(connection)
    assert _JudgeConnection.from_mapping({}) == _JudgeConnection()
    assert env == original and dict(os.environ) == process
    with pytest.raises(FrozenInstanceError):
        connection.model = "changed"


@pytest.mark.parametrize(
    "values,field",
    [
        ({"enabled": 1}, "enabled"),
        ({"enabled": "true"}, "enabled"),
        ({"base_url": None}, "base_url"),
        ({"model": 1}, "model"),
        ({"api_key": None}, "api_key"),
    ],
)
def test_connection_constructor_checks_types(values, field):
    with pytest.raises(ValueError, match=f"Judge {field}"):
        _JudgeConnection(**values)


@pytest.mark.parametrize(
    "route,field",
    [
        ({"MODEL": "fixture-model"}, "BASE_URL"),
        ({"BASE_URL": "https://fixture.invalid/v1"}, "MODEL"),
        ({"BASE_URL": "file:///tmp/model", "MODEL": "fixture-model"}, "BASE_URL"),
    ],
)
def test_only_full_settings_validate_required_native_connection(
    monkeypatch, route, field
):
    env = {"PEVAL_JUDGE_ENABLED": "true"}
    env.update({"PEVAL_JUDGE_" + key: value for key, value in route.items()})
    assert _JudgeConnection.from_mapping(env).enabled
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match="PEVAL_JUDGE_" + field):
        JudgeSettings.from_env()


def test_disabled_native_settings_do_not_parse_other_values(monkeypatch):
    env = {
        "PEVAL_JUDGE_ENABLED": "0",
        "PEVAL_JUDGE_BASE_URL": "invalid-unused-url",
        "PEVAL_JUDGE_MODEL": " \t",
        "PEVAL_JUDGE_API_KEY": "unused-secret",
        "PEVAL_JUDGE_CONCURRENCY": "invalid-unused-number",
        "PEVAL_JUDGE_REASONING_EFFORT": "",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert _JudgeConnection.from_mapping(env) == _JudgeConnection()
    assert JudgeSettings.from_env() == JudgeSettings()
