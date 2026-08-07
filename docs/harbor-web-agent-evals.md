# Harbor-compatible Web Agent evaluations

`psycheval-harbor` adds a deliberately small Harbor `0.18.0` plugin surface for
trusted Web Agent evaluations. Harbor still owns Task loading, Trial lifecycle,
timeouts, ATIF logs, verification, rewards, artifacts, and pass@k aggregation.

The package provides:

- `psycheval_harbor.environment:HostEnvironment`
- `psycheval_harbor.agent:ExternalHarnessAgent`
- a deterministic canned harness
- a real `pevo run --format json` to ATIF v1.7 Psychevo harness
- a binary outcome-and-evidence verifier

## Safety boundary

HostEnvironment is not a sandbox. It executes the Task, external harness, and
verifier as ordinary Linux subprocesses with the caller's filesystem,
credentials, environment, and public network access. Use it only for code you
trust. Every run must opt in explicitly:

```text
--environment-kwarg allow_host_execution=true
```

The provider rejects non-public network policies, Compose, extra mounts,
resource requests, Windows Tasks, and forced image builds. These rejections do
not make host execution isolated; they only keep the supported Harbor subset
honest.

## Install

The plugin pins the published Harbor `0.18.0` package. A fresh clone needs only
the tracked plugin directory:

```sh
uv venv .venv-harbor --python 3.12
uv pip install \
  --python .venv-harbor/bin/python \
  -e tools/psycheval-harbor
```

No `psycheval` wrapper CLI is involved. Invoke Harbor directly.

Harbor `0.18.0` has an upstream `harbor traces export` defect: its exporter
casts the recorded agent name to Harbor's built-in `AgentName` enum before the
custom-agent fallback, so it rejects every custom import-path agent with a
`ValueError`. The Trial result, canonical `agent/trajectory.json`, verifier,
artifacts, and Harbor viewer remain usable. This package keeps its truthful
custom agent identity instead of masquerading as a built-in agent.

## Run deterministic examples

Web search:

```sh
.venv-harbor/bin/harbor run \
  --path examples/harbor/web-search \
  --agent psycheval_harbor.agent:ExternalHarnessAgent \
  --agent-kwarg "command=$PWD/.venv-harbor/bin/python -m psycheval_harbor.canned_harness --scenario web-search" \
  --env psycheval_harbor.environment:HostEnvironment \
  --environment-kwarg allow_host_execution=true \
  --jobs-dir jobs \
  --n-concurrent 1 \
  --yes
```

For the other deterministic cases, use these Task and scenario pairs:

| Task | Scenario |
| --- | --- |
| `examples/harbor/web-fetch` | `web-fetch` |
| `examples/harbor/browser-control` | `browser-control` |

The browser fixture publishes
`artifacts/logs/artifacts/web-form-submitted.png`. Every verifier writes one
binary `verifier/reward.json` key and a detailed `verifier/checks.json`.

Each `tests/grader.json` declares an ordered `required_calls` list. A rule's
tool, argument constraints, and successful observation must all match the same
ATIF call id; later rules must match later calls. `argument_values` checks exact
named values, while `argument_terms` checks query semantics and `argument_url`
uses normalized URL equality. Required artifacts are relative to the artifact
root, non-symlink, non-empty regular files; `.png` requirements also validate
the PNG signature.

## Run real Psychevo live evaluations

These commands use the configured real Psychevo model/provider, contact the
public web, and persist normal `pevo run` session state. They are intentionally
opt-in and must not be used as deterministic CI.

Set the Psychevo executable explicitly, then run search:

```sh
.venv-harbor/bin/harbor run \
  --path examples/harbor/psychevo-web-search-live \
  --agent psycheval_harbor.agent:ExternalHarnessAgent \
  --agent-kwarg "command=$PWD/.venv-harbor/bin/python -m psycheval_harbor.psychevo_harness --pevo $HOME/Projects/psychevo/target/debug/pevo" \
  --env psycheval_harbor.environment:HostEnvironment \
  --environment-kwarg allow_host_execution=true \
  --jobs-dir jobs \
  --n-concurrent 1 \
  --yes
```

Use `examples/harbor/psychevo-web-fetch-live` for the fetch case. The harness
keeps `agent/psychevo.ndjson` and `agent/psychevo.stderr.log`, and writes the
canonical `agent/trajectory.json`. It never reads Psychevo's SQLite state to
invent missing evidence.

## Supported Task subset

Each scored Task needs only:

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

`task.toml` uses schema `1.3` and `/app` as the workdir. The Dockerfile is kept
for Harbor-format portability; HostEnvironment does not build it. Docker
execution requires `psycheval-harbor` and the chosen external harness to be
installed in the image.

Task scripts use these portable variables, with Harbor container-path
fallbacks:

- `PSYCHEVAL_WORKDIR`
- `PSYCHEVAL_TESTS_DIR`
- `PSYCHEVAL_AGENT_LOGS_DIR`
- `PSYCHEVAL_VERIFIER_LOGS_DIR`
- `PSYCHEVAL_ARTIFACTS_DIR`
- `PSYCHEVAL_HARBOR_PYTHON`

The complete normative boundary is in
[`specs/002-harbor-web-agent-evals/spec.md`](../specs/002-harbor-web-agent-evals/spec.md).

## Interpreting failures

A reward of zero means an observable task condition was missing: required
ordered call with same-call arguments and observation, final fact/citation, or
valid artifact. A malformed trajectory, broken grader fixture, or missing
reward is a Trial infrastructure error instead.

For a Psychevo live failure, inspect these in order:

1. `agent/psychevo.ndjson`
2. `agent/trajectory.json`
3. `verifier/checks.json`
4. `agent/psychevo.stderr.log` and `trial.log`

Classify provider credentials, target-site blocking, search-backend failures,
harness conversion defects, and Psychevo defects separately. A correct final
answer without the required structured tool evidence does not pass.
