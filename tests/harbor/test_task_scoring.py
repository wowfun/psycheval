import json

import pytest

from psycheval.harbor.task_scoring import scoring_file_preview, task_scoring_inventory
from tests.fixtures.judge_task import YAML


def write(root, name, content):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def task(root, steps=()):
    write(
        root,
        "task.toml",
        'schema_version = "1.3"\n[task]\nname = "suite/example"\nkeywords = ["中文", "office"]\n'
        + "".join(f'[[steps]]\nname = "{step}"\n' for step in steps),
    )
    for step in steps or ("",):
        write(
            root,
            f"steps/{step}/instruction.md" if step else "instruction.md",
            f"# {step or 'Task'}\nFull instruction",
        )


def inventory(root, **kwargs):
    return task_scoring_inventory(root, read_bytes=lambda p: p.read_bytes(), **kwargs)


def test_summary_metadata_uses_declared_fields_and_keeps_missing_labels(tmp_path):
    task(tmp_path)
    assert inventory(tmp_path)["category"] is None
    assert inventory(tmp_path)["difficulty"] is None
    assert inventory(tmp_path)["custom_metadata"] == {}
    with (tmp_path / "task.toml").open("a", encoding="utf-8") as source:
        source.write(
            '\n[metadata]\ncategory = "coding"\ndifficulty = "hard"\n'
            'source_case = "reserved-id"\nqa_status = "OK"\npriority = 2\n'
            'verified = true\n"质检项" = ["不漏", "不重"]\n'
        )
    result = inventory(tmp_path)
    assert result["category"] == "coding"
    assert result["difficulty"] == "hard"
    assert result["tags"] == ["中文", "office"]
    assert result["custom_metadata"] == {
        "qa_status": "OK",
        "priority": 2,
        "verified": True,
        "质检项": ["不漏", "不重"],
    }


def test_declared_rule_items_match_scoring_and_preserve_rubric_lists(tmp_path):
    task(tmp_path)
    write(
        tmp_path,
        "tests/grader.json",
        json.dumps(
            {
                "required_calls": [{"any": [{"tool_names": ["web_search"]}]}],
                "custom_checks": ["answer"],
                "scoring": {
                    "descriptions": {"custom:answer": "核对最终回复中的结论。"}
                },
            }
        ),
    )
    write(tmp_path, "tests/judge.yaml", YAML)
    value = inventory(tmp_path)
    assert value["tags"] == ["中文", "office"]
    assert value["instruction"] == (tmp_path / "instruction.md").read_bytes().decode(
        "utf-8"
    )
    assert (
        value["rule_count"],
        value["rubric_count"],
        value["scoring_item_count"],
    ) == (5, 1, 6)
    assert [item["id"] for item in value["scoring_items"][:3]] == [
        "required_call_1_tool",
        "required_call_1_arguments",
        "required_call_1_observation",
    ]
    assert value["scoring_items"][-1]["artifact_refs"] == ["report"]
    assert "question" not in value["scoring_items"][0]
    assert value["scoring_items"][-2]["question"] == "核对最终回复中的结论。"
    path = "tests/grader.json"
    preview = scoring_file_preview(path, (tmp_path / path).read_text(encoding="utf-8"))
    assert preview["items"][-1]["description"] == "核对最终回复中的结论。"
    assert preview["items"][0]["description"] is None


def test_steps_override_whole_files_and_shared_items_count_per_step(tmp_path):
    task(tmp_path, ("second", "first", "last"))
    write(
        tmp_path,
        "tests/grader.json",
        '{"custom_checks":["shared"], "scoring":{"descriptions":{"custom:shared":"Shared rule"}}}',
    )
    write(
        tmp_path,
        "steps/first/tests/grader.json",
        '{"custom_checks":["shared","two"], "scoring":{"descriptions":{"custom:shared":"Step rule"}}}',
    )
    write(tmp_path, "tests/judge.yaml", YAML)
    reads = []

    def read(path):
        reads.append(path)
        return path.read_bytes()

    value = task_scoring_inventory(tmp_path, read_bytes=read)
    assert value["instruction_path"] == "steps/second/instruction.md"
    assert (
        value["rule_count"],
        value["rubric_count"],
        value["scoring_item_count"],
    ) == (4, 3, 7)
    assert len({item["key"] for item in value["scoring_items"]}) == 7
    assert {
        item["step"]: item["question"]
        for item in value["scoring_items"]
        if item["id"] == "custom:shared"
    } == {"second": "Shared rule", "first": "Step rule", "last": "Shared rule"}
    assert reads.count(tmp_path / "tests/judge.yaml") == 1
    assert value["scoring_paths"]["rule"] == "tests/grader.json"
    write(tmp_path, "steps/second/tests/judge.yaml", "bad: config")
    value = inventory(tmp_path)
    assert value["rubric_count"] is None and value["scoring_item_count"] is None
    assert (
        len([item for item in value["scoring_items"] if item["type"] == "rubric"]) == 2
    )


def test_missing_is_zero_but_malformed_is_unknown(tmp_path):
    task(tmp_path)
    assert inventory(tmp_path)["scoring_item_count"] == 0
    write(tmp_path, "tests/grader.json", "not json")
    value = inventory(tmp_path)
    assert value["rule_count"] is None
    assert value["rubric_count"] == 0
    assert value["scoring_diagnostics"]


def test_continuation_preview_preserves_references_without_extra_scoring_items(
    tmp_path,
):
    task(tmp_path)
    config = {
        "custom_checks": ["content", "delivery"],
        "scoring": {"weights": {"custom:delivery": 0}},
        "continuation_checks": ["custom:delivery"],
    }
    content = json.dumps(config)
    write(tmp_path, "tests/grader.json", content)
    preview = scoring_file_preview("tests/grader.json", content)
    assert preview["config"] == config
    assert [item["id"] for item in preview["items"]] == [
        "custom:content",
        "custom:delivery",
    ]
    assert preview["items"][1]["weight"] == 0
    value = inventory(tmp_path)
    assert value["rule_count"] == value["scoring_item_count"] == 2
    assert not value["scoring_diagnostics"]
    config["continuation_checks"] = ["custom:unknown"]
    write(tmp_path, "tests/grader.json", json.dumps(config))
    value = inventory(tmp_path)
    assert value["rule_count"] is None
    assert "continuation_checks" in value["scoring_diagnostics"][0]


def test_office_extended_metadata_is_read_without_executing_any_code(tmp_path):
    task(tmp_path)
    write(
        tmp_path, "tests/grading/eval_core.py", 'raise RuntimeError("must not execute")'
    )
    write(
        tmp_path, "tests/judge.yaml", YAML + "\nactivation_policy: {mode: optional}\n"
    )
    value = inventory(tmp_path, format="workbuddy.v1")
    assert value["rule_count"] is None and value["scoring_item_count"] is None
    assert value["rubric_count"] == 1
    assert [item["type"] for item in value["scoring_items"]] == ["rubric"]
    write(tmp_path, "tests/grader.json", '{"custom_checks":["dynamic-group"]}')
    value = inventory(tmp_path, format="workbuddy.v1")
    assert value["scoring_paths"]["rule"] == "tests/grader.json"
    assert value["rule_count"] is None
    assert [item["type"] for item in value["scoring_items"]] == ["rubric"]
    preview = scoring_file_preview(
        "tests/judge.yaml",
        YAML + "\nactivation_policy: {mode: optional}\n",
        format="workbuddy.v1",
    )
    assert preview["config"]["activation_policy"] == {"mode": "optional"}
    with pytest.raises(ValueError):
        scoring_file_preview("tests/judge.yaml", "a: &a [*a]", format="workbuddy.v1")


def test_office_metadata_expansion_is_bounded():
    content = (
        YAML
        + "\nchunk: &chunk "
        + "x" * 512
        + "\nmetadata: ["
        + ",".join(["*chunk"] * 5000)
        + "]"
    )
    with pytest.raises(ValueError, match="Invalid WorkBuddy Judge metadata"):
        scoring_file_preview("tests/judge.yaml", content, format="workbuddy.v1")


def test_office_rubric_count_is_bounded_independently_of_source_size():
    from psycheval.harbor.task_scoring import MAX_OFFICE_RUBRICS

    content = json.dumps(
        {
            "llm_judge": {
                "rubrics": [
                    {"id": str(i), "question": "q"}
                    for i in range(MAX_OFFICE_RUBRICS + 1)
                ]
            }
        }
    )
    with pytest.raises(ValueError, match="exceeds.*rubrics"):
        scoring_file_preview("tests/judge.yaml", content, format="workbuddy.v1")
