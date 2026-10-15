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
Derived browser views use the workspace's [display timezone](workspace.md#display-timezone)
without rewriting the underlying ATIF, Harbor, or catalog values.

Converted trajectories retain adapter-owned explicit trajectory IDs; only absent
IDs are derived from Agent and session identity. Embedded subagent trajectories
are complete ATIF documents with independent steps and metrics, referenced by
their immediate parent's observations. A reference to an embedded child remains
navigable when it also carries an external trajectory path; external-only
references do not create an embedded-child navigation action. Sidecars project child runtime metadata
and diagnostics by trajectory ID. A child's metrics are not added to its parent
or counted as another evaluation source; detail navigation selects the child's
own evidence within the root source.
Sources with embedded children show left-aligned tree navigation for the complete
family; sources without children omit it. The detail sidebar keeps the tree in
its header, with bounded scrolling separate from the step list, so long histories
and large families cannot displace either navigation or steps.
Each tree row has a right-aligned Copy action for that trajectory's last Agent
step's message, without changing the selected trajectory. It copies the original
message text (text blocks in order for multimodal messages), excluding reasoning
and tool results. A missing or blank final Agent message disables the action;
it does not fall back to an earlier response. Copy success or failure is visible.
Each step block also has a right-aligned Copy action for its displayed body:
Message, System Prompt, Reasoning, tool arguments, or observation content.
Structured bodies copy as the displayed formatted JSON. Headings, tool metadata,
and navigation controls are excluded; blank bodies disable Copy. Copying a block
preserves the selected trajectory and step expansion state.
Direct ATIF inspection projects portable runtime metadata for the complete
embedded family through the same sidecar projector as workspace reads. Report
inspection fills child metadata from ATIF while retaining existing sidecar
diagnostics and source-level evaluation fields. Malformed child identities in
report JSON produce validation errors before child metadata projection.

Claude preserves file ordering and merges assistant fragments by message ID,
counting the last valid usage once per response. Prompt usage includes ordinary
input, cache reads, and cache writes; missing measurements remain unknown.
Aggregate usage input totals use the same inclusive prompt count; original
uncached input remains a separate usage component.
Partial usage updates retain the last valid value of each measured component.
Canonical prompt totals require measurements for all three input components;
an omitted cache component is unknown, not an assumed zero. Known components
remain available in usage evidence even when the inclusive total is unknown.
The canonical cached-token subset is also omitted when that prompt total is
unknown, as required by ATIF; the raw cache measurement remains in usage evidence.
Repeated identical Claude conversion diagnostics are displayed once per trajectory.
Child session identities include their Agent ID so an explicitly imported child
cannot replace its root's cell; Claude source metadata retains the native session ID.
Session cost-state records are retained in `extra.claude.cost_state` as source
summary evidence; they do not supply trajectory totals or displayed cost metrics.
Tool-result agent IDs are the authority for child association. Child files must
belong to the selected session's subagents directory and match its identity;
missing, invalid, or cyclic links remain visible diagnostics. Association metadata
must identify a unique tool result: ambiguous batch metadata and orphan
child links are diagnosed without guessing a parent call. Per-result metadata
can associate each child independently. Families are trees; a second parent of
an already embedded child receives an explicit omitted-link diagnostic.
Child sidecar adapter identity follows the root input adapter, including ATIF
imports. Retained source files are never modified. Task notifications,
compaction, and local-command
context retain their source classification; bookkeeping does not create turns.
An explicit native Claude import stores its concrete source binding in the local
source overlay for administrator-requested refresh. The canonical cell remains
the read authority; reads do not consult the original logs. Imported ATIF and
copied cells do not activate source paths from their metadata. Refresh replaces
the derived family only after conversion succeeds and preserves the cell identity.
The detail view's Refresh source action is available to administrators for
refreshable sources, including linked Harbor Trials and native Claude imports.
It operates on the root source even when a child trajectory is selected; Harbor
refresh reloads its linked Trial evidence. Snapshot imports have no refresh action.
Live Harbor Task text is read on demand through the bounded Workspace Task file
interface. Task configuration, required instruction files, and Task ignore
rules are strict UTF-8, independent of the host locale. Task text is not copied
into reports, catalog summaries, search documents, or exports; live detail may
expose only a safe Dataset/Task reference. That reference requires a unique
association within the Trial's configured mount, using each Dataset's resolved
Task root, including manifest-defined nested layouts. Task file-tree responses omit
`__pycache__` directories and their descendants as generated presentation
noise. A Task attached to Copilot is user-supplied analysis context. Psycheval
does not treat it, a Task Skill path, or any other attachment as authoritative
evaluation criteria.
The Workspace is the only browser presentation surface. It fetches derived data
through local HTTP interfaces and does not serialize that state into offline HTML
reports or Workspace snapshots.

The Home Leaderboard identifies a Trial's Dataset by its registered ID, using
the same unique mounted Task-root association as live detail. An unresolved or
ambiguous association has no Dataset value. The catalog stores only the derived
ID and rechecks associations during reconciliation, including registration and
mount changes that leave Trial files unchanged. Dataset is the first data column
by default and follows the existing column layout and query-wide empty-column
visibility rules. Dataset filters match any selected ID and intersect with other
conditions and applied Saved Views. Filtering, sorting, summaries, and exports
use the complete query across pages; the detailed spreadsheet includes Dataset
as its first column and preserves the table's requested sort order. Dataset
filtering does not add a Saved View field or a
summary grouping dimension.
Dataset sorting places missing values last in both directions. Direct edits to
workspace configuration become visible after configuration reload and source
reconciliation; the catalog does not watch configuration files itself.

The Leaderboard Notes column reads each row's workspace note from the catalog,
independently of the selected Trial or loaded detail. It shows a whitespace-folded
excerpt and exposes the complete note as hover text when abbreviated. Notes
use the detail reader's 1 MiB UTF-8 byte limit per file; catalog rows carry that
bounded full content so hover text does not require opening a detail. Missing,
unreadable, and oversized files project an empty note.
Note presence reflects non-blank readable content. Saving or clearing a note refreshes
the catalog projection through the existing generation-aware mutation flow;
the workspace note remains authoritative.

## Telemetry

Inference aggregates retain sufficient statistics for weighted recomputation.
TTFT needs exact request-dispatch and first-token boundaries; decode throughput
also needs an exact terminal boundary and output usage. Cache rate uses explicit
cache-read measurements over inclusive prompt tokens. Missing evidence is
unknown, numeric zero remains a value, and Agent or wall duration is not
relabelled as model timing.

Active duration sums recorded Agent-step and tool execution contributions. It
measures aggregate activity rather than the union of elapsed intervals; parallel
contributions can overlap. Wall duration remains the separate elapsed measure.
Projected durations accept only nonnegative integer milliseconds, excluding
booleans, numeric strings, fractional values, and non-finite numbers.

Tool execution timing is projected from matching observation results' `extra`,
falling back to the tool call's `extra` when the results omit timing or contain
only invalid measurements. An explicit unknown result duration
takes precedence over a call measurement and clears prior sidecar timing;
unknown durations are omitted from the sidecar. Projected tool durations are
nonnegative integer milliseconds, with optional nonblank string source labels from the
same location. Multiple matching results must agree on a duration; conflicting
measurements remain unknown, and differing source labels are omitted. Without
canonical timing, valid sidecar derivations are retained. All local-cell readers
project mirrored facts from ATIF before deriving summaries. Schema and projection
versions are independent. A projection mismatch makes the current generation
unavailable and refreshes cached rows in the next reconciliation transaction,
even when source fingerprints are unchanged. A schema mismatch rebuilds the
derived SQLite index. Neither operation changes source artifacts.

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

Canonical report listing reads the last committed catalog projection during
ordinary reconciliation. A new or invalidated cache has no canonical rows until
its first valid projection commits; catalog invalidation then refreshes Reports.

The read-only ReportLibrary combines this canonical adapter with the existing
workspace-package adapter. Canonical reads always return the current source
file; package reads delegate to WorkspaceReportLibrary. Stable opaque report
references identify the two kinds without encoding paths. Report replacement
does not change a reference, and browser or ACP projections do not disclose
source paths or revisions.

Reports share one searchable, paginated library. Imported reports may stand alone
or have multiple session, Dataset, and Job associations. Canonical reports retain
their immutable source sessions and may have additional manual Dataset and Job
associations. WorkspaceReportLibrary owns these manual associations: imported
packages retain `source_refs` in `state.json` and may add `dataset_ids` and `job_refs`
arrays; canonical associations live under `reports/.associations/`, keyed by report
reference.
Absent optional associations are empty, so existing packages need no rewrite.
Changing associations never writes canonical `analysis.md` or imported report bodies.
Association metadata is validated before publication. An unreadable canonical
association file marks only that report's manual associations unavailable; its
original source and report body remain readable. Such metadata cannot be overwritten
through association editing until repaired. Missing sources retain their association
files so temporary unavailability cannot erase manual links.

Dataset identity is its registration ID. Managed Job identity is its run ID;
external Harbor Job identity includes both mount ID and Job name. A managed run
and a mounted Job are merged only when they identify the same actual output
directory. Dataset targets include registrations without Trials; managed Job
targets include runs without results. External Jobs come from the complete source
catalog. Removed targets remain visible as unavailable associations until explicitly
removed; new associations must resolve to available targets.

The report-library HTTP interface uses typed `{kind, key}` association references.
Session keys are catalog source keys; Dataset keys are registration IDs; Job keys
are `managed:<run-id>` or `harbor:<mount-id>/<job-name>`. Missing session references
retain an opaque key so they can be removed without exposing source paths.
`GET /api/report-library` accepts `page`, `page_size`, `search`, and repeatable
`kind`, `dataset`, and `job` filters (`kind=unassociated` selects reports
without associations). The default ordering is descending update time, with report
reference as a stable tie breaker. `GET /api/report-library/targets` accepts a
`kind`, `search`, `page`, and `page_size`. Both queries cap pages at 100 items and
clamp the requested page to the available range after filtering. Unknown association
kinds are rejected; Dataset and Job IDs may refer to unavailable retained links.
`PUT /api/report-library/{report_ref}/bindings` replaces the manual `bindings` list;
canonical report session bindings cannot be edited through this endpoint.
`POST /api/reports` imports a server `path` with an optional `bindings` list.
Its Location points to `GET /api/report-library/{report_ref}`, which returns metadata;
the `/preview` and `/reader` suffixes provide the sandboxed document and standalone
reader. `DELETE /api/reports/{id}` deletes an imported package only.
`GET /api/reports` supplies Home's direct-session package projection.

Report-page Dataset and Job filters include both manual associations and ownership
derived from associated sessions. Associations retain their origin and are deduplicated
per target. Selected values within a filter are alternatives; different filters
intersect. Search matches report names and association labels, not report bodies.
All matching metadata is combined before pagination. These broader associations
do not add reports to a session's Leaderboard Reports column: that column continues
to show only directly attached imported reports.
