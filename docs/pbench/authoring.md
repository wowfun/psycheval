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
`grader.json`, put each accepted exact spelling in a complete
`required_calls[].any[]` branch with its own `tool_names`, argument constraints,
and observation constraints. Never infer aliases with substrings or combine
evidence from separate branches.

Tasks invoke the installed `psycheval.harbor.verifier` module through
`PSYCHEVAL_HARBOR_PYTHON`; never embed repository-relative source paths or copy
grader logic into either platform entrypoint.
