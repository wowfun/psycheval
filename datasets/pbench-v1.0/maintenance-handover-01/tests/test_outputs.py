"""Verify distinct work-order actions against retained handover evidence."""

import argparse
import csv
import io
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from harbor.models.trajectories import Trajectory

from psycheval.harbor.documents import DocumentParseError, inspect_document
from psycheval.harbor.evidence import EvidenceWriter, SourceSnapshot
from psycheval.harbor.verifier import final_answer_text

TIMEZONE = ZoneInfo("Asia/Shanghai")
HEADERS = ["工单号", "待办动作", "截止时间", "来源记录id"]


def normalize(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value))).casefold()


def parse_deadline(value):
    text = unicodedata.normalize("NFKC", value).strip().strip("`")
    match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2})[ T](\d{2}):(\d{2})(?::00)?(?:\s*(?:北京时间|\+08:00|CST))?",
        text,
    )
    if match is None:
        return None
    day, hour, minute = match.groups()
    try:
        date = datetime.fromisoformat(day).replace(tzinfo=TIMEZONE)
        if (hour, minute) == ("24", "00"):
            return date + timedelta(days=1)
        return date.replace(hour=int(hour), minute=int(minute))
    except ValueError:
        return None


def parse_rows(answer):
    text = answer.strip()
    fenced = re.fullmatch(
        r"```(?:markdown|md)?\s*\n(.*?)\n```", text, flags=re.DOTALL | re.IGNORECASE
    )
    if fenced:
        text = fenced[1]
    report = inspect_document(
        SourceSnapshot(Path("answer.md"), text.encode("utf-8")), format="md"
    )
    tables = [block.table for block in report.blocks if block.table is not None]
    if len(tables) != 1:
        return None
    rows = defaultdict(dict)
    for cell in tables[0].cells:
        if (
            cell.row_span != 1
            or cell.column_span != 1
            or any(not hasattr(block, "text") for block in cell.blocks)
        ):
            return None
        rows[cell.row][cell.column] = "\n".join(
            block.text for block in cell.blocks
        ).strip()
    if not rows or any(set(row) != {1, 2, 3, 4} for row in rows.values()):
        return None
    ordered = [
        [row[column] for column in (1, 2, 3, 4)] for _, row in sorted(rows.items())
    ]
    if [normalize(value) for value in ordered.pop(0)] != HEADERS:
        return None
    return ordered


def matches_action(text, groups):
    text = normalize(text).replace("签认", "签署")
    return all(
        any(normalize(term) in text for term in alternatives) for alternatives in groups
    )


def evaluate_answer(answer, state):
    todos = state["todos"]
    try:
        rows = parse_rows(answer)
    except DocumentParseError as error:
        return False, f"Answer cannot be inspected: {error}"
    if rows is None or len(rows) != len(todos):
        return (
            False,
            f"Expected one supported row per independent action; observed rows={len(rows) if rows is not None else 'invalid table'}",
        )
    assignments = {}
    observations = []
    for row in rows:
        orders = re.findall(r"WX-\d{4}", unicodedata.normalize("NFKC", row[0]).upper())
        if len(orders) != 1:
            return False, "Every row must identify one work order"
        candidates = [
            todo
            for todo in todos
            if todo["order"] == orders[0] and matches_action(row[1], todo["groups"])
        ]
        if len(candidates) != 1 or candidates[0]["id"] in assignments:
            return False, f"Unsupported, merged or repeated action in row={row}"
        todo = candidates[0]
        sources = set(
            re.findall(r"JL-\d{4}", unicodedata.normalize("NFKC", row[3]).upper())
        )
        sources_ok = (
            bool(sources)
            and sources.issubset(todo["sources"])
            and todo["deadline_source"] in sources
        )
        actual_deadline = parse_deadline(row[2])
        deadline_ok = actual_deadline is not None and actual_deadline == parse_deadline(
            todo["deadline"]
        )
        assignments[todo["id"]] = sources_ok and deadline_ok
        observations.append(
            {
                "work_order": orders[0],
                "action": todo["id"],
                "sources": sorted(sources),
                "sources_ok": sources_ok,
                "deadline": row[2],
                "deadline_ok": deadline_ok,
            }
        )
    passed = set(assignments) == {todo["id"] for todo in todos} and all(
        assignments.values()
    )
    return passed, json.dumps(observations, ensure_ascii=False)


def load_initial(paths):
    if not paths.get("inputs") or not paths.get("preparation_state"):
        raise RuntimeError(
            "This Task requires ordinary Native Host input evidence and preparation state"
        )
    source = SourceSnapshot.read(
        Path(paths["inputs"]) / "handover.csv", max_bytes=8 * 1024 * 1024
    )
    state = json.loads(
        SourceSnapshot.read(
            Path(paths["preparation_state"]) / "reference.json", max_bytes=1024 * 1024
        ).content
    )
    if state.get("version") != 1 or source.sha256 != state.get("source_sha256"):
        raise ValueError("Retained handover and preparation state disagree")
    reference = datetime.fromisoformat(state["reference_time"])
    if reference.utcoffset() != timedelta(hours=8):
        raise ValueError("Reference must be a Shanghai timestamp")
    monday = reference.date() - timedelta(days=reference.weekday())
    if (
        state["week_start"] != monday.isoformat()
        or state["week_end_exclusive"] != (monday + timedelta(days=7)).isoformat()
    ):
        raise ValueError("Invalid retained reference week")
    records = list(csv.DictReader(io.StringIO(source.content.decode("utf-8-sig"))))
    identities = {record["记录ID"] for record in records}
    todos = state["todos"]
    if not todos or len({todo["id"] for todo in todos}) != len(todos):
        raise ValueError("Expected actions must be nonempty and unique")
    for todo in todos:
        if (
            not set(todo["sources"]).issubset(identities)
            or todo["deadline_source"] not in todo["sources"]
            or parse_deadline(todo["deadline"]) is None
        ):
            raise ValueError("Expected action has invalid provenance or deadline")
    return source, state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    source, state = load_initial(paths)
    trajectory = Path(paths["agent_logs"]) / "trajectory.json"
    try:
        snapshot = SourceSnapshot.read(trajectory, max_bytes=128 * 1024 * 1024)
    except FileNotFoundError:
        answer = ""
    else:
        answer = final_answer_text(Trajectory.model_validate_json(snapshot.content))
    passed, reason = evaluate_answer(answer, state)
    with EvidenceWriter(paths["verifier_logs"]) as evidence:
        evidence.capture("handover_csv", source)
        excerpt = "Source: initial handover.csv, complete lines below.\n\n" + "\n".join(
            f"L{number}: {line}"
            for number, line in enumerate(
                source.content.decode("utf-8-sig").splitlines(), 1
            )
        )
        evidence.add_text("source_handover", excerpt, source_id="handover_csv")
        evidence.add_text(
            "reference_window",
            json.dumps(
                {
                    key: state[key]
                    for key in ("reference_time", "week_start", "week_end_exclusive")
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        evidence.add_text("final_answer", answer)
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "id": "current_action_bindings",
                        "passed": bool(passed),
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
