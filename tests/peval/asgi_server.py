from __future__ import annotations

import socket
import threading
from typing import Any

import uvicorn

from psycheval.config import ToolConfig
from psycheval.serve.access import ServeAccess
from psycheval.serve.acp import MAX_ACP_FRAME_BYTES
from psycheval.serve.api import create_app
from psycheval.serve.lifecycle import bind_listener
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import ServeStateStore


def make_handler(
    store_or_runtime: ServeStateStore | ServeRuntime,
    config: ToolConfig | None = None,
    *,
    access: ServeAccess | None = None,
):
    if isinstance(store_or_runtime, ServeRuntime):
        runtime = store_or_runtime
        owns_runtime = False
    else:
        if config is None:
            raise ValueError("config is required when make_handler receives a store")
        runtime = ServeRuntime(store_or_runtime, config)
        owns_runtime = True
    app = create_app(runtime, access or ServeAccess(None))
    app.state.test_owns_runtime = owns_runtime
    return app


class LocalHTTPServer:
    """Thread-friendly Uvicorn host used only by HTTP integration tests."""

    def __init__(self, address: tuple[str, int], app: Any) -> None:
        self._initialize(bind_listener(address[0], address[1]), app)

    @classmethod
    def from_listener(cls, listener: socket.socket, app: Any) -> LocalHTTPServer:
        server = cls.__new__(cls)
        server._initialize(listener, app)
        return server

    def _initialize(self, listener: socket.socket, app: Any) -> None:
        self._listener = listener
        self._app = app
        self._started = False
        self._finished = threading.Event()
        self.server_address = listener.getsockname()
        self.server_port = int(self.server_address[1])
        self._server = uvicorn.Server(
            uvicorn.Config(
                app,
                loop="asyncio",
                http="h11",
                ws="websockets-sansio",
                ws_max_size=MAX_ACP_FRAME_BYTES,
                ws_max_queue=16,
                ws_ping_interval=20,
                ws_ping_timeout=20,
                lifespan="off",
                workers=1,
                proxy_headers=False,
                access_log=False,
                server_header=False,
                timeout_graceful_shutdown=1,
                log_config=None,
            )
        )

    def serve_forever(self) -> None:
        self._started = True
        try:
            self._server.run(sockets=[self._listener])
        finally:
            self._finished.set()

    def shutdown(self) -> None:
        self._server.should_exit = True
        if self._started:
            self._finished.wait(timeout=5)

    def server_close(self) -> None:
        if not self._started and self._listener.fileno() >= 0:
            self._listener.close()
        if getattr(self._app.state, "test_owns_runtime", False):
            self._app.state.runtime.close()
            self._app.state.runtime.wait_until_ready(timeout=5)


def bind_server(host: str, port: int | None, app: Any) -> LocalHTTPServer:
    return LocalHTTPServer.from_listener(bind_listener(host, port), app)
