import json

import pytest
from harbor.models.agent.context import AgentContext

from psycheval.harbor.agents.opencode import HostOpenCodeAgent
from psycheval.harbor.agents.sessions.hermes import HermesAdapter, convert_hermes_export
from psycheval.harbor.agents.sessions.models import ConversionOptions
from psycheval.harbor.agents.sessions.opencode import (
    OpencodeAdapter,
    native_usage_metrics,
    usage_from_tokens,
)
from tests.harbor.test_opencode import _exported_session


def test_native_export_and_retained_import_share_opencode_steps_and_usage(tmp_path):
    exported = _exported_session()
    source = tmp_path / "opencode-session.json"
    source.write_text(json.dumps(exported), encoding="utf-8")
    agent = HostOpenCodeAgent(logs_dir=tmp_path, model_name="fixture/model")
    agent.populate_context_post_run(AgentContext())
    native = json.loads((tmp_path / "trajectory.json").read_text(encoding="utf-8"))
    retained = (
        OpencodeAdapter()
        .convert_path(
            str(source), ConversionOptions(model="fixture/model", redact=False)
        )
        .trajectory
    )
    assert native["steps"] == retained["steps"]
    assert native["final_metrics"] == retained["final_metrics"]
    assert source.read_text(encoding="utf-8") == json.dumps(exported)


def test_hermes_session_totals_do_not_become_first_message_measurements():
    exported = {
        "id": "session",
        "input_tokens": 200,
        "output_tokens": 50,
        "messages": [
            {"role": "user", "content": "task"},
            {"role": "assistant", "content": "first"},
            {"role": "assistant", "content": "second"},
        ],
    }
    result = convert_hermes_export(
        json.dumps(exported), None, ConversionOptions(redact=False)
    )
    assert all(not step.get("metrics") for step in result.trajectory["steps"])
    assert result.trajectory["final_metrics"]["total_prompt_tokens"] == 200
    assert result.trajectory["final_metrics"]["total_completion_tokens"] == 50


def test_hermes_pretty_json_and_compact_export_have_identical_projection(tmp_path):
    exported = {
        "id": "session",
        "messages": [
            {"role": "user", "content": "task"},
            {
                "role": "assistant",
                "content": "answer",
                "usage": {"prompt_tokens": 10, "completion_tokens": 3},
            },
        ],
    }
    path = tmp_path / "export.json"
    original = json.dumps(exported, indent=2)
    path.write_text(original, encoding="utf-8")
    options = ConversionOptions(redact=False)
    from psycheval.harbor.agents.sessions.conversion import finalize_atif_conversion

    pretty = finalize_atif_conversion(
        HermesAdapter().convert_path(str(path), options)
    ).trajectory
    compact = convert_hermes_export(json.dumps(exported), None, options).trajectory
    assert pretty == compact
    assert pretty["steps"][-1]["metrics"]["prompt_tokens"] == 10
    assert path.read_text(encoding="utf-8") == original


def test_hermes_partial_session_totals_do_not_mix_message_and_session_scopes():
    exported = {
        "id": "session",
        "input_tokens": 200,
        "messages": [
            {
                "role": "assistant",
                "content": "answer",
                "usage": {"prompt_tokens": 10, "completion_tokens": 3},
            }
        ],
    }
    trajectory = convert_hermes_export(
        json.dumps(exported), None, ConversionOptions(redact=False)
    ).trajectory
    assert trajectory["final_metrics"]["total_prompt_tokens"] == 200
    assert "total_completion_tokens" not in trajectory["final_metrics"]
    assert trajectory["steps"][0]["metrics"]["completion_tokens"] == 3


def test_hermes_native_jsonl_rejects_malformed_record_without_partial_conversion():
    text = '{"role":"assistant","content":"answer"}\n{malformed\n'
    with pytest.raises(ValueError):
        convert_hermes_export(text, "session", ConversionOptions())


@pytest.mark.parametrize("input_count", ["10", 10.0, True, -1, None])
def test_opencode_inclusive_usage_does_not_coerce_or_publish_partial_input(input_count):
    native = {"input": input_count, "output": 3, "cache": {"read": 2, "write": 1}}
    metrics = native_usage_metrics(native)
    assert "prompt_tokens" not in metrics
    assert metrics["completion_tokens"] == 3
    assert usage_from_tokens(native)["cache_read_tokens"] == 2
    assert native["input"] == input_count


def test_opencode_omitted_cache_buckets_use_zero_but_explicit_invalid_does_not():
    assert native_usage_metrics({"input": 10})["prompt_tokens"] == 10
    assert (
        native_usage_metrics({"input": 10, "cache": {"read": 2}})["prompt_tokens"] == 12
    )
    assert "prompt_tokens" not in native_usage_metrics({"cache": {"read": 2}})
    assert "prompt_tokens" not in native_usage_metrics(
        {"input": 10, "cache": {"write": None}}
    )
