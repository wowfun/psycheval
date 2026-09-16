from __future__ import annotations

import asyncio
import json
import stat
import threading
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
    load_effective_runtime_config,
    write_effective_runtime_config,
)
from psycheval.harbor.verifier.__main__ import main
from psycheval.harbor.verifier._judge import JudgeSettings, merge_scores, run_judge
from psycheval.harbor.verifier._judge_config import parse_judge_config
from tests.fixtures.judge_server import judge_server

YAML = """version: 1
artifacts:
  - id: report
    path: 中文 报告.md
    required: true
    type: md
llm_judge:
  method: rubric_binary_mean
  rubrics:
    - id: fidelity
      question: >-
        中文摘要是否
        忠实于来源？
      artifact_refs: [report]
      pass_criteria:
        - >-
          主体、含义和限定条件
          均有来源支持。
        - 保留关键事实。
      fail_criteria:
        - 虚构关键结论。
      scope_limits:
        - 不检查条目数量。
"""


def runtime(tmp_path):
    roots = {
        name: tmp_path / name
        for name in ("workdir", "tests", "agent_logs", "verifier_logs", "artifacts")
    }
    for root in roots.values():
        root.mkdir(parents=True, exist_ok=True)
    config = EffectiveRuntimeConfig(
        paths=RuntimePaths(**{name: str(root) for name, root in roots.items()}),
        verifier=VerifierInvocation("评估当前步骤，不读其他步骤。", "中文步骤"),
    )
    (roots["workdir"] / "中文 报告.md").write_text(
        "这里是当前来源支持的摘要。", encoding="utf-8"
    )
    return config


def config_with_two_rubrics():
    value = yaml.safe_load(YAML)
    value["llm_judge"]["rubrics"].append(
        {**value["llm_judge"]["rubrics"][0], "id": "quality"}
    )
    return parse_judge_config(yaml.safe_dump(value, allow_unicode=True))


def test_yaml_multiline_lists_and_runtime_context_roundtrip(tmp_path):
    config = parse_judge_config(YAML)
    assert config.rubrics[0].question == "中文摘要是否 忠实于来源？"
    assert config.rubrics[0].pass_criteria[0] == "主体、含义和限定条件 均有来源支持。"
    assert config.rule_weight == 0.8 and config.llm_weight == 0.2
    context = runtime(tmp_path)
    path = write_effective_runtime_config(tmp_path / "上下文.json", context)
    assert load_effective_runtime_config(path) == context


@pytest.mark.parametrize(
    "change",
    [
        lambda x: x.update(version=True),
        lambda x: x.update(version=2),
        lambda x: x.update(unknown=1),
        lambda x: x["artifacts"][0].update(required="true"),
        lambda x: x["artifacts"][0].update(path="../secret"),
        lambda x: x["artifacts"][0].update(path="C:/secret"),
        lambda x: x["artifacts"][0].update(path="/secret"),
        lambda x: x["artifacts"][0].update(path="x\\secret"),
        lambda x: x["artifacts"][0].update(source="other"),
        lambda x: x["artifacts"][0].update(type="pdf"),
        lambda x: x["artifacts"].append(x["artifacts"][0]),
        lambda x: x["llm_judge"].update(method="another"),
        lambda x: x["llm_judge"].update(rubrics=[]),
        lambda x: x["llm_judge"]["rubrics"].append(x["llm_judge"]["rubrics"][0]),
        lambda x: x["llm_judge"]["rubrics"][0].update(artifact_refs=["missing"]),
        lambda x: x["llm_judge"]["rubrics"][0].update(
            artifact_refs=["report", "report"]
        ),
        lambda x: x["llm_judge"]["rubrics"][0].update(question=["question"]),
        lambda x: x["llm_judge"]["rubrics"][0].update(pass_criteria="text"),
        lambda x: x["llm_judge"]["rubrics"][0].update(scope_limits=[False]),
        lambda x: x["llm_judge"]["rubrics"][0].update(id="../secret"),
        *(
            lambda x, weight=w: x.update(
                score_merge={"method": "weighted_sum", "llm_weight": weight}
            )
            for w in (-1, True, "1", float("inf"), float("nan"))
        ),
        lambda x: x.update(
            score_merge={"method": "weighted_sum", "rule_weight": 0, "llm_weight": 0}
        ),
        lambda x: x.update(score_merge={"method": "other"}),
    ],
)
def test_yaml_invalid_declarations_fail_statically(change):
    value = yaml.safe_load(YAML)
    change(value)
    with pytest.raises(ValueError):
        parse_judge_config(yaml.safe_dump(value, allow_unicode=True))


@pytest.mark.parametrize(
    "text",
    [
        YAML + "version: 1\n",
        YAML.replace("required: true", "required: true\n    required: false"),
        "!!python/object/apply:os.system ['echo unsafe']",
    ],
)
def test_yaml_duplicate_keys_and_unsafe_constructors(text):
    with pytest.raises(ValueError):
        parse_judge_config(text)


def test_disabled_judge_sends_no_requests_and_preserves_rule_score(tmp_path):
    with judge_server() as server:
        config = parse_judge_config(YAML)
        result = asyncio.run(
            run_judge(config, runtime(tmp_path), JudgeSettings(base_url=server["url"]))
        )
        rewards, merge = merge_scores({"reward": 0.75}, config, result)
        assert rewards == {"reward": 0.75, "rule_score": 0.75}
        assert not merge["applied"] and result["status"] == "disabled"
        assert not server["requests"]


def test_complete_concurrent_judge_merges_and_retains_diagnostics(tmp_path):
    with judge_server() as server:
        server["barrier"] = threading.Barrier(2)
        server["behavior"] = {
            "quality": {"passed": False},
        }
        config, context = config_with_two_rubrics(), runtime(tmp_path)
        settings = JudgeSettings(
            True, server["url"], "fixture-model", "private-credential"
        )
        result = asyncio.run(run_judge(config, context, settings))
        rewards, merge = merge_scores(
            {"reward": 0.75, "required_tool": 1}, config, result
        )
        assert rewards["llm_score"] == 0.5
        assert rewards["reward"] == pytest.approx(0.7)
        assert rewards["required_tool"] == 1 and merge["applied"]
        assert server["peak"] == 2
        user_message = json.loads(server["requests"][0]["messages"][1]["content"])
        assert user_message["step_name"] == "中文步骤"
        assert user_message["instruction"] == context.verifier.instruction
        assert user_message["rubric"]["scope_limits"] == ["不检查条目数量。"]
        diagnostics = Path(context.paths.verifier_logs) / "judge"
        response = json.loads((diagnostics / "rubric-0001.json").read_text())
        assert response["attempts"][0]["usage"]["completion_tokens"] == 8
        assert all(
            "private-credential" not in file.read_text()
            for file in diagnostics.iterdir()
        )


@pytest.mark.parametrize(
    "behavior,attempts",
    [
        ({"status": 429}, 2),
        ({"status": 503}, 2),
        ({"status": 401}, 1),
        ({"raw": "not JSON"}, 1),
        ({"result": {"id": "unexpected"}}, 1),
        ({"result": {"passed": "yes"}}, 1),
        ({"result": {"extra": True}}, 1),
        ({"finish_reason": "length"}, 1),
        (
            {
                "content": '{"id":"quality","passed":true,"passed":false,"reason":"duplicate"}'
            },
            1,
        ),
    ],
)
def test_one_incomplete_rubric_disables_whole_merge(tmp_path, behavior, attempts):
    with judge_server() as server:
        server["behavior"]["quality"] = behavior
        config = config_with_two_rubrics()
        result = asyncio.run(
            run_judge(
                config, runtime(tmp_path), JudgeSettings(True, server["url"], "fixture")
            )
        )
        rewards, merge = merge_scores({"reward": 0.75}, config, result)
        assert result["status"] == "incomplete"
        assert len(result["checks"]) == 1
        assert rewards == {"reward": 0.75, "rule_score": 0.75} and not merge["applied"]
        assert server["counts"]["quality"] == attempts


def test_judge_deadline_prevents_merge_even_if_blocking_work_finishes_last_rubric(
    tmp_path, monkeypatch
):
    import time

    from psycheval.harbor.verifier import _judge

    async def slow_assess(rubric, *args):
        # Represents synchronous diagnostic I/O while finishing the last response.
        time.sleep(0.08)
        return {"id": rubric.id, "passed": True, "reason": "finished too late"}

    monkeypatch.setattr(_judge, "_assess", slow_assess)
    config = parse_judge_config(YAML)
    result = asyncio.run(
        run_judge(
            config,
            runtime(tmp_path),
            JudgeSettings(True, "http://unused.invalid", "fixture", total_timeout=0.04),
        )
    )
    rewards, decision = merge_scores({"reward": 0.75}, config, result)
    assert result["status"] == "incomplete"
    assert "deadline" in result["reason"]
    assert not decision["applied"] and "llm_score" not in rewards


def test_retry_and_total_budget(tmp_path):
    with judge_server() as server:
        server["behavior"]["fidelity"] = {"retry": 429}
        config = parse_judge_config(YAML)
        settings = JudgeSettings(True, server["url"], "fixture")
        result = asyncio.run(run_judge(config, runtime(tmp_path / "retry"), settings))
        assert result["status"] == "complete" and server["counts"]["fidelity"] == 2
        server["behavior"]["fidelity"] = {"delay": 1}
        result = asyncio.run(
            run_judge(
                config,
                runtime(tmp_path / "timeout"),
                replace(settings, total_timeout=0.1),
            )
        )
        assert result["status"] == "incomplete" and "deadline" in result["reason"]


@pytest.mark.parametrize(
    "source", ["workdir", "tests", "artifacts", "agent_logs", "verifier_logs"]
)
def test_declared_roots_missing_agent_evidence_vs_task_error(tmp_path, source):
    context = runtime(tmp_path)
    config = parse_judge_config(YAML)
    config = replace(
        config,
        artifacts=(replace(config.artifacts[0], source=source, path="missing.txt"),),
    )
    with judge_server() as server:
        settings = JudgeSettings(True, server["url"], "fixture")
        if source == "tests":
            with pytest.raises(ValueError, match="Task judge evidence"):
                asyncio.run(run_judge(config, context, settings))
        else:
            result = asyncio.run(run_judge(config, context, settings))
            assert result["status"] == "complete" and not result["checks"][0]["passed"]
        assert not server["requests"]


def test_oversized_evidence_falls_back_without_truncation_or_model_call(tmp_path):
    context = runtime(tmp_path)
    with judge_server() as server:
        result = asyncio.run(
            run_judge(
                parse_judge_config(YAML),
                context,
                JudgeSettings(True, server["url"], "fixture", max_evidence_bytes=2),
            )
        )
        assert result["status"] == "incomplete" and "exceeds" in result["reason"]
        assert not server["requests"]


def test_cli_clears_old_judge_and_generated_evidence_before_script(
    tmp_path, monkeypatch
):
    context = runtime(tmp_path)
    tests, logs = Path(context.paths.tests), Path(context.paths.verifier_logs)
    (tests / "grader.json").write_text('{"custom_checks":["valid"]}')
    (tests / "judge.yaml").write_text(YAML, encoding="utf-8")
    (tests / "test_outputs.py").write_text(
        """import json,sys
from pathlib import Path
context = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
logs = Path(context['paths']['verifier_logs'])
assert not (logs / 'judge').exists()
assert not (logs / 'judge-evidence').exists()
assert context['harbor']['verifier']['step_name'] == '中文步骤'
Path(sys.argv[4]).write_text('{"checks":[{"id":"valid","passed":true}]}')
""",
        encoding="utf-8",
    )
    for name in ("judge", "judge-evidence"):
        (logs / name).mkdir()
        (logs / name / "old").write_text("old")
    for name in ("reward.json", "checks.json", "reward.txt"):
        (logs / name).write_text("old")
    monkeypatch.setenv(
        "PEVAL_CONFIG",
        str(write_effective_runtime_config(tmp_path / "context.json", context)),
    )
    assert main([str(tests / "grader.json")]) == 0
    assert json.loads((logs / "reward.json").read_text())["rule_score"] == 1
    assert not (logs / "reward.txt").exists()
    # Static YAML errors abort before any task script and remove last invocation's reward.
    (tests / "judge.yaml").write_text(YAML + "version: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        main([str(tests / "grader.json")])
    assert not (logs / "reward.json").exists()
    assert (logs / "verifier-error.txt").exists()


@pytest.mark.parametrize("mode", ["cancel", "timeout"])
def test_native_judge_cancellation_terminates_verifier_and_keeps_diagnostics(
    tmp_path, mode
):
    import psutil
    from harbor.models.task.task import Task

    from psycheval.harbor.verifier.host import HostVerifier
    from tests.harbor.test_environment import make_environment

    host = make_environment(
        tmp_path / "host",
        environment_kwargs={
            "workdir_root": tmp_path / "workspaces",
            "workspace_baseline": "none",
        },
    )
    task_dir = host.environment_dir.parent
    (task_dir / "task.toml").write_text('[environment]\nworkdir="/app"\n')
    (task_dir / "instruction.md").write_text("fixture instruction")
    tests = task_dir / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "grader.json").write_text('{"custom_checks":["valid"]}')
    (tests / "judge.yaml").write_text(YAML, encoding="utf-8")
    (tests / "test_outputs.py").write_text(
        """import json,sys,os
from pathlib import Path
context=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
Path(context['paths']['verifier_logs'],'pid.txt').write_text(str(os.getppid()))
Path(sys.argv[4]).write_text('{"checks":[{"id":"valid","passed":true}]}')
""",
        encoding="utf-8",
    )
    (tests / "test.sh").write_text(
        '#!/bin/sh\npython -m psycheval.harbor.verifier "$(dirname "$0")/grader.json"\n'
    )
    (tests / "test.bat").write_text(
        '@echo off\npython -m psycheval.harbor.verifier "%~dp0grader.json"\n'
    )

    with judge_server() as server:
        server["behavior"]["fidelity"] = {"delay": 2}

        async def run():
            await host.start(False)
            workdir = host.work_dir
            (workdir / "中文 报告.md").write_text("当前证据", encoding="utf-8")
            logs = host.trial_paths.verifier_dir
            (logs / "reward.json").write_text('{"reward":1}')
            verifier = HostVerifier(
                task=Task(task_dir),
                trial_paths=host.trial_paths,
                environment=host,
                override_env={
                    "PEVAL_JUDGE_ENABLED": "true",
                    "PEVAL_JUDGE_MODEL": "fixture",
                    "PEVAL_JUDGE_BASE_URL": server["url"],
                    "PYTHONUTF8": "0",
                },
            )
            operation = asyncio.create_task(verifier.verify())
            try:
                async with asyncio.timeout(10):
                    while not server["requests"]:
                        if operation.done():
                            await operation
                            pytest.fail("verifier finished before its model request")
                        await asyncio.sleep(0.02)
                if mode == "cancel":
                    operation.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await operation
                else:
                    with pytest.raises(TimeoutError):
                        await asyncio.wait_for(operation, timeout=0.01)
                pid = int((logs / "pid.txt").read_text())
                assert (
                    not psutil.pid_exists(pid)
                    or psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
                )
                assert not (logs / "reward.json").exists()
                assert (logs / "judge/evidence.json").exists()
            finally:
                if not operation.done():
                    operation.cancel()
                    await asyncio.gather(operation, return_exceptions=True)
                await host.stop(True)
            assert not workdir.exists()

        asyncio.run(run())


@pytest.mark.parametrize(
    "name,value",
    [
        ("ENABLED", "yes"),
        ("MODEL", ""),
        ("BASE_URL", "http://user:secret@localhost/v1"),
        ("CONCURRENCY", "0"),
        ("CONCURRENCY", "1.5"),
        ("REQUEST_TIMEOUT_SEC", "nan"),
        ("TOTAL_TIMEOUT_SEC", "-1"),
        ("MAX_EVIDENCE_BYTES", "false"),
    ],
)
def test_invalid_runtime_settings_are_configuration_errors(monkeypatch, name, value):
    monkeypatch.setenv("PEVAL_JUDGE_ENABLED", "true")
    monkeypatch.setenv("PEVAL_JUDGE_BASE_URL", "http://localhost/v1")
    monkeypatch.setenv("PEVAL_JUDGE_MODEL", "fixture")
    monkeypatch.setenv("PEVAL_JUDGE_" + name, value)
    with pytest.raises(ValueError):
        JudgeSettings.from_env()


def test_judge_reclaims_reserved_directory(tmp_path):
    context = runtime(tmp_path)
    directory = Path(context.paths.verifier_logs) / "judge"
    directory.mkdir()
    (directory / "old-response.json").write_text("obsolete")
    with judge_server() as server:
        result = asyncio.run(
            run_judge(
                parse_judge_config(YAML),
                context,
                JudgeSettings(True, server["url"], "fixture"),
            )
        )
    assert result["status"] == "complete"
    assert not (directory / "old-response.json").exists()


def test_evidence_read_does_not_require_windows_stat_constants(tmp_path, monkeypatch):
    monkeypatch.delattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", raising=False)
    with judge_server() as server:
        result = asyncio.run(
            run_judge(
                parse_judge_config(YAML),
                runtime(tmp_path),
                JudgeSettings(True, server["url"], "fixture"),
            )
        )
    assert result["status"] == "complete"


def test_cli_bounds_yaml_read_before_parsing(tmp_path, monkeypatch):
    context = runtime(tmp_path)
    tests = Path(context.paths.tests)
    (tests / "grader.json").write_text('{"final_terms":["done"]}')
    judge = tests / "judge.yaml"
    judge.write_bytes(b" " * (1024 * 1024 + 1))
    monkeypatch.setenv(
        "PEVAL_CONFIG",
        str(write_effective_runtime_config(tmp_path / "context.json", context)),
    )
    original = Path.read_bytes

    def disallow_unbounded_read(path):
        assert path != judge, "judge.yaml must use a bounded read"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", disallow_unbounded_read)
    with pytest.raises(ValueError, match="1 MiB"):
        main([str(tests / "grader.json")])


@pytest.mark.parametrize("field", ["artifacts", "rubrics"])
def test_judge_rejects_excessive_declarations(field):
    value = yaml.safe_load(YAML)
    items = (
        value["artifacts"] if field == "artifacts" else value["llm_judge"]["rubrics"]
    )
    items.extend({**items[0], "id": f"item_{i}"} for i in range(32))
    with pytest.raises(ValueError, match="32"):
        parse_judge_config(yaml.safe_dump(value))


def test_custom_script_does_not_inherit_judge_connection_settings(
    tmp_path, monkeypatch
):
    context = runtime(tmp_path)
    tests, logs = Path(context.paths.tests), Path(context.paths.verifier_logs)
    (tests / "grader.json").write_text('{"custom_checks":["valid"]}')
    (tests / "judge.yaml").write_text(YAML, encoding="utf-8")
    (tests / "test_outputs.py").write_text(
        "import os,sys; from pathlib import Path\n"
        "assert not any(k.upper().startswith('PEVAL_JUDGE_') for k in os.environ)\n"
        "assert os.environ['TASK_CUSTOM_SETTING']=='preserved'\n"
        'Path(sys.argv[4]).write_text(\'{"checks":[{"id":"valid","passed":true}]}\')\n',
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "PEVAL_CONFIG",
        str(write_effective_runtime_config(tmp_path / "context.json", context)),
    )
    monkeypatch.setenv("TASK_CUSTOM_SETTING", "preserved")
    with judge_server() as server:
        for key, value in {
            "ENABLED": "true",
            "API_KEY": "private-key",
            "MODEL": "fixture",
            "BASE_URL": server["url"],
        }.items():
            monkeypatch.setenv("PEVAL_JUDGE_" + key, value)
        assert main([str(tests / "grader.json")]) == 0
        assert len(server["requests"]) == 1
    assert json.loads((logs / "reward.json").read_text())["llm_score"] == 1


def test_request_timeout_retries_once_and_can_complete(tmp_path):
    with judge_server() as server:
        server["behavior"]["fidelity"] = {"delay": [1, 0]}
        result = asyncio.run(
            run_judge(
                parse_judge_config(YAML),
                runtime(tmp_path),
                JudgeSettings(True, server["url"], "fixture", request_timeout=0.2),
            )
        )
        assert result["status"] == "complete"
        assert server["counts"]["fidelity"] == 2
        diagnostics = json.loads(
            (tmp_path / "verifier_logs/judge/rubric-0001.json").read_text()
        )
        assert diagnostics["attempts"][0]["error"] == "TimeoutError"


def test_optional_missing_evidence_and_explicit_merge_weights(tmp_path):
    context = runtime(tmp_path)
    config = parse_judge_config(YAML)
    config = replace(
        config,
        rule_weight=3,
        llm_weight=1,
        artifacts=(replace(config.artifacts[0], required=False, path="absent.txt"),),
    )
    with judge_server() as server:
        server["behavior"]["fidelity"] = {"passed": False}
        result = asyncio.run(
            run_judge(config, context, JudgeSettings(True, server["url"], "fixture"))
        )
        assert result["status"] == "complete"
        evidence = json.loads(server["requests"][0]["messages"][1]["content"])[
            "evidence"
        ]
        assert evidence["report"]["text"] is None
        assert not evidence["report"]["required"]
    reward, decision = merge_scores({"reward": 1}, config, result)
    assert decision["applied"] and reward["reward"] == 0.75


def test_evidence_budget_is_shared_across_artifacts(tmp_path):
    context = runtime(tmp_path)
    config = parse_judge_config(YAML)
    artifact = config.artifacts[0]
    config = replace(config, artifacts=(artifact, replace(artifact, id="second")))
    size = (Path(context.paths.workdir) / artifact.path).stat().st_size
    with judge_server() as server:
        result = asyncio.run(
            run_judge(
                config,
                context,
                JudgeSettings(
                    True, server["url"], "fixture", max_evidence_bytes=size * 2 - 1
                ),
            )
        )
        assert result["status"] == "incomplete" and "exceeds" in result["reason"]
        assert not server["requests"]


@pytest.mark.parametrize("source", ["workdir", "tests"])
def test_non_utf8_evidence_has_agent_vs_task_error_semantics(tmp_path, source):
    context = runtime(tmp_path)
    config = parse_judge_config(YAML)
    artifact = replace(config.artifacts[0], source=source)
    config = replace(config, artifacts=(artifact,))
    (Path(getattr(context.paths, source)) / artifact.path).write_bytes(b"\xff")
    with judge_server() as server:
        operation = run_judge(
            config, context, JudgeSettings(True, server["url"], "fixture")
        )
        if source == "tests":
            with pytest.raises(ValueError, match="Task judge evidence"):
                asyncio.run(operation)
        else:
            result = asyncio.run(operation)
            assert result["status"] == "complete" and not result["checks"][0]["passed"]
            diagnostic = json.loads(
                (
                    Path(context.paths.verifier_logs) / "judge/rubric-0001.json"
                ).read_text()
            )
            assert diagnostic["attempts"] == [] and diagnostic["result"]["missing"] == [
                artifact.id
            ]
        assert not server["requests"]


@pytest.mark.parametrize(
    "key", ['fixture-credential-with-"quote', "fixture-credential-with-backslash\\"]
)
def test_known_credential_in_evidence_and_response_is_redacted(tmp_path, key):
    context = runtime(tmp_path)
    (Path(context.paths.workdir) / "中文 报告.md").write_text(key, encoding="utf-8")
    with judge_server() as server:
        server["behavior"]["fidelity"] = {"result": {"reason": key}}
        result = asyncio.run(
            run_judge(
                parse_judge_config(YAML),
                context,
                JudgeSettings(True, server["url"], "fixture", key),
            )
        )
    assert result["checks"][0]["reason"] == "[REDACTED]"
    for path in (Path(context.paths.verifier_logs) / "judge").glob("*.json"):
        assert "fixture-credential" not in path.read_text()
        json.loads(path.read_text())


def test_judge_directory_link_is_replaced_and_evidence_link_is_rejected(tmp_path):
    context = runtime(tmp_path)
    external = tmp_path / "outside"
    external.mkdir()
    sentinel = external / "keep.txt"
    sentinel.write_text("must not be read as evidence or changed")
    directory = Path(context.paths.verifier_logs) / "judge"
    report = Path(context.paths.workdir) / "中文 报告.md"
    report.unlink()
    try:
        directory.symlink_to(external, target_is_directory=True)
        report.symlink_to(sentinel)
    except OSError as exc:
        pytest.skip(f"native symlink creation unavailable: {exc}")
    with judge_server() as server:
        result = asyncio.run(
            run_judge(
                parse_judge_config(YAML),
                context,
                JudgeSettings(True, server["url"], "fixture"),
            )
        )
        assert result["status"] == "complete" and not result["checks"][0]["passed"]
        assert not server["requests"]
    assert not directory.is_symlink()
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_text() == "must not be read as evidence or changed"


def test_utf8_configuration_limit_and_reference_count():
    with pytest.raises(ValueError, match="1 MiB"):
        parse_judge_config("#" + "中" * (1024 * 1024 // 3 + 1))
    value = yaml.safe_load(YAML)
    value["artifacts"] = [{**value["artifacts"][0], "id": f"item{i}"} for i in range(9)]
    value["llm_judge"]["rubrics"][0]["artifact_refs"] = [
        item["id"] for item in value["artifacts"]
    ]
    with pytest.raises(ValueError, match="8 entries"):
        parse_judge_config(yaml.safe_dump(value))


def test_cli_accepts_atif_larger_than_regular_json_limit(tmp_path, monkeypatch):
    context = runtime(tmp_path)
    trajectory = {
        "schema_version": "ATIF-v1.7",
        "trajectory_id": "large-observation",
        "agent": {"name": "fixture", "version": "1"},
        "steps": [
            {"step_id": 1, "source": "user", "message": "instruction"},
            {"step_id": 2, "source": "agent", "message": "x" * (17 * 1024 * 1024)},
            {"step_id": 3, "source": "agent", "message": "done"},
        ],
    }
    (Path(context.paths.agent_logs) / "trajectory.json").write_text(
        json.dumps(trajectory)
    )
    grader = Path(context.paths.tests) / "grader.json"
    grader.write_text('{"final_terms":["done"]}')
    monkeypatch.setenv(
        "PEVAL_CONFIG",
        str(write_effective_runtime_config(tmp_path / "context.json", context)),
    )
    assert main([str(grader)]) == 0
    assert (
        json.loads((Path(context.paths.verifier_logs) / "reward.json").read_text())[
            "reward"
        ]
        == 1
    )
