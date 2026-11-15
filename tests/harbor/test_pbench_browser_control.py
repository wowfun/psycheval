"""Real UI witnesses, valid static PNGs and public local Judge publication."""

import asyncio
import json
import logging
import runpy
import shutil
import sys
from copy import deepcopy
from html import escape
from pathlib import Path
from types import SimpleNamespace

import pytest
from harbor.models.trajectories import Trajectory
from harbor.trial.artifact_handler import ArtifactHandler, artifact_host_path

from psycheval.harbor.documents import DocumentLimitError, MissingDocumentDependency
from psycheval.harbor.family import retain
from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
)
from psycheval.harbor.tasks import load_harbor_task
from psycheval.harbor.verifier import (
    JudgeSettings,
    build_scoring_plan,
    load_judge_config,
    run_verifier,
)
from tests.fixtures import load_pbench_trajectory
from tests.fixtures.judge_server import judge_server

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "datasets/pbench-v1.0-plus/browser-control-01"
FIXTURE = ROOT / "tests/fixtures/pbench/browser-control-01"
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
FORM_URL = "https://www.selenium.dev/selenium/web/web-form.html"
FINAL_URL = "https://www.selenium.dev/selenium/web/submitted-form.html?my-text=Morning+briefing&my-password=&my-textarea="
SNAPSHOT = (
    f"### Page\n- Page URL: {FORM_URL}\n### Snapshot\n"
    '- textbox "Text input" [ref=e5]\n'
    '- textbox "Password" [ref=e6]\n'
    '- button "Submit" [ref=e15]\n'
)
CONFIRMATION = (
    f"### Page\n- Page URL: {FINAL_URL}\n### Snapshot\n"
    '- heading "Form submitted" [ref=e2]\n- paragraph [ref=e3]: Received!'
)


def data():
    value = json.loads((FIXTURE / "trajectory.json").read_text(encoding="utf-8"))
    value["extra"] = {"tool_evidence": "complete"}
    return value


def history(value=None):
    value = value or data()
    for number, step in enumerate(value["steps"], 1):
        step["step_id"] = number
    return Trajectory.model_validate(retain(value))


def assess(value=None, tmp_path=Path(".")):
    return GRADER["assess"](history(value), tmp_path)


def mcp_data(prefix="mcp__playwright__", envelope=True):
    value = data()
    for step in value["steps"][1:-1]:
        call = step["tool_calls"][0]
        call["function_name"] = prefix + call["function_name"]
    value["steps"][1]["observation"]["results"][0]["content"] = SNAPSHOT
    value["steps"][2]["tool_calls"][0]["arguments"] = {
        "target": "e5",
        "text": "Morning briefing",
    }
    value["steps"][2]["observation"]["results"][0]["content"] = SNAPSHOT.replace(
        "[ref=e5]", "[active] [ref=e5]: Morning briefing"
    )
    value["steps"][3]["tool_calls"][0]["arguments"] = {"target": "e15"}
    value["steps"][3]["observation"]["results"][0]["content"] = CONFIRMATION
    if envelope:
        for step in value["steps"][1:-1]:
            result = step["observation"]["results"][0]
            result["content"] = json.dumps(
                {
                    "content": [{"type": "text", "text": result["content"]}],
                    "isError": False,
                }
            )
    return value


@pytest.mark.parametrize("prefix", ["", "mcp__playwright__", "playwright_"])
@pytest.mark.parametrize("envelope", [False, True])
def test_actual_ui_and_opaque_targets_accept_native_and_qualified_mcp_names(
    prefix, envelope
):
    assert assess(mcp_data(prefix, envelope))[:2] == (True, True)


@pytest.mark.parametrize(
    "mode", ["click", "enter", "type_submit", "fill_form", "fill_enter", "computer"]
)
def test_permitted_input_and_submission_methods_have_real_ordered_evidence(mode):
    value = data()
    if mode in {"fill_form", "fill_enter"}:
        value["steps"][2]["tool_calls"][0].update(
            function_name="browser_fill_form",
            arguments={
                "fields": [
                    {
                        "target": "#my-text-id",
                        "name": "Text input",
                        "type": "textbox",
                        "value": "Morning briefing",
                    }
                ]
            },
        )
    if mode in {"enter", "fill_enter"}:
        value["steps"][3]["tool_calls"][0].update(
            function_name="browser_press_key",
            arguments={"key": "Enter"},
        )
    if mode == "type_submit":
        value["steps"][2]["tool_calls"][0]["arguments"]["submit"] = True
        value["steps"][2]["observation"] = value["steps"][3]["observation"]
        value["steps"][2]["observation"]["results"][0]["source_call_id"] = "browser-2"
        value["steps"].pop(3)
    if mode == "computer":
        value["steps"][2]["tool_calls"][0].update(
            function_name="computer_action",
            arguments={
                "type": "type_text_at",
                "text": "Morning briefing",
                "x": 100,
                "y": 200,
            },
        )
        value["steps"][3]["tool_calls"][0].update(
            function_name="computer_action",
            arguments={"type": "click", "x": 100, "y": 250},
        )
        value["steps"][4]["tool_calls"][0].update(
            function_name="computer_action",
            arguments={"type": "screenshot", "filename": "web-form-submitted.png"},
        )
    assert assess(value)[:2] == (True, True)


@pytest.mark.parametrize(
    "problem",
    [
        "empty_answer",
        "wrong_final_url",
        "missing_query",
        "wrong_value",
        "wrong_input",
        "missing_navigate",
        "failed_navigate",
        "failed_type",
        "failed_submit",
        "wrong_source_call",
        "missing_confirmation",
        "wrong_observed_url",
        "no_real_input",
        "no_real_submit",
        "fake_evaluate",
        "wrong_click",
        "right_click",
        "out_of_order",
        "direct_result",
        "noncanonical",
        "opaque_unknown_ref",
        "no_coordinate_field_binding",
    ],
)
def test_claims_names_and_result_page_shortcuts_cannot_establish_submission(problem):
    value = data()
    if problem == "empty_answer":
        value["steps"][-1]["message"] = ""
    elif problem == "wrong_final_url":
        value["steps"][-1]["message"] = value["steps"][-1]["message"].replace(
            "my-text=Morning+briefing", "my-text=Different"
        )
    elif problem == "missing_query":
        value["steps"][-1]["message"] = (
            f"Received! {FINAL_URL.split('?')[0]} web-form-submitted.png"
        )
    elif problem == "wrong_value":
        value["steps"][2]["tool_calls"][0]["arguments"]["text"] = "Something else"
    elif problem == "wrong_input":
        value["steps"][2]["tool_calls"][0]["arguments"]["selector"] = (
            "input[name=my-password]"
        )
    elif problem == "missing_navigate":
        value["steps"].pop(1)
    elif problem.startswith("failed_"):
        pos = {"failed_navigate": 1, "failed_type": 2, "failed_submit": 3}[problem]
        value["steps"][pos]["observation"]["results"][0]["extra"]["is_error"] = True
    elif problem == "wrong_source_call":
        value["steps"][3]["tool_calls"].append(
            {
                "tool_call_id": "other-call",
                "function_name": "browser_snapshot",
                "arguments": {},
            }
        )
        value["steps"][3]["observation"]["results"][0]["source_call_id"] = "other-call"
    elif problem == "missing_confirmation":
        value["steps"][3]["observation"]["results"][0]["content"] = json.dumps(
            {"url": FINAL_URL}
        )
    elif problem == "wrong_observed_url":
        value["steps"][3]["observation"]["results"][0]["content"] = json.dumps(
            {
                "url": "https://other.invalid/selenium/web/submitted-form.html?my-text=Morning+briefing",
                "message": "Received!",
            }
        )
    elif problem == "no_real_input":
        value["steps"][2]["tool_calls"][0]["function_name"] = "shell"
    elif problem == "no_real_submit":
        value["steps"][3]["tool_calls"][0]["function_name"] = "browser_snapshot"
    elif problem == "fake_evaluate":
        for step in value["steps"][1:4]:
            step["tool_calls"][0]["function_name"] = "mcp__playwright__browser_evaluate"
            step["tool_calls"][0]["arguments"]["code"] = (
                "browser_navigate(); browser_type(); browser_click();"
            )
    elif problem == "wrong_click":
        value["steps"][3]["tool_calls"][0]["arguments"]["selector"] = "a"
    elif problem == "right_click":
        value["steps"][3]["tool_calls"][0]["arguments"]["button"] = "right"
    elif problem == "out_of_order":
        value["steps"][2], value["steps"][3] = value["steps"][3], value["steps"][2]
    elif problem == "direct_result":
        value["steps"][3]["tool_calls"][0].update(
            function_name="browser_navigate", arguments={"url": FINAL_URL}
        )
    elif problem == "noncanonical":
        value["steps"][2]["tool_calls"][0]["extra"] = {"acp_canonical_name": False}
    elif problem == "opaque_unknown_ref":
        value["steps"][2]["tool_calls"][0]["arguments"] = {
            "target": "e5",
            "element": "Text input",
            "text": "Morning briefing",
        }
    elif problem == "no_coordinate_field_binding":
        value["steps"][2]["tool_calls"][0].update(
            function_name="computer_action",
            arguments={
                "type": "type_text_at",
                "text": "Morning briefing",
                "x": 100,
                "y": 200,
            },
        )
        value["steps"][2]["observation"]["results"][0]["content"] = (
            "Typed Morning briefing"
        )
    assert assess(value)[:2] == (False, False)


@pytest.mark.parametrize(
    "problem",
    [
        "missing",
        "too_early",
        "wrong_name",
        "wrong_directory",
        "failed",
        "no_filename_observation",
        "final_omits_filename",
        "navigation_drift",
    ],
)
def test_screenshot_requires_actual_capture_of_the_observed_result(problem):
    value = data()
    if problem == "missing":
        value["steps"].pop(4)
    elif problem == "too_early":
        value["steps"][3], value["steps"][4] = value["steps"][4], value["steps"][3]
    elif problem == "wrong_name":
        value["steps"][4]["tool_calls"][0]["arguments"]["filename"] = "other.png"
    elif problem == "wrong_directory":
        value["steps"][4]["tool_calls"][0]["arguments"]["filename"] = (
            "other/web-form-submitted.png"
        )
    elif problem == "failed":
        value["steps"][4]["observation"]["results"][0]["extra"]["status"] = "failed"
    elif problem == "no_filename_observation":
        value["steps"][4]["observation"]["results"][0]["content"] = "No output"
    elif problem == "final_omits_filename":
        value["steps"][-1]["message"] = f"Received! {FINAL_URL}"
    elif problem == "navigation_drift":
        value["steps"][4]["observation"]["results"][0]["content"] += (
            "\n- Page URL: https://other.invalid/"
        )
    assert assess(value)[:2] == (True, False)


@pytest.mark.parametrize("later", ["other_page", "failed_save", "missing_observation"])
def test_later_same_filename_save_cannot_borrow_an_earlier_good_screenshot(later):
    value = data()
    replacement = deepcopy(value["steps"][4])
    replacement["tool_calls"][0]["tool_call_id"] = "overwrite"
    replacement["observation"]["results"][0]["source_call_id"] = "overwrite"
    if later == "other_page":
        navigate = deepcopy(value["steps"][1])
        navigate["tool_calls"][0].update(
            tool_call_id="other-page", arguments={"url": "https://other.invalid/"}
        )
        navigate["observation"]["results"][0].update(
            source_call_id="other-page", content="- Page URL: https://other.invalid/"
        )
        value["steps"].insert(-1, navigate)
    elif later == "failed_save":
        replacement["observation"]["results"][0]["extra"]["status"] = "failed"
    else:
        replacement.pop("observation")
    value["steps"].insert(-1, replacement)
    result = assess(value)
    assert result[:2] == (True, False)
    assert len(result[2]["same_filename_screenshot_attempts"]) == 2


def test_two_trajectory_writers_have_no_implicit_global_screenshot_order():
    value, child = data(), data()
    child["trajectory_id"] = "browser-child"
    value["subagent_trajectories"] = [child]
    result = assess(value)
    assert result[:2] == (True, False)
    assert result[2]["screenshot_writer_order_ambiguous"]


def test_whole_child_workflow_is_usable_but_sibling_operations_are_not_joined():
    value, child = data(), data()
    child["trajectory_id"] = "browser-child"
    value["steps"] = [value["steps"][0], value["steps"][-1]]
    value["subagent_trajectories"] = [child]
    assert assess(value)[:2] == (True, True)
    sibling = deepcopy(child)
    sibling["trajectory_id"] = "browser-sibling"
    child["steps"] = child["steps"][:3]
    sibling["steps"] = sibling["steps"][3:]
    for number, step in enumerate(sibling["steps"], 1):
        step["step_id"] = number
    value["subagent_trajectories"].append(sibling)
    assert assess(value)[:2] == (False, False)


@pytest.mark.parametrize(
    "markup", ["`{url}`", "``{url}``", "[final URL]({url})", "{url}"]
)
def test_final_url_markdown_delimiters_do_not_change_trailing_empty_query_value(markup):
    value = data()
    url = FINAL_URL + "&my-hidden="
    value["steps"][3]["observation"]["results"][0]["content"] = json.dumps(
        {"message": "Received!", "url": url}
    )
    value["steps"][-1]["message"] = (
        f"Received! {markup.format(url=url)} web-form-submitted.png"
    )
    assert assess(value)[:2] == (True, True)


def test_markdown_url_with_a_real_different_query_value_still_fails():
    value = data()
    value["steps"][-1]["message"] = (
        f"Received! `{FINAL_URL}&my-hidden=changed` web-form-submitted.png"
    )
    assert assess(value)[:2] == (False, False)


def runtime(tmp_path, value=None, image="valid"):
    roots = {
        name: tmp_path / name
        for name in ("workdir", "agent_logs", "verifier_logs", "artifacts")
    }
    roots["artifacts"] = roots["artifacts"] / "logs/artifacts"
    for path in roots.values():
        path.mkdir(parents=True)
    declared_root = roots["artifacts"].parent.parent
    load_pbench_trajectory(FIXTURE, "Submit it", declared_root)
    if image == "header_only":
        (declared_root / "web-form-submitted.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    elif image == "missing":
        (declared_root / "web-form-submitted.png").unlink()
    (roots["agent_logs"] / "trajectory.json").write_text(
        history(value).model_dump_json(), encoding="utf-8"
    )
    return roots, EffectiveRuntimeConfig(
        paths=RuntimePaths(
            tests=str(TASK / "tests"), **{k: str(v) for k, v in roots.items()}
        ),
        verifier=VerifierInvocation(
            (TASK / "instruction.md").read_text(encoding="utf-8")
        ),
    )


@pytest.mark.parametrize(
    "image,answer,judge_pass,expected",
    [
        ("valid", None, True, 1),
        ("header_only", None, False, 0.4),
        ("missing", None, False, 0.4),
        ("valid", "", False, 0),
        ("valid", None, False, 0.6),
    ],
)
def test_public_verifier_uses_real_png_and_sends_same_observations_and_answer_to_judge(
    tmp_path, image, answer, judge_pass, expected
):
    pytest.importorskip("PIL.Image")
    value = data()
    if answer is not None:
        value["steps"][-1]["message"] = answer
    roots, effective = runtime(tmp_path, value, image)
    with judge_server() as server:
        server["behavior"] = {"faithful_browser_report": {"passed": judge_pass}}
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=effective,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
    assert result["reward"] == pytest.approx(expected)
    assert len(server["requests"]) == (0 if answer == "" else 1)
    prompt = ""
    if server["requests"]:
        prompt = server["requests"][0]["messages"][-1]["content"]
        for artifact in ("browser_observations", "screenshot_facts", "final_answer"):
            text = (roots["verifier_logs"] / f"artifact_text/{artifact}.md").read_text(
                encoding="utf-8"
            )
            assert escape(text, quote=False) in prompt
        assert "browser-3" in prompt and "browser-4" in prompt
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    records = {item["id"]: item for item in manifest["artifacts"]}
    assert (
        records["browser_observations"]["source_artifact_id"] == "retained_trajectory"
    )
    assert records["final_answer"]["source_artifact_id"] == "retained_trajectory"
    if image == "valid":
        assert records["screenshot_facts"]["source_artifact_id"] == "screenshot"
        assert records["screenshot"]["bytes"] > 8
        if prompt:
            assert "160 x 90" in prompt


def test_missing_trajectory_diagnoses_retention_without_claiming_tool_unavailability(
    tmp_path,
):
    pytest.importorskip("PIL.Image")
    roots, effective = runtime(tmp_path)
    (roots["agent_logs"] / "trajectory.json").unlink()
    result = asyncio.run(run_verifier(TASK / "tests/grader.json", runtime=effective))
    assert result["reward"] == 0
    evidence = (
        roots["verifier_logs"] / "artifact_text/browser_observations.md"
    ).read_text(encoding="utf-8")
    assert "missing trajectory" in evidence


@pytest.mark.parametrize("suffix", ["artifacts", "logs", "other/artifacts"])
def test_undeclared_runtime_layout_is_a_configuration_error(tmp_path, suffix):
    with pytest.raises(ValueError, match="Native Host"):
        GRADER["retained_screenshot"](tmp_path / suffix)


def test_harbor_collection_mapping_roundtrip_reaches_the_single_declared_png_and_judge(
    tmp_path,
):
    pytest.importorskip("PIL.Image")
    roots, effective = runtime(tmp_path, image="missing")
    load_pbench_trajectory(FIXTURE, "Submit it", roots["workdir"])
    source = roots["workdir"] / "web-form-submitted.png"
    source_bytes = source.read_bytes()
    retained_base = roots["artifacts"].parent.parent
    task = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert artifact_host_path(retained_base, task.config.artifacts[0]) == GRADER[
        "retained_screenshot"
    ](roots["artifacts"])

    class MountedAgentFiles:
        capabilities = SimpleNamespace(mounted=True)

        async def service_is_dir(self, path, **kwargs):
            return False

        async def service_download_file(self, *, source_path, target_path, **kwargs):
            assert source_path == "web-form-submitted.png"
            shutil.copyfile(roots["workdir"] / source_path, target_path)

    handler = ArtifactHandler(
        artifacts=task.config.artifacts, logger=logging.getLogger(__name__)
    )
    manifest = asyncio.run(
        handler.download_artifacts(
            MountedAgentFiles(), retained_base, source_artifacts_dir="/logs/artifacts"
        )
    )
    assert [(entry.destination, entry.status) for entry in manifest.entries] == [
        ("artifacts/logs/artifacts", "empty"),
        ("artifacts/web-form-submitted.png", "ok"),
    ]
    # Removing the original proves the grader reads the collected destination.
    source.unlink()
    with judge_server() as server:
        server["behavior"] = {"faithful_browser_report": {"passed": True}}
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=effective,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
    assert result["reward"] == 1
    assert len(server["requests"]) == 1
    assert (
        roots["verifier_logs"] / "raw_artifacts/screenshot.png"
    ).read_bytes() == source_bytes


def test_missing_declared_png_never_falls_back_to_workspace_or_convention_file(
    tmp_path,
):
    pytest.importorskip("PIL.Image")
    roots, effective = runtime(tmp_path, image="missing")
    for directory in (roots["workdir"], roots["artifacts"]):
        load_pbench_trajectory(FIXTURE, "Submit it", directory)
    result = asyncio.run(
        run_verifier(
            TASK / "tests/grader.json",
            runtime=effective,
            judge_settings=JudgeSettings(enabled=False),
        )
    )
    assert result["metadata"]["score_merge"]["rule_score"] == pytest.approx(2 / 3)
    facts = (roots["verifier_logs"] / "artifact_text/screenshot_facts.md").read_text(
        encoding="utf-8"
    )
    assert "Screenshot unavailable" in facts


def test_task_contract_declares_retained_output_timeout_and_atomic_scoring():
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    assert loaded.config.verifier.environment_mode == "shared"
    assert [(item.source, item.destination) for item in loaded.config.artifacts] == [
        ("web-form-submitted.png", "web-form-submitted.png")
    ]
    config = json.loads((TASK / "tests/grader.json").read_text())
    assert [item.id for item in build_scoring_plan(config).items] == [
        "custom:submitted_form",
        "custom:submitted_screenshot",
    ]
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert (judge.rule_weight, judge.llm_weight) == (0.6, 0.4)


@pytest.mark.parametrize(
    "error",
    [
        MissingDocumentDependency("install psycheval[image]"),
        DocumentLimitError("decoded pixel budget"),
    ],
)
def test_missing_image_dependency_and_inspection_budgets_remain_verifier_errors(
    tmp_path, monkeypatch, error
):
    roots, _ = runtime(tmp_path)
    context = tmp_path / "context.json"
    context.write_text(
        json.dumps({"paths": {key: str(value) for key, value in roots.items()}}),
        encoding="utf-8",
    )
    output = tmp_path / "output.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["test_outputs.py", "--context", str(context), "--output", str(output)],
    )

    def failing_inspection(*args, **kwargs):
        raise error

    monkeypatch.setitem(
        GRADER["main"].__globals__, "inspect_document", failing_inspection
    )
    with pytest.raises(
        type(error), match=str(error).replace("[", r"\[").replace("]", r"\]")
    ):
        GRADER["main"]()
    assert not output.exists()
