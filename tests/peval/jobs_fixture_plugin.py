"""Synthetic installed harness: its source and result formats are not Harbor."""

import asyncio
import json
import sys
import time


class FixtureHarness:
    def describe(self, context):
        return {
            "label": "Fixture",
            "agents": ["fixture"],
            "models": ["model-a", "model-b"],
            "capabilities": ["variants", "stop"],
            "defaults": {
                "settings": {
                    "n_attempts": 1,
                    "n_concurrent_trials": 1,
                    "timeout_multiplier": 1,
                },
                "variants": [
                    {
                        "id": "a",
                        "label": "A",
                        "agent": "fixture",
                        "model": "model-a",
                        "options": {},
                    }
                ],
            },
        }

    def catalog(self, context):
        return [
            {
                "id": "fixture",
                "label": "Fixture Dataset",
                "tasks": [{"id": "fixture/one", "label": "One", "available": True}],
            }
        ]

    def prepare(self, request, context):
        if request.tasks != ["fixture/one"]:
            raise ValueError("unknown fixture Task")
        return {
            "config": request.model_dump(),
            "selection": [{"id": "fixture/one", "revision": "v1"}],
            "trial_count": len(request.variants)
            * request.settings.get("n_attempts", 1),
        }

    async def execute(self, prepared, control):
        config = prepared["config"]
        control.report(trials_total=prepared["trial_count"])
        if config["settings"].get("block"):
            time.sleep(120)
        if config["settings"].get("child"):
            await control.subprocess(
                [sys.executable, "-c", "import time; time.sleep(120)"]
            )
        await asyncio.sleep(config["settings"].get("delay", 0.5))
        if config["settings"].get("fail"):
            raise RuntimeError("fixture failure")
        results = [
            {
                "id": variant["id"],
                "task": "One",
                "state": "completed",
                "score": 0 if index == 0 else 0.75,
                "score_source": "fixture-native",
                "variant_id": variant["id"],
                "variant_label": variant["label"],
                "agent_name": variant["agent"],
                "model": variant["model"],
            }
            for index, variant in enumerate(config["variants"])
        ]
        (control.output_dir / "native-results.data").write_text(
            json.dumps(results), encoding="utf-8"
        )
        print("fixture run finished", flush=True)
        control.report(trials_completed=len(results))

    def read_results(self, output_dir):
        path = output_dir / "native-results.data"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
