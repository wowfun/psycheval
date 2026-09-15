"""Internal Jobs HTTP endpoints; guest reads and administrator mutations."""

from statistics import mean
from typing import Any

from fastapi import Depends, FastAPI, Query, Request

from psycheval.jobs.service import JobsConflict, JobsService
from psycheval.serve.api_access import (
    ADMIN_ACCESS,
    GUEST_ACCESS,
    access,
    mutation_guard,
    require_admin,
)
from psycheval.serve.api_http import ProblemException, json_response


def register_jobs_routes(app: FastAPI):
    def service(request: Request) -> JobsService:
        return request.app.state.runtime.jobs

    def call(action, *args):
        try:
            return json_response(action(*args))
        except JobsConflict as exc:
            raise ProblemException(409, str(exc)) from exc
        except (ValueError, OSError) as exc:
            raise ProblemException(422, str(exc)) from exc

    @app.get("/api/jobs/options")
    @access(GUEST_ACCESS)
    def options(request: Request):
        return call(service(request).options)

    @app.get("/api/jobs/tasks/{harness_id}")
    @access(GUEST_ACCESS)
    def tasks(request: Request, harness_id: str):
        return call(lambda: {"datasets": service(request).catalog(harness_id)})

    @app.post("/api/jobs/preview", dependencies=[Depends(mutation_guard)])
    @access(GUEST_ACCESS)
    def preview(request: Request, payload: dict[str, Any]):
        return call(service(request).preview, payload)

    @app.put(
        "/api/jobs/preferred-harness",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def preferred_harness(request: Request, payload: dict[str, Any]):
        return call(
            service(request).save_preferred_harness,
            payload.get("harness"),
            payload.get("revision"),
        )

    @app.put(
        "/api/jobs/defaults/{harness_id}",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def defaults(request: Request, harness_id: str, payload: dict[str, Any]):
        return call(
            service(request).save_defaults,
            harness_id,
            payload.get("defaults"),
            payload.get("revision"),
        )

    @app.get("/api/jobs")
    @access(GUEST_ACCESS)
    def listing(request: Request):
        return call(lambda: {"items": request.app.state.runtime.jobs_list()})

    @app.post(
        "/api/jobs", dependencies=[Depends(require_admin), Depends(mutation_guard)]
    )
    @access(ADMIN_ACCESS)
    def start(request: Request, payload: dict[str, Any]):
        return call(
            service(request).start,
            payload.get("request"),
            payload.get("preview_id"),
            payload.get("request_id"),
        )

    @app.get("/api/jobs/{run_id}")
    @access(GUEST_ACCESS)
    def detail(
        request: Request,
        run_id: str,
        offset: int = Query(0, ge=0, le=10000),
        variant_id: str | None = Query(None, max_length=100),
    ):
        def project():
            from psycheval.state.jobs import result_identity_resolver

            runtime = request.app.state.runtime
            value = service(request).detail(run_id)
            results = value["results"]
            groups = {}
            for item in results:
                key = item.get("variant_id") or ""
                group = groups.setdefault(
                    key,
                    {
                        "id": key,
                        "label": item.get("variant_label") or key,
                        "count": 0,
                        "scored": 0,
                        "scores": [],
                    },
                )
                group["count"] += 1
                if item.get("score") is not None:
                    group["scored"] += 1
                    group["scores"].append(item["score"])
            value["variant_summary"] = [
                {
                    "id": group["id"],
                    "label": group["label"],
                    "count": group["count"],
                    "scored": group["scored"],
                    "mean": mean(group["scores"]) if group["scores"] else None,
                }
                for group in groups.values()
            ]
            if variant_id is not None:
                results = [
                    item for item in results if item.get("variant_id") == variant_id
                ]
            value["result_count"] = len(results)
            value["result_offset"] = offset
            value["results"] = results[offset : offset + 50]
            identity = result_identity_resolver(
                runtime.store.paths.root, runtime.config, value
            )
            for result in value["results"]:
                result["source_key"] = identity(result)
            return value

        return call(project)

    @app.get("/api/jobs/{run_id}/logs")
    @access(GUEST_ACCESS)
    def logs(request: Request, run_id: str):
        return call(lambda: {"text": service(request).logs(run_id)})

    @app.post(
        "/api/jobs/{run_id}/stop",
        dependencies=[Depends(require_admin), Depends(mutation_guard)],
    )
    @access(ADMIN_ACCESS)
    def stop(request: Request, run_id: str):
        return call(service(request).stop, run_id)
