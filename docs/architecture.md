# Architecture

Psycheval is one Python project and package. `peval` is the installed CLI name,
not a second package or module.

```text
psycheval
├── cli                 -> installed as `peval`
├── atif                -> standalone ATIF format recognition and validation
├── adapters, conversion -> retained-session conversion
├── report, workspace   -> derived views and user overlays
├── serve, state        -> local evaluation workspace and ACP client runtime
├── assets              -> authored Web modules, templates, and styles
└── harbor              -> Harbor 0.21 adapters, harness, host, verifier
```

## Module boundaries

The package-level implementation reads retained sessions and Harbor Trial
evidence, converts strict ATIF, and builds reports and workspaces behind the
`psycheval.cli` interface. One internal Harbor Trial loader owns read-only
recognition and projection for both direct CLI paths and workspace mounts;
`psycheval.harbor.tasks` owns validated Task configuration, text
decoding, and publishable file selection for both workspace state and the
Dataset workbench. Workspace state owns only discovery, overlays, and derived
catalog records. One EvaluationReports module resolves normalized Harbor and
local source references, reads their canonical evaluation reports, and
atomically upserts reviewed Markdown under a cross-process lock. It is the only
Psycheval module allowed to create or replace canonical source `analysis.md`.
It validates the source and document, but does not infer evaluation criteria
from a live Task or any other Copilot context.
`psycheval.harbor` is the adapter module for Harbor's Agent, Environment,
trajectory, verifier, and external-Dataset seams. It owns host execution,
harness integration, evidence scoring, non-executing Dataset resolution, and
the public WorkBuddy configuration and metrics functions. Its subtree is a relocatable source-copy
unit: it imports no other Psycheval module and uses relative internal imports.
Dataset services accept explicit identifiers, paths, and formats. WorkBuddy
services accept an in-memory Harbor JobConfig or an explicit retained Job path.
Preparation returns a private validated model without allocating files; metrics
return the upstream result without persisting another summary. Harbor owns Task
selection, execution, Job identities, and retained artifacts. The application
owns configuration export and Dataset-to-mount selection.
The package version has one source in the lightweight Harbor initializer,
shared by the root package and build metadata.

Within Harbor, `windows` owns native Windows path and process mechanics and
PowerShell command rendering.
Environment and Agent adapters consume those mechanics without changing the
reported host OS or choosing the Agent's tool shell. WorkBuddy owns dataset
contract recognition, WorkBuddyHostEnvironment workspace preparation, and
execution-format adapters; its verifier reuses the external runtime's registry,
hooks, and scoring engine. Host owns reusable filesystem and process mechanics.
External Dataset sources remain read-only, including during plugin loading.
For native WorkBuddy execution, the Host adapter records the host OS in Harbor's
in-memory Task environment configuration; Harbor uses it when injecting Skills.
The source Task and its scoring contract remain unchanged.

`psycheval.atif` is a separate, standard-library-only source-copy unit. It owns
strict ATIF validation, content recognition, and timestamp parsing.
`psycheval.conversion` owns adapter dispatch, normalization, and metadata
projection, using the existing types owned by `adapters.base`. Adapters own
retained-session directory discovery, inspection diagnostics, and resolution to concrete files.
Adapters also own exact session-ID lookup within their configured session root;
the shared input loader handles pathless CLI and workspace imports. Workspace
input parsing distinguishes existing paths from bare session IDs before loading.
Conversion
recursively normalizes embedded subagent results; one selected root remains one
source, with child navigation owned by the trajectory detail view. Imported ATIF
is validated without repair; only adapter conversion normalizes evidence.

The CLI and Harbor adapter share formats and one `peval.toml`, but not parser
ownership: the CLI reads workspace, adapter, Dataset, and mount fields; Harbor
owns the explicit parser for `[harbor.host]`. Applications pass explicitly
parsed settings to WorkBuddy configuration adaptation, which requires absolute
host roots. Host environments accept explicit workspace parameters
and never discover user configuration. Trusted child harnesses explicitly request
the generated `peval.json` protocol; ordinary Agent commands receive no evaluation
control configuration. The opt-in Host script verifier supplies that protocol
only while Harbor executes verification. See the [Host contract](reference/harbor.md).

The serve subtree owns one internal FastAPI application for the bundled browser
UI. `run_serve_command` owns listener selection, the single-process runtime, and
shutdown through Uvicorn; the application borrows that runtime and does not own
its lifecycle. The `/api` interface is not a public integration API and does not
publish interactive API documentation or a generated client contract.

The browser UI is one persistent document. The server renders every page shell
allowed for the current role and the requested route selects the initial page;
the browser application owns later navigation, page activation, and history.
Page adapters load on first activation and keep their DOM and draft state until
the document is unloaded. They consume explicit invalidation domains instead of
using navigation as a data-refresh mechanism. Agent launch changes use the
`assistant-config` domain; prompt-library changes use the independent
`prompt-assets` domain, so editing a prompt never replaces a live ACP
connection. Direct page URLs remain complete
entry points with the same server-side access checks.

`WorkspaceApp` owns the active page and maps the `catalog`, `reports`,
`dataset-registry`, `tasks`, and `assistant-config` invalidation domains to page
adapters. Page adapters do not import one another; shared browser primitives do
not depend on the Home runtime. Shared action feedback owns scoped messages and
the shell's transient notification host, using the Workspace runtime only to
return to an action's page. Shared action forms reuse the modal lifecycle.
Pages supply resource identities; the operation watcher reads the explicitly
supplied operation resource and invokes the page's refresh callback. Feedback
does not infer results from unrelated HTTP traffic. Serve owns human path-token
parsing at its input boundary; domain filesystem validation remains with its
existing owners. Tree and step-block controls share one clipboard
primitive for writes and copy feedback. One shared sidebar primitive owns lifecycle,
focus, mutual exclusion, and responsive width interaction for report previews
across Home and Reports, the Home Saved View rail, and Trial detail; the global
ACP drawer remains independent and stays mounted and open across in-document
Workspace page navigation. While that fixed drawer is open, the shell locks the
document scroller and makes the bounded Workspace pane its main-content scroll
owner, so pointer scrolling follows the pane under the pointer. `pretty-aui`
retains ownership of transcript scrolling inside the drawer, and closing the
drawer restores document scrolling. When a regular right sidebar is active, the
drawer follows that sidebar's effective content width; otherwise it uses the
same default desktop width scale rather than defining a second one. In the wide
in-page sidebar layout, its flush-right outer box also includes the Workspace
edge gutter so its visible left boundary aligns with a regular sidebar without
shrinking the main-content column by that gutter a second time. The shell also
keeps that outer edge gutter distinct from the shared inner gap between the
main-content column and the active side region. It measures the Workspace
scrollbar after transferring scroll ownership and
compensates the drawer outer box for non-overlay scrollbars; overlay scrollbars
remain zero-width and need no platform-specific constant.
HTML remains `no-store`, browser modules use strong ETags, and ECharts is loaded
only from the versioned immutable workspace asset rather than from a browser-side
third-party fallback.

One read-only ReportLibrary presents canonical source reports and imported
workspace report packages through separate adapters. Its canonical adapter
reads the current source `analysis.md`; its package adapter delegates to the
WorkspaceReportLibrary that owns `reports/`. The catalog contains only the
rebuildable canonical-report projection needed for listing and lookup, never a
second copy of the report body. Reports and ACP context use opaque report
references, so transport responses do not expose source paths or revisions.

The serve-owned ACP seam launches only administrator-configured local child
processes and carries bounded JSON-RPC frames through an authenticated,
same-origin WebSocket. An authenticated bridge remains bound to the exact
administrator session that opened it; logout revokes every bridge and process
owned by that session. On POSIX, shutdown owns the complete new-session process
group and escalates surviving descendants after the grace period even when the
group leader has already exited. The vendored `pretty-aui` standalone client owns ACP
negotiation, sessions, interactions, normalized state, and rendering; serve
does not maintain a second protocol projection. Psycheval supplies only a
workspace- and Agent-scoped browser preference adapter so new conversations can
reuse the currently selected model across reconnects and page loads, and asks
`pretty-aui` to apply the fixed `plan` mode before publishing every genuinely
new conversation. Existing conversations retain their Agent-owned mode and
model; recognition and session configuration remain owned by `pretty-aui`. The gateway
does not enter the retained-session conversion, report, workspace overlay, or
Harbor evidence paths. ACP conversations remain Agent-owned runtime state; an
explicit, bounded context adapter keeps an ordered set of evaluation references
and resolves their current content from the existing authorities without
transferring write ownership to the ACP client. Transient host notices belong to
the vendored `pretty-aui` transcript seam: Psycheval forwards successful
connection and context-selection outcomes to the selected session, routes
session-scoped errors to that loaded session, and does not persist or replay the
resulting rows. Before a chat is mounted, only initialization and connection
errors use the chat placeholder; connection progress and ordinary disconnects
have no separate notification projection. The vendored client renders the
context references as addable and individually removable composer chips, then
records each accepted turn's resolved items as collapsible transcript activities
rather than duplicating resolved content in serve-owned browser state.
`pretty-aui` also owns the model-facing user-message envelope and full-history
recovery that keep resolved context out of a restored user bubble and project
recoverable prompt prefixes as historical Context injection activities.
Attaching a source does not select a diagnosis prompt, fill the composer, or
send a message. The shared composer and controller reject blank prompts.
Its default React renderer also owns bounded tool presentation: trustworthy
Execute, Read, and ACP Diff payloads become semantic cards, while ambiguous
payloads remain lossless generic input/output sections. Psycheval supplies only
localized chrome and does not parse tool payloads or duplicate the renderer.
Psycheval neither parses Agent transcripts nor renews those recovered activities
as live host context references after a page load. A selected source is
resolved from its normalized local identity or Harbor mount, Job, Trial, and
optional step identity; live detail reads validate and load only that target
rather than rediscovering every configured source. When present, its current
canonical report is included as bounded context for review, not as a
publication guard. The context adapter resolves an ordered batch under one
global character budget; stable source identity is never displaced by large
trajectory content. Any terminal ACP turn asks the Psycheval host to refresh
current catalog/detail projections because a tool may have committed a report
before the turn completed or was cancelled. Generic chat event behavior
remains owned by `pretty-aui`.

## Repository topology

- `src/psycheval/` contains runtime code; Harbor adapters live in its `harbor/`
  subtree.
- `tests/harbor/` and `tests/peval/` are collected by the root pytest project.
- `src/psycheval/assets/web/` is the browser module graph distributed with the
  package and served directly by the local workspace. `web/` owns its Node test
  harness.
- `datasets/` contains maintained Harbor Datasets; `examples/` contains
  authoring examples, not maintained evaluation members.
- `skills/peval/` is the repository source of the project Agent Skill and is
  not package data. `peval init --skill <skill-dir>` explicitly installs or
  replaces one workspace copy at `.agents/skills/<name>/`.

## Dependency direction

Core CLI implementation may consume pinned Harbor interfaces and the explicit
`psycheval.harbor.datasets`, `psycheval.harbor.tasks`, and
`psycheval.harbor.workbuddy` services, the explicit host-settings parser in
`psycheval.harbor.runtime_config`, shared identifier rules, and the
`psycheval.harbor.windows` helpers for rendering Windows shell commands, but not
Agent, Environment, or harness internals. The implementations exchange only
owned configuration sections and explicit formats. Tasks invoke the installed
verifier rather than checkout-relative Python paths. Documentation and skills
consume public interfaces; runtime code reads a Skill only when its local
directory is explicitly supplied to `peval init --skill`.

Pydantic models own the validated CLI workspace configuration, HTTP request
shapes, and Problem responses. Large catalog, report, and Harbor projections
remain owned by their domain modules instead of being duplicated as transport
models. Uvicorn is the only production ASGI adapter; integration tests exercise
the same application through a test-owned Uvicorn host.

## Authority seams

Data authority and mutation rules are defined in
[State and data](reference/state-and-data.md).
