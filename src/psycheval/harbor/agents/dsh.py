"""Official DSH ACP profile with explicit configuration and Host-owned state."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from pathlib import Path

import yaml

from ..measurements import publish, unavailable, unavailable_marker
from ..windows import open_read_descriptor
from .acp import HostACPAgent
from .dsh_measurements import capture

DSH_REFERENCE = "fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159"
MAX_PATCH_BYTES = 16 * 1024 * 1024


def _read_patch(source):
    if any(
        path.is_symlink() or path.is_junction() for path in (source, *source.parents)
    ):
        raise ValueError("DSH patch traverses a link")
    before = source.stat(follow_symlinks=False)
    with os.fdopen(open_read_descriptor(source), "rb") as handle:
        opened = os.fstat(handle.fileno())
        if (
            not stat.S_ISREG(opened.st_mode)
            or not os.path.samestat(before, opened)
            or getattr(opened, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise ValueError("DSH patch identity changed")
        if opened.st_size > MAX_PATCH_BYTES:
            raise ValueError("DSH patch exceeds read limit")
        content = handle.read(MAX_PATCH_BYTES + 1)
        if len(content) > MAX_PATCH_BYTES:
            raise ValueError("DSH patch exceeds read limit")
    return content


class HostDSHAgent(HostACPAgent):
    def __init__(self, *args, executable="dsh", patch_paths=(), **kwargs):
        if any(
            key in kwargs
            for key in (
                "argv",
                "config_dir",
                "tool_result_format",
                "authenticate_method_id",
            )
        ):
            raise ValueError("DSH owns launch, configuration and authentication")
        options = dict(kwargs.pop("config_options", {}) or {})
        if "model" in options:
            raise ValueError("Use model_name for DSH model selection")
        model = kwargs.get("model_name")
        if not isinstance(model, str) or not model:
            raise ValueError("DSH model_name requires an exact advertised model ID")
        if not isinstance(executable, str) or not executable or "\0" in executable:
            raise ValueError("DSH executable must be nonempty and NUL-free")
        if not isinstance(patch_paths, (list, tuple)):
            raise ValueError("DSH patch_paths must be an ordered array of paths")
        self._patch_paths = tuple(Path(path).absolute() for path in patch_paths)
        self._dsh_seeded = False
        self._measurement_offsets = {}
        self._measurement_marker = None
        super().__init__(
            *args,
            argv=[executable, "--profile", "acp"],
            config_options={"model": model, **options},
            tool_result_format="dsh",
            **kwargs,
        )

    @staticmethod
    def name():
        return "dsh"

    async def setup(self, environment):
        if self._dsh_seeded:
            await super().setup(environment)
            return
        # Validate every source before spawning the Agent or materializing configuration.
        patches = []
        for source in self._patch_paths:
            content = _read_patch(source)
            try:
                parsed = yaml.compose(content.decode("utf-8"))
            except (yaml.YAMLError, UnicodeError, RecursionError):
                raise ValueError("Invalid DSH YAML patch") from None
            if not isinstance(parsed, yaml.SequenceNode):
                raise ValueError("DSH patch must be a YAML patch list")
            patches.append(content)
        await super().setup(environment)
        cli_version = await self._probe_version(environment)
        home = self._state / "dsh"
        home.mkdir(exist_ok=True)
        self._launch_cwd = home
        self._child_env = {**self.extra_env, **self._child_env, "DSH_HOME": str(home)}
        provenance = []
        patch_argv = []
        for index, content in enumerate(patches):
            target = home / f"patch-{index:03d}.yaml"
            target.write_bytes(content)
            patch_argv.extend(("--patch", str(target)))
            provenance.append(
                {"index": index, "sha256": hashlib.sha256(content).hexdigest()}
            )
        observer = home / "measurements.mjs"
        shutil.copyfile(Path(__file__).with_name("dsh_measurements.mjs"), observer)
        self._measurement_hook = home / "tool-measurements.ndjson"
        self._child_env["PEVAL_DSH_MEASUREMENTS"] = str(self._measurement_hook)
        measurement_patch = home / "measurements.yaml"
        measurement_patch.write_text(
            yaml.safe_dump(
                [
                    {
                        "id": "session-persistence-jsonl",
                        "config": {
                            "root": str(home / "sessions"),
                            "compression": "none",
                        },
                    },
                    {"insert": [{"id": "peval-measurements", "name": str(observer)}]},
                ],
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        self.argv.extend((*patch_argv, "--patch", str(measurement_patch)))
        self._agent_metadata = {
            "dsh_reference": DSH_REFERENCE,
            "dsh_cli_version": cli_version,
            "dsh_patches": provenance,
        }
        self._dsh_seeded = True

    def _publish_call(self, invocation):
        super()._publish_call(invocation)
        self._measurement_marker = None
        try:
            summary = json.loads(
                (self.logs_dir / "acp.summary.json").read_text(encoding="utf-8")
            )
            session = summary.get("session_id")
            if summary.get("invocation_id") != self._invocation_id or not session:
                return
            records, complete, diagnostics = capture(
                self._state / "dsh",
                session,
                self._measurement_offsets,
                self._measurement_hook,
            )
            self._measurement_marker = publish(
                self.logs_dir,
                records,
                producer={
                    "name": "dsh",
                    "version": self._agent_metadata["dsh_cli_version"],
                },
                invocation_id=self._invocation_id,
                session_id=session,
                capabilities={
                    "logical_steps": {
                        "status": "verified" if records else "unavailable",
                        "evidence": "session.v4.jsonl:step/start,assistant/message.stream",
                        "basis_id": "step_start_to_assistant_message_v1",
                        "start_boundary": "step/start",
                        "end_boundary": "assistant/message",
                        "clock": {
                            "id": "dsh:" + session + ":epoch_ms",
                            "type": "epoch_ms",
                            "semantics": "native_event",
                            "precision_ms": 1,
                        },
                    },
                    "tool_results": {
                        "status": "verified"
                        if any(r.get("source") == "dsh.tools/result" for r in records)
                        else "unavailable",
                        "evidence": "tools/result frozen final outcome",
                    },
                },
                complete=complete,
                diagnostics=diagnostics,
            )
        except Exception as error:
            self.logger.warning(
                "DSH measurement unavailable (%s)", type(error).__name__
            )
            self._measurement_marker = unavailable(
                self.logs_dir,
                producer={
                    "name": "dsh",
                    "version": self._agent_metadata.get("dsh_cli_version", "unknown"),
                },
                invocation_id=self._invocation_id,
            )

    def _enrich_trajectory(self, trajectory, summary):
        data = trajectory.to_json_dict()
        data.setdefault("extra", {})["measurements"] = (
            self._measurement_marker or unavailable_marker()
        )
        return type(trajectory).model_validate(data)

    def populate_context_post_run(self, context):
        try:
            super().populate_context_post_run(context)
        finally:
            if not self._measurement_marker:
                self._measurement_marker = unavailable(
                    self.logs_dir,
                    producer={
                        "name": "dsh",
                        "version": self._agent_metadata.get(
                            "dsh_cli_version", "unknown"
                        ),
                    },
                    invocation_id=self._invocation_id,
                )
            context.metadata = {
                **(context.metadata or {}),
                "measurements": self._measurement_marker or unavailable_marker(),
            }

    async def _probe_version(self, environment):
        with environment.scoped_exec_env(self._child_env):
            result = await environment.exec_argv(
                [self.argv[0], "--version"], timeout_sec=30
            )
        value = (result.stdout or "").strip()
        if result.return_code or not value or len(value) > 256:
            raise RuntimeError("DSH version probe failed")
        return value
