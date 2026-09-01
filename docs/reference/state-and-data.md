# State and Data

Psycheval separates authoritative evidence from user-authored overlays and
rebuildable projections.

| Data | Authority | Mutation rule |
| --- | --- | --- |
| Task, Job, Trial, result, reward, artifacts | Harbor files | Read-only to ordinary CLI views |
| Trial evaluation report | Harbor Trial-root `analysis.md` | Publish only through `peval publish trial-analysis` |
| Portable steps, calls, observations, timestamps, usage | ATIF trajectory | Strictly validate before writing |
| Aliases, state, notes, local-source analysis, report bindings | Workspace overlay | Explicit user mutation |
| Catalog rows, summaries, JSON/XLSX exports | Derived data | Rebuildable from authorities |

## Trajectories and sidecars

Every CLI-exported `trajectory.json` is a complete ATIF-v1.7 document. A
`trajectory_meta.json` sidecar owns import context, source references, adapter
details, warnings, and presentation-only derivations. Mirrored trajectory facts
remain projections of ATIF and never become a second authority.

Conversion preserves ordered repeated events, typed calls and results, source
blocks, stable session identity, and explicit unknowns. It never invents a call
from prose. Existing ATIF imports are validated without repair. A Harbor
ATIF-v1.x artifact is exposed as v1.7 only when changing the schema label alone
passes the current strict validator; the compatibility view is not persisted.
Derived browser views render absolute timestamps as UTC without rewriting the
underlying ATIF, Harbor, or catalog values.
Live Harbor Task text is read on demand through the bounded Workspace Task file
interface. Task configuration, required instruction files, and Task ignore
rules are strict UTF-8, independent of the host locale. Task text is not copied
into reports, catalog summaries, search documents, or exports; live detail may
expose only a safe Dataset/Task reference. Task file-tree responses omit
`__pycache__` directories and their descendants as generated presentation noise;
named Task-skill snapshots also omit that generated cache from their readable
file set, size budget, and criterion revision. A named Task-skill snapshot is
limited to 1,000 authored files in addition to its per-file and aggregate byte
budgets. Authored Task files remain visible to validation, revision, copy, and
publish ownership.
The Workspace is the only browser presentation surface. It fetches derived data
through local HTTP interfaces and does not serialize that state into offline HTML
reports or Workspace snapshots.

## Telemetry

Inference aggregates retain sufficient statistics for weighted recomputation.
TTFT needs exact request-dispatch and first-token boundaries; decode throughput
also needs an exact terminal boundary and output usage. Cache rate uses explicit
cache-read measurements over inclusive prompt tokens. Missing evidence is
unknown, numeric zero remains a value, and Agent or wall duration is not
relabelled as model timing.

Leaderboard summaries cover every Trial matched by the current source state,
search, facets, and applied Saved Views, including browser-local Saved Views.
Pagination, sorting, and row selection do not change that scope. Leaderboard and
Saved View grouped summaries treat each measured Trial as one observation for
Count, Mean, and percentile statistics. Unknown Trial values are excluded while
an explicit numeric zero remains part of the distribution. Summary tables,
charts, and spreadsheet exports omit a metric only when its Count is zero in
every group. Grouped summaries remain exact and are never truncated or
approximated; a query whose distinct group count exceeds the service capacity is
rejected so the user can refine the scope or select an overall summary.

An explicit trajectory value wins over aligned supplemental Trial telemetry.
Optional telemetry failure does not invalidate a readable trajectory. Multiple
reward dimensions without an explicit or unambiguous scalar are not averaged
into a synthetic score.

## Identity and mutation

Stable source keys survive aliases, filtering, pagination, archival, and report
attachment. Display aliases never replace evidence identity. Workspace
mutations return or produce a generation; clients reconcile by generation and
stable key. Rebuilding a catalog or report never silently deletes original
inputs or Harbor-owned evidence.

## Harbor Trial analysis

A Harbor evaluation report has one authority: `<trial-dir>/analysis.md`.
Single-step and MultiStep Trial projections share that parent report. Step
directories, collected artifacts, nested log files, and the legacy workspace
`harbor/.../analysis.md` overlay are not report authorities and are not shown as
Trial analysis. Workspace report packages under `reports/` remain independent.

Publication is no-clobber by default. Creation binds the current Trial evidence
revision and named live Task-skill revision. Replacement additionally requires
the exact current analysis revision. The publisher recomputes every revision
under the workspace writer lease and a persistent Trial-root coordination lock
shared by workspaces that mount the same Trial. It rejects active Trials and
stale inputs, then atomically replaces only the Trial-root Markdown file. The
coordination lock is not report evidence and is excluded from source revisions.
A recorded/live Task digest mismatch remains analyzable but must be preserved as
prominent report provenance; a missing, ambiguous, invalid, or unreadable Task
or skill is an error.

For MultiStep Trials, catalog phase rows retain phase-scoped evidence revisions
for projection invalidation. Trial analysis publication and ACP context use the
parent Trial aggregate revision because every phase shares the same report.
