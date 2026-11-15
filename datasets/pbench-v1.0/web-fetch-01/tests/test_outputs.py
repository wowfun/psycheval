"""One source-bound retrieval result over retained, paired tool observations."""

import argparse
import html
import json
import re
from datetime import date, datetime
from pathlib import Path

from harbor.models.trajectories import Trajectory

from psycheval.harbor.documents import DocumentLimits, inspect_document
from psycheval.harbor.evidence import EvidenceWriter, SourceSnapshot
from psycheval.harbor.verifier import ObservationIndex, evaluate, final_answer_text

URL = "https://www.iana.org/help/example-domains"
FETCH = {"any": [{"tool_names": ["*webfetch"], "argument_url": URL}]}
RULES = {
    "required_calls": [FETCH],
    "forbidden_tool_names": [
        "*websearch*",
        "*searchweb*",
        "*exec*",
        "*terminal*",
        "*shell*",
        "bash",
        "pwsh",
        "python",
        "*runcode*",
    ],
}
MONTHS = "January February March April May June July August September October November December".split()
MONTH = "(?:" + "|".join(f"{name}|{name[:3]}" for name in MONTHS) + ")"
DATES = re.compile(
    rf"(?<!\d)(?:\d{{4}}\s*[-/.年]\s*\d{{1,2}}\s*[-/.月]\s*\d{{1,2}}\s*日?"
    rf"|{MONTH}\s+\d{{1,2}},?\s+\d{{4}}|\d{{1,2}}\s+{MONTH}\s+\d{{4}})(?!\d)",
    re.IGNORECASE,
)
REVISION = re.compile(r"last\s+revised\s*[:：]?\s*(?:on\s+)?", re.IGNORECASE)


def dates(text):
    found = []
    for match in DATES.finditer(text):
        value = match[0].strip()
        numeric = re.fullmatch(
            r"(\d{4})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})\s*日?", value
        )
        if numeric:
            try:
                parsed = date(*map(int, numeric.groups()))
            except ValueError:
                continue
        else:
            parsed = None
            for pattern in ("%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y"):
                try:
                    parsed = datetime.strptime(value.replace(",", ""), pattern).date()
                    break
                except ValueError:
                    continue
            if parsed is None:
                continue
        found.append((match.start(), match.end(), parsed.isoformat()))
    return found


def response_body(raw):
    """Read common tool response envelopes without treating HTTP headers as body."""
    if isinstance(raw, str):
        try:
            value = json.loads(raw)
        except ValueError:
            return raw
        return response_body(value) if isinstance(value, (dict, list)) else raw
    if isinstance(raw, list):
        return "\n".join(response_body(value) for value in raw)
    if not isinstance(raw, dict):
        return ""
    status = raw.get("status_code", raw.get("status"))
    if isinstance(status, str) and status.isdecimal():
        status = int(status)
    if raw.get("error") or raw.get("is_error") is True:
        return ""
    if (
        isinstance(status, int)
        and not isinstance(status, bool)
        and not 200 <= status < 300
    ):
        return ""
    if str(status).lower() in {"error", "failed", "failure", "timeout", "cancelled"}:
        return ""
    return "\n".join(
        response_body(raw[key])
        for key in (
            "content",
            "text",
            "markdown",
            "body",
            "html",
            "data",
            "result",
            "results",
            "response",
        )
        if key in raw
    )


def source_text(raw):
    text = response_body(raw)
    if re.search(
        r"<(?:!doctype|html|body|p|div|footer|table|span)\b", text, re.IGNORECASE
    ):
        snapshot = SourceSnapshot(Path("fetched-response.html"), text.encode("utf-8"))
        text = inspect_document(
            snapshot,
            format="html",
            limits=DocumentLimits(source_bytes=512 * 1024, text_bytes=512 * 1024),
        ).text
    return html.unescape(text)


def answer_revision_claims(answer):
    result = []
    for start, end, value in dates(answer):
        prefix = answer[max(0, start - 40) : start]
        if re.search(
            r"(?:retrieved|fetched|accessed|access date|抓取|访问|检索|查询)[^.!?\n]{0,20}$",
            prefix,
            re.IGNORECASE,
        ):
            continue
        result.append((start, end, value))
    return result


def unconfirmed_claim(answer, start, end):
    prefix, suffix = answer[max(0, start - 80) : start], answer[end : end + 55]
    return bool(
        re.search(
            r"(?:\b(?:not|isn't|wasn't|never|maybe|perhaps|possibly|may be|might be)|并非|不是|可能|也许|大概)"
            r"\s*(?:(?:the\s+)?(?:last\s+)?revised(?:\s+on)?|最后(?:修订|更新)(?:于|为)?|(?:修订|更新)(?:于|为)?)?\s*$",
            prefix,
            re.IGNORECASE,
        )
        or re.match(
            r"^[\s`*'\"),]*(?:(?:is|was)\s+)?(?:unverified|uncertain|not\s+(?:verified|confirmed))\b",
            suffix,
            re.IGNORECASE,
        )
    )


def assess(trajectory):
    action_checks = evaluate(trajectory, RULES, Path("."))
    required = {check["id"]: check["passed"] for check in action_checks}
    index = ObservationIndex(trajectory)
    bodies, revisions = [], set()
    for call, observations in index.matching(FETCH):
        for number, raw in enumerate(observations, 1):
            text = source_text(raw)
            if "example domains" not in text.casefold():
                continue
            matches = []
            for label in REVISION.finditer(text):
                following = dates(text[label.end() : label.end() + 60])
                if following and not text[
                    label.end() : label.end() + following[0][0]
                ].strip(" \n\t`*_\"'"):
                    matches.append(following[0][2])
            revisions.update(matches)
            bodies.append(
                f"Source: retained trajectory, tool_call_id={call.tool_call_id}, "
                f"function={call.function_name}, target={URL}, successful paired observation={number}.\n"
                + "\n".join(
                    f"L{line}: {value}"
                    for line, value in enumerate(text.splitlines(), 1)
                )
            )
    answer = final_answer_text(trajectory)
    claims = answer_revision_claims(answer)
    answer_dates = {value for _, _, value in claims}
    cited = bool(
        re.search(
            r"https://www\.iana\.org/help/example-domains/?(?:[#?][^\s<>]*)?(?=[\s<>\])）。,;.!?]|$)",
            answer,
            re.IGNORECASE,
        )
    )
    unconfirmed = any(unconfirmed_claim(answer, start, end) for start, end, _ in claims)
    expected = next(iter(revisions)) if len(revisions) == 1 else None
    passed = bool(
        required
        and all(required.values())
        and expected
        and answer_dates == {expected}
        and cited
        and not unconfirmed
    )
    availability = (
        "source_revision_available"
        if expected
        else "conflicting_revision_lines"
        if revisions
        else "no_successful_revision_source"
    )
    facts = {
        "verified_fetch": passed,
        "source_status": availability,
        "source_revision_dates": sorted(revisions),
        "answer_dates": sorted(answer_dates),
        "target_cited": cited,
        "unconfirmed_revision_claim": unconfirmed,
        "action_checks": action_checks,
        "tool_evidence_error": index.evidence_error,
        "capability_availability": "Not inferred from absent calls; inspect retained Agent/tool configuration separately.",
        "date_basis": "Only Last revised lines in this attempt's successful paired target response; no independent network fetch or fixed date.",
    }
    return (
        passed,
        facts,
        "\n\n".join(bodies)
        or "No successful paired target-page body with an identifiable revision line was retained.",
        answer,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    with EvidenceWriter(
        paths["verifier_logs"], max_text_bytes=2 * 1024 * 1024
    ) as writer:
        try:
            retained = writer.capture(
                "retained_trajectory",
                Path(paths["agent_logs"]) / "trajectory.json",
                max_bytes=128 * 1024 * 1024,
            )
        except FileNotFoundError:
            writer.unavailable("retained_trajectory", "No retained Agent trajectory")
            passed, facts, source, answer = (
                False,
                {"verified_fetch": False, "source_status": "trajectory_unavailable"},
                "No retained fetch evidence.",
                "",
            )
            source_id = None
        else:
            trajectory = Trajectory.model_validate_json(retained.content)
            passed, facts, source, answer = assess(trajectory)
            source_id = "retained_trajectory"
        writer.add_text("fetched_source", source, source_id=source_id)
        writer.add_text("final_answer", answer, source_id=source_id)
        writer.add_text(
            "execution_facts", json.dumps(facts, ensure_ascii=False, indent=2)
        )
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "id": "verified_fetch",
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
