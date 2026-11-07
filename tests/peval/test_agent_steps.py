from copy import deepcopy

import pytest

from psycheval.harbor.atif import agent_step_count
from psycheval.state.catalog_projection import catalog_summary


@pytest.mark.parametrize(
    "extra,expected",
    [
        ({}, 2),
        ({"total_turns": 9999}, 2),
        ({"total_agent_steps": 0, "total_turns": 9999}, 0),
        ({"total_agent_steps": 7}, 7),
        ({"total_agent_steps": 7.0}, 7),
        ({"total_agent_steps": 1.5}, None),
        ({"total_agent_steps": 2**53 - 1}, 2**53 - 1),
        ({"total_agent_steps": 2**53}, None),
        ({"total_agent_steps": 10**1000}, None),
        ({"total_agent_steps": None}, None),
        ({"total_agent_steps": True}, None),
        ({"total_agent_steps": -1}, None),
    ],
)
def test_agent_steps_ignores_retired_counter_without_mutating_evidence(extra, expected):
    trajectory = {
        "steps": [
            {"source": source} for source in ["user", "system", "agent", "agent"]
        ],
        "final_metrics": {"extra": extra},
    }
    original = deepcopy(trajectory)
    assert agent_step_count(trajectory) == expected
    row = catalog_summary(trajectory, {}, 0)
    assert row["agent_steps"] == expected
    assert "atif.extra:total_turns" not in row["metric_values"]
    assert "atif.extra:total_agent_steps" not in row["metric_values"]
    assert bool(row["metric_diagnostics"]) == (
        "total_agent_steps" in extra and expected is None
    )
    assert trajectory == original


def test_absent_trajectory_is_unknown_and_valid_empty_trajectory_is_zero():
    assert agent_step_count({}) is None
    assert agent_step_count({"steps": []}) == 0
    assert agent_step_count({"synthetic": True, "steps": []}) is None


def test_historical_trial_with_removed_agent_import_remains_readable(tmp_path):
    import json

    from psycheval._harbor_trials import (
        load_harbor_trial_bundle,
        project_harbor_trial_bundle,
    )
    from tests.peval.test_harbor_trials import atif_trajectory, write_trial

    trajectory = atif_trajectory()
    trajectory["final_metrics"]["extra"].pop("total_agent_steps")
    trajectory["final_metrics"]["extra"]["total_turns"] = 9999
    trial = tmp_path / "job" / "trial"
    write_trial(trial, trajectory=trajectory)
    config = trial / "config.json"
    value = json.loads(config.read_text(encoding="utf-8"))
    value["agent"] = {"import_path": "psycheval.harbor.opencode:HostOpenCodeAgent"}
    config.write_text(json.dumps(value), encoding="utf-8")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*.json")}
    document = project_harbor_trial_bundle(load_harbor_trial_bundle(trial))[0]
    assert document.readable
    assert agent_step_count(document.trajectory) == 1
    assert all(p.read_bytes() == content for p, content in before.items())
