"""Markdown inspection and selection through the public document interface."""

import codecs
from pathlib import Path

import pytest

from psycheval.harbor.documents import (
    DocumentLimitError,
    DocumentLimits,
    DocumentParseError,
    inspect_document,
    select_document,
)
from psycheval.harbor.documents.models import Paragraph, Table
from psycheval.harbor.evidence import SourceSnapshot


def inspect(text, **kwargs):
    return inspect_document(
        SourceSnapshot(Path("input.md"), text.encode("utf-8")), **kwargs
    )


def test_markdown_body_tables_and_source_ranges():
    text = "# 标题\n\n| A | B |\n| --- | --- |\n| **值** | a\\|b<br>第二行 |\n\n---\n\n<table><tr><th>C</th></tr><tr><td>&lt;x&gt;</td></tr></table>\n"
    report = inspect(text)
    assert report.to_markdown() == text
    assert [b.kind for b in report.blocks] == [
        "heading",
        "table",
        "thematic_break",
        "table",
    ]
    table = report.blocks[1]
    assert (table.start_line, table.end_line) == (2, 5)
    assert table.table.cells[-1].blocks[0].text == "a|b\n第二行"
    assert report.blocks[-1].table.cells[-1].blocks[0].text == "<x>"


def test_fences_comments_setext_and_nested_tables_are_not_top_level_tables():
    report = inspect(
        "```md\n|A|\n|---|\n|x|\n---\n```\n\n<!-- <table><tr><td>x</td></tr></table> -->\n\nTitle\n---\n\n> | A |\n> | --- |\n> | x |\n"
    )
    assert not any(b.table or b.kind == "thematic_break" for b in report.blocks)


@pytest.mark.parametrize(
    "html",
    [
        "<table><tr><td>x</th></tr></table>",
        "<table><tr><td>x",
        "<table><tr><td colspan='bad'>x</td></tr></table>",
        "<table><tr><td rowspan='0'>x</td></tr></table>",
        "<table><tr><td colspan='0'>x</td></tr></table>",
    ],
)
def test_malformed_html_is_not_a_valid_table(html):
    assert not any(b.table for b in inspect(html).blocks)


def test_html_spans_and_multiple_tables():
    report = inspect(
        "<table><tr><td rowspan='2'>A</td><td>B</td></tr><tr><td>C</td></tr></table><table><tr><td>D</td></tr></table>"
    )
    first, second = report.blocks
    assert first.table.cells[0].row_span == 2
    assert (first.table.cells[-1].row, first.table.cells[-1].column) == (2, 2)
    assert second.table.cells[0].blocks[0].text == "D"


def test_nested_html_tables_preserve_cell_block_order_and_outer_layout():
    text = "<table><tr><td rowspan='2'>before<table><tr><td>inner</td></tr></table>after</td><td>B</td></tr><tr><td>C</td></tr></table>"
    report = inspect(text)
    assert report.to_markdown() == text
    outer = report.blocks[0].table
    before, nested, after = outer.cells[0].blocks
    assert isinstance(before, Paragraph) and before.text == "before"
    assert isinstance(nested, Table)
    assert nested.cells[0].blocks[0].text == "inner"
    assert isinstance(after, Paragraph) and after.text == "after"
    assert (outer.cells[-1].row, outer.cells[-1].column) == (2, 2)


def test_deep_html_nesting_uses_the_document_budget_without_recursive_parsing():
    depth = 200
    text = "<table><tr><td>" * depth + "deep" + "</td></tr></table>" * depth
    table = inspect(text).blocks[0].table
    for _ in range(depth - 1):
        assert len(table.cells[0].blocks) == 1
        table = table.cells[0].blocks[0]
        assert isinstance(table, Table)
    assert table.cells[0].blocks[0].text == "deep"
    with pytest.raises(DocumentLimitError):
        inspect(text, limits=DocumentLimits(facts=100))


def test_empty_nested_html_table_does_not_invalidate_its_parent():
    report = inspect("<table><tr><td>before<table></table>after</td></tr></table>")
    before, nested, after = report.blocks[0].table.cells[0].blocks
    assert before.text == "before" and after.text == "after"
    assert isinstance(nested, Table) and nested.cells == ()


@pytest.mark.parametrize(
    "before,malformed",
    [
        (True, "<table><tr><td>bad"),
        (True, "<table><tr><td>bad</th></tr></table>"),
        (False, "<table><tr><td>bad</th></tr></table>"),
        (
            False,
            "<table><tr><td><table><tr><td>bad</th></tr></table></td></tr></table>",
        ),
    ],
    ids=["incomplete-tail", "malformed-tail", "malformed-prefix", "malformed-nested"],
)
def test_malformed_html_does_not_discard_completed_sibling_tables(before, malformed):
    good = "<table><tr><td>good</td></tr></table>"
    text = good + malformed if before else malformed + good
    report = inspect(text)
    assert report.to_markdown() == text
    tables = [block.table for block in report.blocks if block.table]
    assert len(tables) == 1
    assert tables[0].cells[0].blocks[0].text == "good"


@pytest.mark.parametrize(
    "body",
    [
        "<tr>" + "<td rowspan='2'>x</td>" * 400 + "</tr>",
        "<tr>" + "<td rowspan='100'>x</td>" * 100 + "</tr>" + "<tr></tr>" * 99,
    ],
    ids=["placement", "row-pruning"],
)
def test_html_span_work_cannot_bypass_the_facts_budget(body):
    with pytest.raises(DocumentLimitError, match="facts"):
        inspect("<table>" + body + "</table>", limits=DocumentLimits(facts=2000))


def test_html_code_samples_do_not_contribute_tables():
    report = inspect("<pre><code><table><tr><td>example</td></tr></table></code></pre>")
    assert not any(block.table for block in report.blocks)


def test_html_table_preserves_inline_code_text():
    report = inspect("<table><tr><td><code>field_name</code></td></tr></table>")
    assert report.blocks[0].table.cells[0].blocks[0].text == "field_name"


def test_html_optional_end_tags_and_cell_paragraphs():
    report = inspect(
        "<table><tr><th>A<th>B<tr><td><p>first</p><p>second</p><td>C</table>"
    )
    cells = report.blocks[0].table.cells
    assert [(c.row, c.column) for c in cells] == [(1, 1), (1, 2), (2, 1), (2, 2)]
    assert cells[2].blocks[0].text == "first\nsecond"


@pytest.mark.parametrize(
    "encoding,bom",
    [
        ("utf-8-sig", b""),
        ("utf-16-le", codecs.BOM_UTF16_LE),
        ("utf-16-be", codecs.BOM_UTF16_BE),
        ("utf-32-le", codecs.BOM_UTF32_LE),
        ("utf-32-be", codecs.BOM_UTF32_BE),
    ],
)
def test_markdown_encoding(encoding, bom):
    report = inspect_document(
        SourceSnapshot(Path("input.md"), bom + "中文\r\n".encode(encoding))
    )
    assert report.text == "中文\n"


def test_markdown_invalid_encoding_and_limits():
    with pytest.raises(DocumentParseError, match="decode"):
        inspect_document(SourceSnapshot(Path("input.md"), b"\xff\xff"))
    with pytest.raises(DocumentLimitError):
        inspect("中文", limits=DocumentLimits(text_bytes=3))
    with pytest.raises(DocumentLimitError):
        inspect("| A | B |\n| --- | --- |\n| x | y |", limits=DocumentLimits(facts=3))
    with pytest.raises(DocumentLimitError):
        inspect("text", limits=DocumentLimits(source_bytes=2))


def test_markdown_selection_exclusion_dedupe_and_ambiguity(tmp_path):
    work = tmp_path / "work"
    mirror = tmp_path / "mirror"
    ignored = work / ".agents"
    ignored.mkdir(parents=True)
    mirror.mkdir()
    (ignored / "SKILL.md").write_text("not an output")
    (work / "one.md").write_text("output")
    (mirror / "two.md").write_text("output")
    selected = select_document([work, mirror], format="md", excluded_roots=[ignored])
    assert selected.selected is not None and len(selected.candidates) == 2
    (mirror / "two.md").write_text("different")
    assert (
        select_document([work, mirror], format="md", excluded_roots=[ignored]).selected
        is None
    )


def test_markdown_scan_root_can_be_excluded_before_traversal(tmp_path):
    (tmp_path / "output.md").write_text("excluded output")
    selected = select_document(
        [tmp_path], format="md", excluded_roots=[tmp_path], max_entries=1
    )
    assert selected.selected is None and selected.candidates == ()
