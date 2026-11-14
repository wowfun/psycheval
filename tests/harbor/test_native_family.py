import gzip
import json
import sqlite3
from copy import deepcopy

import pytest

from psycheval.harbor.agents.sessions.conversion import finalize_atif_conversion
from psycheval.harbor.agents.sessions.dsh import NativeSession
from psycheval.harbor.agents.sessions.models import ConversionOptions, ConversionResult
from psycheval.harbor.agents.sessions.opencode import (
    OpencodeAdapter,
    convert_native_export,
)
from psycheval.harbor.agents.workbuddy_family import attach, capture
from psycheval.harbor.agents.workbuddy_usage import HistoryBaseline
from psycheval.harbor.family import retain, validate
from psycheval.report.builder import project_meta_from_atif
from tests.harbor.test_family import trajectory
from tests.harbor.test_opencode import _exported_session
from tests.peval.peval_test_support import create_opencode_db


def test_workbuddy_agent_filename_is_not_native_session_identity(tmp_path):
    root = tmp_path / "projects"
    project = root / "project"
    child = project / "root/subagents/agent-child.jsonl"
    child.parent.mkdir(parents=True)
    (project / "root.jsonl").touch()
    child.write_text(
        "\n".join(
            json.dumps(item)
            for item in [
                {
                    "sessionId": "native-child",
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "compute"}],
                    "providerData": {"rootRequestId": "request"},
                },
                {
                    "sessionId": "native-child",
                    "type": "function_call",
                    "callId": "shell",
                    "name": "Bash",
                    "arguments": '{"command":"compute"}',
                    "timestamp": 10,
                    "providerData": {
                        "messageId": "tool-request",
                        "rawUsage": {"prompt_tokens": 5, "completion_tokens": 1},
                    },
                },
                {
                    "sessionId": "native-child",
                    "type": "function_call_result",
                    "callId": "shell",
                    "name": "Bash",
                    "status": "completed",
                    "timestamp": 20,
                    "output": {"text": "failed"},
                    "providerData": {"toolResult": {"rawResponse": {"exitCode": 1}}},
                },
                {
                    "sessionId": "native-child",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "1591"}],
                    "message": {"usage": {}},
                    "providerData": {
                        "messageId": "m",
                        "model": "actual-model",
                        "rawUsage": {"prompt_tokens": 10, "completion_tokens": 2},
                    },
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    logs = tmp_path / "logs"
    logs.mkdir()
    with gzip.open(logs / "acp.events.ndjson.gz", "wt", encoding="utf-8") as stream:
        stream.write(
            json.dumps(
                {
                    "direction": "receive",
                    "phase": "prompt",
                    "message": {
                        "method": "session/update",
                        "params": {
                            "sessionId": "root",
                            "update": {
                                "toolCallId": "call",
                                "status": "completed",
                                "rawOutput": {"text": "1591\n[Agent ID: agent-child]"},
                                "_meta": {
                                    "codebuddy.ai/toolName": "Agent",
                                    "codebuddy.ai/conversationRequestId": "request",
                                    "codebuddy.ai/isBackground": False,
                                },
                            },
                        },
                    },
                }
            )
            + "\n"
        )
    summary = {"session_id": "root", "max_evidence_bytes": 100000}
    result = capture(
        root, summary, HistoryBaseline({}), {"version": "fixture"}, directory=logs
    )
    body = result["children"]["agent-child"][1]
    assert body["session_id"] == "native-child"
    assert body["agent"]["model_name"] == "actual-model"
    assert body["steps"][-1]["message"] == "1591"
    tool_step = next(step for step in body["steps"] if step.get("tool_calls"))
    assert tool_step["tool_calls"][0]["function_name"] == "Bash"
    assert tool_step["tool_calls"][0]["arguments"] == {"command": "compute"}
    assert tool_step["observation"]["results"][0]["extra"]["exit_code"] == 1
    assert tool_step["observation"]["results"][0]["extra"]["is_error"] is True
    parent = trajectory("workbuddy:root")
    parent["session_id"] = "root"
    attach(parent, result)
    assert len(parent["extra"]["family"]["members"]) == 2
    assert result["usage"][0]["session_id"] == "native-child"
    metadata = child.with_suffix(".meta.json")
    metadata.write_text(" " * 100001, encoding="utf-8")
    limited = capture(
        root, summary, HistoryBaseline({}), {"version": "fixture"}, directory=logs
    )
    assert "family_metadata_byte_limit" in limited["diagnostics"]
    assert not limited["children"] and limited["missing"]
    metadata.unlink()
    child.write_text(
        child.read_text(encoding="utf-8").replace(
            '"rootRequestId": "request"', '"rootRequestId": "foreign"'
        ),
        encoding="utf-8",
    )
    assert not capture(
        root, summary, HistoryBaseline({}), {"version": "fixture"}, directory=logs
    )["children"]


def test_dsh_seed_prefix_is_excluded_and_native_model_and_timing_retained():
    parser = NativeSession("child", {"name": "dsh", "version": "fixture"})
    parser.feed(
        {
            "type": "assistant/message",
            "time": 10,
            "data": {"message": {"content": "copied"}},
        }
    )
    parser.feed({"type": "session/end-seed", "data": {"inherited": True}})
    parser.feed({"type": "step/start", "time": 20, "data": {"turn": 1, "step": 1}})
    parser.feed(
        {
            "type": "assistant/message",
            "time": 30,
            "data": {
                "turn": 1,
                "step": 1,
                "message": {
                    "content": [{"type": "text", "text": "answer"}],
                    "source": {"model": "native-model"},
                },
                "usage": {"totalTokens": 12, "outputTokens": 2},
            },
        }
    )
    body = parser.finish()
    assert len(body["steps"]) == 1
    assert body["steps"][0]["extra"]["duration_ms"] == 10
    assert body["agent"]["model_name"] == "native-model"
    assert body["final_metrics"]["total_prompt_tokens"] == 10


def test_failed_dsh_capture_cannot_reuse_previous_invocations_completeness(
    tmp_path, monkeypatch
):
    from harbor.models.trajectories import Trajectory

    from psycheval.harbor.agents import dsh
    from psycheval.harbor.agents.acp.agent import HostACPAgent

    agent = dsh.HostDSHAgent(logs_dir=tmp_path, model_name="fixture")
    agent._invocation_id = "current"
    agent._agent_metadata = {"dsh_cli_version": "fixture"}
    agent._state = tmp_path
    agent._measurement_hook = tmp_path / "hook"
    agent._family_complete, agent._family_diagnostics = True, []
    (tmp_path / "acp.summary.json").write_text(
        json.dumps({"invocation_id": "current", "session_id": "root"}), encoding="utf-8"
    )
    monkeypatch.setattr(HostACPAgent, "_publish_call", lambda *_: None)

    def unavailable(*args, **kwargs):
        raise OSError("missing native history")

    monkeypatch.setattr(dsh, "capture", unavailable)
    agent._publish_call(tmp_path)
    result = agent._enrich_trajectory(Trajectory.model_validate(trajectory("root")), {})
    family = result.extra["family"]
    assert family["discovery_complete"] is False
    assert family["diagnostics"] == ["family_capture_unavailable"]


def test_opencode_standalone_import_retains_children_and_excludes_forks():
    source = _exported_session()
    child, fork = deepcopy(source), deepcopy(source)
    child["info"].update(id="child", parentID=source["info"]["id"])
    fork["info"].update(
        id="fork",
        parentID=source["info"]["id"],
        fork={"sessionID": source["info"]["id"]},
    )
    source["children"] = [fork, child]
    fork_child = deepcopy(child)
    fork_child["info"].update(id="fork-child", parentID="fork")
    source["children"].insert(0, fork_child)
    source["family_missing"] = [
        {
            "trajectory_id": identity,
            "session_id": identity,
            "parent_trajectory_id": parent,
        }
        for identity, parent in [
            ("fork-missing-grandchild", "fork-missing-child"),
            ("fork-missing-child", "fork"),
        ]
    ]
    fork_after_missing = deepcopy(child)
    fork_after_missing["info"].update(
        id="fork-after-missing", parentID="fork-missing-grandchild"
    )
    source["children"].insert(0, fork_after_missing)
    source["messages"][0]["content"].append(
        {
            "type": "tool",
            "id": "dispatch",
            "name": "subagent",
            "state": {
                "status": "completed",
                "input": {},
                "content": [
                    {
                        "type": "text",
                        "text": '<subagent sessionID="child" state="completed">done</subagent>',
                    }
                ],
                "time": {"start": 1, "end": 2},
            },
        }
    )
    result = convert_native_export(source, ConversionOptions())
    assert [c["session_id"] for c in result.trajectory["subagent_trajectories"]] == [
        "child"
    ]
    assert len(result.trajectory["extra"]["family"]["members"]) == 2
    assert not result.trajectory["extra"]["family"]["discovery_complete"]


def test_opencode_indexes_parent_dispatch_results_once(monkeypatch):
    from psycheval.harbor.agents.sessions import opencode_native

    source = _exported_session()
    source["children"] = []
    for i in range(3):
        child = _exported_session()
        child["info"].update(id=f"child-{i}", parentID=source["info"]["id"])
        source["children"].append(child)
        source["messages"][0]["content"].append(
            {
                "type": "tool",
                "id": f"dispatch-{i}",
                "name": "subagent",
                "state": {
                    "status": "completed",
                    "input": {},
                    "content": [
                        {
                            "type": "text",
                            "text": f'<subagent sessionID="child-{i}" state="completed">done</subagent>',
                        }
                    ],
                    "time": {"start": 1, "end": 2},
                },
            }
        )
    original, visits = opencode_native._dispatch_index, []

    def indexed(parent):
        visits.append(parent["trajectory_id"])
        return original(parent)

    monkeypatch.setattr(opencode_native, "_dispatch_index", indexed)
    result = convert_native_export(source, ConversionOptions()).trajectory
    assert visits == [source["info"]["id"]]
    assert len(result["extra"]["family"]["activations"]) == 3


def test_dsh_child_tool_timing_and_terminal_reason_are_native():
    parser = NativeSession("child", {"name": "dsh", "version": "fixture"})
    parser.feed(
        {
            "type": "tool/call",
            "time": 35,
            "data": {"callId": "call", "name": "shell", "arguments": "{}"},
        }
    )
    parser.feed(
        {
            "type": "tool/result",
            "time": 45,
            "data": {"message": {"source": {"callId": "call"}, "content": "done"}},
        }
    )
    parser.feed({"type": "turn/end", "data": {"reason": {"kind": "completed"}}})
    body = parser.finish()
    assert (
        body["steps"][0]["observation"]["results"][0]["extra"]["execution_duration_ms"]
        == 10
    )
    assert (
        retain(body)["extra"]["family"]["members"][0]["execution_status"] == "completed"
    )


def test_opencode_descendants_of_missing_body_remain_metadata_only():
    source = _exported_session()
    child = deepcopy(source)
    child["info"].update(id="grandchild", parentID="missing")
    source["children"] = [child]
    source["family_missing"] = [
        {
            "trajectory_id": "missing",
            "session_id": "missing",
            "parent_trajectory_id": source["info"]["id"],
        }
    ]
    result = convert_native_export(source, ConversionOptions())
    members = result.trajectory["extra"]["family"]["members"]
    assert [(m["trajectory_id"], m["content_status"]) for m in members[1:]] == [
        ("missing", "missing"),
        ("grandchild", "missing"),
    ]
    assert not result.trajectory.get("subagent_trajectories")


@pytest.mark.parametrize("missing_first", [False, True])
def test_standalone_depth_boundary_and_fork_subtree_remain_separate(missing_first):
    from psycheval.harbor.family import MAX_DEPTH, coverage

    source = _exported_session()
    source["family_capture_complete"] = True
    children = []
    parent = source["info"]["id"]
    for index in range(MAX_DEPTH + 3):
        child = _exported_session()
        child["info"].update(id=f"depth-{index}", parentID=parent)
        parent = child["info"]["id"]
        children.append(child)
    if missing_first:
        children[0]["messages"] = []
    source["children"] = list(reversed(children))
    result = convert_native_export(source, ConversionOptions()).trajectory
    assert len(result["extra"]["family"]["members"]) == MAX_DEPTH + 2
    assert coverage(result)["missing_members"] == (
        MAX_DEPTH + 1 if missing_first else 1
    )
    assert "family_depth_limit" in result["extra"]["family"]["diagnostics"]
    source["children"][-1]["info"]["fork"] = {"sessionID": source["info"]["id"]}
    result = convert_native_export(source, ConversionOptions()).trajectory
    assert len(result["extra"]["family"]["members"]) == 1
    assert result["extra"]["family"]["discovery_complete"]


def test_opencode_db_family_excludes_explicit_fork(tmp_path):
    path = tmp_path / "opencode.db"
    create_opencode_db(path)
    with sqlite3.connect(path) as connection:
        connection.execute("ALTER TABLE session ADD COLUMN parent_id TEXT")
        connection.execute("ALTER TABLE session ADD COLUMN fork TEXT")
        connection.execute(
            "UPDATE session SET parent_id='ses-latest' WHERE id='ses-old'"
        )
    root = finalize_atif_conversion(
        OpencodeAdapter().convert_db(str(path), "ses-latest", ConversionOptions())
    )
    assert len(root.trajectory["subagent_trajectories"]) == 1
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE session SET fork='explicit' WHERE id='ses-old'")
    root = finalize_atif_conversion(
        OpencodeAdapter().convert_db(str(path), "ses-latest", ConversionOptions())
    )
    assert not root.trajectory.get("subagent_trajectories")


@pytest.mark.parametrize("version", ["legacy", "v2"])
def test_opencode_database_family_depth_is_bounded_before_reading_bodies(
    tmp_path, monkeypatch, version
):
    from psycheval.harbor import family

    monkeypatch.setattr(family, "MAX_DEPTH", 2)
    path = tmp_path / "depth.db"
    if version == "legacy":
        create_opencode_db(path)
    with sqlite3.connect(path) as connection:
        if version == "legacy":
            connection.execute("ALTER TABLE session ADD COLUMN parent_id TEXT")
            for index in range(5):
                identity = f"child-{index}"
                parent = f"child-{index - 1}" if index else "ses-latest"
                connection.execute(
                    "INSERT INTO session SELECT ?,title,directory,agent,model,time_created,time_updated,? FROM session WHERE id='ses-old'",
                    (identity, parent),
                )
                connection.execute(
                    "INSERT INTO message SELECT ? || id,?,time_created,time_updated,data FROM message WHERE session_id='ses-old'",
                    (identity, identity),
                )
                connection.execute(
                    "INSERT INTO part SELECT ? || id,? || message_id,?,time_created,time_updated,data FROM part WHERE session_id='ses-old'",
                    (identity, identity, identity),
                )
            root_id = "ses-latest"
        else:
            connection.executescript("""
                CREATE TABLE session_v2(id TEXT PRIMARY KEY,parent_id TEXT,fork_session_id TEXT,fork_boundary TEXT,idle_outcome TEXT,time_busy INTEGER,time_idle INTEGER,time_updated INTEGER);
                CREATE TABLE session_message(id TEXT PRIMARY KEY,session_id TEXT,type TEXT,seq INTEGER,data TEXT);
                CREATE TABLE session_part(message_id TEXT,session_id TEXT,ordinal INTEGER,type TEXT,data TEXT);
            """)
            root_id = "root"
            for index in range(6):
                identity = "root" if index == 0 else f"child-{index - 1}"
                parent = (
                    None
                    if not index
                    else "root"
                    if index == 1
                    else f"child-{index - 2}"
                )
                connection.execute(
                    "INSERT INTO session_v2 VALUES(?,?,NULL,NULL,'succeeded',1,2,2)",
                    (identity, parent),
                )
                message = _exported_session()["messages"][0]
                connection.execute(
                    "INSERT INTO session_message VALUES(?,?,'assistant',1,?)",
                    (identity, identity, json.dumps(message)),
                )
    result = finalize_atif_conversion(
        OpencodeAdapter().convert_db(str(path), root_id, ConversionOptions())
    )
    evidence = result.trajectory["extra"]["family"]
    assert len(evidence["members"]) == 4
    assert evidence["members"][-1]["content_status"] == "missing"
    assert "family_depth_limit" in evidence["diagnostics"]
    assert not evidence["discovery_complete"]


def test_copied_context_never_contributes_to_family_workload():
    root = trajectory("root", 1000)
    root["steps"] = [
        {
            "step_id": 1,
            "source": "agent",
            "message": "copy",
            "is_copied_context": True,
            "metrics": {"prompt_tokens": 999, "completion_tokens": 999},
        },
        {
            "step_id": 2,
            "source": "agent",
            "message": "actual",
            "metrics": {"prompt_tokens": 10, "completion_tokens": 2},
        },
    ]
    retain(root)
    values = project_meta_from_atif(root, {})["metric_values"]
    assert values["tokens"] == 12
    assert values["agent_steps"] == 1
    assert values["total_steps"] == 1


def test_claude_proven_single_child_link_retains_dispatch_without_join():

    root, child = trajectory("root"), trajectory("child")
    root["extra"]["claude"] = {"session_id": "root"}
    root["steps"][0]["tool_calls"] = [
        {"tool_call_id": "dispatch", "function_name": "Task", "arguments": {}}
    ]
    root["steps"][0]["observation"] = {
        "results": [
            {
                "source_call_id": "dispatch",
                "content": "done",
                "subagent_trajectory_ref": [{"trajectory_id": "child"}],
            }
        ]
    }
    child["steps"][0]["tool_calls"] = [
        {"tool_call_id": "read", "function_name": "Read", "arguments": {}}
    ]
    child["steps"][0]["observation"] = {
        "results": [{"source_call_id": "read", "content": "done"}]
    }
    root["subagent_trajectories"] = [child]
    result = finalize_atif_conversion(
        ConversionResult(root, [], [], 2, 0, None, None)
    ).trajectory
    edge = result["extra"]["family"]["activations"][0]
    assert edge["parent_call_id"] == "dispatch" and edge["first_call_id"] == "read"
    assert "joined_before_call_id" not in edge


def test_copied_totals_are_labeled_execution_derived_and_native_values_win():
    from psycheval.harbor.measurements import measurement
    from psycheval.report.measurements import project

    root = trajectory("root", 999)
    root["steps"] = [
        {
            "step_id": 1,
            "source": "assistant",
            "message": "copied",
            "is_copied_context": True,
        },
        {
            "step_id": 2,
            "source": "assistant",
            "message": "actual",
            "metrics": {"prompt_tokens": 10, "completion_tokens": 2},
        },
    ]
    result = project(root, {})
    assert result["metric_values"]["tokens"] == 12
    assert result["metric_values"]["agent_steps"] == 1
    assert result["metric_provenance"]["tokens"]["source"] == "derived.execution_steps"
    native = {
        "tokens": measurement(
            123, source="native", method="current_invocation", basis="native"
        )
    }
    result = project(
        root, {"native_measurement_sets": {"root": native, "family": native}}
    )
    assert result["metric_values"]["tokens"] == 123
    assert result["metric_provenance"]["tokens"]["source"] == "native"


def test_family_activation_requires_actual_parent_and_scalar_anchors():
    root = trajectory("root")
    root["subagent_trajectories"] = [trajectory("child")]
    retain(root)
    root["extra"]["family"]["activations"] = [
        {
            "parent_trajectory_id": "root",
            "child_trajectory_id": "child",
            "parent_call_id": [],
        }
    ]
    with pytest.raises(ValueError, match="anchor"):
        validate(root)


def test_opencode_v2_snapshot_imports_users_live_parts_and_excludes_forks(tmp_path):
    path = tmp_path / "native.db"
    with sqlite3.connect(path) as connection:
        connection.executescript("""
            CREATE TABLE session_v2(id TEXT PRIMARY KEY,parent_id TEXT,fork_session_id TEXT,fork_boundary TEXT,idle_outcome TEXT,time_busy INTEGER,time_idle INTEGER,time_updated INTEGER,title TEXT);
            CREATE TABLE session_message(id TEXT PRIMARY KEY,session_id TEXT,type TEXT,seq INTEGER,data TEXT);
            CREATE TABLE session_part(message_id TEXT,session_id TEXT,ordinal INTEGER,type TEXT,data TEXT);
        """)
        for identity, parent, fork in [
            ("root", None, None),
            ("child", "root", None),
            ("fork", "root", "root"),
        ]:
            connection.execute(
                "INSERT INTO session_v2 VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    identity,
                    parent,
                    fork,
                    json.dumps({"type": "through", "messageID": "root-message"})
                    if fork
                    else None,
                    "succeeded",
                    1,
                    10,
                    10,
                    identity,
                ),
            )
            user = {"time": {"created": 1}, "text": identity + " prompt"}
            message = _exported_session()["messages"][0]
            connection.execute(
                "INSERT INTO session_message VALUES(?,?,?,?,?)",
                (identity + "-user", identity, "user", 1, json.dumps(user)),
            )
            connection.execute(
                "INSERT INTO session_message VALUES(?,?,?,?,?)",
                (
                    identity + "-message",
                    identity,
                    "assistant",
                    2,
                    json.dumps(
                        {k: v for k, v in message.items() if k not in {"id", "type"}}
                    ),
                ),
            )
        # Parts still being projected live use the same native content representation.
        connection.execute(
            "INSERT INTO session_part VALUES(?,?,?,?,?)",
            (
                "child-message",
                "child",
                0,
                "text",
                json.dumps({"type": "text", "text": "child result"}),
            ),
        )
    result = OpencodeAdapter().convert_db(str(path), "root", ConversionOptions())
    assert [c["session_id"] for c in result.trajectory["subagent_trajectories"]] == [
        "child"
    ]
    assert result.trajectory["steps"][0]["message"] == "root prompt"
    child = result.trajectory["subagent_trajectories"][0]
    assert child["steps"][0]["message"] == "child prompt"
    assert child["steps"][-1]["message"] == "child result"
    assert {s.session_id for s in OpencodeAdapter().list_sessions(str(path))} == {
        "root",
        "child",
        "fork",
    }
    fork = (
        OpencodeAdapter().convert_db(str(path), "fork", ConversionOptions()).trajectory
    )
    assert all(step.get("is_copied_context") for step in fork["steps"])
    assert project_meta_from_atif(fork, {})["metric_values"]["tokens"] is None
