import json
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


def test_preferred_harness_requires_admin_and_current_revision(client, jobs):
    options = client.get("/api/jobs/options").json()
    assert options["preferred_harness"] is None
    payload = {"harness": "fixture", "revision": options["revision"]}
    assert client.put("/api/jobs/preferred-harness", json=payload).status_code == 403
    token = client.app.state.access.login("fixture-password", "testclient")
    client.cookies.set("peval_admin_session", token)
    assert (
        client.put(
            "/api/jobs/preferred-harness",
            json=payload,
            headers={"Origin": "http://other.test"},
        ).status_code
        == 403
    )
    response = client.put("/api/jobs/preferred-harness", json=payload)
    assert response.status_code == 200
    assert response.json()["preferred_harness"] == "fixture"
    assert jobs.configuration()[0]["jobs"]["preferred_harness"] == "fixture"
    assert client.put("/api/jobs/preferred-harness", json=payload).status_code == 409
    payload.update(harness="missing", revision=response.json()["revision"])
    assert client.put("/api/jobs/preferred-harness", json=payload).status_code == 422


def test_http_start_without_preview(client):
    payload = {"request": request(), "request_id": "direct-http-start"}
    assert client.post("/api/jobs", json=payload).status_code == 403
    token = client.app.state.access.login("fixture-password", "testclient")
    client.cookies.set("peval_admin_session", token)
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 200
    assert response.json()["request"] == request()


def test_log_entries_accept_arbitrary_json_and_keep_plain_text(client, jobs):
    run = retained_run(jobs)
    values = [
        {"arbitrary": ["中文", {"warning": "下游告警", "error": "下游报错"}]},
        [1, False, None],
        "a string",
        900719925474099312345,
        0.25,
        True,
        False,
        None,
        {"html": '<svg onload="unsafe()">'},
    ]
    raw = "\r\n".join(json.dumps(value, ensure_ascii=False) for value in values)
    raw += "\n\nTraceback (most recent call last):\n  fixture failure\n{invalid}\n"
    (run / "worker.log").write_bytes(raw.encode("utf-8"))
    response = client.get(f"/api/jobs/{run.name}/logs")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"entries", "truncated"}
    assert data["truncated"] is False
    assert [json.loads(entry["text"]) for entry in data["entries"][:-1]] == values
    assert all(entry["format"] == "json" for entry in data["entries"][:-1])
    assert data["entries"][-1] == {
        "format": "text",
        "text": "\nTraceback (most recent call last):\n  fixture failure\n{invalid}",
    }
    assert "900719925474099312345" in response.text


def test_logs_replace_partial_lines_and_do_not_repeat_events(client, jobs):
    run = retained_run(jobs)
    path = run / "worker.log"
    assert client.get(f"/api/jobs/{run.name}/logs").json() == {
        "entries": [],
        "truncated": False,
    }
    path.write_bytes(b'{"event":1}\n{"next":')
    first = client.get(f"/api/jobs/{run.name}/logs").json()
    assert [entry["format"] for entry in first["entries"]] == ["json", "text"]
    assert first["entries"][-1]["text"] == '{"next":'
    with path.open("ab") as stream:
        stream.write(b"true}\n")
    second = client.get(f"/api/jobs/{run.name}/logs").json()
    assert [json.loads(entry["text"]) for entry in second["entries"]] == [
        {"event": 1},
        {"next": True},
    ]
    assert client.get(f"/api/jobs/{run.name}/logs").json() == second


def test_logs_redact_json_and_incomplete_text_without_changing_disk(
    client, jobs, monkeypatch
):
    monkeypatch.setenv("FIXTURE_API_KEY", "fixture-environment-secret")
    run = retained_run(jobs)
    raw = (
        '{"nested":{"api_key":"literal-secret","reference":"${API_KEY}"},'
        '"msg":"fixture-environment-secret"}\n'
        'Bearer private-value\n{"password":"partial-secret'
    )
    path = run / "worker.log"
    path.write_text(raw, encoding="utf-8")
    response = client.get(f"/api/jobs/{run.name}/logs")
    assert response.status_code == 200
    for secret in (
        "literal-secret",
        "fixture-environment-secret",
        "private-value",
        "partial-secret",
    ):
        assert secret not in response.text
    assert "${API_KEY}" in response.text
    assert path.read_text(encoding="utf-8") == raw


@pytest.mark.parametrize(
    "prefix",
    [b"x" * (128 * 1024), b"x\n" * (64 * 1024)],
    ids=["long-line", "many-lines"],
)
def test_log_tail_marks_truncation_and_keeps_complete_events(
    client, jobs, prefix, monkeypatch
):
    from psycheval.jobs import service as service_module

    inspected = []
    redact = service_module.redact_retained_text

    def inspect_once(text):
        inspected.append(len(text))
        return redact(text)

    monkeypatch.setattr(service_module, "redact_retained_text", inspect_once)
    run = retained_run(jobs)
    path = run / "worker.log"
    path.write_bytes(prefix + b'\n{"tail":true}\n')
    value = client.get(f"/api/jobs/{run.name}/logs").json()
    assert value["truncated"] is True
    assert json.loads(value["entries"][-1]["text"]) == {"tail": True}
    assert value["entries"][0]["format"] == "text"
    assert len(inspected) == 1
    assert sum(inspected) <= 128 * 1024


def test_deep_or_nonfinite_json_falls_back_without_breaking_later_lines(client, jobs):
    run = retained_run(jobs)
    deep = "[" * 1200 + "0" + "]" * 1200
    (run / "worker.log").write_text(deep + '\nNaN\n{"ok":true}\n', encoding="utf-8")
    response = client.get(f"/api/jobs/{run.name}/logs")
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert entries[0] == {"format": "text", "text": deep + "\nNaN"}
    assert json.loads(entries[1]["text"]) == {"ok": True}


def test_log_json_escaped_surrogate_is_safe_to_transport(client, jobs):
    run = retained_run(jobs)
    (run / "worker.log").write_bytes(b'"\\ud800"\n')
    response = client.get(f"/api/jobs/{run.name}/logs")
    assert response.status_code == 200
    assert response.json()["entries"] == [{"format": "json", "text": '"\\ud800"'}]


def test_partial_utf8_log_line_becomes_one_complete_event(client, jobs):
    run = retained_run(jobs)
    path = run / "worker.log"
    raw = '{"任意":"中文"}\n'.encode("utf-8")
    path.write_bytes(raw[:3])
    first = client.get(f"/api/jobs/{run.name}/logs").json()
    assert first["entries"][0]["format"] == "text"
    with path.open("ab") as stream:
        stream.write(raw[3:])
    second = client.get(f"/api/jobs/{run.name}/logs").json()
    assert len(second["entries"]) == 1
    assert second["entries"][0]["format"] == "json"
    assert json.loads(second["entries"][0]["text"]) == {"任意": "中文"}


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
