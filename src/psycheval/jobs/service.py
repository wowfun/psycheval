"""Persistent run requests; no worker is owned by the web-server lifetime."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path
from threading import Lock

from psycheval.redaction import redact_credentials, sanitize_credentials

from . import harnesses
from .configuration import Defaults, HarnessDocument, JobsDocument
from .protocol import HarnessContext, ResultRecord, RunRequest, validate_configuration
from .storage import (
    ACTIVE,
    JobsConflict,
    digest,
    locked,
    open_regular,
    owned_process,
    read_bytes,
    read_json,
    read_object,
    safe_path,
    validate_state,
    write_json,
    write_text,
)


class JobsService:
    def __init__(self, workspace: Path, *, registry=None):
        self.workspace = workspace.resolve()
        self.root = safe_path(self.workspace, ".peval", "jobs")
        self.registry = registry if registry is not None else harnesses()
        self._prepare_lock = Lock()

    def configuration(self):
        path = self.workspace / "peval.toml"
        raw = read_bytes(path, 2 * 1024 * 1024)
        data = tomllib.loads(raw.decode("utf-8"))
        for key in ("jobs", "harnesses"):
            if not isinstance(data.get(key, {}), dict):
                raise ValueError(f"{key} must be a configuration table")
        defaults = data.get("jobs", {}).get("defaults", {})
        if not isinstance(defaults, dict) or any(
            not isinstance(value, dict) for value in defaults.values()
        ):
            raise ValueError("jobs.defaults must contain harness tables")
        if any(
            not isinstance(value, dict) for value in data.get("harnesses", {}).values()
        ):
            raise ValueError("harnesses must contain harness tables")
        JobsDocument.model_validate(data.get("jobs", {}))
        HarnessDocument.model_validate({"harnesses": data.get("harnesses", {})})
        return data, hashlib.sha256(raw).hexdigest()

    def context(self, harness_id: str):
        data, _ = self.configuration()
        return HarnessContext(
            self.workspace, data.get("harnesses", {}).get(harness_id, {})
        )

    def plugin(self, harness_id):
        if harness_id not in self.registry:
            raise ValueError(f"harness unavailable: {harness_id}")
        return self.registry[harness_id]

    def options(self):
        config, revision = self.configuration()
        descriptions = []
        for key, plugin in self.registry.items():
            try:
                description = plugin.describe(self.context(key))
                if not isinstance(description, dict):
                    raise ValueError("harness description must be an object")
                digest(description)
            except Exception as exc:  # noqa: BLE001 - isolate plugin descriptions.
                description = {"label": key, "available": False, "error": str(exc)}
            descriptions.append(
                {
                    **description,
                    "id": key,
                    "saved_defaults": config.get("jobs", {})
                    .get("defaults", {})
                    .get(key, {}),
                }
            )
        return redact_credentials({"harnesses": descriptions, "revision": revision})

    def catalog(self, harness_id):
        try:
            value = self.plugin(harness_id).catalog(self.context(harness_id))
            digest(value)
            return value
        except Exception as exc:  # noqa: BLE001 - isolate plugin catalog failures.
            raise ValueError(str(exc)) from exc

    def preview(self, payload):
        if not self._prepare_lock.acquire(blocking=False):
            raise JobsConflict("another configuration is being prepared; retry shortly")
        try:
            return self._preview(payload)
        finally:
            self._prepare_lock.release()

    def _preview(self, payload):
        request = RunRequest.model_validate(payload)
        if len(request.tasks) != len(set(request.tasks)):
            raise ValueError("duplicate Task selection")
        if len({variant.id for variant in request.variants}) != len(request.variants):
            raise ValueError("duplicate variant identity")
        fingerprints = [
            digest({"agent": v.agent, "model": v.model, "options": v.options})
            for v in request.variants
        ]
        if len(set(fingerprints)) != len(fingerprints):
            raise ValueError("identical variants: increase the repeat count instead")
        if redact_credentials(payload) != payload:
            raise ValueError("use environment references for credentials")
        prepared = self.plugin(request.harness).prepare(
            request, self.context(request.harness)
        )
        _, revision = self.configuration()
        result = {
            "request": request.model_dump(),
            "prepared": prepared,
            "configuration_revision": revision,
        }
        result["preview_id"] = digest(result)
        return result

    def start(self, payload, preview_id: str, request_id: str):
        if not isinstance(request_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{8,100}", request_id
        ):
            raise ValueError("invalid request identity")
        payload = RunRequest.model_validate(payload).model_dump()
        run_id = hashlib.sha256(request_id.encode()).hexdigest()[:32]
        run_dir = safe_path(self.root, run_id)
        # Repeated accepted submissions need no preparation or source reads.
        if (run_dir / "request.json").exists():
            existing = read_object(run_dir / "request.json")
            if existing.get("request") != payload:
                raise JobsConflict(
                    "request identity already used for another configuration"
                )
            return self.detail(run_id)
        preview = self.preview(payload)
        if preview["preview_id"] != preview_id:
            raise JobsConflict("configuration or Tasks changed; preview again")
        with locked(self.root):
            existing = (
                read_object(run_dir / "request.json") if run_dir.exists() else None
            )
            if existing:
                if existing["request"] != payload:
                    raise JobsConflict(
                        "request identity already used for another configuration"
                    )
                return self.detail(run_id)
            if self.configuration()[1] != preview["configuration_revision"]:
                raise JobsConflict("configuration changed; preview again")
            run_dir.mkdir()
            write_json(run_dir / "request.json", preview)
            state = {
                "id": run_id,
                "harness": payload["harness"],
                "state": "preparing",
                "submitted_at": datetime.now().astimezone().isoformat(),
                "heartbeat": time.time(),
            }
            write_json(run_dir / "state.json", state)
            options = (
                {
                    "creationflags": subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                }
                if os.name == "nt"
                else {"start_new_session": True}
            )
            process = None
            try:
                with (run_dir / "worker.log").open("ab") as log:
                    process = subprocess.Popen(
                        [
                            sys.executable,
                            "-u",
                            "-m",
                            "psycheval.jobs.worker",
                            str(self.workspace),
                            run_id,
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=log,
                        close_fds=True,
                        cwd=self.workspace,
                        **options,
                    )
                # Popen is not retained by ServeRuntime and no shutdown hook kills it.
                from .storage import process_identity

                write_json(run_dir / "launcher.json", process_identity(process.pid))
            except Exception as exc:
                if process is not None and process.poll() is None:
                    # A failed launcher write must not leave an untracked worker.
                    write_json(run_dir / "stop.json", {"requested_at": time.time()})
                    try:
                        process.wait(timeout=40)
                    except subprocess.TimeoutExpired:
                        process.kill()  # Popen retains the native Windows handle.
                        process.wait(timeout=5)
                state.update(state="failed", error=sanitize_credentials(str(exc)))
                write_json(run_dir / "state.json", state)
                raise
        return self.detail(run_id)

    def detail(self, run_id, *, results=True):
        if not isinstance(run_id, str) or not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise ValueError("invalid run identity")
        path = safe_path(self.root, run_id)
        state = read_json(path / "state.json")
        if not state:
            raise ValueError("run not found")
        state = validate_state(state, run_id)
        identity = state.get("worker") or read_json(path / "launcher.json")
        if (
            state["state"] in ACTIVE
            and time.time() - state.get("heartbeat", 0) > 10
            and not owned_process(identity)
        ):
            state.update(
                state="interrupted", error="The worker exited without a final status."
            )
        if (path / "stop.json").exists() and state["state"] in ACTIVE:
            state["state"] = "stopping"
        request = read_object(path / "request.json", {})
        if any(
            not isinstance(request.get(key, {}), dict)
            for key in ("request", "prepared")
        ):
            raise ValueError("invalid Jobs request record")
        state["request"] = request.get("request", {})
        state["prepared"] = request.get("prepared", {})
        state["results"] = []
        if results and state.get("job_name") and state["harness"] in self.registry:
            output = safe_path(self.workspace, "jobs", state["job_name"])
            try:
                raw_results = self.registry[state["harness"]].read_results(output)
                if not isinstance(raw_results, list):
                    raise ValueError("harness results must be a list")
                variants = read_object(path / "variants.json", {})
                seen = set()
                errors = []
                if len(raw_results) > 10_000:
                    errors.append("harness results exceed 10000 Trials")
                for index, raw in enumerate(raw_results[:10_000]):
                    try:
                        result = ResultRecord.model_validate(raw).model_dump(
                            exclude_unset=True
                        )
                        if result["id"] in seen:
                            raise ValueError("duplicate Trial identity")
                        seen.add(result["id"])
                        variant = variants.get(result["id"], {})
                        if not isinstance(variant, dict):
                            raise ValueError("invalid Jobs variant mapping")
                        result.setdefault("variant_id", variant.get("id"))
                        result.setdefault("variant_label", variant.get("label"))
                        result = ResultRecord.model_validate(result).model_dump(
                            exclude_unset=True
                        )
                        state["results"].append(result)
                    except Exception as exc:  # noqa: BLE001 - isolate installed plugin output.
                        if len(errors) < 50:
                            errors.append(
                                f"Trial {index + 1}: {sanitize_credentials(str(exc))}"
                            )
                if errors:
                    state["result_error"] = "\n".join(errors)
            except Exception as exc:  # noqa: BLE001 - installed harness boundary.
                state["result_error"] = sanitize_credentials(str(exc))
        state.pop("worker", None)
        return redact_credentials(state)

    def list(self):
        if not self.root.exists():
            return []
        result = []
        for path in self.root.iterdir():
            if re.fullmatch(r"[a-f0-9]{32}", path.name):
                try:
                    result.append(self.detail(path.name, results=False))
                except (ValueError, OSError) as exc:
                    result.append(
                        {
                            "id": path.name,
                            "state": "invalid",
                            "harness": "",
                            "submitted_at": "",
                            "error": sanitize_credentials(str(exc)),
                        }
                    )
        return sorted(result, key=lambda value: value["submitted_at"], reverse=True)

    def stop(self, run_id):
        detail = self.detail(run_id, results=False)
        if detail["state"] in ACTIVE:
            write_json(
                safe_path(self.root, run_id, "stop.json"), {"requested_at": time.time()}
            )
        return self.detail(run_id)

    def logs(self, run_id):
        self.detail(run_id, results=False)
        path = safe_path(self.root, run_id, "worker.log")
        if not path.exists():
            return ""
        with open_regular(path) as stream:
            size = stream.seek(0, 2)
            stream.seek(max(0, size - 128 * 1024))
            text = stream.read(128 * 1024).decode("utf-8", errors="replace")
        return (
            "[earlier log omitted]\n" if size > 128 * 1024 else ""
        ) + sanitize_credentials(text)

    def save_defaults(self, harness_id, defaults, revision):
        if not isinstance(harness_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,64}", harness_id
        ):
            raise ValueError("invalid harness identity")
        self.plugin(harness_id)
        validate_configuration(defaults)
        if not isinstance(defaults, dict) or set(defaults) - {
            "tasks",
            "variants",
            "settings",
        }:
            raise ValueError("invalid default sections")
        Defaults.model_validate(defaults)
        if redact_credentials(defaults) != defaults:
            raise ValueError("use environment references for credentials")
        with locked(self.root):
            data, current = self.configuration()
            if revision != current:
                raise JobsConflict(
                    "configuration changed; reload before saving defaults"
                )
            all_defaults = copy.deepcopy(data.get("jobs", {}).get("defaults", {}))
            all_defaults[harness_id] = defaults
            path = self.workspace / "peval.toml"
            # Preserve unrelated tables and comments. Inline TOML values retain types.
            lines = (
                read_bytes(path, 2 * 1024 * 1024)
                .decode("utf-8")
                .splitlines(keepends=True)
            )
            retained, skipping = [], False
            for line in lines:
                if re.match(r"^\s*\[", line):
                    try:
                        header = tomllib.loads(line)
                    except tomllib.TOMLDecodeError:
                        header = {}
                    skipping = (
                        isinstance(header.get("jobs"), dict)
                        and "defaults" in header["jobs"]
                    )
                if not skipping:
                    retained.append(line)
            body = "".join(retained).rstrip() + "\n\n"
            for key, value in all_defaults.items():
                body += f"[jobs.defaults.{json.dumps(key)}]\n"
                body += (
                    "".join(f"{json.dumps(k)} = {_toml(v)}\n" for k, v in value.items())
                    + "\n"
                )
            from psycheval.config import ToolConfig, apply_toml_config

            apply_toml_config(ToolConfig(), tomllib.loads(body), base_dir=path.parent)
            write_text(path, body)
        return self.options()


def _toml(value):
    if isinstance(value, dict):
        return (
            "{ "
            + ", ".join(f"{json.dumps(k)} = {_toml(v)}" for k, v in value.items())
            + " }"
        )
    if isinstance(value, list):
        return "[" + ", ".join(_toml(v) for v in value) + "]"
    if value is None:
        raise ValueError("TOML defaults cannot contain null values")
    return json.dumps(value, ensure_ascii=False, allow_nan=False)
