"""Deterministic byte-level ACP peer; never contacts a provider."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

mode = sys.argv[1] if len(sys.argv) > 1 else "normal"
current = "a"
prompt_id = None
session = "fixture-session"


def send(value):
    print(json.dumps({"jsonrpc": "2.0", **value}, ensure_ascii=False), flush=True)


def options():
    return [
        {
            "id": "model",
            "name": "Model",
            "type": "select",
            "currentValue": current,
            "options": [{"value": "a", "name": "A"}, {"value": "b", "name": "B"}],
        }
    ]


def update(value):
    send(
        {"method": "session/update", "params": {"sessionId": session, "update": value}}
    )


for line in sys.stdin:
    request = json.loads(line)
    method, params = request.get("method"), request.get("params", {})
    identity = request.get("id")
    if method == "initialize":
        if mode == "slow-setup":
            time.sleep(0.3)
        send(
            {
                "id": identity,
                "result": {
                    "protocolVersion": 1,
                    "agentCapabilities": {
                        "loadSession": True,
                        **(
                            {"sessionCapabilities": {"resume": {}}}
                            if mode == "resume"
                            else {}
                        ),
                        "mcpCapabilities": {"http": True},
                    },
                    "authMethods": [],
                    "agentInfo": {"name": "fixture", "version": "1"},
                },
            }
        )
    elif method in {"session/new", "session/load", "session/resume"}:
        if mode == "slow-setup":
            time.sleep(0.3)
        if mode == "http":
            assert params["mcpServers"] == [
                {
                    "type": "http",
                    "name": "fixture",
                    "url": "https://mcp.example.test",
                    "headers": [],
                }
            ]
        marker = Path(os.environ["XDG_STATE_HOME"]) / "session"
        if method == "session/new":
            marker.write_text(session)
        else:
            assert params["sessionId"] == marker.read_text()
        if method == "session/load":
            assert mode != "resume"
            update(
                {
                    "sessionUpdate": "tool_call",
                    "toolCallId": "replayed",
                    "name": "old",
                    "title": "old",
                    "status": "completed",
                    "rawInput": {},
                }
            )
        result = {"configOptions": options()}
        if method == "session/new":
            result["sessionId"] = session
        send({"id": identity, "result": result})
    elif method == "session/set_config_option":
        if mode != "unconfirmed":
            current = params["value"]
        send({"id": identity, "result": {"configOptions": options()}})
    elif method == "session/prompt":
        prompt_id = identity
        Path("result.txt").write_text("fixture artifact 中文")
        Path("state-paths.json").write_text(
            json.dumps(
                {
                    k: os.environ[k]
                    for k in (
                        "HOME",
                        "XDG_CONFIG_HOME",
                        "XDG_STATE_HOME",
                        "XDG_RUNTIME_DIR",
                    )
                }
            )
        )
        update(
            {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "中文🙂"},
            }
        )
        call = {
            "sessionUpdate": "tool_call",
            "toolCallId": "call-1",
            "name": "bash",
            "title": "Human readable title",
            "status": "pending",
            "rawInput": {"command": "echo fixture"},
        }
        if mode == "no-name":
            call.pop("name")
        update(call)
        if mode == "malformed":
            print('{"jsonrpc":"2.0","jsonrpc":"2.0"}', flush=True)
            break
        if mode == "eof":
            break
        if mode in {"background", "cancel", "stubborn"}:
            script = "import time; time.sleep(120)"
            if mode == "stubborn":
                script = "import signal,time; from pathlib import Path; signal.signal(signal.SIGTERM, lambda *_: Path('term-count').open('a').write('t')); Path('descendant-ready').touch(); time.sleep(120)"
            descendant = subprocess.Popen(
                [sys.executable, "-c", script],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            Path("descendant.pid").write_text(str(descendant.pid))
            if mode == "stubborn":
                deadline = time.monotonic() + 10
                while not Path("descendant-ready").exists():
                    if time.monotonic() >= deadline:
                        raise RuntimeError("descendant did not start")
                    time.sleep(0.01)
        if mode == "cancel":
            continue
        if mode == "stdout-flood":
            for _ in range(256):
                update(
                    {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": "x" * 2048},
                    }
                )
        if mode == "stderr-flood":
            sys.stderr.write("x" * (256 * 1024))
            sys.stderr.flush()
        if mode in {"allow", "deny"}:
            send(
                {
                    "id": "permission",
                    "method": "session/request_permission",
                    "params": {
                        "sessionId": session,
                        "toolCall": {"toolCallId": "call-1", "title": "Permission"},
                        "options": [
                            {"optionId": "yes", "name": "Yes", "kind": "allow_once"},
                            {"optionId": "no", "name": "No", "kind": "reject_once"},
                        ],
                    },
                }
            )
            continue
        update(
            {
                "sessionUpdate": "tool_call_update",
                "toolCallId": "call-1",
                "status": "completed",
                "rawOutput": {
                    "is_error": False,
                    "content": [{"type": "text", "text": "ok"}],
                    "value": {
                        "status": "exited",
                        "exit_code": 0,
                        "signal": None,
                        "stdout": {"text": "ok"},
                        "stderr": {"text": ""},
                    },
                },
            }
        )
        update(
            {
                "sessionUpdate": "agent_message_chunk",
                "content": {"type": "text", "text": "完成中文🙂"},
            }
        )
        send({"id": identity, "result": {"stopReason": "end_turn"}})
    elif method == "session/cancel":
        send({"id": prompt_id, "result": {"stopReason": "cancelled"}})
    elif identity == "permission":
        Path("permission.json").write_text(json.dumps(request["result"]))
        send({"id": prompt_id, "result": {"stopReason": "end_turn"}})
