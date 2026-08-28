from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.routing import APIRoute

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
        if not isinstance(route, APIRoute):
            continue
        label = f"{','.join(sorted(route.methods or []))} {route.path}"
        level = getattr(route.endpoint, "__peval_access__", None)
        if level is None:
            missing.append(label)
        elif level == ADMIN_ACCESS and not any(
            dependency.call is require_admin
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
