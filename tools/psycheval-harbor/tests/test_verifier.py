from __future__ import annotations

import json
from pathlib import Path

import pytest
from harbor.models.trajectories import Trajectory
from psycheval_harbor.canned_harness import _trajectory
from psycheval_harbor.verifier import grade, main


def test_grader_requires_outcome_and_real_tool_evidence(tmp_path: Path) -> None:
    trajectory = Trajectory(**_trajectory("web-fetch", "Fetch it", tmp_path))
    checks = grade(
        trajectory,
        {
            "required_calls": [
                {
                    "tool": "web_fetch",
                    "argument_url": "https://www.iana.org/help/example-domains",
                    "observation_terms": ["2017-05-13"],
                }
            ],
            "final_terms": ["2017-05-13", "iana.org"],
        },
        tmp_path,
    )
    assert all(check["passed"] for check in checks)


def test_final_prose_cannot_replace_missing_tool_call(tmp_path: Path) -> None:
    trajectory = Trajectory(
        schema_version="ATIF-v1.7",
        trajectory_id="no-tool",
        agent={"name": "fixture", "version": "1"},
        steps=[
            {"step_id": 1, "source": "user", "message": "Fetch it"},
            {
                "step_id": 2,
                "source": "agent",
                "message": "2017-05-13 https://www.iana.org/help/example-domains",
            },
        ],
    )
    checks = grade(
        trajectory,
        {
            "required_calls": [
                {
                    "tool": "web_fetch",
                    "argument_url": "https://www.iana.org/help/example-domains",
                    "observation_terms": ["2017-05-13"],
                }
            ],
            "final_terms": ["2017-05-13", "iana.org"],
        },
        tmp_path,
    )
    by_id = {check["id"]: check["passed"] for check in checks}
    assert by_id["final_answer"] is True
    assert by_id["required_call_1_tool"] is False
    assert by_id["required_call_1_observation"] is False


def test_browser_artifact_is_required(tmp_path: Path) -> None:
    trajectory = Trajectory(**_trajectory("browser-control", "Submit it", tmp_path))
    (tmp_path / "web-form-submitted.png").unlink()
    checks = grade(
        trajectory,
        {
            "required_calls": [
                {
                    "tool": "browser_click",
                    "argument_terms": ["button"],
                    "observation_terms": ["received!"],
                }
            ],
            "final_terms": ["received!"],
            "required_artifacts": ["web-form-submitted.png"],
        },
        tmp_path,
    )
    assert (
        next(check for check in checks if check["id"] == "required_artifacts")["passed"]
        is False
    )


def test_forbidden_tool_is_a_normal_failed_check(tmp_path: Path) -> None:
    value = _trajectory("web-search", "Search it", tmp_path)
    value["steps"].insert(
        2,
        {
            "step_id": 3,
            "source": "agent",
            "message": "",
            "tool_calls": [
                {
                    "tool_call_id": "fetch-1",
                    "function_name": "web_fetch",
                    "arguments": {"url": "https://www.iana.org/help/example-domains"},
                }
            ],
        },
    )
    for index, step in enumerate(value["steps"], start=1):
        step["step_id"] = index
    trajectory = Trajectory(**value)
    checks = grade(
        trajectory,
        {
            "required_calls": [
                {"tool": "web_search", "observation_terms": ["example.com"]}
            ],
            "forbidden_tools": ["web_fetch"],
            "final_terms": ["example.com"],
        },
        tmp_path,
    )
    forbidden = next(check for check in checks if check["id"] == "forbidden_tools")
    assert forbidden == {
        "id": "forbidden_tools",
        "passed": False,
        "evidence": "called: web_fetch",
    }


def test_arguments_and_observation_must_belong_to_the_same_call(
    tmp_path: Path,
) -> None:
    trajectory = Trajectory(
        schema_version="ATIF-v1.7",
        trajectory_id="split-evidence",
        agent={"name": "fixture", "version": "1"},
        steps=[
            {"step_id": 1, "source": "user", "message": "Fetch it"},
            {
                "step_id": 2,
                "source": "agent",
                "message": "",
                "tool_calls": [
                    {
                        "tool_call_id": "right-url-failed",
                        "function_name": "web_fetch",
                        "arguments": {"url": "https://right.example/page"},
                    }
                ],
                "observation": {
                    "results": [
                        {
                            "source_call_id": "right-url-failed",
                            "content": "request failed",
                            "extra": {"is_error": True},
                        }
                    ]
                },
            },
            {
                "step_id": 3,
                "source": "agent",
                "message": "",
                "tool_calls": [
                    {
                        "tool_call_id": "wrong-url-succeeded",
                        "function_name": "web_fetch",
                        "arguments": {"url": "https://wrong.example/page"},
                    }
                ],
                "observation": {
                    "results": [
                        {
                            "source_call_id": "wrong-url-succeeded",
                            "content": "expected evidence",
                            "extra": {"is_error": False},
                        }
                    ]
                },
            },
            {"step_id": 4, "source": "agent", "message": "expected evidence"},
        ],
    )
    checks = grade(
        trajectory,
        {
            "required_calls": [
                {
                    "tool": "web_fetch",
                    "argument_url": "https://right.example/page",
                    "observation_terms": ["expected evidence"],
                }
            ],
            "final_terms": ["expected evidence"],
        },
        tmp_path,
    )
    by_id = {check["id"]: check["passed"] for check in checks}
    assert by_id["required_call_1_arguments"] is True
    assert by_id["required_call_1_observation"] is False


def test_browser_input_is_required_before_submit(tmp_path: Path) -> None:
    trajectory = Trajectory(**_trajectory("browser-control", "Submit it", tmp_path))
    trajectory.steps = [
        step
        for step in trajectory.steps
        if not (step.tool_calls and step.tool_calls[0].function_name == "browser_type")
    ]
    checks = grade(trajectory, _browser_config(), tmp_path)
    by_id = {check["id"]: check["passed"] for check in checks}
    assert by_id["required_call_1_tool"] is False


def test_browser_input_text_must_match_exactly(tmp_path: Path) -> None:
    trajectory = Trajectory(**_trajectory("browser-control", "Submit it", tmp_path))
    type_call = next(
        step.tool_calls[0]
        for step in trajectory.steps
        if step.tool_calls and step.tool_calls[0].function_name == "browser_type"
    )
    type_call.arguments["text"] = "Harbor eval with extra text"
    checks = grade(trajectory, _browser_config(), tmp_path)
    by_id = {check["id"]: check["passed"] for check in checks}
    assert by_id["required_call_1_arguments"] is False


@pytest.mark.parametrize("relative", ["/etc/passwd", "../outside.png"])
def test_artifact_config_rejects_paths_outside_the_artifact_root(
    tmp_path: Path, relative: str
) -> None:
    trajectory = Trajectory(**_trajectory("browser-control", "Submit it", tmp_path))
    config = _browser_config()
    config["required_artifacts"] = [relative]
    with pytest.raises(ValueError, match="relative path below the artifact root"):
        grade(trajectory, config, tmp_path)


@pytest.mark.parametrize(
    ("relative", "payload"),
    [("empty.png", b""), ("not-a-png.png", b"plain text")],
)
def test_artifact_must_be_nonempty_and_match_its_file_type(
    tmp_path: Path, relative: str, payload: bytes
) -> None:
    trajectory = Trajectory(**_trajectory("browser-control", "Submit it", tmp_path))
    (tmp_path / relative).write_bytes(payload)
    config = _browser_config()
    config["required_artifacts"] = [relative]
    checks = grade(trajectory, config, tmp_path)
    artifact_check = next(
        check for check in checks if check["id"] == "required_artifacts"
    )
    assert artifact_check["passed"] is False


def test_artifact_symlink_is_not_accepted(tmp_path: Path) -> None:
    trajectory = Trajectory(**_trajectory("browser-control", "Submit it", tmp_path))
    (tmp_path / "linked.png").symlink_to(tmp_path / "web-form-submitted.png")
    config = _browser_config()
    config["required_artifacts"] = ["linked.png"]
    checks = grade(trajectory, config, tmp_path)
    artifact_check = next(
        check for check in checks if check["id"] == "required_artifacts"
    )
    assert artifact_check["passed"] is False


def test_grader_error_does_not_manufacture_a_reward(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent_logs = tmp_path / "agent"
    verifier_logs = tmp_path / "verifier"
    artifacts = tmp_path / "artifacts"
    agent_logs.mkdir()
    artifacts.mkdir()
    (agent_logs / "trajectory.json").write_text(
        json.dumps(_trajectory("web-search", "Search it", artifacts)),
        encoding="utf-8",
    )
    config = tmp_path / "broken-grader.json"
    config.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("PSYCHEVAL_AGENT_LOGS_DIR", str(agent_logs))
    monkeypatch.setenv("PSYCHEVAL_VERIFIER_LOGS_DIR", str(verifier_logs))
    monkeypatch.setenv("PSYCHEVAL_ARTIFACTS_DIR", str(artifacts))
    with pytest.raises(ValueError, match="required_calls"):
        main([str(config)])
    assert not (verifier_logs / "reward.json").exists()


def _browser_config() -> dict:
    return {
        "required_calls": [
            {
                "tool": "browser_type",
                "argument_values": {"text": "Harbor eval"},
                "observation_terms": ["Harbor eval"],
            },
            {
                "tool": "browser_click",
                "argument_terms": ["button"],
                "observation_terms": ["submitted-form.html", "received!"],
            },
        ],
        "final_terms": ["submitted-form.html", "received!"],
        "required_artifacts": ["web-form-submitted.png"],
    }
