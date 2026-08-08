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

Serve also mounts single-step Harbor Trials found at the workspace root or
under its conventional `jobs/` directory. A Trial appears as soon as
`agent/trajectory.json` is readable; Reload projects later trajectory and
`result.json` changes without modifying Harbor files. Add external Trial, Job,
or jobs roots relative to `peval-py.toml` when needed:

```toml
[harbor]
roots = ["../harbor/jobs"]
```

Multi-step Trials are shown with an unsupported diagnostic. Invalid or missing
linked sources retain their last valid projection and workspace annotations.

Path, DB, and input-table `auto` selection requires a unique inferred adapter.
JSONL upload falls back to workspace config; ATIF/report upload is adapter-free.
The browser add forms intentionally omit alias fields. CLI, manifests, JSON
interfaces, and saved-row inline editing support aliases.

Archive and delete change workspace state only; they do not delete original
files or databases. Linked Harbor Trials cannot be deleted and use Archive to
hide them. Refreshable sources can update cell-local `notes.md`; uploaded
snapshots remain read-only.

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
