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


def test_declared_rule_items_match_scoring_and_preserve_rubric_lists(tmp_path):
    task(tmp_path)
    write(
        tmp_path,
        "tests/grader.json",
        json.dumps(
            {
                "required_calls": [{"any": [{"tool_names": ["web_search"]}]}],
                "custom_checks": ["answer"],
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


def test_steps_override_whole_files_and_shared_items_count_per_step(tmp_path):
    task(tmp_path, ("second", "first", "last"))
    write(tmp_path, "tests/grader.json", '{"custom_checks":["shared"]}')
    write(tmp_path, "steps/first/tests/grader.json", '{"custom_checks":["one","two"]}')
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
