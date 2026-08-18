# Psycheval Harnesses

ExternalHarnessAgent runs a caller-provided command. The command reads the Task
instruction from stdin and writes canonical ATIF v1.7 to
`paths.agent_logs/trajectory.json` from the effective JSON named by
`PEVAL_CONFIG`.

Every invocation receives a fresh effective configuration. Its harness section
is the versioned process protocol:

```json
{
  "schema_version": 1,
  "harbor": {
    "host": {"workdir_root": null, "workspace": null},
    "harness": {"protocol_version": 2, "action": "run"}
  },
  "paths": {
    "workdir": "/app",
    "tests": "/tests",
    "agent_logs": "/logs/agent",
    "verifier_logs": "/logs/verifier",
    "artifacts": "/logs/artifacts"
  },
  "executables": {"python": null}
}
```

`action` is `run` for a fresh invocation and `resume` for a continued native
session. HostEnvironment rewrites the paths and Python executable to native
host values before starting the subprocess. Other environments retain their
environment-local paths.

Pass `--agent-kwarg workdir=/workspace` to override the Task's
`[environment].workdir`; without either setting, the Agent uses `/app` (or
`C:/app` for a Windows target). The value is an environment path and normally
matches Harbor's `--mounts` target. Psycheval creates it when missing, launches
the harness with that cwd, and rejects relative paths or parent traversal.

The same configured command handles both actions. It must overwrite
`trajectory.json` with evidence from only the current invocation. Native
session state belongs below `paths.agent_logs`; a `resume` action with missing
or invalid state must fail instead of starting a new session. Psycheval removes
the previous trajectory before invoking the command, rejects non-zero exits and
invalid ATIF, and leaves step orchestration and rewards to Harbor.

## Multi-step Tasks

Harbor 0.21.0 owns step order, workspace persistence, `min_reward` termination,
reward aggregation, and `steps/<name>/` output archival. Psycheval supplies a
resumable Agent boundary and step-local scoring evidence. For example:

```toml
schema_version = "1.4"
multi_step_reward_strategy = "mean"

[[steps]]
name = "seed"
min_reward = 1.0

[steps.verifier]
environment_mode = "shared"

[[steps]]
name = "continue"
artifacts = ["/logs/agent/trajectory.json"]

[steps.verifier]
environment_mode = "separate"
```

A fresh-context Trial invokes `run, run, ...`. Add Harbor's
`--resume-trajectory` option to invoke `run, resume, ...` while retaining native
state in the live Agent logs directory. A shared verifier reads the current
`/logs/agent/trajectory.json` directly. A separate verifier can read it only
when that step declares the trajectory as an artifact, as above. Neither mode
searches sibling step archives, and Psycheval's verifier does not aggregate
rewards.

The selected workdir is unchanged across steps. With HostEnvironment, at most
one caller workspace bind may accompany Harbor's managed log and artifact
mounts. Its host source is modified directly and is not removed when the Trial
ends; use one source per concurrent Trial.

ExternalHarnessAgent and HermesAgent intentionally do not support
`load_trajectory`. Harbor rejects either native or ATIF loading before Agent
execution. This is distinct from continuing a session created by the first step
of the same Trial.

## Repository Test Fixtures

The source repository keeps one synthetic harness under `tests/fixtures` with
generic `single-step` and `multi-step` lifecycle modes. It is test
infrastructure, is not included in the installed package, and has no public
console command. The generic fixtures cover ExternalHarnessAgent,
HostEnvironment, native path mapping, resume, workspace persistence,
shared/separate verifiers, artifacts, reward aggregation, and early
termination.

Search, Fetch, Browser, and Trend Digest verifiers instead load Task-specific
ATIF, source, and artifact fixtures directly. This keeps Task scoring tests
independent from full Harbor lifecycle tests.

Synthetic ATIF is a harness-authored test record. A matching call and
observation proves that record is internally consistent; it does not
independently prove that the action occurred and must not be reported as Agent
capability evidence.

The repository's complete shared/separate verifier example is
`tests/fixtures/harbor-multi-step`. Its later-step grader forbids earlier tool
names so accumulated trajectory evidence cannot pass unnoticed.

## Psychevo Harness

The Psychevo harness runs `pevo run --format json`, retains its NDJSON and
stderr logs, and converts typed transcript events to ATIF without inventing
missing tool evidence. Every invocation forces `PSYCHEVO_DB` to
`agent/psychevo-state.db` inside the current Harbor Trial. The harness therefore
does not open or mutate the user's persistent Psychevo database, while peval-py
can reuse the retained database and runtime trace as same-Trial telemetry.
After a fresh run it records the exact terminal `threadId`. Resume requires both
that marker and the Trial-owned SQLite database, calls `pevo run --session` with
the exact ID, and rejects a returned ID that drifts. NDJSON, stderr, and ATIF are
rewritten for the current turn; the SQLite database is the complete native
conversation state.

Use it as ExternalHarnessAgent's command rather than invoking it standalone:

```text
--agent-kwarg "command=python -m psycheval.harbor.psychevo_harness --pevo /path/to/pevo"
```

Psychevo Web Search and Web Fetch require configured model/provider access and
real public Web access. They are opt-in live evaluations, not CI checks.

## Hermes Xiaomi Compatibility

Harbor 0.21's installed Hermes Agent predates Hermes's native Xiaomi provider.
Use Psycheval's thin compatibility import with the real provider-qualified
model; it preserves Harbor's `hermes` Agent identity and delegates execution and
ATIF conversion upstream. It also exports the exact session reported by current
Hermes so Harbor 0.21 does not lose a still-active CLI row during bulk export:

```text
--agent psycheval.harbor.hermes:HermesAgent \
--model xiaomi/mimo-v2.5-pro
```

Provide `XIAOMI_API_KEY` in the Harbor parent process environment. Do not pass
the key through `--agent-kwarg` or persist it in Job configuration.
After Hermes reports a valid session ID, failure of this post-run telemetry
export command is logged as a warning. Fresh-run grading can continue from the
upstream bulk export only when it contains the exact current instruction
boundary; an absent or unrelated export is not treated as current evidence. A
missing or malformed session ID still fails explicitly.

Without an explicit Agent version, Harbor's installer follows Hermes `main`, so
the installed CLI is not reproducible solely from Psycheval's lockfile. Setup
therefore probes `chat --resume` and exact `sessions export --session-id`
support before model execution. Resume uses the exact persisted ID through the
[official `hermes chat --resume` interface](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/cli.md),
then adopts the last reported ID if native compression changes it. A resumed
step requires an exact export; it retains the full `hermes-session.jsonl` as
telemetry but projects ATIF beginning at the last user message exactly matching
the rendered current instruction. A missing boundary or export is fatal, so
prior turns are never emitted as current grading evidence. Real Hermes resume
remains an opt-in live smoke because the default `main` ref can change.

## Diagnosing A Trial

For a single-step Trial, inspect these files in order:

1. `agent/psychevo.ndjson`
2. `agent/trajectory.json`
3. `verifier/checks.json`
4. `verifier/reward.json`
5. `agent/psychevo.stderr.log` and `trial.log`

For a multi-step Trial, use the same order below `steps/<name>/`. The root
`result.json` contains Harbor's per-step results and selected mean/final reward;
the root `trial.log` explains `min_reward` termination. Treat each step's
`agent/trajectory.json`, verifier output, and artifacts as one independent
scoring unit.

A reward of zero means the completed trajectory missed a scoring condition. A
missing trajectory/reward, provider error, network failure, target-site block,
or conversion exception is a harness or infrastructure failure instead.

Harbor 0.21.0's default trace exporter still rejects truthful custom import-path
Agent identities in its built-in Agent-name conversion. Use the Trial result,
ATIF trajectory, checks, reward, artifacts, and Harbor viewer; do not masquerade
as a built-in Agent to work around the exporter.
