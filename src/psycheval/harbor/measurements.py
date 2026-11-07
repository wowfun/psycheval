"""Bounded measurement evidence and pure value/provenance construction.

This module is part of the relocatable Harbor integration. Native collectors
pass whitelist records; neither private transcripts nor configuration belong here.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

EVIDENCE_SCHEMA = 1
CONTRACT_VERSION = 1
MANIFEST = "measurements.json"
EVENTS = "measurement-events.ndjson"
MAX_EVENT_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 100_000
MAX_MANIFEST_BYTES = 64 * 1024
MAX_PRIVATE_BYTES = 512 * 1024 * 1024
MAX_NATIVE_RECORD_BYTES = 16 * 1024 * 1024
MAX_PROVENANCE_BYTES = 2048
METRICS = (
    "score",
    "duration_ms",
    "ttft_ms",
    "tps",
    "tokens",
    "cache_hit_rate",
    "agent_steps",
    "model_duration_ms",
    "total_tool_calls",
    "tool_success_rate",
    "cost_usd",
    "last_turn_finished_at_ms",
)
_RECORD_FIELDS = frozenset(
    {
        "type",
        "id",
        "session_id",
        "step_id",
        "request_id",
        "call_id",
        "scope",
        "clock_id",
        "start_ms",
        "first_ms",
        "end_ms",
        "complete",
        "input_tokens",
        "output_tokens",
        "cached_tokens",
        "token_basis",
        "status",
        "exit_code",
        "is_error",
        "cancelled",
        "timed_out",
        "source",
        "source_sha256",
        "end_source_sha256",
        "cost_usd",
        "cost_kind",
        "parent_request_id",
        "parent_session_id",
        "includes_children",
        "diagnostic",
        "attempts",
    }
)


def number(value):
    try:
        return value if type(value) in (int, float) and math.isfinite(value) else None
    except OverflowError:
        return None


def nonnegative(value):
    value = number(value)
    return value if value is not None and value >= 0 else None


def encoded(value):
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode()


def measurement(
    value,
    *,
    source,
    method,
    basis,
    scope="main_session",
    unit="trial",
    version=CONTRACT_VERSION,
    quality="reported",
    fields=(),
    evidence=(),
    coverage=None,
    missing=None,
    producer=None,
    **details,
):
    """Construct a value and its explanation atomically at the selection branch."""
    value = number(value)
    provenance = {
        "contract_version": version,
        "source": source,
        "method": method,
        "basis_id": basis,
        "scope": scope,
        "sample_unit": unit,
        "quality": quality,
        "fields": list(fields),
        "evidence": list(evidence)[:4],
        "coverage": coverage
        or {
            "measured": int(value is not None),
            "unknown": int(value is None),
            "total": 1,
        },
        **(
            {"producer": {key: str(value)[:128] for key, value in producer.items()}}
            if producer
            else {}
        ),
        **details,
    }
    if value is None:
        provenance["missing_reason"] = missing or "missing_evidence"
    validate_provenance(provenance)
    return {"value": value, "provenance": provenance}


def validate_provenance(provenance):
    if len(encoded(provenance)) > MAX_PROVENANCE_BYTES:
        raise ValueError("metric_provenance_limit")
    if len(provenance.get("evidence", [])) > 4:
        raise ValueError("metric_evidence_reference_limit")


def _safe_record(record):
    if not isinstance(record, dict) or set(record) - _RECORD_FIELDS:
        raise ValueError("unapproved_measurement_fields")
    for key, value in record.items():
        if value is None or type(value) is bool:
            continue
        if isinstance(value, str) and len(value.encode()) <= 512:
            continue
        if number(value) is not None:
            continue
        raise ValueError("invalid_measurement_record")
    if record.get("type") not in {"step", "request", "tool", "end"}:
        raise ValueError("invalid_measurement_type")
    return record


def publish(
    directory,
    records,
    *,
    producer,
    invocation_id,
    session_id,
    capabilities,
    complete,
    diagnostics=(),
):
    """Publish a bounded prefix, then atomically commit its digest manifest."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    digest, size, count = hashlib.sha256(), 0, 0
    problems = list(diagnostics)
    temporary = directory / (EVENTS + ".tmp")
    try:
        with temporary.open("wb") as stream:
            for record in records:
                data = encoded(_safe_record(record)) + b"\n"
                if count >= MAX_RECORDS or size + len(data) > MAX_EVENT_BYTES:
                    problems.append("measurement_evidence_truncated")
                    complete = False
                    break
                stream.write(data)
                digest.update(data)
                count += 1
                size += len(data)
        temporary.replace(directory / EVENTS)
        manifest = {
            "schema_version": EVIDENCE_SCHEMA,
            "contract_version": CONTRACT_VERSION,
            "producer": producer,
            "invocation_id": invocation_id,
            "session_id": session_id,
            "capabilities": capabilities,
            "complete": bool(complete),
            "diagnostics": sorted(set(problems)),
            "events": {
                "path": EVENTS,
                "sha256": digest.hexdigest(),
                "bytes": size,
                "records": count,
            },
        }
        data = encoded(manifest)
        if len(data) > MAX_MANIFEST_BYTES:
            raise ValueError("measurement_manifest_limit")
        temporary = directory / (MANIFEST + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(directory / MANIFEST)
        return {
            "schema_version": EVIDENCE_SCHEMA,
            "contract_version": CONTRACT_VERSION,
            "path": MANIFEST,
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    finally:
        (directory / (EVENTS + ".tmp")).unlink(missing_ok=True)
        (directory / (MANIFEST + ".tmp")).unlink(missing_ok=True)


def _read(path, maximum):
    # The reader also serves imported evidence; never follow a linked parent.
    from .windows import open_read_descriptor

    for parent in (path, *path.parents):
        if parent.is_symlink() or parent.is_junction():
            raise ValueError("linked_measurement_evidence")
    with os.fdopen(open_read_descriptor(path), "rb") as stream:
        value = stream.read(maximum + 1)
    if len(value) > maximum:
        raise ValueError("measurement_evidence_limit")
    return value


def unavailable_marker():
    return {
        "schema_version": EVIDENCE_SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "status": "unavailable",
    }


def unavailable(
    directory,
    *,
    producer,
    invocation_id=None,
    session_id=None,
    reason="measurement_evidence_unavailable",
):
    try:
        return publish(
            directory,
            [],
            producer=producer,
            invocation_id=invocation_id,
            session_id=session_id,
            capabilities={
                "logical_steps": {
                    "status": "unavailable",
                    "reason": reason,
                    "evidence": "collector did not retain usable native evidence",
                }
            },
            complete=False,
            diagnostics=[reason],
        )
    except Exception:  # Optional publication must not replace an execution failure.
        return unavailable_marker()


def read(directory, marker, *, include_raw=False):
    """Validate a linked generation. Invalid new evidence never becomes legacy."""
    if (
        not isinstance(marker, dict)
        or marker.get("schema_version") != EVIDENCE_SCHEMA
        or marker.get("contract_version") != CONTRACT_VERSION
    ):
        raise ValueError("unsupported_measurement_contract")
    directory = Path(directory)
    raw = _read(directory / MANIFEST, MAX_MANIFEST_BYTES)
    if marker.get("path") != MANIFEST or hashlib.sha256(raw).hexdigest() != marker.get(
        "sha256"
    ):
        raise ValueError("measurement_manifest_digest")
    manifest = json.loads(raw)
    if (
        not isinstance(manifest, dict)
        or not isinstance(manifest.get("events"), dict)
        or not isinstance(manifest.get("producer"), dict)
        or not isinstance(manifest.get("capabilities"), dict)
        or any(not isinstance(item, dict) for item in manifest["capabilities"].values())
    ):
        raise ValueError("invalid_measurement_manifest")
    if (
        manifest.get("schema_version") != EVIDENCE_SCHEMA
        or manifest.get("contract_version") != CONTRACT_VERSION
    ):
        raise ValueError("unsupported_measurement_contract")
    descriptor = manifest["events"]
    if descriptor.get("path") != EVENTS:
        raise ValueError("measurement_event_path")
    raw = _read(directory / EVENTS, MAX_EVENT_BYTES)
    if len(raw) != descriptor.get("bytes") or hashlib.sha256(
        raw
    ).hexdigest() != descriptor.get("sha256"):
        raise ValueError("measurement_event_digest")
    lines = raw.splitlines()
    if len(lines) > MAX_RECORDS or len(lines) != descriptor.get("records"):
        raise ValueError("measurement_event_count")
    records = [_safe_record(json.loads(line)) for line in lines]
    return (manifest, records, raw) if include_raw else (manifest, records)


def artifact_id(filename):
    return hashlib.sha256(("measurement:" + filename).encode()).hexdigest()[:24]


def artifact(directory, identity):
    """Serve only validated reduced evidence through the existing admin reader."""
    filename = next(
        (name for name in (MANIFEST, EVENTS) if artifact_id(name) == identity), None
    )
    if filename is None:
        return None
    raw = _read(Path(directory) / MANIFEST, MAX_MANIFEST_BYTES)
    marker = {
        "schema_version": EVIDENCE_SCHEMA,
        "contract_version": CONTRACT_VERSION,
        "path": MANIFEST,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    _manifest, _records, events = read(directory, marker, include_raw=True)
    return filename, raw if filename == MANIFEST else events


def _unique(records, kind):
    by_id, conflicts = {}, set()
    for record in records:
        if record.get("type") != kind:
            continue
        identity = (record.get("session_id"), record.get("id"))
        if not all(isinstance(part, str) and part for part in identity):
            conflicts.add(identity)
        elif identity in by_id and by_id[identity] != record:
            conflicts.add(identity)
        else:
            by_id[identity] = record
    return [value for key, value in by_id.items() if key not in conflicts], len(
        conflicts
    )


def interval(row, start, end):
    first, last = nonnegative(row.get(start)), nonnegative(row.get(end))
    if not row.get("clock_id") or first is None or last is None or last < first:
        return None
    return last - first


def tool_outcome(row):
    """Structured execution results override a transport's completed status."""
    code = number(row.get("exit_code"))
    if (
        row.get("is_error")
        or row.get("cancelled")
        or row.get("timed_out")
        or (code is not None and code != 0)
    ):
        return "failed"
    if row.get("status") in {"error", "failed", "cancelled", "timeout"}:
        return "failed"
    if code == 0 or row.get("status") in {"success", "completed"}:
        return "success"
    return "unknown"


def trajectory_tools(trajectory):
    """Normalize existing structured observations without parsing output text."""
    session = trajectory.get("session_id") or "unknown"
    for step in trajectory.get("steps") or []:
        observations = (step.get("observation") or {}).get("results") or []
        for call in step.get("tool_calls") or []:
            identity = call.get("tool_call_id")
            if not isinstance(identity, str):
                continue
            matches = [
                item.get("extra") or {}
                for item in observations
                if item.get("source_call_id") == identity
            ]
            result = matches[0] if len(matches) == 1 else {}
            status = result.get("status", "unknown")
            yield {
                "type": "tool",
                "id": identity,
                "call_id": identity,
                "session_id": session,
                "scope": "main",
                "status": status,
                "exit_code": number(result.get("exit_code")),
                "is_error": result.get("is_error") is True
                and status not in {"incomplete", "unknown"},
                "cancelled": result.get("cancelled") is True,
                "timed_out": result.get("timed_out") is True,
            }


def calculate(manifest, records):
    """Compute native evidence metrics using matching samples and identities."""
    source = manifest["producer"]["name"]
    producer = manifest["producer"]
    capabilities = manifest.get("capabilities", {})
    complete = manifest.get("complete") is True
    evidence = [f"{MANIFEST}#{manifest['events']['sha256']}", EVENTS]
    results = {}
    steps, conflicts = _unique(
        (row for row in records if row.get("scope") == "main"), "step"
    )
    boundary = capabilities.get("logical_steps", {})
    timing = dict(
        start_boundary=boundary.get("start_boundary", "unverified"),
        end_boundary=boundary.get("end_boundary", "unverified"),
        retry_policy="included",
        clock=boundary.get("clock", {}),
    )
    verified = boundary.get("status") == "verified"
    target = len(steps) + conflicts
    durations, firsts, decode = [], [], []
    for step in steps:
        start_end = interval(step, "start_ms", "end_ms")
        start_first = interval(step, "start_ms", "first_ms")
        first_end = interval(step, "first_ms", "end_ms")
        if step.get("complete") and start_end is not None:
            durations.append(start_end)
        if start_first is not None and (
            step.get("end_ms") is None or first_end is not None
        ):
            firsts.append(start_first)
        output = nonnegative(step.get("output_tokens"))
        if (
            step.get("complete")
            and start_end is not None
            and start_first is not None
            and first_end is not None
            and first_end > 0
            and output is not None
            and step.get("token_basis") == "final_output_includes_reasoning"
        ):
            decode.append((output, first_end))
    for key, value, count, method in (
        (
            "model_duration_ms",
            sum(durations)
            if complete and target and len(durations) == target
            else None,
            len(durations),
            "sum(start_to_final_message_ms)",
        ),
        (
            "ttft_ms",
            sum(firsts) / len(firsts) if firsts else None,
            len(firsts),
            "mean(start_to_first_nonempty_output_ms)",
        ),
        (
            "tps",
            sum(x[0] for x in decode) * 1000 / sum(x[1] for x in decode)
            if decode
            else None,
            len(decode),
            "sum(final_output_tokens)/sum(first_output_to_final_message_seconds)",
        ),
    ):
        results[key] = measurement(
            value if verified else None,
            source=source,
            method=method,
            basis=source + ":" + str(boundary.get("basis_id", "unverified")),
            quality=(
                boundary.get("first_output_quality", "reported")
                if key in {"ttft_ms", "tps"}
                else "reported"
            ),
            unit="logical_step",
            producer=producer,
            evidence=evidence,
            fields=("start_ms", "first_ms", "end_ms", "output_tokens"),
            coverage={
                "measured": count if verified else 0,
                "unknown": target - count if verified else None,
                "total": target if complete and verified else None,
                "retained": target,
            },
            missing=boundary.get("reason")
            if not verified
            else "incomplete_boundaries_or_usage",
            token_basis="final_output_includes_reasoning",
            **timing,
        )
    requests, conflicts = _unique(records, "request")
    # An explicitly aggregate parent excludes its identified children, recursively.
    by_id = {(row["session_id"], row["id"]): row for row in requests}

    def covered_by_parent(row):
        seen = {(row["session_id"], row["id"])}
        while row.get("parent_request_id"):
            key = (
                row.get("parent_session_id", row["session_id"]),
                row["parent_request_id"],
            )
            if key in seen:
                return False
            seen.add(key)
            row = by_id.get(key, {})
            if row.get("includes_children"):
                return True
        return False

    requests = [row for row in requests if not covered_by_parent(row)]
    totals, cache, costs = [], [], []
    for row in requests:
        prompt, output, cached = (
            nonnegative(row.get(k))
            for k in ("input_tokens", "output_tokens", "cached_tokens")
        )
        if prompt is not None and output is not None:
            totals.append(prompt + output)
        if prompt is not None and cached is not None and cached <= prompt:
            cache.append((prompt, cached))
        cost = nonnegative(row.get("cost_usd"))
        if cost is not None and row.get("cost_kind") in {"native_estimate", "billed"}:
            costs.append(cost)
    target = len(requests) + conflicts
    cost_kinds = sorted(
        {
            row["cost_kind"]
            for row in requests
            if row.get("cost_kind") in {"native_estimate", "billed"}
        }
    )
    for key, value, count, method, missing in (
        (
            "tokens",
            sum(totals) if complete and target and len(totals) == target else None,
            len(totals),
            "sum(input_including_cache+output)",
            "incomplete_request_usage",
        ),
        (
            "cache_hit_rate",
            sum(x[1] for x in cache) / sum(x[0] for x in cache)
            if sum(x[0] for x in cache) > 0
            else None,
            len(cache),
            "sum(cache_read)/sum(input_including_cache)",
            "missing_cache_samples",
        ),
        (
            "cost_usd",
            sum(costs) if complete and target and len(costs) == target else None,
            len(costs),
            "sum(native_request_cost)",
            "no_trustworthy_cost",
        ),
    ):
        results[key] = measurement(
            value,
            source=source,
            method=method,
            basis=method
            + (":" + "+".join(cost_kinds) if key == "cost_usd" and cost_kinds else ""),
            quality="estimated"
            if key == "cost_usd" and "native_estimate" in cost_kinds
            else "reported",
            scope="harbor_visible_trajectory_tree",
            unit="request",
            producer=producer,
            fields=("input_tokens", "output_tokens", "cached_tokens")
            if key != "cost_usd"
            else ("cost_usd", "cost_kind"),
            evidence=evidence,
            missing=missing,
            coverage={
                "measured": count,
                "unknown": target - count,
                "total": target if complete else None,
                "retained": target,
            },
            background_requests="not_covered",
            **({"cost_kinds": cost_kinds} if key == "cost_usd" else {}),
        )
    tools, conflicts = _unique(
        (row for row in records if row.get("scope") == "main"), "tool"
    )
    outcomes = [tool_outcome(row) for row in tools]
    successes, failures = outcomes.count("success"), outcomes.count("failed")
    known = successes + failures
    results["tool_success_rate"] = measurement(
        successes / known if known else None,
        source=source,
        method="successes/known",
        basis="tool_known_outcomes_v1",
        unit="tool_call",
        fields=("exit_code", "is_error", "cancelled", "timed_out", "status"),
        producer=producer,
        evidence=evidence,
        coverage={
            "measured": known,
            "success": successes,
            "failed": failures,
            "unknown": len(tools) - known + conflicts,
            "total": len(tools) + conflicts if complete else None,
            "retained": len(tools) + conflicts,
        },
        missing="no_known_tool_outcomes",
    )
    ends, end_conflicts = _unique(records, "end")
    ends = [
        row
        for row in ends
        if row.get("scope") == "main"
        and row.get("clock_id")
        and nonnegative(row.get("end_ms")) is not None
    ]
    if ends and not end_conflicts:
        end = max(ends, key=lambda row: row["end_ms"])
        results["last_turn_finished_at_ms"] = measurement(
            end["end_ms"],
            source=source,
            method="native_end_event",
            basis=source + ":" + end.get("source", "native_end"),
            fields=("end_ms",),
            evidence=evidence,
            producer=producer,
            end_boundary=end.get("source"),
            clock={
                "id": end["clock_id"],
                "type": "epoch",
                "unit": "ms",
                "semantics": "native_event",
            },
        )
    return results
