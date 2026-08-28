from __future__ import annotations

from psycheval.config import HarborDataset
from psycheval.serve.path_picker import PathPickerUnavailable
from tests.peval.serve_state_support import (
    ECHARTS_ASSET_PATH,
    FIXTURES,
    HttpError,
    LocalHTTPServer,
    Path,
    ToolConfig,
    cached_echarts_asset,
    echarts_cache_path,
    http,
    json,
    make_handler,
    open_workspace_state,
    patch,
    peval_workspace,
    request_bytes,
    request_json,
    request_text,
    shutil,
    tempfile,
    threading,
    unittest,
    write_trial_cell_artifacts,
)


class PevalServeStateHttpSourceTests(unittest.TestCase):
    def test_http_upload_endpoint_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            config = ToolConfig(adapter="opencode")
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            try:
                status, headers, body = request_json(
                    port,
                    "POST",
                    "/api/upload",
                    {"filename": "report.json", "content": "{}"},
                    origin=f"http://127.0.0.1:{port}",
                )
                self.assertEqual(status, 404)
                self.assertNotIn("access-control-allow-origin", headers)
                self.assertEqual(body["detail"], "Not Found")
                self.assertEqual(store.source_payload(), [])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_path_picker_returns_paths_and_preserves_source_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            config = ToolConfig(adapter="opencode")
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, headers, body = request_json(
                    port,
                    "POST",
                    "/api/path-selections",
                    {"multiple": True},
                    origin="http://example.test",
                )
                self.assertEqual(status, 403)
                self.assertNotIn("access-control-allow-origin", headers)
                self.assertIn("same-origin", body["detail"])

                with patch(
                    "psycheval.serve.api.pick_file_paths",
                    return_value=["/tmp/one.jsonl", "/tmp/two.json"],
                ) as picker:
                    status, headers, body = request_json(
                        port,
                        "POST",
                        "/api/path-selections",
                        {"multiple": True},
                        origin=origin,
                    )
                self.assertEqual(status, 200)
                self.assertNotIn("access-control-allow-origin", headers)
                self.assertEqual(body, {"paths": ["/tmp/one.jsonl", "/tmp/two.json"]})
                picker.assert_called_once_with(multiple=True)

                status, _, body_bytes = request_bytes(port, "/api/sources")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body_bytes.decode("utf-8"))["sources"], [])

                with patch(
                    "psycheval.serve.api.pick_file_paths",
                    side_effect=PathPickerUnavailable("native file picker unavailable"),
                ):
                    status, _, body = request_json(
                        port,
                        "POST",
                        "/api/path-selections",
                        {"multiple": True},
                        origin=origin,
                    )
                self.assertEqual(status, 503)
                self.assertIn("native file picker unavailable", body["detail"])

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/path-selections",
                    {"multiple": "yes"},
                    origin=origin,
                )
                self.assertEqual(status, 422)
                self.assertEqual(body["errors"][0]["pointer"], "/multiple")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_echarts_asset_uses_workspace_cache_and_fake_download(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            config = ToolConfig(adapter="opencode")
            store = open_workspace_state(str(root))
            try:
                cache_path = echarts_cache_path(store)
                self.assertEqual(
                    cache_path,
                    root / ".cache" / "echarts" / "6.0.0" / "echarts.min.js",
                )
                cache_path.parent.mkdir(parents=True)
                cache_path.write_bytes(b"console.log('cached');")
                self.assertEqual(cached_echarts_asset(store), b"console.log('cached');")

                cache_path.unlink()
                with patch(
                    "psycheval.serve.assets.download_echarts_asset",
                    return_value=b"console.log('downloaded');",
                ):
                    self.assertEqual(
                        cached_echarts_asset(store), b"console.log('downloaded');"
                    )
                self.assertEqual(cache_path.read_bytes(), b"console.log('downloaded');")

                cache_path.unlink()
                with patch(
                    "psycheval.serve.assets.download_echarts_asset",
                    side_effect=RuntimeError("network down"),
                ):
                    with self.assertRaisesRegex(HttpError, "failed to cache ECharts"):
                        cached_echarts_asset(store)
            finally:
                store.close()

        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            config = ToolConfig(adapter="opencode")
            store = open_workspace_state(str(root))
            cache_path = echarts_cache_path(store)
            cache_path.parent.mkdir(parents=True)
            cache_path.write_bytes(b"window.echarts={};")
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            try:
                status, headers, body = request_bytes(port, ECHARTS_ASSET_PATH)
                self.assertEqual(status, 200)
                self.assertIn("application/javascript", headers["content-type"])
                self.assertEqual(
                    headers["cache-control"],
                    "public, max-age=31536000, immutable",
                )
                self.assertEqual(headers["x-content-type-options"], "nosniff")
                self.assertEqual(headers["referrer-policy"], "no-referrer")
                self.assertEqual(body, b"window.echarts={};")

                cache_path.unlink()
                with patch(
                    "psycheval.serve.assets.download_echarts_asset",
                    side_effect=RuntimeError("network down"),
                ):
                    status, _, body = request_bytes(port, ECHARTS_ASSET_PATH)
                self.assertEqual(status, 502)
                self.assertIn(b"failed to cache ECharts", body)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_source_alias_is_display_only_and_editable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            source = root / "common_session.jsonl"
            shutil.copy(FIXTURES / "common_session.jsonl", source)
            config = ToolConfig(adapter="opencode")
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {
                        "path": "common_session.jsonl",
                        "adapter": "opencode",
                        "alias": "Readable source",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 200)
                source_key = body["sources"][0]["source_key"]
                self.assertEqual(body["sources"][0]["source_alias"], "Readable source")
                self.assertEqual(
                    body["report"]["trajectory_meta"][0]["source_alias"],
                    "Readable source",
                )
                self.assertEqual(
                    body["report"]["trajectory"][0]["session_id"],
                    "common_session",
                )
                self.assertEqual(
                    body["report"]["trajectory_meta"][0]["data_ref"]["label"],
                    "common_session.jsonl",
                )

                status, _, body = request_json(
                    port,
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {"alias": "Renamed source"},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["sources"][0]["source_key"], source_key)
                self.assertEqual(body["sources"][0]["source_alias"], "Renamed source")
                self.assertEqual(
                    body["report"]["trajectory_meta"][0]["source_alias"],
                    "Renamed source",
                )

                status, _, body = request_json(
                    port,
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {
                        "alias": "Must not persist",
                        "notes": "x" * (1024 * 1024 + 1),
                    },
                    origin=origin,
                )
                self.assertEqual(status, 400)
                self.assertIn("notes.md", body["detail"])
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {"path": "common_session.jsonl", "adapter": "opencode"},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["sources"][0]["source_alias"], "Renamed source")

                status, _, body = request_json(
                    port,
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {"category": "  Regression  "},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["sources"][0]["source_category"], "Regression")
                self.assertEqual(
                    body["report"]["trajectory_meta"][0]["source_category"],
                    "Regression",
                )

                status, _, body = request_json(
                    port,
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {"tags": ["alpha", "beta", "alpha"]},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["sources"][0]["source_tags"], ["alpha", "beta"])
                self.assertEqual(
                    body["report"]["trajectory_meta"][0]["source_tags"],
                    ["alpha", "beta"],
                )

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {"path": "common_session.jsonl", "adapter": "opencode"},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["sources"][0]["source_key"], source_key)
                self.assertEqual(body["sources"][0]["source_alias"], "Renamed source")
                self.assertEqual(body["sources"][0]["source_category"], "Regression")
                self.assertEqual(body["sources"][0]["source_tags"], ["alpha", "beta"])

                status, _, body = request_json(
                    port,
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {"alias": ""},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["sources"][0]["source_key"], source_key)
                self.assertIsNone(body["sources"][0]["source_alias"])
                self.assertNotIn("source_alias", body["report"]["trajectory_meta"][0])

                status, _, body = request_json(
                    port,
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {"category": "   "},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertIsNone(body["sources"][0]["source_category"])
                self.assertNotIn(
                    "source_category", body["report"]["trajectory_meta"][0]
                )

                status, _, body = request_json(
                    port,
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {"tags": []},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["sources"][0]["source_tags"], [])
                self.assertNotIn("source_tags", body["report"]["trajectory_meta"][0])

                status, _, body = request_json(
                    port,
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {"category": ["not", "scalar"]},
                    origin=origin,
                )
                self.assertEqual(status, 422)
                self.assertEqual(body["errors"][0]["pointer"], "/category")

                status, _, body = request_json(
                    port,
                    "PATCH",
                    f"/api/sources/{source_key}",
                    {},
                    origin=origin,
                )
                self.assertEqual(status, 422)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_locale_endpoint_writes_workspace_config_and_updates_rendering(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            config = ToolConfig(adapter="opencode", locale="en")
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, rejected = request_json(
                    port,
                    "PATCH",
                    "/api/config",
                    {"locale": "zh"},
                    origin="http://example.test",
                )
                self.assertEqual(status, 403)
                self.assertIn("same-origin", rejected["detail"])

                config_status, config_headers, _config_body = request_bytes(
                    port, "/api/config"
                )
                self.assertEqual(config_status, 200)
                status, response_headers, body = request_json(
                    port,
                    "PATCH",
                    "/api/config",
                    {"locale": "zh"},
                    origin=origin,
                    request_headers={"If-Match": config_headers["etag"]},
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["locale"], "zh-CN")
                config_text = (root / "peval.toml").read_text(encoding="utf-8")
                self.assertIn('locale = "zh-CN"\n', config_text)

                status, _, html = request_text(port, "/datasets")
                self.assertEqual(status, 200)
                self.assertIn('<html lang="zh-CN">', html)
                self.assertIn("<title>评测工作台</title>", html)
                self.assertIn('aria-label="数据集"', html)
                self.assertNotIn('id="harbor-workbench-title"', html)

                status, _, body = request_json(
                    port,
                    "PATCH",
                    "/api/config",
                    {"locale": "en-US"},
                    origin=origin,
                    request_headers={"If-Match": response_headers["etag"]},
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["locale"], "en")
                self.assertIn(
                    'locale = "en"\n',
                    (root / "peval.toml").read_text(encoding="utf-8"),
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_adapter_default_db_endpoint_writes_config_and_updates_rendering(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            config = ToolConfig(adapter="opencode", locale="en")
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, rejected = request_json(
                    port,
                    "PATCH",
                    "/api/config",
                    {"adapter_defaults": {"opencode": "db/opencode.db"}},
                    origin="http://example.test",
                )
                self.assertEqual(status, 403)
                self.assertIn("same-origin", rejected["detail"])

                config_status, config_headers, _config_body = request_bytes(
                    port, "/api/config"
                )
                self.assertEqual(config_status, 200)
                status, response_headers, configured = request_json(
                    port,
                    "PATCH",
                    "/api/config",
                    {"adapter_defaults": {"missing": "db/missing.db"}},
                    origin=origin,
                    request_headers={"If-Match": config_headers["etag"]},
                )
                self.assertEqual(status, 422)
                self.assertIn("unsupported adapter", configured["detail"])

                status, response_headers, body = request_json(
                    port,
                    "PATCH",
                    "/api/config",
                    {"adapter_defaults": {"opencode": "db/opencode.db"}},
                    origin=origin,
                    request_headers={"If-Match": config_headers["etag"]},
                )
                expected = str((root / "db/opencode.db").resolve())
                self.assertEqual(status, 200)
                self.assertEqual(body["adapter_defaults"]["opencode"], expected)
                config_text = (root / "peval.toml").read_text(encoding="utf-8")
                self.assertIn("[adapters.opencode]\n", config_text)
                self.assertIn('default_db_path = "db/opencode.db"\n', config_text)

                status, _, html = request_text(port, "/config")
                self.assertEqual(status, 200)
                self.assertIn(
                    f'<option value="opencode"  data-default-db="{expected}">opencode</option>',
                    html,
                )

                status, _, body = request_json(
                    port,
                    "PATCH",
                    "/api/config",
                    {"adapter_defaults": {"opencode": None}},
                    origin=origin,
                    request_headers={"If-Match": response_headers["etag"]},
                )
                self.assertEqual(status, 200)
                self.assertNotIn("opencode", body["adapter_defaults"])
                self.assertNotIn(
                    "[adapters.opencode]\ndefault_db_path",
                    (root / "peval.toml").read_text(encoding="utf-8"),
                )

                status, _, html = request_text(port, "/config")
                self.assertEqual(status, 200)
                self.assertNotIn(expected, html)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_harbor_mount_config_adds_edits_and_removes_jobs_and_tasks(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp) / "workspace")
            (root / "peval.toml").write_text(
                '[adapters.opencode]\ndefault_db_path = "db/opencode.db"\n',
                encoding="utf-8",
            )
            jobs = Path(tmp) / "jobs"
            trial = jobs / "job-a" / "trial-a"
            trial.mkdir(parents=True)
            (trial.parent / "config.json").write_text(
                json.dumps({"job_name": "job-a", "jobs_dir": str(jobs)}),
                encoding="utf-8",
            )
            (trial / "config.json").write_text(
                json.dumps({"trial_name": "trial-a", "job_id": "job-a"}),
                encoding="utf-8",
            )
            dataset = Path(tmp) / "dataset"
            task = dataset / "task-a"
            task.mkdir(parents=True)
            task_toml = task / "task.toml"
            task_toml.write_text(
                '[task]\nname = "local/task-a"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )
            (task / "instruction.md").write_text("Do it.\n", encoding="utf-8")
            (task / "environment").mkdir()
            (task / "environment" / "Dockerfile").write_text(
                "FROM python:3.12-slim\n", encoding="utf-8"
            )
            (task / "tests").mkdir()
            (task / "tests" / "test.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            original_task = task_toml.read_bytes()
            with (root / "peval.toml").open("a", encoding="utf-8") as handle:
                handle.write(
                    "\n[[harbor.datasets]]\n"
                    'id = "pbench"\n'
                    f"path = {json.dumps(str(dataset))}\n"
                )
            config = ToolConfig(
                adapter="opencode",
                locale="en",
                harbor_datasets=(HarborDataset(id="pbench", path=str(dataset)),),
            )
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, mount_headers, mounts_body = request_bytes(
                    port, "/api/harbor/mounts"
                )
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(mounts_body), [])
                status, response_headers, _body = request_json(
                    port,
                    "POST",
                    "/api/harbor/mounts",
                    {"path": str(jobs)},
                    origin=origin,
                    request_headers={"If-Match": mount_headers["etag"]},
                )
                self.assertEqual(status, 200)
                status, _, mounts_body = request_bytes(port, "/api/harbor/mounts")
                self.assertEqual(status, 200)
                mounts = json.loads(mounts_body)
                self.assertEqual(mounts[0]["id"], "jobs")
                self.assertEqual(mounts[0]["dataset_ids"], [])

                status, response_headers, _body = request_json(
                    port,
                    "PATCH",
                    "/api/harbor/mounts/jobs",
                    {
                        "new_id": "pbench-jobs",
                        "path": str(jobs),
                        "dataset_ids": ["pbench"],
                    },
                    origin=origin,
                    request_headers={"If-Match": response_headers["etag"]},
                )
                self.assertEqual(status, 200)
                status, _, mounts_body = request_bytes(port, "/api/harbor/mounts")
                self.assertEqual(status, 200)
                mounts = json.loads(mounts_body)
                self.assertEqual(mounts[0]["id"], "pbench-jobs")
                self.assertEqual(mounts[0]["dataset_ids"], ["pbench"])
                config_text = (root / "peval.toml").read_text(encoding="utf-8")
                self.assertIn("[[harbor.mounts]]", config_text)
                self.assertIn('id = "pbench-jobs"', config_text)
                self.assertIn('dataset_ids = ["pbench"]', config_text)
                self.assertIn("[adapters.opencode]", config_text)

                status, _, html = request_text(port, "/config")
                self.assertEqual(status, 200)
                self.assertIn("data-harbor-mount-config", html)
                self.assertIn("data-harbor-dataset-registry", html)
                self.assertNotIn('value="pbench-jobs"', html)
                self.assertNotIn(str(dataset), html)

                before_invalid = config_text
                status, _, rejected = request_json(
                    port,
                    "PATCH",
                    "/api/harbor/mounts/pbench-jobs",
                    {
                        "new_id": "pbench-jobs",
                        "path": str(jobs),
                        "dataset_ids": ["missing"],
                    },
                    origin=origin,
                    request_headers={"If-Match": response_headers["etag"]},
                )
                self.assertEqual(status, 400)
                self.assertIn("unknown dataset id", rejected["detail"])
                self.assertEqual(
                    (root / "peval.toml").read_text(encoding="utf-8"),
                    before_invalid,
                )

                status, mount_headers, _mounts_body = request_bytes(
                    port, "/api/harbor/mounts"
                )
                self.assertEqual(status, 200)
                status, _, _body = request_json(
                    port,
                    "POST",
                    "/api/harbor/mount-deletion-operations",
                    {"mount_ids": ["pbench-jobs"]},
                    origin=origin,
                    request_headers={"If-Match": mount_headers["etag"]},
                )
                self.assertEqual(status, 200)
                status, _, mounts_body = request_bytes(port, "/api/harbor/mounts")
                self.assertEqual(json.loads(mounts_body), [])
                self.assertNotIn(
                    "[[harbor.mounts]]",
                    (root / "peval.toml").read_text(encoding="utf-8"),
                )
                self.assertEqual(task_toml.read_bytes(), original_task)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    @unittest.skip("superseded by compact mutation and background operation coverage")
    def test_http_sources_batch_path_quotes_failure_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            source_a = root / "common one.jsonl"
            source_b = root / "common_two.jsonl"
            shutil.copy(FIXTURES / "common_session.jsonl", source_a)
            shutil.copy(FIXTURES / "common_session.jsonl", source_b)
            config = ToolConfig(adapter="opencode")
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {
                        "path": "common one.jsonl\ncommon_two.jsonl",
                        "adapter": "opencode",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(len(body["sources"]), 2)
                source_keys = [source["source_key"] for source in body["sources"]]
                self.assertEqual(body["report_source_key"], source_keys[0])
                self.assertEqual(len(body["report"]["trajectory"]), 2)
                self.assertEqual(
                    [meta["trial_key"] for meta in body["report"]["trajectory_meta"]],
                    ["session:t001", "session:t001:2"],
                )
                artifact_dirs = {
                    source["source_key"]: root / source["artifact_dir"]
                    for source in body["sources"]
                }
                self.assertTrue(artifact_dirs[source_keys[0]].is_dir())
                self.assertTrue(artifact_dirs[source_keys[1]].is_dir())
                status, _, body = request_json(
                    port,
                    "POST",
                    f"/api/sources/{source_keys[1]}/alias",
                    {"alias": "Second source"},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["report_source_key"], source_keys[1])
                self.assertEqual(len(body["report"]["trajectory"]), 2)
                self.assertEqual(
                    body["report"]["trajectory_meta"][1]["source_alias"],
                    "Second source",
                )

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/refresh",
                    {},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(len(body["report"]["trajectory"]), 2)

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/sources/reload",
                    {},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(len(body["sources"]), 2)
                self.assertEqual(len(body["report"]["trajectory"]), 2)
                log_count = len(
                    store.paths.log_path.read_text(encoding="utf-8").splitlines()
                )

                status, _, failed = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {"path": "missing.jsonl", "adapter": "opencode"},
                    origin=origin,
                )
                self.assertEqual(status, 400)
                self.assertIn("missing.jsonl", failed["error"])
                self.assertEqual(len(store.source_payload()), 2)
                self.assertEqual(
                    len(store.paths.log_path.read_text(encoding="utf-8").splitlines()),
                    log_count,
                )

                status, _, body = request_json(
                    port,
                    "POST",
                    f"/api/sources/{source_keys[0]}/delete",
                    {},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(len(body["sources"]), 1)
                self.assertEqual(body["report_source_key"], source_keys[1])
                self.assertEqual(len(body["report"]["trajectory"]), 1)
                self.assertTrue(source_a.exists())
                self.assertFalse(artifact_dirs[source_keys[0]].exists())
                self.assertTrue(artifact_dirs[source_keys[1]].is_dir())
                self.assertNotIn(
                    source_keys[0],
                    [source["source_key"] for source in store.source_payload()],
                )

                status, _, rejected = request_json(
                    port,
                    "POST",
                    f"/api/sources/{source_keys[1]}/delete",
                    {},
                    origin="http://example.test",
                )
                self.assertEqual(status, 403)
                self.assertIn("same-origin", rejected["error"])
                self.assertEqual(len(store.source_payload()), 1)

                status, _, body = request_json(
                    port,
                    "POST",
                    f"/api/sources/{source_keys[1]}/delete",
                    {},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["sources"], [])
                self.assertIsNone(body["report_source_key"])
                self.assertEqual(body["report"]["trajectory"], [])
                self.assertFalse(artifact_dirs[source_keys[1]].exists())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_sources_auto_adapter_requires_path_inference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            untagged = root / "common_session.jsonl"
            inferred = root / ".opencode" / "common_session.jsonl"
            ambiguous = root / ".hermes" / "opencode" / "common_session.jsonl"
            inferred.parent.mkdir()
            ambiguous.parent.mkdir(parents=True)
            shutil.copy(FIXTURES / "common_session.jsonl", untagged)
            shutil.copy(FIXTURES / "common_session.jsonl", inferred)
            shutil.copy(FIXTURES / "common_session.jsonl", ambiguous)
            config = ToolConfig(adapter="opencode")
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, failed = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {"path": "common_session.jsonl", "adapter": "auto"},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(failed["state"], "failed")
                self.assertIn("could not infer adapter", failed["failures"][0]["error"])
                self.assertIn("available adapters", failed["failures"][0]["error"])
                self.assertEqual(store.source_payload(), [])

                status, _, failed = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {"path": "common_session.jsonl"},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(failed["state"], "failed")
                self.assertIn("could not infer adapter", failed["failures"][0]["error"])
                self.assertEqual(store.source_payload(), [])

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {"path": "common_session.jsonl", "adapter": "opencode"},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["sources"][0]["adapter"], "opencode")
                self.assertEqual(len(body["report"]["trajectory"]), 1)

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {"path": ".opencode/common_session.jsonl", "adapter": "auto"},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["sources"][0]["adapter"], "opencode")
                self.assertEqual(len(body["report"]["trajectory"]), 1)

                before_ambiguous = store.source_payload()
                status, _, failed = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {
                        "path": ".hermes/opencode/common_session.jsonl",
                        "adapter": "auto",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(failed["state"], "failed")
                self.assertIn(
                    "ambiguous adapter inference", failed["failures"][0]["error"]
                )
                self.assertEqual(store.source_payload(), before_ambiguous)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_path_batch_auto_adapter_records_inference_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp) / "workspace")
            inferred_dir = root / ".opencode"
            inferred_dir.mkdir()
            shutil.copy(
                FIXTURES / "common_session.jsonl", root / "common_session.jsonl"
            )
            shutil.copy(
                FIXTURES / "common_session.jsonl", inferred_dir / "common_session.jsonl"
            )
            config = ToolConfig(adapter="opencode", workspace_root=str(root))
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {
                        "path": "common_session.jsonl\n.opencode/common_session.jsonl",
                        "adapter": "auto",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    [result["status"] for result in body["import_results"]],
                    ["error", "ok"],
                )
                self.assertIn(
                    "could not infer adapter", body["import_results"][0]["error"]
                )
                self.assertEqual(len(body["import_results"][1]["source_keys"]), 1)
                self.assertEqual(len(body["sources"]), 1)
                self.assertEqual(body["sources"][0]["adapter"], "opencode")
                self.assertEqual(len(body["report"]["trajectory"]), 1)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_input_table_source_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            config = ToolConfig(adapter="opencode")
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {"input_table": "inputs.csv", "adapter": "auto"},
                    origin=origin,
                )
                self.assertEqual(status, 422)
                self.assertTrue(
                    any(error["pointer"] == "/input_table" for error in body["errors"])
                )
                self.assertEqual(store.source_payload(), [])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    @unittest.skip("interactive all-source report loading was removed")
    def test_http_report_source_state_and_batch_archive_activate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp))
            source_a = root / "common_one.jsonl"
            source_b = root / "common_two.jsonl"
            source_c = root / "common_three.jsonl"
            shutil.copy(FIXTURES / "common_session.jsonl", source_a)
            shutil.copy(FIXTURES / "common_session.jsonl", source_b)
            shutil.copy(FIXTURES / "common_session.jsonl", source_c)
            config = ToolConfig(adapter="opencode")
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"

            def get_report(path: str) -> tuple[int, dict]:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request("GET", path)
                response = conn.getresponse()
                payload = json.loads(response.read().decode("utf-8"))
                conn.close()
                return response.status, payload

            try:
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {
                        "path": "common_one.jsonl\ncommon_two.jsonl\ncommon_three.jsonl",
                        "adapter": "opencode",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 200)
                source_keys = [source["source_key"] for source in body["sources"]]
                self.assertEqual(len(source_keys), 3)
                self.assertEqual(len(body["report"]["trajectory"]), 3)

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/sources/state",
                    {
                        "source_keys": source_keys[1:],
                        "active": False,
                        "report_source_state": "active",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["report_source_state"], "active")
                self.assertEqual(body["report_source_key"], source_keys[0])
                self.assertEqual(len(body["report"]["trajectory"]), 1)
                self.assertEqual(
                    [source["active"] for source in body["sources"]],
                    [True, False, False],
                )

                status, active_report = get_report("/api/report")
                self.assertEqual(status, 200)
                self.assertEqual(len(active_report["trajectory"]), 1)
                status, archived_report = get_report(
                    "/api/report?source_state=archived"
                )
                self.assertEqual(status, 200)
                self.assertEqual(len(archived_report["trajectory"]), 2)
                self.assertEqual(
                    [meta["trial_key"] for meta in archived_report["trajectory_meta"]],
                    ["session:t001", "session:t001:2"],
                )
                status, single_report = get_report(
                    f"/api/report?source_key={source_keys[1]}&source_state=active"
                )
                self.assertEqual(status, 200)
                self.assertEqual(len(single_report["trajectory"]), 1)
                status, all_report = get_report("/api/report?source_state=all")
                self.assertEqual(status, 200)
                self.assertEqual(len(all_report["trajectory"]), 3)
                self.assertEqual(
                    [meta["trial_key"] for meta in all_report["trajectory_meta"]],
                    ["session:t001", "session:t001:2", "session:t001:3"],
                )

                status, _, bad_keys = request_json(
                    port,
                    "POST",
                    "/api/sources/state",
                    {
                        "source_keys": [source_keys[2], "missing-source"],
                        "active": True,
                        "report_source_state": "archived",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 400)
                self.assertIn("unknown source", bad_keys["error"])
                self.assertFalse(
                    next(
                        source
                        for source in store.source_payload()
                        if source["source_key"] == source_keys[2]
                    )["active"]
                )

                status, _, bad_active = request_json(
                    port,
                    "POST",
                    "/api/sources/state",
                    {
                        "source_keys": [source_keys[1]],
                        "active": "yes",
                        "report_source_state": "archived",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 400)
                self.assertIn("active must be true or false", bad_active["error"])

                status, _, bad_state = request_json(
                    port,
                    "POST",
                    "/api/sources/state",
                    {
                        "source_keys": [source_keys[1]],
                        "active": True,
                        "report_source_state": "all",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 400)
                self.assertIn(
                    "report_source_state must be active or archived", bad_state["error"]
                )

                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/sources/state",
                    {
                        "source_keys": [source_keys[1]],
                        "active": True,
                        "report_source_state": "archived",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["report_source_state"], "archived")
                self.assertEqual(body["report_source_key"], source_keys[2])
                self.assertEqual(len(body["report"]["trajectory"]), 1)
                self.assertEqual(
                    [source["active"] for source in body["sources"]],
                    [True, True, False],
                )

                status, _, rejected = request_json(
                    port,
                    "POST",
                    "/api/sources/state",
                    {
                        "source_keys": [source_keys[2]],
                        "active": True,
                        "report_source_state": "archived",
                    },
                    origin="http://example.test",
                )
                self.assertEqual(status, 403)
                self.assertIn("same-origin", rejected["error"])
                self.assertFalse(
                    next(
                        source
                        for source in store.source_payload()
                        if source["source_key"] == source_keys[2]
                    )["active"]
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_path_source_recursively_imports_external_runs_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp) / "workspace")
            external = peval_workspace(Path(tmp) / "external")
            first_cell = (
                external
                / "runs"
                / "external-eval"
                / "psychevo"
                / "session-a"
                / "session_t001"
            )
            second_cell = (
                external
                / "runs"
                / "external-eval"
                / "psychevo"
                / "session-b"
                / "session_t002"
            )
            write_trial_cell_artifacts(
                first_cell, session_id="session-a", trial_key="session_t001"
            )
            write_trial_cell_artifacts(
                second_cell, session_id="session-b", trial_key="session_t002"
            )
            (first_cell / "notes.md").write_text("Imported note.", encoding="utf-8")
            config = ToolConfig(adapter="opencode", workspace_root=str(root))
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {"path": str(external / "runs")},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(len(body["sources"]), 2)
                self.assertEqual(
                    body["report_source_key"], body["sources"][0]["source_key"]
                )
                self.assertEqual(len(body["report"]["trajectory"]), 2)
                self.assertEqual(
                    [source["trial_session_id"] for source in body["sources"]],
                    ["session-a", "session-b"],
                )
                self.assertTrue(body["sources"][0]["snapshot"])
                self.assertFalse(body["sources"][0]["refreshable"])
                copied_note = root / body["sources"][0]["artifact_dir"] / "notes.md"
                self.assertEqual(
                    copied_note.read_text(encoding="utf-8"), "Imported note."
                )
                self.assertTrue((first_cell / "notes.md").is_file())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_path_batch_import_continues_after_failed_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp) / "workspace")
            shutil.copy(
                FIXTURES / "common_session.jsonl", root / "common_session.jsonl"
            )
            config = ToolConfig(adapter="opencode", workspace_root=str(root))
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {
                        "path": "missing.jsonl\ncommon_session.jsonl",
                        "adapter": "opencode",
                    },
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(
                    [result["status"] for result in body["import_results"]],
                    ["error", "ok"],
                )
                self.assertIn("missing.jsonl", body["import_results"][0]["error"])
                self.assertEqual(len(body["import_results"][1]["source_keys"]), 1)
                self.assertEqual(len(body["sources"]), 1)
                self.assertFalse(body["sources"][0]["refreshable"])
                self.assertEqual(len(body["report"]["trajectory"]), 1)
                self.assertEqual(
                    body["report"]["trajectory"][0]["session_id"],
                    "common_session",
                )
                artifact_dir = root / body["sources"][0]["artifact_dir"]
                self.assertFalse((artifact_dir / ".peval" / "state.json").exists())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()

    def test_http_empty_runs_import_fails_without_persisting_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = peval_workspace(Path(tmp) / "workspace")
            external = peval_workspace(Path(tmp) / "external")
            (external / "runs" / "empty").mkdir(parents=True)
            config = ToolConfig(adapter="opencode", workspace_root=str(root))
            store = open_workspace_state(str(root))
            server = LocalHTTPServer(
                ("127.0.0.1", 0),
                make_handler(store, config),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            port = server.server_port
            origin = f"http://127.0.0.1:{port}"
            try:
                status, _, body = request_json(
                    port,
                    "POST",
                    "/api/source-import-operations",
                    {"path": str(external / "runs")},
                    origin=origin,
                )
                self.assertEqual(status, 200)
                self.assertEqual(body["state"], "failed")
                self.assertIn(
                    "no complete Trial cells found", body["failures"][0]["error"]
                )
                self.assertEqual(store.source_payload(), [])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                store.close()
