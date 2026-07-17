from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path


WHEEL_REQUIRED = {
    "peval_py/assets/report.html",
    "peval_py/assets/report.js",
    "peval_py/assets/report_css/00-base.css",
}
SDIST_REQUIRED = {
    "package.json",
    "package-lock.json",
    "web/src/main.js",
    "web/src/app/report-app.js",
    "src/peval_py/assets/report.js",
}


def _failures(
    names: set[str],
    *,
    required: set[str],
    forbidden_parts: set[str],
) -> list[str]:
    failures = [f"missing {name}" for name in sorted(required - names)]
    for name in sorted(names):
        parts = set(Path(name).parts)
        if parts & forbidden_parts:
            failures.append(f"forbidden path {name}")
    return failures


def check_wheel(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
    return _failures(
        names,
        required=WHEEL_REQUIRED,
        forbidden_parts={"web", "node_modules", "package.json", "package-lock.json"},
    )


def check_sdist(path: Path) -> list[str]:
    with tarfile.open(path, "r:gz") as archive:
        members = [name for name in archive.getnames() if "/" in name]
    names = {name.split("/", 1)[1] for name in members}
    return _failures(
        names,
        required=SDIST_REQUIRED,
        forbidden_parts={"node_modules"},
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify peval-py browser assets in built distributions."
    )
    parser.add_argument("wheel", type=Path)
    parser.add_argument("sdist", type=Path)
    args = parser.parse_args()

    failures = check_wheel(args.wheel) + check_sdist(args.sdist)
    if failures:
        for failure in failures:
            print(f"distribution asset check: {failure}")
        return 1
    print("distribution assets match the wheel and sdist contracts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
