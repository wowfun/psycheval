# PBench Reference

PBench is Psycheval's maintained set of Harbor Tasks for generic Agent
capabilities.

Maintained Task packages live under `datasets/pbench-v1.0` and
`datasets/pbench-v1.0-plus`. Immediate child directories are Harbor Tasks.
`examples/tasks/pbench-task-template` is a runnable authoring example for copying
and adaptation, separate from maintained Dataset membership.

Each Task's instruction and scoring configuration define its observable outcome
and weights. Task-owned checks reuse the shared verifier and evidence interfaces;
tool checks apply when performing the action is part of the capability.
Evidence-grounded Judge rubrics assess only published material. Each multi-step
invocation is scored from that step's trajectory and artifacts, with supporting
sources selected by the Task's contract.

Task shell and Batch entrypoints invoke the installed verifier and do not use
repository-relative source paths. Native Host and container setup remain
different execution contracts; a Dockerfile does not prepare a Native Host.
The [Harbor reference](harbor.md) owns their runtime and artifact semantics.

See the [PBench user guide](../user/pbench/index.md) for running a Dataset and
[Scoring](../user/pbench/scoring.md) for author-facing evidence rules.
