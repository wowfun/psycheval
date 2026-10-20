# State and Data

Psycheval separates authoritative evidence from user-authored overlays and
rebuildable projections.

| Data | Authority | Mutation rule |
| --- | --- | --- |
| Task, Job, Trial, result, reward, artifacts | Harbor files | Read-only to ordinary CLI views |
| Canonical evaluation report | Harbor parent Trial or local source-cell `analysis.md` | Source-scoped publication and deletion through EvaluationReports; local Markdown imports use the same writer |
| Portable steps, calls, observations, timestamps, usage | ATIF trajectory | Strictly validate before writing |
| Aliases, state, notes, local analysis JSON, report bindings | Workspace overlay | Explicit user mutation |
| Imported report package | Workspace `reports/` directory | Explicit package mutation through WorkspaceReportLibrary |
| Catalog rows, summaries, JSON/XLSX exports | Derived data | Rebuildable from authorities |

## Trajectories and sidecars

Every CLI-exported `trajectory.json` is a complete ATIF-v1.8 document. A
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

Trajectory time bounds and elapsed wall duration remain unknown when neither
canonical timestamps nor recorded source bounds exist. A single recorded source
bound does not invent the other bound or a duration. Numeric zero is a valid
timestamp; elapsed offsets can be measured from it. Retained Harbor lifecycle
duration may be displayed independently of unknown trajectory timestamps.

For the Leaderboard's Last Turn End, a known trajectory bound takes precedence.
When it is missing, Harbor rows use the recorded Agent execution finish, then
the Trial finish, as an approximation for display and sorting. The catalog's
Last Turn End column-availability counts include these approximations even when
the canonical trajectory finish remains unknown. The catalog
retains the selected source, the browser marks approximations with `≈` and a
source hint, and spreadsheet exports include that source. Missing or invalid
finish records remain unknown; file modification and import times are not
execution-time substitutes. This projection never fills canonical trajectory
timestamps or changes their duration calculations.

Inference aggregates retain sufficient statistics for weighted recomputation.
TTFT needs exact request-dispatch and first-token boundaries; decode throughput
also needs an exact terminal boundary and output usage. Cache rate uses explicit
cache-read measurements over inclusive prompt tokens. Missing evidence is
unknown, numeric zero remains a value, and Agent or wall duration is not
relabelled as model timing.

New native WorkBuddy Trials supply these statistics from their retained
[usage evidence](harbor.md#workbuddy-usage).
Recorded partial or unavailable WorkBuddy usage coverage is projected into the
existing read-only diagnostic display; this does not change execution or
conversion status and does not fill missing totals.

Active duration sums recorded Agent-step and tool execution contributions. It
measures aggregate activity rather than the union of elapsed intervals; parallel
contributions can overlap. Wall duration remains the separate elapsed measure.
Projected durations accept only nonnegative integer milliseconds, excluding
booleans, numeric strings, fractional values, and non-finite numbers.
Client-observed Agent output spans are excluded from model-duration aggregates,
TTFT and decoding speed. Their source labels survive conversion and projection.
`event_observed` timestamps locate events but never authorize adjacent-timestamp
duration estimates. Explicit native OpenCode model-call intervals still supply
Model duration; their sources and boundaries are defined by the
[native OpenCode contract](harbor.md#native-opencode). They do not supply TTFT or
decode speed. Timeline Waterfall and Timeline Detail Table use the same stage
labels regardless of timing source: `Model: <model name>` and
`Tool call: <tool name>`. Timing-source hover hints describe interval boundaries
and whether waiting may be included; observed and estimated timing values retain
their approximation marker. Its total is the sum of recorded contributions, with a coverage
hint when some intervals are unknown; parallel contributions can overlap.
No measured interval means an unknown total, displayed as a dash. A measured zero
remains a visible zero-duration record. Reading older untimed evidence does not
backfill it from vendor timestamps or Harbor lifecycle totals.
Trajectory nodes shade their duration relative to the other nodes in that Trial.
They prefer a measured step duration, then recorded tool contributions, then an
eligible adjacent-timestamp estimate. Observed and estimated values carry source
hints; unknown values remain neutral. Node shading never supplies model metrics.
The presentation fallback may use an eligible step boundary even when untimed
tools exist: it estimates the whole step, including tools. Canonical model
duration refuses that fallback for steps with tools. Recorded tool contributions
may cover only some calls; their sum is never a measured step span.

The core timing classification lives in
[`timing-sources.json`](../../src/psycheval/assets/web/timing-sources.json), consumed
by Python projections and browser labels. It defines source families, model
eligibility, observed/estimated flags and timestamp-estimation admission.
Harbor producers retain their independent evidence contract and emit wire source
identifiers; they do not import core report code. Unknown sources have no inferred
display label. Frontend timeline heuristics remain presentation-only.

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
bar charts, and spreadsheet exports omit a metric only when its Count is zero in
every group. Grouped summaries remain exact and are never truncated or
approximated; a query whose distinct group count exceeds the service capacity is
rejected so the user can refine the scope or select an overall summary.

Tool success rate is the fraction of tool calls without a recorded error:
`(total_tool_calls - total_tool_errors) /
total_tool_calls`. Both counts must be known and valid; zero calls have no rate.
Counts must be finite numeric values; strings and booleans remain unknown in
catalog projections as well as direct trajectory views. The detailed spreadsheet
stores the rate as a numeric cell with a one-decimal percentage display, retaining
the underlying precision.
This is an execution-outcome metric, not a judgment of task correctness. Each
Trial's rate is computed before grouped means and percentiles; raw error evidence
and counts remain unchanged.
The Trial's success/total display follows the same validity rule and does not
infer zero errors from an absent count.

The Home summary offers bar and radar views of the same complete-query data.
Radar axes use a shared statistic and independently normalize against all groups
in the current query, including unselected groups. Min–max scaling maps each axis
to 0–100, reversed for durations so that larger radii mean better performance.
Equal measured values map to 50 and are identified as having no group difference.
Changing comparison groups does not change these bounds. Tokens, turns, and tool
call counts have no performance direction and are excluded from radar axes.
Radar uses solid outlines whose colors remain visible during hover and keyboard
focus. A group's measured relative values may all be zero; its outline then
collapses to the origin and the comparison list and detail explicitly identify
that condition without changing the query-wide scale. Radar preserves selected
axes even when entirely unmeasured. Missing values are drawn at the origin with a
cross annotation offset by axis and group for legibility, with explicit
missing-data labels; these offsets do not encode a measured radius. They remain
unknown in the data and never
enter scaling, statistics, or exports. Ordinary
markers identify measured values, including those normalized to the origin.
Selected groups use distinct colors with a minimum hue separation. Their search
filter stays in page memory through presentation changes and navigation, but is
not part of a shared location. Chart interactions preserve an open summary table.
Radar selections affect presentation only; Saved View and spreadsheet charts
remain bar charts.
Home's Clear conditions action resets query conditions, ordering, and applied View selection;
it preserves summary grouping, statistic, table disclosure, and radar settings.
Presentation changes alone do not enable that action.

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

## Shareable workspace locations

The browser location identifies the current page and open detail independently
of list membership. Home uses `?source=<source_key>` for a Trial, with optional
`trajectory`, `step`, and `tab`; reports use `?report=<report_ref>` on Home or
Reports, with an optional Reports `tab`. Identities are stable keys, not aliases
or list positions. A closed detail leaves the page's list location.

`#view=<base64url>` contains a versioned UTF-8 JSON snapshot of that page's
query and presentation state. It preserves search, facets, ordering, pagination
and page size, plus Home's applied View conditions and aggregate grouping,
statistic, table disclosure, chart type, radar axes, and comparison group keys.
Radar defaults select the first five groups in summary order; explicit selections
are limited to five and may be empty. Changing the grouping resets group selection;
query changes retain surviving explicit keys without filling vacated positions,
and identify unavailable selections. Defaults are omitted deterministically. Applied
server and browser Views become transient snapshots with labels and actual
conditions; opening a link never saves them or resolves them by name. They use
the query, summary and export interfaces' optional `inline_views` filter array:
the filters are ORed with other applied Views, then intersected with the base
query. Inline filters share query validation without saved-name collision checks.
Saved View facet values are normalized before application and capture using the
query service's trim, blank-removal and deduplication rules. Malformed values
remain errors rather than silently changing a shared query.
The serve boundary deduplicates identical applied conditions across saved,
browser and inline Views. Their combined query permits at most 100 distinct
conditions; excess conditions report an error for lists, summaries and exports
instead of truncating the query. Search and empty predicates keep their normal
query semantics.

Initial loads and browser history restoration apply the complete snapshot before
loading a list and its independently requested detail. Invalid, oversized or
unknown-version locations report an error rather than dropping conditions.
On Home and Reports, the fragment is reserved for `#view=` snapshots; plain
anchors and legacy `#source=` fragments are unsupported and show the same explicit
link error. Trial identity belongs in the `source` query parameter.
Complete links are limited to 64 KiB. Missing details retain their requested
identity and report unavailability instead of selecting another object.
Opening/closing details and switching pages add history entries; condition and
detail-position changes replace the current entry. Restoration suppresses URL
writes and obsolete requests. Hidden pages and background reads cannot overwrite
the active location. Unsaved drafts remain local and are not restored from links.
Ordinary page activation also defers location writes until its state is ready.
An explicit detail change during activation retains its add-history intent when
activation settles. Search input publishes its URL with the debounced list query;
copying a link still captures the current controls immediately.
Refreshes requested during restoration run after it settles; newer invalidations
are not acknowledged by an older read. Capture errors remain visible without
replacing the requested URL or dropping any conditions.
Saved View refresh and conflict recovery may only prune the currently applied
named Views; they cannot clear a newer shared snapshot or publish an obsolete
query error after asynchronous work completes.
Home retains one authoritative detail identity and position; its detail coordinator
owns reader exclusion and batches synchronous location changes.
Trajectory position changes apply only to the Trial reader.
Report detail requests are superseded by a new detail selection or navigation,
independently of concurrent list reads and filter changes.
Trial openings without an explicit tab or step start at the default detail tab.

Copy-link controls use the current normalized location without credentials,
content, checked rows, ACP state or personal layout. Links require access to the
same workspace; they restore query definitions against current data, not frozen
results. Existing access checks apply to each object and action.

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
Safe retained canonical reports for local sources remain discoverable when their evidence
is unreadable or missing. Reading and deletion need the validated source location,
not readable trajectory evidence; publication still requires readable evidence.

ReportLibrary combines this canonical adapter with the existing
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
The same metadata stores the optional boolean `archived`, defaulting to false.
Absent optional associations are empty, so existing packages need no rewrite.
Changing associations never writes canonical `analysis.md` or imported report bodies.
Association edits preserve archival state; archival edits preserve associations.
Management mutations serialize the complete read-modify-write cycle, including
validation of retained unavailable associations, under a per-report cross-process
lease. State replacements stage beside report packages,
then atomically replace the package's state file; readers never see staging files
inside the package. Report bodies and management JSON are read through
non-following regular-file handles, with a 20 MiB limit per file. Management
snapshots take their content and modification time from the same opened file,
so a concurrent atomic replacement cannot pair old state with a new timestamp.
Canonical archival validates report existence
inside that lease, so a completed deletion cannot leave newly written state.
Management lock files are retained for the workspace's lifetime: removing them
would let existing waiters and new callers lock different files for one report.
Each report source or management lease acquisition uses one finite deadline across
the in-process mutex and OS lock. Its default belongs to
[`file_access`](../../src/psycheval/file_access.py); expiry raises
`FileLeaseTimeout` before entering the protected operation. The API returns a
retryable 409 conflict for this contention. If deletion has already committed
before a later lease expires, the existing committed-deletion error still applies.
The deadline bounds lock waiting, not the mutation after acquisition; disconnecting
an HTTP caller does not interrupt an accepted mutation midway.
The catalog writer uses the same non-following lease primitive with immediate
contention failure. Waiting for report management never holds the catalog writer:
first publication clears stale management before acquiring it, and deletion clears
management after releasing it, while retaining the source lease throughout.
Report association and archival edits, and imported-package deletion, use only
their report management lease without acquiring the catalog writer. The existing
catalog-loading admission guard still applies.
Storage enumeration includes archived packages;
Home and report queries select their presentation state explicitly.
Archival hides a report from the default library and Home's Reports column,
but does not prevent direct preview, source-detail reads, or Copilot context reads.
Replacing canonical content preserves archival state. Creating a canonical body
after its deletion clears any management state left by interrupted cleanup before
publishing the new body. Markdown import, snapshot annotations and copied Trial
sidecars all use the EvaluationReports writer for this rule. Snapshot and sidecar
ingestion can run inside a catalog operation, so their report leases fail immediately
on contention instead of waiting while holding the catalog writer.
Association metadata is validated before publication. An unreadable canonical
association file marks only that report's manual associations unavailable; its
original source and report body remain readable. Such metadata cannot be overwritten
through association or archival editing until repaired. Missing sources retain their association
files so temporary unavailability cannot erase manual links.
Imported packages with missing or unreadable state also retain their safe body
preview, but reject association and archival edits until repaired.
Damaged packages under safe report directories retain their stable identities in
the library for deletion. Missing or invalid layout uses unavailable metadata;
oversized bodies remain listed but cannot be previewed. Package-directory links
are never admitted through this fallback.
When management metadata is unreadable, its archival state is unknown. The
library projects `archived=false` and unavailable associations, keeping the report
discoverable in Active and All for repair or deletion. This fallback does not
rewrite metadata; repairing it restores the retained archival state.

Administrators may permanently delete either report kind. EvaluationReports owns
canonical deletion and serializes it with publication and Markdown import using
the source lock before the catalog writer lease. It revalidates the target and
removes only the canonical regular `analysis.md`, reconciles the catalog, then
clears that report's manual associations and archival metadata. MultiStep phases
share the parent deletion. Imported deletion removes only the workspace package.
An imported package with a valid ID may be deleted even if its state, body size,
or file layout is invalid; deletion never follows a package-directory symlink.
Neither operation removes sessions, Trial evidence, or the imported original file.
Deletion accepts damaged management metadata without overwriting it. A report
published after deletion starts unarchived, with no previous manual associations.
Failures after removing the body report the committed deletion separately from
metadata cleanup and catalog reconciliation, so clients can refresh accurately.
The deleted report's catalog row is discarded before cleanup and full
reconciliation, so either failure cannot restore it to the library. Discarding a
committed projection advances its catalog generation in the same transaction,
including when subsequent cleanup or reconciliation fails.
Report presence participates in source fingerprints even when Harbor evidence is
unreadable, so adding, changing, or removing the body invalidates cached projections.
Imported deletion first detaches the package into a hidden `reports/.delete-*`
directory, then removes that directory. If removal fails, the report stays absent
from the library and the API reports a committed failure; the detached files remain
on disk. After stopping serve and releasing file handles, an administrator can
remove the matching directory within this workspace's `reports/` directory.
The server does not automatically retry or collect these detached packages.

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
`GET /api/report-library` accepts `state=active|archived|all` (default `active`),
`page`, `page_size`, `search`, and repeatable
`kind`, `dataset`, and `job` filters (`kind=unassociated` selects reports
without associations). The default ordering is descending update time, with report
reference as a stable tie breaker. `GET /api/report-library/targets` accepts a
`kind`, `search`, `page`, and `page_size`. Both queries cap pages at 100 items and
clamp the requested page to the available range after filtering. Unknown association
kinds are rejected; Dataset and Job IDs may refer to unavailable retained links.
`PUT /api/report-library/{report_ref}/bindings` replaces the manual `bindings` list;
canonical report session bindings cannot be edited through this endpoint.
`PUT /api/report-library/{report_ref}/state` sets the strict boolean `archived`
and returns updated metadata. Repeating the same state is idempotent.
`POST /api/reports` imports a server `path` with an optional `bindings` list.
Its Location points to `GET /api/report-library/{report_ref}`, which returns metadata;
the `/preview` and `/reader` suffixes provide the sandboxed document and standalone
reader. `DELETE /api/report-library/{report_ref}` deletes either kind and returns
204, or 404 for a missing report. Committed deletion failures return a Problem
with `committed`, `metadata_cleared`, and `catalog_reconciled` flags.
Deletion responses, including committed failures, declare `X-Peval-Invalidations`:
`reports` and, for canonical content, `catalog`. The catalog domain also
invalidates the selected source's cached detail. Clients
invalidate from this declaration rather than the report reference's spelling.
For imported packages, `metadata_cleared` means detached from the active report
library; `catalog_reconciled` is true because no catalog projection requires
reconciliation. Detached tombstones may still require filesystem cleanup.
`GET /api/reports` supplies Home's unarchived direct-session package projection.

Report-page Dataset and Job filters include both manual associations and ownership
derived from associated sessions. Associations retain their origin and are deduplicated
per target. Selected values within a filter are alternatives; different filters
intersect. Search matches report names and association labels, not report bodies.
All matching metadata is combined before pagination. These broader associations
do not add reports to a session's Leaderboard Reports column: that column continues
to show only directly attached imported reports.

Strict imports accept ATIF 1.7 and 1.8 without modification. Audio content is
valid in 1.8 only; its references and metadata survive projection and export.
Audio is shown as an identified media reference, without automatic playback or
transcription. Adapter conversion emits canonical 1.8.
