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

- `datasets/pbench-v1.0` contains `web-search-01` and `web-fetch-01`.
- `datasets/pbench-v1.0-plus` contains `browser-control-01`.

Each Task remains self-contained with `instruction.md`, `task.toml`,
`environment/`, and `tests/`. Every `tests/` directory contains a thin `test.sh`
and `test.bat`; both invoke the installed `psycheval.harbor.verifier` module and
contain no grader logic. Tasks use Harbor 0.21.0's schema version `1.4`.
Every `task.toml` declares an explicit `[task].name` in
`<dataset-directory>/<task-directory>` form.

The Task manifests also declare stable discovery keywords:

- `pbench-v1.0/web-search-01`: `web-agent`, `web-search`
- `pbench-v1.0/web-fetch-01`: `web-agent`, `web-fetch`
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

The final answer contains the submitted URL and confirmation text. The Trial
also contains a valid `web-form-submitted.png` artifact.

## Portability

Tasks use the installed `psycheval.harbor.verifier` module and
`PSYCHEVAL_HARBOR_PYTHON`; they do not depend on repository-relative Python
source paths. A task-authoring scaffold lives under
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

- Harbor discovers `web-search-01` and `web-fetch-01` from `pbench-v1.0`, and
  `browser-control-01` from `pbench-v1.0-plus`.
- Deterministic canned trajectories pass all three verifiers.
- Forbidden tools, wrong arguments, cross-call observations, missing final
  terms, and invalid artifacts fail the relevant checks.

## Attachments

- [Testing](testing.md)

## Related Topics

- [010. Evaluation Lifecycle](../010-evaluation/spec.md)
- [015. Agent Evaluation](../015-agent-evaluation/spec.md)
- [100. Psycheval](../100-psycheval/spec.md)
