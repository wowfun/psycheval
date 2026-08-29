from __future__ import annotations

import json
import sys


def send(value: dict[str, object]) -> None:
    print(json.dumps(value, separators=(",", ":")), flush=True)


def result(request_id: object, value: dict[str, object]) -> None:
    send({"jsonrpc": "2.0", "id": request_id, "result": value})


session_number = 0
prompt_number = 0
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
                    "sessionCapabilities": {"list": {}, "close": {}},
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
                "modes": {"currentModeId": "", "availableModes": []},
            },
        )
    elif method == "session/list":
        result(request_id, {"sessions": []})
    elif method == "session/prompt":
        prompt_number += 1
        session_id = params["sessionId"]
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
                                        f"Evidence {prompt_number}.{index}: deterministic failure-cluster detail."
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
    elif method == "session/close":
        result(request_id, {})
