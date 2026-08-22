from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import sysconfig
import tempfile
from importlib.metadata import distribution
from pathlib import Path

try:
    from scripts._smoke_harbor import assert_harbor_inspect, write_harbor_trial
except ModuleNotFoundError:  # Executed directly from scripts/.
    from _smoke_harbor import assert_harbor_inspect, write_harbor_trial

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/peval/fixtures/common_session.jsonl"


def command_path(name: str) -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return Path(sysconfig.get_path("scripts")) / f"{name}{suffix}"


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


def require_isolated_wheel_install() -> None:
    direct_url = distribution("psycheval").read_text("direct_url.json")
    if direct_url is None:
        return
    try:
        install_source = json.loads(direct_url)
    except json.JSONDecodeError:
        return
    if install_source.get("dir_info", {}).get("editable") is True:
        raise RuntimeError(
            "distribution smoke requires an isolated wheel installation; "
            "the current interpreter uses an editable psycheval checkout. "
            "Build and install the wheel, then run this script with that "
            "environment's Python (see docs/testing.md)."
        )


def main() -> int:
    require_isolated_wheel_install()
    peval = command_path("peval")
    harness = command_path("psycheval-psychevo-harness")
    if not peval.is_file() or not harness.is_file():
        raise RuntimeError(
            "installed distribution is missing a documented console script"
        )
    if command_path("peval-py").exists():
        raise RuntimeError("installed environment unexpectedly exposes peval-py")
    if importlib.util.find_spec("peval_py") is not None:
        raise RuntimeError("installed environment unexpectedly exposes peval_py")
    if importlib.util.find_spec("psycheval.peval") is not None:
        raise RuntimeError("installed environment unexpectedly exposes psycheval.peval")
    scripts = {entry.name for entry in distribution("psycheval").entry_points}
    if "peval" not in scripts or "psycheval-psychevo-harness" not in scripts:
        raise RuntimeError("psycheval metadata is missing a documented entry point")

    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp)
        home = tmp / "home"
        home.mkdir()
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(home),
                "HARBOR_TELEMETRY": "0",
                "SHELL": "/bin/bash",
                "_TYPER_COMPLETE_TEST_DISABLE_SHELL_DETECTION": "1",
            }
        )

        assert "Usage: peval" in run([str(peval), "-h"], cwd=tmp, env=env)
        assert "Usage: peval" in run([str(peval), "--help"], cwd=tmp, env=env)
        completion = run([str(peval), "--show-completion", "bash"], cwd=tmp, env=env)
        assert "_peval_completion" in completion
        module_help = run(
            [sys.executable, "-m", "psycheval.cli", "--help"],
            cwd=tmp,
            env=env,
        )
        assert "Usage: peval" in module_help
        assert "Run Psychevo and emit ATIF" in run(
            [str(harness), "--help"], cwd=tmp, env=env
        )

        harbor_trial = write_harbor_trial(tmp)
        assert_harbor_inspect(
            run(
                [str(peval), "view", "tr", "-p", str(harbor_trial)],
                cwd=tmp,
                env=env,
            )
        )

        trajectory = tmp / "trajectory.json"
        run(
            [
                str(peval),
                "export",
                "tr",
                "-a",
                "psychevo",
                "-p",
                str(FIXTURE),
                "-o",
                str(trajectory),
            ],
            cwd=tmp,
            env=env,
        )
        payload = json.loads(trajectory.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "ATIF-v1.7"
        assert payload["steps"]

        report = tmp / "report.html"
        run(
            [
                str(peval),
                "view",
                "tr",
                "-m",
                "raw",
                "-a",
                "psychevo",
                "-p",
                str(FIXTURE),
                "-f",
                "html",
                "-o",
                str(report),
            ],
            cwd=tmp,
            env=env,
        )
        html = report.read_text(encoding="utf-8")
        assert 'id="peval-data"' in html
        assert 'id="peval-render-options"' in html

    print("isolated psycheval wheel smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
