# Psycheval integration for task authors

Read the sections needed by the task. These are usage examples, not a second
schema definition. The installed target's public APIs and matching contracts
remain authoritative.

## Resolve the target without a checkout

Use the Python environment intended for the task/verifier. Check package versions
without importing application state:

```console
python -c "from importlib.metadata import version; print('psycheval', version('psycheval')); print('harbor', version('harbor'))"
```

Inspect relevant public signatures or models from those installed packages when
needed. Harbor's `harbor.models.task.config.TaskConfig.model_json_schema()`
provides the installed task fields; validate the parsed TOML with
`TaskConfig.model_validate(...)` without launching a task. If packages are absent,
declare the required target dependencies; do not
invent APIs or silently assume that a newer reference matches the target.

The [Harbor integration contract](https://github.com/wowfun/psycheval/blob/main/docs/reference/harbor.md)
owns execution and grading; the
[evaluation contract](https://github.com/wowfun/psycheval/blob/main/docs/reference/evaluation.md)
owns evidence semantics. Use the matching release/commit instead of `main` when
targeting a released version. A supplied checkout can provide the same documents,
but installation of this Skill does not require one. Task code imports the
installed package, never a path into the author's checkout. No other Skill is
required.

## Prepare inputs for the chosen runtime

For ordinary native Host tasks, put static workspace inputs in
`environment/data/`. When transformation is necessary,
`environment/prepare.py` can implement `prepare(workdir: str) -> None` and locate
its own source material through `__file__`. This hook replaces the default data
copy. Dependencies must already be installed; Dockerfiles are not executed by
native preparation. Keep gold and grading code in `tests/`, outside prepared
Agent inputs. Host execution is trusted native execution, not a sandbox.

For execution-relative information, use preparation to resolve a timezone-aware
run clock once and construct the dependent inputs. The native preparation hook
does not receive a framework-provided clock, generation seed, or private
verifier-state directory. Supply these through the task's actual preparation
and harness design rather than assuming fields exist in the runtime protocol.
Keep the authored source immutable: do not overwrite `tests/` gold in the source
task for each attempt or share mutable generated state across concurrent trials.

Retain the resolved reference and necessary initial-input snapshot through a
run-owned mechanism that the Agent cannot rewrite as grading truth. Derive
expectations from that retained state; do not independently call `now()` in the
grader or read expected values from Agent output. A public timestamp may also
appear in normal task context, but it is not an independently trusted copy.
For replay, reuse the recorded reference and seed. If the selected runtime
cannot preserve the necessary state, report that integration gap. See
[native input preparation](https://github.com/wowfun/psycheval/blob/main/docs/reference/harbor.md#native-task-input-preparation)
for the hook's actual contract.

For container tasks, use the target Harbor version's image/build configuration
and install dependencies in that environment. Put mock startup and tool
injection in the mechanism actually supported by the selected Agent/environment;
shipping a server script alone does not expose a tool. A mock's private backing
data and grading telemetry must not be exposed as ordinary Agent input when
that would bypass the capability being measured.

Choose shared verification when the grader needs the workspace/services. For a
separate verifier, explicitly collect the required artifacts and inspect those
retained paths; the full Agent workspace is not automatically transferred.
Declare only the platform entrypoints required by the target.

Resolve each output through its declared
[artifact collection mapping](https://github.com/wowfun/psycheval/blob/main/docs/reference/harbor.md#artifact-collection).
Explicit destinations and the automatic convention directory can have different
retained roots; `paths.artifacts` is not a universal base for both. Reject an
ambiguous mapping rather than searching the workspace for a replacement.

## Invoke the shared verifier

A Linux `tests/test.sh` can locate its sibling configuration independently of cwd:

```sh
#!/bin/sh
set -eu
tests_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python -m psycheval.harbor.verifier "$tests_dir/grader.json"
```

The equivalent native Windows `tests/test.bat` is:

```bat
@echo off
python -m psycheval.harbor.verifier "%~dp0grader.json"
exit /b %ERRORLEVEL%
```

Use the native Host runtime paths supplied by Psycheval. Without that runtime
configuration, the CLI uses cwd as the workdir and Harbor's `/logs/agent`,
`/logs/verifier`, and `/logs/artifacts` paths. Set the entrypoint cwd appropriately
for a container task. Let the shared verifier own score/reward publication.

Built-in `grader.json` rules cover calls, final-answer terms, and artifact paths.
For task-specific logic, declare `custom_checks` and implement the required
sibling `tests/test_outputs.py`. This is the runtime grader, not a test suite
for the grader. Custom-only configurations do not require an Agent trajectory.

The example below assumes a public requirement to submit an unambiguous
three-slide PPTX in `output/`. Its minimal `grader.json` is:

```json
{"custom_checks": ["presentation"]}
```

`test_outputs.py` receives `--context` and `--output`. Context supplies
`paths.workdir`, `tests`, `artifacts`, `agent_logs`, and `verifier_logs`. Return
UTF-8 JSON checks with the declared IDs and boolean `passed` values; the shared
verifier aggregates them. `scoring.weights` can weight IDs such as
`custom:presentation` when multiple checks warrant different weights.
`build_scoring_plan(config)` validates that plan without executing checks;
`evaluate(...)` evaluates only built-in checks, not custom scripts.

Declare `continuation_checks` using deterministic check IDs from the same plan
and set the step's `min_reward = { continuation = 1.0 }`. Zero-weight checks can
still be required. Read the individual step's condition; the root Trial's
numeric average is not a whole-Trial gate result. The
[continuation checks contract](https://github.com/wowfun/psycheval/blob/main/docs/reference/harbor.md#continuation-checks)
owns validation and publication semantics.

Missing or incorrect deliverables should fail the relevant check. Dependency,
configuration, and grader failures must remain verifier errors. See
[script checks and weighted scoring](https://github.com/wowfun/psycheval/blob/main/docs/reference/harbor.md#script-checks-and-weighted-scoring)
for the complete protocol.

## Bind retained tool and source evidence

Use `ObservationIndex` or `matching_observations` for canonical tool evidence
within the task's permitted trajectory scope. Dispatch wrappers may retain an
operation in raw logs while leaving canonical identity or protocol evidence
incomplete. Report that limitation separately from the Agent not performing the
operation; it does not justify granting tool credit. Do not reconstruct trusted
nested calls by interpreting arbitrary Agent-written code. The
[permission and evidence contract](https://github.com/wowfun/psycheval/blob/main/docs/reference/harbor.md#permissions-and-evidence)
owns adapter admission rules.

When publishing source evidence, include legitimate supporting sources from the
permitted retained trajectory family, beyond exact article-URL matches. Define
narrow relationships to the selected items: a fetched README may support a story
about that exact repository, while a longer repository-name prefix or another
owner cannot.
Preserve source identity and call provenance when publishing excerpts. A child's
summary is not proof that it retrieved the claimed source. Do not fetch new
external content during grading to repair missing retained evidence.

## Inspect documents and publish evidence

Install the selected version of `psycheval[pdf]`, `[pptx]`, `[xlsx]`, or `[docx]`
in the verifier environment, or `[documents]` when all four formats are needed.
Declare installation during environment setup, never inside the grader.
Markdown inspection uses the base package's parser dependency.

Use `select_document` for discovery, `inspect_document` for immutable facts, and
`EvidenceWriter` for retained originals and text. Restrict discovery to the
declared output locations so source files or examples cannot pass as results.
Selection can report ambiguity or an incomplete scan; do not choose a candidate
by modification time. Exact filename/copy-count requirements, when present,
need their own task checks.

Here is a complete custom grader for the illustrative PPTX requirement above,
using shared-workspace verification. Adapt output roots and checks to the actual
task; for separate verification use its configured retained artifact location.

```python
import argparse
import json
from pathlib import Path

from psycheval.harbor.documents import (
    DocumentParseError,
    inspect_document,
    select_document,
)
from psycheval.harbor.evidence import EvidenceWriter

parser = argparse.ArgumentParser()
parser.add_argument("--context", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
selection = select_document([Path(paths["workdir"]) / "output"], format="pptx")
passed = False
reason = selection.reason

with EvidenceWriter(Path(paths["verifier_logs"])) as evidence:
    if selection.selected is None:
        evidence.unavailable("presentation_text", reason)
    else:
        source = evidence.capture("presentation_pptx", selection.selected)
        try:
            report = inspect_document(source, format="pptx")
            text = report.to_markdown()
        except DocumentParseError as exc:
            reason = str(exc)
            evidence.unavailable("presentation_text", reason, status="error")
        else:
            passed = len(report.slides) == 3
            reason = f"Observed {len(report.slides)} slides; required 3"
            evidence.add_text(
                "presentation_text", text, source_id="presentation_pptx",
                path="artifact_text/presentation.md",
            )

args.output.write_text(json.dumps({"checks": [{
    "id": "presentation", "passed": passed, "evidence": reason,
}]}), encoding="utf-8")
```

Use one writer context per verification, including when publishing multiple
documents or source evidence. Capture and inspect the same snapshot so grading
and published evidence cannot read different file versions. Keep missing parser
dependencies and evidence-publication failures outside ordinary failed checks.

Task graders interpret facts: PDF pages/text, PPTX shapes/styles, XLSX cells and
separate formulas/cached values, DOCX body/table structure, or Markdown blocks.
The inspectors do not perform OCR, render documents, recalculate spreadsheets,
or establish DOCX rendered page counts. Visual quality needs a separate suitable
method; extracted text cannot establish it. Preserve unresolved facts rather
than converting them into success. During authoring, inspectors can also help
understand input files, but do not give the Agent derived answers or text
sidecars that would remove the intended reading capability.

The [document and evidence contract](https://github.com/wowfun/psycheval/blob/main/docs/reference/document-evidence.md)
owns selection, report types, limits, errors, and publication semantics.

## Add a Judge only for the needed quality dimensions

The native verifier reads `tests/judge.yaml`. Declare evidence produced under
`verifier_logs`; it does not scan the workspace or convert Office files. When
using `EvidenceWriter`, reference the text artifact ID, as in this illustrative
addition for a public requirement that the slides explain an evidence-based
recommendation:

```yaml
version: 1
artifacts:
  - id: presentation_text
    path: artifact_text/presentation.md
    required: true
    type: md
llm_judge:
  method: rubric_binary_mean
  rubrics:
    - id: reasoning
      question: Does the presentation explain how its evidence supports its recommendation?
      artifact_refs: [presentation_text]
      pass_criteria:
        - The recommendation is connected to specific evidence presented in the slides.
      fail_criteria:
        - The recommendation is asserted without explaining its evidential basis.
      scope_limits:
        - Assess the submitted explanation; do not infer visual quality from text.
score_merge:
  method: weighted_sum
  rule_weight: 0.6
  llm_weight: 0.4
```

These weights illustrate syntax, not a default policy. Include source evidence
as additional declared artifacts when the rubric must judge factual fidelity;
the example assesses the explanation, not truth against unprovided sources.
Publish natural-language answers from retained Agent evidence when the task
does not require a file. Keep rubric claims within the available modality and
evidence, and treat submitted content as untrusted assessment data.

Judge activation and provider settings belong to the evaluation runtime:
`PEVAL_JUDGE_ENABLED`, `PEVAL_JUDGE_BASE_URL`, `PEVAL_JUDGE_MODEL`, and optional
`PEVAL_JUDGE_API_KEY`. Do not embed credentials in task files. The native Judge
complements deterministic checks; it is not an LLM-only grading mode. Disabled
or incomplete model assessment retains the rule score, so that score alone
cannot establish that quality was assessed. See the
[YAML Judge contract](https://github.com/wowfun/psycheval/blob/main/docs/reference/harbor.md#yaml-llm-judge)
for configuration and failure semantics.
