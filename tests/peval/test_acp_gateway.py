from __future__ import annotations

import asyncio
import http.client
import json
import os
import signal
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from websockets.exceptions import ConnectionClosedError, InvalidStatus
from websockets.sync.client import connect

from psycheval.config import AcpAgent, ToolConfig
from psycheval.serve.access import ServeAccess
from psycheval.serve.acp import (
    MAX_ACP_FRAME_BYTES,
    MAX_AGENT_CONNECTIONS,
    MAX_GATEWAY_CONNECTIONS,
    AcpGateway,
    _Bridge,
    _BridgeFailure,
)
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import open_workspace_state
from tests.peval.asgi_server import LocalHTTPServer, make_handler

ECHO_AGENT = r"""
import pathlib
import sys

starts = pathlib.Path(sys.argv[1])
starts.write_text(str(int(starts.read_text() or "0") + 1))
for line in sys.stdin:
    message = line.rstrip("\n")
    if message == "__INVALID_UTF8__":
        sys.stdout.buffer.write(b"\xff\n")
        sys.stdout.buffer.flush()
    elif message == "__OVERSIZED_OUTPUT__":
        sys.stdout.buffer.write(b"x" * (int(sys.argv[2]) + 1) + b"\n")
        sys.stdout.buffer.flush()
    else:
        print(message, flush=True)
"""


def _process_is_running(pid: int) -> bool:
    status = Path(f"/proc/{pid}/stat")
    if status.exists():
        fields = status.read_text(encoding="utf-8").split()
        return len(fields) > 2 and fields[2] != "Z"
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class AcpGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "peval.toml").write_text('locale = "en"\n', encoding="utf-8")
        script = self.root / "echo_agent.py"
        script.write_text(ECHO_AGENT, encoding="utf-8")
        self.starts = self.root / "starts.txt"
        self.starts.write_text("0", encoding="utf-8")
        self.store = open_workspace_state(str(self.root))
        self.runtime = ServeRuntime(
            self.store,
            ToolConfig(
                workspace_root=str(self.root),
                acp_agents=(
                    AcpAgent(
                        id="synthetic",
                        title="Synthetic",
                        command=sys.executable,
                        args=(str(script), str(self.starts), str(MAX_ACP_FRAME_BYTES)),
                    ),
                ),
            ),
        )
        self.server = LocalHTTPServer(
            ("127.0.0.1", 0),
            make_handler(self.runtime, access=ServeAccess("gateway-password")),
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.ws_url = (
            f"ws://127.0.0.1:{self.server.server_port}/api/acp/agents/synthetic/ws"
        )
        self.cookie = self._login()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.runtime.close()
        self.store.close()
        self.temporary.cleanup()

    def _login(self) -> str:
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        connection.request(
            "POST",
            "/api/session",
            body=json.dumps({"password": "gateway-password"}),
            headers={"Content-Type": "application/json", "Origin": self.origin},
        )
        response = connection.getresponse()
        response.read()
        self.assertEqual(response.status, 200)
        cookie = response.getheader("Set-Cookie")
        connection.close()
        assert cookie is not None
        return cookie.split(";", 1)[0]

    def _agents(self) -> dict[str, object]:
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        connection.request("GET", "/api/acp/agents", headers={"Cookie": self.cookie})
        response = connection.getresponse()
        body = response.read()
        connection.close()
        self.assertEqual(response.status, 200, body)
        return json.loads(body)

    def _logout(self) -> None:
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        connection.request(
            "DELETE",
            "/api/session",
            headers={"Cookie": self.cookie, "Origin": self.origin},
        )
        response = connection.getresponse()
        body = response.read()
        connection.close()
        self.assertEqual(response.status, 200, body)

    def test_bridges_one_bounded_text_stream_and_reports_live_ownership(self) -> None:
        self.assertEqual(self._agents()["max_message_bytes"], MAX_ACP_FRAME_BYTES)
        with connect(
            self.ws_url,
            origin=self.origin,
            additional_headers={"Cookie": self.cookie},
            max_size=MAX_ACP_FRAME_BYTES,
        ) as socket:
            payload = '{"jsonrpc":"2.0","id":1,"method":"initialize"}'
            socket.send(payload)
            self.assertEqual(socket.recv(timeout=3), payload)
            media_sized = json.dumps({"payload": "x" * (3 * 1024 * 1024)})
            socket.send(media_sized)
            self.assertEqual(socket.recv(timeout=5), media_sized)
            self.assertEqual(self.starts.read_text(encoding="utf-8"), "1")
            agent = self._agents()["agents"][0]  # type: ignore[index]
            self.assertTrue(agent["connected"])
            self.assertEqual(agent["connections"], 1)

        deadline = time.monotonic() + 3
        while self._agents()["agents"][0]["connected"] and time.monotonic() < deadline:  # type: ignore[index]
            time.sleep(0.02)
        self.assertFalse(self._agents()["agents"][0]["connected"])  # type: ignore[index]

    @unittest.skipUnless(os.name == "nt", "requires Windows batch launchers")
    def test_windows_bare_command_resolves_cmd_launcher_on_path(self) -> None:
        command = f"psycheval-acp-{self.root.name}"
        first_dir = self.root / "first npm bin"
        second_dir = self.root / "second npm bin"
        for directory in (first_dir, second_dir):
            directory.mkdir()
            (directory / f"{command}.cmd").write_text(
                '@echo off\n"%PEVAL_TEST_ACP_PYTHON%" -X utf8 "%~dp0agent.py" %*\n',
                encoding="ascii",
            )
            (directory / "agent.py").write_text(
                "import json, os, sys\n"
                "message = sys.stdin.readline().rstrip('\\n')\n"
                "print(json.dumps({'message': message, 'args': sys.argv[1:], "
                "'cwd': os.getcwd(), 'script': __file__}), flush=True)\n",
                encoding="utf-8",
            )
        args = ("acp", "two words", "", "中文参数")
        python_args = ("-X", "utf8", str(first_dir / "agent.py"), *args)
        cases = (
            (command, args, first_dir, first_dir),
            (command, args, second_dir, second_dir),
            (f"{command}.cmd", args, first_dir, first_dir),
            (str(first_dir / f"{command}.cmd"), args, second_dir, first_dir),
            (sys.executable, python_args, second_dir, first_dir),
            (
                Path(sys.executable).name,
                python_args,
                Path(sys.executable).parent,
                first_dir,
            ),
        )
        for executable, launch_args, search_dir, expected_dir in cases:
            with self.subTest(executable=executable, search_dir=search_dir):
                config = AcpAgent(
                    id="synthetic",
                    title="Synthetic",
                    command=executable,
                    args=launch_args,
                )
                self.runtime.acp.reconfigure((config,))
                with patch.dict(
                    os.environ,
                    {
                        "PATH": str(search_dir),
                        "PATHEXT": ".EXE;.CMD",
                        "PEVAL_TEST_ACP_PYTHON": sys.executable,
                    },
                ):
                    with connect(
                        self.ws_url,
                        origin=self.origin,
                        additional_headers={"Cookie": self.cookie},
                    ) as socket:
                        payload = '{"jsonrpc":"2.0","id":1,"method":"initialize"}'
                        socket.send(payload)
                        result = json.loads(socket.recv(timeout=3))
                        self.assertEqual(result["message"], payload)
                        self.assertEqual(result["args"], list(args))
                        self.assertEqual(Path(result["cwd"]), self.root.resolve())
                        self.assertEqual(
                            Path(result["script"]), expected_dir / "agent.py"
                        )

                deadline = time.monotonic() + 3
                while (
                    self._agents()["agents"][0]["connections"]
                    and time.monotonic() < deadline
                ):  # type: ignore[index]
                    time.sleep(0.02)
                self.assertEqual(self._agents()["agents"][0]["connections"], 0)  # type: ignore[index]
                self.assertEqual(self.runtime.acp.configuration("synthetic"), config)

    def test_missing_command_releases_reservations_and_allows_recovery(self) -> None:
        working = self.runtime.acp.configuration("synthetic")
        missing = f"psycheval-acp-missing-{self.root.name}"
        for command in (missing, str(self.root / f"{missing}.cmd")):
            with self.subTest(command=command):
                self.runtime.acp.reconfigure(
                    (AcpAgent(id="synthetic", title="Missing", command=command),)
                )
                with patch.dict(
                    os.environ, {"PATH": str(self.root), "PATHEXT": ".CMD"}
                ):
                    for _attempt in range(MAX_AGENT_CONNECTIONS + 1):
                        with self.assertRaises(InvalidStatus) as rejected:
                            connect(
                                self.ws_url,
                                origin=self.origin,
                                additional_headers={"Cookie": self.cookie},
                            )
                        self.assertEqual(rejected.exception.response.status_code, 403)
                        agent = self._agents()["agents"][0]  # type: ignore[index]
                        self.assertEqual(agent["connections"], 0)

        self.runtime.acp.reconfigure((working,))
        with connect(
            self.ws_url,
            origin=self.origin,
            additional_headers={"Cookie": self.cookie},
        ) as socket:
            socket.send("recovered")
            self.assertEqual(socket.recv(timeout=3), "recovered")

    def test_rejects_guest_cross_origin_binary_and_unknown_agent_connections(
        self,
    ) -> None:
        with self.assertRaises(InvalidStatus):
            connect(self.ws_url, origin=self.origin)
        with self.assertRaises(InvalidStatus):
            connect(
                self.ws_url,
                origin="http://evil.example",
                additional_headers={"Cookie": self.cookie},
            )
        with self.assertRaises(InvalidStatus):
            connect(
                self.ws_url.replace("synthetic", "missing"),
                origin=self.origin,
                additional_headers={"Cookie": self.cookie},
            )

        with connect(
            self.ws_url,
            origin=self.origin,
            additional_headers={"Cookie": self.cookie},
        ) as socket:
            socket.send(b"binary is not ACP JSON")
            with self.assertRaises(ConnectionClosedError) as closed:
                socket.recv(timeout=3)
            self.assertEqual(closed.exception.rcvd.code, 1003)

    def test_rejects_multiline_oversized_and_invalid_agent_frames(self) -> None:
        cases = (
            ("one\ntwo", 1007),
            ("x" * (MAX_ACP_FRAME_BYTES + 1), 1009),
            ("__INVALID_UTF8__", 1007),
            ("__OVERSIZED_OUTPUT__", 1009),
        )
        for payload, expected_code in cases:
            with self.subTest(expected_code=expected_code, payload=payload[:24]):
                with connect(
                    self.ws_url,
                    origin=self.origin,
                    additional_headers={"Cookie": self.cookie},
                    max_size=MAX_ACP_FRAME_BYTES + 1024,
                ) as socket:
                    socket.send(payload)
                    with self.assertRaises(ConnectionClosedError) as closed:
                        socket.recv(timeout=3)
                    self.assertEqual(closed.exception.rcvd.code, expected_code)

    def test_configuration_change_terminates_the_borrowed_process(self) -> None:
        with connect(
            self.ws_url,
            origin=self.origin,
            additional_headers={"Cookie": self.cookie},
        ) as socket:
            self.runtime.acp.reconfigure(())
            with self.assertRaises(ConnectionClosedError):
                socket.recv(timeout=3)

    def test_logout_revokes_the_open_bridge_and_borrowed_process(self) -> None:
        with connect(
            self.ws_url,
            origin=self.origin,
            additional_headers={"Cookie": self.cookie},
        ) as socket:
            socket.send("before logout")
            self.assertEqual(socket.recv(timeout=3), "before logout")

            self._logout()

            with self.assertRaises(ConnectionClosedError) as closed:
                socket.recv(timeout=3)
            self.assertEqual(closed.exception.rcvd.code, 1008)

        deadline = time.monotonic() + 3
        while (
            self.runtime.acp.agents()["agents"][0]["connected"]
            and time.monotonic() < deadline
        ):  # type: ignore[index]
            time.sleep(0.02)
        self.assertFalse(self.runtime.acp.agents()["agents"][0]["connected"])  # type: ignore[index]

    @unittest.skipUnless(os.name == "posix", "requires POSIX process groups")
    def test_cleanup_kills_descendants_after_the_group_leader_exits(self) -> None:
        child_pid_path = self.root / "child.pid"
        parent = self.root / "process_tree.py"
        parent.write_text(
            "\n".join(
                [
                    "import pathlib, subprocess, sys, time",
                    "child = subprocess.Popen([sys.executable, '-c', "
                    '"import os, pathlib, signal, sys, time; "'
                    '"signal.signal(signal.SIGTERM, signal.SIG_IGN); "'
                    '"pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); "'
                    '"time.sleep(60)", sys.argv[1]])',
                    "time.sleep(60)",
                ]
            ),
            encoding="utf-8",
        )

        async def exercise() -> int:
            gateway = AcpGateway(
                (
                    AcpAgent(
                        id="tree",
                        title="Tree",
                        command=sys.executable,
                        args=(str(parent), str(child_pid_path)),
                    ),
                ),
                self.root,
            )
            process = await gateway._spawn(gateway.configuration("tree"))
            stdout = asyncio.create_task(process.stdout.read())
            stderr = asyncio.create_task(process.stderr.read())
            try:
                deadline = time.monotonic() + 3
                while not child_pid_path.exists() and time.monotonic() < deadline:
                    await asyncio.sleep(0.02)
                self.assertTrue(child_pid_path.exists())
                child_pid = int(child_pid_path.read_text(encoding="utf-8"))
                bridge = _Bridge(
                    agent_id="tree",
                    session_token="test-session",
                    loop=asyncio.get_running_loop(),
                    process=process,
                    websocket=SimpleNamespace(),
                )
                process.stdin.close()
                await process.stdin.wait_closed()
                await bridge.terminate()
                await asyncio.gather(stdout, stderr)
                return child_pid
            finally:
                if process.returncode is None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    await process.wait()
                if not stdout.done():
                    stdout.cancel()
                if not stderr.done():
                    stderr.cancel()
                await asyncio.gather(stdout, stderr, return_exceptions=True)

        child_pid = asyncio.run(exercise())
        deadline = time.monotonic() + 3
        while _process_is_running(child_pid) and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertFalse(_process_is_running(child_pid))


class AcpLimitsTests(unittest.TestCase):
    def test_gateway_reservations_enforce_per_agent_and_global_capacity(
        self,
    ) -> None:
        agents = tuple(
            AcpAgent(id=f"agent-{index}", title=f"Agent {index}", command="agent")
            for index in range(5)
        )
        gateway = AcpGateway(agents, Path.cwd())

        for _index in range(MAX_AGENT_CONNECTIONS):
            gateway._reserve("agent-0")
        with self.assertRaises(_BridgeFailure) as per_agent:
            gateway._reserve("agent-0")
        self.assertEqual(per_agent.exception.code, 1013)
        self.assertEqual(gateway.agents()["agents"][0]["connections"], 4)  # type: ignore[index]

        for _index in range(MAX_AGENT_CONNECTIONS):
            gateway._release_reservation("agent-0")
        for agent in agents[:4]:
            for _index in range(MAX_AGENT_CONNECTIONS):
                gateway._reserve(agent.id)
        self.assertEqual(
            sum(item["connections"] for item in gateway.agents()["agents"]),  # type: ignore[union-attr]
            MAX_GATEWAY_CONNECTIONS,
        )
        with self.assertRaises(_BridgeFailure) as global_limit:
            gateway._reserve("agent-4")
        self.assertEqual(global_limit.exception.code, 1013)
        gateway.close()


if __name__ == "__main__":
    unittest.main()
