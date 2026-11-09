"""Bounded Markdown facts, without rendering or interpreting task requirements."""

from __future__ import annotations

import codecs
from dataclasses import dataclass, field
from html.parser import HTMLParser

from ._limits import DocumentParseError, InspectionBudget
from .models import MarkdownBlock, MarkdownReport, Paragraph, Table, TableCell


@dataclass
class _HTMLCell:
    tag: str
    row: int
    column: int
    row_span: int
    column_span: int
    parts: list[str] = field(default_factory=list)
    blocks: list[Paragraph | Table] = field(default_factory=list)

    def flush_text(self):
        text = "".join(self.parts).strip()
        if text:
            self.blocks.append(Paragraph(len(self.blocks) + 1, text))
        self.parts.clear()


@dataclass
class _HTMLTable:
    index: int
    cells: list[TableCell] = field(default_factory=list)
    cell: _HTMLCell | None = None
    row: int = 0
    column: int = 0
    in_row: bool = False
    invalid: bool = False
    covered: list[tuple[int, int, int, int]] = field(default_factory=list)


class _HTMLTables(HTMLParser):
    def __init__(self, budget):
        super().__init__(convert_charrefs=True)
        self.budget = budget
        self.tables = []
        self.stack = []
        self.table_count = 0
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        self.budget.fact()
        if tag in {"script", "style"} or (tag in {"pre", "code"} and not self.stack):
            self.skip += 1
        if self.skip:
            return
        if tag == "table":
            if self.stack:
                parent = self.stack[-1]
                if parent.cell is None:
                    parent.invalid = True
                else:
                    parent.cell.flush_text()
            self.table_count += 1
            self.stack.append(_HTMLTable(self.table_count))
            return
        if not self.stack:
            return
        table = self.stack[-1]
        if tag == "tr":
            if table.in_row:
                self.handle_endtag("tr")
            table.row += 1
            self.budget.fact(len(table.covered))
            table.covered = [
                span for span in table.covered if span[0] + span[2] > table.row
            ]
            table.column = 1
            table.in_row = True
        elif tag in {"td", "th"}:
            if table.cell is not None:
                self.handle_endtag(table.cell.tag)
            if not table.in_row:
                table.invalid = True
                return
            while True:
                self.budget.fact(len(table.covered))
                if not any(
                    r <= table.row < r + rs and c <= table.column < c + cs
                    for r, c, rs, cs in table.covered
                ):
                    break
                table.column += 1
            attrs = dict(attrs)
            try:
                rs, cs = (int(attrs.get(key, "1")) for key in ("rowspan", "colspan"))
            except (ValueError, TypeError):
                table.invalid = True
                return
            if (
                not 1 <= rs <= self.budget.limits.facts
                or not 1 <= cs <= self.budget.limits.facts
            ):
                table.invalid = True
                return
            table.cell = _HTMLCell(tag, table.row, table.column, rs, cs)
        elif tag == "br" and table.cell is not None:
            table.cell.parts.append("\n")

    def handle_endtag(self, tag):
        self.budget.fact()
        if tag in {"script", "style", "pre", "code"}:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if not self.stack:
            return
        table = self.stack[-1]
        if table.cell is not None and tag in {"p", "div", "li"}:
            table.cell.parts.append("\n")
        if tag in {"td", "th"}:
            cell = table.cell
            if cell is None or cell.tag != tag:
                table.invalid = True
                return
            cell.flush_text()
            table.cells.append(
                TableCell(
                    cell.row,
                    cell.column,
                    cell.row_span,
                    cell.column_span,
                    tuple(cell.blocks) or (Paragraph(1, ""),),
                )
            )
            if cell.row_span > 1:
                table.covered.append(
                    (cell.row, cell.column, cell.row_span, cell.column_span)
                )
            table.column += cell.column_span
            table.cell = None
        elif tag == "tr":
            if table.cell is not None:
                self.handle_endtag(table.cell.tag)
            if not table.in_row:
                table.invalid = True
            table.in_row = False
        elif tag == "table":
            if table.in_row:
                self.handle_endtag("tr")
            self.stack.pop()
            if table.invalid:
                if self.stack:
                    self.stack[-1].invalid = True
                return
            result = Table(table.index, tuple(table.cells))
            if self.stack:
                parent = self.stack[-1]
                if parent.cell is not None:
                    parent.cell.blocks.append(result)
            else:
                self.tables.append(result)

    def handle_data(self, data):
        if self.stack and self.stack[-1].cell is not None and not self.skip:
            self.stack[-1].cell.parts.append(data)

    def finish(self):
        self.close()
        return tuple(self.tables)


def _inline_text(token):
    parts = []
    for child in token.children or ():
        if child.type in {"text", "code_inline", "image"}:
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"} or (
            child.type == "html_inline"
            and child.content.lower() in {"<br>", "<br/>", "<br />"}
        ):
            parts.append("\n")
    return "".join(parts)


def inspect(snapshot, limits):
    from . import MissingDocumentDependency

    try:
        from markdown_it import MarkdownIt
    except ModuleNotFoundError as error:
        raise MissingDocumentDependency(
            f"Missing dependency {error.name!r}; install or repair markdown-it-py before inspection"
        ) from error
    encoding = "utf-8-sig"
    for bom, codec in (
        (codecs.BOM_UTF32_LE, "utf-32"),
        (codecs.BOM_UTF32_BE, "utf-32"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
    ):
        if snapshot.content.startswith(bom):
            encoding = codec
            break
    try:
        text = (
            snapshot.content.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
        )
    except UnicodeError as error:
        raise DocumentParseError("Cannot decode Markdown") from error
    budget = InspectionBudget(limits)
    budget.text(text)
    tokens = MarkdownIt("commonmark", {"html": True}).enable("table").parse(text)
    blocks = []
    cells, row, column = [], 0, 0
    start = None
    for token in tokens:
        budget.fact()
        for child in token.children or ():
            budget.fact()
        if token.type == "table_open" and token.level == 0:
            start = token.map
            cells, row, column = [], 0, 0
        elif start is not None:
            if token.type == "tr_open":
                row += 1
                column = 0
            elif token.type in {"th_open", "td_open"}:
                column += 1
            elif token.type == "inline":
                cells.append(
                    TableCell(row, column, 1, 1, (Paragraph(1, _inline_text(token)),))
                )
            elif token.type == "table_close":
                blocks.append(
                    MarkdownBlock("table", *start, Table(len(blocks) + 1, tuple(cells)))
                )
                start = None
        elif token.level == 0 and token.map is not None:
            if token.type == "html_block":
                html = _HTMLTables(budget)
                html.feed(token.content)
                tables = html.finish()
                if tables:
                    blocks.extend(
                        MarkdownBlock("table", *token.map, table) for table in tables
                    )
                    continue
            kind = {"hr": "thematic_break", "fence": "code", "code_block": "code"}.get(
                token.type, token.type.removesuffix("_open")
            )
            blocks.append(MarkdownBlock(kind, *token.map))
    return MarkdownReport(snapshot, text, tuple(blocks), limits.text_bytes)
