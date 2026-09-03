from __future__ import annotations

import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.routing import APIRoute

from psycheval.config import ToolConfig, load_config
from psycheval.serve import ServeRuntime
from psycheval.serve.api import ADMIN_ACCESS, _verify_route_access, access
from psycheval.serve.constants import MAX_JSON_BODY_BYTES
from psycheval.state import open_workspace_state
from psycheval.state.harbor_verifier_evidence import HarborVerifierArtifact
from tests.peval.asgi_server import LocalHTTPServer, make_handler


class ServeApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.config_path = self.root / "peval.toml"
        self.config_path.write_text('locale = "en"\n', encoding="utf-8")
        self.store = open_workspace_state(str(self.root))
        self.runtime = ServeRuntime(
            self.store,
            ToolConfig(workspace_root=str(self.root), locale="en"),
        )
        self.app = make_handler(self.runtime)
        self.server = LocalHTTPServer(("127.0.0.1", 0), self.app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

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
        body: bytes | None = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        request_headers = dict(headers or {})
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            request_headers.setdefault(
                "Origin", f"http://127.0.0.1:{self.server.server_port}"
            )
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        content = response.read()
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        connection.close()
        return response.status, response_headers, content

    def config(self) -> tuple[dict[str, object], dict[str, str]]:
        status, headers, body = self.request("GET", "/api/config")
        self.assertEqual(status, 200, body)
        payload = json.loads(body)
        self.assertEqual(
            set(payload),
            {"acp_agents", "adapter_defaults", "datasets", "locale", "mounts"},
        )
        return payload, headers

    def assert_problem_headers(self, headers: dict[str, str]) -> None:
        self.assertEqual(headers["content-type"], "application/problem+json")
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(headers["referrer-policy"], "no-referrer")
        self.assertEqual(headers["x-content-type-options"], "nosniff")

    def test_routes_are_classified_and_schema_endpoints_are_not_exposed(self) -> None:
        routes = [route for route in self.app.routes if isinstance(route, APIRoute)]
        self.assertGreater(len(routes), 50)
        self.assertTrue(
            all(getattr(route.endpoint, "__peval_access__", None) for route in routes)
        )
        for path in ("/docs", "/redoc", "/openapi.json"):
            status, headers, _body = self.request("GET", path)
            self.assertEqual(status, 404)
            self.assertEqual(headers["cache-control"], "no-store")
            self.assertEqual(headers["referrer-policy"], "no-referrer")
            self.assertEqual(headers["x-content-type-options"], "nosniff")

        _config, headers = self.config()
        self.assertRegex(headers["etag"], r'^"[0-9a-f]{64}"$')
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertNotIn("server", headers)

    def test_workbuddy_verifier_artifact_route_sets_safe_response_headers(self) -> None:
        artifact_id = "a" * 24
        artifact = HarborVerifierArtifact(
            filename='report"\r\nX-Evil.md',
            media_type="text/markdown; charset=utf-8",
            content=b"# report\n",
        )
        stream_closed = threading.Event()
        stream = SimpleNamespace(
            filename="report.md",
            media_type="text/markdown; charset=utf-8",
            size=9,
            chunks=iter((b"# report\n",)),
            close=Mock(side_effect=stream_closed.set),
        )
        with (
            patch.object(
                self.runtime.catalog.sources,
                "read_harbor_verifier_artifact",
                return_value=artifact,
            ) as read,
            patch.object(
                self.runtime.catalog,
                "row_for_key",
                return_value={
                    "kind": "harbor-trial",
                    "source_ref": "harbor/jobs/job/trial",
                },
            ) as lookup,
        ):
            status, headers, body = self.request(
                "GET", f"/api/harbor/verifier-artifacts/source-key/{artifact_id}"
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(body, b"# report\n")
            self.assertEqual(headers["content-type"], "text/markdown; charset=utf-8")
            self.assertEqual(
                headers["content-disposition"],
                'inline; filename="report___X-Evil.md"',
            )
            self.assertEqual(headers["cache-control"], "no-store")
            self.assertEqual(headers["referrer-policy"], "no-referrer")
            self.assertEqual(headers["x-content-type-options"], "nosniff")
            self.assertEqual(headers["content-security-policy"], "sandbox")
            lookup.assert_called_once_with("source-key")
            read.assert_called_once_with(
                "harbor/jobs/job/trial", artifact_id, purpose="preview"
            )

        with (
            patch.object(
                self.runtime.catalog.sources,
                "read_harbor_verifier_artifact",
                side_effect=AssertionError("download must not be buffered"),
            ),
            patch.object(
                self.runtime.catalog.sources,
                "open_harbor_verifier_artifact_download",
                create=True,
                return_value=stream,
            ) as open_download,
            patch.object(
                self.runtime.catalog,
                "row_for_key",
                return_value={
                    "kind": "harbor-trial",
                    "source_ref": "harbor/jobs/job/trial",
                },
            ) as lookup,
        ):
            status, headers, body = self.request(
                "GET",
                f"/api/harbor/verifier-artifacts/source-key/{artifact_id}?download=true",
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(
                headers["content-disposition"], 'attachment; filename="report.md"'
            )
            lookup.assert_called_once_with("source-key")
            open_download.assert_called_once_with("harbor/jobs/job/trial", artifact_id)
            self.assertTrue(stream_closed.wait(timeout=5))
            stream.close.assert_called_once_with()

        with patch.object(
            self.runtime.catalog.sources,
            "read_harbor_verifier_artifact",
            return_value=artifact,
        ) as read:
            status, _headers, _body = self.request(
                "GET", "/api/harbor/verifier-artifacts/source-key/not-an-opaque-id"
            )
            self.assertEqual(status, 404)
            read.assert_not_called()

    def test_problem_validation_media_type_and_preconditions(self) -> None:
        _config, config_headers = self.config()
        etag = config_headers["etag"]

        status, headers, body = self.request(
            "PATCH",
            "/api/config",
            json.dumps({"unknown": True}).encode(),
            headers={"Content-Type": "application/json", "If-Match": etag},
        )
        problem = json.loads(body)
        self.assertEqual(status, 422)
        self.assert_problem_headers(headers)
        self.assertEqual(problem["errors"][0]["pointer"], "/unknown")

        status, headers, body = self.request(
            "PATCH",
            "/api/config",
            b'{"locale":',
            headers={"Content-Type": "application/json", "If-Match": etag},
        )
        self.assertEqual(status, 400)
        self.assert_problem_headers(headers)
        self.assertEqual(json.loads(body)["detail"], "request body is not valid JSON")

        status, headers, body = self.request(
            "PATCH",
            "/api/config",
            b'locale = "zh"',
            headers={"Content-Type": "text/plain", "If-Match": etag},
        )
        self.assertEqual(status, 415)
        self.assert_problem_headers(headers)
        self.assertIn("application/json", json.loads(body)["detail"])

        status, headers, _body = self.request(
            "PATCH",
            "/api/config",
            b'{"locale":"zh"}',
            headers={"If-Match": etag},
        )
        self.assertEqual(status, 415)
        self.assert_problem_headers(headers)

        status, headers, _body = self.request(
            "PATCH",
            "/api/config",
            b'{"locale":"zh"}',
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 428)
        self.assert_problem_headers(headers)

        status, response_headers, _body = self.request(
            "PATCH",
            "/api/config",
            b'{"locale":"zh"}',
            headers={"Content-Type": "application/json", "If-Match": '"stale"'},
        )
        self.assertEqual(status, 412)
        self.assert_problem_headers(response_headers)
        self.assertEqual(response_headers["etag"], etag)

    def test_config_patch_is_atomic_and_reloads_pydantic_state(self) -> None:
        source = self.config_path.read_bytes()
        _config, config_headers = self.config()
        etag = config_headers["etag"]

        status, _headers, body = self.request(
            "PATCH",
            "/api/config",
            json.dumps({"locale": "zh", "adapter_defaults": {"opencode": 1}}).encode(),
            headers={"Content-Type": "application/json", "If-Match": etag},
        )
        self.assertEqual(status, 422, body)
        self.assertEqual(self.config_path.read_bytes(), source)

        status, headers, body = self.request(
            "PATCH",
            "/api/config",
            json.dumps(
                {
                    "locale": "zh",
                    "adapter_defaults": {"opencode": "db/opencode.db"},
                }
            ).encode(),
            headers={"Content-Type": "application/json", "If-Match": etag},
        )
        payload = json.loads(body)
        self.assertEqual(status, 200, body)
        self.assertEqual(payload["locale"], "zh-CN")
        self.assertEqual(
            payload["adapter_defaults"]["opencode"],
            str((self.root / "db/opencode.db").resolve()),
        )
        self.assertNotEqual(headers["etag"], etag)
        loaded = load_config(workspace_root=self.root)
        self.assertEqual(loaded.locale, "zh-CN")
        self.assertEqual(
            loaded.adapter_default_db_paths["opencode"],
            str((self.root / "db/opencode.db").resolve()),
        )

    def test_declared_body_over_limit_is_rejected_before_validation(self) -> None:
        _config, config_headers = self.config()
        status, headers, body = self.request(
            "PATCH",
            "/api/config",
            b"{}",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(MAX_JSON_BODY_BYTES + 1),
                "If-Match": config_headers["etag"],
            },
        )
        self.assertEqual(status, 413, body)
        self.assert_problem_headers(headers)
        self.assertIn("exceeds serve limit", json.loads(body)["detail"])

    def test_chunked_body_over_limit_is_rejected_as_content_too_large(self) -> None:
        _config, config_headers = self.config()
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port, timeout=5
        )
        connection.request(
            "PATCH",
            "/api/config",
            body=[b'{"description":"', b"x" * MAX_JSON_BODY_BYTES, b'"}'],
            headers={
                "Content-Type": "application/json",
                "If-Match": config_headers["etag"],
                "Origin": f"http://127.0.0.1:{self.server.server_port}",
            },
            encode_chunked=True,
        )
        response = connection.getresponse()
        body = response.read()
        headers = {key.lower(): value for key, value in response.getheaders()}
        connection.close()

        self.assertEqual(response.status, 413, body)
        self.assert_problem_headers(headers)
        self.assertIn("exceeds serve limit", json.loads(body)["detail"])

    def test_admin_access_classification_requires_enforcement(self) -> None:
        app = FastAPI()

        @app.get("/unsafe")
        @access(ADMIN_ACCESS)
        def unsafe() -> dict[str, bool]:
            return {"unsafe": True}

        with self.assertRaisesRegex(RuntimeError, "administrator dependency"):
            _verify_route_access(app)

    def test_batch_task_operations_require_strong_item_etags(self) -> None:
        status, headers, body = self.request(
            "POST",
            "/api/harbor/task-state-operations",
            json.dumps(
                {
                    "archived": True,
                    "items": [
                        {
                            "dataset_id": "missing",
                            "task": "task",
                            "etag": '"revision" trailing',
                        }
                    ],
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 400, body)
        self.assert_problem_headers(headers)
        self.assertIn("strong ETag", json.loads(body)["detail"])

    def test_source_operations_expose_async_protocol_and_reject_ambiguous_batches(
        self,
    ) -> None:
        status, headers, body = self.request(
            "POST",
            "/api/source-import-operations",
            json.dumps({"path": "missing.jsonl", "adapter": "opencode"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        operation = json.loads(body)
        self.assertEqual(status, 202, body)
        self.assertEqual(headers["location"], f"/api/operations/{operation['id']}")
        self.assertEqual(headers["retry-after"], "1")
        self.assertIn(operation["state"], {"queued", "running", "failed"})

        status, headers, body = self.request(
            "POST",
            "/api/source-import-operations",
            json.dumps(
                {
                    "path": "one.jsonl\ntwo.jsonl",
                    "adapter": "opencode",
                    "session_ids": ["one", "two"],
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 422, body)
        self.assert_problem_headers(headers)
        self.assertIn("multiple paths", json.dumps(json.loads(body)["errors"]))

        status, headers, body = self.request(
            "POST",
            "/api/source-state-operations",
            json.dumps({"source_keys": [], "active": False}).encode(),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 422, body)
        self.assert_problem_headers(headers)

    def test_mount_create_rejects_fields_that_only_patch_can_apply(self) -> None:
        status, headers, body = self.request(
            "POST",
            "/api/harbor/mounts",
            json.dumps(
                {"path": "jobs", "id": "ignored", "dataset_ids": ["ignored"]}
            ).encode(),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 422, body)
        self.assert_problem_headers(headers)
        pointers = {item["pointer"] for item in json.loads(body)["errors"]}
        self.assertEqual(pointers, {"/dataset_ids", "/id"})

    def test_unknown_source_mutations_return_not_found(self) -> None:
        requests = [
            ("PATCH", "/api/sources/missing", {"alias": "name"}),
            (
                "POST",
                "/api/source-state-operations",
                {"source_keys": ["missing"], "active": False},
            ),
            (
                "POST",
                "/api/source-refresh-operations",
                {"source_keys": ["missing"]},
            ),
            (
                "POST",
                "/api/source-deletion-operations",
                {"source_keys": ["missing"]},
            ),
        ]
        for method, path, payload in requests:
            with self.subTest(path=path):
                status, headers, body = self.request(
                    method,
                    path,
                    json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                )
                self.assertEqual(status, 404, body)
                self.assert_problem_headers(headers)
                self.assertIn("unknown source", json.loads(body)["detail"])

    def test_browser_modules_revalidate_with_a_strong_etag(self) -> None:
        status, headers, body = self.request("GET", "/assets/peval/main.js")
        self.assertEqual(status, 200, body)
        self.assertTrue(body.strip())
        self.assertEqual(headers["cache-control"], "no-cache")
        self.assertEqual(
            headers["content-type"], "application/javascript; charset=utf-8"
        )
        self.assertRegex(headers["etag"], r'^"[0-9a-f]{64}"$')

        status, repeated_headers, repeated_body = self.request(
            "GET",
            "/assets/peval/main.js",
            headers={"If-None-Match": headers["etag"]},
        )
        self.assertEqual(status, 304, repeated_body)
        self.assertEqual(repeated_body, b"")
        self.assertEqual(repeated_headers["etag"], headers["etag"])
        self.assertEqual(repeated_headers["cache-control"], "no-cache")


if __name__ == "__main__":
    unittest.main()
