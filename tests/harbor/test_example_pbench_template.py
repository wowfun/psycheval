"""Runnable local writing starter: grounded gates and actual Native collection."""

import asyncio
import json
import logging
import runpy
import sys
from dataclasses import replace
from html import escape
from pathlib import Path

import pytest
from harbor.models.trajectories import Trajectory
from harbor.models.trial.paths import TrialPaths
from harbor.trial.artifact_handler import ArtifactHandler

from psycheval.harbor.documents import MissingDocumentDependency, inspect_document
from psycheval.harbor.environment import HostEnvironment
from psycheval.harbor.evidence import SourceSnapshot
from psycheval.harbor.family import retain
from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
    load_effective_runtime_config,
)
from psycheval.harbor.tasks import load_harbor_task
from psycheval.harbor.verifier import JudgeSettings, build_scoring_plan, run_verifier
from tests.fixtures.judge_server import judge_server

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "examples/tasks/pbench-task-template"
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
SOURCE = (TASK / "environment/data/operations-note.md").read_text(encoding="utf-8")
GOOD = (
    "# Room change for session leaders\n\n"
    "The North studio will be closed on 17 June 2027 from 09:30 to 11:00 for ventilation servicing. "
    "Sessions will meet in the South studio. Please move your session kits there before 09:30. "
    "Reception and other rooms remain open; no sessions are cancelled.\n"
)


def report(text):
    content = text.encode("utf-8") if isinstance(text, str) else text
    return inspect_document(SourceSnapshot(Path("notice.md"), content), format="md")


def check(text):
    return GRADER["check_notice"](report(text), GRADER["reference"](SOURCE))


@pytest.mark.parametrize(
    "text",
    [
        GOOD,
        SOURCE,
        GOOD.replace("17 June 2027", "June 17th, 2027"),
        GOOD.replace("17 June 2027", "June 17, 2027")
        .replace("09:30", "9:30 a.m.")
        .replace("11:00", "11 a.m."),
        GOOD.replace("17 June 2027", "2027-06-17").replace(
            "will be closed", "is out of service"
        ),
        GOOD.replace("will be closed", "won't be available").replace("before", "by"),
        "# Studio notice\n\n- North studio unavailable: 17 Jun 2027, 09:30–11:00.\n- Sessions will be held in the South studio.\n- Leaders: bring session materials before 09:30. Reception remains open.\n",
        "# Session notice\n\n| Arrangement | Details |\n| --- | --- |\n| North studio closure | 17 June 2027, 09:30–11:00 |\n| Sessions | South studio |\n\nPlease move session kits to the South studio before 09:30. Other rooms and reception remain open.\n",
    ],
)
def test_clear_paraphrases_formats_and_source_wording_are_accepted(text):
    assert check(text)[0], check(text)[1]


BAD = [
    "",
    "Please enjoy the gardens.",
    GOOD.replace("17 June 2027", "18 June 2027"),
    GOOD.replace("17 June 2027", "17 June 2028"),
    GOOD.replace("17 June 2027", "17 June"),
    GOOD.replace("11:00", "11:30"),
    GOOD.replace("09:30 to 11:00", "11:00 to 09:30"),
    GOOD.replace("before 09:30", "before 10:00"),
    GOOD.replace(
        "The North studio will be closed", "The North studio will not be closed"
    ),
    GOOD.replace("The North studio", "The East studio"),
    GOOD.replace("South studio", "East studio"),
    GOOD.replace("Please move your session kits there before 09:30.", ""),
    GOOD + "\nSessions are cancelled.\n",
    GOOD + "\nReception is closed.\n",
    "North studio South studio 17 June 2027 09:30 11:00 sessions kits move before 09:30",
    "```text\n" + GOOD + "\n```",
    "<!--\n" + GOOD + "\n-->",
    GOOD.replace("kits there before", "kits to the North studio before"),
    GOOD.replace("kits there before 09:30", "kits there before 11:00")
    + "\nArrive before 09:30.\n",
    GOOD.replace(
        "Sessions will meet in the South studio",
        "Sessions will meet in the North studio",
    ).replace("kits there before", "kits to the South studio before"),
]


@pytest.mark.parametrize("text", BAD)
def test_missing_wrong_negated_or_hidden_key_facts_fail_objective_gate(text):
    assert not check(text)[0]


def trajectory(answer="The notice is ready in notice.md."):
    return Trajectory.model_validate(
        retain(
            {
                "schema_version": "ATIF-v1.7",
                "trajectory_id": "local-notice-fixture",
                "agent": {"name": "synthetic-local-fixture", "version": "1"},
                "steps": [
                    {"step_id": 1, "source": "user", "message": "Write the notice"},
                    {"step_id": 2, "source": "agent", "message": answer},
                ],
                "extra": {"tool_evidence": "complete"},
            }
        )
    )


def runtime(
    tmp_path, notice=GOOD, source=SOURCE, answer="The notice is ready in notice.md."
):
    roots = {key: tmp_path / key for key in ("workdir", "agent_logs", "verifier_logs")}
    roots["artifacts"] = tmp_path / "artifacts/logs/artifacts"
    roots["inputs"] = tmp_path / "input_evidence/inputs"
    for path in roots.values():
        path.mkdir(parents=True)
    (roots["inputs"] / "operations-note.md").write_text(source, encoding="utf-8")
    if notice is not None:
        content = notice.encode("utf-8") if isinstance(notice, str) else notice
        (roots["artifacts"].parent.parent / "notice.md").write_bytes(content)
    (roots["agent_logs"] / "trajectory.json").write_text(
        trajectory(answer).model_dump_json(), encoding="utf-8"
    )
    return roots, EffectiveRuntimeConfig(
        paths=RuntimePaths(
            tests=str(TASK / "tests"), **{key: str(path) for key, path in roots.items()}
        ),
        verifier=VerifierInvocation(
            (TASK / "instruction.md").read_text(encoding="utf-8")
        ),
    )


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        BAD[1],
        BAD[2],
        BAD[5],
        BAD[9],
        BAD[10],
        BAD[11],
        BAD[12],
        BAD[13],
        BAD[14],
        BAD[-2],
        BAD[-1],
        BAD[-3],
        b"\xff",
    ],
)
def test_even_a_passing_judge_cannot_bypass_missing_or_wrong_basic_facts(
    tmp_path, text
):
    roots, effective = runtime(tmp_path, notice=text)
    with judge_server() as server:
        server["behavior"] = {"usable_notice": {"passed": True}}
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=effective,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
    assert result["reward"] == 0
    assert server["requests"] == []
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    assert (
        next(item for item in manifest["artifacts"] if item["id"] == "verified_notice")[
            "extract_status"
        ]
        == "missing"
    )


@pytest.mark.parametrize(
    "text,passed,expected",
    [
        (GOOD, True, 1),
        (GOOD, False, 0.3),
        (
            GOOD + "\nA long unrelated story about a moon expedition follows.\n",
            False,
            0.3,
        ),
    ],
)
def test_semantic_quality_remains_material_and_judge_receives_exact_published_evidence(
    tmp_path, text, passed, expected
):
    roots, effective = runtime(tmp_path, notice=text)
    with judge_server() as server:
        server["behavior"] = {"usable_notice": {"passed": passed}}
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=effective,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
    assert result["reward"] == expected
    assert len(server["requests"]) == 1
    prompt = server["requests"][0]["messages"][-1]["content"]
    for identity in (
        "source_excerpt",
        "verified_notice",
        "final_answer",
        "execution_facts",
    ):
        published = (roots["verifier_logs"] / f"artifact_text/{identity}.md").read_text(
            encoding="utf-8"
        )
        assert escape(published, quote=False) in prompt
    assert "L3:" in prompt and "operations-note.md" in prompt
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )
    records = {item["id"]: item for item in manifest["artifacts"]}
    assert records["source_excerpt"]["source_artifact_id"] == "initial_note"
    assert records["verified_notice"]["source_artifact_id"] == "notice_md"
    assert records["final_answer"]["source_artifact_id"] == "retained_trajectory"


def test_missing_retained_notice_has_no_workspace_or_convention_fallback(tmp_path):
    roots, effective = runtime(tmp_path, notice=None)
    for directory in (roots["workdir"], roots["artifacts"]):
        (directory / "notice.md").write_text(GOOD, encoding="utf-8")
    result = asyncio.run(
        run_verifier(
            TASK / "tests/grader.json",
            runtime=effective,
            judge_settings=JudgeSettings(enabled=False),
        )
    )
    assert result["reward"] == 0


@pytest.mark.parametrize(
    "source",
    [
        "Unknown source contract",
        SOURCE.replace("17 June 2027", "30 February 2027"),
        SOURCE.replace("09:30", "25:30"),
    ],
)
def test_bad_initial_source_is_a_verifier_error_not_an_agent_failure(tmp_path, source):
    roots, effective = runtime(tmp_path, source=source)
    with pytest.raises(RuntimeError, match="custom verifier exited"):
        asyncio.run(run_verifier(TASK / "tests/grader.json", runtime=effective))
    assert not (roots["verifier_logs"] / "reward.txt").exists()


@pytest.mark.parametrize("field", ["inputs", "artifacts"])
def test_unavailable_initial_snapshot_or_wrong_runtime_layout_is_a_configuration_error(
    tmp_path, field
):
    roots, effective = runtime(tmp_path)
    paths = replace(
        effective.paths,
        **{field: None if field == "inputs" else str(tmp_path / "artifacts")},
    )
    with pytest.raises(RuntimeError, match="custom verifier exited"):
        asyncio.run(
            run_verifier(
                TASK / "tests/grader.json", runtime=replace(effective, paths=paths)
            )
        )
    assert not (roots["verifier_logs"] / "reward.txt").exists()


def test_missing_parser_dependency_propagates_from_custom_entrypoint(
    tmp_path, monkeypatch
):
    roots, _ = runtime(tmp_path)
    context, output = tmp_path / "context.json", tmp_path / "output.json"
    context.write_text(
        json.dumps({"paths": {key: str(path) for key, path in roots.items()}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["test_outputs.py", "--context", str(context), "--output", str(output)],
    )

    def absent_parser(*args, **kwargs):
        raise MissingDocumentDependency("missing installed Markdown parser")

    monkeypatch.setitem(GRADER["main"].__globals__, "inspect_document", absent_parser)
    with pytest.raises(MissingDocumentDependency):
        GRADER["main"]()
    assert not output.exists()


def test_real_native_default_preparation_collection_and_judge_roundtrip(tmp_path):
    task = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    trial = TrialPaths(tmp_path / "trial")
    trial.mkdir()
    convention = trial.artifacts_dir / "logs/artifacts"
    convention.mkdir(parents=True)
    host = HostEnvironment(
        environment_dir=TASK / "environment",
        environment_name="example-notice",
        session_id="example-notice",
        trial_paths=trial,
        task_env_config=task.config.environment,
        logger=logging.getLogger(__name__),
        mounts=[
            {"type": "bind", "source": str(trial.agent_dir), "target": "/logs/agent"},
            {
                "type": "bind",
                "source": str(trial.verifier_dir),
                "target": "/logs/verifier",
            },
            {"type": "bind", "source": str(convention), "target": "/logs/artifacts"},
        ],
        host_access={"filesystem": True, "process": True},
        workdir_root=tmp_path / "workspaces",
        workspace_baseline="none",
    )

    async def run():
        await host.start(False)
        try:
            configured = load_effective_runtime_config(
                host.runtime_config_env()["PEVAL_CONFIG"]
            )
            initial = Path(configured.paths.inputs) / "operations-note.md"
            assert initial.read_text(encoding="utf-8") == SOURCE
            assert (host.work_dir / "operations-note.md").read_text(
                encoding="utf-8"
            ) == SOURCE
            (host.work_dir / "operations-note.md").write_text(
                "Modified after preparation", encoding="utf-8"
            )
            (host.work_dir / "notice.md").write_text(GOOD, encoding="utf-8")
            (trial.agent_dir / "trajectory.json").write_text(
                trajectory().model_dump_json(), encoding="utf-8"
            )
            collector = ArtifactHandler(
                artifacts=task.config.artifacts, logger=logging.getLogger(__name__)
            )
            manifest = await collector.download_artifacts(
                host, trial.artifacts_dir, source_artifacts_dir="/logs/artifacts"
            )
            assert [
                (entry.destination, entry.status) for entry in manifest.entries
            ] == [
                ("artifacts/logs/artifacts", "empty"),
                ("artifacts/notice.md", "ok"),
            ]
            (host.work_dir / "notice.md").unlink()
            assert initial.read_text(encoding="utf-8") == SOURCE
            effective = replace(
                configured,
                verifier=VerifierInvocation(
                    (TASK / "instruction.md").read_text(encoding="utf-8")
                ),
            )
            with judge_server() as server:
                server["behavior"] = {"usable_notice": {"passed": True}}
                result = await run_verifier(
                    TASK / "tests/grader.json",
                    runtime=effective,
                    judge_settings=JudgeSettings(True, server["url"], "fixture"),
                )
            assert result["reward"] == 1
            assert len(server["requests"]) == 1
            assert (
                "Modified after preparation"
                not in server["requests"][0]["messages"][-1]["content"]
            )
            assert (trial.verifier_dir / "raw_artifacts/notice_md.md").read_text(
                encoding="utf-8"
            ) == GOOD
        finally:
            await host.stop(True)

    asyncio.run(run())


def test_example_contract_is_runnable_host_only_and_not_a_dataset_task():
    task = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert task.config.agent.timeout_sec == 900
    assert task.config.verifier.environment_mode == "shared"
    assert not (TASK / "environment/Dockerfile").exists()
    config = json.loads((TASK / "tests/grader.json").read_text(encoding="utf-8"))
    assert [item.id for item in build_scoring_plan(config).items] == [
        "custom:notice_facts"
    ]
    assert "required_calls" not in config
    assert all(
        TASK not in list(dataset.iterdir())
        for dataset in (ROOT / "datasets").iterdir()
        if dataset.is_dir()
    )
