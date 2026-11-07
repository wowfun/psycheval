"""Client-observed intervals for one retained ACP invocation (never inference)."""

from datetime import datetime, timedelta


class ObservedTiming:
    def __init__(self, summary):
        self.enabled = "client_clock" in summary
        self.origin = None
        self.error = None
        self.previous = -1
        self.chunks = {}
        self.tools = {}
        if not self.enabled:
            return
        clock = summary["client_clock"]
        try:
            if (
                not isinstance(clock, dict)
                or type(clock.get("version")) is not int
                or clock["version"] != 1
                or clock.get("invocation_id") != summary.get("invocation_id")
            ):
                raise ValueError
            self.origin = datetime.fromisoformat(clock["origin_utc"])
            if self.origin.utcoffset() != timedelta(0):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            self.error = "invalid_client_clock"

    def event(self, event):
        if not self.enabled or self.error:
            return None
        offset = event.get("elapsed_ns")
        if type(offset) is not int or offset < 0 or offset < self.previous:
            self.error = "invalid_client_clock_offset"
            return None
        try:
            self.timestamp(offset)
        except OverflowError:
            self.error = "invalid_client_clock_offset"
            return None
        self.previous = offset
        return offset

    def timestamp(self, offset):
        return (self.origin + timedelta(microseconds=offset // 1000)).isoformat()

    def chunk(self, step_id, offset):
        if offset is None:
            return
        span = self.chunks.setdefault(step_id, [offset, offset, 0])
        span[1] = offset
        span[2] += 1

    def tool(self, update, offset):
        if not self.enabled:
            return
        identity = update["toolCallId"]
        span = self.tools.setdefault(identity, {"first": offset})
        status = update.get("status")
        if "terminal" in span:
            if status is not None and status != span["terminal"]:
                span["error"] = "conflicting_tool_status"
            return
        if update.get("sessionUpdate") == "tool_call" and status not in {
            "completed",
            "failed",
        }:
            span.setdefault("initial", offset)
        if status == "in_progress":
            span.setdefault("running", offset)
        if status in {"completed", "failed"}:
            span.update(terminal=status, end=offset)

    def project(self, steps):
        if not self.enabled:
            return {}
        for step in steps:
            if step["source"] != "agent":
                continue
            extra = step.setdefault("extra", {})
            extra.update(duration_ms=None, duration_source="acp_client_observed_output")
            chunks = self.chunks.get(step["step_id"])
            if not self.error and chunks:
                step["timestamp"] = self.timestamp(chunks[0])
                extra["timestamp_source"] = "acp_client_observed"
                if chunks[2] > 1:
                    extra["duration_ms"] = (chunks[1] - chunks[0]) // 1_000_000
            if extra["duration_ms"] is None:
                extra["timing_diagnostic"] = self.error or "missing_output_boundaries"
            results = {
                r["source_call_id"]: r
                for r in step.get("observation", {}).get("results", [])
            }
            for call in step.get("tool_calls", []):
                span = self.tools[call["tool_call_id"]]
                start = span.get("running", span.get("initial"))
                end = span.get("end")
                if not self.error:
                    if "timestamp" not in step and span["first"] is not None:
                        step["timestamp"] = self.timestamp(span["first"])
                        extra["timestamp_source"] = "acp_client_observed"
                    if start is not None:
                        call["extra"]["started_at"] = self.timestamp(start)
                error = self.error or span.get("error")
                if start is None or end is None:
                    error = error or "missing_tool_boundaries"
                result = results[call["tool_call_id"]]["extra"]
                result["execution_duration_ms"] = None
                if error:
                    result["timing_diagnostic"] = error
                    continue
                source = "in_progress" if "running" in span else "lifecycle"
                result.update(
                    execution_duration_ms=(end - start) // 1_000_000,
                    execution_duration_source=f"acp_client_observed_{source}",
                    finished_at=self.timestamp(end),
                )
        return {
            "timestamp_semantics": "event_observed",
            **({"timing_diagnostic": self.error} if self.error else {}),
        }
