"""Task-specific facts; static inspection does not imply rendered behavior."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path

from psycheval.harbor.documents import DocumentParseError, inspect_document
from psycheval.harbor.evidence import EvidenceWriter


def compact(value):
    return re.sub(r"\s+", "", value)


def descendants(report, identity):
    nodes = {node.id: node for node in report.nodes}
    pending, found = [identity], []
    while pending:
        node = nodes[pending.pop()]
        found.append(node)
        pending.extend(part for part in node.content if isinstance(part, int))
    return found


def rules(items):
    for rule in items:
        yield rule
        yield from rules(rule.children)


def declaration(rule, name, value):
    return any(
        item.name.lower() == name and compact(item.value).lower() == value
        for item in rule.declarations
    )


def inspect_page(report):
    articles = [node for node in report.nodes if node.tag == "article"]
    approved = {
        "项目日历": ("/updates/project-calendar", "ICS"),
        "文件协作": ("/updates/file-collaboration", "50GB"),
        "访客评审": ("/updates/guest-review", "7天"),
    }
    matched, extracted = set(), []
    content_ok = len(articles) == len(approved)
    for article in articles:
        members = {node.id for node in descendants(report, article.id)}
        headings = [
            heading for heading in report.headings if heading.node_id in members
        ]
        links = [link for link in report.links if link.node_id in members]
        text = report.text_content(article.id)
        extracted.append(
            f"## Article node {article.id}\n{text}\nLinks: "
            + json.dumps([asdict(link) for link in links], ensure_ascii=False)
        )
        title = headings[0].text.strip() if len(headings) == 1 else None
        if title not in approved or title in matched:
            content_ok = False
            continue
        matched.add(title)
        href, detail = approved[title]
        summaries = [
            node for node in descendants(report, article.id) if node.tag == "p"
        ]
        summary = " ".join(report.text_content(node.id) for node in summaries)
        content_ok &= (
            len(links) == 1
            and links[0].href == href
            and bool(links[0].text.strip())
            and detail in compact(summary)
            and len(compact(summary)) >= 20
            and not any(
                token in compact(summary) for token in ("在线白板", "¥59", "100GB")
            )
            and not any(
                other_detail in compact(summary)
                for other_title, (_, other_detail) in approved.items()
                if other_title != title
            )
        )
    body = compact(report.text)
    content_ok &= matched == set(approved) and "在线白板" not in body
    expected = [
        ["方案", "每席位月费", "文件空间"],
        ["基础版", "39", "10GB"],
        ["协作版", "69", "50GB"],
        ["专业版", "99", "200GB"],
    ]
    table_ok = False
    if len(report.tables) == 1:
        rows = {}
        for cell in report.tables[0].cells:
            rows.setdefault(cell.row_id, []).append(compact(cell.text))
        actual = list(rows.values())
        for row in actual[1:]:
            if len(row) == 3:
                match = re.fullmatch(r"(?:¥|￥|人民币)?(\d+)(?:\.0+)?(?:元)?", row[1])
                if match:
                    row[1] = match[1]
        table_ok = (
            bool(actual)
            and actual[0] == expected[0]
            and sorted(actual[1:]) == sorted(expected[1:])
        )
    all_rules = list(rules(report.styles))
    main_grid = any(
        rule.kind == "rule"
        and rule.prelude.strip() == ".release-grid"
        and declaration(rule, "display", "grid")
        for rule in report.styles
    )
    mobile_grid = any(
        rule.kind == "media"
        and re.sub(r"\s+", "", rule.prelude).lower() == "(max-width:600px)"
        and any(
            child.kind == "rule"
            and child.prelude.strip() == ".release-grid"
            and declaration(child, "grid-template-columns", "1fr")
            for child in rule.children
        )
        for rule in report.styles
    )
    notes = [
        node
        for node in report.nodes
        if "internal-note" in dict(node.attributes).get("class", "").split()
    ]
    note_ok = (
        len(notes) == 1
        and "hidden" in dict(notes[0].attributes)
        and any(
            rule.kind == "inline"
            and rule.source_node_id == notes[0].id
            and declaration(rule, "display", "none")
            for rule in all_rules
        )
    )
    title_ok = any(
        heading.level == 1 and heading.text.strip() == "澄帆产品更新"
        for heading in report.headings
    )
    images = [node for node in report.nodes if node.tag == "img"]
    image_ref_ok = (
        len(images) == 1
        and dict(images[0].attributes).get("src") == "assets/header.png"
        and len(dict(images[0].attributes).get("alt", "").strip()) >= 2
    )
    grid_nodes = [
        node
        for node in report.nodes
        if "release-grid" in dict(node.attributes).get("class", "").split()
    ]
    grid_ok = len(grid_nodes) == 1 and all(
        article.id in {node.id for node in descendants(report, grid_nodes[0].id)}
        for article in articles
    )
    no_scripts = not any(
        node.tag.rsplit("}", 1)[-1] == "script"
        or any(
            name.lower().startswith("on")
            or value.strip().lower().startswith("javascript:")
            for name, value in node.attributes
        )
        for node in report.nodes
    )
    no_external_resources = (
        not any(
            node.tag in {"link", "iframe", "object", "embed"}
            or (
                node.tag == "img"
                and re.match(r"(?:https?:)?//", dict(node.attributes).get("src", ""))
            )
            for node in report.nodes
        )
        and not any(rule.kind == "import" for rule in all_rules)
        and not any(
            "url(" in item.value.lower()
            for rule in all_rules
            for item in rule.declarations
        )
    )
    syntax_ok = not any(rule.errors for rule in all_rules)
    static_ok = (
        main_grid
        and mobile_grid
        and note_ok
        and title_ok
        and image_ref_ok
        and grid_ok
        and no_scripts
        and no_external_resources
        and syntax_ok
        and report.encoding == "utf-8"
    )
    return bool(content_ok), bool(table_ok), bool(static_ok), "\n\n".join(extracted)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    workdir = Path(paths["workdir"])
    if paths["inputs"] is None:
        raise RuntimeError("This Task requires Native Host initial-input evidence")
    results = dict.fromkeys(("release_content", "plan_table", "static_delivery"), False)
    reasons = dict.fromkeys(results, "Missing output/index.html")
    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        source = evidence.capture(
            "launch_brief", Path(paths["inputs"]) / "launch-brief.md"
        )
        excerpt = (
            "Source: initial launch-brief.md, complete lines below\n\n"
            + "\n".join(
                f"L{index}: {line}"
                for index, line in enumerate(
                    source.content.decode("utf-8").splitlines(), 1
                )
            )
        )
        evidence.add_text("source_excerpt", excerpt, source_id="launch_brief")
        page = workdir / "output/index.html"
        if not page.is_file():
            evidence.unavailable("page_text", "Missing output/index.html")
        else:
            snapshot = evidence.capture("page_html", page)
            try:
                report = inspect_document(snapshot)
            except DocumentParseError as error:
                evidence.unavailable("page_text", str(error), status="error")
                reasons = dict.fromkeys(results, f"Uninspectable HTML: {error}")
            else:
                content_ok, table_ok, static_ok, text = inspect_page(report)
                results.update(
                    release_content=content_ok,
                    plan_table=table_ok,
                    static_delivery=static_ok,
                )
                reasons.update(
                    release_content="Per-article title, summary fact and detail link binding",
                    plan_table="Plan rows compared with the published price and capacity table",
                    static_delivery="Static HTML structure, encoding, declarations and local image reference",
                )
                evidence.add_text(
                    "page_text",
                    text + "\n\n## Complete body text\n" + report.text,
                    source_id="page_html",
                )
        image = workdir / "output/assets/header.png"
        image_ok = False
        if image.is_file():
            snapshot = evidence.capture("banner_png", image)
            try:
                report = inspect_document(snapshot)
            except DocumentParseError as error:
                evidence.unavailable("image_facts", str(error), status="error")
            else:
                image_ok = (
                    report.width == 1200
                    and report.height == 320
                    and report.nonopaque_fraction == 0
                    and any(value > 0 for value in report.variances[:3])
                )
                evidence.add_text(
                    "image_facts", report.to_markdown(), source_id="banner_png"
                )
        else:
            evidence.unavailable("image_facts", "Missing output/assets/header.png")
        results["static_delivery"] &= image_ok
        reasons["static_delivery"] += (
            f"; PNG dimensions/opacity/nonuniform pixels passed={image_ok}"
        )
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {"id": key, "passed": bool(value), "evidence": reasons[key]}
                    for key, value in results.items()
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
