from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE_SUFFIXES = {
    ".bash",
    ".cjs",
    ".css",
    ".fish",
    ".html",
    ".js",
    ".jsx",
    ".mjs",
    ".ps1",
    ".py",
    ".pyi",
    ".sh",
    ".ts",
    ".tsx",
}
GENERATED_WEB_VENDOR = Path("src/psycheval/assets/web/vendor")


def _is_authored_code(path: Path, relative: Path) -> bool:
    return (
        path.is_file()
        and path.suffix in CODE_SUFFIXES
        and "node_modules" not in relative.parts
        and "__pycache__" not in relative.parts
        and not relative.is_relative_to(GENERATED_WEB_VENDOR)
    )


def test_authored_code_files_stay_below_semantic_split_threshold() -> None:
    oversized: dict[str, int] = {}
    for source_root in ("src", "tests", "scripts", "web"):
        for path in (ROOT / source_root).rglob("*"):
            relative = path.relative_to(ROOT)
            if not _is_authored_code(path, relative):
                continue
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count > 2_000:
                oversized[relative.as_posix()] = line_count

    assert oversized == {}


def test_semantic_split_scope_excludes_only_the_generated_web_vendor() -> None:
    assert not _is_authored_code(
        ROOT / GENERATED_WEB_VENDOR / "pretty-aui/pretty-aui.js",
        GENERATED_WEB_VENDOR / "pretty-aui/pretty-aui.js",
    )
    assert _is_authored_code(
        ROOT / "src/psycheval/assets/web/modules/acp-client.js",
        Path("src/psycheval/assets/web/modules/acp-client.js"),
    )


def test_distribution_declares_the_repository_license() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]

    assert project["license"] == "MIT"
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License\n")


def test_vendored_pretty_aui_consolidates_third_party_licenses() -> None:
    standalone = ROOT / GENERATED_WEB_VENDOR / "pretty-aui"
    assert standalone.joinpath("LICENSE").is_file()
    third_party = standalone.joinpath("THIRD_PARTY_LICENSES.txt").read_text(
        encoding="utf-8"
    )
    for package_name in (
        "@agentclientprotocol/sdk",
        "dompurify",
        "marked",
        "preact",
        "zod",
    ):
        assert package_name in third_party
    assert not standalone.joinpath("licenses").exists()


def test_distribution_workflow_does_not_pin_artifact_version() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert re.search(r"\.local/dist/psycheval-\d+\.\d+\.\d+", workflow) is None
    assert ".local/dist/psycheval-*.whl" in workflow
    assert ".local/dist/psycheval-*.tar.gz" in workflow


def test_ci_uses_least_privilege_and_avoids_duplicate_branch_runs() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow
    assert "push:\n    branches: [main]" in workflow
    assert "concurrency:" in workflow
    assert "cancel-in-progress: true" in workflow


def test_pyinstaller_workflow_collects_harbor_data_and_smokes_workbench() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "--collect-data harbor" in workflow
    assert "--collect-data psycheval" in workflow
    assert "psycheval.peval" not in workflow
    assert "--additional-hooks-dir scripts/pyinstaller_hooks" in workflow
    assert "scripts/smoke_pyinstaller.py" in workflow
    assert ".local/pyinstaller/dist/peval" in workflow


def test_checkout_installs_the_tool_before_using_bare_peval_commands() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = readme.split("## Install", 1)[1].split("## Quick start", 1)[0]
    quick_start = readme.split("## Quick start", 1)[1].split("## Documentation", 1)[0]

    assert "uv tool install -e ." in install
    assert "peval init" in quick_start
    assert "peval --help" in quick_start
    assert "peval view trajectory --help" in quick_start


def test_user_facing_peval_examples_do_not_use_python_or_uv_wrappers() -> None:
    paths = [ROOT / "README.md"]
    paths.extend((ROOT / "docs").rglob("*.md"))
    paths.extend((ROOT / "skills/peval").rglob("*.md"))

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "uv run peval" not in text, path
        assert "python -m psycheval.cli" not in text, path


def test_peval_skill_is_read_only_and_trajectory_focused() -> None:
    skill_root = ROOT / "skills/peval"
    files = {
        path.relative_to(skill_root).as_posix()
        for path in skill_root.rglob("*")
        if path.is_file()
    }
    assert files == {
        "SKILL.md",
        "references/analysis-guide.md",
        "references/view-tr.md",
    }

    text = "\n".join(
        (skill_root / relative).read_text(encoding="utf-8")
        for relative in sorted(files)
    )
    for unsupported_workflow in (
        "peval export",
        "peval import",
        "peval init",
        "peval serve",
        "report_tools.py",
        "source-ref",
    ):
        assert unsupported_workflow not in text
    assert "peval view tr -p <trial-dir>" in text
    assert "trajectory_available" in text


def test_distribution_smoke_rejects_editable_install_with_actionable_error() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/smoke_distribution.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode != 0
    output = completed.stdout + completed.stderr
    assert "requires an isolated wheel installation" in output
    assert "current interpreter uses an editable psycheval checkout" in output
