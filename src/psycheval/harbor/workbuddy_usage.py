"""Bounded, invocation-local accounting from WorkBuddy's private native history."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from pathlib import Path

from .acp_evidence import _events
from .acp_protocol import MAX_EVENT_FRAME, MAX_EVIDENCE_FRAMES
from .inference_telemetry import InferenceObservation, metrics_from_observations
from .windows import open_read_descriptor

USAGE_FILENAME = "workbuddy.usage.json"
MAX_USAGE_BYTES = 8 * 1024 * 1024
MAX_HISTORY_FILES = 1024


class UsageLimitError(ValueError):
    """A categorical history or usage admission limit, safe to retain in diagnostics."""


_COUNTERS = {
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "inputTokens",
    "outputTokens",
    "totalTokens",
    "cached_tokens",
    "cache_read_tokens",
    "cacheReadTokens",
    "cacheReadInputTokens",
    "cache_read_input_tokens",
    "prompt_cache_hit_tokens",
    "prompt_cache_miss_tokens",
    "cache_write_tokens",
    "cacheWriteTokens",
    "cacheCreationInputTokens",
    "cache_creation_input_tokens",
}
_DETAILS = {
    "prompt_tokens_details",
    "completion_tokens_details",
    "inputTokensDetails",
    "outputTokensDetails",
    "input_tokens_details",
    "output_tokens_details",
}
_DETAIL_COUNTERS = {
    "cached_tokens",
    "reasoning_tokens",
    "cache_creation_tokens",
    "cache_write_tokens",
}
_FIELDS = ("prompt_tokens", "completion_tokens", "cached_tokens", "cache_write_tokens")


def _identity(value):
    return isinstance(value, str) and 0 < len(value) <= 512 and "\0" not in value


def _safe_path(path, checked=None):
    for parent in (path, *path.parents):
        if checked is not None and parent in checked:
            break
        if parent.is_symlink() or parent.is_junction():
            raise ValueError("linked_history")
        if checked is not None:
            checked.add(parent)


@contextmanager
def _open_history(path):
    _safe_path(path)
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("nonregular_history")
    with os.fdopen(open_read_descriptor(path), "rb") as stream:
        opened = os.fstat(stream.fileno())
        current = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or getattr(opened, "st_file_attributes", 0) & 0x400
            or not os.path.samestat(before, opened)
            or not os.path.samestat(current, opened)
        ):
            raise ValueError("replaced_history")
        yield stream, opened
        after = path.stat(follow_symlinks=False)
        if not os.path.samestat(opened, after) or (
            opened.st_size,
            opened.st_mtime_ns,
        ) != (after.st_size, after.st_mtime_ns):
            raise ValueError("changing_history")


def _files(root):
    checked = set()
    _safe_path(root, checked)
    if not root.exists():
        return []
    result = []
    for index, project in enumerate(root.iterdir()):
        if index >= MAX_HISTORY_FILES:
            raise UsageLimitError("history_file_limit")
        _safe_path(project, checked)
        if not project.is_dir():
            continue
        for child_index, path in enumerate(project.iterdir()):
            if child_index >= MAX_HISTORY_FILES or len(result) >= MAX_HISTORY_FILES:
                raise UsageLimitError("history_file_limit")
            if path.suffix == ".jsonl":
                _safe_path(path, checked)
                result.append(path)
    return sorted(result)


def _hash_prefix(stream, count):
    digest = hashlib.sha256()
    last = b""
    while count:
        chunk = stream.read(min(count, 65536))
        if not chunk:
            raise ValueError("truncated_history")
        digest.update(chunk)
        last = chunk[-1:]
        count -= len(chunk)
    return digest, last


@dataclass(frozen=True)
class HistoryBaseline:
    files: dict
    diagnostics: tuple[str, ...] = ()
    cache: dict = dataclass_field(default_factory=dict)


def _signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def history_baseline(root: Path, maximum: int, *, cache=None) -> HistoryBaseline:
    files = {}
    cache = {} if cache is None else cache
    remaining = maximum
    try:
        paths = _files(root)
        names = {str(path.relative_to(root)) for path in paths}
        for relative in set(cache) - names:
            del cache[relative]
        for path in paths:
            with _open_history(path) as (stream, info):
                relative = str(path.relative_to(root))
                saved = cache.get(relative)
                digest = None
                if saved and saved[0] == _signature(info):
                    digest = saved[1]
                elif info.st_size <= remaining:
                    hashed, last = _hash_prefix(stream, info.st_size)
                    if info.st_size and last != b"\n":
                        raise ValueError("incomplete_baseline")
                    remaining -= info.st_size
                    digest = hashed.hexdigest()
                files[relative] = (
                    info.st_dev,
                    info.st_ino,
                    info.st_size,
                    digest,
                )
            if digest is not None:
                cache[relative] = (_signature(info), digest)
            else:
                cache.pop(relative, None)
    except UsageLimitError as error:
        return HistoryBaseline({}, (str(error),), cache)
    except Exception:  # noqa: BLE001 - baseline observation must not prevent execution.
        return HistoryBaseline({}, ("baseline_unavailable",), cache)
    return HistoryBaseline(files, cache=cache)


def prompt_requests(directory: Path, summary: dict):
    requests, conversations, usage = set(), set(), []
    for event in _events(
        directory / "acp.events.ndjson.gz",
        summary["max_evidence_bytes"],
        summary.get("max_decoded_evidence_bytes"),
    ):
        message = event["message"]
        if (event["direction"], event["phase"], message.get("method")) != (
            "receive",
            "prompt",
            "session/update",
        ):
            continue
        params = message.get("params", {})
        if params.get("sessionId") != summary.get("session_id"):
            raise ValueError("unrelated_session")
        update = params.get("update", {})
        meta = update.get("_meta") or {}
        request = meta.get("codebuddy.ai/modelRequestId")
        conversation = meta.get("codebuddy.ai/conversationRequestId") or meta.get(
            "codebuddy.ai/requestId"
        )
        if _identity(request):
            requests.add(request)
        if _identity(conversation):
            conversations.add(conversation)
        if update.get("sessionUpdate") == "usage_update" and isinstance(
            meta.get("usage"), dict
        ):
            usage.append(
                (meta.get("codebuddy.ai/messageId"), _retain_usage(meta["usage"]))
            )
    return requests, conversations, usage


def _retain_usage(value):
    if not isinstance(value, dict):
        return {}
    result = {
        key: item
        for key, item in value.items()
        if key in _COUNTERS and (type(item) is int or item is None)
    }
    for key in _DETAILS:
        detail = value.get(key)
        if isinstance(detail, dict):
            result[key] = {
                k: v
                for k, v in detail.items()
                if k in _DETAIL_COUNTERS and (type(v) is int or v is None)
            }
        elif isinstance(detail, list) and len(detail) <= MAX_EVIDENCE_FRAMES:
            result[key] = [_retain_detail(item) for item in detail]
    return result


def _retain_detail(value):
    if not isinstance(value, dict):
        return {}
    return {
        key: item
        for key, item in value.items()
        if key in _DETAIL_COUNTERS and (type(item) is int or item is None)
    }


def capture_usage(root, directory, summary, baseline, cli_version):
    requests, conversations, acp_usage = prompt_requests(directory, summary)
    evidence = {
        "schema_version": 1,
        "invocation_id": summary["invocation_id"],
        "session_id": summary["session_id"],
        "cli_version": cli_version,
        "expected_requests": sorted(requests),
        "conversation_requests": sorted(conversations),
        "sources": [],
        "records": [],
        "diagnostics": list(baseline.diagnostics),
        "acp_usage": [
            {"message_id": identity, "usage": value}
            for identity, value in acp_usage
            if _identity(identity)
        ],
    }
    if baseline.diagnostics:
        return evidence
    remaining = summary["max_evidence_bytes"]
    admitted = 0
    candidates = [
        path for path in _files(root) if path.name == summary["session_id"] + ".jsonl"
    ]
    if len(candidates) != 1:
        evidence["diagnostics"].append("native_session_unavailable")
        return evidence
    for path in candidates:
        relative = str(path.relative_to(root))
        with _open_history(path) as (stream, info):
            if info.st_size > remaining:
                raise UsageLimitError("history_byte_limit")
            previous = baseline.files.get(relative)
            offset = 0
            digest = hashlib.sha256()
            if previous:
                if (info.st_dev, info.st_ino) != previous[
                    :2
                ] or info.st_size < previous[2]:
                    raise ValueError("replaced_baseline")
                if previous[3] is None:
                    raise UsageLimitError("baseline_byte_limit")
                digest, _ = _hash_prefix(stream, previous[2])
                if digest.hexdigest() != previous[3]:
                    raise ValueError("changed_baseline")
                offset = previous[2]
            complete = offset == info.st_size
            for index in range(MAX_EVIDENCE_FRAMES + 1):
                line = stream.readline(MAX_EVENT_FRAME + 1)
                if not line:
                    break
                digest.update(line)
                if index == MAX_EVIDENCE_FRAMES or len(line) > MAX_EVENT_FRAME:
                    raise UsageLimitError("history_line_limit")
                complete = line.endswith(b"\n")
                if not complete:
                    evidence["diagnostics"].append("incomplete_native_tail")
                    break
                try:
                    item = json.loads(line)
                    if isinstance(item, dict) and isinstance(item.get("payload"), dict):
                        item = item["payload"]
                    if (
                        item.get("sessionId", summary["session_id"])
                        != summary["session_id"]
                    ):
                        raise ValueError("unrelated_native_session")
                    provider = item.get("providerData", {})
                    raw, normalized = provider.get("rawUsage"), provider.get("usage")
                    if isinstance(raw, dict) or isinstance(normalized, dict):
                        conversation = provider.get("conversationRequestId")
                        request = provider.get("messageId")
                        if conversation in conversations:
                            if not _identity(request):
                                evidence["diagnostics"].append(
                                    "native_request_identity_missing"
                                )
                            else:
                                record = {
                                    "source": relative,
                                    "offset": offset,
                                    "history_id": item.get("id")
                                    if _identity(item.get("id"))
                                    else None,
                                    "conversation_request_id": conversation,
                                    "model_request_id": request,
                                    "raw_usage": _retain_usage(raw),
                                    "usage": _retain_usage(normalized),
                                }
                                admitted += len(json.dumps(record).encode("utf-8"))
                                if admitted > MAX_USAGE_BYTES - 65536:
                                    evidence["diagnostics"].append("usage_byte_limit")
                                    break
                                evidence["records"].append(record)
                        elif conversation is None:
                            evidence["diagnostics"].append(
                                "native_conversation_identity_missing"
                            )
                except (ValueError, TypeError, AttributeError, RecursionError):
                    evidence["diagnostics"].append("invalid_native_record")
                offset += len(line)
            evidence["sources"].append(
                {
                    "path": relative,
                    "bytes": info.st_size,
                    "baseline_bytes": previous[2] if previous else 0,
                    "hashed_bytes": stream.tell(),
                    "sha256": digest.hexdigest(),
                }
            )
            cached = (
                (_signature(info), digest.hexdigest())
                if (complete and stream.tell() == info.st_size)
                else None
            )
        if cached is not None:
            baseline.cache[relative] = cached
    evidence["diagnostics"] = sorted(set(evidence["diagnostics"]))
    return evidence


def publish_usage(path, evidence):
    content = (
        json.dumps(evidence, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    if len(content) > MAX_USAGE_BYTES:
        raise UsageLimitError("usage_byte_limit")
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_bytes(content)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return hashlib.sha256(content).hexdigest()


def _count(value):
    return value if type(value) is int and value >= 0 else None


def _consistent(values, conflicts=None, field=None):
    known = {_count(value) for value in values if value is not None}
    if None in known or len(known) != 1:
        if known and conflicts is not None:
            conflicts.add(field)
        return None
    return next(iter(known))


def _detail(value, field):
    if isinstance(value, dict):
        return value.get(field)
    if isinstance(value, list) and value:
        counts = [
            _count(item.get(field)) if isinstance(item, dict) else None
            for item in value
        ]
        return sum(counts) if all(item is not None for item in counts) else None
    return None


def normalize_usage(value, *, conflicts=None):
    """Normalize native provider/SDK components, without inferring cache writes."""
    value = value if isinstance(value, dict) else {}
    prompt = _consistent(
        [value.get(key) for key in ("prompt_tokens", "inputTokens", "input_tokens")],
        conflicts,
        "prompt_tokens",
    )
    completion = _consistent(
        [
            value.get(key)
            for key in ("completion_tokens", "outputTokens", "output_tokens")
        ],
        conflicts,
        "completion_tokens",
    )
    cached = _consistent(
        [
            *(
                value.get(key)
                for key in (
                    "cached_tokens",
                    "cache_read_tokens",
                    "cacheReadTokens",
                    "cacheReadInputTokens",
                    "cache_read_input_tokens",
                    "prompt_cache_hit_tokens",
                )
            ),
            *(
                _detail(value.get(key), "cached_tokens")
                for key in (
                    "prompt_tokens_details",
                    "inputTokensDetails",
                    "input_tokens_details",
                )
            ),
        ],
        conflicts,
        "cached_tokens",
    )
    write = _consistent(
        [
            *(
                value.get(key)
                for key in (
                    "cache_write_tokens",
                    "cacheWriteTokens",
                    "cacheCreationInputTokens",
                    "cache_creation_input_tokens",
                )
            ),
            *(
                _detail(value.get(key), field)
                for key in (
                    "prompt_tokens_details",
                    "inputTokensDetails",
                    "input_tokens_details",
                )
                for field in ("cache_creation_tokens", "cache_write_tokens")
            ),
        ],
        conflicts,
        "cache_write_tokens",
    )
    # Native Anthropic provider input excludes cache reads and creations. SDK
    # inputTokens and OpenAI prompt_tokens are already inclusive.
    if (
        "input_tokens" in value
        and not any(key in value for key in ("prompt_tokens", "inputTokens"))
        and any(
            key in value
            for key in ("cache_read_input_tokens", "cache_creation_input_tokens")
        )
    ):
        prompt = (
            prompt + cached + write
            if all(item is not None for item in (prompt, cached, write))
            else None
        )
    if cached is not None and (prompt is None or cached > prompt):
        if conflicts is not None and prompt is not None:
            conflicts.add("cached_tokens")
        cached = None
    return dict(zip(_FIELDS, (prompt, completion, cached, write)))


def project_usage(trajectory, evidence, digest):
    """Use the native request ledger once; ACP snapshots never add consumption."""
    measurements = defaultdict(lambda: {field: set() for field in _FIELDS})
    invalid = defaultdict(set)
    for record in evidence.get("records", []):
        request = record["model_request_id"]
        raw = normalize_usage(record["raw_usage"], conflicts=invalid[request])
        normalized_conflicts = set()
        normalized = normalize_usage(record["usage"], conflicts=normalized_conflicts)
        for field in _FIELDS:
            value = raw[field] if raw[field] is not None else normalized[field]
            if raw[field] is None and field in normalized_conflicts:
                invalid[request].add(field)
            # This CLI's SDK supplies cached_tokens=0 even when the provider
            # omitted cache measurements. Only a provider measurement proves zero.
            if field == "cached_tokens" and (
                (raw[field] is None and (normalized[field] == 0 or record["raw_usage"]))
                or (
                    raw[field] == 0
                    and "inputTokens" in record["raw_usage"]
                    and not any(
                        key in record["raw_usage"]
                        for key in (
                            "cached_tokens",
                            "cache_read_input_tokens",
                            "prompt_cache_hit_tokens",
                        )
                    )
                )
            ):
                value = None
            if value is not None:
                measurements[request][field].add(value)
        measurements[request]  # Keep requests whose components are all unknown.
    expected = set(evidence.get("expected_requests", [])) | set(measurements)
    for update in evidence.get("acp_usage", []):
        request = update["message_id"]
        if request not in measurements:
            continue
        for field, value in normalize_usage(update["usage"]).items():
            if value is not None and measurements[request][field]:
                measurements[request][field].add(value)
    observations = {}
    conflicts = 0
    for request, fields in measurements.items():
        values = {}
        for field, known in fields.items():
            conflict = len(known) > 1 or field in invalid[request]
            values[field] = (
                next(iter(known)) if len(known) == 1 and not conflict else None
            )
            conflicts += conflict
        if values["cached_tokens"] is not None and (
            values["prompt_tokens"] is None
            or values["cached_tokens"] > values["prompt_tokens"]
        ):
            values["cached_tokens"] = None
        observations[request] = InferenceObservation(
            **values, usage_source="workbuddy.native_history"
        )
    diagnostics = list(evidence.get("diagnostics", []))
    if conflicts:
        diagnostics.append("conflicting_usage")
    covered = {
        field: sum(
            getattr(observations.get(request), field, None) is not None
            for request in expected
        )
        for field in _FIELDS
    }
    extra = trajectory.setdefault("extra", {})
    extra["workbuddy_usage"] = {
        "path": USAGE_FILENAME,
        "sha256": digest,
        "expected_requests": len(expected),
        "observed_requests": len(observations),
        "coverage": covered,
        "diagnostics": sorted(set(diagnostics)),
        "status": "complete"
        if expected
        and not diagnostics
        and all(covered[field] == len(expected) for field in _FIELDS[:3])
        else "partial",
    }
    owners = defaultdict(list)
    for step in trajectory["steps"]:
        for request in (step.get("extra") or {}).get("workbuddy_model_request_ids", []):
            owners[request].append(step)
    by_step = defaultdict(list)
    for request, observation in observations.items():
        if len(owners[request]) == 1:
            by_step[owners[request][0]["step_id"]].append(observation)
    for step in trajectory["steps"]:
        aligned = by_step.get(step["step_id"])
        if aligned:
            step["metrics"] = metrics_from_observations(aligned)
            step["llm_call_count"] = len(aligned)
    metrics = metrics_from_observations(observations.values())
    if metrics:
        final = trajectory.setdefault("final_metrics", {})
        for source, target in (
            ("prompt_tokens", "total_prompt_tokens"),
            ("completion_tokens", "total_completion_tokens"),
            ("cached_tokens", "total_cached_tokens"),
        ):
            if (
                not evidence.get("diagnostics")
                and expected
                and covered[source] == len(expected)
                and source in metrics
            ):
                final[target] = metrics[source]
        final["total_steps"] = len(trajectory["steps"])
        final["extra"] = {**(final.get("extra") or {}), **metrics["extra"]}
    return trajectory
