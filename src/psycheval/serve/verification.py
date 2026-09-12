"""Read-only HTTP access to retained verification files."""

import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.background import BackgroundTask

from psycheval.serve.api_access import GUEST_ACCESS, access
from psycheval.serve.api_http import (
    ProblemException,
    content_disposition,
    json_response,
)
from psycheval.serve.runtime import ServeRuntime
from psycheval.state.verification_files import (
    read_verification_file,
    verification_file_tree,
)


def register_verification_routes(app: FastAPI) -> None:
    def verification_location(runtime: ServeRuntime, source_key: str):
        row = runtime.catalog.row_for_key(source_key)
        if row.get("kind") != "harbor-trial":
            return None
        return runtime.catalog.sources.verification_file_location(row["source_ref"])

    @app.get("/api/verification-files/{source_key}")
    @access(GUEST_ACCESS)
    def verification_files(request: Request, source_key: str) -> JSONResponse:
        try:
            location = verification_location(request.app.state.runtime, source_key)
            tree = verification_file_tree(*location) if location else []
        except (OSError, ValueError) as exc:
            raise ProblemException(404, str(exc)) from exc
        return json_response({"tree": tree})

    @app.get(
        "/api/verification-files/{source_key}/{file_id}",
    )
    @access(GUEST_ACCESS)
    def verification_file(
        request: Request, source_key: str, file_id: str, download: bool = False
    ) -> Response:
        try:
            if re.fullmatch(r"[0-9a-f]{24}", file_id) is None:
                raise ValueError("unknown verification file")
            location = verification_location(request.app.state.runtime, source_key)
            if location is None:
                raise ValueError("source has no retained verification files")
            content = read_verification_file(*location, file_id, download=download)
        except (OSError, ValueError) as exc:
            raise ProblemException(404, str(exc)) from exc
        if isinstance(content, dict):
            return json_response(content)
        headers = {
            "Content-Disposition": content_disposition(
                "attachment" if download else "inline", content.filename
            ),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
            "Referrer-Policy": "no-referrer",
        }
        if download:
            return StreamingResponse(
                content.chunks,
                media_type=content.media_type,
                headers=headers,
                background=BackgroundTask(content.close),
            )
        return Response(content.content, media_type=content.media_type, headers=headers)
