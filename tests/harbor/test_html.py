"""Static HTML facts through the public document interface."""

from pathlib import Path

import pytest

from psycheval.harbor.documents import (
    DocumentLimitError,
    DocumentLimits,
    MissingDocumentDependency,
    inspect_document,
    select_document,
)
from psycheval.harbor.evidence import SourceSnapshot


def inspect_html(text, **kwargs):
    pytest.importorskip("html5lib")
    pytest.importorskip("tinycss2")
    return inspect_document(
        SourceSnapshot(
            Path("page.html"), text if isinstance(text, bytes) else text.encode("utf-8")
        ),
        **kwargs,
    )


@pytest.mark.parametrize("markup", ["<!--{}-->", "<script>{}</script>"])
def test_html_source_and_extracted_text_have_independent_budgets(markup):
    source = "<!doctype html>" + markup.format("x" * 8192) + "<p>Body</p>"
    report = inspect_html(
        source, limits=DocumentLimits(source_bytes=len(source), text_bytes=8)
    )
    assert report.text == "Body" and report.decoded_source == source
    with pytest.raises(DocumentLimitError, match="source byte"):
        inspect_html(source, limits=DocumentLimits(source_bytes=len(source) - 1))
    with pytest.raises(DocumentLimitError):
        inspect_html(
            "<!doctype html><p>too much text</p>", limits=DocumentLimits(text_bytes=8)
        )


def test_html_repeated_node_queries_index_the_document_only_once():
    from dataclasses import replace

    class CountedNodes(tuple):
        visits = 0

        def __iter__(self):
            self.visits += len(self)
            return super().__iter__()

    report = inspect_html(
        "<!doctype html>" + "".join(f"<a href='/{n}'>Item {n}</a>" for n in range(100))
    )
    nodes = CountedNodes(report.nodes)
    report = replace(report, nodes=nodes)
    for link in report.links:
        assert report.text_content(link.node_id) == link.text
    assert "Item 99" in report.text
    assert nodes.visits == len(nodes)


def test_html_preserves_item_node_binding_and_static_hidden_declarations(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("HTML inspection must not use the network")

    monkeypatch.setattr(socket, "socket", forbidden)
    report = inspect_html("""<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="https://invalid.test/style.css">
<main><section id="news" class="column"><h4>中文 <em>heading</em></h4>
<article><a href="https://invalid.test/first">Title <span>one</span></a><p>Summary</p></article>
<p hidden style="display:none !important; color:var(--ink)">Declared hidden</p>
<script>SECRET_SCRIPT</script><template>TEMPLATE_TEXT</template>
<svg><script>SVG_SCRIPT</script></svg></section></main>""")
    assert report.encoding == "utf-8"
    assert report.headings[0].level == 4 and report.headings[0].text == "中文 heading"
    link = report.links[0]
    assert link.href == "https://invalid.test/first" and link.text == "Title one"
    nodes = {node.id: node for node in report.nodes}
    article = nodes[nodes[link.node_id].parent_id]
    assert article.tag == "article"
    assert "Summary" in report.text_content(article.id)
    hidden = next(node for node in report.nodes if "hidden" in dict(node.attributes))
    assert "Declared hidden" in report.text
    rule = next(rule for rule in report.styles if rule.source_node_id == hidden.id)
    assert [(d.name, d.value, d.important) for d in rule.declarations] == [
        ("display", "none", True),
        ("color", "var(--ink)", False),
    ]
    assert all(
        word not in report.text
        for word in ("SECRET_SCRIPT", "TEMPLATE_TEXT", "SVG_SCRIPT")
    )
    assert any(
        dict(node.attributes).get("href") == "https://invalid.test/style.css"
        for node in report.nodes
    )
    assert "https://invalid.test/first" in report.to_markdown()


def test_html_css_preserves_nested_conditions_and_reports_syntax_errors():
    report = inspect_html("""<!doctype html><meta charset=utf-8><style>
@media (max-width: 600px) { .grid {display:grid; grid-template-columns:1fr !important}
  @supports (display: grid) { .child {color: red} } }
@container panel (width > 10px) { .item {color:blue} }
@import url(https://invalid.test/style.css);
</style><p style="color:red; broken; width:1px">Body</p>""")
    media, container, external, inline = report.styles
    assert media.kind == "media" and "600px" in media.prelude
    assert media.children[0].prelude == ".grid"
    assert media.children[0].declarations[-1].important
    assert media.children[1].kind == "supports"
    assert container.kind == "container" and external.kind == "import"
    assert inline.errors and len(inline.declarations) == 2


def test_html_bad_css_value_is_diagnostic_not_a_fabricated_declaration():
    report = inspect_html('<style>p { color: "bad\n; width: 1px; }</style>')
    rule = report.styles[0]
    assert rule.errors
    assert [(value.name, value.value) for value in rule.declarations] == [
        ("width", "1px")
    ]


def test_html_bare_stylesheet_declaration_is_diagnostic_not_inline_css():
    report = inspect_html('<style>color:red;</style><p style="color:blue">Body</p>')
    stylesheet, inline = report.styles
    assert stylesheet.kind == "stylesheet" and stylesheet.errors
    assert not stylesheet.declarations
    assert [(item.name, item.value) for item in inline.declarations] == [
        ("color", "blue")
    ]


def test_html_cells_reference_parser_inserted_rows():
    report = inspect_html("<table><td>A<td>B</table>")
    first, second = report.tables[0].cells
    nodes = {node.id: node for node in report.nodes}
    assert first.row_id == second.row_id
    assert nodes[first.row_id].tag == "tr"
    assert nodes[first.row_id].parent_id != first.row_id


def test_html_nested_tables_keep_cell_identity_and_authored_spans():
    report = inspect_html("""<!doctype html><table id=outer><tr><th colspan=2>Header
<tr><td rowspan=0>A<td><table id=inner><tr><td>B</table></table>""")
    outer, inner = report.tables
    assert len(outer.cells) == 3 and len(inner.cells) == 1
    assert outer.cells[0].column_span == 2
    assert outer.cells[1].row_span == 0
    assert inner.cells[0].text == "B"
    assert inner.cells[0].node_id not in {cell.node_id for cell in outer.cells}


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16", "windows-1252"])
def test_html_encoding_and_recovered_document(encoding):
    report = inspect_html("<p>caf\u00e9".encode(encoding))
    assert report.text == "caf\u00e9"
    assert report.diagnostics  # Missing doctype is retained, not a parser failure.


@pytest.mark.parametrize(
    "limits",
    [
        DocumentLimits(facts=2),
        DocumentLimits(text_bytes=2),
        DocumentLimits(source_bytes=2),
    ],
)
def test_html_budgets_are_errors(limits):
    with pytest.raises(DocumentLimitError):
        inspect_html("<p>long body</p>", limits=limits)


def test_html_selection_aliases_and_missing_optional_dependency(tmp_path, monkeypatch):
    import psycheval.harbor.documents as documents

    path = tmp_path / "page.htm"
    path.write_text("<p>Body</p>")
    assert select_document([tmp_path], format="html").selected == path
    real_import = documents.importlib.import_module

    def blocked(name):
        if name == "tinycss2":
            raise ModuleNotFoundError("blocked", name=name)
        return real_import(name)

    monkeypatch.setattr(documents.importlib, "import_module", blocked)
    with pytest.raises(MissingDocumentDependency, match=r"psycheval\[html\]"):
        inspect_document(path)
