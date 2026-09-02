# State and Data

Psycheval separates authoritative evidence from user-authored overlays and
rebuildable projections.

| Data | Authority | Mutation rule |
| --- | --- | --- |
| Task, Job, Trial, result, reward, artifacts | Harbor files | Read-only to ordinary CLI views |
| Canonical evaluation report | Harbor parent Trial or local source-cell `analysis.md` | Atomic source-scoped upsert through EvaluationReports; local Markdown imports use the same writer |
| Portable steps, calls, observations, timestamps, usage | ATIF trajectory | Strictly validate before writing |
| Aliases, state, notes, local analysis JSON, report bindings | Workspace overlay | Explicit user mutation |
| Imported report package | Workspace `reports/` directory | Explicit package mutation through WorkspaceReportLibrary |
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
`__pycache__` directories and their descendants as generated presentation
noise. A Task attached to Copilot is user-supplied analysis context. Psycheval
does not treat it, a Task Skill path, or any other attachment as authoritative
evaluation criteria.
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

## Evaluation reports

Each source has at most one canonical Markdown evaluation report. A Harbor
source uses `<trial-dir>/analysis.md` at the parent Trial root. Single-step and
MultiStep phase references resolve to that parent, so every phase shares one
report. A local source uses `analysis.md` in its existing
`runs/.../<cell>/` directory. Step directories, collected artifacts, nested log
files, and the legacy workspace `harbor/.../analysis.md` overlay are not report
authorities. Workspace report packages under `reports/` remain independent.

EvaluationReports accepts only an existing readable local source or a finished
Harbor Trial. It validates the reviewed draft as a safe, bounded, non-empty
UTF-8 Markdown file, then serializes writers with the source coordination lock
and atomically replaces only canonical `analysis.md`. The stored bytes match
the reviewed draft; the publisher does not add provenance or other hidden
content. Publication does not read or compare evidence, evaluation-criteria, or
current-report revisions, and has no create, replace, force, or no-clobber
branch. Concurrent valid publications complete in lock order, and the last
completed write is authoritative. Local Markdown import uses the same lock and
atomic writer; local JSON import remains a separate overlay mutation.

Catalog fingerprints and generations are rebuildable invalidation details, not
publication guards. The canonical-report projection stores listing and lookup
metadata only. It indexes safe, non-empty UTF-8 Markdown, merges MultiStep
phases into one parent report, and never stores the report body. JSON-only,
blank, oversized, symlinked, or otherwise unsafe reports do not enter this
projection.

The read-only ReportLibrary combines this canonical adapter with the existing
workspace-package adapter. Canonical reads always return the current source
file; package reads delegate to WorkspaceReportLibrary. Stable opaque report
references identify the two kinds without encoding paths. Report replacement
does not change a reference, and browser or ACP projections do not disclose
source paths or revisions.
