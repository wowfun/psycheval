"""Published Office score shape preserves generic verifier scoring semantics."""

from dataclasses import replace

import pytest

from psycheval.harbor.verifier._judge import merge_scores
from psycheval.harbor.verifier._judge_config import parse_judge_config
from psycheval.harbor.verifier._score import score_payload
from psycheval.harbor.verifier._scoring import (
    aggregate,
    build_scoring_plan,
    normalize_checks,
)
from tests.fixtures.judge_task import YAML

VERDICT_FIELDS = {
    "item_id",
    "status",
    "judge_name",
    "judge_type",
    "score",
    "evidence_ids",
    "reason",
    "confidence",
    "metadata",
}
GROUP_FIELDS = {
    "judge_name",
    "judge_type",
    "judge_family",
    "status",
    "ok",
    "verdicts",
    "scores",
    "evidence_ids",
    "errors",
    "metadata",
}


def publish(config=None, judge=None):
    plan = build_scoring_plan(
        {
            "custom_checks": ["pass", "fail", "missing"],
            "scoring": {
                "weights": {"custom:pass": 2, "custom:fail": 1, "custom:missing": 0}
            },
        }
    )
    checks = [
        {"id": "custom:fail", "passed": False, "evidence": "wrong value"},
        {"id": "custom:pass", "passed": True, "evidence": "confirmed"},
    ]
    judge = judge or {"status": "absent", "reason": "no judge.yaml", "checks": []}
    rewards, merge = merge_scores(aggregate(checks, plan=plan), config, judge)
    return score_payload(
        normalize_checks(checks, plan=plan), rewards, config, judge, merge
    )


def two_rubrics():
    config = parse_judge_config(YAML)
    return replace(
        config,
        rubrics=(*config.rubrics, replace(config.rubrics[0], id="quality")),
        rule_weight=2,
        llm_weight=1,
    )


def test_rule_score_schema_counts_order_and_precision():
    result = publish()
    assert set(result) == {
        "reward",
        "overall",
        "test_status",
        "test_pass_rate",
        "tests_passed",
        "tests_total",
        "verdicts",
        "judges",
        "diagnostics",
        "metadata",
    }
    assert result["reward"] == result["overall"] == 2 / 3
    assert result["test_pass_rate"] == 1 / 3
    assert result["tests_passed"] == 1 and result["tests_total"] == 3
    assert result["test_status"] == "partial_pass"
    assert len(result["judges"]) == 1
    group = result["judges"][0]
    assert group["scores"]["pass_rate"] == 1 / 3
    assert group["scores"]["overall"] == 2 / 3
    assert set(group) == GROUP_FIELDS
    assert group["status"] == "fail" and group["ok"]
    assert result["verdicts"] == group["verdicts"]
    assert [item["item_id"] for item in result["verdicts"]] == [
        "custom:pass",
        "custom:fail",
        "custom:missing",
    ]
    assert all(set(item) == VERDICT_FIELDS for item in result["verdicts"])
    missing = result["verdicts"][2]
    assert missing["metadata"] == {
        "dimension": "custom_outputs",
        "weight": 0,
        "missing": True,
    }
    assert (
        missing["score"] == 0 and missing["reason"] == "Declared check was not reported"
    )
    assert result["metadata"]["score_merge"] == {
        "method": "none",
        "applied": False,
        "reason": "no judge.yaml",
        "rule_score": 2 / 3,
        "overall": 2 / 3,
    }


def test_completed_judge_preserves_individual_results_and_nonunit_merge():
    result = publish(
        two_rubrics(),
        {
            "status": "complete",
            "reason": "done",
            "elapsed_sec": 0.123,
            "checks": [
                {
                    "id": "quality",
                    "passed": False,
                    "reason": "missing evidence",
                    "missing": ["report"],
                },
                {"id": "fidelity", "passed": True, "reason": "忠实"},
            ],
        },
    )
    expected = (2 * (2 / 3) + 0.5) / 3
    assert result["reward"] == expected
    assert result["test_pass_rate"] == 1 / 3
    assert result["llm_judge_component_score"] == 0.5
    assert result["verdicts"] == [
        item for group in result["judges"] for item in group["verdicts"]
    ]
    group = result["judges"][1]
    assert set(group) == GROUP_FIELDS
    assert group["status"] == "pass" and group["ok"]
    assert group["judge_family"] == "llm"
    assert group["evidence_ids"] == ["report"]
    first, second = group["verdicts"]
    assert first["item_id"] == "llm:fidelity" and first["status"] == "pass"
    assert first["metadata"]["rubric"]["id"] == "fidelity"
    assert second["item_id"] == "llm:quality" and second["status"] == "fail"
    assert second["metadata"]["missing"] == ["report"]
    merge = result["metadata"]["score_merge"]
    assert merge["applied"] and merge["rule_weight"] == 2 and merge["llm_weight"] == 1
    assert merge["overall"] == expected and merge["llm_score"] == 0.5
    assert result["diagnostics"]["status_counts"] == {
        "pass": 2,
        "fail": 3,
        "review": 0,
        "abstain": 0,
        "build_error": 0,
        "judge_error": 0,
    }


def test_status_follows_final_office_reward_even_when_rule_rate_is_below_one():
    config = replace(two_rubrics(), rule_weight=0, llm_weight=1)
    result = publish(
        config,
        {
            "status": "complete",
            "reason": "done",
            "checks": [
                {"id": name, "passed": True, "reason": "confirmed"}
                for name in ("fidelity", "quality")
            ],
        },
    )
    assert result["test_status"] == "full_pass"
    assert result["test_pass_rate"] == 1 / 3
    assert result["reward"] == 1


@pytest.mark.parametrize("status", ["disabled", "incomplete"])
def test_unavailable_judge_abstains_without_losing_completed_verdicts(status):
    checks = (
        [{"id": "quality", "passed": True, "reason": "completed"}]
        if status == "incomplete"
        else []
    )
    result = publish(
        two_rubrics(),
        {
            "status": status,
            "reason": "not completed",
            "checks": checks,
            "errors": {"fidelity": "request timed out"} if checks else {},
        },
    )
    assert result["reward"] == 2 / 3
    assert "llm_judge_component_score" not in result
    assert not result["metadata"]["score_merge"]["applied"]
    assert "llm_score" not in result["metadata"]["score_merge"]
    group = result["judges"][1]
    assert group["status"] == "abstain" and group["ok"]
    assert group["scores"] == {}
    first, second = group["verdicts"]
    assert first["status"] == "abstain" and first["score"] is None
    assert first["reason"] == ("request timed out" if checks else "not completed")
    assert second["status"] == ("pass" if checks else "abstain")
    assert second["score"] == (1 if checks else None)
