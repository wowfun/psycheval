"""OOXML contract checks and source-bound, text-only Judge plumbing."""

import asyncio
import io
import json
import runpy
import shutil
import zipfile
from html import escape
from pathlib import Path

import pytest

from psycheval.harbor.documents import inspect_document
from psycheval.harbor.evidence import SourceSnapshot
from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
)
from psycheval.harbor.tasks import load_harbor_task
from psycheval.harbor.verifier import JudgeSettings, load_judge_config, run_verifier
from tests.fixtures.judge_server import judge_server

TASK = (
    Path(__file__).resolve().parents[2]
    / "datasets/pbench-v1.0/observatory-onboarding-01"
)
SOURCE = TASK / "environment/data/night-shift-brief.md"
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
GROUPS = GRADER["source_groups"](SOURCE.read_text(encoding="utf-8"))


def deck(width=13.333):
    """Generic structural fixture, deliberately not a model answer."""
    backend = pytest.importorskip("pptx")
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt

    result = backend.Presentation()
    result.slide_width, result.slide_height = Inches(width), Inches(7.5)
    for stage, names in GROUPS:
        slide = result.slides.add_slide(result.slide_layouts[6])
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = RGBColor(17, 29, 48)
        title = slide.shapes.add_textbox(
            Inches(0.6), Inches(0.3), Inches(12), Inches(0.7)
        )
        title.text = stage
        title.text_frame.paragraphs[0].runs[0].font.size = Pt(32)
        title.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(245, 189, 75)
        for column, name in enumerate(names):
            x = 0.6 + column * 6.3
            panel = slide.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(x), Inches(1.5), Inches(5.8), Inches(5.4)
            )
            panel.fill.solid()
            panel.fill.fore_color.rgb = RGBColor(25, 44, 64)
            panel.line.fill.background()
            text = slide.shapes.add_textbox(
                Inches(x + 0.2), Inches(1.7), Inches(5.4), Inches(4.8)
            )
            text.text = name
            p = text.text_frame.paragraphs[0]
            p.runs[0].font.size = Pt(25)
            p.runs[0].font.color.rgb = RGBColor(245, 189, 75)
            p = text.text_frame.add_paragraph()
            p.text = "本结构样件不包含培训答案；语义内容须由Judge另行核对。"
            p.runs[0].font.size = Pt(20)
            p.runs[0].font.color.rgb = RGBColor(230, 237, 244)
    return result


def snapshot(presentation):
    buffer = io.BytesIO()
    presentation.save(buffer)
    return SourceSnapshot(Path("deck.pptx"), buffer.getvalue())


def numbered_deck(mode="normal"):
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches, Pt

    presentation = deck()
    for page, (slide, (_, names)) in enumerate(zip(presentation.slides, GROUPS)):
        bodies = [slide.shapes[2], slide.shapes[4]]
        for column, (name, body) in enumerate(zip(names, bodies)):
            first = body.text_frame.paragraphs[0]
            body.text_frame._txBody.remove(first._p)
            body.top, body.height = Inches(2.5), Inches(3.5)
            x = 0.8 + column * 6.3
            number = page * 2 + column + 1 if mode == "global_ordinals" else column + 1
            badge = slide.shapes.add_shape(
                MSO_SHAPE.OVAL, Inches(x), Inches(1.7), Inches(0.4), Inches(0.4)
            )
            badge.fill.solid()
            badge.fill.fore_color.rgb = RGBColor(245, 166, 35)
            badge.line.fill.background()
            badge.text = str(number)
            run = badge.text_frame.paragraphs[0].runs[0]
            run.font.size, run.font.color.rgb = Pt(14), RGBColor(10, 27, 51)
            heading = slide.shapes.add_textbox(
                Inches(x + 0.52), Inches(1.65), Inches(4.5), Inches(0.5)
            )
            heading.text = name
            run = heading.text_frame.paragraphs[0].runs[0]
            run.font.size, run.font.color.rgb = Pt(22), RGBColor(230, 237, 244)
            if mode == "no_fill":
                badge.fill.background()
            elif mode == "dark_fill":
                badge.fill.fore_color.rgb = RGBColor(17, 29, 48)
            elif mode == "with_unit":
                badge.text_frame.paragraphs[0].runs[0].text = "2秒"
            elif mode == "numeric_threshold":
                badge.text_frame.paragraphs[0].runs[0].text = "12"
            elif mode == "unknown_fill":
                from pptx.oxml.xmlchemy import OxmlElement

                properties = badge._element.spPr
                for child in list(properties):
                    if child.tag.rsplit("}", 1)[-1] in {
                        "solidFill",
                        "noFill",
                        "gradFill",
                    }:
                        properties.remove(child)
                properties.append(OxmlElement("a:blipFill"))
            elif mode == "unrelated_number":
                badge.top = Inches(4)
            elif mode == "oversized_number":
                badge.width, badge.height = Inches(3), Inches(3)
            elif mode == "dark_body":
                body.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(
                    10, 27, 51
                )
            elif mode == "dark_body_on_light_fill":
                body.fill.solid()
                body.fill.fore_color.rgb = RGBColor(245, 166, 35)
                body.text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(
                    10, 27, 51
                )
    return presentation


@pytest.mark.parametrize("mode", ["normal", "global_ordinals"])
def test_dark_ordinal_badges_are_decoration_outside_the_light_body_requirement(mode):
    report = inspect_document(snapshot(numbered_deck(mode)))
    assert GRADER["evaluate_report"](report, GROUPS)[0]


@pytest.mark.parametrize(
    "mode",
    [
        "no_fill",
        "dark_fill",
        "with_unit",
        "numeric_threshold",
        "unknown_fill",
        "unrelated_number",
        "oversized_number",
        "dark_body",
        "dark_body_on_light_fill",
    ],
)
def test_ordinal_decoration_does_not_exempt_actual_dark_body_or_unsupported_numbers(
    mode,
):
    report = inspect_document(snapshot(numbered_deck(mode)))
    assert not GRADER["evaluate_report"](report, GROUPS)[0]


@pytest.mark.parametrize("width", [13.333, 13 + 1 / 3, 16])
def test_widescreen_rounding_and_scaling_are_not_mistaken_for_requirement_failure(
    width,
):
    presentation = deck(width)
    if width == 16:
        from pptx.util import Inches

        presentation.slide_height = Inches(9)
    report = inspect_document(snapshot(presentation))
    assert GRADER["evaluate_report"](report, GROUPS)[0]


@pytest.mark.parametrize(
    "mutation",
    [
        "five_pages",
        "blank_page",
        "missing_concept",
        "swapped_pair",
        "white_canvas",
        "white_title",
        "dark_text",
        "off_canvas",
        "wrong_ratio",
    ],
)
def test_contract_rejects_wrong_groups_palette_canvas_or_redundant_pages(mutation):
    from pptx.dml.color import RGBColor
    from pptx.util import Inches

    presentation = deck()
    slide = presentation.slides[0]
    if mutation == "five_pages":
        presentation.slides.add_slide(presentation.slide_layouts[6])
    elif mutation == "blank_page":
        for shape in list(slide.shapes):
            shape._element.getparent().remove(shape._element)
    elif mutation == "missing_concept":
        slide.shapes[2].text_frame.paragraphs[0].runs[0].text = "其他主题"
    elif mutation == "swapped_pair":
        slide.shapes[2].text_frame.paragraphs[0].runs[0].text = GROUPS[1][1][0]
    elif mutation == "white_canvas":
        slide.background.fill.fore_color.rgb = RGBColor(255, 255, 255)
    elif mutation == "white_title":
        slide.shapes[0].text_frame.paragraphs[0].runs[0].font.color.rgb = RGBColor(
            255, 255, 255
        )
    elif mutation == "dark_text":
        slide.shapes[2].text_frame.paragraphs[1].runs[0].font.color.rgb = RGBColor(
            0, 0, 0
        )
    elif mutation == "off_canvas":
        slide.shapes[2].left = presentation.slide_width + Inches(1)
    else:
        presentation.slide_width = Inches(10)
    assert not GRADER["evaluate_report"](
        inspect_document(snapshot(presentation)), GROUPS
    )[0]


def test_missing_size_stays_missing_instead_of_inventing_default_widescreen():
    from lxml import etree

    original, changed = snapshot(deck()), io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(original.content)) as archive,
        zipfile.ZipFile(changed, "w") as target,
    ):
        for item in archive.infolist():
            raw = archive.read(item.filename)
            if item.filename == "ppt/presentation.xml":
                node = etree.fromstring(raw)
                size = node.find(
                    "{http://schemas.openxmlformats.org/presentationml/2006/main}sldSz"
                )
                node.remove(size)
                raw = etree.tostring(node)
            target.writestr(item, raw)
    report = inspect_document(SourceSnapshot(Path("missing.pptx"), changed.getvalue()))
    assert report.slide_width_emu is None and report.slide_height_emu is None
    assert not GRADER["evaluate_report"](report, GROUPS)[0]


def test_late_nontext_panel_fill_is_in_facts_without_claiming_visible_area():
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.util import Inches

    presentation = deck()
    panel = presentation.slides[0].shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(9), Inches(6.8), Inches(2), Inches(0.3)
    )
    panel.fill.solid()
    panel.fill.fore_color.rgb = RGBColor(10, 35, 58)
    facts = json.loads(GRADER["static_facts"](inspect_document(snapshot(presentation))))
    last = facts["slides"][0]["shapes"][-1]
    assert last["fill_type"] == "solidFill" and last["fill_colors"] == [[10, 35, 58]]
    assert "no rendering" in facts["limits"] and "visible-area" in facts["limits"]


@pytest.mark.parametrize("judge_pass,expected", [(False, 0.3), (True, 1)])
def test_source_snapshot_and_same_deck_text_and_facts_reach_actual_judge_request(
    tmp_path, judge_pass, expected
):
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert (judge.rule_weight, judge.llm_weight) == (0.3, 0.7)
    assert judge.rubrics[0].artifact_refs == (
        "source_excerpt",
        "presentation_text",
        "presentation_facts",
    )
    roots = {
        name: tmp_path / name
        for name in ("workdir", "inputs", "agent_logs", "verifier_logs", "artifacts")
    }
    for root in roots.values():
        root.mkdir()
    shutil.copyfile(SOURCE, roots["inputs"] / SOURCE.name)
    (roots["workdir"] / SOURCE.name).write_text(
        "Agent modified this working copy", encoding="utf-8"
    )
    output = roots["workdir"] / "output"
    output.mkdir()
    path = output / "newcomer.pptx"
    deck().save(path)
    runtime = EffectiveRuntimeConfig(
        paths=RuntimePaths(
            tests=str(TASK / "tests"),
            **{name: str(path) for name, path in roots.items()},
        ),
        verifier=VerifierInvocation(
            (TASK / "instruction.md").read_text(encoding="utf-8")
        ),
    )
    with judge_server() as server:
        server["behavior"] = {"faithful_onboarding": {"passed": judge_pass}}
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
        assert len(server["requests"]) == 1
        prompt = server["requests"][0]["messages"][-1]["content"]
    assert result["test_pass_rate"] == 1
    assert result["reward"] == pytest.approx(expected)
    assert result["metadata"]["score_merge"]["applied"]
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    records = {row["id"]: row for row in manifest["artifacts"]}
    for name, source_id in (
        ("source_excerpt", "training_brief"),
        ("presentation_text", "presentation_pptx"),
        ("presentation_facts", "presentation_pptx"),
    ):
        assert records[name]["source_artifact_id"] == source_id
        text = (roots["verifier_logs"] / records[name]["text_path"]).read_text(
            encoding="utf-8"
        )
        assert escape(text, quote=False) in prompt
    assert "L1: # 霁岚观测站" in prompt
    assert "Agent modified this working copy" not in prompt
    assert (
        roots["verifier_logs"] / records["presentation_pptx"]["verifier_raw_path"]
    ).read_bytes() == path.read_bytes()
