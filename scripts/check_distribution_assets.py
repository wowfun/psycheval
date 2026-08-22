from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path

WHEEL_REQUIRED = {
    "psycheval/assets/__init__.py",
    "psycheval/assets/report.css",
    "psycheval/assets/report.html",
    "psycheval/assets/report.js",
    "psycheval/assets/report_css/00-base.css",
    "psycheval/assets/report_css/05-data-table.css",
    "psycheval/assets/report_css/06-leaderboard-summary.css",
    "psycheval/assets/report_css/08-trajectory.css",
    "psycheval/assets/report_css/10-trace.css",
    "psycheval/assets/report_css/12-steps.css",
    "psycheval/assets/report_css/14-analysis.css",
    "psycheval/assets/report_css/16-timeline.css",
    "psycheval/assets/report_css/20-serve-toolbar.css",
    "psycheval/assets/report_css/22-source-forms.css",
    "psycheval/assets/report_css/23-harbor-workbench.css",
    "psycheval/assets/report_css/24-source-list-export.css",
    "psycheval/assets/report_css/26-step-drawer.css",
    "psycheval/assets/report_css/28-workspace-reports.css",
    "psycheval/assets/report_css/30-workspace-views.css",
    "psycheval/assets/serve_harbor_datasets.html",
    "psycheval/assets/serve_report_manager.html",
    "psycheval/assets/serve_source_manager.html",
}
SDIST_REQUIRED = {
    "package.json",
    "package-lock.json",
    "web/src/main.js",
    "web/src/app/report-app.js",
} | {f"src/{name}" for name in WHEEL_REQUIRED}


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
        forbidden_parts={
            "peval",
            "web",
            "node_modules",
            "package.json",
            "package-lock.json",
        },
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
        description="Verify peval browser assets in built distributions."
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
