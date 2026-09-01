# Workspaces

[简体中文](../../i18n/zh-CN/user/peval/workspace.md)

Initialize and serve a workspace:

```console
peval init -r .local/evaluation
peval init -r .local/evaluation --skill skills/peval
peval serve -r .local/evaluation
```

Workspace discovery and initialization semantics live in the
[workspace reference](../../reference/workspace.md).

## Unified configuration

One file may configure both the CLI and Harbor host execution:

```toml
description = "Nightly evaluation workspace"

[adapters.psychevo]
default_db_path = "~/.psychevo/state.db"

[harbor.host]
workdir_root = "../workspaces"

[[harbor.datasets]]
id = "pbench"
path = "../datasets/pbench-v1.0"

[[harbor.mounts]]
id = "nightly"
path = "../jobs"
dataset_ids = ["pbench"]

[[acp.agents]]
id = "opencode"
title = "OpenCode"
command = "opencode"
args = ["acp"]
```

Use `-r`/`--root` to select a workspace. Without it, `peval` discovers
`peval.toml` from the current directory and its parents (or `PEVAL_ROOT`). The
file is validated strictly, so remove obsolete or misspelled fields instead of
expecting them to be ignored.

Configuration ownership and path semantics live in the
[workspace reference](../../reference/workspace.md).

The administrator-only **Configuration** page (`/config`) is the UI for
trajectory ingestion, ACP Agents, prompt assets, Dataset registration, and
Harbor mounts. **Add ACP agent** opens a form panel seeded with an OpenCode
template; configured entries remain editable as direct executable-and-argument
arrays. Changes apply immediately, and changing or removing a connected Agent
stops its process. Repository Markdown files provide the default prompts.
Editing one in the page writes a same-name override to the workspace `prompts/`
directory; **Restore default** removes that override. The four English prompts
and their four Simplified Chinese counterparts are separate assets, so each can
be customized or restored without changing its translation. Dataset IDs and paths are edited
directly in the registry table. Registering an existing Dataset
requires only its path; adding a Jobs mount likewise requires only the Jobs path.
Each generated ID uses the directory basename when it is path-safe and unique,
or a random path-safe ID when the basename is invalid or already used. A new
mount starts without Dataset associations. Both registries use editable tables:
double-click a Mount ID, Jobs path, or ordered Datasets cell to edit it, or edit
a Dataset's Harbor mounts cell to change membership. Association editors
complete only registered IDs; adding a Dataset from the Dataset table appends it
to each selected Mount's evidence lookup order. Selected Mounts can be removed
as one atomic operation without deleting Jobs files. Unregistering a Dataset
likewise leaves its files in place and is rejected while a mount still references
it. Handwritten `peval.toml` entries still require explicit IDs.

The **Datasets** page manages Tasks only. Double-click a Task cell to rename it,
select rows to archive, restore, or permanently delete them, and use **Sync
manifest** only when `dataset.toml` should be updated. The **Leaderboard** owns
the corresponding trajectory lifecycle, including archived views and permanent
source deletion.

Home, Datasets, Reports, and Configuration share one persistent browser
document. Their direct URLs still open the named page, while navigation and the
browser back/forward controls switch pages without reloading the document.
Visited pages retain their selection, scroll position, and unsaved Dataset file
or Report binding draft. Use each page's Reload or Rescan action for external
filesystem changes; a related mutation made in another page refreshes the stale
page when it is next activated. Reloading or closing the browser still warns
before discarding an unsaved draft.

## Psycheval Copilot

After adding an allowlisted Agent such as OpenCode in Configuration, use
**Copilot** in the administrator header. Connect the Agent and use the
`pretty-aui` session controls to create, select, or close conversations. Select
a model in the composer and new conversations reuse it; the preference survives
page reloads for the same Workspace and Agent. Existing conversations retain
their own Agent-managed model. Every new conversation starts in the Agent's
`plan` mode, while an opened conversation retains its Agent-managed mode. Attach
multiple sources, Tasks, or reports with
the **Add context** control
above the prompt. Select an evaluation item, add it, and repeat; remove one with
the named close control on its chip. Adding the same reference again has no
effect. The drawer stays open when you switch Workspace pages; close it
explicitly with its close control, backdrop, or Escape. Page selection changes
do not silently alter attached references. Every attached reference is resolved
again for each prompt, so the Agent receives current bounded content in the
visible chip order.

Connection success, context attachment, duplicate attachment, removal, and
related errors appear as ordered, low-emphasis rows in the session transcript.
They exist only in the current browser controller and are neither sent to the
Agent nor restored from session history. An error that occurs before the chat is
available appears in the empty chat placeholder; connection progress and a
normal disconnect do not add notification rows.

For a live turn, the transcript shows each submitted item as a **Context
injection** activity while the user bubble and its Copy action keep only the
original prompt. The client adds an explicit model-facing boundary around that
prompt, so reopening a conversation written by the current client can recover
the original user content even when the Agent flattened the context and prompt
into plain text. Restored history recreates best-effort **Context injection**
activities from that prompt prefix: preserved metadata retains distinct items,
while flattened content appears as one recovered item. These historical rows do
not become live Workspace references. Conversations created before this boundary
format are displayed exactly as the Agent replays them because their context and
user content cannot be separated safely.

When no Agent is configured, the connection control links directly to the ACP
Agent form in **Configuration**.
The composer can load any configured Markdown prompt asset; adding a source,
Task, or report selects the corresponding suggested asset without sending it.
All eight language variants remain available. A fresh Chinese page starts with
the Chinese evaluation-review prompt and recommends Chinese context prompts;
other locales use English. An existing valid saved selection always wins over
that locale default.

Provision the Agent outside Psycheval first. For OpenCode, use `opencode auth
login` in a terminal when its provider needs authentication. The panel shows
messages, plans, tool progress, permission and elicitation requests, modes,
configuration, usage, and Agent-owned session history. Separate sessions may
run concurrently while one session accepts only one active prompt. Disconnecting
or closing `peval serve` terminates the gateway child process. Conversations
stay in Agent state and are never imported as evaluation evidence.

Expand a tool row to inspect its structured result. Recognized Execute, Read,
and file-change calls use terminal, source, and diff cards; other calls retain
separate input and output sections. Long source and diff bodies keep their head
and tail visible until expanded. Each available Copy control copies the semantic
body for its section—such as raw command output or file text—without card labels,
line-number gutters, or command chrome.

ACP Agents inherit the serve process environment and OS permissions. Only
configure executables you trust, and do not treat a permission card in the
drawer as a filesystem or process sandbox. The exact access and persistence
rules are in the [workspace reference](../../reference/workspace.md).

## Skill-based Trial evaluation

From the Psycheval checkout root, explicitly install the repository Skill with
`peval init -r .local/evaluation --skill skills/peval`. The option replaces the
complete same-name workspace copy; plain `peval init` does not install a Skill.
Start a new Copilot session after an install or replacement, attach one or more
Harbor Trials, and name the Task skill to evaluate. The Copilot reads each Trial
through its source reference and reads the named live Task criterion from
`environment/skills/<name>`.

The skill drafts one standard Markdown report per parent Trial while the session
is in plan mode. Review the draft and displayed evidence, skill, and current
analysis revisions. Then manually switch to execute/build mode and confirm
publication. The write is revision-bound and no-clobber; replacing an existing
report also requires its exact current revision. Single-step and MultiStep
phases share `<trial-dir>/analysis.md`, which the Trial detail view reads after
the completed turn refreshes the catalog.

## Serve access

Before binding to a non-local address, follow the access rules in the
[workspace reference](../../reference/workspace.md).

Import authored analysis into a selected local Trial-cell source reference
with:

```console
peval import analysis -r .local/evaluation \
  --source-ref runs/default/psychevo/<session>/<cell> \
  -p analysis.json -p analysis.md
```
