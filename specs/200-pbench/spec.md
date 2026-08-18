---
name: PBench
---

# PBench

PBench is Psycheval's maintained Agent capability benchmark. Psychevo is its
first real harness, while the Dataset and scoring contracts remain Agent-agnostic.

## Scope

This topic specifies the local Harbor Datasets `datasets/pbench-v1.0` and
`datasets/pbench-v1.0-plus`, their current Tasks, and their scoring requirements.
Publishing Harbor registry entries, introducing Dataset manifests, and defining
a universal benchmark-conversion adapter are out of scope.

## Dataset Layout

Both Dataset directories are directly runnable as Harbor local Datasets. Each
Task is an immediate child directory because Harbor local Dataset discovery is
not recursive.

- `datasets/pbench-v1.0` contains `web-search-01`, `web-fetch-01`, and
  `trend-digest-01`.
- `datasets/pbench-v1.0-plus` contains `browser-control-01`.

Each Task remains self-contained with `instruction.md`, `task.toml`,
`environment/`, and `tests/`, or the equivalent per-step directories for a
multi-step Task. Every Task exposes thin `test.sh` and `test.bat` verifier
entrypoints. The simple capability Tasks invoke the installed
`psycheval.harbor.verifier`; `trend-digest-01` uses a Task-specific programmatic
verifier while reusing the installed verifier's required-call, artifact, and
final-answer checks. Tasks use Harbor 0.21.0's schema version `1.4`.
Every `task.toml` declares an explicit `[task].name` in
`<dataset-directory>/<task-directory>` form.

The Task manifests also declare stable discovery keywords:

- `pbench-v1.0/web-search-01`: `web-agent`, `web-search`
- `pbench-v1.0/web-fetch-01`: `web-agent`, `web-fetch`
- `pbench-v1.0/trend-digest-01`: `web-agent`, `multi-step`,
  `trend-research`, `skills`
- `pbench-v1.0-plus/browser-control-01`: `web-agent`, `browser-control`

## Web Search

The Agent must use a Web Search capability to identify IANA's Example Domains
page and report `example.com`, `example.org`, and the IANA URL.

The accepted exact tool names are `web_search` and `websearch`. The selected
branch's call contains argument terms `iana` and `example domains`. A successful
observation on that same call contains
`www.iana.org/help/example-domains`, `example.com`, and `example.org`.
The exact aliases `web_fetch`, `webfetch`, `exec_command`, `bash`, `terminal`,
`execute_code`, and `shell` are forbidden. The final answer contains both domains
and the IANA URL.

## Web Fetch

The Agent must use a direct Web Fetch capability with the exact URL
`https://www.iana.org/help/example-domains` and report the page's displayed last
updated date.

The accepted exact tool names are `web_fetch` and `webfetch`. The successful
observation on that same call contains the URL, `2017-05-13`, and
`example domains`. The exact aliases `web_search`, `websearch`, `exec_command`,
`bash`, `terminal`, `execute_code`, and `shell` are forbidden. The final answer
contains `2017-05-13` and the IANA URL.

## Browser Control

The Agent opens Selenium's Web Form, enters `Harbor eval` in the text input, and
submits the form using browser or computer-control capabilities. For each
ordered action, evidence matches one complete branch: exact `browser_type` or
Harbor `computer_action` with `type_text_at`, followed by exact `browser_click`
or `computer_action` with `click`. The text branch contains the exact input and
the submit branch's successful observation contains `submitted-form.html` and
`received!`. Browser and computer-action evidence may not be combined within a
required call.

The final answer contains the submitted URL, confirmation text, and the exact
`web-form-submitted.png` artifact name. The Trial also contains that valid
artifact.

## Trend Digest

`pbench-v1.0/trend-digest-01` is a three-step Task named `github`, `x`, and
`hacker-news`. The environment and workspace persist across steps. Resuming the
native Agent conversation is selected at Job runtime with
`agent.resume_trajectory`; it is not a Task manifest field. Acceptance runs use
resume so the Agent receives `run`, `resume`, and `resume`, while fresh-context
runs remain supported. The Task intentionally has no `solution/` directories
and does not support Harbor's Oracle Agent.

The Task provides `/app/input/x-users.xlsx`. Its `users` sheet has
`handle`, `name`, and `enabled` columns and enables the eleven tracked accounts
committed with the Task. The environment also provides task-local `x-daily`
and `hackernews-daily` skills at `/app/skills`. These skills fetch and normalize
source data but do not author the final reports:

- `x-daily` records every enabled account as `success`, `no_updates`, or
  `fetch_failed`, and includes posts from the rolling 24-hour interval ending
  at its UTC `generated_at`. At least one account fetch must succeed.
- `hackernews-daily` reads the official `topstories` feed and records the first
  twelve valid stories in API order.
- GitHub has no Task skill. The Agent retrieves
  `https://github.com/trending?since=weekly` directly and reports the first ten
  repositories evidenced by the current step.

Each step writes exactly one current artifact to `/logs/artifacts`, named
`github-<UTC datetime>.md`, `x-<UTC datetime>.md`, or
`hacker-news-<UTC datetime>.md`, where the datetime uses
`YYYYMMDDTHHMMSSZ`. Front matter exposes every graded freshness input: all
reports contain `platform`, matching UTC `generated_at`, and `source`; GitHub
also contains `window: weekly`, X contains the snapshot's `window_start` and
`window_end`, and Hacker News contains the snapshot's `snapshot_at`. Each
one-sentence step instruction names its output pattern and these required
fields so the verifier contract is not hidden. Reports use Chinese headings and
concise summaries while retaining source titles or post text, metrics,
timestamps where available, and original links. X reports classify every
enabled account, including explicit fetch failures. Each step's final answer
names its exact current report; the Hacker News answer is also the final answer
of the complete Task but does not read or repeat evidence from earlier steps.

The Task verifier reads only the current step's live
`/logs/agent/trajectory.json`, `/logs/artifacts`, and matching normalized
snapshot. X and Hacker News express skill execution through generic
`required_calls`: the tool name matches the Shell families `*exec*`,
`*terminal*`, `*shell*`, or `bash`, the arguments contain `x-daily` or
`hackernews-daily`, and the same call has a successful observation. The Task
verifier passes these rules and the outcome/artifact fields through
`psycheval.harbor.verifier.evaluate`; it combines the resulting call checks
with its snapshot validation instead of maintaining a second skill-call
matcher. GitHub retains its task-specific weekly-source and repository
extraction checks.

The Task verifier emits `source_evidence`, `freshness`, `coverage`, `format`, and
binary `final_answer`, plus `reward`. The quality subtotal is `0.30 *
source_evidence + 0.25 * freshness + 0.30 * coverage + 0.15 * format`; the step
reward is that subtotal multiplied by `final_answer`. GitHub and X gate
continuation on perfect `source_evidence`, `freshness`, `format`, and
`final_answer`. X provider failures reduce coverage but are not hidden; an
all-account failure fails source evidence. Harbor owns early termination,
per-key mean aggregation, and step artifact archival.

## Portability

Verifier entrypoints locate their own Task files and run the installed verifier
with `python` from `PATH`; they do not depend on repository-relative Python
source paths. Host runtime path and executable ownership is specified by
[Psycheval](../100-psycheval/spec.md). A task-authoring scaffold lives under
`examples/tasks/pbench-task-template` and is not a Dataset member.

The Task instructions describe capabilities and observable outcomes rather than
requiring one provider's function spelling. The grader configuration owns the
explicit accepted aliases.

The source-checkout command uses Psycheval's explicit HostEnvironment so the
installed project interpreter is available to the verifier. The current
minimal Dockerfiles are Agent workspaces, not standalone Psycheval runtime
images; a default Docker invocation is unsupported unless its image separately
installs a released Psycheval distribution.

PBench Task manifests remain Linux-targeted. On a native Windows host,
HostEnvironment reports Windows so Harbor selects `test.bat`; on Linux and WSL
it selects `test.sh`. This is native HostEnvironment portability, not Harbor
Windows container support.

## Acceptance Criteria

- Harbor discovers `web-search-01`, `web-fetch-01`, and `trend-digest-01` from
  `pbench-v1.0`, and `browser-control-01` from `pbench-v1.0-plus`.
- Explicit deterministic ATIF, source, and artifact fixtures pass all four Task
  verifiers without requiring a synthetic Harbor Trial for each Task.
- Forbidden tools, wrong arguments, cross-call observations, missing final
  terms, and invalid artifacts fail the relevant checks.
- Trend Digest rejects stale or cross-step source evidence, missing or failed
  skill calls, malformed report names/front matter, missing or incorrect final
  artifact references, missing normalized items, and total X source failure;
  partial X source failure remains visible as reduced coverage.

## Attachments

- [Testing](testing.md)

## Related Topics

- [010. Evaluation Lifecycle](../010-evaluation/spec.md)
- [015. Agent Evaluation](../015-agent-evaluation/spec.md)
- [100. Psycheval](../100-psycheval/spec.md)
