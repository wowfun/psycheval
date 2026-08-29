from __future__ import annotations

import socket
import sys

import uvicorn

from psycheval.cli.arguments import CliArgs
from psycheval.config import apply_overrides, config_for_adapter, load_config
from psycheval.inputs import parse_adapter_assignments
from psycheval.serve.access import ServeAccess
from psycheval.serve.acp import MAX_ACP_FRAME_BYTES
from psycheval.serve.api import create_app
from psycheval.serve.constants import DEFAULT_PORT_END, DEFAULT_PORT_START, LOCALHOSTS
from psycheval.serve.runtime import ServeRuntime
from psycheval.state import open_workspace_state


def run_serve_command(args: CliArgs) -> None:
    raw_host = getattr(args, "host", None) or "127.0.0.1"
    store = open_workspace_state(getattr(args, "root", None))
    listener: socket.socket | None = None
    runtime: ServeRuntime | None = None
    try:
        access = ServeAccess.from_workspace(store.paths.root)
        host = validate_bind_host(raw_host, access.authentication_enabled)
        config = apply_overrides(
            load_config(workspace_root=store.paths.root),
            args,
        )
        adapter_assignments = parse_adapter_assignments(
            getattr(args, "adapter", None) or [],
            config.adapter,
        )
        config = config_for_adapter(config, adapter_assignments.default_adapter)
        runtime = ServeRuntime(store, config, initialize_snapshot=False)
        listener = bind_listener(host, getattr(args, "port", None))
        actual_port = int(listener.getsockname()[1])
        print(f"peval serve: {format_url(host, actual_port)}", flush=True)
        if host.lower() not in LOCALHOSTS:
            print(
                "warning: non-local peval HTTP is for trusted private networks only; "
                "passwords and sessions are not protected by TLS",
                file=sys.stderr,
                flush=True,
            )
        runtime.start_initial_load(args, adapter_assignments)
        server = uvicorn.Server(
            uvicorn.Config(
                create_app(runtime, access),
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
                timeout_graceful_shutdown=5,
                log_config=None,
            )
        )
        server.run(sockets=[listener])
    except KeyboardInterrupt:
        return
    finally:
        if listener is not None:
            listener.close()
        if runtime is not None:
            runtime.close()
            runtime.wait_until_ready(timeout=5)
        store.close()


def validate_localhost(host: str) -> str:
    text = str(host).strip()
    normalized = text[1:-1] if text.startswith("[") and text.endswith("]") else text
    if normalized.lower() not in LOCALHOSTS:
        raise ValueError(
            "serve only binds localhost by default; use 127.0.0.1, localhost, or ::1"
        )
    return normalized


def validate_bind_host(host: str, authentication_enabled: bool) -> str:
    text = str(host).strip()
    normalized = text[1:-1] if text.startswith("[") and text.endswith("]") else text
    if not normalized:
        raise ValueError("serve host must not be empty")
    if normalized.lower() not in LOCALHOSTS and not authentication_enabled:
        raise ValueError(
            "non-local serve requires a non-empty PEVAL_ADMIN_PASSWORD in "
            "the process environment or workspace .env"
        )
    return normalized


def bind_listener(host: str, requested_port: int | None) -> socket.socket:
    if requested_port is not None:
        if isinstance(requested_port, bool) or not 0 <= requested_port <= 65535:
            raise ValueError("serve port must be between 0 and 65535")
        return _bind_port(host, requested_port)

    last_error: OSError | None = None
    for port in range(DEFAULT_PORT_START, DEFAULT_PORT_END + 1):
        try:
            return _bind_port(host, port)
        except OSError as exc:
            last_error = exc
    raise OSError(
        f"could not bind {host}:{DEFAULT_PORT_START}..{DEFAULT_PORT_END}"
    ) from last_error


def _bind_port(host: str, port: int) -> socket.socket:
    last_error: OSError | None = None
    try:
        addresses = socket.getaddrinfo(
            host,
            port,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
    except socket.gaierror as exc:
        raise OSError(f"could not resolve serve host {host}: {exc}") from exc
    for family, socktype, proto, _canonical, address in addresses:
        listener = socket.socket(family, socktype, proto)
        try:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.set_inheritable(False)
            listener.bind(address)
            listener.listen(128)
            return listener
        except OSError as exc:
            last_error = exc
            listener.close()
    assert last_error is not None
    raise last_error


def format_url(host: str, port: int) -> str:
    display_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
    return f"http://{display_host}:{port}/"
