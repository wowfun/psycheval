import argparse
import json
import re
import unicodedata
from dataclasses import asdict
from pathlib import Path

from harbor.models.trajectories.trajectory import Trajectory

from psycheval.harbor.documents import (
    DocumentParseError,
    inspect_document,
    select_document,
)
from psycheval.harbor.documents.models import Paragraph
from psycheval.harbor.evidence import EvidenceWriter, SourceSnapshot
from psycheval.harbor.verifier import final_answer_text


def compact(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def has(text, *terms):
    text = compact(text)
    return all(
        any(value in text for value in term)
        if isinstance(term, tuple)
        else term in text
        for term in terms
    )


def amount(text, expression):
    return (
        re.search(
            r"(?<![\d一二三四五六七八九十])(?:"
            + expression
            + r")(?![\d一二三四五六七八九十])",
            compact(text),
        )
        is not None
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    if not paths["inputs"] or not paths["preparation_state"]:
        raise RuntimeError(
            "This Task requires Native Host input snapshots and preparation state"
        )
    inputs = Path(paths["inputs"])
    reference = json.loads(
        (Path(paths["preparation_state"]) / "reference.json").read_text(
            encoding="utf-8"
        )
    )
    source_path = inputs / "release-approval.docx"
    change_path = inputs / "change-request.md"
    selection = select_document([Path(paths["workdir"]) / "output"], format="docx")
    checks = {"policy_revision": False, "numbering_structure": False}
    reasons = {key: selection.reason for key in checks}
    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        trajectory_path = Path(paths["agent_logs"]) / "trajectory.json"
        if trajectory_path.is_file():
            trajectory = Trajectory.model_validate_json(
                SourceSnapshot.read(
                    trajectory_path, max_bytes=128 * 1024 * 1024
                ).content
            )
            evidence.add_text("final_answer", final_answer_text(trajectory))
        else:
            evidence.unavailable(
                "final_answer", "No current-step retained ATIF trajectory"
            )
        source = evidence.capture("source_docx", source_path)
        source_report = inspect_document(source)
        source_text = source_report.to_markdown()
        evidence.add_text(
            "source_excerpt",
            "Source: initial release-approval.docx; body paragraph references follow.\n\n"
            + source_text,
            source_id="source_docx",
        )
        changes = evidence.capture("change_request", change_path)
        change_text = changes.content.decode("utf-8")
        if reference["effective_date"] not in change_text:
            raise ValueError("Retained change request and preparation date disagree")
        evidence.add_text(
            "change_excerpt",
            "Source: initial change-request.md; line references follow.\n\n"
            + "\n".join(
                f"L{index}: {line}"
                for index, line in enumerate(change_text.splitlines(), 1)
            ),
            source_id="change_request",
        )
        if selection.selected is None:
            evidence.add_text(
                "policy_text",
                "No unambiguous final DOCX was submitted. " + selection.reason,
            )
        else:
            result = evidence.capture("policy_docx", selection.selected)
            try:
                report = inspect_document(result)
            except DocumentParseError as error:
                reason = f"Unreadable final DOCX: {error}"
                evidence.add_text("policy_text", reason, source_id="policy_docx")
                reasons = dict.fromkeys(checks, reason)
            else:
                paragraphs = [
                    block for block in report.blocks if isinstance(block, Paragraph)
                ]
                text = report.to_markdown()
                evidence.add_text("policy_text", text, source_id="policy_docx")
                labels = [
                    "申请提交",
                    "数据复核",
                    "发布执行",
                    "口径检查",
                    "权限检查",
                    "紧急修复",
                    "延期发布",
                ]
                items = {
                    label: [p for p in paragraphs if p.text.strip().startswith(label)]
                    for label in labels
                }
                unique = all(len(values) == 1 for values in items.values())
                if unique:
                    item = {label: values[0] for label, values in items.items()}
                    submit = item["申请提交"].text
                    review = item["数据复核"].text
                    release = item["发布执行"].text
                    revision_ok = (
                        len(selection.candidates) == 1
                        and has(
                            submit,
                            "工作日",
                            ("变更清单", "变更列表", "变更明细"),
                            ("影响范围", "影响面"),
                            ("数据分类", "数据类别", "数据分级"),
                            ("回滚负责人", "回滚责任人"),
                        )
                        and amount(submit, r"(?:3|三)个?工作日")
                        and has(
                            review,
                            ("数据负责人", "数据责任人"),
                            "口径",
                            "敏感数据",
                            ("安全负责人", "安全责任人"),
                            ("批准", "审批", "同意"),
                            ("发布前", "上线前", "部署前"),
                        )
                        and has(
                            release,
                            "分钟",
                            ("错误率", "出错率"),
                            ("回滚负责人", "回滚责任人"),
                            "回滚",
                            ("团队群", "工作群"),
                            ("版本号", "版本编号"),
                        )
                        and amount(release, r"(?:30|三十)分钟")
                        and amount(release, r"(?:2(?:\.0+)?%|百分之二)")
                        and has(
                            item["紧急修复"].text,
                            ("值班负责人", "值班责任人"),
                            ("批准", "审批", "同意"),
                            "记录",
                        )
                        and amount(
                            item["紧急修复"].text, r"(?:24|二十四)小时|(?:1|一)天"
                        )
                        and has(
                            item["口径检查"].text,
                            ("指标定义", "指标口径"),
                            ("样本期间", "样本周期", "样本时间范围"),
                            ("去重规则", "去重逻辑"),
                            ("复核人", "复核人员"),
                        )
                        and has(
                            item["权限检查"].text,
                            ("访问授权", "访问权限"),
                            ("数据负责人", "数据责任人"),
                            "确认",
                        )
                        and has(
                            item["延期发布"].text,
                            "审批",
                            ("暂停", "推迟", "延期"),
                            ("发布负责人", "发布责任人"),
                            ("团队群", "工作群"),
                            "计划",
                        )
                        and any(
                            value in compact(text)
                            for value in (
                                reference["effective_date"],
                                "{}年{}月{}日".format(
                                    *map(int, reference["effective_date"].split("-"))
                                ),
                            )
                        )
                        and any(
                            p.text.strip().startswith("修订说明")
                            and len(p.text.strip()) > 25
                            for p in paragraphs
                        )
                    )
                    checks["policy_revision"] = revision_ok
                    reasons["policy_revision"] = (
                        "Compared each labelled obligation with initial materials and the retained preparation date"
                    )

                    def numbered(
                        label, level, format, template, start, restart, style=None
                    ):
                        paragraph = item[label]
                        fact = paragraph.numbering
                        return bool(
                            fact
                            and not fact.error
                            and fact.num_id
                            and fact.num_id > 0
                            and fact.level == level
                            and fact.num_format == format
                            and fact.level_text == template
                            and fact.start == start
                            and fact.restart == restart
                            and (style is None or paragraph.style == style)
                        )

                    main = all(
                        numbered(label, 0, "decimal", "%1.", 1, None, "Procedure Step")
                        for label in labels[:3]
                    )
                    sub = all(
                        numbered(label, 1, "lowerLetter", "%2)", 1, 1)
                        for label in labels[3:5]
                    )
                    exceptions = all(
                        numbered(
                            label, 0, "upperLetter", "%1)", 3, None, "Exception Step"
                        )
                        for label in labels[5:]
                    )
                    plain = [
                        p
                        for p in paragraphs
                        if p.text.strip().startswith(("说明", "修订说明"))
                    ]
                    plain_ok = len(plain) >= 2 and all(
                        p.numbering is None
                        or (p.numbering.num_id == 0 and not p.numbering.error)
                        for p in plain
                    )
                    named_ids = {id(p) for p in item.values()}
                    extra_numbered = any(
                        id(p) not in named_ids
                        and p.numbering is not None
                        and p.numbering.num_id != 0
                        for p in paragraphs
                    )
                    checks["numbering_structure"] = bool(
                        revision_ok
                        and main
                        and sub
                        and exceptions
                        and plain_ok
                        and not extra_numbered
                    )
                    reasons["numbering_structure"] = (
                        "Checked resolved numbering definitions and styles; no displayed sequence or Word rendering was inferred"
                    )
                    evidence.add_text(
                        "numbering_facts",
                        "Observed paragraph numbering definitions (not displayed labels):\n\n"
                        + json.dumps(
                            [
                                {
                                    "paragraph": p.index,
                                    "text": p.text,
                                    "style": p.style,
                                    "numbering": asdict(p.numbering)
                                    if p.numbering
                                    else None,
                                }
                                for p in paragraphs
                            ],
                            ensure_ascii=False,
                            indent=2,
                        ),
                        source_id="policy_docx",
                    )
                else:
                    reasons = dict.fromkeys(
                        checks,
                        "Missing, duplicated or unrecognizable required labelled policy paragraphs",
                    )
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {"id": key, "passed": passed, "evidence": reasons[key]}
                    for key, passed in checks.items()
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
