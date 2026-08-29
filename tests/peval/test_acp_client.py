from __future__ import annotations

import http.client
import json
import tempfile
import threading
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
from psycheval.serve.prompt_assets import PromptAssetConflict, PromptAssetLibrary
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import open_workspace_state
from tests.peval.asgi_server import LocalHTTPServer, make_handler


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

            customized = library.save(
                default.id,
                "# Team diagnosis\n\nInspect the first failed tool call.\n",
                expected_revision=default.revision,
            )
            override = Path(temporary) / "prompts" / "failure-diagnosis.md"
            self.assertTrue(customized.customized)
            self.assertTrue(override.is_file())
            with self.assertRaises(PromptAssetConflict):
                library.save(
                    default.id, "# Stale edit\n", expected_revision=default.revision
                )

            restored = library.reset(
                customized.id, expected_revision=customized.revision
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


class AcpHttpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "peval.toml").write_text('locale = "en"\n', encoding="utf-8")
        self.store = open_workspace_state(str(self.root))
        self.runtime = ServeRuntime(
            self.store,
            ToolConfig(
                workspace_root=str(self.root),
                acp_agents=(
                    AcpAgent(
                        id="synthetic",
                        title="Synthetic",
                        command="synthetic-acp",
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

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.runtime.close()
        self.store.close()
        self.temporary.cleanup()

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        *,
        cookie: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], dict[str, object] | list[object]]:
        body = json.dumps(payload).encode() if payload is not None else None
        request_headers = dict(headers or {})
        if body is not None:
            request_headers.update(
                {"Content-Type": "application/json", "Origin": self.origin}
            )
        if cookie:
            request_headers["Cookie"] = cookie
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        response_body = response.read()
        connection.close()
        return response.status, response_headers, json.loads(response_body)

    def login(self) -> str:
        status, headers, _body = self.request(
            "POST", "/api/session", {"password": "gateway-password"}
        )
        self.assertEqual(status, 200)
        return headers["set-cookie"].split(";", 1)[0]

    def test_gateway_catalog_and_context_resolution_are_admin_only(self) -> None:
        requests = (
            ("GET", "/api/acp/agents", None),
            (
                "POST",
                "/api/acp/context-resolutions",
                {
                    "context": {"kind": "source", "source_key": "missing"},
                    "embedded_context": True,
                },
            ),
        )
        for method, path, body in requests:
            with self.subTest(method=method):
                status, _headers, response = self.request(method, path, body)
                self.assertEqual(status, 403)
                self.assertIn("administrator", str(response))

    def test_catalog_exposes_gateway_cwd_and_old_projection_routes_are_gone(
        self,
    ) -> None:
        cookie = self.login()
        status, _headers, response = self.request(
            "GET", "/api/acp/agents", cookie=cookie
        )
        self.assertEqual(status, 200)
        assert isinstance(response, dict)
        self.assertEqual(response["cwd"], str(self.root.resolve()))
        self.assertEqual(response["agents"][0]["id"], "synthetic")  # type: ignore[index]

        retired_projection_routes = (
            ("PUT", "/api/acp/agents/synthetic/connection", {}),
            ("DELETE", "/api/acp/agents/synthetic/connection", None),
            ("GET", "/api/acp/agents/synthetic/sessions", None),
            ("POST", "/api/acp/agents/synthetic/sessions", {}),
            ("PUT", "/api/acp/agents/synthetic/sessions/session-1", {}),
            ("DELETE", "/api/acp/agents/synthetic/sessions/session-1", None),
            ("GET", "/api/acp/agents/synthetic/sessions/session-1/events", None),
            ("POST", "/api/acp/agents/synthetic/sessions/session-1/prompts", {}),
            (
                "DELETE",
                "/api/acp/agents/synthetic/sessions/session-1/prompts/active",
                None,
            ),
            (
                "POST",
                "/api/acp/agents/synthetic/sessions/session-1/permission-responses",
                {},
            ),
            ("PUT", "/api/acp/agents/synthetic/sessions/session-1/mode", {}),
            (
                "PUT",
                "/api/acp/agents/synthetic/sessions/session-1/config-options/model",
                {},
            ),
        )
        for method, path, body in retired_projection_routes:
            with self.subTest(method=method, path=path):
                status, _headers, _response = self.request(
                    method, path, body, cookie=cookie
                )
                self.assertEqual(status, 404)

    def test_context_resolution_validates_at_the_workspace_boundary(self) -> None:
        cookie = self.login()
        status, _headers, response = self.request(
            "POST",
            "/api/acp/context-resolutions",
            {
                "context": {
                    "kind": "source",
                    "source_key": "missing-source",
                    "unexpected": True,
                },
                "embedded_context": True,
            },
            cookie=cookie,
        )
        self.assertEqual(status, 400)
        self.assertIn("unexpected ACP context fields", str(response))

        status, _headers, response = self.request(
            "POST",
            "/api/acp/context-resolutions",
            {
                "context": {"kind": "source", "source_key": "missing-source"},
                "embedded_context": False,
            },
            cookie=cookie,
        )
        self.assertEqual(status, 400)
        self.assertIn("unknown source", str(response))


if __name__ == "__main__":
    unittest.main()
