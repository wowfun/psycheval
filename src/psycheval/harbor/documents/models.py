"""Immutable parser-independent facts and faithful body text."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from ..evidence import SourceSnapshot
from ._limits import DocumentLimits, bounded_markdown

RGB = tuple[float, float, float]
Colors = tuple[RGB, ...]
CellValue = str | int | float | bool | date | datetime | time | timedelta | None


@dataclass(frozen=True)
class PptxOptions:
    fallback_font_size: float = 18.0
    background_coverage: float = 0.95

    def __post_init__(self):
        if self.fallback_font_size <= 0 or not 0 < self.background_coverage <= 1:
            raise ValueError("Invalid PPTX inspection options")


@dataclass(frozen=True)
class TextRun:
    text: str
    font_size: float | None = None
    colors: Colors = ()
    error: str | None = None


@dataclass(frozen=True)
class Paragraph:
    index: int
    text: str
    runs: tuple[TextRun, ...] = ()
    style: str | None = None


@dataclass(frozen=True)
class TableCell:
    row: int
    column: int
    row_span: int
    column_span: int
    blocks: tuple[Paragraph | Table, ...]


@dataclass(frozen=True)
class Table:
    index: int
    cells: tuple[TableCell, ...]


@dataclass(frozen=True)
class PptxShape:
    index: int
    shape_id: int
    bounds: tuple[float, float, float, float] | None
    paragraphs: tuple[Paragraph, ...]
    table: Table | None = None
    geometry_error: str | None = None

    @property
    def has_text(self):
        return bool(self.paragraphs) or bool(
            self.table
            and any(
                block.text.strip()
                for cell in self.table.cells
                for block in cell.blocks
                if isinstance(block, Paragraph)
            )
        )


@dataclass(frozen=True)
class PptxSlide:
    number: int
    shapes: tuple[PptxShape, ...]
    title_shape_id: int | None
    title_colors: Colors
    title_error: str | None
    background_colors: Colors
    title_background_colors: Colors
    background_error: str | None

    @property
    def text_shape_count(self):
        return sum(shape.has_text for shape in self.shapes)


@dataclass(frozen=True)
class PptxReport:
    source: SourceSnapshot
    slides: tuple[PptxSlide, ...]
    text_limit: int = DocumentLimits().text_bytes

    def to_markdown(self):
        parts = []
        for slide in self.slides:
            parts.append(f"## Slide {slide.number}")
            for shape in slide.shapes:
                if not shape.has_text:
                    continue
                parts.append(f"### Shape {shape.index}")
                if shape.table:
                    for cell in shape.table.cells:
                        for paragraph in cell.blocks:
                            if (
                                isinstance(paragraph, Paragraph)
                                and paragraph.text.strip()
                            ):
                                parts.append(
                                    f"Row {cell.row}, cell {cell.column}, paragraph {paragraph.index}:\n{paragraph.text}"
                                )
                else:
                    parts.extend(
                        f"Paragraph {p.index}:\n{p.text}" for p in shape.paragraphs
                    )
        return bounded_markdown(parts, self.text_limit)


@dataclass(frozen=True)
class PdfPage:
    number: int
    text: str
    width: float
    height: float


@dataclass(frozen=True)
class PdfReport:
    source: SourceSnapshot
    pages: tuple[PdfPage, ...]
    text_limit: int = DocumentLimits().text_bytes

    def to_markdown(self):
        return bounded_markdown(
            (f"## Page {p.number}\n\n{p.text}" for p in self.pages), self.text_limit
        )


@dataclass(frozen=True)
class XlsxCell:
    address: str
    value: CellValue
    formula: str | None = None
    cached_value: CellValue = None


@dataclass(frozen=True)
class XlsxSheet:
    name: str
    visibility: str
    cells: tuple[XlsxCell, ...]
    merged_ranges: tuple[str, ...]


@dataclass(frozen=True)
class XlsxReport:
    source: SourceSnapshot
    sheets: tuple[XlsxSheet, ...]
    text_limit: int = DocumentLimits().text_bytes

    def to_markdown(self):
        parts = []
        for sheet in self.sheets:
            parts.append(f"## Sheet: {sheet.name}\n\nVisibility: {sheet.visibility}")
            for cell in sheet.cells:
                if cell.formula is not None:
                    parts.append(
                        f"{cell.address} formula:\n{cell.formula}\nCached value: {cell.cached_value!r}"
                    )
                else:
                    parts.append(f"{cell.address}:\n{cell.value}")
            if sheet.merged_ranges:
                parts.append("Merged ranges: " + ", ".join(sheet.merged_ranges))
        return bounded_markdown(parts, self.text_limit)


@dataclass(frozen=True)
class DocxReport:
    source: SourceSnapshot
    blocks: tuple[Paragraph | Table, ...]
    text_limit: int = DocumentLimits().text_bytes

    def to_markdown(self):
        def render(blocks):
            parts = []
            for block in blocks:
                if isinstance(block, Paragraph):
                    parts.append(
                        f"Paragraph {block.index} ({block.style or 'Normal'}):\n{block.text}"
                    )
                else:
                    parts.append(f"### Table {block.index}")
                    for cell in block.cells:
                        parts.append(
                            f"Row {cell.row}, cell {cell.column} ({cell.row_span} x {cell.column_span}):"
                        )
                        parts.extend(render(cell.blocks))
            return parts

        return bounded_markdown(render(self.blocks), self.text_limit)
