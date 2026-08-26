# State and Data

Psycheval separates authoritative evidence from user-authored overlays and
rebuildable projections.

| Data | Authority | Mutation rule |
| --- | --- | --- |
| Task, Job, Trial, result, reward, artifacts | Harbor files | Read-only to the CLI |
| Portable steps, calls, observations, timestamps, usage | ATIF trajectory | Strictly validate before writing |
| Aliases, state, notes, analysis, report bindings | Workspace overlay | Explicit user mutation |
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
interface. Task text is not copied into reports, catalog summaries, search
documents, or exports; live detail may expose only a safe Dataset/Task reference.
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
