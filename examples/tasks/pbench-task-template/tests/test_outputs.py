"""One local-source notice check and gated, source-bound Judge evidence."""

import argparse
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from harbor.models.trajectories import Trajectory

from psycheval.harbor.documents import (
    DocumentLimitError,
    DocumentParseError,
    inspect_document,
)
from psycheval.harbor.evidence import EvidenceLimitError, EvidenceWriter
from psycheval.harbor.verifier import final_answer_text

SOURCE = "operations-note.md"
OUTPUT = "notice.md"
MONTHS = {
    name: number
    for number, name in enumerate(
        (
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ),
        1,
    )
}
CLOCK = re.compile(r"\b(\d{1,2}):([0-5]\d)\s*(am|pm)?\b|\b(\d{1,2})\s*(am|pm)\b")


def normalized(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("’", "'")
    text = re.sub(r"\b(\d{1,2})(?:st|nd|rd|th)\b", r"\1", text)
    text = text.replace("a.m.", "am").replace("p.m.", "pm")
    text = re.sub(r"(?<=\d)\.(?=\d{2}\b)", ":", text)
    text = re.sub(r"[–—]", "-", text)
    return re.sub(r"\s+", " ", re.sub(r"[*_`#]", "", text)).strip()


def dates(text):
    result = set()
    for pattern, order in (
        (r"\b(\d{1,2})\s+([a-z]+)\.?\s+(\d{4})\b", (2, 1, 0)),
        (r"\b([a-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})\b", (2, 0, 1)),
        (r"\b(\d{4})-(\d{2})-(\d{2})\b", (0, 1, 2)),
    ):
        for match in re.finditer(pattern, text):
            fields = match.groups()
            year, month, day = (fields[index] for index in order)
            if not month.isdigit() and month[:3] not in MONTHS:
                continue
            month = int(month) if month.isdigit() else MONTHS[month[:3]]
            try:
                result.add(date(int(year), month, int(day)).isoformat())
            except ValueError:
                result.add("invalid date")
    return result


def clocks(text):
    result = []
    for match in CLOCK.finditer(text):
        hour, minute, meridiem, short_hour, short_meridiem = match.groups()
        hour, minute = int(hour or short_hour), int(minute or 0)
        meridiem = meridiem or short_meridiem
        if meridiem:
            if not 1 <= hour <= 12:
                continue
            hour = hour % 12 + (12 if meridiem == "pm" else 0)
        if hour < 24:
            result.append((hour * 60 + minute, match.start(), match.end()))
    return result


def reference(text):
    """The source grammar is intentionally local to this small worked example."""
    text = normalized(text)
    schedule = re.search(
        r"the (.+?) is unavailable on (.+?) from (\d{2}:\d{2}) to (\d{2}:\d{2}) for ",
        text,
    )
    action = re.search(
        r"session leaders must move (.+?) to the (.+?) before (\d{2}:\d{2})\.", text
    )
    routing = re.search(r"booked sessions will meet in the (.+?)\.", text)
    if not schedule or not action or not routing:
        raise ValueError(
            "Initial operations note does not match this Task's source contract"
        )
    closed, day, start, end = schedule.groups()
    items, temporary, deadline = action.groups()
    parsed_dates = dates(day)
    parsed_clocks = [clocks(value) for value in (start, end, deadline)]
    if any(len(value) != 1 for value in parsed_clocks):
        raise ValueError("Initial operations note contains an invalid time")
    start, end, deadline = (value[0][0] for value in parsed_clocks)
    if (
        len(parsed_dates) != 1
        or "invalid date" in parsed_dates
        or temporary != routing[1]
        or deadline != start
        or end <= start
    ):
        raise ValueError(
            "Initial operations note contains inconsistent schedule/routing facts"
        )
    return {
        "closed": closed,
        "date": next(iter(parsed_dates)),
        "start": start,
        "end": end,
        "temporary": temporary,
        "items": items,
        "deadline": deadline,
    }


def closes(text, room):
    text = re.sub(
        r"\b(?:isn't|is not|won't be|will not be) available\b", "unavailable", text
    )
    text = text.replace("not available", "unavailable")
    matches = re.finditer(
        re.escape(room)
        + r"\b([^.!?;]*?)\b(?:closed|closes|closure|unavailable|shut|out of use|out of service)\b",
        text,
    )
    return any(
        not re.search(r"\b(?:not|never|isn't|won't)\b", match[1]) for match in matches
    ) or bool(
        re.search(
            r"\b(?:closure of|do not use|avoid using) (?:the )?"
            + re.escape(room)
            + r"\b",
            text,
        )
    )


def check_notice(report, expected):
    # Inspect visible prose/list/table facts; hidden code/comments do not count.
    lines = report.text.splitlines()
    parts = []
    for block in report.blocks:
        if block.kind in {"heading", "paragraph", "bullet_list", "ordered_list"}:
            parts.append("\n".join(lines[block.start_line : block.end_line]))
        elif block.table is not None:
            rows = {}
            for cell in block.table.cells:
                rows.setdefault(cell.row, []).append(
                    " ".join(item.text for item in cell.blocks if hasattr(item, "text"))
                )
            parts.extend(" | ".join(row) for row in rows.values())
    prose = "\n".join(parts)
    text = normalized(prose)
    times = clocks(text)
    correct_range = any(
        left[0] == expected["start"]
        and right[0] == expected["end"]
        and re.search(r"\b(?:to|until|through|and)\b|-", text[left[2] : right[1]])
        for left, right in zip(times, times[1:])
    )
    deadline = any(
        minute == expected["deadline"]
        and re.search(r"\b(?:before|by|prior to|no later than)\s*$", text[:start])
        for minute, start, _ in times
    )
    cancellations = any(
        not re.search(r"\bno\s*$", text[: match.start()])
        for match in re.finditer(
            r"\b(?:sessions?|classes?)\s+(?:(?:will be|have been|has been|are|is)\s+)?(?:cancelled|canceled)\b",
            text,
        )
    )
    temporary = re.escape(expected["temporary"])
    routing = bool(
        re.search(
            r"\b(?:sessions|classes)\b[^.!?;]*\b(?:meet|use|held|take place|relocate|relocated|move|moved|switch|run|are|will be)\b[^.!?;]*\b"
            + temporary
            + r"\b",
            text,
        )
        or re.search(
            r"\b(?:sessions|classes)\s*[:|\-]\s*(?:the )?" + temporary + r"\b", text
        )
        or re.search(
            r"\b"
            + temporary
            + r"\b[^.!?;]*\b(?:hosts?|accommodates?)\b[^.!?;]*\b(?:sessions|classes)\b",
            text,
        )
    )
    wrong_action = False
    for clause in re.split(r"[.!?;]", text):
        if not re.search(
            r"\b(?:move|bring|take|transfer|relocate|shift)\b", clause
        ) or not re.search(
            r"\b(?:kits?|session materials|session equipment)\b", clause
        ):
            continue
        destinations = re.findall(r"\b(?:to|into) (?:the )?([a-z]+ studio)\b", clause)
        wrong_action |= any(
            destination != expected["temporary"] for destination in destinations
        )
        wrong_action |= any(
            minute != expected["deadline"]
            and re.search(r"\b(?:before|by|prior to|no later than)\s*$", clause[:start])
            for minute, start, _ in clocks(clause)
        )
    facts = {
        "date": dates(text) == {expected["date"]},
        "closure": closes(text, expected["closed"])
        and not closes(text, expected["temporary"]),
        "window": bool(correct_range)
        and {value for value, _, _ in times} == {expected["start"], expected["end"]},
        "routing": routing,
        "leader_action": bool(
            re.search(r"\b(?:move|bring|take|transfer|relocate|shift)\b", text)
        )
        and (
            expected["items"] in text
            or (
                expected["items"] == "session kits"
                and bool(
                    re.search(
                        r"\b(?:kits?|session materials|session equipment)\b", text
                    )
                )
            )
        )
        and deadline,
        "no_direct_conflict": not cancellations
        and not closes(text, "reception")
        and not wrong_action,
    }
    return all(facts.values()), facts


def retained_output(artifacts):
    if not artifacts.is_absolute() or artifacts.parts[-2:] != ("logs", "artifacts"):
        raise ValueError(
            "This example requires the Native Host artifacts/logs/artifacts mapping"
        )
    return artifacts.parent.parent / OUTPUT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    if not paths.get("inputs"):
        raise ValueError("This example requires Native Host retained initial inputs")
    output = retained_output(Path(paths["artifacts"]))
    with EvidenceWriter(paths["verifier_logs"]) as writer:
        source = writer.capture("initial_note", Path(paths["inputs"]) / SOURCE)
        source_report = inspect_document(source, format="md")
        expected = reference(source_report.text)
        writer.add_text(
            "source_excerpt",
            f"{SOURCE}, lines 1-{len(source_report.text.splitlines())}:\n\n"
            + "\n".join(
                f"L{number}: {line}"
                for number, line in enumerate(source_report.text.splitlines(), 1)
            ),
            source_id="initial_note",
        )
        passed, facts = False, {"deliverable": "missing"}
        try:
            notice = writer.capture("notice_md", output)
        except EvidenceLimitError:
            raise
        except (FileNotFoundError, ValueError) as error:
            writer.unavailable("notice_md", str(error))
        else:
            try:
                report = inspect_document(notice, format="md")
            except DocumentLimitError:
                raise
            except DocumentParseError as error:
                facts = {"deliverable": str(error)}
            else:
                passed, facts = check_notice(report, expected)
                writer.add_text("notice_text", report.text, source_id="notice_md")
                if passed:
                    writer.add_text(
                        "verified_notice", report.text, source_id="notice_md"
                    )
        if not passed:
            writer.unavailable(
                "verified_notice",
                "Basic source-bound notice facts are missing or incorrect",
            )
        try:
            trajectory = writer.capture(
                "retained_trajectory",
                Path(paths["agent_logs"]) / "trajectory.json",
                max_bytes=128 * 1024 * 1024,
            )
        except FileNotFoundError:
            writer.unavailable("final_answer", "No retained Agent trajectory")
        else:
            answer = final_answer_text(
                Trajectory.model_validate_json(trajectory.content)
            )
            writer.add_text("final_answer", answer, source_id="retained_trajectory")
        writer.add_text(
            "execution_facts",
            json.dumps(
                {
                    "source": {
                        "path": SOURCE,
                        "sha256": source.sha256,
                        "basis": "retained initial input, not mutable workspace",
                    },
                    "output": str(output),
                    "basic_notice_facts": facts,
                    "notice_gate_passed": passed,
                    "scope": "Basic facts only. Tool use is not scored; prose quality and full factual fidelity require Judge assessment.",
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "id": "notice_facts",
                        "passed": passed,
                        "evidence": json.dumps(facts, ensure_ascii=False),
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
