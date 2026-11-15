"""Bind real UI actions, their result and a retained PNG; never execute a browser."""

import argparse
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from harbor.models.trajectories import Trajectory

from psycheval.harbor.documents import (
    DocumentLimitError,
    DocumentParseError,
    inspect_document,
)
from psycheval.harbor.evidence import EvidenceLimitError, EvidenceWriter
from psycheval.harbor.family import tools_complete
from psycheval.harbor.verifier import ObservationIndex, final_answer_text

FORM = "/selenium/web/web-form.html"
RESULT = "/selenium/web/submitted-form.html"
FILENAME = "web-form-submitted.png"
VALUE = "Morning briefing"
URL = re.compile(r"https?://[^\s<>\[\]\"'`]+", re.I)
OPERATIONS = (
    "browsernavigate",
    "browsertype",
    "browserfillform",
    "browserclick",
    "browserpresskey",
    "browsersnapshot",
    "browsertakescreenshot",
    "browsernavigateback",
    "browsernavigateforward",
    "browsergoback",
    "browsergoforward",
    "browsertabs",
    "browserclose",
)
NAMES = {
    name: operation
    for operation in OPERATIONS
    for name in (operation, "mcpplaywright" + operation, "playwright" + operation)
}
NAMES.update(
    {name: "computeraction" for name in ("computeraction", "mcpcomputercomputeraction")}
)
RULE = {"any": [{"tool_names": list(NAMES)}]}


def observation_text(text):
    """Unwrap MCP text blocks without interpreting tool-generated code as actions."""
    try:
        pending = [json.loads(text)]
    except ValueError:
        return text
    extracted = []
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            for key in ("text", "content", "output"):
                value = item.get(key)
                if isinstance(value, str):
                    extracted.append(value)
                elif isinstance(value, (dict, list)):
                    pending.append(value)
        elif isinstance(item, list):
            pending.extend(reversed(item))
    # Do not mix the escaped JSON envelope with its decoded text: a literal
    # backslash-n can otherwise become part of a URL or snapshot target.
    return "\n".join(extracted) if extracted else text


def url_key(value, path):
    try:
        parsed = urlsplit(unescape(value).strip().rstrip(".,;:!?)]}）"))
        if (
            parsed.scheme.lower() != "https"
            or parsed.hostname not in {"www.selenium.dev", "selenium.dev"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
            or parsed.path != path
        ):
            return None
        query = tuple(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
        if path == RESULT and [v for k, v in query if k == "my-text"] != [VALUE]:
            return None
        return parsed.hostname, parsed.path, query
    except ValueError:
        return None


def urls(text, path):
    return {
        key: match[0]
        for match in URL.finditer(text)
        if (key := url_key(match[0], path)) is not None
    }


def field_refs(text, role, label):
    """Resolve opaque snapshot targets through the observed accessible label."""
    pattern = rf'(?im)^.*\b{role}\s+"{re.escape(label)}"[^\n]*\bref=([\w-]+)'
    found = set(re.findall(pattern, text))
    try:
        pending = [json.loads(text)]
    except ValueError:
        return found
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            if item.get("role") == role and item.get("name") == label:
                found.update(str(item[key]) for key in ("ref", "target") if key in item)
            pending.extend(v for v in item.values() if isinstance(v, (dict, list)))
        elif isinstance(item, list):
            pending.extend(item)
    return found


def target(arguments):
    return str(
        arguments.get("target")
        or arguments.get("ref")
        or arguments.get("selector")
        or ""
    )


def input_target(arguments, refs):
    value = target(arguments)
    return value in refs or bool(
        re.search(r"(?<![\w-])my-text(?:-id)?(?![\w-])", value)
    )


def submit_target(arguments, refs):
    value = target(arguments)
    return value in refs or bool(
        re.fullmatch(r"button(?:\[type\s*=\s*['\"]?submit['\"]?\])?", value, re.I)
        or re.search(r"button.*(?:has-text|name).*Submit", value, re.I)
    )


def computer_coordinates(arguments):
    return all(
        isinstance(arguments.get(key), (int, float))
        and not isinstance(arguments[key], bool)
        for key in ("x", "y")
    )


def typed_field_observed(text):
    # A coordinate alone cannot identify the field. Require its observed value.
    if re.search(rf'textbox\s+"Text input"[^\n]*:\s*{re.escape(VALUE)}\b', text, re.I):
        return True
    try:
        item = json.loads(text)
    except ValueError:
        return False
    return (
        isinstance(item, dict)
        and item.get("field") in {"Text input", "my-text", "my-text-id"}
        and item.get("value") == VALUE
    )


def named_screenshot(arguments, workdir):
    value = arguments.get("filename") or arguments.get("path")
    if not isinstance(value, str):
        return False
    if value.replace("\\", "/") in {FILENAME, "./" + FILENAME}:
        return True
    path = Path(value)
    return path.is_absolute() and path.resolve() == (workdir / FILENAME).resolve()


def retained_screenshot(artifacts_dir):
    """Task destination is beside the Native Host mounted convention subtree."""
    if not artifacts_dir.is_absolute() or artifacts_dir.parts[-2:] != (
        "logs",
        "artifacts",
    ):
        raise ValueError(
            "This Task requires the Native Host artifacts/logs/artifacts mapping"
        )
    return artifacts_dir.parent.parent / FILENAME


def owners(trajectory):
    pending = [trajectory]
    while pending:
        owner = pending.pop()
        yield owner
        pending.extend(reversed(owner.subagent_trajectories or []))


def assess(trajectory, workdir):
    answer = final_answer_text(trajectory)
    index = ObservationIndex(trajectory)
    history_complete = not index.evidence_error and tools_complete(
        trajectory.model_dump()
    )
    matches = {id(call): texts for call, texts in index.matching(RULE)}
    observations, witnesses, screenshot_attempts = [], [], []
    for owner in owners(trajectory):
        opened, typed, focused, submitted = False, False, False, False
        input_refs, submit_refs, current = set(), set(), None
        for step in owner.steps:
            if step.is_copied_context:
                continue
            for call in step.tool_calls or []:
                name = call.function_name.lower().replace("_", "").replace("-", "")
                operation = NAMES.get(name)
                texts = matches.get(id(call), ())
                if operation is None:
                    continue
                arguments = call.arguments
                text = "\n".join(observation_text(value) for value in texts)
                owner_id = owner.trajectory_id or owner.session_id
                is_computer = operation == "computeraction"
                action = arguments.get("type") if is_computer else None
                screenshot = (
                    operation == "browsertakescreenshot" or action == "screenshot"
                )
                attempt = None
                if screenshot and named_screenshot(arguments, workdir):
                    attempt = {
                        "trajectory_id": owner_id,
                        "call_id": call.tool_call_id,
                        "successful_observation": bool(texts),
                        "confirmed_result": False,
                    }
                    screenshot_attempts.append(attempt)
                observations.append(
                    {
                        "trajectory_id": owner_id,
                        "call_id": call.tool_call_id,
                        "tool": call.function_name,
                        "arguments": arguments,
                        "successful_observations": texts,
                    }
                )
                if (
                    operation == "browsernavigate"
                    or operation
                    in {
                        "browsernavigateback",
                        "browsernavigateforward",
                        "browsergoback",
                        "browsergoforward",
                        "browserclose",
                    }
                    or (
                        operation == "browsertabs" and arguments.get("action") != "list"
                    )
                ):
                    opened, typed, focused, submitted = False, False, False, False
                    input_refs, submit_refs, current = set(), set(), None
                    if (
                        operation == "browsernavigate"
                        and url_key(str(arguments.get("url", "")), FORM)
                        and urls(text, FORM)
                    ):
                        opened = True
                if not texts:
                    continue
                # Current-page context must not drift to a different final URL.
                page_urls = re.findall(r"(?im)^- Page URL:\s*(https?://\S+)", text)
                if current and any(
                    url_key(value, RESULT) != current["url_key"] for value in page_urls
                ):
                    current = None
                    submitted = False
                input_action = operation == "browsertype" or action == "type_text_at"
                if input_action and opened and arguments.get("text") == VALUE:
                    bound = (
                        computer_coordinates(arguments) and typed_field_observed(text)
                        if is_computer
                        else input_target(arguments, input_refs)
                    )
                    if bound:
                        typed = focused = True
                        if (
                            operation == "browsertype"
                            and arguments.get("submit") is True
                        ):
                            submitted = True
                if operation == "browserfillform" and opened:
                    fields = arguments.get("fields", [])
                    if isinstance(fields, list) and any(
                        isinstance(field, dict)
                        and field.get("type") == "textbox"
                        and field.get("value") == VALUE
                        and input_target(field, input_refs)
                        for field in fields
                    ):
                        typed = True
                        focused = bool(
                            fields
                            and isinstance(fields[-1], dict)
                            and fields[-1].get("type") == "textbox"
                            and fields[-1].get("value") == VALUE
                            and input_target(fields[-1], input_refs)
                        )
                if operation == "browserclick" or action == "click":
                    button = arguments.get("button", "left")
                    bound = (
                        computer_coordinates(arguments)
                        if is_computer
                        else submit_target(arguments, submit_refs)
                    )
                    if typed and bound and button == "left":
                        submitted = True
                    focused = False
                if (
                    typed
                    and focused
                    and (
                        operation == "browserpresskey"
                        or action in {"press_key", "key_press", "keypress"}
                    )
                    and arguments.get("key") in {"Enter", "ENTER", "Return"}
                ):
                    submitted = True
                # A screenshot is evidence of the already observed result, never
                # a substitute for an earlier successful UI submission.
                if (
                    attempt is not None
                    and current
                    and FILENAME in text
                    and arguments.get("type", "png") in {"png", "screenshot"}
                ):
                    current["screenshot_call_id"] = call.tool_call_id
                    attempt["confirmed_result"] = True
                if (
                    submitted
                    and not screenshot
                    and re.search(r"\bReceived!", text, re.I)
                ):
                    result_urls = urls(text, RESULT)
                    if len(result_urls) == 1:
                        key, value = next(iter(result_urls.items()))
                        if current is None or current["url_key"] != key:
                            current = {
                                "trajectory_id": owner.trajectory_id
                                or owner.session_id,
                                "confirmation_call_id": call.tool_call_id,
                                "url": value,
                                "url_key": key,
                                "screenshot_call_id": None,
                            }
                            witnesses.append(current)
                input_refs.update(field_refs(text, "textbox", "Text input"))
                submit_refs.update(field_refs(text, "button", "Submit"))
    final_urls = urls(answer, RESULT)
    supported = [
        item
        for item in witnesses
        if item["url_key"] in final_urls and re.search(r"\bReceived!", answer, re.I)
    ]
    form_passed = bool(supported and not index.evidence_error)
    # The retained filename denotes one final file. A later save can overwrite
    # an earlier good capture, even when its observation is missing or failed.
    # Separate owners have no implicit chronological order in retained ATIF.
    screenshot_owners = {item["trajectory_id"] for item in screenshot_attempts}
    last_attempt = screenshot_attempts[-1] if len(screenshot_owners) == 1 else None
    screenshot_action = bool(
        last_attempt
        and history_complete
        and last_attempt["confirmed_result"]
        and any(
            item["trajectory_id"] == last_attempt["trajectory_id"]
            and item["screenshot_call_id"] == last_attempt["call_id"]
            for item in supported
        )
    )
    diagnosis = {
        "ordered_submission_and_final_report": form_passed,
        "post_confirmation_screenshot_action": screenshot_action,
        "final_names_screenshot": FILENAME in answer,
        "witnesses": witnesses,
        "same_filename_screenshot_attempts": screenshot_attempts,
        "screenshot_writer_order_ambiguous": len(screenshot_owners) > 1,
        "screenshot_tool_history_complete": bool(history_complete),
        "retention_problem": index.evidence_error,
        "observed_tool_names": [call.function_name for call in index.calls],
        "limit": "Missing retained actions do not establish which tools were offered. UI witnesses stay within one trajectory; unrelated sibling actions are never combined.",
    }
    return (
        form_passed,
        bool(screenshot_action and FILENAME in answer),
        diagnosis,
        observations,
        answer,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    screenshot_path = retained_screenshot(Path(paths["artifacts"]))
    with EvidenceWriter(
        paths["verifier_logs"], max_text_bytes=4 * 1024 * 1024
    ) as writer:
        try:
            retained = writer.capture(
                "retained_trajectory",
                Path(paths["agent_logs"]) / "trajectory.json",
                max_bytes=128 * 1024 * 1024,
            )
        except FileNotFoundError:
            writer.unavailable("retained_trajectory", "No retained Agent trajectory")
            form, screenshot_action, diagnosis, observations, answer = (
                False,
                False,
                {"retention_problem": "missing trajectory"},
                [],
                "",
            )
            source = None
        else:
            form, screenshot_action, diagnosis, observations, answer = assess(
                Trajectory.model_validate_json(retained.content), Path(paths["workdir"])
            )
            source = "retained_trajectory"
        image_source, image_valid = None, False
        try:
            image = writer.capture("screenshot", screenshot_path)
        except EvidenceLimitError:
            raise
        except (FileNotFoundError, ValueError) as error:
            facts = f"Screenshot unavailable: {error}"
            writer.unavailable("screenshot", facts)
        else:
            image_source = "screenshot"
            try:
                report = inspect_document(image, format="png")
            except DocumentLimitError:
                raise
            except DocumentParseError as error:
                facts = f"Retained screenshot cannot be decoded as PNG: {error}"
            else:
                image_valid = True
                facts = report.to_markdown()
        screenshot = bool(form and screenshot_action and image_valid)
        diagnosis["retained_png_decodable"] = image_valid
        diagnosis["screenshot_passed"] = screenshot
        writer.add_text(
            "browser_observations",
            json.dumps(
                {"verification_facts": diagnosis, "observations": observations},
                ensure_ascii=False,
                indent=2,
            ),
            source_id=source,
        )
        writer.add_text(
            "screenshot_facts",
            facts
            + "\n\nStatic image facts do not establish depicted content or visual correctness.",
            source_id=image_source,
        )
        writer.add_text("final_answer", answer, source_id=source)
    args.output.write_text(
        json.dumps(
            {
                "checks": [
                    {
                        "id": "submitted_form",
                        "passed": form,
                        "evidence": json.dumps(diagnosis, ensure_ascii=False),
                    },
                    {
                        "id": "submitted_screenshot",
                        "passed": screenshot,
                        "evidence": facts,
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
