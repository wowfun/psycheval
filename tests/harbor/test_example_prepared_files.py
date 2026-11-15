"""Prepared inputs, strict weighted output and the real native retention seam."""

import asyncio
import json
import logging
import runpy
import shutil
from html import escape
from pathlib import Path

import pytest
from harbor.models.trajectories import Trajectory
from harbor.trial.artifact_handler import ArtifactHandler, artifact_host_path

from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
    load_effective_runtime_config,
)
from psycheval.harbor.tasks import load_harbor_task
from psycheval.harbor.verifier import (
    JudgeSettings,
    build_scoring_plan,
    load_judge_config,
    run_verifier,
)
from tests.fixtures.judge_server import judge_server
from tests.harbor.environment_support import make_environment

TASK = Path(__file__).resolve().parents[2] / "examples/tasks/native-prepared-files"
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
GOOD = b'{"total":6,"as_of":"2026-09-17"}'
ANSWER = (
    "I added the input.json values 1 + 2 + 3 = 6 and copied its as_of date unchanged."
)


def context(tmp_path):
    roots = {
        name: tmp_path / name
        for name in (
            "workdir",
            "inputs",
            "preparation_state",
            "agent_logs",
            "verifier_logs",
        )
    }
    roots["artifacts"] = tmp_path / "artifacts/logs/artifacts"
    for path in roots.values():
        path.mkdir(parents=True)
    runpy.run_path(str(TASK / "environment/prepare.py"))["prepare"](
        str(roots["workdir"]), str(roots["preparation_state"])
    )
    shutil.copyfile(roots["workdir"] / "input.json", roots["inputs"] / "input.json")
    roots["tests"] = TASK / "tests"
    (roots["artifacts"].parent.parent / "output.json").write_bytes(GOOD)
    return {"paths": {key: str(value) for key, value in roots.items()}}


def score(value, grader=GRADER):
    checks = grader["grade"](value)["checks"]
    assert [check["id"] for check in checks] == ["total", "date"]
    return sum(weight for weight, check in zip((3, 1), checks) if check["passed"]) / 4


@pytest.mark.parametrize(
    "output,expected",
    [
        (GOOD, 1),
        (b'\xef\xbb\xbf{"total":6.0,"as_of":"2026-09-17"}', 1),
        (b'{"total":6e0,"as_of":"2026-09-17","note":"done"}', 1),
        (b'{"total":6,"as_of":"wrong"}', 0.75),
        (b'{"total":6}', 0.75),
        (b'{"as_of":"2026-09-17"}', 0.25),
        *[
            (f'{{"total":{total},"as_of":"2026-09-17"}}'.encode(), 0.25)
            for total in (
                "true",
                '"6"',
                "null",
                "{}",
                "[]",
                "5",
                "6.0000000000000000001",
                "1e999",
            )
        ],
        (b'{"total":6,"as_of":20260917}', 0.75),
        (None, 0),
        (b"\xff", 0),
        (b"{", 0),
        (b"[]", 0),
        (b"null", 0),
        (GOOD + b"{}", 0),
        (b'{"total":0,"total":6,"as_of":"2026-09-17"}', 0),
        (b'{"total":6,"as_of":"2026-09-17","extra":{"a":1,"a":2}}', 0),
        *[
            (b'{"total":6,"as_of":"2026-09-17","extra":' + token + b"}", 0)
            for token in (b"NaN", b"Infinity", b"-Infinity")
        ],
        pytest.param(b" " * (64 * 1024), 0, id="oversize"),
        (b'{"total":1e9999999999999999999999,"as_of":"2026-09-17"}', 0),
    ],
)
def test_output_is_strict_json_but_preserves_independent_three_to_one_credit(
    tmp_path, output, expected
):
    value = context(tmp_path)
    path = Path(value["paths"]["artifacts"]).parent.parent / "output.json"
    if output is None:
        path.unlink()
    else:
        path.write_bytes(output)
    assert score(value) == expected
    if output is not None and len(output) < 64 * 1024:
        assert (
            tmp_path / "verifier_logs/raw_artifacts/output_json.json"
        ).read_bytes() == output


@pytest.mark.parametrize(
    "field",
    [
        "workdir",
        "tests",
        "inputs",
        "preparation_state",
        "artifacts",
        "agent_logs",
        "verifier_logs",
    ],
)
def test_missing_runtime_path_is_a_verifier_error(tmp_path, field):
    value = context(tmp_path)
    value["paths"][field] = None
    with pytest.raises(ValueError, match="RuntimePaths"):
        GRADER["grade"](value)


@pytest.mark.parametrize(
    "kind,content",
    [
        ("gt", b'{"total":true,"as_of":"2026-09-17"}'),
        ("gt", b'{"total":6.0,"as_of":"2026-09-17"}'),
        ("gt", b'{"total":5,"as_of":"2026-09-17"}'),
        ("gt", b'{"total":6,"as_of":"2026-09-18"}'),
        ("gt", b'{"total":6,"total":6,"as_of":"2026-09-17"}'),
        ("input", b'{"values":[true,2,3],"as_of":"2026-09-17"}'),
        ("input", b'{"values":[1.0,2,3],"as_of":"2026-09-17"}'),
        ("input", b'{"values":[],"as_of":"2026-09-17"}'),
        ("input", b'{"values":[1,2,3],"as_of":"2026-09-18"}'),
        ("input", b'{"values":[1,2,NaN],"as_of":"2026-09-17"}'),
        ("state", b'{"as_of":"2026-09-18"}'),
        ("state", b'{"as_of":"2026-09-31"}'),
        ("state", b'{"as_of":"20260917"}'),
        ("state", b'{"as_of":true}'),
        ("state", b"{}"),
        ("state", b"{"),
    ],
)
def test_broken_trusted_material_is_not_an_agent_failure(tmp_path, kind, content):
    value = context(tmp_path)
    task = tmp_path / "task"
    shutil.copytree(TASK, task)
    grader = runpy.run_path(str(task / "tests/test_outputs.py"))
    paths = value["paths"]
    path = {
        "gt": task / "tests/gt/expected.json",
        "input": Path(paths["inputs"]) / "input.json",
        "state": Path(paths["preparation_state"]) / "reference.json",
    }[kind]
    path.write_bytes(content)
    with pytest.raises(ValueError):
        grader["grade"](value)
    assert not (tmp_path / "verifier_logs/artifact_manifest.json").exists()


@pytest.mark.parametrize(
    "field,name", [("inputs", "input.json"), ("preparation_state", "reference.json")]
)
def test_missing_trusted_file_is_a_verifier_error(tmp_path, field, name):
    value = context(tmp_path)
    (Path(value["paths"][field]) / name).unlink()
    with pytest.raises(FileNotFoundError):
        GRADER["grade"](value)


def test_snapshot_reads_ignore_later_workspace_and_source_changes(
    tmp_path, monkeypatch
):
    value = context(tmp_path)
    paths = value["paths"]
    (Path(paths["workdir"]) / "input.json").write_text(
        '{"values":[900],"as_of":"wrong"}'
    )
    capture = GRADER["EvidenceWriter"].capture

    def changing_capture(writer, identity, source, **kwargs):
        snapshot = capture(writer, identity, source, **kwargs)
        if identity in {"initial_input", "output_json"}:
            snapshot.path.write_text("changed after the snapshot", encoding="utf-8")
        return snapshot

    monkeypatch.setattr(GRADER["EvidenceWriter"], "capture", changing_capture)
    assert score(value) == 1
    assert json.loads(
        (tmp_path / "verifier_logs/raw_artifacts/initial_input.json").read_bytes()
    )["values"] == [1, 2, 3]
    assert (
        tmp_path / "verifier_logs/raw_artifacts/output_json.json"
    ).read_bytes() == GOOD


def test_missing_retained_output_does_not_fall_back_to_workspace_or_convention(
    tmp_path,
):
    value = context(tmp_path)
    paths = value["paths"]
    (Path(paths["artifacts"]).parent.parent / "output.json").unlink()
    for name in ("workdir", "artifacts"):
        (Path(paths[name]) / "output.json").write_bytes(GOOD)
    assert score(value) == 0


@pytest.mark.parametrize("kind", ["gt", "input", "state", "runtime"])
def test_trusted_failures_remain_errors_through_public_verifier(tmp_path, kind):
    value = context(tmp_path)
    task = tmp_path / "task"
    shutil.copytree(TASK, task)
    paths = value["paths"]
    paths["tests"] = str(task / "tests")
    if kind == "runtime":
        paths["inputs"] = None
    else:
        path = {
            "gt": task / "tests/gt/expected.json",
            "input": Path(paths["inputs"]) / "input.json",
            "state": Path(paths["preparation_state"]) / "reference.json",
        }[kind]
        path.write_bytes(b'{"invalid": true}')
    runtime = EffectiveRuntimeConfig(paths=RuntimePaths(**paths))
    with pytest.raises(RuntimeError, match="custom verifier exited"):
        asyncio.run(
            run_verifier(
                task / "tests/grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(enabled=False),
            )
        )


def test_undeclared_artifact_mapping_is_a_configuration_error(tmp_path):
    value = context(tmp_path)
    value["paths"]["artifacts"] = str(tmp_path / "artifacts")
    with pytest.raises(ValueError, match="Native Host"):
        GRADER["grade"](value)


def test_output_publication_failure_remains_a_verifier_error(tmp_path, monkeypatch):
    from psycheval.harbor.evidence import EvidenceLimitError

    value = context(tmp_path)
    capture = GRADER["EvidenceWriter"].capture

    def failing_capture(writer, identity, source, **kwargs):
        if identity == "output_json":
            raise EvidenceLimitError("publication budget exhausted")
        return capture(writer, identity, source, **kwargs)

    monkeypatch.setattr(GRADER["EvidenceWriter"], "capture", failing_capture)
    with pytest.raises(EvidenceLimitError, match="publication"):
        GRADER["grade"](value)


def final_trajectory(answer=ANSWER):
    return Trajectory.model_validate(
        {
            "schema_version": "ATIF-v1.7",
            "trajectory_id": "prepared-files-fixture",
            "agent": {"name": "fixture", "version": "1"},
            "steps": [
                {
                    "step_id": 1,
                    "source": "user",
                    "message": "Transform the prepared input.",
                },
                {"step_id": 2, "source": "agent", "message": "HISTORICAL_SENTINEL"},
                {"step_id": 3, "source": "agent", "message": answer},
            ],
        }
    )


@pytest.mark.parametrize(
    "output,answer,judge_pass,expected,calls",
    [
        (GOOD, ANSWER, True, 1, 1),
        (GOOD, "Done.", False, 0.9, 1),
        (GOOD, None, True, 0.9, 0),
        (b'{"total":6,"as_of":"wrong"}', ANSWER, True, 0.675, 0),
        (None, ANSWER, True, 0, 0),
    ],
)
def test_public_verifier_merges_only_verified_output_explanations(
    tmp_path, output, answer, judge_pass, expected, calls
):
    value = context(tmp_path)
    paths = value["paths"]
    path = Path(paths["artifacts"]).parent.parent / "output.json"
    if output is None:
        path.unlink()
    else:
        path.write_bytes(output)
    if answer is not None:
        (Path(paths["agent_logs"]) / "trajectory.json").write_text(
            final_trajectory(answer).model_dump_json(), encoding="utf-8"
        )
    runtime = EffectiveRuntimeConfig(
        paths=RuntimePaths(**paths),
        verifier=VerifierInvocation(
            (TASK / "instruction.md").read_text(encoding="utf-8")
        ),
    )
    with judge_server() as server:
        server["behavior"] = {"supported_explanation": {"passed": judge_pass}}
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
    assert result["reward"] == pytest.approx(expected)
    rules = [item for item in result["verdicts"] if item["judge_type"] == "rule_script"]
    assert rules and len(rules) == 2
    assert len(server["requests"]) == calls
    assert result["metadata"]["score_merge"]["applied"]
    if calls:
        prompt = server["requests"][0]["messages"][-1]["content"]
        for identity in (
            "prepared_input",
            "output_text",
            "validation_facts",
            "verified_output",
            "final_answer",
        ):
            text = (
                Path(paths["verifier_logs"]) / f"artifact_text/{identity}.md"
            ).read_text(encoding="utf-8")
            assert escape(text, quote=False) in prompt
        assert "HISTORICAL_SENTINEL" not in prompt


def test_real_native_preparation_and_artifact_collection_reach_judge(tmp_path):
    host = make_environment(
        tmp_path / "host", environment_kwargs={"workdir_root": tmp_path / "workspaces"}
    )
    task_root = host.environment_dir.parent
    shutil.copytree(TASK, task_root, dirs_exist_ok=True)
    loaded = load_harbor_task(task_root, read_bytes=Path.read_bytes)

    async def run():
        await host.start(False)
        try:
            runtime = load_effective_runtime_config(
                environ=host.runtime_config_env(
                    verifier=VerifierInvocation(
                        (TASK / "instruction.md").read_text(encoding="utf-8")
                    )
                )
            )
            await host.upload_dir(task_root / "tests", "/tests")
            (host.work_dir / "output.json").write_bytes(GOOD)
            (Path(runtime.paths.agent_logs) / "trajectory.json").write_text(
                final_trajectory().model_dump_json(), encoding="utf-8"
            )
            manifest = await ArtifactHandler(
                artifacts=loaded.config.artifacts, logger=logging.getLogger(__name__)
            ).download_artifacts(
                host,
                host.trial_paths.artifacts_dir,
                source_artifacts_dir="/logs/artifacts",
            )
            assert any(
                item.destination == "artifacts/output.json" and item.status == "ok"
                for item in manifest.entries
            )
            assert (
                artifact_host_path(
                    host.trial_paths.artifacts_dir, loaded.config.artifacts[0]
                )
                == Path(runtime.paths.artifacts).parent.parent / "output.json"
            )
            (host.work_dir / "output.json").unlink()
            (host.work_dir / "input.json").write_text(
                '{"values":[900],"as_of":"wrong"}', encoding="utf-8"
            )
            with judge_server() as server:
                result = await run_verifier(
                    Path(runtime.paths.tests) / "grader.json",
                    runtime=runtime,
                    judge_settings=JudgeSettings(True, server["url"], "fixture"),
                )
            assert result["reward"] == 1
            assert len(server["requests"]) == 1
            prompt = server["requests"][0]["messages"][-1]["content"]
            assert "1, 2, 3" in prompt and ANSWER in prompt
            assert (
                Path(runtime.paths.verifier_logs) / "raw_artifacts/output_json.json"
            ).read_bytes() == GOOD
        finally:
            await host.stop(True)

    asyncio.run(run())


def test_example_contract_keeps_rule_weights_and_small_optional_explanation():
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    assert loaded.config.verifier.environment_mode == "shared"
    assert [(item.source, item.destination) for item in loaded.config.artifacts] == [
        ("output.json", "output.json")
    ]
    plan = build_scoring_plan(json.loads((TASK / "tests/grader.json").read_bytes()))
    assert [(item.id, item.weight) for item in plan.items] == [
        ("custom:total", 3),
        ("custom:date", 1),
    ]
    judge = load_judge_config(TASK / "tests/judge.yaml")
    assert (judge.rule_weight, judge.llm_weight) == (0.9, 0.1)
