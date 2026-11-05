from __future__ import annotations

import http.client
import json
import threading
import unittest
from pathlib import Path

from psycheval.config import ToolConfig
from psycheval.metric_contract import DEFAULT_METRIC_IDS
from psycheval.serve import ServeAccess, ServeRuntime
from psycheval.state import open_workspace_state
from tests.peval.asgi_server import LocalHTTPServer, make_handler


def leaderboard_summary_query(**changes) -> dict:
    payload = {
        "state": "active",
        "search": "",
        "categories": [],
        "tags": [],
        "agents": [],
        "models": [],
        "tasks": [],
        "jobs": [],
        "providers": [],
        "datasets": [],
        "results": [],
        "views": [],
        "browser_views": [],
        "group_by": "overall",
    }
    payload.update(changes)
    return payload


def summary_request(query, group_by="overall", statistic="mean"):
    return {
        "scope": "leaderboard",
        "metrics": list(DEFAULT_METRIC_IDS),
        "query": query,
        "group_by": group_by,
        "statistic": statistic,
    }


class CatalogHttpTestCase(unittest.TestCase):
    def running_server(self, root: Path, *, access: ServeAccess | None = None):
        (root / "peval.toml").write_text(
            'analysis_eval_slug = "default"\n', encoding="utf-8"
        )
        store = open_workspace_state(str(root))
        runtime = ServeRuntime(
            store,
            ToolConfig(workspace_root=str(root), analysis_eval_slug="default"),
        )
        server = LocalHTTPServer(
            ("127.0.0.1", 0),
            make_handler(runtime, access=access),
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return store, runtime, server, thread

    def request(
        self,
        server: LocalHTTPServer,
        method: str,
        path: str,
        payload: dict | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {}
        if body is not None:
            headers = {
                "Content-Type": "application/json",
                "Origin": f"http://127.0.0.1:{server.server_port}",
            }
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_port, timeout=5
        )
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        content = response.read()
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        connection.close()
        return response.status, response_headers, content

    def stop(self, store, server, thread) -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        store.close()
