from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from harbor.models.trajectories import Trajectory

from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    write_effective_runtime_config,
)
from psycheval.harbor.verifier import aggregate, evaluate
from tests.fixtures import load_pbench_trajectory as _fixture_trajectory

_FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "pbench"
_WEB_SEARCH_FIXTURE = _FIXTURES_ROOT / "web-search-01"
_WEB_FETCH_FIXTURE = _FIXTURES_ROOT / "web-fetch-01"
_BROWSER_CONTROL_FIXTURE = _FIXTURES_ROOT / "browser-control-01"


def test_grader_requires_outcome_and_structured_tool_evidence(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_WEB_FETCH_FIXTURE, "Fetch it", tmp_path)
    )
    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(
                    _branch(
                        "web_fetch",
                        "webfetch",
                        argument_url="https://www.iana.org/help/example-domains",
                        observation_terms=["2017-05-13"],
                    )
                )
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
    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(
                    _branch(
                        "web_fetch",
                        "webfetch",
                        argument_url="https://www.iana.org/help/example-domains",
                        observation_terms=["2017-05-13"],
                    )
                )
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
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    (tmp_path / "web-form-submitted.png").unlink()
    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(
                    _branch(
                        "browser_click",
                        argument_terms=["button"],
                        observation_terms=["received!"],
                    )
                )
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
    value = _fixture_trajectory(_WEB_SEARCH_FIXTURE, "Search it", tmp_path)
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
    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(
                    _branch(
                        "web_search", "websearch", observation_terms=["example.com"]
                    )
                )
            ],
            "forbidden_tool_names": ["web_fetch", "webfetch"],
            "final_terms": ["example.com"],
        },
        tmp_path,
    )
    forbidden = next(check for check in checks if check["id"] == "forbidden_tools")
    assert forbidden == {
        "id": "forbidden_tools",
        "dimension": "forbidden_tools",
        "passed": False,
        "evidence": "called: web_fetch",
    }


def test_exact_forbidden_tool_names_do_not_use_fuzzy_matching(tmp_path: Path) -> None:
    value = _fixture_trajectory(_WEB_SEARCH_FIXTURE, "Search it", tmp_path)
    value["steps"].insert(
        2,
        {
            "step_id": 3,
            "source": "agent",
            "message": "",
            "tool_calls": [
                {
                    "tool_call_id": "unrelated-1",
                    "function_name": "custom_web_fetch_helper",
                    "arguments": {},
                }
            ],
        },
    )
    for index, step in enumerate(value["steps"], start=1):
        step["step_id"] = index

    checks = evaluate(
        Trajectory(**value),
        {
            "required_calls": [
                _required_call(
                    _branch(
                        "web_search", observation_terms=["example.com", "example.org"]
                    )
                )
            ],
            "forbidden_tool_names": ["web_fetch", "webfetch"],
            "final_terms": ["example.com", "example.org"],
        },
        tmp_path,
    )

    forbidden = next(check for check in checks if check["id"] == "forbidden_tools")
    assert forbidden["passed"] is True


def test_tool_name_globs_apply_to_required_and_forbidden_calls(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_WEB_FETCH_FIXTURE, "Fetch it", tmp_path)
    )

    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(
                    _branch(
                        "web_*",
                        argument_url="https://www.iana.org/help/example-domains",
                        observation_terms=["2017-05-13"],
                    )
                )
            ],
            "forbidden_tool_names": ["*fetch"],
            "final_terms": ["2017-05-13"],
        },
        tmp_path,
    )
    by_id = {check["id"]: check for check in checks}

    assert by_id["required_call_1_tool"]["passed"] is True
    assert by_id["forbidden_tools"] == {
        "id": "forbidden_tools",
        "dimension": "forbidden_tools",
        "passed": False,
        "evidence": "called: web_fetch",
    }


def test_tool_name_globs_are_case_sensitive(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_WEB_FETCH_FIXTURE, "Fetch it", tmp_path)
    )

    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(_branch("WEB_*", observation_terms=["2017-05-13"]))
            ],
            "final_terms": ["2017-05-13"],
        },
        tmp_path,
    )

    assert (
        next(check for check in checks if check["id"] == "required_call_1_tool")[
            "passed"
        ]
        is False
    )


def test_skill_name_in_successful_shell_call_arguments_is_required(
    tmp_path: Path,
) -> None:
    trajectory = Trajectory(
        schema_version="ATIF-v1.7",
        trajectory_id="skill-call",
        agent={"name": "fixture", "version": "1"},
        steps=[
            {"step_id": 1, "source": "user", "message": "Run the skill"},
            _step_with_call(
                2,
                "skill-1",
                "agent_exec_command",
                {"cmd": ["python", "/app/skills/x-daily/scripts/fetch.py"]},
                "completed",
            ),
            {"step_id": 3, "source": "agent", "message": "done"},
        ],
    )
    config = {
        "required_calls": [
            _required_call(
                _branch(
                    "*exec*",
                    "*terminal*",
                    "*shell*",
                    "bash",
                    argument_terms=["x-daily"],
                )
            )
        ],
        "final_terms": ["done"],
    }

    assert all(check["passed"] for check in evaluate(trajectory, config, tmp_path))

    trajectory.steps[1].tool_calls[0].arguments = {"cmd": "python fetch.py"}
    trajectory.steps[1].observation.results[0].content = "x-daily completed"
    trajectory.steps[2].message = "x-daily done"
    checks = evaluate(trajectory, config, tmp_path)
    assert (
        next(check for check in checks if check["id"] == "required_call_1_arguments")[
            "passed"
        ]
        is False
    )


def test_nonzero_exit_code_is_not_a_successful_observation(tmp_path: Path) -> None:
    trajectory = Trajectory(
        schema_version="ATIF-v1.7",
        trajectory_id="failed-skill-call",
        agent={"name": "fixture", "version": "1"},
        steps=[
            {"step_id": 1, "source": "user", "message": "Run the skill"},
            _step_with_call(
                2,
                "skill-1",
                "exec_command",
                {"cmd": "/app/skills/x-daily/scripts/fetch.py"},
                "failed",
            ),
            {"step_id": 3, "source": "agent", "message": "done"},
        ],
    )
    trajectory.steps[1].observation.results[0].extra["exit_code"] = 2

    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(_branch("*exec*", argument_terms=["x-daily"]))
            ],
            "final_terms": ["done"],
        },
        tmp_path,
    )

    assert (
        next(check for check in checks if check["id"] == "required_call_1_observation")[
            "passed"
        ]
        is False
    )


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
    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(
                    _branch(
                        "web_fetch",
                        "webfetch",
                        argument_url="https://right.example/page",
                        observation_terms=["expected evidence"],
                    )
                )
            ],
            "final_terms": ["expected evidence"],
        },
        tmp_path,
    )
    by_id = {check["id"]: check["passed"] for check in checks}
    assert by_id["required_call_1_arguments"] is True
    assert by_id["required_call_1_observation"] is False


def test_browser_input_is_required_before_submit(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    trajectory.steps = [
        step
        for step in trajectory.steps
        if not (step.tool_calls and step.tool_calls[0].function_name == "browser_type")
    ]
    checks = evaluate(trajectory, _browser_config(), tmp_path)
    by_id = {check["id"]: check["passed"] for check in checks}
    assert by_id["required_call_1_tool"] is False


def test_ordered_rules_use_the_earliest_complete_branch_witness(
    tmp_path: Path,
) -> None:
    trajectory = Trajectory(
        schema_version="ATIF-v1.7",
        trajectory_id="earliest-ordered-witness",
        agent={"name": "fixture", "version": "1"},
        steps=[
            {"step_id": 1, "source": "user", "message": "Act in order"},
            _step_with_call(2, "first-a", "tool_a", {}, "first complete"),
            _step_with_call(3, "middle-b", "tool_b", {}, "second complete"),
            _step_with_call(4, "later-a", "tool_a_alias", {}, "first complete"),
            {"step_id": 5, "source": "agent", "message": "done"},
        ],
    )

    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(
                    _branch("tool_a", observation_terms=["first complete"]),
                    _branch("tool_a_alias", observation_terms=["first complete"]),
                ),
                _required_call(
                    _branch("tool_b", observation_terms=["second complete"])
                ),
            ],
            "final_terms": ["done"],
        },
        tmp_path,
    )

    assert all(check["passed"] for check in checks), checks


def test_browser_input_text_must_match_exactly(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    type_call = next(
        step.tool_calls[0]
        for step in trajectory.steps
        if step.tool_calls and step.tool_calls[0].function_name == "browser_type"
    )
    type_call.arguments["text"] = "Harbor eval with extra text"
    checks = evaluate(trajectory, _browser_config(), tmp_path)
    by_id = {check["id"]: check["passed"] for check in checks}
    assert by_id["required_call_1_arguments"] is False


@pytest.mark.parametrize("tool_name", ["web_fetch", "webfetch"])
def test_each_explicit_fetch_alias_is_a_complete_valid_branch(
    tmp_path: Path, tool_name: str
) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_WEB_FETCH_FIXTURE, "Fetch it", tmp_path)
    )
    trajectory.steps[1].tool_calls[0].function_name = tool_name

    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(
                    _branch(
                        "web_fetch",
                        "webfetch",
                        argument_url="https://www.iana.org/help/example-domains",
                        observation_terms=["2017-05-13"],
                    )
                )
            ],
            "final_terms": ["2017-05-13"],
        },
        tmp_path,
    )

    assert all(check["passed"] for check in checks), checks


def test_alias_branches_cannot_combine_arguments_and_observations(
    tmp_path: Path,
) -> None:
    trajectory = Trajectory(
        schema_version="ATIF-v1.7",
        trajectory_id="split-alias-branches",
        agent={"name": "fixture", "version": "1"},
        steps=[
            {"step_id": 1, "source": "user", "message": "Fetch it"},
            _step_with_call(
                2,
                "canonical-right-args",
                "web_fetch",
                {"url": "https://right.example/page"},
                "unrelated response",
            ),
            _step_with_call(
                3,
                "compact-wrong-args",
                "webfetch",
                {"url": "https://wrong.example/page"},
                "expected evidence",
            ),
            {"step_id": 4, "source": "agent", "message": "expected evidence"},
        ],
    )

    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                {
                    "any": [
                        _branch(
                            "web_fetch",
                            argument_url="https://right.example/page",
                            observation_terms=["expected evidence"],
                        ),
                        _branch(
                            "webfetch",
                            argument_url="https://right.example/page",
                            observation_terms=["expected evidence"],
                        ),
                    ]
                }
            ],
            "final_terms": ["expected evidence"],
        },
        tmp_path,
    )

    by_id = {check["id"]: check["passed"] for check in checks}
    assert by_id["required_call_1_tool"] is True
    assert by_id["required_call_1_arguments"] is True
    assert by_id["required_call_1_observation"] is False


def test_browser_computer_action_branches_are_accepted(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    calls = [
        call
        for step in trajectory.steps
        for call in (step.tool_calls or [])
        if call.function_name in {"browser_type", "browser_click"}
    ]
    calls[0].function_name = "computer_action"
    calls[0].arguments = {
        "type": "type_text_at",
        "text": "Harbor eval",
        "coordinate": [100, 200],
    }
    calls[1].function_name = "computer_action"
    calls[1].arguments = {"type": "click", "coordinate": [100, 250]}

    checks = evaluate(trajectory, _browser_config(), tmp_path)

    assert all(check["passed"] for check in checks), checks


def test_reward_dimensions_are_binary_and_total_requires_every_check(
    tmp_path: Path,
) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_WEB_FETCH_FIXTURE, "Fetch it", tmp_path)
    )
    checks = evaluate(
        trajectory,
        {
            "required_calls": [
                _required_call(
                    _branch(
                        "web_fetch",
                        argument_url="https://wrong.example/page",
                        observation_terms=["2017-05-13"],
                    )
                )
            ],
            "final_terms": ["2017-05-13"],
        },
        tmp_path,
    )

    assert aggregate(checks) == {
        "reward": 0,
        "required_tool": 1,
        "required_arguments": 0,
        "required_observation": 0,
        "forbidden_tools": 1,
        "final_answer": 1,
        "required_artifacts": 1,
    }


@pytest.mark.parametrize(
    "relative",
    [
        "/etc/passwd",
        "../outside.png",
        "nested\\outside.png",
        "C:/outside.png",
        "",
        ".",
    ],
)
def test_artifact_config_rejects_paths_outside_the_artifact_root(
    tmp_path: Path, relative: str
) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    config = _browser_config()
    config["required_artifacts"] = [relative]
    with pytest.raises(ValueError, match="relative POSIX glob below the artifact root"):
        evaluate(trajectory, config, tmp_path)


def test_required_artifact_glob_requires_every_match_in_final_answer(
    tmp_path: Path,
) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    second = tmp_path / "browser-console.txt"
    second.write_text("console output", encoding="utf-8")
    trajectory.steps[
        -1
    ].message = "Received! submitted-form.html web-form-submitted.png"
    config = _browser_config()
    config["required_artifacts"] = ["web-form-submitted.png", "browser-*.txt"]

    checks = evaluate(trajectory, config, tmp_path)
    by_id = {check["id"]: check for check in checks}

    assert by_id["required_artifacts"]["passed"] is True
    assert by_id["final_answer"]["passed"] is False
    assert "browser-console.txt" in by_id["final_answer"]["evidence"]

    trajectory.steps[-1].message += " browser-console.txt"
    checks = evaluate(trajectory, config, tmp_path)
    assert all(check["passed"] for check in checks), checks


def test_required_artifact_path_does_not_match_inside_a_longer_path(
    tmp_path: Path,
) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    (tmp_path / "a.md").write_text("artifact", encoding="utf-8")
    trajectory.steps[-1].message = "created data.md"

    checks = evaluate(trajectory, {"required_artifacts": ["a.md"]}, tmp_path)
    by_id = {check["id"]: check for check in checks}

    assert by_id["required_artifacts"]["passed"] is True
    assert by_id["final_answer"]["passed"] is False
    assert "a.md" in by_id["final_answer"]["evidence"]


def test_required_artifact_glob_must_match_at_least_one_file(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    config = _browser_config()
    config["required_artifacts"] = ["missing-*.png"]

    checks = evaluate(trajectory, config, tmp_path)
    by_id = {check["id"]: check for check in checks}

    assert by_id["required_artifacts"]["passed"] is False
    assert "matched no artifacts" in by_id["required_artifacts"]["evidence"]


def test_outcome_only_configuration_does_not_require_call_rules(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )

    checks = evaluate(
        trajectory,
        {"required_artifacts": ["web-form-submitted.png"]},
        tmp_path,
    )

    assert {check["id"] for check in checks} == {
        "final_answer",
        "required_artifacts",
    }
    assert all(check["passed"] for check in checks)


def test_empty_configuration_is_rejected(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_WEB_SEARCH_FIXTURE, "Search it", tmp_path)
    )

    with pytest.raises(ValueError, match="at least one non-empty constraint"):
        evaluate(trajectory, {}, tmp_path)


def test_final_answer_uses_only_the_last_nonempty_agent_message(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    trajectory.steps.append(
        trajectory.steps[-1].model_copy(
            update={
                "step_id": 6,
                "message": "Received! submitted-form.html",
            }
        )
    )

    checks = evaluate(trajectory, _browser_config(), tmp_path)
    by_id = {check["id"]: check for check in checks}

    assert by_id["required_artifacts"]["passed"] is True
    assert by_id["final_answer"]["passed"] is False


@pytest.mark.parametrize(
    ("relative", "payload"),
    [("empty.png", b""), ("not-a-png.png", b"plain text")],
)
def test_artifact_must_be_nonempty_and_match_its_file_type(
    tmp_path: Path, relative: str, payload: bytes
) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    (tmp_path / relative).write_bytes(payload)
    config = _browser_config()
    config["required_artifacts"] = [relative]
    checks = evaluate(trajectory, config, tmp_path)
    artifact_check = next(
        check for check in checks if check["id"] == "required_artifacts"
    )
    assert artifact_check["passed"] is False


def test_artifact_symlink_is_not_accepted(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_BROWSER_CONTROL_FIXTURE, "Submit it", tmp_path)
    )
    try:
        (tmp_path / "linked.png").symlink_to(tmp_path / "web-form-submitted.png")
    except OSError as exc:
        pytest.skip(f"host does not permit symlink creation: {exc}")
    config = _browser_config()
    config["required_artifacts"] = ["linked.png"]
    checks = evaluate(trajectory, config, tmp_path)
    artifact_check = next(
        check for check in checks if check["id"] == "required_artifacts"
    )
    assert artifact_check["passed"] is False


def test_grader_error_does_not_manufacture_a_reward(tmp_path: Path) -> None:
    agent_logs = tmp_path / "agent"
    verifier_logs = tmp_path / "verifier"
    artifacts = tmp_path / "artifacts"
    agent_logs.mkdir()
    artifacts.mkdir()
    (agent_logs / "trajectory.json").write_text(
        json.dumps(_fixture_trajectory(_WEB_SEARCH_FIXTURE, "Search it", artifacts)),
        encoding="utf-8",
    )
    config = tmp_path / "broken-grader.json"
    config.write_text("{}", encoding="utf-8")
    completed = _run_cli(config, agent_logs, verifier_logs, artifacts)

    assert completed.returncode != 0
    assert "at least one non-empty constraint" in completed.stderr
    assert not (verifier_logs / "reward.json").exists()


def test_legacy_or_unknown_config_fields_are_rejected(tmp_path: Path) -> None:
    trajectory = Trajectory(
        **_fixture_trajectory(_WEB_SEARCH_FIXTURE, "Search it", tmp_path)
    )
    with pytest.raises(ValueError, match="unsupported fields: forbidden_tools"):
        evaluate(
            trajectory,
            {
                "required_calls": [
                    _required_call(
                        _branch("web_search", observation_terms=["example.com"])
                    )
                ],
                "forbidden_tools": ["web_fetch"],
                "final_terms": ["example.com"],
            },
            tmp_path,
        )


def test_module_cli_writes_total_and_dimension_rewards(tmp_path: Path) -> None:
    agent_logs = tmp_path / "agent"
    verifier_logs = tmp_path / "verifier"
    artifacts = tmp_path / "artifacts"
    agent_logs.mkdir()
    artifacts.mkdir()
    (agent_logs / "trajectory.json").write_text(
        json.dumps(_fixture_trajectory(_WEB_SEARCH_FIXTURE, "Search it", artifacts)),
        encoding="utf-8",
    )
    config = tmp_path / "grader.json"
    config.write_text(
        json.dumps(
            {
                "required_calls": [
                    _required_call(
                        _branch(
                            "web_search",
                            "websearch",
                            argument_terms=["iana", "example domains"],
                            observation_terms=["example.com", "example.org"],
                        )
                    )
                ],
                "forbidden_tool_names": ["web_fetch", "webfetch"],
                "final_terms": ["example.com", "example.org"],
            }
        ),
        encoding="utf-8",
    )
    completed = _run_cli(config, agent_logs, verifier_logs, artifacts)

    assert completed.returncode == 0, completed.stdout + completed.stderr
    rewards = json.loads((verifier_logs / "reward.json").read_text(encoding="utf-8"))
    assert rewards == {
        "reward": 1,
        "required_tool": 1,
        "required_arguments": 1,
        "required_observation": 1,
        "forbidden_tools": 1,
        "final_answer": 1,
        "required_artifacts": 1,
    }


def test_module_cli_fails_fast_on_corrupt_effective_config(tmp_path: Path) -> None:
    config = tmp_path / "grader.json"
    config.write_text("{}\n", encoding="utf-8")
    runtime = tmp_path / "broken-peval.json"
    runtime.write_text("{not-json\n", encoding="utf-8")
    environment = os.environ.copy()
    environment["PEVAL_CONFIG"] = str(runtime)

    completed = subprocess.run(
        [sys.executable, "-m", "psycheval.harbor.verifier", str(config)],
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
        check=False,
    )

    assert completed.returncode != 0
    assert "failed to read effective PEVAL_CONFIG JSON" in completed.stderr


def _run_cli(
    config: Path, agent_logs: Path, verifier_logs: Path, artifacts: Path
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    runtime_path = write_effective_runtime_config(
        config.parent / "peval-runtime.json",
        EffectiveRuntimeConfig(
            paths=RuntimePaths(
                workdir=str(config.parent),
                tests=str(config.parent),
                agent_logs=str(agent_logs),
                verifier_logs=str(verifier_logs),
                artifacts=str(artifacts),
            )
        ),
    )
    environment["PEVAL_CONFIG"] = str(runtime_path)
    return subprocess.run(
        [sys.executable, "-m", "psycheval.harbor.verifier", str(config)],
        capture_output=True,
        text=True,
        env=environment,
        timeout=30,
        check=False,
    )


def _browser_config() -> dict:
    return {
        "required_calls": [
            {
                "any": [
                    _branch(
                        "browser_type",
                        argument_values={"text": "Harbor eval"},
                        observation_terms=["Harbor eval"],
                    ),
                    _branch(
                        "computer_action",
                        argument_values={
                            "type": "type_text_at",
                            "text": "Harbor eval",
                        },
                        observation_terms=["Harbor eval"],
                    ),
                ]
            },
            {
                "any": [
                    _branch(
                        "browser_click",
                        argument_terms=["button"],
                        observation_terms=["submitted-form.html", "received!"],
                    ),
                    _branch(
                        "computer_action",
                        argument_values={"type": "click"},
                        observation_terms=["submitted-form.html", "received!"],
                    ),
                ]
            },
        ],
        "final_terms": ["submitted-form.html", "received!"],
        "required_artifacts": ["web-form-submitted.png"],
    }


def _required_call(*branches: dict) -> dict:
    return {"any": list(branches)}


def _branch(*tool_names: str, **constraints) -> dict:
    return {"tool_names": list(tool_names), **constraints}


def _step_with_call(
    step_id: int,
    call_id: str,
    tool_name: str,
    arguments: dict,
    observation: str,
) -> dict:
    return {
        "step_id": step_id,
        "source": "agent",
        "message": "",
        "tool_calls": [
            {
                "tool_call_id": call_id,
                "function_name": tool_name,
                "arguments": arguments,
            }
        ],
        "observation": {
            "results": [
                {
                    "source_call_id": call_id,
                    "content": observation,
                    "extra": {"is_error": False, "status": "completed"},
                }
            ]
        },
    }
