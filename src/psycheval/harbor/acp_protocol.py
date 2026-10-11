"""Strict, bounded wire transport around the optional ACP SDK."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
from functools import cache
from pathlib import Path

MAX_FRAME = 1024 * 1024
MAX_EVENT_FRAME = 2 * MAX_FRAME
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 65536
MAX_CONFIG_OPTIONS = 8
MAX_CONFIG_ID_BYTES = 256
MAX_CONFIG_VALUE_BYTES = 2048
MAX_EVIDENCE_FRAMES = 65536
DEFAULT_MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
FORCED_CLEANUP_RESERVE_SEC = 5
KILL_REAP_RESERVE_SEC = 2
EVIDENCE_FILES = (
    "acp.stdin.ndjson",
    "acp.stdout.ndjson",
    "acp.events.ndjson",
    "acp.stderr.log",
)


class ProtocolError(ValueError):
    """Categorical wire failure; diagnostics never echo peer payloads."""


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ProtocolError("duplicate JSON key")
        value[key] = item
    return value


def _constant(_):
    raise ProtocolError("non-finite JSON number")


def decode(line: bytes) -> dict:
    if not line.endswith(b"\n") or not line.strip() or len(line) - 1 > MAX_FRAME:
        raise ProtocolError("invalid or oversized NDJSON record")
    try:
        value = json.loads(
            line.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant
        )
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ProtocolError("invalid JSON record") from exc
    return _validate_message(value)


def _validate_message(value: dict) -> dict:
    if not isinstance(value, dict) or value.get("jsonrpc") != "2.0":
        raise ProtocolError("invalid JSON-RPC envelope")
    if "id" in value and (
        type(value["id"]) not in {int, str}
        or value["id"] == ""
        or len(str(value["id"]).encode()) > 128
    ):
        raise ProtocolError("invalid correlation identity")
    if "method" in value:
        if (
            not isinstance(value["method"], str)
            or not value["method"]
            or not isinstance(value.get("params", {}), dict)
            or "result" in value
            or "error" in value
        ):
            raise ProtocolError("invalid request envelope")
    elif "id" not in value or ("result" in value) == ("error" in value):
        raise ProtocolError("invalid response envelope")
    nodes = [(value, 0)]
    count = 0
    while nodes:
        item, depth = nodes.pop()
        count += 1
        if depth > MAX_JSON_DEPTH or count > MAX_JSON_NODES:
            raise ProtocolError("JSON structure exceeds limits")
        if isinstance(item, float) and not math.isfinite(item):
            raise ProtocolError("non-finite JSON number")
        if isinstance(item, dict):
            nodes.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            nodes.extend((child, depth + 1) for child in item)
    return value


@cache
def _sdk_validator(name):
    from acp import schema
    from jsonschema import Draft202012Validator

    return Draft202012Validator(getattr(schema, name).model_json_schema(by_alias=True))


@cache
def sdk_validators():
    names = {
        "initialize": "InitializeResponse",
        "authenticate": "AuthenticateResponse",
        "session/new": "NewSessionResponse",
        "session/load": "LoadSessionResponse",
        "session/resume": "ResumeSessionResponse",
        "session/set_config_option": "SetSessionConfigOptionResponse",
        "session/prompt": "PromptResponse",
        "session/update": "SessionNotification",
        "session/request_permission": "RequestPermissionRequest",
    }
    return {method: _sdk_validator(name) for method, name in names.items()}


def validate_payload(validator, value):
    if next(validator.iter_errors(value), None) is not None:
        raise ProtocolError("invalid known ACP payload")
    if isinstance(value, dict):
        update = value.get("update", value)
        if isinstance(update, dict):
            if "name" in update and (
                not isinstance(update["name"], str) or not update["name"]
            ):
                raise ProtocolError("invalid tool name")
            options = update.get("configOptions", [])
            if not isinstance(options, list) or len(options) > 64:
                raise ProtocolError("invalid configuration list")
            ids = set()
            for option in options:
                if (
                    next(
                        _sdk_validator("SessionConfigOptionSelect").iter_errors(option),
                        None,
                    )
                    is not None
                ):
                    raise ProtocolError("invalid select configuration option")
                if option["id"] in ids or option.get("type") != "select":
                    raise ProtocolError("duplicate or unsupported configuration option")
                ids.add(option["id"])
                choices = option["options"]
                flat = []
                grouped = any("group" in choice for choice in choices)
                for choice in choices:
                    if grouped != ("group" in choice):
                        raise ProtocolError("mixed configuration groups")
                    flat.extend(choice["options"] if grouped else [choice])
                values = [choice["value"] for choice in flat]
                if (
                    len(flat) > 4096
                    or len(set(values)) != len(values)
                    or option["currentValue"] not in values
                ):
                    raise ProtocolError("invalid configuration choices")
                if any(
                    not choice or len(choice.encode()) > MAX_CONFIG_VALUE_BYTES
                    for choice in values
                ):
                    raise ProtocolError("invalid configuration value")


def evidence_manifest(directory: Path, maximum=DEFAULT_MAX_EVIDENCE_BYTES):
    if type(maximum) is not int or maximum <= 0:
        raise ProtocolError("invalid retained evidence byte budget")
    files, consumed = {}, 0
    for name in EVIDENCE_FILES:
        path = directory / name
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file():
            raise ProtocolError("invalid retained evidence file")
        digest, size = hashlib.sha256(), 0
        with path.open("rb") as stream:
            while chunk := stream.read(64 * 1024):
                size += len(chunk)
                consumed += len(chunk)
                if consumed > maximum:
                    raise ProtocolError("retained ACP evidence exceeds byte budget")
                digest.update(chunk)
        files[name] = {"bytes": size, "sha256": digest.hexdigest()}
    return files


def verify_evidence(directory: Path, summary: dict):
    expected = summary.get("evidence_files")
    if (
        not isinstance(summary.get("invocation_id"), str)
        or not summary["invocation_id"]
        or not isinstance(expected, dict)
        or set(expected) != set(EVIDENCE_FILES)
        or evidence_manifest(
            directory, summary.get("max_evidence_bytes", DEFAULT_MAX_EVIDENCE_BYTES)
        )
        != expected
    ):
        raise ProtocolError("retained ACP evidence integrity failed")


class EvidenceBudget:
    """One invocation's shared wire, event and stderr admission budget."""

    def __init__(self, summary: dict, maximum: int = DEFAULT_MAX_EVIDENCE_BYTES):
        if type(maximum) is not int or maximum <= 0:
            raise ValueError("ACP evidence byte budget must be a positive integer")
        self.summary, self.maximum = summary, maximum
        self.summary["max_evidence_bytes"] = maximum
        self.bytes = self.frames = 0

    def _exhausted(self):
        self.summary.update(protocol_complete=False, evidence_limit_exceeded=True)
        raise ProtocolError("ACP evidence admission exceeded")

    def admit_frame(self):
        if self.frames >= MAX_EVIDENCE_FRAMES:
            self._exhausted()
        self.frames += 1

    def write(self, stream, data: bytes):
        if len(data) > self.maximum - self.bytes:
            self._exhausted()
        stream.write(data)
        stream.flush()
        self.bytes += len(data)

    def retain(self, value):
        size = (
            len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())
            + 1
        )
        if size > self.maximum - self.bytes:
            self._exhausted()
        self.bytes += size


class StrictTransport:
    """SDK message transport retaining wire order before permissive DTO parsing."""

    def __init__(self, reader, writer, directory: Path, summary: dict, budget=None):
        self.reader, self.writer, self.summary = reader, writer, summary
        self.budget = budget if budget is not None else EvidenceBudget(summary)
        self.validators = sdk_validators()
        self.pending = {}
        self.phase = "setup"
        self.replay_id = None
        self.raw_in = (directory / "acp.stdout.ndjson").open("wb")
        self.raw_out = (directory / "acp.stdin.ndjson").open("wb")
        self.events = (directory / "acp.events.ndjson").open("wb")

    def record(self, direction, message):
        data = (
            json.dumps(
                {"direction": direction, "phase": self.phase, "message": message},
                ensure_ascii=False,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("utf-8")
        if len(data) > MAX_EVENT_FRAME:
            raise ProtocolError("oversized retained ACP event")
        self.budget.write(self.events, data)

    async def send(self, message):
        _validate_message(message)
        line = (
            json.dumps(
                message, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode()
            + b"\n"
        )
        if len(line) - 1 > MAX_FRAME:
            raise ProtocolError("oversized NDJSON record")
        self.budget.admit_frame()
        method = message.get("method")
        old_phase, old_replay_id = self.phase, self.replay_id
        if "id" in message and method:
            if len(self.pending) >= 32:
                raise ProtocolError("request admission exceeded")
            self.pending[message["id"]] = method
        if method == "session/load":
            self.phase, self.replay_id = "replay", message["id"]
        if method == "session/prompt":
            self.phase = "prompt"
        try:
            self.budget.write(self.raw_out, line)
            self.record("send", message)
            self.writer.write(line)
            await self.writer.drain()
        except BaseException:
            self.summary["protocol_complete"] = False
            if method and "id" in message:
                self.pending.pop(message["id"], None)
            self.phase, self.replay_id = old_phase, old_replay_id
            raise
        if method == "session/prompt":
            self.summary["prompt_submitted"] = True

    async def receive(self):
        try:
            try:
                line = await self.reader.readuntil(b"\n")
            except asyncio.IncompleteReadError as exc:
                line = exc.partial
            except asyncio.LimitOverrunError as exc:
                prefix = await self.reader.readexactly(min(exc.consumed, MAX_FRAME + 1))
                self.budget.write(self.raw_in, prefix)
                raise ProtocolError("oversized NDJSON record") from exc
            if not line:
                if self.pending:
                    self.summary["protocol_complete"] = False
                return None
            self.budget.admit_frame()
            self.budget.write(self.raw_in, line)
            message = decode(line)
            method = message.get("method")
            if method:
                if method in self.validators:
                    validate_payload(self.validators[method], message.get("params", {}))
                elif "id" in message and not method.startswith("_"):
                    raise ProtocolError("unadvertised client service requested")
            else:
                method = self.pending.pop(message["id"], None)
                if method is None:
                    raise ProtocolError("unknown response identity")
                if "result" in message:
                    validate_payload(self.validators[method], message["result"])
                elif (
                    not isinstance(message["error"], dict)
                    or type(message["error"].get("code")) is not int
                    or not isinstance(message["error"].get("message"), str)
                ):
                    raise ProtocolError("invalid error response")
            self.record("receive", message)
            if message.get("id") == self.replay_id and "method" not in message:
                self.phase, self.replay_id = "setup", None
            return message
        except Exception:
            self.summary["protocol_complete"] = False
            raise

    async def close(self):
        if not self.writer.is_closing():
            self.writer.close()

    def finish(self):
        errors = []
        for stream in (self.raw_in, self.raw_out, self.events):
            try:
                stream.close()
            except OSError as exc:
                errors.append(exc)
        if errors:
            raise errors[0]
