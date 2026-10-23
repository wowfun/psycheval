from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from psycheval.harbor.verifier import JudgeSettings, _judge_evidence, run_verifier
from psycheval.harbor.verifier._judge import (
    clear_judge_outputs,
    merge_scores,
    run_verifier_judge,
)
from psycheval.harbor.verifier._judge_config import parse_judge_config
from psycheval.harbor.verifier._judge_evidence import TEXT_TYPES, read_evidence
from tests.fixtures.judge_server import judge_server
from tests.fixtures.judge_task import YAML, api_task, runtime


def manifest(logs, *records):
    (logs / "artifact_manifest.json").write_text(
        json.dumps({"artifacts": records}, ensure_ascii=False), encoding="utf-8"
    )


def extracted_record(**overrides):
    return {
        "id": "report",
        "source_path": "output/report.xlsx",
        "text_path": "artifact_text/中文 报告.md",
        "extract_status": "ok",
        "type": "xlsx",
        "producer": "task-owned",
        **overrides,
    }


def assess(context, config=None, **settings):
    with judge_server() as server:
        result = asyncio.run(
            run_verifier_judge(
                config or parse_judge_config(YAML),
                context,
                JudgeSettings(True, server["url"], "fixture", **settings),
            )
        )
        return result, server["requests"]


def test_text_types_match_local_office_reference():
    reference = (
        Path(__file__).resolve().parents[2]
        / ".references/workbuddy-bench/wb-bench-office-v1.0/shared/verifier/llm.py"
    )
    if not reference.is_file():
        pytest.skip("optional local WorkBuddy Office reference is unavailable")
    tree = ast.parse(reference.read_text(encoding="utf-8"))
    definitions = [
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_TEXT_LIKE_TYPES"
            for target in node.targets
        )
    ]
    assert len(definitions) == 1, "Office text-type declaration changed"
    # Inspect the reference without importing its plugins or runtime dependencies.
    assert TEXT_TYPES == ast.literal_eval(definitions[0])


@pytest.mark.parametrize("kind", ["text", ".MARKDOWN", "yml", "xml", "py", "source"])
def test_office_text_types_and_values_are_preserved(tmp_path, kind):
    value = yaml.safe_load(YAML)
    value["artifacts"][0]["type"] = kind
    config = parse_judge_config(yaml.safe_dump(value))
    assert config.to_dict()["artifacts"] == value["artifacts"]
    result, requests = assess(runtime(tmp_path), config)
    assert result["checks"][0]["passed"] and len(requests) == 1


@pytest.mark.parametrize("source", ["workdir", "tests", "verifier_logs"])
def test_source_field_is_rejected(source):
    value = yaml.safe_load(YAML)
    value["artifacts"][0]["source"] = source
    with pytest.raises(ValueError, match="fields"):
        parse_judge_config(yaml.safe_dump(value))


def test_thirty_six_office_declarations_load_without_conversion():
    value = yaml.safe_load(YAML)
    value["artifacts"].extend(
        {"id": f"item{i}", "path": f"output/{i}.xlsx", "required": True, "type": "xlsx"}
        for i in range(35)
    )
    assert (
        parse_judge_config(yaml.safe_dump(value)).to_dict()["artifacts"]
        == value["artifacts"]
    )


@pytest.mark.parametrize("kind", ["md", "xlsx", "pdf"])
def test_manifest_precedes_declared_path_and_uses_only_declared_records(tmp_path, kind):
    context = runtime(tmp_path)
    logs = Path(context.paths.verifier_logs)
    target = logs / "artifact_text/中文 报告.md"
    target.parent.mkdir()
    target.write_text("提取证据\n{context}", encoding="utf-8", newline="")
    config = parse_judge_config(YAML)
    config = replace(config, artifacts=(replace(config.artifacts[0], type=kind),))
    # The declaration still points to the different fixture text; source_path is
    # descriptive and the undeclared record must never read or spend the budget.
    manifest(
        logs,
        extracted_record(source_path="C:/private/original.xlsx", required=False),
        extracted_record(id="undeclared", text_path="../private.txt"),
    )
    result, requests = assess(context, config)
    assert result["checks"][0]["passed"]
    prompt = requests[0]["messages"][-1]["content"]
    assert "### Artifact report\n" in prompt
    assert "### Artifact undeclared\n" not in prompt
    assert (
        "Faithful text:\n<artifact_faithful_text>\n提取证据\n{context}\n"
        "</artifact_faithful_text>"
    ) in prompt
    metadata = json.loads(
        prompt.split("Metadata:\n", 1)[1].split("\n\nFaithful text:", 1)[0]
    )
    assert metadata == {
        "error": None,
        "required": True,
        "extract_status": "ok",
    }
    index = json.loads((logs / "judge/evidence.json").read_text(encoding="utf-8"))
    assert index == {
        "report": {
            "error": None,
            "required": True,
            "extract_status": "ok",
            "text_path": "artifact_text/中文 报告.md",
            "byte_count": len(target.read_bytes()),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
    }


@pytest.mark.parametrize("use_manifest", [False, True])
def test_evidence_index_fingerprints_the_same_read_without_copying_text(
    tmp_path, monkeypatch, use_manifest
):
    context = runtime(tmp_path)
    logs = Path(context.paths.verifier_logs)
    relative = "artifact_text/中文 报告.md" if use_manifest else "中文 报告.md"
    target = logs / relative
    target.parent.mkdir(exist_ok=True)
    raw = '中文 📰\r\n{"literal": "{context}"}\r\n'.encode("utf-8")
    target.write_bytes(raw)
    if use_manifest:
        manifest(logs, extracted_record())
    original = _judge_evidence._read_bytes
    reads = []

    def read_once(root, path, limit):
        reads.append(path)
        data = original(root, path, limit)
        if path == relative:
            target.write_text("changed after read", encoding="utf-8")
        return data

    monkeypatch.setattr(_judge_evidence, "_read_bytes", read_once)
    evidence, index = read_evidence(parse_judge_config(YAML), logs, 1024)
    assert reads == ["artifact_manifest.json", relative]
    assert evidence["report"]["text"] == raw.decode("utf-8")
    assert index["report"]["text_path"] == relative
    assert index["report"]["byte_count"] == len(raw)
    assert index["report"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert "text" not in index["report"]
    assert index["report"]["sha256"] != hashlib.sha256(target.read_bytes()).hexdigest()


@pytest.mark.parametrize("kind", ["xlsx", "pdf", "makrdown"])
@pytest.mark.parametrize("required", [True, False])
def test_nontext_declaration_does_not_read_original_without_manifest(
    tmp_path, kind, required
):
    context = runtime(tmp_path)
    config = parse_judge_config(YAML)
    config = replace(
        config, artifacts=(replace(config.artifacts[0], type=kind, required=required),)
    )
    result, requests = assess(context, config)
    assert result["status"] == "complete"
    assert result["checks"][0]["passed"] is not required
    assert bool(requests) is not required
    evidence, index = read_evidence(config, Path(context.paths.verifier_logs), 1024)
    assert evidence["report"]["extract_status"] == "missing"
    assert kind in evidence["report"]["error"]
    assert "manifest record" in evidence["report"]["error"]
    assert index["report"]["text_path"] is None
    assert index["report"]["byte_count"] is None
    assert index["report"]["sha256"] is None


@pytest.mark.parametrize(
    "record,required,called",
    [
        ({"extract_status": "missing"}, True, False),
        ({"extract_status": "missing"}, False, True),
        ({"extract_status": "error"}, True, False),
        ({"extract_status": "error"}, False, False),
        ({"extract_status": "unsupported"}, False, False),
        ({"text_path": None}, False, False),
        ({"text_path": "absent.md"}, False, False),
    ],
)
def test_manifest_record_prevents_fallback_even_for_optional_artifacts(
    tmp_path, record, required, called
):
    context = runtime(tmp_path)
    logs = Path(context.paths.verifier_logs)
    manifest(logs, extracted_record(**record))
    config = parse_judge_config(YAML)
    config = replace(
        config, artifacts=(replace(config.artifacts[0], required=required),)
    )
    result, requests = assess(context, config)
    assert result["status"] == "complete"
    assert result["checks"][0]["passed"] is called
    assert bool(requests) is called
    index = json.loads((logs / "judge/evidence.json").read_text(encoding="utf-8"))
    assert "text" not in index["report"]
    assert index["report"]["byte_count"] is None
    assert index["report"]["sha256"] is None


@pytest.mark.parametrize("required", [True, False])
def test_empty_text_has_office_required_semantics(tmp_path, required):
    context = runtime(tmp_path)
    (Path(context.paths.verifier_logs) / "中文 报告.md").write_text("")
    config = parse_judge_config(YAML)
    config = replace(
        config, artifacts=(replace(config.artifacts[0], required=required),)
    )
    result, requests = assess(context, config)
    assert result["checks"][0]["passed"] is not required
    assert bool(requests) is not required

    index = json.loads(
        (Path(context.paths.verifier_logs) / "judge/evidence.json").read_text(
            encoding="utf-8"
        )
    )
    assert index["report"]["text_path"] == "中文 报告.md"
    assert index["report"]["byte_count"] == 0
    assert index["report"]["sha256"] == hashlib.sha256(b"").hexdigest()


@pytest.mark.parametrize(
    "payload",
    [
        b"{",
        b"[]",
        b"{}",
        b'{"artifacts":{}}',
        b'{"artifacts":[null]}',
        b'{"artifacts":[{"id":7}]}',
        b'{"artifacts":[{"id":"report"},{"id":"report"}]}',
        b'{"artifacts":[],"artifacts":[]}',
        b'{"artifacts":[],"other":NaN}',
        b"\xff",
        b" " * (1024 * 1024 + 1),
    ],
    ids=[
        "syntax",
        "root",
        "missing-list",
        "list-type",
        "record-type",
        "id-type",
        "duplicate-id",
        "duplicate-key",
        "nonfinite",
        "encoding",
        "oversize",
    ],
)
def test_invalid_manifest_disables_judge_without_model_calls(tmp_path, payload):
    context = runtime(tmp_path)
    (Path(context.paths.verifier_logs) / "artifact_manifest.json").write_bytes(payload)
    config = parse_judge_config(YAML)
    result, requests = assess(context, config)
    rewards, decision = merge_scores({"reward": 0.75}, config, result)
    assert result["status"] == "incomplete" and "manifest" in result["reason"]
    assert not requests and not decision["applied"] and "llm_score" not in rewards
    assert rewards["reward"] == 0.75


def test_unreadable_manifest_disables_judge(tmp_path, monkeypatch):
    context = runtime(tmp_path)
    original = Path.open

    def denied(path, *args, **kwargs):
        if path.name == "artifact_manifest.json":
            raise PermissionError("synthetic access denial")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    manifest_path = Path(context.paths.verifier_logs) / "artifact_manifest.json"
    # The file must exist for the containment/type check to reach open().
    with original(manifest_path, "w") as stream:
        stream.write('{"artifacts":[]}')
    result, requests = assess(context)
    assert result["status"] == "incomplete" and "PermissionError" in result["reason"]
    assert not requests


@pytest.mark.parametrize(
    "relative",
    [
        "../private.txt",
        "/private.txt",
        "C:/private.txt",
        "a/../private.txt",
        "a\\private.txt",
        "",
        1,
    ],
)
def test_manifest_text_path_is_contained(tmp_path, relative):
    context = runtime(tmp_path)
    manifest(Path(context.paths.verifier_logs), extracted_record(text_path=relative))
    result, requests = assess(context)
    assert result["status"] == "complete" and not result["checks"][0]["passed"]
    assert not requests


@pytest.mark.parametrize("source", ["manifest text_path", "declared artifact path"])
def test_evidence_read_diagnostic_identifies_the_source(tmp_path, source):
    context = runtime(tmp_path)
    logs = Path(context.paths.verifier_logs)
    if source == "manifest text_path":
        manifest(logs, extracted_record(text_path="../private.txt"))
    else:
        (logs / "中文 报告.md").unlink()
    evidence, index = read_evidence(parse_judge_config(YAML), logs, 1024)
    assert source in evidence["report"]["error"]
    if source == "manifest text_path":
        assert "contained relative POSIX path" in evidence["report"]["error"]
        assert "judge artifact path" not in evidence["report"]["error"]
        assert evidence["report"]["extract_status"] == "error"
        assert index["report"]["text_path"] is None
    else:
        assert "FileNotFoundError" in evidence["report"]["error"]
        assert evidence["report"]["extract_status"] == "missing"
        assert index["report"]["text_path"] == "中文 报告.md"
    assert index["report"]["byte_count"] is None
    assert index["report"]["sha256"] is None


@pytest.mark.parametrize("location", ["manifest", "text", "parent"])
def test_evidence_links_are_not_followed(tmp_path, location):
    context = runtime(tmp_path)
    logs = Path(context.paths.verifier_logs)
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "keep.txt"
    sentinel.write_text("outside secret")
    try:
        if location == "manifest":
            (logs / "artifact_manifest.json").symlink_to(sentinel)
        elif location == "text":
            (logs / "linked.md").symlink_to(sentinel)
            manifest(logs, extracted_record(text_path="linked.md"))
        else:
            (logs / "linked").symlink_to(external, target_is_directory=True)
            manifest(logs, extracted_record(text_path="linked/keep.txt"))
    except OSError as exc:
        pytest.skip(f"native symlink creation unavailable: {exc}")
    result, requests = assess(context)
    assert not requests
    assert result["status"] == ("incomplete" if location == "manifest" else "complete")
    if location != "manifest":
        assert not result["checks"][0]["passed"]
    assert sentinel.read_text() == "outside secret"


def test_managed_output_cleanup_unlinks_without_touching_targets(tmp_path):
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "keep.txt"
    sentinel.write_text("preserve")
    logs = tmp_path / "logs"
    logs.mkdir()
    try:
        (logs / "artifact_manifest.json").symlink_to(sentinel)
        for name in (
            "judge",
            "artifact_text",
            "raw_artifacts",
            "judge_evidence",
            "judge-evidence",
        ):
            (logs / name).symlink_to(external, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"native symlink creation unavailable: {exc}")
    clear_judge_outputs(logs)
    assert list(logs.iterdir()) == []
    assert list(external.iterdir()) == [sentinel]
    assert sentinel.read_text() == "preserve"


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows junction")
@pytest.mark.parametrize("directory", ["artifact_text", "raw_artifacts"])
@pytest.mark.parametrize("owner", ["judge", "writer"])
def test_junction_evidence_is_rejected_and_cleanup_preserves_target(
    tmp_path, directory, owner
):
    context = runtime(tmp_path)
    logs = Path(context.paths.verifier_logs)
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "report.md"
    sentinel.write_text("must remain private")
    link = logs / directory
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(external)],
        capture_output=True,
        check=True,
    )
    try:
        manifest(logs, extracted_record(text_path=f"{directory}/report.md"))
        result, requests = assess(context)
        assert not requests and not result["checks"][0]["passed"]
        if owner == "judge":
            clear_judge_outputs(logs)
        else:
            from psycheval.harbor.evidence import EvidenceWriter

            with EvidenceWriter(logs):
                pass
        assert not link.exists() and not link.is_junction()
        assert sentinel.read_text() == "must remain private"
    finally:
        if link.is_junction():
            link.rmdir()


def test_public_api_uses_fresh_manifest_on_each_invocation(tmp_path):
    grader, context = api_task(tmp_path)
    declaration = yaml.safe_load(YAML)
    declaration["artifacts"][0].update(path="output/report.xlsx", type="xlsx")
    (grader.parent / "judge.yaml").write_text(
        yaml.safe_dump(declaration), encoding="utf-8"
    )
    (grader.parent / "test_outputs.py").write_text(
        """import json, sys
from pathlib import Path
context = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
logs = Path(context["paths"]["verifier_logs"])
assert not (logs / "artifact_manifest.json").exists()
assert not (logs / "artifact_text").exists()
source = Path(context["paths"]["workdir"]) / "source.txt"
if source.exists():
    (logs / "artifact_text").mkdir()
    (logs / "artifact_text/report.md").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (logs / "artifact_manifest.json").write_text(json.dumps({"artifacts": [{"id": "report", "text_path": "artifact_text/report.md", "extract_status": "ok"}]}))
Path(sys.argv[4]).write_text('{"checks":[{"id":"valid","passed":true}]}')
""",
        encoding="utf-8",
    )
    source = Path(context.paths.workdir) / "source.txt"
    source.write_text("current evidence", encoding="utf-8")
    with judge_server() as server:
        settings = JudgeSettings(True, server["url"], "fixture")
        first = asyncio.run(
            run_verifier(grader, runtime=context, judge_settings=settings)
        )
        source.unlink()
        second = asyncio.run(
            run_verifier(grader, runtime=context, judge_settings=settings)
        )
        assert len(server["requests"]) == 1
        assert "current evidence" in server["requests"][0]["messages"][-1]["content"]
    assert first["reward"] == 1
    assert second["reward"] == 0.8
    logs = Path(context.paths.verifier_logs)
    assert not (logs / "artifact_manifest.json").exists()
    assert json.loads((logs / "score.json").read_text(encoding="utf-8")) == second
