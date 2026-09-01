from __future__ import annotations

from pathlib import Path

from scripts import check_docs, check_skill

ROOT = Path(__file__).resolve().parents[1]


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
