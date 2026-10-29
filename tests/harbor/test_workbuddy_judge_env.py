from __future__ import annotations

import logging
import os

import pytest

from psycheval.harbor import workbuddy_verifier
from psycheval.harbor.verifier import JudgeSettings

WB = "WORKBUDDY_VERIFIER_LLM_"
NATIVE = "PEVAL_JUDGE_"
ROUTE = {
    "BASE_URL": "https://fixture.invalid/v1",
    "API_KEY": "fixture-private-route-key",
    "MODEL": "fixture-model",
}
LOGGER = logging.getLogger(__name__)


def set_route(monkeypatch, prefix):
    for field, value in ROUTE.items():
        monkeypatch.setenv(prefix + field, value)
    if prefix == NATIVE:
        monkeypatch.setenv(NATIVE + "ENABLED", "true")


def resolve(env=None):
    return workbuddy_verifier._resolve_workbuddy_env(env or {}, LOGGER)


def test_process_route_is_whitelisted_and_resolved_once(monkeypatch, caplog):
    set_route(monkeypatch, WB)
    monkeypatch.setenv(WB + "MAX_OUTPUT_TOKENS", "8192")
    monkeypatch.setenv(WB + "UNRELATED", "not-forwarded")
    monkeypatch.setenv("FIXTURE_ROUTE_MODEL", "declared-model")
    monkeypatch.setenv(WB + "MODEL", "${FIXTURE_ROUTE_MODEL}")
    before = dict(os.environ)
    with caplog.at_level(logging.INFO):
        result = resolve()
    assert result == {
        **{WB + field: value for field, value in ROUTE.items()},
        WB + "MODEL": "${FIXTURE_ROUTE_MODEL}",
        WB + "MAX_OUTPUT_TOKENS": "8192",
    }
    assert resolve({WB + "MODEL": "${FIXTURE_ROUTE_MODEL}"})[WB + "MODEL"] == (
        "declared-model"
    )
    assert "configured from WORKBUDDY_VERIFIER_LLM_*" in caplog.text
    assert all(value not in caplog.text for value in ROUTE.values())
    assert dict(os.environ) == before


@pytest.mark.parametrize("field", [*ROUTE, "MAX_OUTPUT_TOKENS"])
@pytest.mark.parametrize("value", ["", "${FIXTURE_ROUTE_OVERRIDE}"])
def test_explicit_workbuddy_values_override_process_defaults(monkeypatch, field, value):
    set_route(monkeypatch, WB)
    monkeypatch.setenv(WB + "MAX_OUTPUT_TOKENS", "8192")
    monkeypatch.setenv("FIXTURE_ROUTE_OVERRIDE", "explicit-value")
    env = {WB + field: value}
    result = resolve(env)
    assert result[WB + field] == ("explicit-value" if value else "")
    assert env == {WB + field: value}


@pytest.mark.parametrize("field", [*ROUTE, "MAX_OUTPUT_TOKENS"])
@pytest.mark.parametrize("origin", ["process", "explicit"])
def test_any_workbuddy_declaration_blocks_native_fallback(
    monkeypatch, field, origin, caplog
):
    set_route(monkeypatch, NATIVE)
    env = {WB + field: ""}
    if origin == "process":
        monkeypatch.setenv(WB + field, "")
        result = resolve()
    else:
        result = resolve(env)
    assert result == env
    assert "WORKBUDDY_VERIFIER_LLM_* is incomplete" in caplog.text
    assert NATIVE not in caplog.text


@pytest.mark.parametrize("flag", [None, "false", "0", "FALSE", "true", "1", "TRUE"])
def test_native_fallback_respects_enable_flag(monkeypatch, flag, caplog):
    set_route(monkeypatch, NATIVE)
    if flag is None:
        monkeypatch.delenv(NATIVE + "ENABLED")
    else:
        monkeypatch.setenv(NATIVE + "ENABLED", flag)
    with caplog.at_level(logging.INFO):
        result = resolve()
    if flag in {"true", "1", "TRUE"}:
        assert result == {WB + field: value for field, value in ROUTE.items()}
        assert "configured from PEVAL_JUDGE_*" in caplog.text
    else:
        assert result == {}
        assert not caplog.records


def test_native_fallback_uses_explicit_values_and_only_connection_fields(monkeypatch):
    set_route(monkeypatch, NATIVE)
    monkeypatch.setenv("FIXTURE_ROUTE_MODEL", "explicit-model")
    monkeypatch.setenv(NATIVE + "CONCURRENCY", "invalid-but-not-a-route-setting")
    monkeypatch.setenv(NATIVE + "REASONING_EFFORT", "high")
    env = {NATIVE + "ENABLED": "1", NATIVE + "MODEL": "${FIXTURE_ROUTE_MODEL}"}
    result = resolve(env)
    assert result == {
        NATIVE + "ENABLED": "1",
        NATIVE + "MODEL": "explicit-model",
        **{WB + field: value for field, value in ROUTE.items()},
        WB + "MODEL": "explicit-model",
    }
    assert env[NATIVE + "MODEL"] == "${FIXTURE_ROUTE_MODEL}"
    assert resolve({NATIVE + "ENABLED": "false"}) == {NATIVE + "ENABLED": "false"}


@pytest.mark.parametrize("explicit", [False, True])
def test_native_fallback_and_settings_share_normalized_fields(monkeypatch, explicit):
    set_route(monkeypatch, NATIVE)
    route = {
        "BASE_URL": "https://fixture.invalid/v1///",
        "MODEL": " normalized-model \t",
        "API_KEY": " fixture-private-route-key ",
    }
    env = {}
    for field, value in route.items():
        if explicit:
            env[NATIVE + field] = value
        else:
            monkeypatch.setenv(NATIVE + field, value)
    settings = (
        JudgeSettings(True, route["BASE_URL"], route["MODEL"], route["API_KEY"])
        if explicit
        else JudgeSettings.from_env()
    )
    result = resolve(env)
    assert result[WB + "BASE_URL"] == settings.base_url == "https://fixture.invalid/v1"
    assert result[WB + "MODEL"] == settings.model == "normalized-model"
    assert result[WB + "API_KEY"] == settings.api_key == route["API_KEY"]


@pytest.mark.parametrize("field", list(ROUTE))
@pytest.mark.parametrize("value", [None, "", " \t"])
def test_native_projection_preserves_absent_and_declared_empty_fields(
    monkeypatch, field, value, caplog
):
    set_route(monkeypatch, NATIVE)
    monkeypatch.delenv(NATIVE + field)
    env = {} if value is None else {NATIVE + field: value}
    result = resolve(env)
    if value is None:
        assert WB + field not in result
    else:
        assert result[NATIVE + field] == value
        assert result[WB + field] == (value.strip() if field == "MODEL" else value)
    assert "missing required variables: " + NATIVE + field in caplog.text


def test_native_fallback_keeps_workbuddy_validation_policy(monkeypatch, caplog):
    set_route(monkeypatch, NATIVE)
    monkeypatch.setenv(NATIVE + "BASE_URL", "file:///fixture/model/")
    assert resolve()[WB + "BASE_URL"] == "file:///fixture/model"
    assert not caplog.records
    with pytest.raises(ValueError, match="PEVAL_JUDGE_BASE_URL"):
        JudgeSettings.from_env()


def test_native_keyless_settings_remain_incomplete_for_workbuddy(monkeypatch, caplog):
    set_route(monkeypatch, NATIVE)
    monkeypatch.delenv(NATIVE + "API_KEY")
    assert JudgeSettings.from_env().api_key == ""
    assert WB + "API_KEY" not in resolve()
    assert "missing required variables: PEVAL_JUDGE_API_KEY" in caplog.text


def test_direct_workbuddy_strings_are_not_native_normalized(monkeypatch):
    set_route(monkeypatch, WB)
    env = {WB + "BASE_URL": "https://fixture.invalid/v1///", WB + "MODEL": " model "}
    result = resolve(env)
    assert all(result[key] == value for key, value in env.items())


@pytest.mark.parametrize("flag", ["yes", " true ", "", "2", "private-invalid-flag"])
def test_invalid_native_flag_preserves_the_native_error(monkeypatch, flag):
    monkeypatch.setenv(NATIVE + "ENABLED", flag)
    with pytest.raises(ValueError) as native:
        JudgeSettings.from_env()
    with pytest.raises(ValueError) as fallback:
        resolve()
    assert str(fallback.value) == str(native.value)
    monkeypatch.delenv(NATIVE + "ENABLED")
    with pytest.raises(ValueError, match="PEVAL_JUDGE_ENABLED must be true or false"):
        resolve({NATIVE + "ENABLED": flag})


def test_selected_workbuddy_route_ignores_native_enable_flag(monkeypatch):
    set_route(monkeypatch, WB)
    monkeypatch.setenv(NATIVE + "ENABLED", "invalid-unused-flag")
    assert resolve() == {WB + field: value for field, value in ROUTE.items()}


@pytest.mark.parametrize("prefix", [WB, NATIVE])
@pytest.mark.parametrize("missing", list(ROUTE))
def test_incomplete_route_warns_without_values_and_continues(
    monkeypatch, caplog, prefix, missing
):
    set_route(monkeypatch, prefix)
    monkeypatch.delenv(prefix + missing)
    result = resolve()
    assert WB + missing not in result
    assert f"missing required variables: {prefix}{missing}" in caplog.text
    assert all(value not in caplog.text for value in ROUTE.values())


def test_whitespace_route_value_is_reported_missing(monkeypatch, caplog):
    set_route(monkeypatch, WB)
    assert resolve({WB + "MODEL": " \t"})[WB + "MODEL"] == " \t"
    assert f"missing required variables: {WB}MODEL" in caplog.text


def test_missing_explicit_reference_keeps_harbor_error(monkeypatch):
    monkeypatch.delenv("FIXTURE_MISSING_ROUTE_VALUE", raising=False)
    with pytest.raises(ValueError, match="FIXTURE_MISSING_ROUTE_VALUE.*not found"):
        resolve({WB + "MODEL": "${FIXTURE_MISSING_ROUTE_VALUE}"})


def test_no_route_is_quiet(caplog):
    with caplog.at_level(logging.INFO):
        assert resolve() == {}
    assert not caplog.records
