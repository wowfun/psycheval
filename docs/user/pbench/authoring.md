# Authoring PBench Tasks

Copy `examples/tasks/pbench-task-template` to start an authoring example. It is
not a maintained Dataset member.

Keep one observable capability per Task. Use the evidence rules owned by the
[evaluation reference](../../reference/evaluation.md) and the PBench-specific
contract in the [PBench reference](../../reference/pbench.md).

Both `tests/test.sh` and `tests/test.bat` should locate Task configuration from
their own directory and invoke the installed verifier with Python from `PATH`.
Do not embed checkout-relative source paths or duplicate the verifier logic in
platform wrappers. Programmatic graders may call
`psycheval.harbor.verifier.evaluate` and `aggregate`.

Validate discovery and scoring with explicit ATIF, source, and artifact fixtures.
