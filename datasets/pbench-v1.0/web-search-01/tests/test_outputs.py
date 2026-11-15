"""Search-result binding and final-answer evidence; no network requests."""

import argparse
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlsplit

from harbor.models.trajectories import Trajectory

from psycheval.harbor.evidence import EvidenceWriter
from psycheval.harbor.verifier import ObservationIndex, evaluate, final_answer_text

EXPECTED = {"example.com", "example.org"}
SEARCH = {
    "any": [{"tool_names": ["websearch", "mcpexawebsearchexa", "exawebsearchexa"]}]
}
FORBIDDEN = [
    "*webfetch*",
    "*exec*",
    "*shell*",
    "*terminal*",
    "bash",
    "pwsh",
    "python",
    "*browser*navigate*",
    "*browser*open*",
    "*browser*evaluate*",
    "*browser*runcode*",
    "computeraction",
]
URL = re.compile(r"https?://[^\s<>\[\]\"']+", re.I)
DOMAIN = re.compile(
    r"(?<![a-z0-9_-])(?:[a-z0-9-]+\.)+[a-z]{2,63}\.?(?![a-z0-9_-])", re.I
)


def target_url(value):
    try:
        parsed = urlsplit(unescape(value).strip().rstrip(".,;:!?)]}）"))
        return (
            parsed.scheme.lower() in {"http", "https"}
            and parsed.hostname in {"iana.org", "www.iana.org"}
            and parsed.username is None
            and parsed.password is None
            and parsed.port in {None, 80 if parsed.scheme.lower() == "http" else 443}
            and unquote(parsed.path).rstrip("/") == "/help/example-domains"
        )
    except ValueError:
        return False


def domains(text):
    return {match[0].lower().rstrip(".") for match in DOMAIN.finditer(text)}


def text_results(text):
    """Keep standard search-result blocks separate instead of joining all hits."""
    # Exa result delimiters take precedence over headings/lists in Highlights.
    boundaries = list(re.finditer(r"(?m)^Title:[^\n]*\nURL:\s*https?://", text))
    if not boundaries:
        boundaries = list(
            re.finditer(
                r"(?m)^(?:#{1,6}\s+)?(?:\d+[.)]\s+)?\[[^\]\n]+\]\(https?://|^(?:#{1,6}\s+)?\d+[.)]\s+[^\n]*https?://",
                text,
            )
        )
    if boundaries:
        return [
            text[
                match.start() : boundaries[index + 1].start()
                if index + 1 < len(boundaries)
                else len(text)
            ]
            for index, match in enumerate(boundaries)
        ]
    # Plain single-hit snippets are also normal tool output. Multiple distinct
    # source URLs without result delimiters do not establish item binding.
    urls = URL.findall(text)
    return [text] if urls and all(target_url(url) for url in urls) else []


def source_items(text):
    try:
        value = json.loads(text)
    except ValueError:
        return text_results(text)
    pending, items, visited = [value], [], 0
    while pending:
        visited += 1
        if visited > 20000:
            raise ValueError("Search result structure exceeds 20000 components")
        value = pending.pop()
        if isinstance(value, dict):
            urls = [
                value[key]
                for key in ("url", "href", "link")
                if isinstance(value.get(key), str)
            ]
            if urls:
                fields = [
                    value[key]
                    for key in (
                        "title",
                        "snippet",
                        "description",
                        "text",
                        "content",
                        "summary",
                        "body",
                    )
                    if isinstance(value.get(key), str)
                ]
                if fields and any(target_url(url) for url in urls):
                    items.append("\n".join([*urls, *fields]))
                # A nested result is independently processed, never attributed
                # to the URL of a containing object.
            pending.extend(
                child for child in value.values() if isinstance(child, (dict, list))
            )
            if not urls:
                pending.extend(
                    value[key]
                    for key in ("text", "content", "output")
                    if isinstance(value.get(key), str)
                )
        elif isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, str):
            items.extend(text_results(value))
    return items


def assess(trajectory, artifacts_dir):
    answer = final_answer_text(trajectory)
    index = ObservationIndex(trajectory)
    policy = next(
        check
        for check in evaluate(
            trajectory, {"forbidden_tool_names": FORBIDDEN}, artifacts_dir
        )
        if check["id"] == "forbidden_tools"
    )
    matches = index.matching(SEARCH)
    observations = []
    supported = False
    for number, (call, texts) in enumerate(matches, 1):
        for observation_number, text in enumerate(texts, 1):
            items = source_items(text)
            for item in items:
                if any(
                    target_url(url) for url in URL.findall(item)
                ) and EXPECTED <= domains(item):
                    supported = True
            observations.append(
                {
                    "search_number": number,
                    "call_id": call.tool_call_id,
                    "tool": call.function_name,
                    "arguments": call.arguments,
                    "observation_number": observation_number,
                    "text": text,
                }
            )
    cited = any(target_url(url) for url in URL.findall(answer))
    passed = bool(
        answer.strip()
        and policy["passed"]
        and supported
        and cited
        and EXPECTED <= domains(answer)
    )
    diagnosis = {
        "matching_successful_search_calls": len(matches),
        "source_supports_both_examples_in_one_item": supported,
        "final_has_examples": EXPECTED <= domains(answer),
        "final_cites_help_page": cited,
        "permitted_channels_only": policy["passed"],
        "policy_evidence": policy["evidence"],
        "retention_problem": index.evidence_error,
        "observed_tool_names": [call.function_name for call in index.calls],
        "limit": "Absent retained search evidence does not prove that a tool was advertised or declined.",
    }
    return passed, diagnosis, observations, answer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    trajectory_path = Path(paths["agent_logs"]) / "trajectory.json"
    with EvidenceWriter(
        paths["verifier_logs"], max_text_bytes=4 * 1024 * 1024
    ) as writer:
        try:
            snapshot = writer.capture(
                "retained_trajectory", trajectory_path, max_bytes=128 * 1024 * 1024
            )
        except FileNotFoundError:
            writer.unavailable("retained_trajectory", "No retained Agent trajectory")
            passed, diagnosis, observations, answer = (
                False,
                {"retention_problem": "missing trajectory"},
                [],
                "",
            )
            source = None
        else:
            trajectory = Trajectory.model_validate_json(snapshot.content)
            passed, diagnosis, observations, answer = assess(
                trajectory, Path(paths["artifacts"])
            )
            source = "retained_trajectory"
        writer.add_text(
            "search_observations",
            "# Retained search evidence\n\n"
            + json.dumps(
                {"verification_facts": diagnosis, "observations": observations},
                ensure_ascii=False,
                indent=2,
            ),
            source_id=source,
        )
        writer.add_text("final_answer", answer, source_id=source)
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "id": "search_backed_answer",
                        "passed": passed,
                        "evidence": json.dumps(diagnosis, ensure_ascii=False),
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
