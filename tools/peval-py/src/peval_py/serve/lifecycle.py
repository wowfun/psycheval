from __future__ import annotations

from argparse import Namespace
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer

from peval_py.config import apply_overrides, config_for_adapter, load_config
from peval_py.inputs import parse_adapter_assignments
from peval_py.serve.constants import DEFAULT_PORT_END, DEFAULT_PORT_START, LOCALHOSTS
from peval_py.serve.handler import make_handler
from peval_py.serve.runtime import ServeRuntime
from peval_py.state import open_workspace_state


class LocalHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_serve_command(
    args: Namespace,
) -> None:
    host = validate_localhost(getattr(args, "host", None) or "127.0.0.1")
    store = open_workspace_state(getattr(args, "root", None))
    server: HTTPServer | None = None
    runtime: ServeRuntime | None = None
    try:
        config = apply_overrides(
            load_config(
                getattr(args, "config", None),
                workspace_root=str(store.paths.root),
            ),
            args,
        )
        adapter_assignments = parse_adapter_assignments(
            getattr(args, "adapter", None) or [],
            config.adapter,
        )
        config = config_for_adapter(config, adapter_assignments.default_adapter)
        runtime = ServeRuntime(store, config, initialize_snapshot=False)
        handler = make_handler(runtime)
        server = bind_server(host, getattr(args, "port", None), handler)
        print(f"peval-py serve: {format_url(host, server.server_port)}", flush=True)
        runtime.start_initial_load(args, adapter_assignments)
        server.serve_forever()
    except KeyboardInterrupt:
        return
    finally:
        if server is not None:
            server.server_close()
        if runtime is not None:
            runtime.wait_until_ready(timeout=5)
        store.close()


def validate_localhost(host: str) -> str:
    text = str(host).strip()
    normalized = text[1:-1] if text.startswith("[") and text.endswith("]") else text
    if normalized.lower() not in LOCALHOSTS:
        raise ValueError("serve only binds localhost by default; use 127.0.0.1, localhost, or ::1")
    return normalized


def bind_server(
    host: str,
    requested_port: int | None,
    handler: type[BaseHTTPRequestHandler],
) -> HTTPServer:
    if requested_port is not None:
        return LocalHTTPServer((host, requested_port), handler)

    last_error: OSError | None = None
    for port in range(DEFAULT_PORT_START, DEFAULT_PORT_END + 1):
        try:
            return LocalHTTPServer((host, port), handler)
        except OSError as exc:
            last_error = exc
    raise OSError(
        f"could not bind {host}:{DEFAULT_PORT_START}..{DEFAULT_PORT_END}"
    ) from last_error


def format_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"http://{display_host}:{port}/"
