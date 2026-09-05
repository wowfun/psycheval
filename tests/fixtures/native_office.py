"""Small owned Task fixtures using the Office v1.0 execution wrapper."""

from __future__ import annotations

import io
import shutil
import tarfile
from pathlib import Path

from tests.fixtures.workbuddy import write_office_bundle


def write_native_office(root: Path, test_code: str) -> Path:
    write_office_bundle(root)
    for task in (root / "tasks").iterdir():
        if task.name != "office-00":
            shutil.rmtree(task)
    task = root / "tasks/office-00"
    (task / "task.toml").write_text(
        'version = "1.0"\n[metadata]\nsource_case = "native-fixture"\n'
        '[environment]\nworkdir = "/workspace"\n',
        encoding="utf-8",
    )
    (task / "environment/Dockerfile").write_text("FROM scratch\n")
    baseline = b"before\n"
    member = tarfile.TarInfo("input.txt")
    member.size = len(baseline)
    with tarfile.open(task / "environment/workspace.tar.gz", "w:gz") as archive:
        archive.addfile(member, io.BytesIO(baseline))
    shared = root / "shared/verifier"
    shutil.copy2(
        Path(__file__).with_name("workbuddy_office_rule.txt"), shared / "rule.py"
    )
    (shared / "manifest.py").write_text("""from dataclasses import dataclass, field

@dataclass
class VerifierManifest:
    cwd: str = "/workspace"
    command: str = ""
    env: dict = field(default_factory=dict)
""")
    (shared / "plugin.py").write_text("""import tomllib
from workbuddy_bench.judge import EvaluationItem, EvaluationPlan, PassRateScoringPolicy, VerifierRegistry
from workbuddy_bench.judge.runners.rule import HarborScriptRuleJudgeRunner
from .manifest import VerifierManifest
from .rule import build_rule_judge

def build_registry(build_context):
    task = build_context.contract.task_dir
    data = tomllib.loads((task / "tests/verifier.toml").read_text())
    manifest = VerifierManifest(**data["run"], env=data.get("env", {}))
    def build_plan(context):
        return EvaluationPlan(dataset_id=context.dataset_id, task_id=context.task_id,
            items=[EvaluationItem(id="rule", type="rule")],
            judges=[build_rule_judge(item_id="rule", manifest=manifest, timeout_sec=30)])
    return VerifierRegistry(plan_builder=build_plan, scoring_policy=PassRateScoringPolicy(),
        judge_runners={"rule_script": HarborScriptRuleJudgeRunner(build_context.runtime)})
""")
    (task / "tests/grading").mkdir()
    (task / "tests/grading/test_verify.py").write_text(test_code, encoding="utf-8")
    (task / "tests/verifier.toml").write_text(
        """schema_version = "workbuddy.office.verifier.v1"
[run]
cwd = "/workspace"
command = 'PYTHONPATH="/workspace:${PYTHONPATH:-}" python -m pytest /tests/grading -p no:cacheprovider -v --tb=short --junitxml=/logs/verifier/results.xml > /logs/verifier/test_output.txt 2>&1'
[env]
PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
""",
        encoding="utf-8",
    )
    return task
