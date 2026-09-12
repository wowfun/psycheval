from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from psycheval.config import ToolConfig
from psycheval.serve.access import ServeAccess
from psycheval.serve.api_http import BodyLimitMiddleware, ProblemException
from psycheval.serve.constants import MAX_JSON_BODY_BYTES
from psycheval.serve.jobs import register_jobs_routes
from tests.peval.test_jobs import jobs as jobs
from tests.peval.test_jobs import request, retained_run


@pytest.fixture
def client(jobs):
    app = FastAPI()
    app.state.runtime = SimpleNamespace(
        jobs=jobs,
        config=ToolConfig(),
        store=SimpleNamespace(paths=SimpleNamespace(root=jobs.workspace)),
    )
    app.state.access = ServeAccess("fixture-password")
    app.add_middleware(BodyLimitMiddleware)

    @app.exception_handler(ProblemException)
    async def problem(_, exc):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status)

    register_jobs_routes(app)
    with TestClient(app) as value:
        yield value


def test_guest_preview_is_read_only_and_bounded(client):
    assert client.post("/api/jobs/preview", json=request()).status_code == 200
    assert (
        client.post(
            "/api/jobs/preview", json=request(), headers={"Origin": "http://other.test"}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/jobs/preview", content="{}", headers={"Content-Type": "text/plain"}
        ).status_code
        == 415
    )
    payload = request()
    payload["tasks"] = [str(i) for i in range(1001)]
    assert client.post("/api/jobs/preview", json=payload).status_code == 422
    assert (
        client.post(
            "/api/jobs/preview", json={"large": "x" * MAX_JSON_BODY_BYTES}
        ).status_code
        == 413
    )
    assert client.post(f"/api/jobs/{'a' * 32}/stop", json={}).status_code == 403


def test_ten_thousand_results_are_paged_with_global_variant_means(
    client, jobs, monkeypatch
):
    run = retained_run(jobs, job_name="2026-09-11__10-00-00")
    monkeypatch.setattr(
        jobs.registry["fixture"],
        "read_results",
        lambda _: [
            {
                "id": str(i),
                "task": "one",
                "state": "completed",
                "score": i % 2,
                "score_source": "fixture",
                "variant_id": "a" if i % 2 else "b",
            }
            for i in range(10000)
        ],
    )
    response = client.get(f"/api/jobs/{run.name}?offset=50&variant_id=a")
    assert response.status_code == 200
    value = response.json()
    assert len(value["results"]) == 50
    assert value["result_count"] == 5000
    assert value["result_offset"] == 50
    assert value["results"][0]["id"] == "101"
    assert {row["id"]: row["mean"] for row in value["variant_summary"]} == {
        "a": 1,
        "b": 0,
    }
    assert len(response.content) < 50000


def test_large_finite_scores_do_not_overflow_variant_summary(client, jobs, monkeypatch):
    run = retained_run(jobs, job_name="2026-09-11__10-00-00")
    monkeypatch.setattr(
        jobs.registry["fixture"],
        "read_results",
        lambda _: [
            {
                "id": str(i),
                "task": "one",
                "state": "completed",
                "score": 1e308,
                "score_source": "fixture",
                "variant_id": "a",
            }
            for i in range(2)
        ],
    )
    response = client.get(f"/api/jobs/{run.name}")
    assert response.status_code == 200
    assert response.json()["variant_summary"][0]["mean"] == 1e308
    assert [r["score"] for r in response.json()["results"]] == [1e308, 1e308]
