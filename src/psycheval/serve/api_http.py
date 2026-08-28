from __future__ import annotations

import base64
import binascii
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from psycheval.serve.constants import MAX_JSON_BODY_BYTES


class Problem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
    errors: list[dict[str, str]] | None = None


class ProblemException(Exception):
    def __init__(
        self,
        status: int,
        detail: str,
        *,
        slug: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.slug = slug or problem_slug(status)
        self.headers = headers or {}


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp, limit: int = MAX_JSON_BODY_BYTES) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                await _send_problem(scope, receive, send, 400, "invalid Content-Length")
                return
            if declared < 0:
                await _send_problem(scope, receive, send, 400, "invalid Content-Length")
                return
            if declared > self.limit:
                await _send_problem(
                    scope, receive, send, 413, "request body exceeds serve limit"
                )
                return
        messages = []
        received = 0
        while True:
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.limit:
                    await _send_problem(
                        scope, receive, send, 413, "request body exceeds serve limit"
                    )
                    return
                messages.append(message)
                if not message.get("more_body", False):
                    break
            else:
                messages.append(message)
                break

        async def replay_receive() -> Message:
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, replay_receive, send)


async def _send_problem(
    scope: Scope,
    receive: Receive,
    send: Send,
    status: int,
    detail: str,
) -> None:
    response = json_response(
        {
            "type": f"urn:peval:problem:{problem_slug(status)}",
            "title": problem_title(status),
            "status": status,
            "detail": detail,
            "instance": scope.get("path", ""),
        },
        status=status,
        media_type="application/problem+json",
    )
    await response(scope, receive, send)


def problem_title(status: int) -> str:
    return {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        409: "Conflict",
        412: "Precondition Failed",
        413: "Content Too Large",
        415: "Unsupported Media Type",
        422: "Unprocessable Content",
        428: "Precondition Required",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
    }.get(status, "HTTP Error")


def problem_slug(status: int) -> str:
    return problem_title(status).lower().replace(" ", "-")


def json_response(
    payload: Any,
    *,
    status: int = 200,
    headers: dict[str, str] | None = None,
    media_type: str = "application/json",
) -> JSONResponse:
    response_headers = {
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
    }
    response_headers.update(headers or {})
    return JSONResponse(
        payload,
        status_code=status,
        headers=response_headers,
        media_type=media_type,
    )


def etag(revision: str) -> str:
    return f'"{revision}"'


def if_match_value(value: str | None) -> str:
    if value is None:
        raise ProblemException(428, "If-Match is required")
    if value.startswith("W/") or len(value) < 2 or value[0] != '"' or value[-1] != '"':
        raise ProblemException(400, "If-Match must contain one strong ETag")
    revision = value[1:-1]
    if not revision or '"' in revision or "," in revision:
        raise ProblemException(400, "If-Match must contain one strong ETag")
    return revision


def expect_revision(expected_header: str | None, current: str) -> str:
    expected = if_match_value(expected_header)
    if expected != current:
        raise ProblemException(
            412,
            "resource changed; refresh before saving",
            headers={"ETag": etag(current)},
        )
    return expected


def opaque_path_token(value: str) -> str:
    encoded = base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def opaque_path_value(token: str) -> str:
    try:
        raw = token.encode("ascii")
        padding = b"=" * (-len(raw) % 4)
        value = base64.b64decode(raw + padding, altchars=b"-_", validate=True).decode(
            "utf-8"
        )
    except (UnicodeEncodeError, UnicodeDecodeError, binascii.Error, ValueError) as exc:
        raise ValueError("invalid opaque path token") from exc
    if not value or opaque_path_token(value) != token:
        raise ValueError("invalid opaque path token")
    return value
