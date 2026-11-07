"""Native evidence coverage is independent of task success and stream parsing."""

import json

import pytest
from harbor.models.agent.context import AgentContext

from psycheval.harbor import measurements as m
from psycheval.harbor.agents.opencode import HostOpenCodeAgent


def publish(tmp_path, monkeypatch, events, *, failed=False, trajectory=True):
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent._trajectory = None
    agent._invocation_failed = failed
    agent._measurement_path = tmp_path / "observer.ndjson"
    agent._measurement_path.write_text(
        "\n".join(json.dumps(e) for e in [{"kind": "loaded"}, *events]) + "\n",
        encoding="utf-8",
    )
    if trajectory:
        (tmp_path / "trajectory.partial.json").write_text(
            json.dumps({"session_id": "s", "steps": []}), encoding="utf-8"
        )
    else:
        (tmp_path / "opencode.txt").write_text(
            json.dumps({"type": "step_start", "sessionID": "s", "timestamp": 9000}),
            encoding="utf-8",
        )
    monkeypatch.setattr(agent, "version", lambda: "fixture")
    agent._publish_measurements(AgentContext())
    manifest = json.loads((tmp_path / m.MANIFEST).read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (tmp_path / m.EVENTS).read_text().splitlines()]
    return manifest, m.calculate(manifest, rows)


def events(*, settled=True):
    result = [
        {"kind": "request", "id": "r", "session": "s"},
        {
            "kind": "session.step.started",
            "message": "a",
            "request": "r",
            "session": "s",
            "start": 100,
        },
        {"kind": "output", "id": "r", "session": "s", "time": 200},
    ]
    if settled:
        result.extend(
            [
                {
                    "kind": "usage",
                    "id": "r",
                    "session": "s",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "cached_tokens": 2,
                },
                {
                    "kind": "session.step.streamed",
                    "message": "a",
                    "request": "r",
                    "session": "s",
                    "time": 700,
                },
                {
                    "kind": "session.step.ended",
                    "message": "a",
                    "request": "r",
                    "session": "s",
                    "time": 800,
                },
            ]
        )
    return result


def test_execution_failure_does_not_imply_collection_loss(tmp_path, monkeypatch):
    manifest, measured = publish(tmp_path, monkeypatch, events(), failed=True)
    assert manifest["complete"]
    assert measured["model_duration_ms"]["value"] == 600
    assert measured["tokens"]["value"] == 15


@pytest.mark.parametrize("settled", [False, True])
def test_truncation_keeps_valid_samples_but_not_totals(tmp_path, monkeypatch, settled):
    manifest, measured = publish(
        tmp_path,
        monkeypatch,
        events(settled=settled) + [{"kind": "truncated"}],
        failed=True,
    )
    assert not manifest["complete"]
    assert measured["ttft_ms"]["value"] == 100
    assert measured["tps"]["value"] == (10 if settled else None)
    assert measured["model_duration_ms"]["value"] is None
    assert measured["tokens"]["value"] is None


def test_unsupported_stream_keeps_native_duration(tmp_path, monkeypatch):
    native = [e for e in events() if e["kind"] not in {"output", "usage"}]
    native.insert(2, {"kind": "unsupported_protocol", "id": "r", "session": "s"})
    manifest, measured = publish(tmp_path, monkeypatch, native)
    assert manifest["complete"]
    assert measured["model_duration_ms"]["value"] == 600
    assert measured["ttft_ms"]["value"] is None
    assert measured["tps"]["value"] is None


def test_cancellation_retains_ttft_without_claiming_complete_scope(
    tmp_path, monkeypatch
):
    manifest, measured = publish(
        tmp_path, monkeypatch, events(settled=False), failed=True
    )
    assert not manifest["complete"]
    assert measured["ttft_ms"]["value"] == 100
    assert measured["model_duration_ms"]["value"] is None
    assert measured["tps"]["value"] is None


def test_conflicting_identity_cannot_supply_samples(tmp_path, monkeypatch):
    native = events()
    native.insert(3, {"kind": "request", "id": "r", "session": "s", "time": 999})
    manifest, measured = publish(tmp_path, monkeypatch, native)
    assert not manifest["complete"]
    assert measured["ttft_ms"]["value"] is None
    assert measured["tps"]["value"] is None
    assert measured["cache_hit_rate"]["value"] is None


def test_identical_request_replay_does_not_erase_usage(tmp_path, monkeypatch):
    native = events()
    native.append(native[0].copy())
    manifest, measured = publish(tmp_path, monkeypatch, native)
    assert manifest["complete"]
    assert measured["tokens"]["value"] == 15
    assert measured["ttft_ms"]["value"] == 100


def test_first_output_is_observed_and_native_duration_is_reported(
    tmp_path, monkeypatch
):
    _, measured = publish(tmp_path, monkeypatch, events())
    assert measured["model_duration_ms"]["provenance"]["quality"] == "reported"
    assert measured["ttft_ms"]["provenance"]["quality"] == "observed"
    assert measured["tps"]["provenance"]["quality"] == "observed"


def test_cancel_before_message_preserves_native_ttft_without_fabricating_trajectory(
    tmp_path, monkeypatch
):
    manifest, measured = publish(
        tmp_path, monkeypatch, events(settled=False), failed=True, trajectory=False
    )
    assert not manifest["complete"]
    assert measured["ttft_ms"]["value"] == 100  # Not the CLI notification time.
    assert not (tmp_path / "trajectory.partial.json").exists()
    assert not (tmp_path / "trajectory.json").exists()
