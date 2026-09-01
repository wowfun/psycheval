from __future__ import annotations

import json
import sys
import threading

output_lock = threading.Lock()


def send(value: dict[str, object]) -> None:
    with output_lock:
        print(json.dumps(value, separators=(",", ":")), flush=True)


def result(request_id: object, value: dict[str, object]) -> None:
    send({"jsonrpc": "2.0", "id": request_id, "result": value})


def complete_prompt(request_id: object, session_id: str, ordinal: int) -> None:
    send(
        {
            "jsonrpc": "2.0",
            "method": "session/update",
            "params": {
                "sessionId": session_id,
                "update": {
                    "sessionUpdate": "plan",
                    "entries": [
                        {
                            "content": "Inspect the evaluation evidence",
                            "priority": "high",
                            "status": "completed",
                        },
                        {
                            "content": "Explain the failure cluster",
                            "priority": "medium",
                            "status": "in_progress",
                        },
                    ],
                },
            },
        }
    )
    send(
        {
            "jsonrpc": "2.0",
            "method": "session/update",
            "params": {
                "sessionId": session_id,
                "update": {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {
                        "type": "text",
                        "text": "\n\n".join(
                            [
                                "Synthetic response: the evaluation evidence is ready for review.",
                                *[
                                    f"Evidence {ordinal}.{index}: deterministic failure-cluster detail."
                                    for index in range(1, 9)
                                ],
                            ]
                        ),
                    },
                },
            },
        }
    )
    result(request_id, {"stopReason": "end_turn"})


session_number = 0
prompt_number = 0
catalog_sessions = {
    "catalog-session": {
        "sessionId": "catalog-session",
        "title": "Earlier session",
        "updatedAt": "2999-01-01T00:00:00.000Z",
    }
}
for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    if method == "initialize":
        result(
            request_id,
            {
                "protocolVersion": 1,
                "agentInfo": {
                    "name": "synthetic-acp",
                    "title": "Synthetic ACP",
                    "version": "1.0",
                },
                "agentCapabilities": {
                    "loadSession": True,
                    "promptCapabilities": {"embeddedContext": True},
                    "sessionCapabilities": {
                        "list": {},
                        "close": {},
                        "delete": {},
                    },
                },
                "authMethods": [],
            },
        )
    elif method == "session/new":
        session_number += 1
        result(
            request_id,
            {
                "sessionId": f"visual-session-{session_number}",
                "modes": {
                    "currentModeId": "build",
                    "availableModes": [
                        {"id": "plan", "name": "Plan"},
                        {"id": "build", "name": "Build"},
                    ],
                },
            },
        )
    elif method == "session/set_mode":
        result(request_id, {})
    elif method == "session/list":
        result(request_id, {"sessions": list(catalog_sessions.values())})
    elif method == "session/delete":
        catalog_sessions.pop(params["sessionId"], None)
        result(request_id, {})
    elif method == "session/load":
        session_id = params["sessionId"]
        envelope_token = "44444444444444444444444444444444"
        replay_chunks = (
            '[peval://source/e2e-restored]\n{"score":0}',
            f"\n\n<pretty-aui-user-message-v1-{envelope_token}>\n",
            "Only the restored browser query",
            f"\n</pretty-aui-user-message-v1-{envelope_token}>",
        )
        for chunk in replay_chunks:
            send(
                {
                    "jsonrpc": "2.0",
                    "method": "session/update",
                    "params": {
                        "sessionId": session_id,
                        "update": {
                            "sessionUpdate": "user_message_chunk",
                            "messageId": "opencode-restored-user",
                            "content": {"type": "text", "text": chunk},
                        },
                    },
                }
            )
        send(
            {
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "sessionId": session_id,
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "messageId": "opencode-restored-assistant",
                        "content": {
                            "type": "text",
                            "text": "Synthetic restored response.",
                        },
                    },
                },
            }
        )
        result(
            request_id,
            {
                "modes": {
                    "currentModeId": "build",
                    "availableModes": [
                        {"id": "plan", "name": "Plan"},
                        {"id": "build", "name": "Build"},
                    ],
                },
            },
        )
    elif method == "session/prompt":
        prompt_number += 1
        session_id = params["sessionId"]
        prompt_text = "".join(
            block.get("text", "")
            for block in params.get("prompt", [])
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        )
        if "Hold the running session" in prompt_text:
            timer = threading.Timer(
                3,
                complete_prompt,
                args=(request_id, session_id, prompt_number),
            )
            timer.daemon = True
            timer.start()
            continue
        if "Show structured tools" in prompt_text:
            send(
                {
                    "jsonrpc": "2.0",
                    "method": "session/update",
                    "params": {
                        "sessionId": session_id,
                        "update": {
                            "sessionUpdate": "tool_call",
                            "toolCallId": f"execute-{prompt_number}",
                            "title": "Execute fixture command",
                            "kind": "execute",
                            "status": "in_progress",
                            "rawInput": {
                                "command": "printf 'alpha\\nbeta\\n'",
                                "cwd": "/workspace",
                            },
                        },
                    },
                }
            )
            send(
                {
                    "jsonrpc": "2.0",
                    "method": "session/update",
                    "params": {
                        "sessionId": session_id,
                        "update": {
                            "sessionUpdate": "tool_call_update",
                            "toolCallId": f"execute-{prompt_number}",
                            "status": "completed",
                            "content": [
                                {
                                    "type": "content",
                                    "content": {
                                        "type": "text",
                                        "text": "alpha\nbeta\n",
                                    },
                                }
                            ],
                        },
                    },
                }
            )
            read_text = "\n".join(
                f"{index}: fixture line {index}" for index in range(1, 11)
            )
            send(
                {
                    "jsonrpc": "2.0",
                    "method": "session/update",
                    "params": {
                        "sessionId": session_id,
                        "update": {
                            "sessionUpdate": "tool_call",
                            "toolCallId": f"read-{prompt_number}",
                            "title": "Read fixture.txt",
                            "kind": "read",
                            "status": "completed",
                            "locations": [{"path": "/workspace/fixture.txt"}],
                            "rawInput": {
                                "filePath": "/workspace/fixture.txt",
                                "offset": 1,
                            },
                            "rawOutput": {
                                "metadata": {
                                    "display": {
                                        "type": "file",
                                        "text": read_text,
                                    }
                                }
                            },
                        },
                    },
                }
            )
            send(
                {
                    "jsonrpc": "2.0",
                    "method": "session/update",
                    "params": {
                        "sessionId": session_id,
                        "update": {
                            "sessionUpdate": "tool_call",
                            "toolCallId": f"diff-{prompt_number}",
                            "title": "Edit fixture.txt",
                            "kind": "edit",
                            "status": "completed",
                            "content": [
                                {
                                    "type": "diff",
                                    "path": "/workspace/fixture.txt",
                                    "oldText": "\n".join(
                                        f"old line {index}" for index in range(1, 6)
                                    ),
                                    "newText": "\n".join(
                                        f"new line {index}" for index in range(1, 6)
                                    ),
                                }
                            ],
                        },
                    },
                }
            )
        complete_prompt(request_id, session_id, prompt_number)
    elif method == "session/close":
        result(request_id, {})
