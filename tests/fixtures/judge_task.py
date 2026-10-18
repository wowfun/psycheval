"""Shared generic Judge task and runtime fixtures."""

from __future__ import annotations

from pathlib import Path

from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
)

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
    (roots["verifier_logs"] / "中文 报告.md").write_text(
        "这里是当前来源支持的摘要。", encoding="utf-8"
    )
    return config


def api_task(tmp_path):
    context = runtime(tmp_path)
    tests = Path(context.paths.tests)
    grader = tests / "grader.json"
    grader.write_text('{"custom_checks":["valid"]}', encoding="utf-8")
    (tests / "judge.yaml").write_text(YAML, encoding="utf-8")
    (tests / "test_outputs.py").write_text(
        "import argparse\nfrom pathlib import Path\n"
        "parser = argparse.ArgumentParser()\n"
        "parser.add_argument('--context', required=True)\n"
        "parser.add_argument('--output', type=Path, required=True)\n"
        "args = parser.parse_args()\n"
        "args.output.write_text("
        '\'{"checks":[{"id":"valid","passed":true}]}\', encoding=\'utf-8\')\n',
        encoding="utf-8",
    )
    return grader, context
