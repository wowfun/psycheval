from __future__ import annotations

import json
import platform
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from psycheval.cli import app
from psycheval.harbor import workbuddy
from tests.fixtures.workbuddy import write_office_bundle


@pytest.mark.parametrize("environment", ["host", "container"])
@pytest.mark.parametrize("host_setting", ["explicit", "absent", "invalid"])
def test_prepare_validates_settings_and_prints_standalone_commands(
    tmp_path, monkeypatch, environment, host_setting
):
    bundle = tmp_path / "bundle"
    write_office_bundle(bundle)
    workspace = tmp_path / "evaluation"
    workspace.mkdir()
    config = workspace / "peval.toml"
    host_config = {
        "explicit": '[harbor.host]\nworkdir_root = "../trial workspaces"\n',
        "absent": "",
        "invalid": "[harbor.host]\nworkdir_root = 42\n",
    }[host_setting]
    config.write_text(
        host_config + '[[harbor.datasets]]\nid="office"\nformat="workbuddy.v1"\n'
        f"path={json.dumps(str(bundle))}\n",
        encoding="utf-8",
    )
    base = tmp_path / "base.yaml"
    base.write_text(
        yaml.safe_dump(
            {
                "agents": [{"name": "opencode"}],
                "environment": {
                    "import_path": "psycheval.harbor.environment:HostEnvironment",
                    "kwargs": {"host_access": {"filesystem": True, "process": True}},
                }
                if environment == "host"
                else {"type": "docker"},
            }
        )
    )
    monkeypatch.setattr(
        workbuddy, "validate_workbuddy_runtime", lambda: {"version": "fixture"}
    )
    monkeypatch.setattr(workbuddy, "validate_workbuddy_host_dependencies", lambda: None)
    monkeypatch.setattr(
        "psycheval.harbor.workbuddy_verifier.validate_office_profile", lambda *_: None
    )
    monkeypatch.setenv("PEVAL_CONFIG", str(tmp_path / "unrelated.toml"))
    before = {p: p.read_bytes() for p in workspace.rglob("*") if p.is_file()}
    result = CliRunner().invoke(
        app,
        [
            "harbor",
            "prepare",
            "--root",
            str(workspace),
            "--dataset",
            "office",
            "--config",
            str(base),
            "--task",
            "office-00",
        ],
    )
    if host_setting == "invalid":
        assert result.exit_code != 0
        assert "workdir_root" in result.output
        assert {
            p: p.read_bytes() for p in workspace.rglob("*") if p.is_file()
        } == before
        assert not (workspace / "harbor-plans").exists()
        return
    assert result.exit_code == 0, result.output
    assert "PEVAL_CONFIG" not in result.output
    if platform.system() == "Windows":
        assert "$env:PYTHONUTF8 = '1'" in result.output
        assert "$env:PYTHONIOENCODING = 'utf-8'" in result.output
    plans = list((workspace / "harbor-plans").glob("*/workbuddy-run-plan.json"))
    assert len(plans) == 1
    plan = json.loads(plans[0].read_text())
    generated = yaml.safe_load(Path(plan["jobs"][0]["config"]).read_text())
    if environment == "host":
        assert generated["environment"]["kwargs"]["workdir_root"] == str(
            tmp_path / "trial workspaces"
            if host_setting == "explicit"
            else Path.home() / "workspaces"
        )
    else:
        assert "workdir_root" not in generated["environment"].get("kwargs", {})
    if host_setting == "explicit":
        assert 'workdir_root = "../trial workspaces"' in config.read_text()
    assert "harbor" in result.output and "summarize" in result.output
