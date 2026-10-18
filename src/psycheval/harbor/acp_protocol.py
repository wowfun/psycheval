"""Strict, bounded wire transport around the optional ACP SDK."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import zlib
from datetime import UTC, datetime
from functools import cache
from pathlib import Path

MAX_FRAME = 16 * 1024 * 1024
MAX_EVENT_FRAME = 2 * MAX_FRAME
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 65536
MAX_CONFIG_OPTIONS = 8
MAX_CONFIG_ID_BYTES = 256
MAX_CONFIG_VALUE_BYTES = 2048
MAX_EVIDENCE_FRAMES = 65536
MAX_EXTENDED_EVIDENCE_FRAMES = 1024 * 1024
DEFAULT_MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
FORCED_CLEANUP_RESERVE_SEC = 5
KILL_REAP_RESERVE_SEC = 2
EVIDENCE_FILES = (
    "acp.stdin.ndjson.gz",
    "acp.stdout.ndjson.gz",
    "acp.events.ndjson.gz",
    "acp.stderr.log.gz",
)


class ProtocolError(ValueError):
    """Categorical wire failure; diagnostics never echo peer payloads."""


def evidence_frame_limit(maximum):
    if type(maximum) is not int or maximum <= 0:
        raise ValueError("ACP evidence byte budget must be a positive integer")
    return min(MAX_EXTENDED_EVIDENCE_FRAMES, max(MAX_EVIDENCE_FRAMES, maximum // 1024))


def config_option_choices(option):
    """Flatten validated ACP select options without altering their identities."""
    for entry in option.get("options", []):
        yield from entry["options"] if "group" in entry else [entry]


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
    validate_json_structure(value)
    return value


def validate_json_structure(value):
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


@cache
def _sdk_validator(name, result_format="acp"):
    from acp import schema
    from jsonschema import Draft202012Validator

    document = getattr(schema, name).model_json_schema(by_alias=True)

    # ACP categories are optional UX hints, not a closed execution enum.
    def categories(node):
        if isinstance(node, dict):
            properties = node.get("properties", {})
            if "category" in properties and "currentValue" in properties:
                properties["category"] = {"type": ["string", "null"]}
            for child in node.values():
                categories(child)
        elif isinstance(node, list):
            for child in node:
                categories(child)

    if result_format == "codebuddy":
        categories(document)
    return Draft202012Validator(document)


@cache
def sdk_validators(result_format="acp"):
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
    return {
        method: _sdk_validator(name, result_format) for method, name in names.items()
    }


def validate_payload(validator, value, result_format="acp"):
    if next(validator.iter_errors(value), None) is not None:
        raise ProtocolError("invalid known ACP payload")
    if isinstance(value, dict):
        update = value.get("update", value)
        if isinstance(update, dict):
            if "name" in update and (
                not isinstance(update["name"], str) or not update["name"]
            ):
                raise ProtocolError("invalid tool name")
            metadata = update.get("_meta", {})
            if result_format == "codebuddy" and isinstance(metadata, dict):
                if "codebuddy.ai/toolName" in metadata and (
                    not isinstance(metadata["codebuddy.ai/toolName"], str)
                    or not metadata["codebuddy.ai/toolName"]
                ):
                    raise ProtocolError("invalid CodeBuddy tool name")
                if (
                    "codebuddy.ai/businessFailed" in metadata
                    and type(metadata["codebuddy.ai/businessFailed"]) is not bool
                ):
                    raise ProtocolError("invalid CodeBuddy business outcome")
            options = update.get("configOptions", [])
            if not isinstance(options, list) or len(options) > 64:
                raise ProtocolError("invalid configuration list")
            ids = set()
            for option in options:
                if not isinstance(option, dict):
                    raise ProtocolError("invalid configuration option")
                if (
                    next(
                        _sdk_validator(
                            "SessionConfigOptionBoolean"
                            if option.get("type") == "boolean"
                            else "SessionConfigOptionSelect",
                            result_format,
                        ).iter_errors(option),
                        None,
                    )
                    is not None
                ):
                    raise ProtocolError("invalid select configuration option")
                if option["id"] in ids or option.get("type") not in {
                    "select",
                    "boolean",
                }:
                    raise ProtocolError("duplicate or unsupported configuration option")
                ids.add(option["id"])
                if option["type"] == "boolean":
                    continue
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


class EvidenceReader:
    """Incremental gzip reader shared by live observers and closed-file validation."""

    def __init__(self, path, maximum, decoded_maximum=None):
        self.maximum = maximum
        self.decoded_maximum = maximum if decoded_maximum is None else decoded_maximum
        if any(type(n) is not int or n <= 0 for n in (maximum, self.decoded_maximum)):
            raise ProtocolError("invalid retained evidence byte budget")
        self.stream = path.open("rb")
        self.decoder = zlib.decompressobj(31)
        self.pending = b""
        self.bytes = self.decoded_bytes = 0
        self.digest, self.decoded_digest = hashlib.sha256(), hashlib.sha256()

    def read(self, maximum=64 * 1024):
        while True:
            chunk = self.pending
            if not chunk:
                chunk = self.stream.read(min(64 * 1024, self.maximum - self.bytes + 1))
                if not chunk:
                    return b""  # Live EOF may precede the gzip trailer.
                self.bytes += len(chunk)
                if self.bytes > self.maximum:
                    raise ProtocolError(
                        "retained ACP evidence exceeds stored byte budget"
                    )
                self.digest.update(chunk)
            if self.decoder.eof:
                raise ProtocolError("trailing compressed ACP evidence")
            try:
                result = self.decoder.decompress(
                    chunk, min(maximum, self.decoded_maximum - self.decoded_bytes + 1)
                )
            except zlib.error as exc:
                raise ProtocolError("invalid compressed ACP evidence") from exc
            self.pending = self.decoder.unconsumed_tail
            if self.decoder.unused_data:
                raise ProtocolError("trailing compressed ACP evidence")
            self.decoded_bytes += len(result)
            if self.decoded_bytes > self.decoded_maximum:
                raise ProtocolError("retained ACP evidence exceeds decoded byte budget")
            self.decoded_digest.update(result)
            if result:
                return result

    def finish(self):
        if not self.decoder.eof or self.pending:
            raise ProtocolError("incomplete compressed ACP evidence")

    def close(self):
        self.stream.close()

    def manifest(self):
        return {
            "encoding": "gzip",
            "bytes": self.bytes,
            "sha256": self.digest.hexdigest(),
            "decoded_bytes": self.decoded_bytes,
            "decoded_sha256": self.decoded_digest.hexdigest(),
        }


def evidence_manifest(
    directory: Path, maximum=DEFAULT_MAX_EVIDENCE_BYTES, decoded_maximum=None
):
    decoded_maximum = maximum if decoded_maximum is None else decoded_maximum
    if any(type(n) is not int or n <= 0 for n in (maximum, decoded_maximum)):
        raise ProtocolError("invalid retained evidence byte budget")
    files, consumed, decoded = {}, 0, 0
    for name in EVIDENCE_FILES:
        path = directory / name
        if not path.exists():
            continue
        if path.is_symlink() or not path.is_file():
            raise ProtocolError("invalid retained evidence file")
        reader = EvidenceReader(path, maximum, decoded_maximum)
        try:
            while reader.read():
                if (
                    consumed + reader.bytes > maximum
                    or decoded + reader.decoded_bytes > decoded_maximum
                ):
                    raise ProtocolError("retained ACP evidence exceeds byte budget")
            reader.finish()
            consumed += reader.bytes
            decoded += reader.decoded_bytes
            if consumed > maximum or decoded > decoded_maximum:
                raise ProtocolError("retained ACP evidence exceeds byte budget")
            files[name] = reader.manifest()
        finally:
            reader.close()
    return files


def verify_evidence(directory: Path, summary: dict):
    expected = summary.get("evidence_files")
    if (
        not isinstance(summary.get("invocation_id"), str)
        or not summary["invocation_id"]
        or not isinstance(expected, dict)
        or set(expected) != set(EVIDENCE_FILES)
        or evidence_manifest(
            directory,
            summary.get("max_evidence_bytes", DEFAULT_MAX_EVIDENCE_BYTES),
            summary.get("max_decoded_evidence_bytes"),
        )
        != expected
    ):
        raise ProtocolError("retained ACP evidence integrity failed")


class EvidenceBudget:
    """Shared stored/decoded admission, including metadata and gzip closing space."""

    def __init__(
        self,
        summary: dict,
        maximum: int = DEFAULT_MAX_EVIDENCE_BYTES,
        decoded_maximum=None,
    ):
        decoded_maximum = maximum if decoded_maximum is None else decoded_maximum
        if any(type(n) is not int or n <= 0 for n in (maximum, decoded_maximum)):
            raise ValueError("ACP evidence byte budgets must be positive integers")
        self.summary, self.maximum, self.decoded_maximum = (
            summary,
            maximum,
            decoded_maximum,
        )
        self.summary["max_evidence_bytes"] = maximum
        self.summary["max_decoded_evidence_bytes"] = decoded_maximum
        self.maximum_frames = evidence_frame_limit(maximum)
        self.summary["max_evidence_frames"] = self.maximum_frames
        self.bytes = self.decoded_bytes = self.frames = self.reserved = 0
        self.writers = []

    def _exhausted(self, kind):
        self.summary.update(protocol_complete=False, evidence_limit_exceeded=True)
        self.summary.setdefault("evidence_limit_kind", kind)
        raise ProtocolError("ACP evidence admission exceeded")

    def admit_frame(self):
        if self.frames >= self.maximum_frames:
            self._exhausted("frames")
        self.frames += 1

    def check(self, stored, decoded):
        if stored > self.maximum - self.bytes - self.reserved:
            self._exhausted("stored_bytes")
        if decoded > self.decoded_maximum - self.decoded_bytes:
            self._exhausted("decoded_bytes")

    def write(self, stream, data: bytes, decoded_size=None):
        decoded_size = len(data) if decoded_size is None else decoded_size
        self.check(len(data), decoded_size)
        stream.write(data)
        stream.flush()
        self.bytes += len(data)
        self.decoded_bytes += decoded_size

    def retain(self, value):
        size = (
            len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode())
            + 1
        )
        self.check(size, size)
        self.bytes += size
        self.decoded_bytes += size

    def close(self):
        errors = []
        for writer in self.writers:
            try:
                writer.close()
            except BaseException as exc:
                errors.append(exc)
        if errors:
            raise errors[0]


class EvidenceWriter:
    """Commit each sync-flushed record only after both budgets admit it."""

    _CLOSING_RESERVE = 20  # Empty gzip; nonempty sync-flushed streams need 10 bytes.

    def __init__(self, path, budget):
        budget.check(self._CLOSING_RESERVE, 0)
        self.stream = path.open("wb")
        self.budget = budget
        self.compressor = zlib.compressobj(1, wbits=31)
        self.closed = False
        self.failed = False
        budget.reserved += self._CLOSING_RESERVE
        budget.writers.append(self)

    def write(self, data):
        if self.closed or self.failed:
            raise OSError("ACP evidence writer is unavailable")
        self.budget.check(0, len(data))
        candidate = self.compressor.copy()
        encoded = candidate.compress(data) + candidate.flush(zlib.Z_SYNC_FLUSH)
        try:
            self.budget.write(self.stream, encoded, len(data))
        except OSError:
            self.failed = True
            raise
        self.compressor = candidate

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.budget.reserved -= self._CLOSING_RESERVE
        try:
            if not self.failed:
                self.budget.write(self.stream, self.compressor.flush(zlib.Z_FINISH), 0)
        finally:
            self.stream.close()


class StrictTransport:
    """SDK message transport retaining wire order before permissive DTO parsing."""

    def __init__(
        self,
        reader,
        writer,
        directory: Path,
        summary: dict,
        budget=None,
        *,
        result_format="acp",
    ):
        self.reader, self.writer, self.summary = reader, writer, summary
        self.budget = budget if budget is not None else EvidenceBudget(summary)
        self.result_format = result_format
        self.validators = sdk_validators(result_format)
        self.pending = {}
        self.phase = "setup"
        self.expected_model = None
        self.replay_id = None
        self.raw_in = EvidenceWriter(directory / "acp.stdout.ndjson.gz", self.budget)
        self.raw_out = EvidenceWriter(directory / "acp.stdin.ndjson.gz", self.budget)
        self.events = EvidenceWriter(directory / "acp.events.ndjson.gz", self.budget)

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
        self.events.write(data)

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
            self.raw_out.write(line)
            self.record("send", message)
            submitted_at = datetime.now(UTC).isoformat()
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
            self.summary["prompt_submitted_at"] = submitted_at

    async def receive(self):
        try:
            try:
                line = await self.reader.readuntil(b"\n")
            except asyncio.IncompleteReadError as exc:
                line = exc.partial
            except asyncio.LimitOverrunError as exc:
                prefix = await self.reader.readexactly(min(exc.consumed, MAX_FRAME + 1))
                self.raw_in.write(prefix)
                raise ProtocolError("oversized NDJSON record") from exc
            if not line:
                if self.pending:
                    self.summary["protocol_complete"] = False
                return None
            self.budget.admit_frame()
            self.raw_in.write(line)
            message = decode(line)
            method = message.get("method")
            if method:
                if method in self.validators:
                    validate_payload(
                        self.validators[method],
                        message.get("params", {}),
                        self.result_format,
                    )
                elif "id" in message and not method.startswith("_"):
                    raise ProtocolError("unadvertised client service requested")
            else:
                method = self.pending.pop(message["id"], None)
                if method is None:
                    raise ProtocolError("unknown response identity")
                if "result" in message:
                    validate_payload(
                        self.validators[method], message["result"], self.result_format
                    )
                elif (
                    not isinstance(message["error"], dict)
                    or type(message["error"].get("code")) is not int
                    or not isinstance(message["error"].get("message"), str)
                ):
                    raise ProtocolError("invalid error response")
            self.record("receive", message)
            if (
                self.expected_model
                and self.phase == "prompt"
                and method == "session/update"
            ):
                update = message.get("params", {}).get("update", {})
                metadata = update.get("_meta") or {}
                requested = metadata.get("codebuddy.ai/requestModelId")
                if requested is not None and requested != self.expected_model:
                    self.summary["model_mismatch"] = True
                    raise ProtocolError("Agent changed the requested model")
                for option in update.get("configOptions", []):
                    if (
                        option["id"] == "model"
                        and option["currentValue"] != self.expected_model
                    ):
                        self.summary["model_mismatch"] = True
                        raise ProtocolError("Agent changed the requested model")
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
