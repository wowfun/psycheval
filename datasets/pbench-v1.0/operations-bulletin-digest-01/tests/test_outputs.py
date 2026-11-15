"""Source-bound selection and retained, locatable facts for an operations digest."""

import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path

from harbor.models.trajectories import Trajectory

from psycheval.harbor.documents import inspect_document
from psycheval.harbor.evidence import EvidenceWriter, SourceSnapshot
from psycheval.harbor.verifier import final_answer_text

# Task-owned event identity: ordinary cross-channel records carry no answer labels.
GROUPS = {
    "北门车辆通行": ({"B-4731", "B-7392", "B-5904"}, {"B-7392"}, ("北门",)),
    "环线班车": ({"B-2846", "B-8163", "B-4627"}, {"B-8163", "B-4627"}, ("班车",)),
    "B座夜间供水": ({"B-3915"}, {"B-3915"}, ("B座", "B 座")),
    "C座电梯": ({"B-1078", "B-6450"}, {"B-6450"}, ("电梯",)),
    "北停车场充电": ({"B-3216", "B-9602"}, {"B-9602"}, ("充电",)),
    "晚餐转场": ({"B-1548", "B-9027"}, {"B-9027"}, ("食堂",)),
    "访客接待": ({"B-5874", "B-2639"}, {"B-2639"}, ("访客",)),
}
EXCLUDED = {"B-8301", "B-6708", "B-4016", "B-7195", "B-2084", "B-4481"}
CITATION = re.compile(r"〔\s*(B-\d{4})\s*〕")
ITEM = re.compile(r"(?m)^ {0,3}\d+[.)、]\s+\S")


def source_records(report):
    lines = report.text.splitlines()
    headings = [
        (index, re.fullmatch(r"## (B-\d{4})", line))
        for index, line in enumerate(lines)
        if re.fullmatch(r"## (B-\d{4})", line)
    ]
    records = {}
    for position, (start, heading) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        text = "\n".join(lines[start:end]).strip()
        fields = {}
        for label, key in (
            ("发布方", "publisher"),
            ("发布时间", "published_at"),
            ("标题", "title"),
            ("正文", "body"),
        ):
            value = re.search(rf"(?m)^{label}：(.+)$", text)
            if value is None:
                raise ValueError(f"Malformed retained source: {heading[1]} {label}")
            fields[key] = value[1]
        identity = heading[1]
        if identity in records:
            raise ValueError(f"Duplicate retained source: {identity}")
        records[identity] = {
            **fields,
            "start_line": start + 1,
            "end_line": end,
            "text": text,
        }
    expected_ids = EXCLUDED.union(*(sources for sources, _, _ in GROUPS.values()))
    if set(records) != expected_ids:
        raise ValueError("Retained archive source set differs from the authored task")
    return records


def selection_reference(context, records):
    cutoff = datetime.fromisoformat(context["cutoff"])
    if (
        cutoff.tzinfo is None
        or context["timezone"] != "Asia/Shanghai"
        or cutoff.date().isoformat() != context["reference_date"]
    ):
        raise ValueError("Invalid retained reference context")
    for _, current, _ in GROUPS.values():
        for identity in current:
            published = datetime.fromisoformat(records[identity]["published_at"])
            if published.date() != cutoff.date() or published > cutoff:
                raise ValueError("Current source is outside the retained reference")
    rows = [
        "Task selection reference, derived from the retained archive and public scope. "
        "This is not evidence that the Agent delivered these items.",
        "Include one distinct reminder per following matter; at least one current-source ID must support it:",
    ]
    for label, (_, current, _) in GROUPS.items():
        rows.append(
            f"- {label}: "
            + "; ".join(
                f"{identity} — {records[identity]['title']} ({records[identity]['published_at']})"
                for identity in sorted(current)
            )
        )
    rows.extend(
        [
            "Exclude these records as independent reminders under the public scope:",
            *(
                f"- {identity}: {records[identity]['title']} ({records[identity]['published_at']})"
                for identity in sorted(EXCLUDED)
            ),
            "Old versions and duplicate relays may support context, but must not replace current facts. "
            "Do not award factual or practical quality merely for matching source IDs or this list.",
        ]
    )
    return "\n".join(rows)


def assess(answer, context):
    starts = list(ITEM.finditer(answer))
    if not starts:
        return False, "No independent numbered operational reminders"
    introduction = answer[: starts[0].start()]
    reference = date.fromisoformat(context["reference_date"])
    dates = (
        reference.isoformat(),
        reference.strftime("%Y/%m/%d"),
        f"{reference.year}年{reference.month}月{reference.day}日",
        f"{reference.year}年{reference.month:02}月{reference.day:02}日",
    )
    date_text = re.sub(r"\s+", "", introduction)
    if not any(value in date_text for value in dates) or not re.search(
        r"15\s*(?:[:：]\s*00|[时点](?:\s*(?:00|整))?)", introduction
    ):
        return False, "Introduction lacks the retained reference date or 15:00 cutoff"
    if not any(
        value in introduction
        for value in ("上海", "Asia/Shanghai", "+08:00", "UTC+8", "北京时间")
    ):
        return False, "Introduction lacks the Shanghai time context"
    groups_seen, item_citations = set(), []
    problems = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(answer)
        text = answer[start.start() : end]
        cited = set(CITATION.findall(text))
        item_citations.extend(CITATION.findall(text))
        matches = [
            label for label, (sources, _, _) in GROUPS.items() if cited & sources
        ]
        if len(matches) != 1:
            problems.append(
                f"Item {index + 1}: unrelated, absent or merged source groups"
            )
            continue
        label = matches[0]
        sources, current, terms = GROUPS[label]
        if cited - sources or not cited & current:
            problems.append(f"Item {index + 1}: unsupported or obsolete source binding")
        if not any(term in CITATION.sub("", text) for term in terms):
            problems.append(f"Item {index + 1}: no corresponding subject beyond IDs")
        if label in groups_seen:
            problems.append(f"Item {index + 1}: duplicated matter {label}")
        groups_seen.add(label)
    missing = sorted(set(GROUPS) - groups_seen)
    if missing:
        problems.append(f"Missing distinct matters: {missing}")
    if len(CITATION.findall(answer)) != len(item_citations):
        problems.append("Unbound citations outside numbered reminders")
    return not problems, "; ".join(
        problems
    ) or "Every in-scope matter has a distinct current-source-bound reminder"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    if not paths.get("inputs") or not paths.get("preparation_state"):
        raise RuntimeError(
            "This task requires ordinary Native Host retained inputs and preparation state"
        )
    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        inputs = Path(paths["inputs"]) / "materials"
        raw_context = evidence.capture("context_json", inputs / "briefing-context.json")
        context = json.loads(raw_context.content)
        raw_sources = evidence.capture("bulletin_sources", inputs / "bulletins.md")
        raw_state = evidence.capture(
            "preparation_record", Path(paths["preparation_state"]) / "reference.json"
        )
        state = json.loads(raw_state.content)
        if state["context"] != context or state["sha256"] != {
            "briefing-context.json": raw_context.sha256,
            "bulletins.md": raw_sources.sha256,
        }:
            raise ValueError("Retained preparation record and initial inputs disagree")
        report = inspect_document(raw_sources, format="md")
        records = source_records(report)
        evidence.add_text(
            "reference_context",
            json.dumps(context, ensure_ascii=False, indent=2),
            source_id="context_json",
        )
        evidence.add_text(
            "source_slices",
            "\n\n".join(
                f"### Source slice {identity}\n"
                f"Source: bulletin_sources, lines {record['start_line']}–{record['end_line']} (1-based).\n\n"
                + record["text"]
                for identity, record in records.items()
            ),
            source_id="bulletin_sources",
        )
        evidence.add_text("selection_reference", selection_reference(context, records))
        try:
            trajectory = SourceSnapshot.read(
                Path(paths["agent_logs"]) / "trajectory.json",
                max_bytes=128 * 1024 * 1024,
            )
        except FileNotFoundError:
            answer = ""
        else:
            answer = final_answer_text(
                Trajectory.model_validate_json(trajectory.content)
            )
        evidence.add_text("final_answer", answer)
        passed, reason = assess(answer, context)
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "id": "source_bound_selection",
                        "passed": passed,
                        "evidence": reason,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
