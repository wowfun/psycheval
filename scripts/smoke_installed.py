"""Run with the installed wheel's Python, outside the checkout, using -I."""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.resources
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--skill", type=Path, required=True)
    parser.add_argument("--echarts", type=Path, required=True)
    args = parser.parse_args()

    from fastapi.testclient import TestClient

    import psycheval
    from psycheval.atif import validate_atif_trajectory
    from psycheval.config import ToolConfig
    from psycheval.harbor import __version__
    from psycheval.harbor.acp_agent import HostACPAgent
    from psycheval.harbor.agent import ExternalHarnessAgent
    from psycheval.harbor.opencode import HostOpenCodeAgent
    from psycheval.harbor.workbuddy import prepare_workbuddy_job
    from psycheval.jobs.protocol import Harness
    from psycheval.serve.access import ServeAccess
    from psycheval.serve.api import create_app
    from psycheval.serve.assets import ECHARTS_ASSET_PATH, echarts_cache_path
    from psycheval.serve.runtime import ServeRuntime
    from psycheval.state import open_workspace_state

    assert (
        not Path(psycheval.__file__).resolve().is_relative_to(args.repository / "src")
    )
    distribution = importlib.metadata.distribution("psycheval")
    assert distribution.version == psycheval.__version__ == __version__
    assert {
        ep.name for ep in distribution.entry_points if ep.group == "console_scripts"
    } == {"peval"}
    assert HostACPAgent.capabilities.mcp_servers
    assert ExternalHarnessAgent.capabilities.skills
    assert not HostOpenCodeAgent.capabilities.bridges
    assert callable(prepare_workbuddy_job) and Harness is not None
    trajectory = {
        "schema_version": "ATIF-v1.8",
        "agent": {"name": "smoke", "version": "1"},
        "steps": [
            {
                "step_id": 1,
                "source": "user",
                "message": [
                    {
                        "type": "audio",
                        "source": {"media_type": "audio/wav", "path": "sample.wav"},
                    }
                ],
            }
        ],
    }
    validate_atif_trajectory(trajectory)
    package = importlib.resources.files("psycheval")
    assert package.joinpath(
        "assets/web/vendor/pretty-aui/THIRD_PARTY_LICENSES.txt"
    ).is_file()
    executable = Path(sys.executable).parent / (
        "peval.exe" if os.name == "nt" else "peval"
    )
    subprocess.run([str(executable), "--help"], check=True, capture_output=True)
    root = Path.cwd() / "workspace"

    def initialize(*extra):
        return json.loads(
            subprocess.check_output(
                [str(executable), "init", "-r", str(root), "--json", *extra],
                encoding="utf-8",
            )
        )

    assert initialize()["agent_skill"] is None
    assert (
        initialize("--skill", str(args.skill))["agent_skill"]["action"] == "installed"
    )
    skill_file = root / ".agents/skills" / args.skill.name / "SKILL.md"
    skill_file.write_text("edited", encoding="utf-8")
    assert initialize("--skill", str(args.skill))["agent_skill"]["action"] == "replaced"
    assert skill_file.read_bytes() == (args.skill / "SKILL.md").read_bytes()
    store = open_workspace_state(str(root))
    runtime = ServeRuntime(store, ToolConfig(workspace_root=str(root), locale="en"))
    try:
        cache = echarts_cache_path(store)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(args.echarts.read_bytes())
        with TestClient(create_app(runtime, ServeAccess(None))) as client:
            for route in (
                "/",
                "/jobs",
                "/datasets",
                "/assets/peval/workspace.css",
                "/assets/peval/main.js",
                ECHARTS_ASSET_PATH,
            ):
                response = client.get(route)
                assert response.status_code == 200 and response.content, route
    finally:
        runtime.close()
        store.close()
    print(
        f"Installed distribution smoke passed: {distribution.version}, Python {sys.version.split()[0]}"
    )


if __name__ == "__main__":
    main()
