from __future__ import annotations

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


def test_installed_metadata_and_copied_adapter_share_the_package_version() -> None:
    from importlib.metadata import version

    import psycheval
    from psycheval import harbor

    assert version("psycheval") == psycheval.__version__ == harbor.__version__


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


def test_ci_uses_least_privilege_and_avoids_duplicate_branch_runs() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "permissions:\n  contents: read" in workflow
    assert "push:\n    branches: [main]" in workflow
    assert "concurrency:" in workflow
    assert "cancel-in-progress: true" in workflow


def test_ci_uses_only_the_editable_source_tool_installation() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "uv tool install -e . --force" in workflow
    assert "scripts/smoke_source_tool.py" in workflow
    assert "scripts/check_skill.py\n          skills/peval" in workflow
    assert "uv build" not in workflow
    assert ".whl" not in workflow
    assert ".tar.gz" not in workflow
    assert "smoke_distribution" not in workflow
    assert "check_distribution_assets" not in workflow
    assert "pyinstaller" not in workflow.lower()


def test_checkout_installs_the_tool_before_using_bare_peval_commands() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    install = readme.split("## Install", 1)[1].split("## Quick start", 1)[0]
    quick_start = readme.split("## Quick start", 1)[1].split("## Documentation", 1)[0]

    assert "uv tool install -e ." in install
    assert "peval init -r .local/evaluation" in quick_start
    assert "peval init\n" not in quick_start
    assert "peval --help" in quick_start
    assert "peval view trajectory --help" in quick_start


def test_removed_distribution_smoke_helpers_do_not_survive_as_dead_code() -> None:
    assert not (ROOT / "scripts/_smoke_harbor.py").exists()


def test_user_facing_peval_examples_do_not_use_python_or_uv_wrappers() -> None:
    paths = [ROOT / "README.md"]
    paths.extend((ROOT / "docs").rglob("*.md"))
    paths.extend((ROOT / "skills/peval").rglob("*.md"))

    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "uv run peval" not in text, path
        assert "python -m psycheval.cli" not in text, path


def test_single_peval_skill_owns_freeform_review_then_publication() -> None:
    skill_root = ROOT / "skills/peval"
    assert not (ROOT / "src/psycheval/assets/agent_skills").exists()
    files = {
        path.relative_to(skill_root).as_posix()
        for path in skill_root.rglob("*")
        if path.is_file()
    }
    assert files == {
        "SKILL.md",
        "assets/evaluation-report-template.md",
        "references/analysis-guide.md",
        "references/evaluation-report-workflow.md",
        "references/view-tr.md",
    }

    text = "\n".join(
        (skill_root / relative).read_text(encoding="utf-8")
        for relative in sorted(files)
    )
    assert "peval view tr -r <workspace> --source-ref <ref>" in text
    assert "peval publish evaluation-report" in text
    assert "complete current Markdown draft" in text
    assert "execute/build mode" in text
    assert "user's evaluation brief" in text
    assert "peval view task-skill" not in text
    assert "peval publish trial-analysis" not in text
    assert "--replace-revision" not in text
    assert "--expected-evidence-revision" not in text
    assert "--expected-skill-revision" not in text
    assert "--skill <skill-name>" not in text
    assert "trajectory_available" in text
