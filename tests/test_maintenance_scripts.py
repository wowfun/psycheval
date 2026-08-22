from __future__ import annotations

import io
from pathlib import Path

from scripts import check_docs, check_skill
from scripts.check_distribution_assets import WHEEL_REQUIRED
from scripts.smoke_pyinstaller import wait_serve_url

ROOT = Path(__file__).resolve().parents[1]


def test_wheel_contract_covers_every_runtime_asset() -> None:
    assets_root = ROOT / "src/psycheval/assets"
    expected = {
        f"psycheval/assets/{path.relative_to(assets_root).as_posix()}"
        for path in assets_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }

    assert WHEEL_REQUIRED == expected


def test_frozen_serve_smoke_ignores_output_before_the_url() -> None:
    class Process:
        stdout = io.StringIO("startup notice\npeval serve: http://127.0.0.1:58010/\n")
        stderr = io.StringIO()

        @staticmethod
        def poll() -> None:
            return None

    assert wait_serve_url(Process()) == "http://127.0.0.1:58010/"  # type: ignore[arg-type]


def test_docs_checker_handles_reference_links_and_parenthesized_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    source = docs / "index.md"
    source.write_text(
        "[parenthesized](guide_(one).md)\n"
        "[missing reference][missing]\n\n"
        "[missing]: does-not-exist.md\n",
        encoding="utf-8",
    )
    (docs / "guide_(one).md").write_text("# Guide\n", encoding="utf-8")
    monkeypatch.setattr(check_docs, "ROOT", tmp_path)

    assert check_docs.link_failures([source]) == [
        "docs/index.md: missing link target: does-not-exist.md"
    ]


def test_skill_checker_finds_markdown_linked_resources(tmp_path: Path) -> None:
    skill = tmp_path / "peval"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: peval\n"
        "description: Test skill.\n"
        "---\n\n"
        "Read the [missing guide](references/missing.md).\n",
        encoding="utf-8",
    )

    assert check_skill.validate(skill) == [
        "missing referenced skill resource: references/missing.md"
    ]
