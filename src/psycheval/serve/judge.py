"""Internal rubric inspection and diagnostic-run HTTP boundary."""

import asyncio
import json

from fastapi import Depends, FastAPI, Request
from fastapi.responses import Response
from pydantic import Field

from psycheval.judge_runs.service import PreviewConflict
from psycheval.serve.api_access import (
    ADMIN_ACCESS,
    GUEST_ACCESS,
    access,
    mutation_guard,
    require_admin,
    role_for,
)
from psycheval.serve.api_http import ProblemException, json_response
from psycheval.serve.api_models import BrowserPath, StrictRequest


class JudgePreviewRequest(StrictRequest):
    rubric_ids: list[str] | None = Field(default=None, max_length=32)
    all_rubrics: bool = False
    profile: str | None = None
    judge_config: str | None = Field(default=None, max_length=1024 * 1024)
    task: BrowserPath | None = None
    instruction_text: str | None = Field(default=None, max_length=1024 * 1024)


class JudgeRunRequest(JudgePreviewRequest):
    expected_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


def register_judge_routes(app: FastAPI):
    def target(request, source_key):
        runtime = request.app.state.runtime
        row = runtime.catalog.row_for_key(source_key)
        if row.get("kind") != "harbor-trial":
            raise ValueError("Judge inspection requires a Harbor Trial")
        return runtime.judge, row["source_ref"]

    def safe(request, action):
        try:
            return action()
        except (OSError, ValueError, KeyError) as exc:
            detail = (
                str(exc)
                if role_for(request) == ADMIN_ACCESS
                else "Judge source or diagnostic record unavailable"
            )
            raise ProblemException(422, detail) from exc

    def visible(request, value):
        if role_for(request) == ADMIN_ACCESS:
            return value

        # Source identities remain normalized mounted references. Connection
        # configuration is administrator-only; prompt text uses retained
        # file redaction, just like the Verification browser.
        def project(item):
            if isinstance(item, dict):
                return {
                    key: project(child)
                    for key, child in item.items()
                    if key not in {"base_url", "api_key"}
                }
            if isinstance(item, list):
                return [project(child) for child in item]
            return item

        return project(value)

    @app.get("/api/judge/{source_key}")
    @access(GUEST_ACCESS)
    def inspect(request: Request, source_key: str):
        def call():
            service, source = target(request, source_key)
            return json_response(visible(request, service.inspect(source_ref=source)))

        return safe(request, call)

    @app.get("/api/judge/{source_key}/prompt/{rubric_id}")
    @access(GUEST_ACCESS)
    def prompt(
        request: Request,
        source_key: str,
        rubric_id: str,
        download: bool = False,
    ):
        def call():
            service, source = target(request, source_key)
            value = service.prompt(rubric_id, source_ref=source)
            value = visible(request, value)
            if download:
                return Response(
                    json.dumps(value, ensure_ascii=False, indent=2),
                    media_type="application/json",
                    headers={
                        "Content-Disposition": 'attachment; filename="judge-prompt.json"',
                        "Cache-Control": "no-store",
                        "X-Content-Type-Options": "nosniff",
                    },
                )
            # Keep the regular read bounded for the browser without presenting a
            # clipped message as a complete recorded request.
            remaining = 2 * 1024 * 1024
            value["truncated"] = False
            for message in value.get("messages") or []:
                content = message["content"]
                message["content"] = content[:remaining]
                remaining = max(0, remaining - len(content))
                value["truncated"] |= len(message["content"]) != len(content)
            return json_response(value)

        return safe(request, call)

    @app.post(
        "/api/judge/{source_key}/preview",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def preview(request: Request, source_key: str, body: JudgePreviewRequest):
        def call():
            service, source = target(request, source_key)
            return json_response(
                service.preview(source_ref=source, **body.model_dump())
            )

        return safe(request, call)

    @app.post(
        "/api/judge/{source_key}/run",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    async def run(request: Request, source_key: str, body: JudgeRunRequest):
        service, source = safe(request, lambda: target(request, source_key))

        async def disconnected():
            while not await request.is_disconnected():
                await asyncio.sleep(0.05)

        execution = asyncio.create_task(
            service.run(source_ref=source, **body.model_dump())
        )
        disconnect = asyncio.create_task(disconnected())
        try:
            done, _ = await asyncio.wait(
                (execution, disconnect), return_when=asyncio.FIRST_COMPLETED
            )
            if disconnect in done:
                return Response(status_code=499)
            return json_response(await execution)
        except PreviewConflict as exc:
            raise ProblemException(409, str(exc)) from exc
        except (OSError, ValueError, KeyError) as exc:
            raise ProblemException(422, str(exc)) from exc
        finally:
            for task in (execution, disconnect):
                if not task.done():
                    task.cancel()
            await asyncio.gather(execution, disconnect, return_exceptions=True)
