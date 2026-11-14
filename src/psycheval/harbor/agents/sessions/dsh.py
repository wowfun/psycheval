"""Incremental conversion of admitted DSH v4 execution events."""

import json
from datetime import datetime, timezone

from ...atif import iso_timestamp_ms
from ...inference_telemetry import finalize_trajectory_metrics
from ...redaction import redact_value
from .common import bounded_arguments, bounded_value
from .models import ConversionOptions


class NativeSession:
    def __init__(self, identity, agent):
        self.data = {
            "schema_version": "ATIF-v1.8",
            "trajectory_id": "dsh:" + identity,
            "session_id": identity,
            "agent": {k: v for k, v in agent.items() if k != "model_name"},
            "steps": [],
            "extra": {"timestamp_semantics": "event_observed"},
        }
        self.calls = {}
        self.finished = False
        self.started = {}
        self.active_calls = {}
        self.child_calls = {}
        self.children = set()

    def feed(self, event):
        kind, data = event.get("type"), event.get("data") or {}
        if kind == "session/end-seed" and data.get("inherited") is True:
            self.data["steps"].clear()
            self.calls.clear()
            self.started.clear()
            self.active_calls.clear()
            self.children.clear()
            self.child_calls.clear()
            self.finished = False
            return
        if kind == "step/start":
            self.finished = False
            self.started[(data.get("turn"), data.get("step"))] = event.get("time")
        if kind == "subagent/catalog" and data.get("childId"):
            self.children.add(data["childId"])
            candidates = [
                identity
                for identity, call in self.active_calls.items()
                if call["function_name"] == "subagent"
                and call["arguments"].get("name") == data.get("name")
            ]
            if len(candidates) == 1:
                self.child_calls[data["childId"]] = candidates[0]
        message = data.get("message") or {}
        if kind in {"user/message", "system/message", "assistant/message"}:
            source = {
                "user/message": "user",
                "system/message": "system",
                "assistant/message": "agent",
            }[kind]
            content = message.get("content", message.get("text", ""))
            blocks = content if isinstance(content, list) else []
            if isinstance(content, list):
                content = "\n".join(
                    block.get("text", "")
                    for block in content
                    if block.get("type") == "text"
                )
            step = {
                "step_id": len(self.data["steps"]) + 1,
                "source": source,
                "message": str(content)[:131072],
            }
            reasoning = "\n".join(
                b.get("text", "")
                for b in blocks
                if b.get("type") in {"reasoning", "reasoning_text"}
            )
            if reasoning:
                step["reasoning_content"] = reasoning[:131072]
            native_source = message.get("source") or {}
            if native_source.get("model"):
                self.data["agent"] = {
                    **self.data["agent"],
                    "model_name": str(native_source["model"]),
                }
            timestamp = event.get("time")
            start = (
                self.started.get((data.get("turn"), data.get("step")))
                if source == "agent"
                else None
            )
            if type(start) is int and type(timestamp) is int and timestamp >= start:
                step["extra"] = {
                    "duration_ms": timestamp - start,
                    "duration_source": "dsh_native_model_step",
                }
                timestamp = start
            if isinstance(timestamp, (int, float)):
                step["timestamp"] = datetime.fromtimestamp(
                    timestamp / 1000, timezone.utc
                ).isoformat()
            usage = data.get("usage") or {}
            output, total = usage.get("outputTokens"), usage.get("totalTokens")
            if output is not None and total is not None and total >= output:
                step["metrics"] = {
                    "prompt_tokens": total - output,
                    "completion_tokens": output,
                }
                if usage.get("cacheReadTokens") is not None:
                    step["metrics"]["cached_tokens"] = usage["cacheReadTokens"]
            self.data["steps"].append(step)
        elif kind == "tool/call":
            step = next(
                (s for s in reversed(self.data["steps"]) if s["source"] == "agent"),
                None,
            )
            if step is None:
                step = {
                    "step_id": len(self.data["steps"]) + 1,
                    "source": "agent",
                    "message": "",
                }
                self.data["steps"].append(step)
            args = data.get("arguments", "{}")
            args = json.loads(args) if isinstance(args, str) else args
            call = {
                "tool_call_id": data["callId"],
                "function_name": data["name"],
                "arguments": bounded_arguments(args, ConversionOptions())[0],
            }
            step.setdefault("tool_calls", []).append(call)
            self.calls[data["callId"]] = step
            self.active_calls[data["callId"]] = call
            call["extra"] = {"started_at": _iso(event.get("time"))}
        elif kind == "tool/result":
            identity = (message.get("source") or {}).get("callId")
            active = self.active_calls.pop(identity, {})
            start = iso_timestamp_ms((active.get("extra") or {}).get("started_at"))
            end = event.get("time")
            timing = (
                {
                    "execution_duration_ms": end - start,
                    "execution_duration_source": "dsh_native_tool_call",
                }
                if start is not None and type(end) is int and end >= start
                else {}
            )
            if identity in self.calls:
                self.calls[identity].setdefault("observation", {"results": []})[
                    "results"
                ].append(
                    {
                        "source_call_id": identity,
                        "content": bounded_value(
                            message.get("content", ""), ConversionOptions()
                        )[0],
                        "extra": {
                            **timing,
                            "finished_at": _iso(event.get("time")),
                            "is_error": message.get("isError", False),
                            "status": "failed"
                            if message.get("isError")
                            else "completed",
                        },
                    }
                )
        elif kind == "turn/end":
            self.finished = True
            self.data["extra"]["execution_status"] = (data.get("reason") or {}).get(
                "kind", "unknown"
            )

    def finish(self):
        self.data["extra"]["tool_evidence"] = "complete" if self.finished else "partial"
        if not self.finished:
            self.data["extra"]["incomplete"] = True
        return finalize_trajectory_metrics(redact_value(self.data))


def _iso(value):
    if type(value) not in (int, float):
        return None
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
