"""One deck-contract prerequisite; semantic fidelity is judged against source."""

import argparse
import colorsys
import json
import re
import unicodedata
from pathlib import Path

from psycheval.harbor.documents import (
    DocumentParseError,
    inspect_document,
    select_document,
)
from psycheval.harbor.documents.models import Paragraph
from psycheval.harbor.evidence import EvidenceWriter


def source_groups(text):
    groups = []
    for line in text.splitlines():
        if line.startswith("## "):
            groups.append((line[3:], []))
        elif line.startswith("### ") and groups:
            groups[-1][1].append(line[4:])
    if len(groups) != 4 or any(len(names) != 2 for _, names in groups):
        raise ValueError("Initial source must contain four authored pairs of concepts")
    return groups


def paragraphs(shape):
    return (
        tuple(
            block
            for cell in shape.table.cells
            for block in cell.blocks
            if isinstance(block, Paragraph)
        )
        if shape.table
        else shape.paragraphs
    )


def navy(color):
    hue, saturation, value = colorsys.rgb_to_hsv(*(channel / 255 for channel in color))
    return 180 <= hue * 360 <= 265 and saturation >= 0.15 and value <= 0.5


def amber(color):
    hue, saturation, value = colorsys.rgb_to_hsv(*(channel / 255 for channel in color))
    return 25 <= hue * 360 <= 65 and saturation >= 0.35 and value >= 0.6


def light(color):
    return (
        sum(
            channel * weight for channel, weight in zip(color, (0.2126, 0.7152, 0.0722))
        )
        >= 130
    )


def ordinal_badge(shape, slide, names, concept_count):
    text = re.sub(
        r"\s+",
        "",
        unicodedata.normalize("NFKC", "".join(p.text for p in paragraphs(shape))),
    )
    if (
        not re.fullmatch(r"\d{1,2}", text)
        or not 1 <= int(text) <= concept_count
        or shape.table
        or shape.geometry_error
        or shape.bounds is None
        or shape.fill_error
        or not shape.fill_colors
        or not all(light(color) for color in shape.fill_colors)
        or any(
            run.error or not run.colors
            for paragraph in paragraphs(shape)
            for run in paragraph.runs
            if run.text.strip()
        )
    ):
        return False
    left, top, right, bottom = shape.bounds
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        return False
    for heading in slide.shapes:
        label = re.sub(r"\s+", "", "".join(p.text for p in paragraphs(heading)))
        if label not in names or heading.geometry_error or heading.bounds is None:
            continue
        hleft, htop, _, hbottom = heading.bounds
        heading_height = hbottom - htop
        overlap = min(bottom, hbottom) - max(top, htop)
        if (
            0 < max(width, height) <= heading_height * 1.5
            and 0 <= hleft - right <= heading_height
            and overlap >= min(height, heading_height) * 0.5
        ):
            return True
    return False


def evaluate_report(report, groups):
    issues, badges = [], []
    width, height = report.slide_width_emu, report.slide_height_emu
    dimensions_ok = bool(
        width and height and abs(width / height / (16 / 9) - 1) <= 0.01
    )
    if not dimensions_ok:
        issues.append(
            f"16:9 dimensions unavailable or outside 1% ratio tolerance: {width} x {height}"
        )
    if len(report.slides) != 4:
        issues.append(f"Expected four teaching slides, got {len(report.slides)}")
    for slide, (stage, names) in zip(report.slides, groups):
        page = f"slide {slide.number} ({stage})"
        text = "\n".join(
            paragraph.text for shape in slide.shapes for paragraph in paragraphs(shape)
        )
        compact = re.sub(r"\s+", "", text)
        if not all(name in compact for name in names):
            issues.append(
                f"{page}: source concept labels missing from their assigned page: {names}"
            )
        if (
            slide.background_error
            or not slide.background_colors
            or not all(
                navy(color)
                for color in (*slide.background_colors, *slide.title_background_colors)
            )
        ):
            issues.append(
                f"{page}: deep-blue canvas/title background unresolved or outside palette"
            )
        if (
            slide.title_error
            or not slide.title_colors
            or not all(amber(color) for color in slide.title_colors)
        ):
            issues.append(f"{page}: amber page title unresolved or outside palette")
        for shape in slide.shapes:
            if dimensions_ok:
                box = shape.bounds
                tolerance = max(width, height) * 0.001
                if (
                    box is None
                    or shape.geometry_error
                    or not (
                        -tolerance <= box[0] <= box[2] <= width + tolerance
                        and -tolerance <= box[1] <= box[3] <= height + tolerance
                    )
                ):
                    issues.append(
                        f"{page}, shape {shape.index}: geometry unavailable or outside canvas"
                    )
            if ordinal_badge(shape, slide, names, sum(len(pair) for _, pair in groups)):
                badges.append((slide.number, shape.index))
                continue
            for paragraph in paragraphs(shape):
                for run in paragraph.runs:
                    if run.text.strip() and (
                        run.error
                        or not run.colors
                        or not all(light(color) for color in run.colors)
                    ):
                        issues.append(
                            f"{page}, shape {shape.index}, paragraph {paragraph.index}: light text color unresolved or outside palette"
                        )
    reason = (
        "; ".join(issues)
        or "Four paired slides, 16:9 canvas, declared night palette and bounded OOXML geometry matched; semantic fidelity remains a separate Judge assessment"
    )
    if badges:
        reason += f"; decorative ordinal badges excluded from body color only: {badges}"
    return not issues, reason


def static_facts(report):
    return json.dumps(
        {
            "limits": "OOXML facts only: no rendering, pixel distribution, visible-area, clipping, occlusion or visual-readability verdict",
            "slide_width_emu": report.slide_width_emu,
            "slide_height_emu": report.slide_height_emu,
            "slides": [
                {
                    "number": slide.number,
                    "title_shape_id": slide.title_shape_id,
                    "title_colors": slide.title_colors,
                    "title_error": slide.title_error,
                    "background_colors": slide.background_colors,
                    "title_background_colors": slide.title_background_colors,
                    "background_error": slide.background_error,
                    "shapes": [
                        {
                            "index": shape.index,
                            "shape_id": shape.shape_id,
                            "bounds_left_top_right_bottom_emu": shape.bounds,
                            "geometry_error": shape.geometry_error,
                            "fill_type": shape.fill_type,
                            "fill_colors": shape.fill_colors,
                            "fill_error": shape.fill_error,
                            "paragraphs": [
                                {
                                    "index": paragraph.index,
                                    "runs": [
                                        {
                                            "font_size": run.font_size,
                                            "colors": run.colors,
                                            "error": run.error,
                                        }
                                        for run in paragraph.runs
                                    ],
                                }
                                for paragraph in paragraphs(shape)
                            ],
                        }
                        for shape in slide.shapes
                    ],
                }
                for slide in report.slides
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    if not paths.get("inputs"):
        raise RuntimeError(
            "This Task requires ordinary Native Host retained initial inputs"
        )
    passed, reason = False, "No single final PPTX in output/"
    with EvidenceWriter(paths["verifier_logs"]) as writer:
        source = writer.capture(
            "training_brief", Path(paths["inputs"]) / "night-shift-brief.md"
        )
        source_report = inspect_document(source, format="md")
        groups = source_groups(source_report.text)
        excerpt = (
            "Source: initial night-shift-brief.md, complete numbered lines.\n\n"
            + "\n".join(
                f"L{index}: {line}"
                for index, line in enumerate(source_report.text.splitlines(), 1)
            )
        )
        writer.add_text("source_excerpt", excerpt, source_id="training_brief")
        selection = select_document([Path(paths["workdir"]) / "output"], format="pptx")
        if selection.selected is None or len(selection.candidates) != 1:
            reason += ": " + selection.reason
            writer.add_text("presentation_text", reason)
            writer.add_text("presentation_facts", reason)
        else:
            snapshot = writer.capture("presentation_pptx", selection.selected)
            try:
                report = inspect_document(snapshot)
            except DocumentParseError as error:
                reason = f"No assessable PPTX: {error}"
                writer.add_text(
                    "presentation_text", reason, source_id="presentation_pptx"
                )
                writer.add_text(
                    "presentation_facts", reason, source_id="presentation_pptx"
                )
            else:
                passed, reason = evaluate_report(report, groups)
                writer.add_text(
                    "presentation_text",
                    report.to_markdown(),
                    source_id="presentation_pptx",
                )
                writer.add_text(
                    "presentation_facts",
                    static_facts(report),
                    source_id="presentation_pptx",
                )
    args.output.write_text(
        json.dumps(
            {"checks": [{"id": "deck_contract", "passed": passed, "evidence": reason}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
