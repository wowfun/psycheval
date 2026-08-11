# Eval Workspace

## Initialize and Serve

```bash
peval-py init --root .local/peval-py
peval-py serve --root .local/peval-py
```

`init` creates only `peval-py.toml` and `state.db`, preserving an existing valid
state path. `serve` resolves an explicit root, `PEVAL_ROOT`, or a current/parent
config. It starts with an empty shell, then lazily loads catalog and selected
report data.

The local page uses a cached ECharts 6.0.0 asset and falls back to its fixed CDN
only if the local asset cannot load.

## Sources

Source Manager imports Session/ATIF paths, supported SQLite DBs, input tables,
JSONL, ATIF JSON, and normalized report JSON. Path and DB forms accept multiple
quoted paths and preserve Windows/UNC paths; compatible WSL mount paths are
resolved on POSIX.

Serve reads single-step Harbor Trials directly from explicitly mounted jobs
roots. There is no implicit workspace or `workspace/jobs` discovery. Give each
mount a stable lowercase ID; relative paths resolve from `peval-py.toml`:

```toml
[[harbor.mounts]]
id = "jobs-2026-08-08"
path = "../harbor/jobs"
```

The source reference is
`harbor/<mount-id>/<job-name>/<trial-name>`. Reload reads the current
trajectory, config, lock, result, reward, and status from Harbor without
copying them into the workspace. Multi-step Trials show an unsupported
diagnostic, and invalid Trials show their current error without a last-good
trajectory. A deleted Trial disappears unless a user overlay or report binding
still refers to it; retained missing rows reconnect when the same source
reference returns.

Older Harbor ATIF-v1.x trajectories are accepted only when a schema-label-only
compatibility view passes the complete current validator. Serve derives missing
aggregate counts from canonical steps and may use the matching Harbor result or
structurally aligned Trial telemetry for missing timing and accounting fields.
This includes OpenCode's Trial database, Psychevo's Trial-owned database and
runtime trace, and a Hermes session export. Session, step, message, and tool-call
identities must align where they share a namespace. Harbor's Hermes wrapper and
the native Hermes export use different session IDs, so their proof is same-Trial
containment plus exact step/message/tool-call alignment. Explicit trajectory
values always win. Exact runtime timing takes precedence over a bounded
model-boundary estimate. Estimates remain visible in model-duration summaries
with their `duration_source` provenance.
A failed Trial without a trajectory remains visible with the current Harbor
exception as a Source Manager diagnostic, but cannot be opened or exported as a
trajectory report.

Archive, alias, category, tags, notes, and analysis are lazy workspace overlays
under `harbor/<mount-id>/<job-name>/<trial-name>/`. Merely browsing or reloading
does not create that directory. `[harbor].roots` and `harbor-link.json` belong
to the incompatible legacy projection layout; initialize a new workspace
instead of migrating it in place.

Path, DB, and input-table `auto` selection requires a unique inferred adapter.
JSONL upload falls back to workspace config; ATIF/report upload is adapter-free.
The browser add forms intentionally omit alias fields. CLI, manifests, JSON
interfaces, and saved-row inline editing support aliases.

Archive and delete change workspace state only; they do not delete original
files or databases. Linked Harbor Trials cannot be deleted and use Archive to
hide them. Refreshable Harbor sources update overlay `notes.md`; uploaded
snapshots remain read-only. `peval-py import analysis --source-ref ...` targets
either a local Trial artifact or a Harbor overlay by its source reference.

## Selection and Summary

Leaderboard and Source Manager keep independent selections across pages. Header
checkboxes toggle only the current page, while actions consume the complete
retained selection. Sources that cease to exist are reconciled out.

Live serve displays Summary for zero, one, or multiple rows, using an empty
shell at zero. A workspace snapshot must contain at least one matched row and
shows Summary from one row onward.

## Exports

| Export | Scope |
| --- | --- |
| Table `.xlsx` | Every row in the complete unpaginated query; ignores selection. |
| JSON Report | All retained selected keys, or the current catalog page when none are selected; at most 100 cells. |
| Workspace snapshot `.html` | Complete query, or query intersected with retained selection; at most 100 final rows. |
| Summary `.xlsx` | Current visible Leaderboard page; ignores selection. |

The serve menu contains Table, JSON Report, and Workspace snapshot. There is no
legacy HTML Report export; snapshot HTML is the self-contained workspace form.

Synchronous single-source mutations return compact generation/change data.
Bulk reload, state, and delete operations return queued status and are polled;
neither response shape embeds a complete report.
