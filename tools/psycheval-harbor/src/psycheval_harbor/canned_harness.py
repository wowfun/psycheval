from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import Any

from harbor.utils.trajectory_validator import TrajectoryValidator

IANA_URL = "https://www.iana.org/help/example-domains"
SELENIUM_URL = "https://www.selenium.dev/selenium/web/web-form.html"
SELENIUM_RESULT_URL = "https://www.selenium.dev/selenium/web/submitted-form.html"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic web-agent fixture")
    parser.add_argument(
        "--scenario",
        choices=("web-search", "web-fetch", "browser-control"),
        required=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    instruction = sys.stdin.read()
    if not instruction.strip():
        raise SystemExit("canned harness received an empty instruction")
    logs_dir = Path(os.environ.get("PSYCHEVAL_AGENT_LOGS_DIR", "/logs/agent"))
    artifacts_dir = Path(os.environ.get("PSYCHEVAL_ARTIFACTS_DIR", "/logs/artifacts"))
    logs_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    trajectory = _trajectory(args.scenario, instruction, artifacts_dir)
    trajectory_path = logs_dir / "trajectory.json"
    trajectory_path.write_text(
        json.dumps(trajectory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    validator = TrajectoryValidator()
    if not validator.validate(trajectory_path):
        raise SystemExit(
            "fixture generated invalid ATIF: " + "; ".join(validator.errors)
        )
    return 0


def _trajectory(scenario: str, instruction: str, artifacts_dir: Path) -> dict[str, Any]:
    if scenario == "web-search":
        agent_steps = [
            _tool_step(
                2,
                "search-1",
                "web_search",
                {"query": "IANA example domains example.com example.org"},
                {
                    "items": [
                        {
                            "title": "Example Domains",
                            "url": IANA_URL,
                            "snippet": "IANA maintains example.com and example.org for documentation purposes.",
                        }
                    ]
                },
            ),
            {
                "step_id": 3,
                "source": "agent",
                "message": f"example.com and example.org — {IANA_URL}",
            },
        ]
    elif scenario == "web-fetch":
        agent_steps = [
            _tool_step(
                2,
                "fetch-1",
                "web_fetch",
                {"url": IANA_URL},
                {
                    "url": IANA_URL,
                    "status": 200,
                    "content": "Example Domains. Last revised 2017-05-13.",
                },
            ),
            {
                "step_id": 3,
                "source": "agent",
                "message": f"The page was last revised 2017-05-13. {IANA_URL}",
            },
        ]
    else:
        screenshot = artifacts_dir / "web-form-submitted.png"
        screenshot.write_bytes(
            base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            )
        )
        agent_steps = [
            _tool_step(
                2,
                "browser-1",
                "browser_navigate",
                {"url": SELENIUM_URL},
                {"url": SELENIUM_URL, "title": "Web form"},
            ),
            _tool_step(
                3,
                "browser-2",
                "browser_type",
                {"selector": "input[name='my-text']", "text": "Harbor eval"},
                {"value": "Harbor eval"},
            ),
            _tool_step(
                4,
                "browser-3",
                "browser_click",
                {"selector": "button"},
                {"url": SELENIUM_RESULT_URL, "message": "Received!"},
            ),
            {
                "step_id": 5,
                "source": "agent",
                "message": f"Received! Final URL: {SELENIUM_RESULT_URL}",
            },
        ]
    return {
        "schema_version": "ATIF-v1.7",
        "trajectory_id": f"canned:{scenario}",
        "agent": {"name": "psycheval-canned", "version": "0.1.0"},
        "steps": [
            {"step_id": 1, "source": "user", "message": instruction},
            *agent_steps,
        ],
    }


def _tool_step(
    step_id: int,
    call_id: str,
    function_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "source": "agent",
        "message": "",
        "tool_calls": [
            {
                "tool_call_id": call_id,
                "function_name": function_name,
                "arguments": arguments,
            }
        ],
        "observation": {
            "results": [
                {
                    "source_call_id": call_id,
                    "content": json.dumps(result, ensure_ascii=False, sort_keys=True),
                    "extra": {"is_error": False, "status": "completed"},
                }
            ]
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
