from harbor.models.trajectories import Trajectory

from psycheval.harbor.family import retain
from psycheval.harbor.verifier import evaluate
from psycheval.harbor.verifier._calls import forbidden_tool_check


def body(identity, *names):
    return {
        "schema_version": "ATIF-v1.8",
        "trajectory_id": identity,
        "session_id": identity,
        "agent": {"name": "fixture", "version": "1"},
        "extra": {"tool_evidence": "complete"},
        "steps": [
            {
                "step_id": i + 1,
                "source": "agent",
                "message": "answer",
                "tool_calls": [
                    {"tool_call_id": str(i), "function_name": name, "arguments": {}}
                ],
                "observation": {
                    "results": [{"source_call_id": str(i), "content": "done"}]
                },
            }
            for i, name in enumerate(names)
        ],
    }


def test_matching_is_independent_of_sibling_enumeration(tmp_path):
    config = {
        "required_calls": [
            {"any": [{"tool_names": ["first"]}]},
            {"any": [{"tool_names": ["second"]}]},
        ]
    }
    a, b = body("a", "first"), body("b", "first", "second")
    outputs = []
    for children in ([a, b], [b, a]):
        root = body("root", "delegate")
        root["subagent_trajectories"] = children
        outputs.append(
            evaluate(Trajectory.model_validate(retain(root)), config, tmp_path)
        )
    assert outputs[0] == outputs[1]
    assert all(
        c["passed"] for c in outputs[0] if c["dimension"].startswith("required_")
    )
    root["subagent_trajectories"] = [body("a", "first"), body("b", "second")]
    checks = evaluate(Trajectory.model_validate(retain(root)), config, tmp_path)
    assert not next(c for c in checks if c["id"] == "required_call_2_tool")["passed"]


def test_dispatch_and_join_require_retained_activation_anchors(tmp_path):
    root = body("root", "delegate", "finish")
    root["subagent_trajectories"] = [body("child", "read")]
    config = {
        "required_calls": [
            {"any": [{"tool_names": [name]}]} for name in ("delegate", "read", "finish")
        ]
    }
    retain(
        root,
        activations=[
            {
                "parent_trajectory_id": "root",
                "child_trajectory_id": "child",
                "parent_call_id": "0",
                "first_call_id": "0",
                "last_call_id": "0",
                "joined_before_call_id": "1",
            }
        ],
    )
    checks = evaluate(Trajectory.model_validate(root), config, tmp_path)
    assert all(c["passed"] for c in checks if c["dimension"].startswith("required_"))
    root["extra"]["family"]["activations"][0].pop("joined_before_call_id")
    checks = evaluate(Trajectory.model_validate(root), config, tmp_path)
    assert not next(c for c in checks if c["id"] == "required_call_3_tool")["passed"]


def test_forbidden_absence_requires_selected_scope_completeness():
    root, child = body("root", "read"), body("child", "write")
    child["extra"]["tool_evidence"] = "unknown"
    root["subagent_trajectories"] = [child]
    model = Trajectory.model_validate(retain(root))
    assert not forbidden_tool_check(model, ["forbidden"])["passed"]
    assert forbidden_tool_check(model, ["forbidden"], "root")["passed"]
    assert not forbidden_tool_check(model, ["write"])["passed"]


def test_duplicate_call_identity_cannot_borrow_another_calls_result(tmp_path):
    root = body("root", "first", "second")
    root["steps"][1]["tool_calls"][0]["tool_call_id"] = "0"
    root["steps"][1]["observation"]["results"][0]["source_call_id"] = "0"
    model = Trajectory.model_validate(root)
    checks = evaluate(
        model,
        {
            "required_calls": [{"any": [{"tool_names": ["first"]}]}],
            "forbidden_tool_names": ["third"],
        },
        tmp_path,
    )
    assert all(
        not c["passed"] and "duplicate" in c["evidence"]
        for c in checks
        if c["dimension"] != "final_answer"
    )
    assert next(c for c in checks if c["id"] == "final_answer")["passed"]
    from psycheval.harbor.verifier import ObservationIndex

    index = ObservationIndex(model)
    assert index.matching({"any": [{"tool_names": ["first"]}]}) == []
    assert "duplicate" in index.evidence_error


def test_cyclic_execution_evidence_is_scored_incomplete(tmp_path):
    root = body("root", "delegate")
    root["subagent_trajectories"] = [body("child", "read")]
    retain(
        root,
        activations=[
            {
                "parent_trajectory_id": "root",
                "child_trajectory_id": "child",
                "parent_call_id": "0",
                "first_call_id": "0",
                "last_call_id": "0",
                "joined_before_call_id": "0",
            }
        ],
    )
    checks = evaluate(
        Trajectory.model_validate(root),
        {"required_calls": [{"any": [{"tool_names": ["read"]}]}]},
        tmp_path,
    )
    assert all(
        not c["passed"] and "cyclic" in c["evidence"]
        for c in checks
        if c["id"].startswith("required_call")
    )


def test_matching_capacity_does_not_turn_evidence_into_verifier_error(
    tmp_path, monkeypatch
):
    from psycheval.harbor.verifier import _calls

    monkeypatch.setattr(_calls, "MAX_MATCH_OPERATIONS", 0)
    checks = evaluate(
        Trajectory.model_validate(body("root", "read")),
        {"required_calls": [{"any": [{"tool_names": ["read"]}]}]},
        tmp_path,
    )
    assert all(
        not c["passed"] and "capacity" in c["evidence"]
        for c in checks
        if c["id"].startswith("required_call")
    )


def test_long_causal_chain_does_not_exhaust_matching_capacity():
    from psycheval.harbor.verifier._calls import required_call_checks

    root = body("root", *(["exec"] * 1001))
    checks = required_call_checks(
        Trajectory.model_validate(root),
        [{"any": [{"tool_names": ["exec"]}]}] * 3,
    )
    assert all(check["passed"] for check in checks)
