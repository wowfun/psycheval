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
    └── grader.json
```

Keep one observable capability in each Task. State required tools or parameters
only when they are part of the capability contract, and allow legitimate path
variation elsewhere. Pair every required call with same-call successful
observation evidence and require final facts only when they are independently
useful to the user.

Tasks invoke the installed `psycheval.harbor.verifier` module through
`PSYCHEVAL_HARBOR_PYTHON`; never embed repository-relative source paths.
