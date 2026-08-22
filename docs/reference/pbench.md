# PBench Reference

PBench is Psycheval's maintained set of Harbor Tasks for generic Agent
capabilities.

`datasets/pbench-v1.0` contains `web-search-01`, `web-fetch-01`, and the
three-step `trend-digest-01`. `datasets/pbench-v1.0-plus` contains
`browser-control-01`. Immediate child directories are Harbor Tasks; the
authoring scaffold under `examples/tasks/pbench-task-template` is not a Dataset
member.

Search, fetch, and browser control use the shared verifier's ordered call,
same-call observation, forbidden-tool, final-answer, and artifact rules. Trend
Digest adds task-owned dynamic source, freshness, coverage, and format checks
while reusing the shared verifier for calls and artifacts. Each multi-step
invocation is scored only from that step's trajectory and artifacts.

Task shell and Batch entrypoints invoke the installed verifier and do not use
repository-relative source paths. The manifests remain Linux-targeted;
HostEnvironment selects the native entrypoint, which is distinct from claiming
Windows container support.

See the [PBench user guide](../user/pbench/index.md) for running a Dataset and
[Scoring](../user/pbench/scoring.md) for author-facing evidence rules.
