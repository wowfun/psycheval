from __future__ import annotations

import http.client
import json
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from psycheval.config import (
    AcpAgent,
    ToolConfig,
    apply_toml_config,
    write_workspace_acp_agents,
)
from psycheval.serve.access import ServeAccess
from psycheval.serve.acp import AcpError, AcpManager
from psycheval.serve.prompt_assets import PromptAssetConflict, PromptAssetLibrary
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import open_workspace_state
from tests.peval.asgi_server import LocalHTTPServer, make_handler

FAKE_AGENT = r"""
import json
import pathlib
import sys

counter = pathlib.Path(sys.argv[1])
counter.write_text(str(int(counter.read_text() or "0") + 1))
session_number = 0

def send(value):
    print(json.dumps(value, separators=(",", ":")), flush=True)

for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    request_id = message.get("id")
    params = message.get("params") or {}
    if method == "initialize":
        send({"jsonrpc":"2.0","id":request_id,"result":{
            "protocolVersion": 1,
            "agentCapabilities": {"loadSession": True, "promptCapabilities": {"embeddedContext": True}},
            "agentInfo": {"name":"Synthetic ACP","version":"1.0"},
            "authMethods": []
        }})
    elif method == "session/list":
        send({"jsonrpc":"2.0","id":request_id,"result":{"sessions":[]}})
    elif method == "session/new":
        session_number += 1
        send({"jsonrpc":"2.0","id":request_id,"result":{
            "sessionId":f"session/{session_number}",
            "modes":{"currentModeId":"ask","availableModes":[{"id":"ask","name":"Ask"}]}
        }})
    elif method == "session/resume":
        send({"jsonrpc":"2.0","id":request_id,"error":{"code":-32601,"message":"use load"}})
    elif method == "session/load":
        send({"jsonrpc":"2.0","id":request_id,"result":{"sessionId":params["sessionId"]}})
    elif method == "session/prompt":
        session_id = params["sessionId"]
        send({"jsonrpc":"2.0","id":900,"method":"session/request_permission","params":{
            "sessionId":session_id,
            "toolCall":{"toolCallId":"tool-1","title":"Read evaluation file"},
            "options":[{"optionId":"allow_once","name":"Allow once"}]
        }})
        permission = json.loads(sys.stdin.readline())
        while permission.get("method") == "session/cancel":
            permission = json.loads(sys.stdin.readline())
        assert permission["id"] == 900
        send({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":session_id,"update":{
            "sessionUpdate":"plan","entries":[{"content":"Inspect evidence","status":"completed"}]
        }}})
        send({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":session_id,"update":{
            "sessionUpdate":"agent_message_chunk","content":{"type":"text","text":"Evidence reviewed."}
        }}})
        send({"jsonrpc":"2.0","id":request_id,"result":{"stopReason":"end_turn"}})
    elif method == "session/close":
        send({"jsonrpc":"2.0","id":request_id,"result":{}})
    elif method in {"session/set_mode", "session/set_config_option"}:
        send({"jsonrpc":"2.0","id":request_id,"result":{}})
"""

NEGOTIATING_AGENT = r"""
import json
import pathlib
import sys

mode = sys.argv[1]
counter = pathlib.Path(sys.argv[2])
counter.write_text(str(int(counter.read_text() or "0") + 1))
for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") != "initialize":
        continue
    request_id = message["id"]
    version = message["params"]["protocolVersion"]
    if mode == "reject-v2" and version == 2:
        print(json.dumps({"jsonrpc":"2.0","id":request_id,"error":{"code":-32602,"message":"v1 shape required"}}), flush=True)
    else:
        print(json.dumps({"jsonrpc":"2.0","id":request_id,"result":{"protocolVersion":version,"agentCapabilities":{},"agentInfo":{"name":"Negotiating"}}}), flush=True)
"""


class AcpConfigTests(unittest.TestCase):
    def test_parses_whitelisted_agent_without_shell_command_text(self) -> None:
        config = apply_toml_config(
            ToolConfig(),
            {
                "acp": {
                    "agents": [
                        {
                            "id": "opencode",
                            "title": "OpenCode",
                            "command": "opencode",
                            "args": ["acp"],
                        }
                    ]
                }
            },
        )
        self.assertEqual(config.acp_agents[0].id, "opencode")
        self.assertEqual(config.acp_agents[0].args, ("acp",))

    def test_rejects_duplicate_or_path_like_agent_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "lowercase"):
            apply_toml_config(
                ToolConfig(),
                {"acp": {"agents": [{"id": "../agent", "title": "A", "command": "a"}]}},
            )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            apply_toml_config(
                ToolConfig(),
                {
                    "acp": {
                        "agents": [
                            {"id": "agent", "title": "A", "command": "a"},
                            {"id": "agent", "title": "B", "command": "b"},
                        ]
                    }
                },
            )

    def test_writes_only_acp_agent_tables_and_preserves_sibling_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config_path = Path(temporary) / "peval.toml"
            config_path.write_text(
                'locale = "zh-CN"\n\n[[acp.agents]]\nid = "old"\n'
                'title = "Old"\ncommand = "old"\n\n[harbor.host]\nport = 9000\n',
                encoding="utf-8",
            )
            saved = write_workspace_acp_agents(
                config_path,
                (
                    AcpAgent(
                        id="opencode",
                        title="OpenCode 本地",
                        command="opencode",
                        args=("acp",),
                    ),
                ),
            )
            rendered = config_path.read_text(encoding="utf-8")
            self.assertEqual(saved[0].title, "OpenCode 本地")
            self.assertIn("[harbor.host]\nport = 9000", rendered)
            self.assertNotIn('id = "old"', rendered)
            self.assertIn('args = ["acp"]', rendered)


class PromptAssetTests(unittest.TestCase):
    def test_workspace_same_name_override_and_restore_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            library = PromptAssetLibrary(temporary)
            default = library.read("failure-diagnosis")
            self.assertFalse(default.customized)
            self.assertIn("# Failure diagnosis", default.content)

            customized = library.save(
                default.id,
                "# Team diagnosis\n\nInspect the first failed tool call.\n",
                expected_revision=default.revision,
            )
            override = Path(temporary) / "prompts" / "failure-diagnosis.md"
            self.assertTrue(customized.customized)
            self.assertEqual(customized.title, "Team diagnosis")
            self.assertTrue(override.is_file())

            with self.assertRaises(PromptAssetConflict):
                library.save(
                    default.id,
                    "# Stale edit\n",
                    expected_revision=default.revision,
                )

            restored = library.reset(
                customized.id,
                expected_revision=customized.revision,
            )
            self.assertFalse(restored.customized)
            self.assertEqual(restored.content, default.content)
            self.assertFalse(override.exists())

    def test_broken_prompts_symlink_is_rejected_as_a_workspace_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "prompts").symlink_to(
                root / "missing-prompts", target_is_directory=True
            )
            library = PromptAssetLibrary(root)
            default = library.read("failure-diagnosis")

            with self.assertRaisesRegex(
                ValueError, "workspace prompts path must be a directory"
            ):
                library.save(
                    default.id,
                    "# Team diagnosis\n",
                    expected_revision=default.revision,
                )

    def test_concurrent_prompt_saves_allow_only_one_matching_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "prompts").mkdir()
            library = PromptAssetLibrary(root)
            default = library.read("failure-diagnosis")
            barrier = threading.Barrier(12)

            def save(index: int) -> str:
                barrier.wait()
                try:
                    library.save(
                        default.id,
                        f"# Concurrent edit {index}\n",
                        expected_revision=default.revision,
                    )
                except PromptAssetConflict:
                    return "conflict"
                return "saved"

            with ThreadPoolExecutor(max_workers=12) as executor:
                outcomes = list(executor.map(save, range(12)))

            self.assertEqual(outcomes.count("saved"), 1)
            self.assertEqual(outcomes.count("conflict"), 11)

    def test_prompt_overrides_reject_oversize_symlink_and_non_utf8_content(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            library = PromptAssetLibrary(root)
            default = library.read("failure-diagnosis")
            with self.assertRaisesRegex(ValueError, "256 KiB"):
                library.save(
                    default.id,
                    "# Too large\n" + ("x" * (256 * 1024)),
                    expected_revision=default.revision,
                )

            prompts = root / "prompts"
            prompts.mkdir()
            target = root / "outside.md"
            target.write_text("# Outside\n", encoding="utf-8")
            override = prompts / default.filename
            override.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "regular file"):
                library.read(default.id)

            override.unlink()
            override.write_bytes(b"\xff\xfe")
            with self.assertRaisesRegex(ValueError, "UTF-8"):
                library.read(default.id)


class AcpManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        script = root / "fake_agent.py"
        script.write_text(FAKE_AGENT, encoding="utf-8")
        self.counter = root / "starts.txt"
        self.counter.write_text("0", encoding="utf-8")
        config = AcpAgent(
            id="synthetic",
            title="Synthetic",
            command=sys.executable,
            args=(str(script), str(self.counter)),
        )
        self.manager = AcpManager((config,), root)

    def tearDown(self) -> None:
        self.manager.close()
        self.temp.cleanup()

    def test_v2_probe_restarts_and_negotiates_v1(self) -> None:
        payload = self.manager.connect("synthetic")
        self.assertEqual(payload["protocol_version"], 1)
        self.assertEqual(self.counter.read_text(encoding="utf-8"), "2")
        self.assertEqual(payload["agent_info"]["name"], "Synthetic ACP")

    def test_v1_fallback_exit_during_initialize_is_not_reported_connected(
        self,
    ) -> None:
        root = Path(self.temp.name)
        script = root / "exiting_v1_agent.py"
        script.write_text(
            """
import json
import sys

for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") != "initialize":
        continue
    version = message["params"]["protocolVersion"]
    print(json.dumps({"jsonrpc":"2.0","id":message["id"],"result":{"protocolVersion":1}}), flush=True)
    if version == 1:
        raise SystemExit(0)
""",
            encoding="utf-8",
        )
        manager = AcpManager(
            (
                AcpAgent(
                    id="exiting-v1",
                    title="Exiting v1",
                    command=sys.executable,
                    args=(str(script),),
                ),
            ),
            root,
        )
        try:
            with self.assertRaisesRegex(AcpError, "exited during initialization"):
                manager.connect("exiting-v1")
        finally:
            manager.close()

    def test_v2_success_and_initialize_error_fallback_paths(self) -> None:
        root = Path(self.temp.name)
        script = root / "negotiating_agent.py"
        script.write_text(NEGOTIATING_AGENT, encoding="utf-8")
        for mode, expected_version, expected_starts in (
            ("v2", 2, 1),
            ("reject-v2", 1, 2),
        ):
            with self.subTest(mode=mode):
                counter = root / f"{mode}.txt"
                counter.write_text("0", encoding="utf-8")
                manager = AcpManager(
                    (
                        AcpAgent(
                            id="negotiating",
                            title="Negotiating",
                            command=sys.executable,
                            args=(str(script), mode, str(counter)),
                        ),
                    ),
                    root,
                )
                try:
                    payload = manager.connect("negotiating")
                    self.assertEqual(payload["protocol_version"], expected_version)
                    self.assertEqual(
                        int(counter.read_text(encoding="utf-8")), expected_starts
                    )
                finally:
                    manager.close()

    def test_failed_v1_fallback_stops_the_retry_process(self) -> None:
        root = Path(self.temp.name)
        script = root / "rejecting_agent.py"
        heartbeat = root / "rejecting-heartbeat.txt"
        script.write_text(
            """
import json
import pathlib
import sys
import threading
import time

heartbeat = pathlib.Path(sys.argv[1])

def beat():
    while True:
        heartbeat.write_text(str(time.monotonic_ns()))
        time.sleep(0.01)

threading.Thread(target=beat, daemon=True).start()
for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":message["id"],"error":{"code":-32602,"message":"unsupported"}}), flush=True)
""",
            encoding="utf-8",
        )
        manager = AcpManager(
            (
                AcpAgent(
                    id="rejecting",
                    title="Rejecting",
                    command=sys.executable,
                    args=(str(script), str(heartbeat)),
                ),
            ),
            root,
        )
        try:
            with self.assertRaisesRegex(AcpError, "unsupported"):
                manager.connect("rejecting")
            time.sleep(0.1)
            before = heartbeat.stat().st_mtime_ns
            time.sleep(0.1)
            self.assertEqual(heartbeat.stat().st_mtime_ns, before)
        finally:
            manager.close()

    def test_session_prompt_permission_events_and_single_prompt_gate(self) -> None:
        self.manager.connect("synthetic")
        session = self.manager.open_session("synthetic")
        session_id = session["session_id"]
        self.assertEqual(
            len(self.manager.sessions("synthetic", refresh=True)["sessions"]), 1
        )
        mode = self.manager.set_mode("synthetic", session_id, "ask")
        self.assertEqual(mode["session"]["current_mode"], "ask")
        configured = self.manager.set_config(
            "synthetic", session_id, "verbosity", "high"
        )
        self.assertEqual(configured["result"], {})
        self.manager.prompt(
            "synthetic",
            session_id,
            [{"type": "text", "text": "Review this evaluation"}],
        )
        with self.assertRaisesRegex(AcpError, "active prompt") as raised:
            self.manager.prompt(
                "synthetic",
                session_id,
                [{"type": "text", "text": "Overlapping prompt"}],
            )
        self.assertEqual(raised.exception.status, 409)

        permission = self._wait_for_event(session_id, "permission")
        cancelling = self.manager.cancel("synthetic", session_id)
        self.assertTrue(cancelling["active_prompt"])
        self._wait_for_event(session_id, "status")
        self.manager.permission(
            "synthetic",
            session_id,
            permission["request_id"],
            "allow_once",
            cancelled=False,
        )
        complete = self._wait_for_event(session_id, "prompt_complete")
        self.assertEqual(complete["stop_reason"], "end_turn")
        snapshot = self.manager.events("synthetic", session_id, after=0, wait=0)
        self.assertIn("plan", {event["type"] for event in snapshot["events"]})
        self.assertIn("message", {event["type"] for event in snapshot["events"]})
        self.assertFalse(snapshot["session"]["active_prompt"])

    def test_multiple_sessions_are_independent_and_closeable(self) -> None:
        self.manager.connect("synthetic")
        first = self.manager.open_session("synthetic")
        second = self.manager.open_session("synthetic")
        self.assertNotEqual(first["session_id"], second["session_id"])
        closed = self.manager.close_session("synthetic", second["session_id"])
        self.assertTrue(closed["closed"])
        self.assertEqual(len(self.manager.sessions("synthetic")["sessions"]), 2)

    def test_disconnect_marks_sessions_for_explicit_resume(self) -> None:
        self.manager.connect("synthetic")
        session = self.manager.open_session("synthetic")
        self.manager.disconnect("synthetic")
        listed = self.manager.sessions("synthetic")["sessions"]
        self.assertFalse(listed[0]["loaded"])
        self.manager.connect("synthetic")
        resumed = self.manager.open_session(
            "synthetic", resume_session_id=session["session_id"]
        )
        self.assertTrue(resumed["loaded"])

    def test_reconfigure_preserves_unchanged_connection_and_stops_changed_one(
        self,
    ) -> None:
        self.manager.connect("synthetic")
        original = AcpAgent(
            id="synthetic",
            title="Synthetic",
            command=sys.executable,
            args=(
                str(Path(self.temp.name) / "fake_agent.py"),
                str(self.counter),
            ),
        )
        self.manager.reconfigure((original,))
        self.assertTrue(self.manager.agents()["agents"][0]["connected"])

        changed = AcpAgent(
            id="synthetic",
            title="Changed",
            command=original.command,
            args=original.args,
        )
        self.manager.reconfigure((changed,))
        payload = self.manager.agents()["agents"][0]
        self.assertEqual(payload["title"], "Changed")
        self.assertFalse(payload["connected"])

    def test_reconfigure_does_not_wait_for_a_stubborn_agent_to_exit(self) -> None:
        root = Path(self.temp.name)
        script = root / "stubborn_agent.py"
        heartbeat = root / "stubborn-heartbeat.txt"
        script.write_text(
            """
import json
import pathlib
import signal
import sys
import threading
import time

heartbeat = pathlib.Path(sys.argv[1])
signal.signal(signal.SIGTERM, lambda *_args: None)

def beat():
    while True:
        heartbeat.write_text(str(time.monotonic_ns()))
        time.sleep(0.01)

threading.Thread(target=beat, daemon=True).start()
for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":message["id"],"result":{"protocolVersion":2}}), flush=True)
""",
            encoding="utf-8",
        )
        original = AcpAgent(
            id="stubborn",
            title="Stubborn",
            command=sys.executable,
            args=(str(script), str(heartbeat)),
        )
        manager = AcpManager((original,), root)
        try:
            manager.connect("stubborn")
            started = time.monotonic()
            manager.reconfigure(
                (
                    AcpAgent(
                        id=original.id,
                        title="Changed",
                        command=original.command,
                        args=original.args,
                    ),
                )
            )
            self.assertLess(time.monotonic() - started, 0.5)

            deadline = time.monotonic() + 3
            stable_since: float | None = None
            previous = heartbeat.stat().st_mtime_ns
            while time.monotonic() < deadline:
                time.sleep(0.05)
                current = heartbeat.stat().st_mtime_ns
                if current != previous:
                    previous = current
                    stable_since = None
                elif stable_since is None:
                    stable_since = time.monotonic()
                elif time.monotonic() - stable_since >= 0.15:
                    break
            self.assertIsNotNone(stable_since)
        finally:
            manager.close()

    def test_process_exit_fails_initialize_without_waiting_for_timeout(self) -> None:
        root = Path(self.temp.name)
        exiting = root / "exiting_agent.py"
        exiting.write_text("raise SystemExit(7)\n", encoding="utf-8")
        manager = AcpManager(
            (
                AcpAgent(
                    id="exiting",
                    title="Exiting",
                    command=sys.executable,
                    args=(str(exiting),),
                ),
            ),
            root,
        )
        started = time.monotonic()
        try:
            with self.assertRaisesRegex(AcpError, "exited"):
                manager.connect("exiting")
            self.assertLess(time.monotonic() - started, 2)
        finally:
            manager.close()

    def test_malformed_inbound_frame_does_not_disconnect_the_agent(self) -> None:
        root = Path(self.temp.name)
        malformed = root / "malformed_event_agent.py"
        malformed.write_text(
            """
import json
import sys

mode = sys.argv[1]
for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":message["id"],"result":{"protocolVersion":2}}), flush=True)
        if mode == "missing-session":
            invalid = {"jsonrpc":"2.0","method":"session/update","params":{"update":{"sessionUpdate":"agent_message_chunk"}}}
        elif mode == "unhashable-response-id":
            invalid = {"jsonrpc":"2.0","id":[],"result":{}}
        else:
            invalid = {"jsonrpc":"2.0","id":{},"method":"session/request_permission","params":{"sessionId":"ignored","options":[]}}
        print(json.dumps(invalid), flush=True)
        print(json.dumps({"jsonrpc":"2.0","method":"session/update","params":{"sessionId":"survives","update":{"sessionUpdate":"agent_message_chunk","content":{"type":"text","text":"still connected"}}}}), flush=True)
""",
            encoding="utf-8",
        )
        for mode in (
            "missing-session",
            "unhashable-response-id",
            "unhashable-permission-id",
        ):
            with self.subTest(mode=mode):
                manager = AcpManager(
                    (
                        AcpAgent(
                            id="malformed",
                            title="Malformed",
                            command=sys.executable,
                            args=(str(malformed), mode),
                        ),
                    ),
                    root,
                )
                try:
                    manager.connect("malformed")
                    deadline = time.monotonic() + 1
                    sessions: list[dict[str, object]] = []
                    while time.monotonic() < deadline:
                        sessions = manager.sessions("malformed")["sessions"]
                        if sessions:
                            break
                        time.sleep(0.01)
                    self.assertTrue(manager.agents()["agents"][0]["connected"])
                    self.assertEqual(sessions[0]["session_id"], "survives")
                    events = manager.events("malformed", "survives", after=0, wait=0)[
                        "events"
                    ]
                    self.assertEqual(events[0]["text"], "still connected")
                finally:
                    manager.close()

    def test_event_stream_resets_after_truncation_and_wakes_blocking_readers(
        self,
    ) -> None:
        for index in range(1300):
            self.manager.publish(
                "synthetic", "stream", {"type": "status", "status": str(index)}
            )
        truncated = self.manager.events("synthetic", "stream", after=0, wait=0)
        self.assertTrue(truncated["reset"])
        self.assertGreater(truncated["events"][0]["revision"], 1)
        revision = int(truncated["revision"])

        with ThreadPoolExecutor(max_workers=1) as executor:
            started = time.monotonic()
            waiting = executor.submit(
                self.manager.events,
                "synthetic",
                "stream",
                after=revision,
                wait=2,
            )
            time.sleep(0.05)
            self.manager.publish(
                "synthetic", "stream", {"type": "status", "status": "awake"}
            )
            awakened = waiting.result(timeout=1)
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(awakened["events"][0]["status"], "awake")

    def test_manager_bounds_inactive_session_projections(self) -> None:
        for index in range(1300):
            self.manager.publish(
                "synthetic",
                f"session-{index}",
                {"type": "status", "status": "created"},
            )
        sessions = self.manager.sessions("synthetic")["sessions"]
        self.assertLess(len(sessions), 1300)
        self.assertIn("session-1299", {item["session_id"] for item in sessions})

    def test_agent_stderr_lines_are_bounded(self) -> None:
        root = Path(self.temp.name)
        script = root / "large_stderr_agent.py"
        script.write_text(
            """
import json
import sys

sys.stderr.write(("x" * 100_000) + "\\n")
sys.stderr.flush()
for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") == "initialize":
        print(json.dumps({"jsonrpc":"2.0","id":message["id"],"result":{"protocolVersion":2}}), flush=True)
""",
            encoding="utf-8",
        )
        manager = AcpManager(
            (
                AcpAgent(
                    id="noisy",
                    title="Noisy",
                    command=sys.executable,
                    args=(str(script),),
                ),
            ),
            root,
        )
        try:
            manager.connect("noisy")
            deadline = time.monotonic() + 2
            stderr_tail: list[str] = []
            while time.monotonic() < deadline:
                stderr_tail = manager.agents()["agents"][0]["stderr_tail"]
                if stderr_tail:
                    break
                time.sleep(0.01)
            self.assertTrue(any("exceeded" in line for line in stderr_tail))
            self.assertTrue(all(len(line) < 1000 for line in stderr_tail))
        finally:
            manager.close()

    def _wait_for_event(self, session_id: str, event_type: str) -> dict[str, object]:
        revision = 0
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            payload = self.manager.events(
                "synthetic", session_id, after=revision, wait=0.2
            )
            for event in payload["events"]:
                if event["type"] == event_type:
                    return event
            revision = payload["revision"]
        self.fail(f"missing ACP event: {event_type}")


class AcpHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "peval.toml").write_text(
            'analysis_eval_slug = "default"\n', encoding="utf-8"
        )
        script = self.root / "fake_agent.py"
        script.write_text(FAKE_AGENT, encoding="utf-8")
        self.counter = self.root / "starts.txt"
        self.counter.write_text("0", encoding="utf-8")
        self.store = open_workspace_state(str(self.root))
        self.runtime = ServeRuntime(
            self.store,
            ToolConfig(
                workspace_root=str(self.root),
                analysis_eval_slug="default",
                acp_agents=(
                    AcpAgent(
                        id="synthetic",
                        title="Synthetic",
                        command=sys.executable,
                        args=(str(script), str(self.counter)),
                    ),
                ),
            ),
        )
        self.server = LocalHTTPServer(
            ("127.0.0.1", 0),
            make_handler(
                self.runtime,
                access=ServeAccess("correct horse battery staple"),
            ),
        )
        self.server_thread = threading.Thread(
            target=self.server.serve_forever, daemon=True
        )
        self.server_thread.start()

    def tearDown(self) -> None:
        self.runtime.close()
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=5)
        self.store.close()
        self.temp.cleanup()

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        *,
        cookie: str | None = None,
        request_headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], dict[str, object]]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers: dict[str, str] = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Origin"] = f"http://127.0.0.1:{self.server.server_port}"
        if cookie:
            headers["Cookie"] = cookie
        headers.update(request_headers or {})
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        response_body = response.read()
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        connection.close()
        return response.status, response_headers, json.loads(response_body)

    def login(self) -> str:
        status, headers, _payload = self.request(
            "POST",
            "/api/session",
            {"password": "correct horse battery staple"},
        )
        self.assertEqual(status, 200)
        return headers["set-cookie"].split(";", 1)[0]

    def test_new_acp_configuration_prompt_and_task_routes_are_admin_only(self) -> None:
        session_token = "c2Vzc2lvbi0x"
        requests = (
            ("GET", "/api/acp/agents", None),
            ("GET", "/api/acp/agents/synthetic/sessions", None),
            (
                "GET",
                f"/api/acp/agents/synthetic/sessions/{session_token}/events?wait=0",
                None,
            ),
            ("PUT", "/api/acp/agents/synthetic/connection", {}),
            ("DELETE", "/api/acp/agents/synthetic/connection", {}),
            ("POST", "/api/acp/agents/synthetic/sessions", {}),
            (
                "POST",
                f"/api/acp/agents/synthetic/sessions/{session_token}/prompts",
                {},
            ),
            (
                "DELETE",
                f"/api/acp/agents/synthetic/sessions/{session_token}/prompts/active",
                {},
            ),
            (
                "DELETE",
                f"/api/acp/agents/synthetic/sessions/{session_token}",
                {},
            ),
            (
                "POST",
                f"/api/acp/agents/synthetic/sessions/{session_token}/permission-responses",
                {},
            ),
            (
                "PUT",
                f"/api/acp/agents/synthetic/sessions/{session_token}/mode",
                {},
            ),
            (
                "PUT",
                f"/api/acp/agents/synthetic/sessions/{session_token}/config-options/verbosity",
                {},
            ),
            ("GET", "/api/prompts", None),
            ("PUT", "/api/prompts/report", {}),
            ("PATCH", "/api/config", {}),
            ("POST", "/api/harbor/task-state-operations", {}),
            ("POST", "/api/harbor/task-deletion-operations", {}),
            ("PUT", "/api/harbor/datasets/tasks/manifest", {}),
        )
        for method, path, body in requests:
            with self.subTest(method=method, path=path):
                status, _headers, payload = self.request(method, path, body)
                self.assertEqual(status, 403)
                self.assertIn("administrator", str(payload["detail"]))

    def test_acp_http_lifecycle_statuses_validation_and_error_mapping(self) -> None:
        cookie = self.login()
        status, _headers, payload = self.request(
            "GET", "/api/acp/agents", cookie=cookie
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["agents"][0]["id"], "synthetic")  # type: ignore[index]

        status, _headers, payload = self.request(
            "PUT", "/api/acp/agents/missing/connection", {}, cookie=cookie
        )
        self.assertEqual(status, 404)
        self.assertIn("unknown ACP agent", str(payload["detail"]))
        status, _headers, _payload = self.request(
            "POST", "/api/acp/agents/missing/sessions", {}, cookie=cookie
        )
        self.assertEqual(status, 404)

        status, _headers, connected = self.request(
            "PUT",
            "/api/acp/agents/synthetic/connection",
            {},
            cookie=cookie,
        )
        self.assertEqual(status, 200)
        self.assertTrue(connected["connected"])
        status, _headers, sessions = self.request(
            "GET",
            "/api/acp/agents/synthetic/sessions?refresh=true",
            cookie=cookie,
        )
        self.assertEqual(status, 200)
        self.assertEqual(sessions["sessions"], [])

        status, headers, session = self.request(
            "POST",
            "/api/acp/agents/synthetic/sessions",
            {},
            cookie=cookie,
        )
        self.assertEqual(status, 201)
        session_id = str(session["session_id"])
        self.assertEqual(session_id, "session/1")
        session_token = "c2Vzc2lvbi8x"
        self.assertEqual(
            headers["location"],
            f"/api/acp/agents/synthetic/sessions/{session_token}",
        )

        for method, path, body in (
            (
                "PUT",
                f"/api/acp/agents/synthetic/sessions/{session_token}/mode",
                {"mode_id": "ask"},
            ),
            (
                "PUT",
                f"/api/acp/agents/synthetic/sessions/{session_token}/config-options/verbosity",
                {"value": "high"},
            ),
        ):
            status, _headers, _payload = self.request(method, path, body, cookie=cookie)
            self.assertEqual(status, 200)

        status, _headers, _payload = self.request(
            "POST",
            f"/api/acp/agents/synthetic/sessions/{session_token}/permission-responses",
            {
                "request_id": True,
                "cancelled": True,
            },
            cookie=cookie,
        )
        self.assertEqual(status, 422)
        status, _headers, _payload = self.request(
            "POST",
            f"/api/acp/agents/synthetic/sessions/{session_token}/prompts",
            {
                "prompt": "Review this evaluation",
            },
            cookie=cookie,
        )
        self.assertEqual(status, 202)

        revision = 0
        permission: dict[str, object] | None = None
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline and permission is None:
            status, _headers, events = self.request(
                "GET",
                f"/api/acp/agents/synthetic/sessions/{session_token}/events?cursor={revision}&wait=0.2",
                cookie=cookie,
            )
            self.assertEqual(status, 200)
            revision = int(events["next_cursor"])
            permission = next(
                (
                    event
                    for event in events["events"]  # type: ignore[union-attr]
                    if event["type"] == "permission"
                ),
                None,
            )
        self.assertIsNotNone(permission)
        status, _headers, _payload = self.request(
            "POST",
            f"/api/acp/agents/synthetic/sessions/{session_token}/permission-responses",
            {
                "request_id": permission["request_id"],  # type: ignore[index]
                "option_id": "allow_once",
                "cancelled": False,
            },
            cookie=cookie,
        )
        self.assertEqual(status, 200)

        deadline = time.monotonic() + 4
        complete = False
        while time.monotonic() < deadline and not complete:
            status, _headers, events = self.request(
                "GET",
                f"/api/acp/agents/synthetic/sessions/{session_token}/events?cursor={revision}&wait=0.2",
                cookie=cookie,
            )
            self.assertEqual(status, 200)
            revision = int(events["next_cursor"])
            complete = any(
                event["type"] == "prompt_complete"
                for event in events["events"]  # type: ignore[union-attr]
            )
        self.assertTrue(complete)

        for method, path in (
            (
                "DELETE",
                f"/api/acp/agents/synthetic/sessions/{session_token}/prompts/active",
            ),
            ("DELETE", f"/api/acp/agents/synthetic/sessions/{session_token}"),
        ):
            status, _headers, _payload = self.request(
                method,
                path,
                {},
                cookie=cookie,
            )
            self.assertEqual(status, 200)
        status, _headers, disconnected = self.request(
            "DELETE",
            "/api/acp/agents/synthetic/connection",
            {},
            cookie=cookie,
        )
        self.assertEqual(status, 200)
        self.assertFalse(disconnected["connected"])

    def test_prompt_http_conflict_size_and_symlink_errors(self) -> None:
        cookie = self.login()
        status, _headers, catalog = self.request("GET", "/api/prompts", cookie=cookie)
        self.assertEqual(status, 200)
        prompt = catalog[0]  # type: ignore[index]
        status, _headers, saved = self.request(
            "PUT",
            f"/api/prompts/{prompt['id']}",
            {"content": "# Workspace prompt\n"},
            cookie=cookie,
            request_headers={"If-Match": f'"{prompt["revision"]}"'},
        )
        self.assertEqual(status, 200)
        customized = saved

        status, _headers, _payload = self.request(
            "PUT",
            f"/api/prompts/{prompt['id']}",
            {"content": "# Stale prompt\n"},
            cookie=cookie,
            request_headers={"If-Match": f'"{prompt["revision"]}"'},
        )
        self.assertEqual(status, 412)
        status, _headers, _payload = self.request(
            "PUT",
            f"/api/prompts/{prompt['id']}",
            {"content": "# Too large\n" + ("x" * (256 * 1024))},
            cookie=cookie,
            request_headers={"If-Match": f'"{customized["revision"]}"'},
        )
        self.assertEqual(status, 400)
        status, _headers, _payload = self.request(
            "DELETE",
            f"/api/prompts/{prompt['id']}/override",
            None,
            cookie=cookie,
            request_headers={"If-Match": f'"{customized["revision"]}"'},
        )
        self.assertEqual(status, 200)

        outside = self.root / "outside.md"
        outside.write_text("# Outside\n", encoding="utf-8")
        (self.root / "prompts" / str(prompt["filename"])).symlink_to(outside)
        status, _headers, payload = self.request("GET", "/api/prompts", cookie=cookie)
        self.assertEqual(status, 400)
        self.assertIn("regular file", str(payload["detail"]))

    def test_prompt_source_context_maps_unknown_source_to_client_error(self) -> None:
        cookie = self.login()
        status, _headers, payload = self.request(
            "POST",
            "/api/acp/agents/synthetic/sessions/bWlzc2luZy1zZXNzaW9u/prompts",
            {
                "prompt": "Review this evaluation",
                "context": {"kind": "source", "source_key": "missing-source"},
            },
            cookie=cookie,
        )
        self.assertEqual(status, 400)
        self.assertIn("unknown source", str(payload["detail"]))


if __name__ == "__main__":
    unittest.main()
