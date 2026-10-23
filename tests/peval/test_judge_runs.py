import asyncio
import json
import shutil
import subprocess
import sys
import threading
from dataclasses import replace

import httpx
import pytest
import tomlkit
import yaml

from psycheval.cli import main
from psycheval.config import load_config
from psycheval.harbor.verifier import (
    JudgeSettings,
    parse_judge_config,
    prepare_judge,
    run_judge,
    run_verifier,
)
from psycheval.judge_runs.service import JudgeService, PreviewConflict
from psycheval.serve import ServeAccess, ServeRuntime
from psycheval.state import CatalogQuery, open_workspace_state
from tests.fixtures.judge_server import judge_server
from tests.fixtures.judge_task import YAML, api_task
from tests.peval.asgi_server import LocalHTTPServer, make_handler


@pytest.fixture
def experiment(tmp_path):
    with judge_server() as provider:
        trial = tmp_path / "jobs/job/trial"
        logs = trial / "verifier"
        logs.mkdir(parents=True)
        grader, context = api_task(tmp_path / "task")
        context = replace(
            context, paths=replace(context.paths, verifier_logs=str(logs))
        )
        (logs / "中文 报告.md").write_text("忠实的证据。", encoding="utf-8")
        (trial / "config.json").write_text(
            json.dumps(
                {"trial_name": "trial", "task": {"path": str(grader.parent.parent)}}
            )
        )
        (trial / "result.json").write_text(
            json.dumps({"trial_name": "trial", "finished_at": "2026-01-01T00:00:00Z"})
        )
        settings = JudgeSettings(True, provider["url"], "fixture")
        asyncio.run(run_verifier(grader, runtime=context, judge_settings=settings))
        config = {
            "harbor": {"mounts": [{"id": "test", "path": "jobs"}]},
            "judge": {
                "default_profile": "fixture",
                "profiles": {
                    "fixture": {"base_url": provider["url"], "model": "fixture"}
                },
            },
        }
        (tmp_path / "peval.toml").write_text(tomlkit.dumps(config), encoding="utf-8")
        yield JudgeService(tmp_path), provider, trial, grader, context


def test_prompt_uses_retained_id_without_task_profile_or_credentials(experiment):
    service, provider, trial, grader, _ = experiment
    path = trial / "verifier/judge/rubric-0001.json"
    path.rename(path.with_name("rubric-0032.json"))
    grader.unlink()
    (service.root / "peval.toml").write_text(
        '[harbor]\n[[harbor.mounts]]\nid="test"\npath="jobs"\n'
    )
    before = len(provider["requests"])
    prompt = service.prompt("fidelity", source_ref="harbor/test/job/trial")
    assert prompt["messages"] == provider["requests"][0]["messages"]
    assert prompt["status"] == "recorded" and len(provider["requests"]) == before
    assert service.prompt("unknown", path=str(trial))["status"] == "unavailable"
    assert prompt["settings"]["model"] == "fixture"
    assert not (trial / "verifier/judge/input.json").exists()


def snapshot(root):
    return {
        str(path.relative_to(root)): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


def test_preview_and_run_are_stateless_and_write_nothing(experiment, monkeypatch):
    service, provider, trial, grader, _ = experiment
    # Historical files are inert, even if malformed.
    history = service.root / "judge-runs/old"
    history.mkdir(parents=True)
    (history / "run.json").write_text("not JSON")
    (grader.parent / "test_outputs.py").write_text(
        "raise AssertionError('must not run')"
    )
    before = snapshot(service.root)
    draft = yaml.safe_load(YAML)
    draft["llm_judge"]["rubrics"][0]["scope_limits"] = [
        "Only evaluate the retained text."
    ]
    args = dict(
        path=str(trial), rubric_ids=["fidelity"], judge_config=yaml.safe_dump(draft)
    )
    count = len(provider["requests"])

    def forbidden(*args, **kwargs):
        pytest.fail("trial execution attempted a diagnostic or temporary write")

    monkeypatch.setattr("psycheval.harbor.verifier._judge._write_diagnostic", forbidden)
    for name in ("mkdtemp", "mkstemp", "TemporaryDirectory"):
        monkeypatch.setattr("tempfile." + name, forbidden)
    preview = service.preview(**args)
    assert len(provider["requests"]) == count
    assert "input" not in preview and "preparation_id" not in preview
    assert "api_key" not in preview["settings"]
    assert "runs" not in service.inspect(path=str(trial))
    # A fresh service can execute the preview: there is no cached preparation.
    result = asyncio.run(
        JudgeService(service.root).run(
            **args, expected_fingerprint=preview["fingerprint"]
        )
    )
    assert result["state"] == "complete"
    assert len(provider["requests"]) == count + 1
    assert (
        result["diagnostics"]["rubric-0001.json"]["messages"]
        == preview["messages"]["fidelity"]
    )
    assert provider["requests"][-1]["messages"] == preview["messages"]["fidelity"]
    assert snapshot(service.root) == before


def test_selection_ignores_unused_oversized_evidence(experiment):
    _, provider, trial, _, context = experiment
    value = yaml.safe_load(YAML)
    value["artifacts"].append(
        {"id": "unused", "path": "huge.txt", "required": True, "type": "text"}
    )
    value["llm_judge"]["rubrics"].append(
        {**value["llm_judge"]["rubrics"][0], "id": "other", "artifact_refs": ["unused"]}
    )
    (trial / "verifier/huge.txt").write_text("x" * 2048)
    prepared = prepare_judge(
        parse_judge_config(yaml.safe_dump(value)),
        evidence_root=trial / "verifier",
        context=context.verifier,
        settings=JudgeSettings(
            True, provider["url"], "fixture", max_evidence_bytes=100
        ),
        rubric_ids=("fidelity",),
    )
    assert list(prepared.to_dict()["evidence"]) == ["report"]
    with pytest.raises(ValueError, match="unknown"):
        prepare_judge(
            parse_judge_config(YAML),
            evidence_root=trial / "missing",
            settings=JudgeSettings(),
            rubric_ids=("unknown",),
        )
    result = asyncio.run(run_judge(prepared))
    assert result["status"] == "complete"


@pytest.mark.parametrize("change", ["evidence", "profile", "draft"])
def test_fingerprint_conflict_prevents_model_call(experiment, change):
    service, provider, trial, grader, _ = experiment
    args = dict(path=str(trial), all_rubrics=True)
    original = service.preview(**args)
    assert original["messages"]["fidelity"] == provider["requests"][0]["messages"]
    grader.unlink()  # Retained score owns context; the Task is unnecessary.
    if change == "evidence":
        (trial / "verifier/中文 报告.md").write_text(
            "Updated retained evidence.", encoding="utf-8"
        )
    elif change == "profile":
        path = service.root / "peval.toml"
        config = tomlkit.parse(path.read_text(encoding="utf-8"))
        config["judge"]["profiles"]["fixture"]["model"] = "revised"
        path.write_text(tomlkit.dumps(config), encoding="utf-8")
    else:
        args["instruction_text"] = "Revised instruction"
    before = len(provider["requests"])
    with pytest.raises(PreviewConflict, match="preview again"):
        asyncio.run(service.run(**args, expected_fingerprint=original["fingerprint"]))
    assert len(provider["requests"]) == before
    updated = service.preview(**args)
    result = asyncio.run(
        service.run(**args, expected_fingerprint=updated["fingerprint"])
    )
    assert result["state"] == "complete"
    assert provider["requests"][-1]["messages"] == updated["messages"]["fidelity"]


def test_retained_score_context_excludes_credentials_and_keeps_merge_weights(
    experiment,
):
    service, provider, trial, grader, context = experiment
    secret = "fixture-secret-must-not-be-retained"
    context = replace(
        context, verifier=replace(context.verifier, instruction=f"Context {secret}")
    )
    config = yaml.safe_load(YAML)
    config["score_merge"] = {
        "method": "weighted_sum",
        "rule_weight": 0.6,
        "llm_weight": 0.4,
    }
    (grader.parent / "judge.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    asyncio.run(
        run_verifier(
            grader,
            runtime=context,
            judge_settings=JudgeSettings(
                True, provider["url"], "fixture", api_key=secret
            ),
        )
    )
    score_text = (trial / "verifier/score.json").read_text(encoding="utf-8")
    assert secret not in score_text
    inspected = service.inspect(path=str(trial))
    assert inspected["context"]["instruction"] == "Context [REDACTED]"
    assert "api_key" not in inspected["settings"]
    assert inspected["config"]["score_merge"] == config["score_merge"]
    assert not (trial / "verifier/judge/input.json").exists()


def test_historical_context_requires_explicit_input(experiment):
    service, _, trial, _, _ = experiment
    score_path = trial / "verifier/score.json"
    score = json.loads(score_path.read_text(encoding="utf-8"))
    for group in score["judges"]:
        group["metadata"].pop("context", None)
    score_path.write_text(json.dumps(score), encoding="utf-8")
    assert service.inspect(path=str(trial))["missing"] == ["instruction"]
    with pytest.raises(ValueError, match="instruction missing"):
        service.preview(path=str(trial), all_rubrics=True)
    preview = service.preview(
        path=str(trial), all_rubrics=True, instruction_text="Explicit context"
    )
    assert "Explicit context" in preview["messages"]["fidelity"][0]["content"]


def test_credential_resolution_is_deferred_and_evidence_limits_apply(
    experiment, monkeypatch
):
    service, provider, trial, _, _ = experiment
    document = tomlkit.parse((service.root / "peval.toml").read_text(encoding="utf-8"))
    document["judge"]["profiles"]["fixture"]["api_key"] = "${TEST_JUDGE_MISSING_KEY}"
    (service.root / "peval.toml").write_text(tomlkit.dumps(document), encoding="utf-8")
    monkeypatch.delenv("TEST_JUDGE_MISSING_KEY", raising=False)
    before = len(provider["requests"])
    preview = service.preview(path=str(trial), all_rubrics=True)
    with pytest.raises(ValueError, match="environment variable"):
        asyncio.run(service.run(path=str(trial), all_rubrics=True))
    assert len(provider["requests"]) == before
    assert preview["fingerprint"]
    document["judge"]["profiles"]["fixture"]["max_evidence_bytes"] = 1
    (service.root / "peval.toml").write_text(tomlkit.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="(?i)max_evidence_bytes"):
        service.preview(path=str(trial), all_rubrics=True)


@pytest.mark.parametrize("failure", ["http", "protocol", "timeout"])
def test_partial_failures_return_completed_and_unassessed(experiment, failure):
    service, provider, trial, _, _ = experiment
    draft = yaml.safe_load(YAML)
    draft["llm_judge"]["rubrics"].append(
        {**draft["llm_judge"]["rubrics"][0], "id": "other"}
    )
    provider["behavior"]["other"] = {
        "http": {"status": 401},
        "protocol": {"raw": "invalid"},
        "timeout": {"delay": 1},
    }[failure]
    if failure == "timeout":
        path = service.root / "peval.toml"
        config = tomlkit.parse(path.read_text(encoding="utf-8"))
        config["judge"]["profiles"]["fixture"]["total_timeout"] = 0.4
        path.write_text(tomlkit.dumps(config), encoding="utf-8")
    before = snapshot(service.root)
    result = asyncio.run(
        service.run(
            path=str(trial), all_rubrics=True, judge_config=yaml.safe_dump(draft)
        )
    )
    assert result["state"] == "incomplete"
    assert [item["id"] for item in result["checks"]] == ["fidelity"]
    assert set(result["errors"]) == {"other"}
    assert snapshot(service.root) == before


def test_cancellation_releases_model_tasks_and_discards_partial_results(
    experiment, monkeypatch
):
    from psycheval.harbor.verifier import _judge

    service, provider, trial, _, _ = experiment
    provider["behavior"]["fidelity"] = {"delay": 1}
    original = _judge._request
    active = set()

    async def tracked(*args):
        active.add(asyncio.current_task())
        try:
            return await original(*args)
        finally:
            active.remove(asyncio.current_task())

    monkeypatch.setattr(_judge, "_request", tracked)
    before = snapshot(service.root)

    async def scenario():
        run = asyncio.create_task(service.run(path=str(trial), all_rubrics=True))
        async with asyncio.timeout(3):
            while not active:
                await asyncio.sleep(0.01)
        run.cancel()
        with pytest.raises(asyncio.CancelledError):
            await run
        assert not active
        assert not [
            task for task in asyncio.all_tasks() if task is not asyncio.current_task()
        ]

    asyncio.run(scenario())
    assert snapshot(service.root) == before


def test_disabled_judge_has_no_request_and_cli_exports_do_not_overwrite(
    experiment, capsys
):
    service, provider, trial, grader, context = experiment
    count = len(provider["requests"])
    asyncio.run(run_verifier(grader, runtime=context, judge_settings=JudgeSettings()))
    assert service.prompt("fidelity", path=str(trial))["status"] == "not_requested"
    assert service.prompt("unknown", path=str(trial))["status"] == "unavailable"
    assert service.preview(path=str(trial), all_rubrics=True)["messages"]
    assert not (trial / "verifier/judge/input.json").exists()
    assert len(provider["requests"]) == count
    original = grader.read_bytes()
    assert (
        main(
            [
                "judge",
                "inspect",
                "-r",
                str(service.root),
                "-p",
                str(trial),
                "--export-config",
                str(grader),
            ]
        )
        == 2
    )
    assert grader.read_bytes() == original
    assert "Error" in capsys.readouterr().err


def test_cli_prompt_preview_and_run(experiment, capsys):
    service, provider, trial, _, _ = experiment
    base = ["-r", str(service.root), "-p", str(trial)]
    before = len(provider["requests"])
    assert main(["judge", "inspect", *base]) == 0
    summary = capsys.readouterr().out
    assert "Source:" in summary and "fidelity: pass" in summary
    assert main(["judge", "inspect", *base, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["supported"] is True
    assert main(["judge", "prompt", *base, "--rubric", "fidelity", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["prompts"][0]["status"] == "recorded"
    assert main(["judge", "preview", *base, "--all", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "unsent"
    assert len(provider["requests"]) == before
    assert main(["judge", "run", *base, "--all", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "complete"


@pytest.mark.parametrize("password", [None, "test-password"])
def test_http_prompt_read_and_execution_permissions(experiment, password):
    service, provider, _, _, _ = experiment
    store = open_workspace_state(str(service.root))
    runtime = ServeRuntime(store, load_config(workspace_root=service.root))
    server = LocalHTTPServer(
        ("127.0.0.1", 0), make_handler(runtime, access=ServeAccess(password))
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        runtime.wait_until_ready(10)
        rows = runtime.catalog.query(
            CatalogQuery(state="all", include_unreadable=True)
        ).items
        key = rows[0].to_dict()["source_key"]
        url = f"http://127.0.0.1:{server.server_port}"
        with httpx.Client(base_url=url) as client:
            response = client.get(f"/api/judge/{key}/prompt/fidelity")
            assert response.status_code == 200, response.text
            assert response.json()["status"] == "recorded"
            response = client.post(
                f"/api/judge/{key}/preview", json={"all_rubrics": True}
            )
            assert response.status_code == (403 if password else 200), response.text
            if password is None:
                configuration = client.get("/api/config")
                config = configuration.json()["judge"]
                config["profiles"]["fixture"]["title"] = "Reviewed profile"
                saved = client.patch(
                    "/api/config",
                    json={"judge": config},
                    headers={"If-Match": configuration.headers["etag"]},
                )
                assert saved.status_code == 200, saved.text
                assert (
                    saved.json()["judge"]["profiles"]["fixture"]["title"]
                    == "Reviewed profile"
                )
                config["profiles"]["fixture"]["api_key"] = "literal-credential"
                rejected = client.patch(
                    "/api/config",
                    json={"judge": config},
                    headers={"If-Match": saved.headers["etag"]},
                )
                assert rejected.status_code == 422
                assert "literal-credential" not in rejected.text
                response = client.post(
                    f"/api/judge/{key}/run",
                    json={"all_rubrics": True, "expected_fingerprint": "0" * 64},
                )
                assert response.status_code == 409, response.text
                response = client.post(
                    f"/api/judge/{key}/run", json={"all_rubrics": True}
                )
                assert response.status_code == 200, response.text
                assert response.json()["state"] == "complete", response.text
            else:
                assert (
                    client.post(
                        f"/api/judge/{key}/run", json={"all_rubrics": True}
                    ).status_code
                    == 403
                )
            for old in ("prepare", "runs"):
                assert (
                    client.post(f"/api/judge/{key}/{old}", json={}).status_code == 404
                )
    finally:
        server.shutdown()
        thread.join(5)
        server.server_close()
        runtime.close()


def test_cli_text_exit_codes_and_removed_commands(experiment, capsys, monkeypatch):
    service, provider, trial, _, _ = experiment
    base = ["-r", str(service.root), "-p", str(trial)]
    before = snapshot(service.root)
    assert main(["judge", "preview", *base, "--all"]) == 0
    assert "Unsent preview" in capsys.readouterr().out
    provider["behavior"]["fidelity"] = {"passed": False}
    assert main(["judge", "run", *base, "--all"]) == 0
    assert "pass -> fail" in capsys.readouterr().out
    provider["behavior"]["fidelity"] = {"status": 401}
    assert main(["judge", "run", *base, "--all", "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["state"] == "incomplete"
    for args in (
        ["list"],
        ["show", "id"],
        ["prompt", *base, "--rubric", "fidelity", "--run-id", "id"],
    ):
        assert main(["judge", *args]) == 2
        capsys.readouterr()

    async def interrupt(self, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(JudgeService, "run", interrupt)
    assert main(["judge", "run", *base, "--all", "--json"]) == 1
    assert json.loads(capsys.readouterr().out) == {
        "state": "cancelled",
        "checks": [],
        "errors": {},
    }
    assert snapshot(service.root) == before


def test_http_disconnect_cancels_and_releases_execution(experiment, monkeypatch):
    from psycheval.harbor.verifier import _judge

    service, provider, _, _, _ = experiment
    provider["behavior"]["fidelity"] = {"delay": 2}
    started, released = threading.Event(), threading.Event()
    request = _judge._request
    active = set()

    async def tracked(*args):
        active.add(asyncio.current_task())
        started.set()
        try:
            return await request(*args)
        finally:
            active.remove(asyncio.current_task())

    monkeypatch.setattr(_judge, "_request", tracked)
    execute = JudgeService.run

    async def observed(self, **kwargs):
        try:
            return await execute(self, **kwargs)
        finally:
            released.set()

    monkeypatch.setattr(JudgeService, "run", observed)
    runtime = ServeRuntime(
        open_workspace_state(str(service.root)),
        load_config(workspace_root=service.root),
    )
    server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        runtime.wait_until_ready(10)
        key = (
            runtime.catalog.query(CatalogQuery(state="all", include_unreadable=True))
            .items[0]
            .to_dict()["source_key"]
        )

        async def scenario():
            async with httpx.AsyncClient(timeout=None) as client:
                pending = asyncio.create_task(
                    client.post(
                        f"http://127.0.0.1:{server.server_port}/api/judge/{key}/run",
                        json={"all_rubrics": True},
                    )
                )
                assert await asyncio.to_thread(started.wait, 3)
                pending.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await pending
                assert await asyncio.to_thread(released.wait, 3)
                assert not active

        asyncio.run(scenario())
        assert not (service.root / "judge-runs").exists()
    finally:
        server.shutdown()
        thread.join(5)
        server.server_close()
        runtime.close()


@pytest.mark.parametrize("json_output", [False, True])
def test_cli_interrupt_releases_execution(experiment, json_output):
    service, _, trial, _, _ = experiment
    before = snapshot(service.root)
    # Exercise the SIGINT handler used by asyncio.Runner without delivering a
    # console-control event to the parent pytest process on Windows.
    script = """
import _thread, asyncio, sys
from psycheval.cli import main
from psycheval.harbor.verifier import _judge
released = False
async def pending(*args):
    global released
    asyncio.get_running_loop().call_later(0.05, _thread.interrupt_main)
    try:
        await asyncio.sleep(60)
    finally:
        released = True
_judge._request = pending
code = main(sys.argv[1:])
assert released, 'CLI returned before the model task settled'
raise SystemExit(code)
"""
    process = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-c",
            script,
            "judge",
            "run",
            "-r",
            str(service.root),
            "-p",
            str(trial),
            "--all",
            *(["--json"] if json_output else []),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=10,
    )
    assert process.returncode == 1, process.stderr
    if json_output:
        assert json.loads(process.stdout)["state"] == "cancelled"
    else:
        assert process.stdout.strip() == "Cancelled"
    assert snapshot(service.root) == before


@pytest.mark.parametrize("action", ["preview", "run"])
def test_request_uses_one_configuration_and_source_snapshot(
    experiment, monkeypatch, action
):
    import psycheval.judge_runs.service as module

    service, _, trial, _, _ = experiment
    config_reads, source_reads = [], []
    load, source = module.load_config, service.source

    def load_once(**kwargs):
        config_reads.append(kwargs)
        return load(**kwargs)

    def resolve_once(**kwargs):
        source_reads.append(kwargs)
        return source(**kwargs)

    monkeypatch.setattr(module, "load_config", load_once)
    monkeypatch.setattr(service, "source", resolve_once)
    args = dict(path=str(trial), all_rubrics=True)
    if action == "run":
        asyncio.run(service.run(**args))
    else:
        service.preview(**args)
    assert len(config_reads) == 1 and len(source_reads) == 1


def test_service_response_omits_raw_model_bodies(experiment):
    service, _, trial, _, _ = experiment
    result = asyncio.run(service.run(path=str(trial), all_rubrics=True))
    assert len(result["diagnostics"]) == 1
    diagnostic = next(iter(result["diagnostics"].values()))
    assert set(diagnostic) == {"id", "messages", "result"}
    assert diagnostic["messages"] and diagnostic["result"]["passed"]


@pytest.mark.parametrize(
    "action,options",
    [
        ("prompt", ["--task", "unused"]),
        ("run", ["--export-config", "unused"]),
        ("inspect", ["--rubric", "fidelity"]),
        ("inspect", ["--all"]),
        ("preview", ["--export-config", "unused"]),
        ("prompt", ["--profile", "fixture"]),
    ],
)
def test_cli_rejects_options_outside_subcommand(experiment, capsys, action, options):
    service, provider, trial, _, _ = experiment
    count = len(provider["requests"])
    args = ["judge", action, "-r", str(service.root), "-p", str(trial)]
    if action == "prompt":
        args += ["--rubric", "fidelity"]
    if action in {"preview", "run"}:
        args += ["--all"]
    assert main([*args, *options]) == 2
    assert "not supported" in capsys.readouterr().err
    assert len(provider["requests"]) == count


@pytest.mark.parametrize("trial_finished", [True, False])
def test_catalog_step_rows_support_judge_without_step_result_files(
    experiment, trial_finished
):
    from tests.peval.test_harbor_evidence import write_evidence_trial

    service, _, trial, grader, _ = experiment
    end = "2026-01-01T00:00:00Z"
    write_evidence_trial(
        trial,
        config_task={"path": str(grader.parent.parent)},
        result={
            "trial_name": "trial",
            "finished_at": end if trial_finished else None,
            "step_results": [
                {"step_name": "first", "verifier": {"finished_at": end}},
                {"step_name": "second", "verifier": {"finished_at": None}},
            ],
        },
    )
    (trial / "agent/trajectory.json").unlink()
    for name in ("first", "second"):
        step = trial / "steps" / name
        (step / "agent").mkdir(parents=True)
        # The retained step source needs an ATIF file; use the shared fixture data.
        from tests.peval.test_harbor_trials import atif_trajectory

        (step / "agent/trajectory.json").write_text(
            json.dumps(atif_trajectory(name)), encoding="utf8"
        )
        shutil.copytree(trial / "verifier", step / "verifier")
        assert not (step / "result.json").exists()
    runtime = ServeRuntime(
        open_workspace_state(str(service.root)),
        load_config(workspace_root=service.root),
    )
    server = LocalHTTPServer(("127.0.0.1", 0), make_handler(runtime))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        runtime.wait_until_ready(10)
        rows = [
            row.to_dict()
            for row in runtime.catalog.query(
                CatalogQuery(state="all", include_unreadable=True)
            ).items
        ]
        assert len(rows) == 2
        first = next(row for row in rows if row["step_name"] == "first")
        assert first["source_ref"].endswith("/steps/first")
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}") as client:
            response = client.post(
                f"/api/judge/{first['source_key']}/preview", json={"all_rubrics": True}
            )
            assert response.status_code == 200, response.text
            response = client.post(
                f"/api/judge/{first['source_key']}/run", json={"all_rubrics": True}
            )
            assert response.status_code == 200, response.text
            assert response.json()["step"] == "first"
            assert response.json()["state"] == "complete"
        if not trial_finished:
            with pytest.raises(ValueError, match="finished Trial or step"):
                service.preview(path=str(trial), step="second", all_rubrics=True)
    finally:
        server.shutdown()
        thread.join(5)
        server.server_close()
        runtime.close()
