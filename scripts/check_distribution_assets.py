from __future__ import annotations

import argparse
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = ROOT / "src/psycheval/assets"
WHEEL_REQUIRED = {
    f"psycheval/assets/{path.relative_to(ASSETS_ROOT).as_posix()}"
    for path in ASSETS_ROOT.rglob("*")
    if path.is_file() and "__pycache__" not in path.parts
}
SDIST_REQUIRED = {
    "package.json",
    "package-lock.json",
} | {f"src/{name}" for name in WHEEL_REQUIRED}
FORBIDDEN_BUNDLE = "psycheval/assets/report.js"
LEGACY_WORKSPACE_ASSETS = {
    "psycheval/assets/report.css",
    "psycheval/assets/report.html",
}
LEGACY_WORKSPACE_PREFIX = "psycheval/assets/report_css/"


def _failures(
    names: set[str],
    *,
    required: set[str],
    forbidden_parts: set[str],
    forbidden_names: set[str] = frozenset(),
    forbidden_prefixes: tuple[str, ...] = (),
) -> list[str]:
    failures = [f"missing {name}" for name in sorted(required - names)]
    for name in sorted(names):
        parts = set(Path(name).parts)
        if parts & forbidden_parts:
            failures.append(f"forbidden path {name}")
        if name in forbidden_names or name.startswith(forbidden_prefixes):
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
            "node_modules",
            "package.json",
            "package-lock.json",
        },
        forbidden_names={FORBIDDEN_BUNDLE, *LEGACY_WORKSPACE_ASSETS},
        forbidden_prefixes=(LEGACY_WORKSPACE_PREFIX,),
    )


def check_sdist(path: Path) -> list[str]:
    with tarfile.open(path, "r:gz") as archive:
        members = [name for name in archive.getnames() if "/" in name]
    names = {name.split("/", 1)[1] for name in members}
    return _failures(
        names,
        required=SDIST_REQUIRED,
        forbidden_parts={"node_modules"},
        forbidden_names={
            f"src/{FORBIDDEN_BUNDLE}",
            *(f"src/{name}" for name in LEGACY_WORKSPACE_ASSETS),
        },
        forbidden_prefixes=("web/src/", f"src/{LEGACY_WORKSPACE_PREFIX}"),
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
