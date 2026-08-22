from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from harbor.models.trajectories import Trajectory

from psycheval.atif import convert_records
from psycheval.config import ToolConfig
from psycheval.sources import read_jsonl

ROOT = Path(__file__).resolve().parents[2]


def test_explicit_null_content_union_conforms_to_public_harbor_validator() -> None:
    trajectory = {
        "schema_version": "ATIF-v1.7",
        "trajectory_id": "agent:content-null",
        "session_id": "content-null",
        "agent": {"name": "agent", "version": "1.0"},
        "steps": [
            {
                "step_id": 1,
                "source": "user",
                "message": [
                    {"type": "text", "text": "caption", "source": None},
                    {
                        "type": "image",
                        "text": None,
                        "source": {
                            "media_type": "image/png",
                            "path": "screen.png",
                        },
                    },
                ],
            }
        ],
        "final_metrics": {"total_steps": 1},
    }

    validated = Trajectory.model_validate(trajectory)

    assert validated.steps[0].message[0].source is None
    assert validated.steps[0].message[1].text is None


@pytest.mark.parametrize("adapter", ["psychevo", "opencode", "hermes", "deepagents"])
def test_representative_peval_export_conforms_to_public_harbor_validator(
    adapter: str,
) -> None:
    records = [
        replace(record, source_session_id="sess-common")
        for record in read_jsonl(
            str(ROOT / "tests/peval/fixtures/common_session.jsonl")
        )
    ]

    converted = convert_records(records, ToolConfig(adapter=adapter, redact=False))

    validated = Trajectory.model_validate(converted.trajectory)
    assert validated.schema_version == "ATIF-v1.7"
    assert validated.trajectory_id == f"{adapter}:sess-common"
