from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest

from tests.fixtures import trend_digest as trend_fixtures
from tests.harbor.trend_digest_support import (
    NOW,
    TASK_ROOT,
    grade,
    loaded_task_module,
    make_case,
)


@pytest.fixture(scope="module")
def verifier() -> Iterator[ModuleType]:
    with loaded_task_module(
        "pbench_trend_github_verifier",
        Path("tests/test_outputs.py"),
    ) as module:
        yield module


@pytest.mark.parametrize("source_format", ["html", "markdown"])
def test_github_repository_slots_use_relative_heading_links_not_navigation(
    tmp_path, verifier, source_format
):
    runtime, config, _, _ = make_case(tmp_path, "github")
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    source = (
        "https://github.com/features/copilot\nhttps://github.com/solutions/use-case\n"
    )
    for index in range(1, 11):
        url = f"/fixture-org-{index}/fixture-repo-{index}"
        source += (
            f'<article><h2><a href="{url}">repository {index}</a></h2></article>\n'
            if source_format == "html"
            else f"## [repository {index}]({url})\n"
        )
    data["steps"][1]["observation"]["results"][0]["content"] = source
    path.write_text(json.dumps(data), encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1


def _github_saved_page(tmp_path, *, source_format="jsonl"):
    runtime, config, _, snapshot = make_case(tmp_path, "github")
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    fetch = data["steps"][1]
    fetch["tool_calls"][0].update(
        function_name="Bash",
        arguments={
            "command": f'curl -sSL "{trend_fixtures.GITHUB_URL}" -o /tmp/trending.html'
        },
    )
    fetch["observation"]["results"][0]["content"] = "623412 /tmp/trending.html"
    rows = [
        {"rank": rank, "name": name, "desc": f"Source description {rank}"}
        for rank, name in enumerate(snapshot["repositories"], 1)
    ]
    source = (
        json.dumps(rows)
        if source_format == "json"
        else "\n".join(json.dumps(row) for row in rows)
    )
    command = "cd /tmp && python - <<'PY'\nh=open('trending.html').read()\nparse(h)\nPY"
    read = {
        "step_id": 3,
        "source": "agent",
        "message": "",
        "tool_calls": [
            {
                "tool_call_id": "read-page",
                "function_name": "Bash",
                "arguments": {"command": command},
            }
        ],
        "observation": {
            "results": [
                {
                    "source_call_id": "read-page",
                    "content": f"Command: {command}\nStdout: {source}\n\nStderr: (empty)\nExit Code: 0",
                    "extra": {"exit_code": 0},
                }
            ]
        },
    }
    data["steps"].insert(2, read)
    data["steps"][-1]["step_id"] = 4
    return runtime, config, path, data, source


@pytest.mark.parametrize("source_format", ["json", "jsonl"])
def test_github_saved_page_parse_supplies_ranked_source_evidence(
    tmp_path, verifier, source_format
):
    runtime, config, path, data, source = _github_saved_page(
        tmp_path, source_format=source_format
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    evidence = (
        Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
    ).read_text(encoding="utf-8")
    assert source in evidence and "read-page" in evidence and "call-1" in evidence
    assert "parse(h)" not in evidence and "Stdout:" not in evidence


@pytest.mark.parametrize("path_kind", ["literal", "environment"])
def test_github_node_fetch_and_linked_rank_wrapper(tmp_path, verifier, path_kind):
    runtime, config, path, data, _ = _github_saved_page(tmp_path, source_format="json")
    fetch, read = data["steps"][1:3]
    target = (
        '"trending.html"'
        if path_kind == "literal"
        else 'process.env.TEMP + "/trending.html"'
    )
    fetch["tool_calls"][0]["arguments"] = {
        "command": f'const url = "{trend_fixtures.GITHUB_URL}"; fetch(url).then(r => r.text()).then(t => fs.writeFileSync({target}, t, "utf8"));'
    }
    read["tool_calls"][0]["arguments"] = {
        "command": f'const html = fs.readFileSync({target}, "utf8"); parse(html);'
    }
    source = json.dumps(
        {
            "total": 11,
            "top10": [
                {
                    "rank": rank,
                    "repo": f"fixture-org-{rank}/fixture-repo-{rank}",
                    "description": f"Source fact {rank}",
                }
                for rank in range(1, 11)
            ],
        }
    )
    read["observation"]["results"][0]["content"] = source
    path.write_text(json.dumps(data), encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    evidence = (
        Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
    ).read_text(encoding="utf-8")
    assert (
        source in evidence
        and "Fetch call: call-1" in evidence
        and "Evidence call: read-page" in evidence
    )


@pytest.mark.parametrize(
    "defect",
    [
        "no_fetch",
        "failed_fetch",
        "unrelated_path",
        "symbolic_suffix",
        "computed_path",
        "before_fetch",
        "partial",
        "conflicting_identity",
        "bad_rank",
        "multiple_arrays",
        "nested_wrapper",
        "bad_total",
    ],
)
def test_github_node_wrapper_does_not_bypass_source_or_rank_validation(
    tmp_path, verifier, defect
):
    runtime, config, path, data, _ = _github_saved_page(tmp_path, source_format="json")
    fetch, read = data["steps"][1:3]
    fetch["tool_calls"][0]["arguments"] = {
        "command": f'fetch("{trend_fixtures.GITHUB_URL}").then(r=>r.text()).then(t=>fs.writeFileSync("trending.html",t));'
    }
    read["tool_calls"][0]["arguments"] = {
        "command": 'parse(fs.readFileSync("trending.html","utf8"));'
    }
    rows = [
        {"rank": rank, "repo": f"fixture-org-{rank}/fixture-repo-{rank}"}
        for rank in range(1, 11)
    ]
    wrapper = {"total": 11, "top10": rows}
    if defect == "no_fetch":
        fetch["tool_calls"][0]["arguments"]["command"] = (
            f'console.log("{trend_fixtures.GITHUB_URL}"); fs.writeFileSync("trending.html", "invented");'
        )
    elif defect == "failed_fetch":
        fetch["observation"]["results"][0]["extra"]["exit_code"] = 1
    elif defect == "unrelated_path":
        read["tool_calls"][0]["arguments"]["command"] = (
            'parse(fs.readFileSync("other.html","utf8"));'
        )
    elif defect == "symbolic_suffix":
        fetch["tool_calls"][0]["arguments"]["command"] = (
            f'fetch("{trend_fixtures.GITHUB_URL}").then(t=>fs.writeFileSync(process.env.TEMP+"/trending.html",t));'
        )
        read["tool_calls"][0]["arguments"]["command"] = (
            'parse(fs.readFileSync(process.env.TEMP+"/other.html","utf8"));'
        )
    elif defect == "computed_path":
        fetch["tool_calls"][0]["arguments"]["command"] = (
            f'fetch("{trend_fixtures.GITHUB_URL}").then(t=>fs.writeFileSync("trending.html"+suffix,t));'
        )
    elif defect == "before_fetch":
        data["steps"][1:3] = [read, fetch]
        read["step_id"], fetch["step_id"] = 2, 3
    elif defect == "partial":
        wrapper["top10"] = rows[:5]
        later = json.loads(json.dumps(read))
        later["step_id"] = 4
        later["tool_calls"][0]["tool_call_id"] = "read-second-half"
        later["observation"]["results"][0].update(
            source_call_id="read-second-half",
            content=json.dumps({"total": 11, "top10": rows[5:]}),
        )
        data["steps"].insert(3, later)
        data["steps"][-1]["step_id"] = 5
    elif defect == "conflicting_identity":
        rows[0]["url"] = "https://github.com/other/repository"
    elif defect == "bad_rank":
        rows[1]["rank"] = 1
    elif defect == "multiple_arrays":
        wrapper["other"] = rows
    elif defect == "nested_wrapper":
        wrapper = {"data": wrapper}
    elif defect == "bad_total":
        wrapper["total"] = 9
    read["observation"]["results"][0]["content"] = json.dumps(wrapper)
    path.write_text(json.dumps(data), encoding="utf-8")
    _, checks = grade(verifier, runtime, config)
    assert not any(
        checks[f"custom:github_repository_{rank:02}"]["passed"] for rank in range(1, 11)
    )
    assert not (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").exists()


@pytest.mark.parametrize("field", ["name", "repo"])
def test_github_ranked_direct_fetch_accepts_repository_fields_and_later_details(
    tmp_path, verifier, field
):
    runtime, config, path, data, _ = _github_saved_page(tmp_path, source_format="json")
    source = json.dumps(
        [
            {"rank": rank, field: f"fixture-org-{rank}/fixture-repo-{rank}"}
            for rank in range(1, 11)
        ]
    )
    data["steps"][1]["tool_calls"][0]["arguments"] = {
        "code": f"fetch('{trend_fixtures.GITHUB_URL}')"
    }
    data["steps"][1]["tool_calls"][0]["function_name"] = "execute"
    data["steps"][1]["observation"]["results"][0]["content"] = source
    data["steps"][2]["tool_calls"][0].update(
        function_name="execute",
        arguments={"code": f"fetch('{trend_fixtures.GITHUB_URL}')"},
    )
    data["steps"][2]["observation"]["results"][0]["content"] = (
        "Later weekly page descriptions"
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    evidence = (
        Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
    ).read_text(encoding="utf-8")
    assert source in evidence and "Later weekly page descriptions" in evidence
    assert (
        verifier.github_repositories(
            json.dumps([{"rank": 1, "name": "org/first", "repo": "org/conflicting"}])
        )
        == []
    )


@pytest.mark.parametrize(
    "fetch_command,read_name,read_arguments",
    [
        (
            'curl --output="/tmp/trending.html"',
            "Read",
            {"file_path": "/tmp/trending.html"},
        ),
        ("wget -O /tmp/trending.html", "bash", {"command": "cat /tmp/trending.html"}),
        (
            'Invoke-WebRequest -OutFile "C:\\Temp\\trending.html"',
            "exec_command",
            {"command": 'Get-Content -LiteralPath "c:\\temp\\trending.html"'},
        ),
        (
            'Invoke-WebRequest -OutFile "C:\\Temp\\trending.html"',
            "pwsh",
            {"command": 'Get-Content -LiteralPath "c:\\temp\\trending.html"'},
        ),
        (
            'cd /tmp && curl -o "trending.html"',
            "Bash",
            {
                "command": "cd /tmp && python -c \"print(Path('trending.html').read_text())\""
            },
        ),
    ],
)
def test_github_saved_page_supports_literal_shell_and_read_paths(
    tmp_path, verifier, fetch_command, read_name, read_arguments
):
    runtime, config, path, data, source = _github_saved_page(tmp_path)
    fetch, read = data["steps"][1:3]
    fetch["tool_calls"][0]["arguments"]["command"] = (
        fetch_command + f' "{trend_fixtures.GITHUB_URL}"'
    )
    read["tool_calls"][0].update(function_name=read_name, arguments=read_arguments)
    read["observation"]["results"][0]["content"] = source
    path.write_text(json.dumps(data), encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1


def test_github_source_keeps_later_linked_descriptions(tmp_path, verifier):
    runtime, config, path, data, source = _github_saved_page(tmp_path)
    later = json.loads(json.dumps(data["steps"][2]))
    later["step_id"] = 4
    later["tool_calls"][0]["tool_call_id"] = "read-descriptions"
    result = later["observation"]["results"][0]
    result["source_call_id"] = "read-descriptions"
    result["content"] = "Additional extracted description from the same weekly page"
    data["steps"].insert(3, later)
    data["steps"][-1]["step_id"] = 5
    path.write_text(json.dumps(data), encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    evidence = (
        Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
    ).read_text(encoding="utf-8")
    assert source in evidence and result["content"] in evidence
    assert "read-descriptions" in evidence


@pytest.mark.parametrize(
    "failure",
    [
        "fetch_failed",
        "read_failed",
        "unrelated_path",
        "copied_fetch",
        "copied_read",
        "before_fetch",
        "echo_only",
        "bad_rank",
        "duplicate_repo",
        "write_only",
        "wget_log",
    ],
)
@pytest.mark.parametrize("tool_name", ["exec_command", "pwsh"])
def test_github_saved_page_requires_current_successful_linked_evidence(
    tmp_path, verifier, failure, tool_name
):
    runtime, config, path, data, _ = _github_saved_page(tmp_path)
    fetch, read = data["steps"][1:3]
    fetch["tool_calls"][0]["function_name"] = tool_name
    read["tool_calls"][0]["function_name"] = tool_name
    observation = read["observation"]["results"][0]
    if failure == "fetch_failed":
        fetch["observation"]["results"][0]["extra"]["exit_code"] = 1
    elif failure == "read_failed":
        observation["extra"]["exit_code"] = 1
    elif failure == "unrelated_path":
        read["tool_calls"][0]["arguments"]["command"] = (
            "cd /other && python -c \"print(open('trending.html').read())\""
        )
    elif failure.startswith("copied_"):
        (fetch if failure == "copied_fetch" else read)["is_copied_context"] = True
    elif failure == "before_fetch":
        data["steps"][1:3] = [read, fetch]
        read["step_id"], fetch["step_id"] = 2, 3
    elif failure == "echo_only":
        observation["content"] = (
            observation["content"]
            .replace("Stdout:", "# command only\n")
            .split("\n\nStderr:")[0]
            + "\nStdout: done\n\nStderr: (empty)"
        )
    elif failure == "bad_rank":
        observation["content"] = observation["content"].replace(
            '"rank": 2', '"rank": 1'
        )
    elif failure == "duplicate_repo":
        observation["content"] = observation["content"].replace(
            "fixture-org-2/fixture-repo-2", "fixture-org-1/fixture-repo-1"
        )
    elif failure == "write_only":
        read["tool_calls"][0]["arguments"]["command"] = (
            "cd /tmp && python -c \"open('trending.html', 'w').write('invented')\""
        )
    elif failure == "wget_log":
        fetch["tool_calls"][0]["arguments"]["command"] = (
            f"wget -o /tmp/trending.html {trend_fixtures.GITHUB_URL}"
        )
    path.write_text(json.dumps(data), encoding="utf-8")
    checks = grade(verifier, runtime, config)[1]
    assert not any(
        checks[f"custom:github_repository_{rank:02}"]["passed"] for rank in range(1, 11)
    )
    assert not (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").exists()


@pytest.mark.parametrize("same_variable", [True, False])
def test_github_powershell_download_and_node_symbolic_path(
    tmp_path, verifier, monkeypatch, same_variable
):
    runtime, config, path, data, _ = _github_saved_page(tmp_path)
    monkeypatch.setenv("TEMP", "verifier-environment-must-not-be-used")
    fetch, read = data["steps"][1:3]
    fetch["tool_calls"][0]["arguments"] = {
        "command": f'$r = Invoke-WebRequest "{trend_fixtures.GITHUB_URL}"; '
        '$r.Content | Out-File -Encoding utf8 "$env:TEMP\\trending.html"'
    }
    variable = "TEMP" if same_variable else "OTHER_TEMP"
    read["tool_calls"][0]["arguments"] = {
        "command": "const html = fs.readFileSync(process.env."
        + variable
        + "+'\\\\trending.html', 'utf8'); parse(html);"
    }
    rows = [
        {
            "rank": rank,
            "path": f"/fixture-org-{rank}/fixture-repo-{rank}",
            "name": f"fixture-org-{rank} / fixture-repo-{rank}",
            "desc": f"Source description {rank}",
        }
        for rank in range(1, 11)
    ]
    read["observation"]["results"][0]["content"] = (
        "article tags: 10\nBox-row article: 10\n"
        + "\n".join(json.dumps(row) for row in rows)
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    checks = grade(verifier, runtime, config)[1]
    assert checks["custom:github_repository_10"]["passed"] is same_variable
    if same_variable:
        evidence = (
            Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
        ).read_text(encoding="utf-8")
        assert "article tags: 10" in evidence and "Source description 10" in evidence


@pytest.mark.parametrize("kind", ["github", "raw", "unrelated", "failed"])
def test_github_sources_include_only_selected_repository_support(
    tmp_path, verifier, kind
):
    runtime, config, path, data, _ = _github_saved_page(tmp_path)
    repo = "fixture-org-1/fixture-repo-1" + (
        "-unrelated" if kind == "unrelated" else ""
    )
    url = (
        f"https://raw.githubusercontent.com/{repo}/main/README.md"
        if kind == "raw"
        else f"https://github.com/{repo}"
    )
    fetch = json.loads(json.dumps(data["steps"][2]))
    fetch["step_id"] = 4
    fetch["tool_calls"][0].update(
        tool_call_id="repo-fetch",
        arguments={"command": f'curl "{url}" -o /tmp/repo.html'},
    )
    fetch["observation"]["results"][0].update(
        source_call_id="repo-fetch",
        content="200 bytes saved",
        extra={"exit_code": 1 if kind == "failed" else 0},
    )
    read = json.loads(json.dumps(fetch))
    read["step_id"] = 5
    read["tool_calls"][0].update(
        tool_call_id="repo-read",
        function_name="Read",
        arguments={"file_path": "/tmp/repo.html"},
    )
    read["observation"]["results"][0].update(
        source_call_id="repo-read",
        content="README supporting facts <&>",
        extra={"exit_code": 0},
    )
    data["steps"][3:3] = [fetch, read]
    data["steps"][-1]["step_id"] = 6
    path.write_text(json.dumps(data), encoding="utf-8")
    assert grade(verifier, runtime, config)[0]["reward"] == 1
    text = (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").read_text(
        encoding="utf-8"
    )
    assert ("README supporting facts <&>" in text) is (kind in {"github", "raw"})


def test_github_json_wrapped_urls_remain_source_evidence(verifier):
    urls = [f"https://github.com/owner/repo-{rank}" for rank in range(10)]
    assert (
        verifier.github_repositories(json.dumps({"content": "\n".join(urls)})) == urls
    )


def test_github_collection_does_not_copy_trajectory_per_call(
    tmp_path, verifier, monkeypatch
):
    from harbor.models.trajectories import Step, Trajectory

    runtime, config, path, data, _ = _github_saved_page(tmp_path)
    for index in range(200):
        data["steps"].insert(
            -1,
            {
                "step_id": index + 4,
                "source": "agent",
                "message": "",
                "tool_calls": [
                    {
                        "tool_call_id": f"noise-{index}",
                        "function_name": "Bash",
                        "arguments": {"command": "echo diagnostic"},
                    }
                ],
                "observation": {
                    "results": [
                        {
                            "source_call_id": f"noise-{index}",
                            "content": "diagnostic",
                            "extra": {"exit_code": 0},
                        }
                    ]
                },
            },
        )
    data["steps"][-1]["step_id"] = 204
    path.write_text(json.dumps(data), encoding="utf-8")
    counts = {"step": 0, "trajectory": 0}
    original_step, original_trajectory = Step.model_copy, Trajectory.model_copy

    def step_copy(self, **kwargs):
        counts["step"] += 1
        return original_step(self, **kwargs)

    def trajectory_copy(self, **kwargs):
        counts["trajectory"] += 1
        return original_trajectory(self, **kwargs)

    monkeypatch.setattr(Step, "model_copy", step_copy)
    monkeypatch.setattr(Trajectory, "model_copy", trajectory_copy)
    verifier.check_outputs(runtime.to_dict(), config, now=NOW)
    assert counts["step"] == 0
    assert counts["trajectory"] <= 1


@pytest.mark.parametrize("incomplete", [False, True])
def test_github_linked_source_reaches_xml_judge_and_is_regenerated(
    tmp_path, monkeypatch, incomplete
):
    import asyncio
    from dataclasses import replace
    from html import escape

    from psycheval.harbor.verifier import JudgeSettings, run_verifier
    from tests.fixtures.judge_server import judge_server

    runtime, _, path, data, _ = _github_saved_page(tmp_path)
    path.write_text(json.dumps(data), encoding="utf-8")
    tests = tmp_path / "isolated tests"
    shutil.copytree(TASK_ROOT / "tests", tests)
    shutil.copytree(TASK_ROOT / "steps/github/tests", tests, dirs_exist_ok=True)
    runtime = replace(runtime, paths=replace(runtime.paths, tests=str(tests)))
    monkeypatch.setenv("PBENCH_TREND_NOW", NOW.isoformat())
    with judge_server() as server:
        server["behavior"]["summary_faithfulness"] = (
            {"content": "invalid protocol"} if incomplete else {"passed": False}
        )
        settings = JudgeSettings(True, server["url"], "fixture")
        result = asyncio.run(
            run_verifier(
                tests / "grader.json", runtime=runtime, judge_settings=settings
            )
        )
        assert result["test_pass_rate"] == 1
        assert result["metadata"]["score_merge"]["applied"] is not incomplete
        assert result["reward"] == pytest.approx(
            1 if incomplete else 0.35 + 0.65 * 2 / 3
        )
        sources = Path(runtime.paths.verifier_logs) / "artifact_text/sources.md"
        text = sources.read_bytes().decode("utf-8")
        assert len(server["requests"]) == 3
        for request in server["requests"]:
            prompt = request["messages"][-1]["content"]
            assert "<artifact_faithful_text>" in prompt
            assert escape(text, quote=False) in prompt
            assert "read-page" in prompt and "Source description 10" in prompt

        data["steps"][2]["observation"]["results"][0]["extra"]["exit_code"] = 1
        path.write_text(json.dumps(data), encoding="utf-8")
        asyncio.run(
            run_verifier(
                tests / "grader.json", runtime=runtime, judge_settings=settings
            )
        )
        assert not sources.exists()
        assert (
            len(server["requests"]) == 3
        )  # Missing evidence is a local rubric failure.


def test_github_source_bodies_are_deduplicated_with_all_provenance(tmp_path, verifier):
    runtime, config, path, data, _ = _github_saved_page(tmp_path)
    repeated = json.loads(json.dumps(data["steps"][2]))
    repeated["step_id"] = 4
    repeated["tool_calls"][0]["tool_call_id"] = "read-again"
    repeated["observation"]["results"][0]["source_call_id"] = "read-again"
    data["steps"].insert(3, repeated)
    for index, step in enumerate(data["steps"], 1):
        step["step_id"] = index
    path.write_text(json.dumps(data), encoding="utf-8")
    verifier.check_outputs(runtime.to_dict(), config, now=NOW)
    text = (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").read_text(
        encoding="utf-8"
    )
    assert text.count("Source description 10") == 1
    assert "Evidence call: read-page" in text and "Evidence call: read-again" in text


def test_oversized_github_sources_are_explicit_unavailable_evidence(
    tmp_path, monkeypatch
):
    import asyncio
    from dataclasses import replace

    from psycheval.harbor.verifier import JudgeSettings, run_verifier
    from tests.fixtures.judge_server import judge_server

    runtime, _, path, data, _ = _github_saved_page(tmp_path)
    observation = data["steps"][2]["observation"]["results"][0]
    observation["content"] = observation["content"].replace(
        "\n\nStderr:", "\n" + "x" * (1024 * 1024) + "\n\nStderr:"
    )
    path.write_text(json.dumps(data), encoding="utf-8")
    tests = tmp_path / "isolated tests"
    shutil.copytree(TASK_ROOT / "tests", tests)
    shutil.copytree(TASK_ROOT / "steps/github/tests", tests, dirs_exist_ok=True)
    runtime = replace(runtime, paths=replace(runtime.paths, tests=str(tests)))
    monkeypatch.setenv("PBENCH_TREND_NOW", NOW.isoformat())
    with judge_server() as server:
        result = asyncio.run(
            run_verifier(
                tests / "grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "fixture"),
            )
        )
        assert result["test_pass_rate"] == 1
        assert result["metadata"]["score_merge"]["applied"] is True
        assert result["reward"] == pytest.approx(0.35)
        assert server["requests"] == []
    logs = Path(runtime.paths.verifier_logs)
    manifest = json.loads((logs / "artifact_manifest.json").read_text(encoding="utf-8"))
    source = next(item for item in manifest["artifacts"] if item["id"] == "sources")
    assert source["extract_status"] == "error" and "budget" in source["reason"]
    assert not (logs / "artifact_text/sources.md").exists()
    assert (logs / "artifact_text/report.md").exists()


def test_github_local_read_is_not_a_source_fetch(tmp_path, verifier):
    runtime, config, _, _ = make_case(tmp_path, "github")
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["steps"][1]["tool_calls"][0]["function_name"] = "read"
    path.write_text(json.dumps(data), encoding="utf-8")
    rewards, _ = grade(verifier, runtime, config)
    assert rewards["required_tool"] == 0
    assert rewards["required_observation"] == 0


@pytest.mark.parametrize("tool_name", ["WebFetch", "WEB-FETCH", "web_fetch"])
def test_webfetch_spellings_preserve_github_source_gates(tmp_path, verifier, tool_name):
    runtime, config, _, _ = make_case(tmp_path, "github")
    path = Path(runtime.paths.agent_logs) / "trajectory.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["steps"][1]["tool_calls"][0]["function_name"] = tool_name
    path.write_text(json.dumps(data), encoding="utf-8")
    rewards, _ = grade(verifier, runtime, config)
    assert rewards["required_arguments"] == 1
    assert rewards["required_observation"] == 1
    assert rewards["reward"] == 1
    assert (Path(runtime.paths.verifier_logs) / "artifact_text/sources.md").is_file()
