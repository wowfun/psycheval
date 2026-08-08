---
name: PBench
---

# PBench

PBench is Psycheval's maintained Agent capability benchmark. Psychevo is its
first real harness, while the Dataset and scoring contracts remain Agent-agnostic.

## Scope

This topic specifies the local Harbor Dataset `datasets/pbench-v1.0`, its current
Tasks, and their scoring requirements. Publishing a Harbor registry entry,
introducing a Dataset manifest, and defining a universal benchmark-conversion
adapter are out of scope.

## Dataset Layout

`datasets/pbench-v1.0` is directly runnable as a Harbor local Dataset. Each Task
is an immediate child directory because Harbor local Dataset discovery is not
recursive. The Dataset contains exactly these initial Tasks:

- `web-search`
- `web-fetch`
- `browser-control`

Each Task remains self-contained with `instruction.md`, `task.toml`,
`environment/`, and `tests/`. Task schema version `1.3` is retained because
Harbor 0.20.0 supports it and no schema change is required.

## Web Search

The Agent must use `web_search` to identify IANA's Example Domains page and
report `example.com`, `example.org`, and the IANA URL.

The required call contains argument terms `iana` and `example domains`. A
successful observation on that same call contains
`www.iana.org/help/example-domains`, `example.com`, and `example.org`.
`web_fetch` and `exec_command` are forbidden. The final answer contains both
domains and the IANA URL.

## Web Fetch

The Agent must call `web_fetch` with the exact URL
`https://www.iana.org/help/example-domains` and report the page's displayed last
updated date.

The successful observation on that same call contains the URL, `2017-05-13`,
and `example domains`. `web_search` and `exec_command` are forbidden. The final
answer contains `2017-05-13` and the IANA URL.

## Browser Control

The Agent opens Selenium's Web Form, enters `Harbor eval` in the text input, and
submits the form. Ordered evidence contains a `browser_type` call with that
exact text followed by a button `browser_click` whose successful observation
contains `submitted-form.html` and `received!`.

The final answer contains the submitted URL and confirmation text. The Trial
also contains a valid `web-form-submitted.png` artifact.

## Portability

Tasks use the installed `psycheval.harbor.verifier` module and
`PSYCHEVAL_HARBOR_PYTHON`; they do not depend on repository-relative Python
source paths. A task-authoring scaffold lives under
`examples/tasks/pbench-task-template` and is not a Dataset member.

The source-checkout command uses Psycheval's explicit HostEnvironment so the
installed project interpreter is available to the verifier. The current
minimal Dockerfiles are Agent workspaces, not standalone Psycheval runtime
images; a default Docker invocation is unsupported unless its image separately
installs a released Psycheval distribution.

## Acceptance Criteria

- Harbor discovers all three immediate Task directories from the Dataset path.
- Deterministic canned trajectories pass all three verifiers.
- Forbidden tools, wrong arguments, cross-call observations, missing final
  terms, and invalid artifacts fail the relevant checks.

## Attachments

- [Testing](testing.md)

## Related Topics

- [010. Evaluation Lifecycle](../010-evaluation/spec.md)
- [015. Agent Evaluation](../015-agent-evaluation/spec.md)
- [100. Psycheval](../100-psycheval/spec.md)
