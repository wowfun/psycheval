# Authoring PBench Tasks

Copy `examples/tasks/pbench-task-template` when starting a Task. The scaffold is
an authoring example and is not part of the maintained Dataset.

```text
task/
├── instruction.md
├── task.toml
├── environment/
│   └── Dockerfile
└── tests/
    ├── test.sh
    ├── test.bat
    └── grader.json
```

Keep one observable capability in each Task. State required tools or parameters
only when they are part of the capability contract, and allow legitimate path
variation elsewhere. Pair every required call with same-call successful
observation evidence and require final facts only when they are independently
useful to the user.

Describe capabilities in `instruction.md`, not one provider's tool spelling. In
`grader.json`, put each accepted case-sensitive tool-name glob in a complete
`required_calls[].any[]` branch with its own argument and observation
constraints. A pattern without glob metacharacters is exact. Never combine
evidence from separate branches or calls. To require a bundled skill, match the
execution tool family, put the skill name in `argument_terms`, and require the
paired successful observation; prose mentioning the skill is not evidence.

Keep `required_artifacts` as a list of artifact-root-relative POSIX glob
strings. A string without glob metacharacters is an exact path. Every pattern
must match at least one valid file, every match is required, and the Agent's
final answer must name every matched relative path exactly. Use this directly
for runtime-named outputs such as `report-*.md`; do not add a second field for
final-answer artifact references.

Tasks invoke the installed `psycheval.harbor.verifier` package module with
`python` from `PATH`. Each `test.sh` or `test.bat` locates `grader.json` from its
own script directory; never embed repository-relative source paths or copy
grader logic into either platform entrypoint. On HostEnvironment,
`PEVAL_CONFIG` supplies native evidence paths and the project interpreter's
directory is first on `PATH`. Programmatic Task verifiers reuse the module's
`evaluate` and `aggregate` interface.
