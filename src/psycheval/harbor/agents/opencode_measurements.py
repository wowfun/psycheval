"""Normalize whitelisted OpenCode hook observations against native message IDs."""

from ..measurements import MAX_EVENT_BYTES, trajectory_tools
from .dsh_measurements import bounded_records


def capture(path, trajectory):
    session = trajectory.get("session_id")
    requests, steps, diagnostics, ends = {}, {}, [], []
    request_events, request_conflicts = {}, set()
    loaded = False
    if not path.exists():
        return [], False, False, ["plugin_not_loaded"]
    for event in bounded_records(path, [MAX_EVENT_BYTES], diagnostics):
        kind = event.get("kind")
        if kind == "loaded":
            loaded = True
            continue
        if kind in {
            "truncated",
            "unlinked_response",
            "unsupported_protocol",
            "invalid_stream",
            "observer_error",
            "event_subscription_failed",
        }:
            diagnostics.append(kind)
            continue
        if event.get("session") != session:
            continue  # Unassociated background/child requests are not visible-tree evidence.
        base = {
            "session_id": session,
            "scope": "main",
            "clock_id": "opencode:" + session + ":epoch_ms",
        }
        identity = event.get("id")
        if kind == "request":
            if identity in requests:
                if request_events[identity] == event:
                    continue
                diagnostics.append("duplicate_request_identity")
                request_conflicts.add(identity)
                continue
            request_events[identity] = event
            requests[identity] = {
                **base,
                "type": "request",
                "id": identity,
                "request_id": identity,
            }
        elif kind in {"output", "usage"}:
            request = requests.get(identity)
            if request is None:
                diagnostics.append("unlinked_request_event")
                continue
            if kind == "output":
                request.setdefault("first_ms", event.get("time"))
            else:
                request.update(
                    {
                        k: event[k]
                        for k in ("input_tokens", "output_tokens", "cached_tokens")
                        if k in event
                    }
                )
        elif kind == "session.step.started":
            message, request_id = event.get("message"), event.get("request")
            if not message or request_id not in requests:
                diagnostics.append("unlinked_native_step")
                continue
            request = requests[request_id]
            if request.get("step_id") not in {None, message}:
                diagnostics.append("request_step_identity_conflict")
                continue
            request["step_id"] = message
            start = event.get("start")
            step = steps.setdefault(
                message,
                {
                    **base,
                    "type": "step",
                    "id": message,
                    "step_id": message,
                    "start_ms": start,
                    "complete": False,
                    "attempts": 0,
                },
            )
            step["attempts"] += 1
            # Retries repeat Step.Started for the SAME native assistant ID.
            if (
                start is not None
                and step.get("start_ms") is not None
                and start < step["start_ms"]
            ):
                diagnostics.append("out_of_order_native_start")
        elif kind == "session.step.streamed":
            step = steps.get(event.get("message"))
            request = requests.get(event.get("request"))
            if (
                step is None
                or request is None
                or request.get("step_id") != event.get("message")
            ):
                diagnostics.append("unlinked_native_completion")
                continue
            if step.get("complete") and step.get("end_ms") != event.get("time"):
                diagnostics.append("conflicting_native_completion")
                continue
            step.update(
                end_ms=event.get("time"),
                complete=True,
                output_tokens=request.get("output_tokens"),
                token_basis="final_output_includes_reasoning",
            )
        elif kind == "session.step.ended" and event.get("message") in steps:
            ends.append(
                {
                    **base,
                    "type": "end",
                    "id": event["message"],
                    "end_ms": event.get("time"),
                    "source": "session.step.ended",
                }
            )
    for request in requests.values():
        step = steps.get(request.get("step_id"))
        first = request.get("first_ms")
        if step is not None and first is not None:
            step["first_ms"] = min(step.get("first_ms", first), first)
    if not loaded:
        diagnostics.append("plugin_not_loaded")
    if not steps:
        diagnostics.append("native_step_boundaries_unavailable")
    if any(not r.get("step_id") for r in requests.values()):
        diagnostics.append("unlinked_request")
    # A collection warning is not an identity failure: a retained prefix still
    # supplies valid samples. Stream parsing cannot disprove native boundaries.
    identity_errors = {
        "duplicate_request_identity",
        "unlinked_request_event",
        "unlinked_native_step",
        "request_step_identity_conflict",
        "out_of_order_native_start",
        "unlinked_native_completion",
        "conflicting_native_completion",
        "unlinked_request",
        "unlinked_response",
    }
    linked = loaded and bool(steps) and not identity_errors.intersection(diagnostics)
    ended = {row["id"] for row in ends}
    complete = (
        linked
        and set(steps).issubset(ended)
        and not (set(diagnostics) - {"unsupported_protocol", "invalid_stream"})
    )
    return (
        [
            *steps.values(),
            *requests.values(),
            # Let the shared identity constructor exclude ambiguous requests
            # from subset statistics as well as complete totals.
            *(
                {**requests[key], "diagnostic": "identity_conflict"}
                for key in request_conflicts
            ),
            *trajectory_tools(trajectory),
            *ends,
        ],
        linked,
        complete,
        sorted(set(diagnostics)),
    )
