# Authoring PBench Tasks

Copy `examples/tasks/pbench-task-template` to start from a runnable local-source
writing example. Adapt its instruction, inputs, output contract, checks and Judge
rubrics together. It is not a maintained Dataset member.

Keep one observable capability per Task. Use the evidence rules owned by the
[evaluation reference](../../reference/evaluation.md) and the PBench-specific
contract in the [PBench reference](../../reference/pbench.md).

Both `tests/test.sh` and `tests/test.bat` should locate Task configuration from
their own directory and invoke the installed verifier with Python from `PATH`.
Do not embed checkout-relative source paths or duplicate the verifier logic in
platform wrappers. The [Harbor reference](../../reference/harbor.md) owns native
preparation and artifact collection; the
[Harbor verifier reference](../../reference/harbor-verifier.md) owns custom checks
and Judge configuration;
[document and evidence publication](../../reference/document-evidence.md) owns
immutable source capture and the material the Judge receives.

Validate discovery and scoring through the public verifier with isolated source
and output fixtures and a local Judge service. `evaluate` runs built-in checks;
it does not execute custom scripts. Exercise actual artifact collection when a
grader consumes retained outputs, so hand-built runtime paths do not hide a
collection mismatch. Keep default validation separate from opt-in live Agent and
model runs.
