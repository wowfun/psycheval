# peval-py Serve Workspace State

## Serve Workspace State

`peval-py serve` is backed by a selected peval-py workspace. Python-owned
configuration lives at `<workspace>/peval-py.toml`. The workspace config stores
optional top-level `locale`, built-in adapter default DB paths, and serve
defaults only. Peval-py does not create, read, or write a workspace
`state.db`; existing files with that name are ignored by peval-py workspace
state.

When `serve -r <workspace>` selects a root whose `peval-py.toml` does not yet
exist, serve creates the workspace before resolving its effective runtime
configuration. The initial process must therefore expose the generated adapter
`default_db_path` values to Source Manager without requiring a restart. Config
precedence remains workspace `peval-py.toml`, then explicit `-c/--config`, then
CLI overrides.

Serve may create a derived catalog at
`<workspace>/.cache/peval-py/serve-catalog.sqlite3`. It uses SQLite WAL, an
explicit schema version, and committed catalog generations. SQLite FTS5 with a
trigram tokenizer is a serve runtime requirement and is probed at startup; an
unavailable build fails with a clear startup error. Schema mismatch, corruption,
or an incomplete generation causes deletion and a cold rebuild rather than a
migration. The catalog contains no canonical user data and must be reconstructible
from Trial artifacts and `.peval/state.json`.

Serve may also create an ECharts cache at
`<workspace>/.cache/echarts/6.0.0/echarts.min.js` and a structured append-only
log at `<workspace>/logs/peval-py-serve.jsonl`.

Imported workspace analysis reports are durable artifacts, not cache entries.
Each report is stored as one package:

```text
<workspace>/reports/<report-id>/
  <original-name>.md|markdown|html|htm
  state.json
```

`<report-id>` uses the local time-ordered form
`YYYYMMDD-HHMMSS-ffffff`; a same-microsecond collision appends `-2`, `-3`, and
so on. `state.json` contains only an ordered, de-duplicated `source_keys`
array whose values are workspace-relative Trial cell paths such as
`runs/default/agent-a/c2/c2_t001`; the id, filename, format, and import time are
derived from the package directory and its one supported report file. Relative
cell references are intentionally human-editable and must not be absolute,
contain `..`, escape the workspace, or identify a path outside `runs/`. Imports
accept one regular UTF-8 file no larger than 20 MiB, copy its bytes into a
hidden temporary package, and atomically rename the completed package into
place. The source path is not retained or watched.

Report bindings identify exact Trial-cell sources rather than display session
ids or composed-report Trial keys. Serve mutations translate opaque runtime
source keys to relative cell paths before persistence; catalog reads preserve
all persisted paths but project only their currently resolved runtime source
keys. Missing sessions are silently omitted without rewriting state, so a
matching cell that later reappears restores the association. A valid report
with no current binding remains visible in report inventory. Explicit rebinding
atomically replaces the full source-key array and requires at least one current
readable source. Explicit deletion permanently removes the whole report
package. Incomplete temporary packages and committed but invalid packages do
not fail serve startup and do not enter the catalog.

Saved Leaderboard views are durable, human-editable workspace artifacts. Each
regular UTF-8 file directly under `<workspace>/views/` has the form

```md
---
schema_version: 1
group_by: agent
---
User notes.
```

The filename stem is the view name and the Markdown body is its notes. Filters
use the same state, literal search, Tags, Agent, Model, and Result semantics as
the serve Leaderboard; `group_by` is exactly `overall`, `agent`, or `model`.
Only non-default filters are written: omitted filters mean `active` source state
with an empty Search, Tags, Agent, Model, and Result selection. When any filter
is non-default, `filters` contains only that setting; `state: active` and any
empty/All filter are never written. The save dialog likewise shows only the
non-default filters, while always showing the selected grouping.
View names may be Unicode but are one filename stem: empty names, path
separators, `.`, `..`, and control characters are invalid. Saves write a
temporary sibling then atomically replace `<workspace>/views/<view-name>.md`.
Existing views require explicit overwrite confirmation. Symlinks, malformed
frontmatter, and unsupported schema or values are ignored during discovery so
they cannot break serve startup or the valid-view catalog.

Runtime source state lives beside each Trial cell in
`<cell>/.peval/state.json`. Missing `.peval/` or missing
`.peval/state.json` is not an error: a complete Trial cell without local source
state is treated as a readable active, non-refreshable artifact source with
default metadata. The state file is a minimal overlay with optional
`source_alias`, optional `source_tags` as an ordered string array, optional
archived state (`active = false`), optional latest status/error fields,
and no source provenance object. Derived fields such as source key, artifact
path, adapter/session/model display fields, refreshability, snapshot state, and
Trial summary fields are computed from the cell path plus
`agent/trajectory.json` and `agent/trajectory_meta.json`. Successful imports and
refreshes do not create or update a cell overlay unless they carry user overlay
data. When a mutation leaves no overlay fields, `state.json` is removed. Older
overlay files remain best-effort readable for alias, tags, active state, and
status/error, but legacy source provenance is ignored and dropped on the next
source mutation.

Refresh and import attempts append JSONL records to
`<workspace>/logs/peval-py-serve.jsonl` with time, status, source key, warning
count, and error summary. The log is evidence only; it is not a source index
and is not required to compose reports.

Active and archived readable sources are catalog summary rows and may be queried
independently or together. Each readable row may include a compact
`step_outline` with source `step_id`, normalized role, and optional duration so
the browser can render Trajectory Overview without loading step bodies. Sources
whose artifacts are missing or invalid remain
Source Manager rows with `last_status = "missing"` or `last_status = "error"`,
but are excluded from Leaderboard results and detail loading. The state layer
keeps only canonical Trial artifacts plus per-cell source state; the catalog
stores summaries and search text, never historical report blobs or step body
content.

Canonical Trial artifacts live under the peval run tree. The minimum persisted
unit is the Trial cell:

```text
<workspace>/runs/<analysis_eval_slug>/<agent-id>/<session-id>/<cell-key>/
  agent/trajectory.json
  agent/trajectory_meta.json
  .peval/state.json        # optional; present only for local overlay data
  notes.md
  analysis.json
  analysis.md
```

`<cell-key>` is `trajectory_meta.trial_key` after safe path-segment
normalization. A complete cell directory is a discoverable artifact fact even
when it has no `.peval/state.json`. `trajectory.json` is the ATIF-like agent
trajectory. `trajectory_meta.json` is the viewer/report sidecar for timing,
status, warnings, and step metadata. Cell-local `analysis.json`, `analysis.md`,
and `notes.md` are the persisted annotation truth for that Trial. Session-root
`analysis.json`, `analysis.md`, and `notes.md` belong to the whole session and
are reserved but not read by this version.

`serve` startup binds the local HTTP server first, publishes the last valid
catalog generation immediately when present, then imports explicit CLI sources
and reconciles `<workspace>/runs/<analysis_eval_slug>/<agent>/<session>/<cell>`
in the background. Discovery uses fixed-depth `scandir`, set-based identity
deduplication, and never follows symlinks. It does not search other eval slugs.
Each candidate receives a fingerprint covering `agent/trajectory.json`,
`agent/trajectory_meta.json`, `.peval/state.json`, `notes.md`, `analysis.json`,
and `analysis.md`. An unchanged cell does not parse JSON; a new or changed cell
parses trajectory and meta at most once during reconciliation. Removed cells
are absent from the next generation. A malformed cell is isolated as an error
or missing Source Manager row and does not abort publication.

Rows persist all Leaderboard summary fields, source state, and one normalized
search document. FTS5 trigram search is case-insensitive literal search over
messages, reasoning, tool calls, observations, session id, alias, tags, agent,
model, and status. Queries shorter than three characters use an escaped
case-insensitive `LIKE` over the cached search document. Search syntax is never
interpreted as an FTS expression supplied by the user.

Reconciliation constructs the next generation in one SQLite transaction and
atomically publishes it after all candidates are processed. Readers continue
to page, search, and load unchanged details from the prior generation while the
catalog reports `Checking runs`. With no valid generation, the shell remains in
an empty loading state. No watcher or periodic scan is used: generations change
only at startup validation, explicit Reload, import, or a mutation performed by
the running process.

The
Path source form may also import a local external workspace root, `runs/`,
`runs/<eval>`, or a directory above Trial cells; that import recursively finds
complete Trial cells, copies each cell into the current workspace run tree, and
writes an overlay only when needed for user state. External run trees are
read-only provenance; deleting a source deletes only the current workspace copy.
The served report JSON is computed from active readable source overlays plus
these artifacts and is not persisted as a complete blob.

Uploaded JSONL files are converted through the selected adapter. Uploaded ATIF
JSON trajectory objects and uploaded peval-py report JSON are accepted without
requiring a message adapter. Uploaded source payloads are limited to 20 MiB,
converted immediately, persisted only as canonical Trial artifacts plus optional
cell-local overlay data, and discarded after ingestion; raw uploaded files are
not written to disk or stored as blobs. When the uploaded source is a peval-py
report JSON, matching Trial `annotations.notes[]` are materialized into that
Trial cell's `notes.md`, matching `annotations.analysis[]` entries are
materialized into `analysis.json` and `analysis.md`, and report-level notes are
ignored until a session/report artifact model exists.

The Source Manager Path form accepts line-delimited batch input. Blank lines are
ignored. Each non-blank line is parsed and imported independently, so one bad
path does not block later paths. Multi-line Path/runs imports, multi-session
imports, Reload, and bulk archive/activate/delete enter the same background
writer queue. Operations continue after per-item failures and expose ordered
success/failure results plus completed/total progress. On completion a reconcile
publishes disk truth as one new generation. The same Path form may call same-origin `POST
/api/path-picker` to open a local native file picker and fill the textarea with
absolute file paths, one per line. Browser-native file inputs are not used for
this path-fill behavior because they do not expose absolute filesystem paths to
JavaScript. If no native picker backend is available or the picker fails, the
API returns a JSON error and the browser preserves the existing textarea value.
Source Manager Path, DB, and input-table imports whose adapter is `auto` or
omitted do not fall back to the configured default adapter when conversion needs
an adapter. The path tokens must identify exactly one available adapter, or the
mutation fails with a clear adapter-choice error. Batch Path imports keep this
as a per-line error so later inferable lines can still import.

One workspace permits one writer operation at a time. While reconciliation or
an operation is active, reads use the committed generation but all write
requests receive `409`; the browser disables writer controls. A second serve
process may read a committed generation, but cannot acquire the catalog writer
lease and receives a clear cache-busy error. The process retains only the
current and most recently completed operation status.

Serve source mutation endpoints return compact generation/change envelopes and
never return a full source list or all-source report. Source aliases remain
display metadata and API/state capability, but the Source Manager add/upload
forms do not expose alias inputs; aliases are edited from the source list or
provided by non-UI callers. Browser clients requery their current catalog page,
resolve retained cross-page selections, and conditionally reload the selected
detail after a mutation commits.

`peval-py init` writes only the Python-owned serve state described above.
Existing unrelated workspace files, including any old workspace `state.db`, are
left untouched, but they are neither created nor required.
