from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from psycheval.config import load_config as load_peval_config
from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    HarnessInvocation,
    RuntimeConfigError,
    RuntimePaths,
    load_effective_runtime_config,
    load_host_settings,
    optional_effective_runtime_config,
    write_effective_runtime_config,
)

_SYNTHETIC_HARNESS = (
    Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_harness.py"
)


def runtime_config(**overrides: object) -> EffectiveRuntimeConfig:
    values = {
        "paths": RuntimePaths(
            workdir="/workspace",
            tests="/tests",
            agent_logs="/logs/agent",
            verifier_logs="/logs/verifier",
            artifacts="/logs/artifacts",
        ),
        "workdir_root": "/home/test/workspaces",
        "workspace": "/home/test/workspaces/YfQLWrD",
        "python": "/usr/bin/python",
        "harness": HarnessInvocation(action="resume"),
    }
    values.update(overrides)
    return EffectiveRuntimeConfig(**values)


def test_host_settings_use_builtin_default_without_user_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))

    settings = load_host_settings(environ={}, cwd=tmp_path)

    assert settings.source_path is None
    assert settings.workdir_root == home / "workspaces"


def test_unified_config_is_read_by_each_section_owner(tmp_path: Path) -> None:
    config = tmp_path / "config" / "peval.toml"
    config.parent.mkdir()
    config.write_text(
        'description = "Nightly workspace"\n\n'
        '[adapters.psychevo]\ndefault_db_path = "state.db"\n\n'
        '[harbor.host]\nworkdir_root = "relative workspaces"\n'
        '[[harbor.datasets]]\nid = "pbench"\npath = "datasets/pbench"\n\n'
        '[[harbor.mounts]]\nid = "nightly"\npath = "runs/nightly"\n'
        'dataset_ids = ["pbench"]\n',
        encoding="utf-8",
    )
    original = config.read_bytes()

    settings = load_host_settings(
        environ={"PEVAL_CONFIG": str(config)}, cwd=tmp_path / "ignored"
    )

    assert settings.source_path == config.resolve()
    assert settings.workdir_root == config.parent / "relative workspaces"
    workspace = load_peval_config(workspace_root=str(config.parent))
    assert workspace.description == "Nightly workspace"
    assert workspace.adapter_default_db_paths == {
        "psychevo": str((config.parent / "state.db").resolve())
    }
    assert workspace.harbor_datasets[0].id == "pbench"
    assert workspace.harbor_mounts[0].dataset_ids == ("pbench",)
    assert config.read_bytes() == original


def test_host_settings_expand_configured_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = tmp_path / "peval.toml"
    config.write_text(
        '[harbor.host]\nworkdir_root = "~/custom-workspaces"\n', encoding="utf-8"
    )
    monkeypatch.setenv("HOME", str(tmp_path / "profile"))

    settings = load_host_settings(environ={"PEVAL_CONFIG": str(config)})

    assert settings.workdir_root == tmp_path / "profile" / "custom-workspaces"


def test_host_settings_empty_root_disables_automatic_workspace(tmp_path: Path) -> None:
    config = tmp_path / "peval.toml"
    config.write_text('[harbor.host]\nworkdir_root = ""\n', encoding="utf-8")

    settings = load_host_settings(environ={"PEVAL_CONFIG": "peval.toml"}, cwd=tmp_path)

    assert settings.workdir_root is None


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("[harbor.host]\nworkdir_root = 3\n", "must be a string"),
        ("[harbor.host]\nunknown = true\n", "unknown PEVAL config"),
        ("[harbor\n", "failed to read"),
    ],
)
def test_host_settings_reject_invalid_user_config(
    tmp_path: Path, content: str, message: str
) -> None:
    config = tmp_path / "peval.toml"
    config.write_text(content, encoding="utf-8")

    with pytest.raises(RuntimeConfigError, match=message):
        load_host_settings(environ={"PEVAL_CONFIG": str(config)})


def test_host_settings_reject_missing_explicit_config(tmp_path: Path) -> None:
    for configured in ("", str(tmp_path / "missing.toml")):
        with pytest.raises(RuntimeConfigError, match="readable TOML file"):
            load_host_settings(environ={"PEVAL_CONFIG": configured}, cwd=tmp_path)


def test_effective_runtime_config_round_trip_is_permission_restricted(
    tmp_path: Path,
) -> None:
    path = write_effective_runtime_config(
        tmp_path / "runtime" / "peval.json", runtime_config()
    )

    loaded = load_effective_runtime_config(path, require_harness=True)

    assert loaded == runtime_config()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_effective_runtime_config_round_trip_without_harness(tmp_path: Path) -> None:
    expected = runtime_config(harness=None)
    path = write_effective_runtime_config(tmp_path / "peval.json", expected)

    assert "harness" not in expected.to_dict()["harbor"]
    assert load_effective_runtime_config(path) == expected


def test_effective_runtime_config_rejects_unknown_and_old_protocol(
    tmp_path: Path,
) -> None:
    payload = runtime_config().to_dict()
    payload["harbor"]["harness"]["protocol_version"] = 1
    path = tmp_path / "peval.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeConfigError, match="protocol_version"):
        load_effective_runtime_config(path, require_harness=True)

    payload = runtime_config().to_dict()
    payload["paths"]["extra"] = "/leak"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeConfigError, match="paths.extra"):
        load_effective_runtime_config(path)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        (("harbor",), "host"),
        (("harbor", "host"), "workspace"),
        (("executables",), "python"),
    ],
)
def test_effective_runtime_config_requires_fixed_schema_fields(
    tmp_path: Path, section: tuple[str, ...], field: str
) -> None:
    payload = runtime_config().to_dict()
    parent = payload
    for part in section:
        parent = parent[part]
    parent.pop(field)
    path = tmp_path / f"missing-{field}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeConfigError, match=field):
        load_effective_runtime_config(path)


@pytest.mark.parametrize("payload", [None, "{not-json"])
def test_synthetic_harness_fails_fast_without_valid_effective_config(
    tmp_path: Path, payload: str | None
) -> None:
    environment = os.environ.copy()
    environment.pop("PEVAL_CONFIG", None)
    if payload is not None:
        config = tmp_path / "broken.json"
        config.write_text(payload, encoding="utf-8")
        environment["PEVAL_CONFIG"] = str(config)

    completed = subprocess.run(
        [
            sys.executable,
            str(_SYNTHETIC_HARNESS),
            "--mode",
            "single-step",
        ],
        input="Find the current source",
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
        check=False,
    )

    assert completed.returncode != 0
    assert "PEVAL_CONFIG" in completed.stderr


def test_optional_effective_runtime_config_preserves_container_fallback() -> None:
    assert optional_effective_runtime_config(environ={}) is None
