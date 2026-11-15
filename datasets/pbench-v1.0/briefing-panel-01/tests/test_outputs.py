"""Task-owned requirements over shared immutable PPTX facts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from psycheval.harbor.documents import (
    DocumentParseError,
    inspect_document,
    select_document,
)
from psycheval.harbor.evidence import EvidenceWriter


def paragraphs(slide):
    result = []
    for shape in slide.shapes:
        result.extend(p.text for p in shape.paragraphs)
        if shape.table:
            rows = {}
            for cell in shape.table.cells:
                rows.setdefault(cell.row, []).extend(
                    block.text for block in cell.blocks if hasattr(block, "text")
                )
            result.extend(" | ".join(row) for row in rows.values())
    return result


def content_ok(report):
    if len(report.slides) != 2:
        return False
    first = "\n".join(paragraphs(report.slides[0]))
    second = paragraphs(report.slides[1])
    all_text = first + "\n" + "\n".join(second)
    metrics = [
        (r"处理时间|处理时长|耗时", r"(?<!\d)18(?!\d).*?(?<!\d)11(?!\d)", r"分钟"),
        (r"异常率", r"0[.．]90*(?!\d).*?2[.．]40*(?!\d)", r"[%％]"),
        (r"人工复核|人工.*复核量|复核量", r"(?<!\d)26(?!\d).*?(?<!\d)17(?!\d)", r"单"),
    ]
    matches = [
        {
            index
            for index, line in enumerate(second)
            if all(re.search(pattern, line) for pattern in patterns)
        }
        for patterns in metrics
    ]
    independent = any(
        a != b and a != c and b != c
        for a in matches[0]
        for b in matches[1]
        for c in matches[2]
    )
    metric_rows = {
        index
        for index, line in enumerate(second)
        if re.search(r"\d\s*(?:[%％]|分钟|单|元|小时)", line)
        or any(
            re.search(patterns[0], line) and re.search(r"\d", line)
            for patterns in metrics
        )
    }
    # Repeating a source metric in a risk explanation is not an additional KPI.
    precision = metric_rows <= set().union(*matches)
    return bool(
        independent
        and precision
        and re.search(r"试点", first)
        and re.search(r"夜班", all_text)
        and re.search(r"峰值", all_text)
        and re.search(r"两条|2\s*条", all_text)
        and re.search(r"五个工作日|5\s*个?工作日", all_text)
        and "待补充" not in all_text
    )


def wide_canvas_ok(report):
    tolerance = 9144  # 0.01 inch in EMU, matching the public production tolerance.
    return bool(
        len(report.slides) == 2
        and report.slide_width_emu is not None
        and report.slide_height_emu is not None
        and abs(report.slide_width_emu - 12192000) <= tolerance
        and abs(report.slide_height_emu - 6858000) <= tolerance
    )


def panel_ok(report):
    if (
        len(report.slides) != 2
        or not report.slide_width_emu
        or not report.slide_height_emu
    ):
        return False
    width, height = report.slide_width_emu, report.slide_height_emu
    for shape in report.slides[0].shapes:
        if not shape.bounds or shape.fill_error:
            continue
        left, top, right, bottom = shape.bounds
        text = "\n".join(
            paragraph.text
            for contained in report.slides[0].shapes
            if contained.bounds
            and contained.bounds[0] >= left
            and contained.bounds[1] >= top
            and contained.bounds[2] <= right
            and contained.bounds[3] <= bottom
            for paragraph in contained.paragraphs
        )
        geometry = (
            left >= width * 0.5
            and top >= 0
            and right <= width
            and bottom <= height
            and right - left >= width * 0.28
            and bottom - top >= height * 0.5
        )
        dark = (
            shape.fill_type == "solidFill"
            and bool(shape.fill_colors)
            and all(
                all(
                    abs(actual - target) <= 2
                    for actual, target in zip(rgb, (24, 50, 79), strict=True)
                )
                for rgb in shape.fill_colors
            )
        )
        conditions = "实施前提" in text and all(
            re.search(term, text)
            for term in (
                r"异常|响应",
                r"负责|责任|联系人",
                r"回退|回滚",
                r"夜班",
                r"峰值",
            )
        )
        if geometry and dark and conditions:
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    context = json.loads(args.context.read_text(encoding="utf-8"))
    paths = context["paths"]
    if not paths.get("inputs"):
        raise RuntimeError("This Native Host task requires retained initial inputs")
    checks = {
        name: False for name in ("decision_content", "wide_canvas", "decision_panel")
    }
    reason = "No unambiguous final presentation"
    with EvidenceWriter(paths["verifier_logs"]) as writer:
        original = writer.capture(
            "source_notes", Path(paths["inputs"]) / "review-notes.md"
        )
        source_text = original.content.decode("utf-8")
        lines = source_text.splitlines()
        writer.add_text(
            "source_excerpt",
            "Source: initial input review-notes.md, lines 1-"
            + str(len(lines))
            + "\n\n"
            + source_text,
            source_id="source_notes",
        )
        selected = select_document([Path(paths["workdir"]) / "output"], format="pptx")
        if selected.selected is None or len(selected.candidates) != 1:
            reason = f"Expected one final PPTX, found {len(selected.candidates)}: {selected.reason}"
            writer.add_text(
                "presentation", "No assessable final presentation: " + reason
            )
        else:
            snapshot = writer.capture("presentation_pptx", selected.selected)
            try:
                report = inspect_document(snapshot)
            except DocumentParseError as error:
                reason = str(error)
                writer.add_text(
                    "presentation",
                    "No assessable final presentation: " + reason,
                    source_id="presentation_pptx",
                )
            else:
                reason = "Inspected immutable final PPTX"
                checks["decision_content"] = content_ok(report)
                checks["wide_canvas"] = wide_canvas_ok(report)
                checks["decision_panel"] = content_ok(report) and panel_ok(report)
                writer.add_text(
                    "presentation", report.to_markdown(), source_id="presentation_pptx"
                )
                writer.add_text(
                    "static_facts",
                    json.dumps(
                        {
                            "slide_width_emu": report.slide_width_emu,
                            "slide_height_emu": report.slide_height_emu,
                            "slides": [
                                {
                                    "number": slide.number,
                                    "shapes": [
                                        {
                                            "index": shape.index,
                                            "bounds": shape.bounds,
                                            "fill_type": shape.fill_type,
                                            "fill_colors": shape.fill_colors,
                                            "fill_error": shape.fill_error,
                                        }
                                        for shape in slide.shapes
                                    ],
                                }
                                for slide in report.slides
                            ],
                            "limits": "Bounds and candidate colors are static facts, not rendered visible area or pixel distribution.",
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    source_id="presentation_pptx",
                )
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {"id": name, "passed": passed, "evidence": reason}
                    for name, passed in checks.items()
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
