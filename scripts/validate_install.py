"""Create an empty wheel consumer environment and exercise it outside the repo."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", help="Wheel path or exact index requirement")
    parser.add_argument("--python", required=True)
    parser.add_argument("--constraints", type=Path)
    parser.add_argument("--echarts", type=Path, help="Preseeded ECharts smoke fixture")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    echarts = (
        args.echarts or root / "node_modules/echarts/dist/echarts.min.js"
    ).resolve()
    if not echarts.is_file():
        parser.error("ECharts fixture is missing; pass --echarts or run npm ci")
    package = (
        str(Path(args.package).resolve())
        if Path(args.package).is_file()
        else args.package
    )
    with tempfile.TemporaryDirectory(prefix="psycheval-wheel-") as directory:
        temporary = Path(directory)
        env = {
            name: value
            for name, value in os.environ.items()
            if name.upper()
            in {
                "PATH",
                "PATHEXT",
                "SYSTEMROOT",
                "SYSTEMDRIVE",
                "WINDIR",
                "COMSPEC",
                "TEMP",
                "TMP",
                "LANG",
            }
        }
        home = temporary / "home"
        home.mkdir()
        env.update(
            HOME=str(home),
            USERPROFILE=str(home),
            XDG_CONFIG_HOME=str(home / "config"),
            XDG_DATA_HOME=str(home / "data"),
            XDG_STATE_HOME=str(home / "state"),
            XDG_CACHE_HOME=str(home / "cache"),
            APPDATA=str(home / "appdata"),
            LOCALAPPDATA=str(home / "local"),
            PYTHONUTF8="1",
            PYTHONIOENCODING="utf-8",
            HARBOR_TELEMETRY_ENABLED="false",
        )
        # Interpreter selection can use uv's existing managed Python cache; the
        # installed program below receives only the isolated environment.
        subprocess.run(
            ["uv", "venv", str(temporary / "venv"), "--python", args.python], check=True
        )
        python = (
            temporary
            / "venv"
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        command = ["uv", "pip", "install", "--python", str(python), package]
        if args.constraints:
            command += ["-c", str(args.constraints.resolve())]
        if args.refresh:
            command += ["--refresh"]
        subprocess.run(command, check=True)
        subprocess.run(["uv", "pip", "check", "--python", str(python)], check=True)
        subprocess.run(
            [
                str(python),
                "-I",
                str(root / "scripts/smoke_installed.py"),
                "--repository",
                str(root),
                "--skill",
                str(root / "skills/peval"),
                "--echarts",
                str(echarts),
            ],
            cwd=temporary,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()
