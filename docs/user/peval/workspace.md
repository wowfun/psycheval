# Workspaces

[简体中文](../../i18n/zh-CN/user/peval/workspace.md)

Initialize and serve a workspace:

```console
peval init -r .local/evaluation
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
directory; **Restore default** removes that override. Dataset IDs and paths are edited
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
`pretty-aui` session controls to create, select, or close conversations. You can
attach multiple sources, Tasks, or reports with the **Add context** control
above the prompt. Select an evaluation item, add it, and repeat; remove one with
the named close control on its chip. Adding the same reference again has no
effect. The drawer stays open when you switch Workspace pages; close it
explicitly with its close control, backdrop, or Escape. Page selection changes
do not silently alter attached references. Every attached reference is resolved
again for each prompt, so the Agent receives current bounded content in the
visible chip order.
When no Agent is configured, the connection control links directly to the ACP
Agent form in **Configuration**.
The composer can load any configured Markdown prompt asset; adding a source,
Task, or report selects the corresponding suggested asset without sending it.

Provision the Agent outside Psycheval first—for OpenCode, use `opencode auth
login` in a terminal when its provider needs authentication. The panel shows
messages, plans, tool progress, permission and elicitation requests, modes,
configuration, usage, and Agent-owned session history. Separate sessions may
run concurrently while one session accepts only one active prompt. Disconnecting
or closing `peval serve` terminates the gateway child process. Conversations
stay in Agent state and are never imported as evaluation evidence.

ACP Agents inherit the serve process environment and OS permissions. Only
configure executables you trust, and do not treat a permission card in the
drawer as a filesystem or process sandbox. The exact access and persistence
rules are in the [workspace reference](../../reference/workspace.md).

## Serve access

Before binding to a non-local address, follow the access rules in the
[workspace reference](../../reference/workspace.md).

Import authored analysis into a selected source reference with:

```console
peval import analysis -r .local/evaluation \
  --source-ref runs/default/psychevo/<session>/<cell> \
  -p analysis.json -p analysis.md
```
