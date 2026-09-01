from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


def run(command: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke an editable uv tool install.")
    parser.add_argument("peval", type=Path)
    parser.add_argument("skill", type=Path)
    args = parser.parse_args()
    peval = args.peval.resolve()
    if not peval.is_file():
        raise RuntimeError(f"source-tool peval command not found: {peval}")
    harness = peval.with_name("psycheval-psychevo-harness")
    if not harness.is_file():
        raise RuntimeError(f"source-tool Harbor harness not found: {harness}")
    skill = args.skill.resolve()
    if not skill.joinpath("SKILL.md").is_file():
        raise RuntimeError(f"source Agent Skill not found: {skill}")
    with tempfile.TemporaryDirectory() as raw_tmp:
        root = Path(raw_tmp)
        home = root / "home"
        home.mkdir()
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["HARBOR_TELEMETRY"] = "0"
        assert "Usage: peval" in run([str(peval), "--help"], cwd=root, env=env)
        assert "usage:" in run([str(harness), "--help"], cwd=root, env=env).lower()
        workspace = root / "workspace"
        initialized = json.loads(
            run([str(peval), "init", "-r", str(workspace), "--json"], cwd=root, env=env)
        )
        assert initialized["agent_skill"] is None
        assert not (workspace / ".agents").exists()
        installed = json.loads(
            run(
                [
                    str(peval),
                    "init",
                    "-r",
                    str(workspace),
                    "--skill",
                    str(skill),
                    "--json",
                ],
                cwd=root,
                env=env,
            )
        )
        assert installed["agent_skill"]["action"] == "installed"
        destination = workspace / ".agents/skills" / skill.name
        destination.joinpath("SKILL.md").write_text(
            "workspace edit\n", encoding="utf-8"
        )
        replaced = json.loads(
            run(
                [
                    str(peval),
                    "init",
                    "-r",
                    str(workspace),
                    "--skill",
                    str(skill),
                    "--json",
                ],
                cwd=root,
                env=env,
            )
        )
        assert replaced["agent_skill"]["action"] == "replaced"
        assert (
            destination.joinpath("SKILL.md").read_bytes()
            == skill.joinpath("SKILL.md").read_bytes()
        )
    print("editable uv source-tool smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
