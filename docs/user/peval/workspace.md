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

Failed Trials can retain an **incomplete diagnostic trajectory**. Open the usual
trajectory view to inspect the messages and tool activity received before the
failure; the Trial keeps its original error status. Windows cleanup warnings
include retained paths and do not prevent scoring valid evidence. Diagnostic
trajectories are not grading inputs. See the [Host ACP contract](../../reference/harbor.md#host-acp-agent).

## Unified configuration

### Inspect and try Judge rubrics

In a Trial's **Verification** panel, open a rubric and choose **Actual prompt**
to read its retained request, copy messages, or download the snapshot. This
does not call a model. Choose **Try rubric** (or select several rubrics) to edit
a draft, choose a model profile, preview the unsent prompt, and run it. The panel
shows the original and current verdicts and reasons, with expandable actual
messages. Each Trial keeps only its latest attempt in page memory. Closing the
panel, changing Trials or navigating within the application preserves drafts and
results; refreshing or closing the page clears them. Only one run executes per
page. Closing the panel leaves it active; use **Cancel** to stop and discard it.
For multi-step Trials, select the desired step's row in the workspace.

Add experiment profiles under **Configuration → Judge profiles**, or in
`peval.toml`:

```toml
[judge]
default_profile = "review"

[judge.profiles.review]
title = "Rubric review"
base_url = "https://api.example.com/v1"
model = "judge-model"
api_key = "${JUDGE_API_KEY}"
reasoning_effort = "high"
```

Export the referenced environment variable in the shell that starts `peval`.
Preview does not need the credential; execution does. The CLI offers the same
workflow (replace the source reference and rubric IDs with your Trial's values):

```console
peval judge inspect -r .local/evaluation --source-ref harbor/nightly/job/trial --export-config draft.yaml
peval judge prompt -r .local/evaluation --source-ref harbor/nightly/job/trial --rubric fidelity
peval judge preview -r .local/evaluation --source-ref harbor/nightly/job/trial --rubric fidelity --judge-config draft.yaml --profile review
peval judge run -r .local/evaluation --source-ref harbor/nightly/job/trial --rubric fidelity --rubric completeness --judge-config draft.yaml --profile review
```

Use `-p PATH_TO_TRIAL` instead of `--source-ref`; add `--step NAME` for a
multi-step Trial. Historical trials without an instruction snapshot require
`--instruction instruction.md` or an explicit `--task TASK_DIRECTORY`.
Experiments support the generic YAML Judge and preserve original scores and
Task files. See [Judge inspection and runs](../../reference/judge-runs.md)
for input, lifetime and permission semantics. CLI runs print results directly;
Ctrl+C cancels. Only explicit exports write files.

### Show custom metrics

Publish numeric Trial measurements in ATIF `final_metrics.extra`, or scores in
the verifier's `reward.json` (Harbor records these in the Trial result). For
example, `{"energy_wh": 2.5}` becomes `atif.extra:energy_wh`. In `peval.toml`:

```toml
[metrics."atif.extra:energy_wh"]
label = "Energy"
unit = "Wh"
direction = "lower"
```

After reloading configuration and rescanning, use **Columns** on the leaderboard
or **Metrics** on Summary to search and enable it. Summary starts with the original ten
metrics; its selection also controls exports. Neutral metrics work in tables
and bars; a direction admits them to radar. Configuration is optional. See
[metric descriptions](../../reference/workspace.md#metric-descriptions).

Hover over a metric or unavailable metric choice to inspect its source, basis,
coverage and missing reason. Mixed summaries keep their numeric aggregates and
explain differing formulas and Trial counts. Decode TPS measures effective output
throughput including retry waiting; provenance is also retained in JSON and Excel.

### Other workspace settings

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
trajectory ingestion, ACP Agents, and prompt assets.
**Add ACP agent** opens a form panel seeded with an OpenCode
template; configured entries remain editable as direct executable-and-argument
arrays. Changes apply immediately, and changing or removing a connected Agent
stops its process. Repository Markdown files provide the default prompts.
Editing one in the page writes a same-name override to the workspace `prompts/`
directory; **Restore default** removes that override. The four English prompts
and their four Simplified Chinese counterparts are separate assets, so each can
be customized or restored without changing its translation.

Manage Dataset registrations above the Tasks table on **Datasets**. Open
**Harbor mounts** above the Jobs table to manage mounted result directories.
Dataset IDs and paths are edited directly in the registry table. Registering an existing Dataset
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

The **Datasets** page initially shows every registered Task. Click a Dataset row
to filter Tasks, then **Clear filters** to return to all Datasets. Management
checkboxes do not select a Dataset or open details. Click a Task row to open its
resizable right sidebar; closing it returns focus to the row. File browsing,
Markdown preview and editing remain there. Switching Tasks protects unsaved file
drafts. Double-click a Task cell to rename it, select rows to archive, restore or
permanently delete them, and use **Sync manifest** only when `dataset.toml` should
be updated.

The **Jobs** table combines managed runs and individual mounted Jobs, deduplicated
by result directory. Click a row for progress, logs and paged results; mounted
Jobs expose retained results without process controls. Below it, **New run** uses
the same searchable, sortable Task table. Checkboxes select Tasks across filters;
clicking a row opens read-only details without changing the run selection.
Guests can select Tasks and preview configuration but cannot start a run.

Both tables show **Note**, **Reports**, and actual Task or root Trial counts.
Unavailable counts display a dash. Double-click Note, or focus it and press Enter,
to edit multiline Markdown; Save and Cancel retain line breaks. Notes are saved
in workspace collection overlays, leaving source directories unchanged. Reports
counts active associated reports and opens the Reports page with that filter.
Guests see notes and report links; paths, mount relationships and management
controls are administrator-only.

Administrators can archive Jobs with verified completion. Archival excludes all
of that Job's Trials from Home discovery, filtering, summaries and exports without
deleting files or changing scores. **Show archived** exposes retained counts and
Restore; restored Jobs are discovered normally. Reports are not archived with
their Job. Collection storage and lifecycle rules live in the
[state contract](../../reference/state-and-data.md#collection-overlays).

Home, Datasets, Jobs, Reports, and Configuration share one persistent browser
document. Their direct URLs still open the named page, while navigation and the
browser back/forward controls switch pages without reloading the document.
Visited pages retain their selection, scroll position, and unsaved Dataset file
or Report binding draft. Use each page's Reload or Rescan action for external
filesystem changes; a related mutation made in another page refreshes the stale
page when it is next activated. Reloading or closing the browser still warns
before discarding an unsaved draft.

Use **Copy link** on the Leaderboard or a Trial/report reader to share its current
location. The address bar follows opened details and current conditions; links
restore filtering, sorting, pagination, aggregate display and the selected
trajectory, step or report tab. Applied Saved Views carry their actual conditions,
including browser-local Views, so recipients need no matching saved definition.
If a query reports too many applied View conditions, choose fewer Views before
retrying.
Opening a link does not save Views or include unsaved edits. Recipients need
access to the same workbench; results reflect its current data. Browser Back and
Forward restore object/page navigation, while condition changes replace the
current entry. Invalid links or links exceeding 64 KiB show an error; **Open
default view** explicitly clears the requested conditions. See the
[location contract](../../reference/state-and-data.md#shareable-workspace-locations).

The **Reports** page combines canonical evaluation reports and imported packages
in one searchable library. It reads canonical content from the current source
`analysis.md`; imported content stays in its workspace package. Administrators can
edit manual associations and archive, restore, or permanently delete either kind
from the detail panel. Use the Active, Archived, or All filter to find reports.
If local source evidence becomes unreadable, its retained report can still be read or
deleted. Damaged imported packages remain listed for deletion; their preview
may be unavailable.
Archived reports remain readable but disappear from the default list and Home's
Reports column. Publishing updated content keeps a report archived. Deletion
removes the report body and management metadata while preserving sessions, Trial
evidence, and imported original files. A later publication starts unarchived.
See the [report data contract](../../reference/state-and-data.md#evaluation-reports).
Guests can preview either kind through the same bounded renderer, but do not
receive source paths or revision metadata.

## Psycheval Copilot

After adding an allowlisted Agent such as OpenCode in Configuration, use
**Copilot** in the administrator header. Connect the Agent and use the
`pretty-aui` session controls to create, select, or close conversations. Select
a model in the composer and new conversations reuse it; the preference survives
page reloads for the same Workspace and Agent. Existing conversations retain
their own Agent-managed model. Every new conversation starts in the Agent's
`plan` mode, while an opened conversation retains its Agent-managed mode.

Use **+** for images and Agent commands, or **Prompts** for templates. Select a source, Task, step or report, then choose **References** above the input. The current object starts selected; related materials
are optional. Review the locations and insert the selected text. References and
templates append after your existing draft, remain editable and never send
automatically. They are ordinary text and are not repeated on later turns.
Source references include `source_ref`, `peval view tr` guidance and real evidence
paths. Steps also identify their trajectory, avoiding confusion between root and
child events with the same number. Task observations are cached catalog values,
not fresh verification. WorkBuddy references include the Dataset root for
ancestor configuration and shared verifier files.

The prompt submenu groups all eight templates by Chinese and English, with the
interface language first. No template is selected automatically. Workspace
customizations retain their text and remain marked in Configuration. Agent
commands preserve the message body and images and wait for you to send.

Select, paste or drop PNG, JPEG, WebP or GIF images into the composer. Mixed
clipboard content prefers text. Images retain original bytes; the composer
shows used and remaining budget. Image-only messages are supported. Unsupported
Agent capabilities and oversized images are refused without losing the draft;
ordinary files are not uploaded. Local admission cannot guarantee an Agent or
provider's full-conversation image limits.

The drawer stays open across Workspace page navigation. Drafts remain with each
session in the same controller, including reconnect after unexpected connection
failure. Explicit disconnect, changing Agent, reload and controller teardown end
that guarantee. Definitely undelivered failures preserve the submitted draft;
later edits are never overwritten. **Append undelivered draft** explicitly merges
a retained failed submission; an over-budget merge changes neither input.
Uncertain delivery never triggers an automatic resend.

Connection notices and errors stay in their owning live transcript. Older
**Context injection** activities remain readable when restored from Agent
history and never become new attachments. After every terminal turn, including
cancellation, the Workspace refreshes its catalog because a tool may have
committed a report. When no Agent is configured, the connection control links to
the ACP Agent form in **Configuration**.

Referenced paths disclose actual locations to the configured local Agent.
Direct filesystem reads bypass Psycheval HTTP redaction and may require Agent
permission. A read-only report label is guidance, not an OS sandbox; canonical
reports still use `peval publish evaluation-report`.

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
body for its section, such as raw command output or file text, without card labels,
line-number gutters, or command chrome.

ACP Agents inherit the serve process environment and OS permissions. Only
configure executables you trust, and do not treat a permission card in the
drawer as a filesystem or process sandbox. The exact access and persistence
rules are in the [workspace reference](../../reference/workspace.md).

## Free-form evaluation reports

From the Psycheval checkout root, explicitly install the repository Skill with
`peval init -r .local/evaluation --skill skills/peval`. The option replaces the
complete same-name workspace copy; plain `peval init` does not install a Skill.
Start a new Copilot session after an install or replacement and insert a reference to a Harbor
Trial or imported local session. Enter a non-blank evaluation brief and supply
any useful basis through the message or inserted references, such as a Task, a
report, a live Task context, or a Skill path with an explicit request to read it. Psycheval does not discover,
validate, or rank those materials as authoritative evaluation criteria. When a
turn contains more than one source and the publication target is unclear, the
Skill asks which source to use. Batch work is reviewed and published one report
at a time.

The Skill drafts the standard Markdown report in plan mode. Its template covers
the evaluation brief and supplied basis, executive conclusion, evaluation
questions and coverage, findings, observed strengths, recommendations, metrics,
and limitations and confidence. It distinguishes retained Trial evidence,
live context observed during analysis, user-supplied material, and inference;
it does not claim that live content records the Trial-time state.

Review the complete draft after every revision. To publish it, manually switch
to execute/build mode and explicitly confirm the exact draft. This review is a
Skill workflow, not a server-side approval token. The publisher stores the
reviewed Markdown unchanged:

```console
peval publish evaluation-report -r .local/evaluation \
  --source-ref <ref> -p <approved-draft.md>
```

Harbor parent and MultiStep phase references share the parent Trial
`analysis.md`; imported local sessions use their cell `analysis.md`. Publication
does not use revisions or a separate replace flag. If a report already exists,
the confirmed publication replaces it atomically; concurrent publications are
serialized and the last completed write wins. The Home Trial detail and the
**Reports** library read this canonical file after the
catalog refreshes.

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
