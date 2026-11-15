"""Minimum outline facts plus source-grounded, non-rendering Judge evidence."""

import argparse
import json
import re
import unicodedata
from pathlib import Path

from harbor.models.trajectories import Trajectory

from psycheval.harbor.documents import (
    DocumentLimits,
    DocumentParseError,
    inspect_document,
)
from psycheval.harbor.evidence import EvidenceWriter, SourceSnapshot
from psycheval.harbor.verifier import final_answer_text

LIMITS = DocumentLimits(source_bytes=1024 * 1024, text_bytes=1024 * 1024, facts=20000)


def label_key(label):
    return re.sub(r"[\s`*_#]+", "", unicodedata.normalize("NFKC", label)).casefold()


def mermaid_label(value):
    value = value.split(":::", 1)[0].strip()
    shape = re.fullmatch(
        r"[\w-]+\s*(?:\(\((.*?)\)\)|\((.*?)\)|\[(.*?)\]|\{(.*?)\})", value
    )
    if shape:
        value = next(part for part in shape.groups() if part is not None)
    return value.strip().strip('"')


def mermaid_entries(lines):
    nodes = []
    for number, line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        if not nodes and stripped.casefold() == "mindmap":
            nodes.append(None)
            continue
        if not nodes:
            return None
        if re.match(
            r"(?:classDef|class|style|click)\s", stripped
        ) or stripped.startswith(":::"):
            continue
        nodes.append(
            (
                len(line.expandtabs(4)) - len(line.lstrip().expandtabs(4)),
                mermaid_label(stripped),
                number,
            )
        )
    return nodes[1:] if nodes else None


def indented_nodes(entries):
    nodes, stack = [], []
    for indentation, label, line in entries:
        if not label_key(label):
            continue
        while stack and indentation <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1] if stack else None
        nodes.append({"label": label, "parent": parent, "line": line})
        stack.append((indentation, len(nodes) - 1))
    return nodes


def outline_details(nodes):
    roots = [index for index, node in enumerate(nodes) if node["parent"] is None]
    branches = [
        index
        for index, node in enumerate(nodes)
        if roots and node["parent"] == roots[0]
    ]
    distinct = len({label_key(nodes[index]["label"]) for index in branches})
    children = {node["parent"] for node in nodes if node["parent"] is not None}
    expanded = all(branch in children for branch in branches)
    passed = (
        len(roots) == 1
        and len(branches) >= 3
        and distinct == len(branches)
        and expanded
    )
    return passed, {
        "roots": len(roots),
        "main_branches": len(branches),
        "distinct_main_labels": distinct,
        "all_main_branches_expanded": expanded,
        "nodes": nodes,
        "scope": "Static text hierarchy only; semantics and resource feasibility require Judge",
    }


def markdown_nodes(report):
    lines = report.text.splitlines()
    nodes, headings, lists = [], [], []
    for position, block in enumerate(report.blocks):
        if block.kind == "heading":
            tail = report.blocks[position + 1 :]
            if (
                nodes
                and tail
                and all(item.kind == "paragraph" for item in tail)
                and outline_details(nodes)[0]
            ):
                # A complete outline may be followed by a standalone prose
                # section. Keep it in Judge evidence, outside structural nodes.
                return nodes
            first = lines[block.start_line].strip()
            match = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", first)
            if match:
                level, label = len(match[1]), match[2]
            else:
                level = 1 if lines[block.start_line + 1].lstrip().startswith("=") else 2
                label = first
            while headings and level <= headings[-1][0]:
                headings.pop()
            parent = headings[-1][1] if headings else None
            nodes.append(
                {"label": label, "parent": parent, "line": block.start_line + 1}
            )
            headings.append((level, len(nodes) - 1))
            lists.clear()
        elif block.kind in {"bullet_list", "ordered_list"}:
            lists.clear()
            for index in range(block.start_line, block.end_line):
                match = re.match(r"^([ \t]*)(?:[-+*]|\d+[.)])\s+(\S.*)$", lines[index])
                if not match:
                    continue
                indentation = len(match[1].expandtabs(4))
                while lists and indentation <= lists[-1][0]:
                    lists.pop()
                parent = (
                    lists[-1][1] if lists else headings[-1][1] if headings else None
                )
                nodes.append({"label": match[2], "parent": parent, "line": index + 1})
                lists.append((indentation, len(nodes) - 1))
        elif block.kind == "paragraph" and not nodes:
            text = "\n".join(lines[block.start_line : block.end_line]).strip()
            title = re.fullmatch(r"(?:\*\*|__)(.+?)(?:\*\*|__)", text)
            if title and "\n" not in text:
                nodes.append(
                    {"label": title[1], "parent": None, "line": block.start_line + 1}
                )
                headings.append((0, 0))
    return nodes


def hierarchy(report):
    """Inspect indentation/heading relationships, not Mermaid renderability."""
    lines = report.text.splitlines()
    maps = []
    for block in report.blocks:
        if block.kind != "code":
            continue
        opening = re.fullmatch(
            r" {0,3}(`{3,}|~{3,})\s*mermaid\s*", lines[block.start_line]
        )
        if opening is None:
            continue
        body = list(
            enumerate(
                lines[block.start_line + 1 : block.end_line], block.start_line + 2
            )
        )
        if body and re.fullmatch(
            rf"\s*{re.escape(opening[1][0])}{{{len(opening[1])},}}\s*", body[-1][1]
        ):
            body.pop()
        entries = mermaid_entries(body)
        if entries is not None:
            maps.append(indented_nodes(entries))
    if len(maps) > 1:
        return False, {"reason": "Expected one mind map, found several Mermaid maps"}
    nodes = maps[0] if maps else markdown_nodes(report)
    if len(nodes) > 1000:
        return False, {"reason": "Outline exceeds the 1000-node inspection budget"}
    passed, details = outline_details(nodes)
    details["format"] = "mermaid-indentation" if maps else "markdown-hierarchy"
    return passed, details


def read_answer(paths):
    try:
        trajectory = SourceSnapshot.read(
            Path(paths["agent_logs"]) / "trajectory.json", max_bytes=128 * 1024 * 1024
        )
    except FileNotFoundError:
        return ""
    return final_answer_text(Trajectory.model_validate_json(trajectory.content))


def evaluate(paths):
    if not paths.get("inputs"):
        raise RuntimeError("This Task requires retained ordinary Native Host inputs")
    brief = SourceSnapshot.read(
        Path(paths["inputs"]) / "event-brief.md", max_bytes=256 * 1024
    )
    brief_report = inspect_document(brief, format="md", limits=LIMITS)
    answer = read_answer(paths)
    report, diagnostic = None, {"reason": "No final mind-map content"}
    passed = False
    if answer.strip():
        try:
            report = inspect_document(
                SourceSnapshot(Path("final-map.md"), answer.encode("utf-8")),
                format="md",
                limits=LIMITS,
            )
        except DocumentParseError as error:
            diagnostic = {"reason": str(error)}
        else:
            passed, diagnostic = hierarchy(report)
    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        evidence.capture("source_brief", brief)
        excerpt = (
            "Source: initial event-brief.md, complete lines below.\n\n"
            + "\n".join(
                f"L{number}: {line}"
                for number, line in enumerate(brief_report.text.splitlines(), 1)
            )
        )
        evidence.add_text("event_brief", excerpt, source_id="source_brief")
        if report is None:
            evidence.unavailable("final_map", diagnostic["reason"])
        else:
            evidence.add_text("final_map", report.to_markdown())
    return [
        {
            "id": "minimum_hierarchy",
            "passed": passed,
            "evidence": json.dumps(diagnostic, ensure_ascii=False),
        }
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    args.output.write_text(
        json.dumps({"checks": evaluate(paths)}, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
