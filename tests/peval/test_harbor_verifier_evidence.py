from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import psycheval.state.harbor_verifier_evidence as verifier_evidence_module
from psycheval.state.harbor_verifier_evidence import (
    open_harbor_verifier_artifact_download,
    read_harbor_verifier_artifact,
    read_harbor_verifier_evidence,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_projects_canonical_score_verdicts_and_safe_artifacts(tmp_path: Path) -> None:
    trial = tmp_path / "job" / "task__1"
    verifier = trial / "verifier"
    (verifier / "artifact_text").mkdir(parents=True)
    (verifier / "raw_artifacts").mkdir()
    (verifier / "artifact_text" / "report.md").write_text(
        "# Bounded evidence\n", encoding="utf-8"
    )
    (verifier / "raw_artifacts" / "chart.png").write_bytes(b"\x89PNG\r\n")
    _write_json(
        verifier / "score.json",
        {
            "reward": 0.7,
            "overall": 0.7,
            "test_pass_rate": 0.75,
            "tests_passed": 3,
            "tests_total": 4,
            "test_status": "passed",
            "failed_checks": ["private diagnostic"],
            "host_paths": {"workspace": "/secret/workspace"},
            "env": {"TOKEN": "secret"},
        },
    )
    _write_json(
        verifier / "llm_judge.json",
        {
            "judge_status": "completed",
            "llm_judge": 0.5,
            "raw_response": "secret model response",
            "rubrics": [
                {
                    "id": "quality",
                    "verdict": "pass",
                    "score": 1,
                    "reason": "private free-form response",
                }
            ],
        },
    )
    _write_json(
        verifier / "artifact_manifest.json",
        {
            "host_root": "/secret/workspace",
            "artifacts": [
                {
                    "id": "chart",
                    "source_path": "/secret/workspace/chart.png",
                    "verifier_raw_path": "raw_artifacts/chart.png",
                    "text_path": "artifact_text/report.md",
                    "type": "png",
                    "required": True,
                    "extract_status": "ok",
                    "producer": "private-command",
                }
            ],
        },
    )

    evidence = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=0.7,
    )
    payload = evidence.to_dict(include_artifacts=True)

    assert payload["score"] == 0.7
    assert payload["score_source"] == "reward"
    assert payload["harbor_reward"] == 0.7
    assert payload["reward_consistency"] == "matched"
    assert payload["tests"] == {"passed": 3, "total": 4, "status": "passed"}
    assert payload["llm_judge"] == {
        "status": "completed",
        "score": 0.5,
        "rubrics": [{"id": "quality", "verdict": "pass", "score": 1.0}],
    }
    assert payload["artifacts"] == [
        {
            "id": "313bd5ab8c6dabcbcd16fda3",
            "name": "chart",
            "type": "png",
            "required": True,
            "status": "ok",
            "preview": {"kind": "text"},
            "download_available": True,
        }
    ]
    serialized = json.dumps(payload)
    for forbidden in (
        "/secret/workspace",
        "TOKEN",
        "secret model response",
        "private free-form response",
        "private diagnostic",
        "private-command",
    ):
        assert forbidden not in serialized

    artifact = read_harbor_verifier_artifact(
        trial,
        containment_root=tmp_path,
        artifact_id=payload["artifacts"][0]["id"],
        purpose="preview",
    )
    assert artifact.media_type == "text/markdown; charset=utf-8"
    assert artifact.content == b"# Bounded evidence\n"

    download = read_harbor_verifier_artifact(
        trial,
        containment_root=tmp_path,
        artifact_id=payload["artifacts"][0]["id"],
        purpose="download",
    )
    assert download.media_type == "image/png"
    assert download.content == b"\x89PNG\r\n"

    streamed = open_harbor_verifier_artifact_download(
        trial,
        containment_root=tmp_path,
        artifact_id=payload["artifacts"][0]["id"],
    )
    assert streamed.media_type == "image/png"
    assert streamed.size == 6
    assert b"".join(streamed.chunks) == b"\x89PNG\r\n"
    streamed.close()


def test_evidence_projection_does_not_read_artifact_payloads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trial = tmp_path / "task__1"
    verifier = trial / "verifier"
    (verifier / "artifact_text").mkdir(parents=True)
    (verifier / "raw_artifacts").mkdir()
    (verifier / "artifact_text" / "report.md").write_text(
        "# large report\n", encoding="utf-8"
    )
    (verifier / "raw_artifacts" / "payload.bin").write_bytes(b"payload")
    _write_json(verifier / "score.json", {"reward": 1})
    _write_json(
        verifier / "artifact_manifest.json",
        {
            "artifacts": [
                {
                    "id": "report",
                    "text_path": "artifact_text/report.md",
                    "verifier_raw_path": "raw_artifacts/payload.bin",
                }
            ]
        },
    )
    original = verifier_evidence_module._read_regular
    reads: list[str] = []

    def record_read(root: Path, path: Path, *, max_bytes: int) -> bytes:
        reads.append(path.name)
        return original(root, path, max_bytes=max_bytes)

    monkeypatch.setattr(verifier_evidence_module, "_read_regular", record_read)

    evidence = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=1,
    )

    assert reads == ["score.json", "artifact_manifest.json", "llm_judge.json"]
    assert evidence.artifacts[0]["preview"] == {"kind": "text"}


@pytest.mark.parametrize(
    ("score", "harbor_reward", "expected_score", "source", "consistency"),
    [
        ({"overall": 0.4}, 0.5, 0.4, "overall", "drifted"),
        ({"test_pass_rate": 0.25}, None, 0.25, "test_pass_rate", "missing"),
        (
            {"tests_passed": 2, "tests_total": 5},
            0.4,
            0.4,
            "tests_passed_over_tests_total",
            "matched",
        ),
        ({"reward": 1, "test_status": "build_error"}, 0, 0.0, "build_error", "matched"),
    ],
)
def test_score_precedence_and_consistency(
    tmp_path: Path,
    score: dict[str, object],
    harbor_reward: float | None,
    expected_score: float,
    source: str,
    consistency: str,
) -> None:
    trial = tmp_path / "task__1"
    _write_json(trial / "verifier" / "score.json", score)

    evidence = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=harbor_reward,
    )

    assert evidence.score == expected_score
    assert evidence.score_source == source
    assert evidence.reward_consistency == consistency


def test_missing_or_malformed_workbuddy_score_is_zero(tmp_path: Path) -> None:
    trial = tmp_path / "task__1"
    trial.mkdir()
    missing = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=None,
    )
    assert (missing.score, missing.score_source) == (0.0, "missing")

    score_path = trial / "verifier" / "score.json"
    score_path.parent.mkdir()
    score_path.write_text("{", encoding="utf-8")
    malformed = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=1,
    )
    assert (malformed.score, malformed.score_source) == (0.0, "malformed")
    assert malformed.reward_consistency == "malformed"
    assert malformed.warnings


@pytest.mark.parametrize("value", (float("nan"), float("inf"), -float("inf")))
def test_non_finite_workbuddy_scores_are_malformed(
    tmp_path: Path, value: float
) -> None:
    trial = tmp_path / "task__1"
    _write_json(trial / "verifier" / "score.json", {"reward": value})

    evidence = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=value,
    )

    assert (evidence.score, evidence.score_source) == (0.0, "malformed")
    assert evidence.harbor_reward is None
    assert evidence.reward_consistency == "missing"


def test_generic_harbor_evidence_does_not_synthesize_a_missing_score(
    tmp_path: Path,
) -> None:
    trial = tmp_path / "task__1"
    trial.mkdir()

    evidence = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="harbor",
        harbor_reward=None,
    )

    assert evidence.status == "missing"
    assert evidence.score is None
    assert evidence.score_source is None


def test_manifest_cannot_escape_or_traverse_a_symlink(tmp_path: Path) -> None:
    trial = tmp_path / "task__1"
    verifier = trial / "verifier"
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    (verifier / "artifact_text").mkdir(parents=True)
    os.symlink(outside, verifier / "artifact_text" / "linked.txt")
    _write_json(verifier / "score.json", {"reward": 1})
    _write_json(
        verifier / "artifact_manifest.json",
        {
            "artifacts": [
                {"id": "escape", "text_path": "../outside.txt"},
                {"id": "link", "text_path": "artifact_text/linked.txt"},
            ]
        },
    )

    evidence = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=1,
    )

    assert evidence.artifacts == ()
    assert len(evidence.warnings) == 2
    with pytest.raises(ValueError, match="unknown verifier artifact"):
        read_harbor_verifier_artifact(
            trial,
            containment_root=tmp_path,
            artifact_id="not-an-id",
            purpose="download",
        )


def test_manifest_artifact_reads_share_an_aggregate_byte_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trial = tmp_path / "task__1"
    verifier = trial / "verifier"
    artifacts = verifier / "raw_artifacts"
    artifacts.mkdir(parents=True)
    (artifacts / "one.bin").write_bytes(b"1234")
    (artifacts / "two.bin").write_bytes(b"5678")
    _write_json(verifier / "score.json", {"reward": 1})
    _write_json(
        verifier / "artifact_manifest.json",
        {
            "artifacts": [
                {"id": "one", "verifier_raw_path": "raw_artifacts/one.bin"},
                {"id": "two", "verifier_raw_path": "raw_artifacts/two.bin"},
            ]
        },
    )
    monkeypatch.setattr(verifier_evidence_module, "ARTIFACT_TOTAL_MAX_BYTES", 5)

    evidence = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=1,
    )

    assert [item["name"] for item in evidence.artifacts] == ["one"]
    assert evidence.warnings == (
        "artifact 2 ignored: verifier evidence exceeds 1 bytes: two.bin",
    )


def test_artifact_download_name_does_not_copy_unsafe_path_suffix(
    tmp_path: Path,
) -> None:
    trial = tmp_path / "task__1"
    verifier = trial / "verifier"
    artifacts = verifier / "raw_artifacts"
    artifacts.mkdir(parents=True)
    unsafe_name = "result.\r\nX-Evil"
    (artifacts / unsafe_name).write_bytes(b"fixture")
    _write_json(
        verifier / "artifact_manifest.json",
        {
            "artifacts": [
                {
                    "id": "report",
                    "verifier_raw_path": f"raw_artifacts/{unsafe_name}",
                }
            ]
        },
    )
    evidence = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=None,
    )

    artifact = read_harbor_verifier_artifact(
        trial,
        containment_root=tmp_path,
        artifact_id=evidence.artifacts[0]["id"],
        purpose="download",
    )

    assert artifact.filename == "report"


@pytest.mark.parametrize("suffix", (".html", ".svg", ".js"))
def test_active_content_artifacts_are_not_inline_previewable(
    tmp_path: Path, suffix: str
) -> None:
    trial = tmp_path / "task__1"
    verifier = trial / "verifier"
    artifacts = verifier / "artifact_text"
    artifacts.mkdir(parents=True)
    path = artifacts / f"active{suffix}"
    path.write_text("<script>globalThis.pwned = true</script>", encoding="utf-8")
    _write_json(
        verifier / "artifact_manifest.json",
        {"artifacts": [{"id": "active", "text_path": f"artifact_text/{path.name}"}]},
    )
    evidence = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=None,
    )

    with pytest.raises(ValueError, match="not previewable"):
        read_harbor_verifier_artifact(
            trial,
            containment_root=tmp_path,
            artifact_id=evidence.artifacts[0]["id"],
            purpose="preview",
        )


def test_unreadable_optional_evidence_is_projected_as_a_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trial = tmp_path / "task__1"
    verifier = trial / "verifier"
    _write_json(verifier / "score.json", {"reward": 1})
    original = verifier_evidence_module._read_regular

    def unreadable_score(root: Path, path: Path, *, max_bytes: int) -> bytes:
        if path.name == "score.json":
            raise PermissionError("permission denied")
        return original(root, path, max_bytes=max_bytes)

    monkeypatch.setattr(verifier_evidence_module, "_read_regular", unreadable_score)

    evidence = read_harbor_verifier_evidence(
        trial,
        containment_root=tmp_path,
        dataset_format="workbuddy.v1",
        harbor_reward=1,
    )

    assert evidence.status == "malformed"
    assert evidence.score == 0
    assert evidence.warnings == ("verifier score ignored: permission denied",)
