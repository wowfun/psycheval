from __future__ import annotations

import ipaddress
from collections.abc import Callable
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, WebSocket, WebSocketException
from fastapi.routing import APIRoute, APIWebSocketRoute

from psycheval.serve.access import ADMIN_ROLE, ServeAccess
from psycheval.serve.api_http import ProblemException

AccessLevel = Literal["guest", "admin"]
GUEST_ACCESS: AccessLevel = "guest"
ADMIN_ACCESS: AccessLevel = "admin"


def access(level: AccessLevel) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorate(endpoint: Callable[..., Any]) -> Callable[..., Any]:
        setattr(endpoint, "__peval_access__", level)
        return endpoint

    return decorate


def role_for(request: Request) -> str:
    control: ServeAccess = request.app.state.access
    return control.role(request.headers.get("cookie"))


def require_admin(request: Request) -> None:
    if role_for(request) != ADMIN_ROLE:
        raise ProblemException(403, "administrator access required")


_FORWARDING_HEADERS = (
    "forwarded",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-real-ip",
)


def _is_loopback_ip(value: str) -> bool:
    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    host = text.partition("%")[0]
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped.is_loopback
    return address.is_loopback


def _is_localhost_host_header(host: str | None) -> bool:
    if not host:
        return False
    try:
        parsed = urlsplit(f"http://{host.strip()}")
    except ValueError:
        return False
    if (
        not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        return False
    hostname = parsed.hostname.lower().rstrip(".")
    return hostname == "localhost" or _is_loopback_ip(hostname)


def is_localhost_request(request: Request) -> bool:
    """Return True only for direct loopback connections targeting localhost."""
    if request.client is None or not _is_loopback_ip(request.client.host):
        return False
    if not _is_localhost_host_header(request.headers.get("host")):
        return False
    if any(request.headers.get(name) is not None for name in _FORWARDING_HEADERS):
        return False
    return True


def require_localhost(request: Request) -> None:
    if not is_localhost_request(request):
        raise ProblemException(
            403, "file manager reveal is only available on localhost"
        )


def role_for_websocket(websocket: WebSocket) -> str:
    control: ServeAccess = websocket.app.state.access
    return control.role(websocket.headers.get("cookie"))


def require_admin_websocket(websocket: WebSocket) -> None:
    if role_for_websocket(websocket) != ADMIN_ROLE:
        raise WebSocketException(code=1008, reason="administrator access required")


def require_same_origin_websocket(websocket: WebSocket) -> None:
    host = websocket.headers.get("host")
    origin = websocket.headers.get("origin")
    if not host or not origin:
        raise WebSocketException(code=1008, reason="ACP requires a same-origin client")
    try:
        parsed = urlsplit(origin)
    except ValueError:
        parsed = None
    expected_scheme = "https" if websocket.url.scheme == "wss" else "http"
    if (
        parsed is None
        or parsed.scheme != expected_scheme
        or parsed.netloc.lower() != host.lower()
        or bool(parsed.path or parsed.query or parsed.fragment)
    ):
        raise WebSocketException(code=1008, reason="ACP requires a same-origin client")


def require_same_origin(request: Request) -> None:
    host = request.headers.get("host")
    if not host:
        raise ProblemException(403, "mutating APIs require a Host header")
    for name in ("origin", "referer"):
        value = request.headers.get(name)
        if value is None:
            continue
        try:
            parsed = urlsplit(value)
        except ValueError:
            parsed = None
        if (
            parsed is None
            or parsed.scheme != "http"
            or not parsed.netloc
            or parsed.netloc.lower() != host.lower()
            or (name == "origin" and (parsed.path or parsed.query or parsed.fragment))
        ):
            raise ProblemException(
                403, f"mutating APIs require same-origin {name.title()}"
            )


def mutation_guard(request: Request) -> None:
    require_same_origin(request)
    content_type = request.headers.get("content-type")
    if request.method in {"POST", "PUT", "PATCH"} and not content_type:
        raise ProblemException(415, "mutating APIs accept application/json only")
    if (
        content_type
        and content_type.partition(";")[0].strip().lower() != "application/json"
    ):
        raise ProblemException(415, "mutating APIs accept application/json only")


def verify_route_access(app: FastAPI) -> None:
    missing = []
    unenforced_admin = []
    for route in app.routes:
        if not isinstance(route, (APIRoute, APIWebSocketRoute)):
            continue
        methods = getattr(route, "methods", None)
        label = f"{','.join(sorted(methods or ['WEBSOCKET']))} {route.path}"
        level = getattr(route.endpoint, "__peval_access__", None)
        if level is None:
            missing.append(label)
        elif level == ADMIN_ACCESS:
            expected = (
                require_admin_websocket
                if isinstance(route, APIWebSocketRoute)
                else require_admin
            )
            if not any(
                dependency.call is expected
                for dependency in route.dependant.dependencies
            ):
                unenforced_admin.append(label)
    if missing:
        raise RuntimeError(f"serve routes missing access classification: {missing}")
    if unenforced_admin:
        raise RuntimeError(
            "serve administrator routes missing administrator dependency: "
            f"{unenforced_admin}"
        )
