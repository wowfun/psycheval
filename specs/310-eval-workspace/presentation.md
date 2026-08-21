# Evaluation Workspace Presentation

Role-specific controls and guest-safe content projection are specified by
[Access Control](access.md).

Live serve uses a shared top header with low-profile text navigation on its
left. Home, Datasets, Reports, and Sources are real pages; the active link has a
visible focus-blue lower rule and `aria-current="page"`. Guests omit Sources.
Role, authentication, and locale controls remain on the right, while reload and
mutation actions belong to the active page. Static reports and workspace
snapshots do not acquire this navigation.

Home starts directly with its report notes, Leaderboard, and analysis content
below the shared navigation. It does not repeat a Home page title, expose a
source-count/status summary, or provide a page-level Refresh action. A configured
workspace description remains as the only optional identity text between the
navigation and main content. On Home, that compact description is aligned to
the right edge of the content surface and its ordinary prose is right-aligned;
structured Markdown such as lists and tables retains its readable left
alignment.

Datasets uses the shared data table above the selected Task detail specified by
[Harbor Dataset Management](harbor-datasets.md). Its semantic Task status
remains visible without turning the navigation or page actions into decorative
pill tabs. Reports retains its inventory/bindings layout as a page and keeps
the existing right-side Reader. Sources retains its input/configuration region
and paginated table as a page. Modal backdrops, modal close controls, and body
scroll locks are removed from these three management surfaces.
Datasets, Reports, and Sources use the same outer workspace width so changing
routes does not shift the shared header or page edges; each page handles wider
internal tables with its own scrolling instead of changing that outer width.
Their page surfaces fill the viewport space remaining below the shared header.
When Dataset or Report content is short, the final detail/body region stretches
to the surface's lower edge so columns share one visible bottom boundary instead
of leaving an unowned blank band. Content may still grow the document when its
minimum usable height exceeds the viewport, and narrow-screen stacking retains
its own content-driven height.

The shared server/browser Saved Views presentation and local mutation behavior
is specified by [Saved Views](saved-views.md).

## Workspace Identity

Home renders the effective workspace `description` as Markdown in a lightweight
identity region below the shared header. Guests and administrators see the same
description. Missing or blank content removes the region without leaving an
empty card or placeholder. Rendering uses the same HTML-escaping Markdown
subset as report notes, so configuration content cannot inject raw HTML.
Workspace snapshots preserve the description in their existing top placement;
ordinary static reports do not acquire workspace identity content.

## Summary Availability

- Live serve shows Summary for zero, one, or multiple report rows; zero rows use
  an empty Summary shell.
- Workspace snapshot export requires at least one matched row and shows Summary
  for one or multiple rows.
- Static-report behavior is specified separately in
  [300. Reports](../300-peval-py/reports.md).

## Selection

Leaderboard and the Sources page maintain independent selections. A table-header
checkbox adds or removes only the current page's keys, while actions consume the
entire retained selection unless their specific contract says otherwise.

Pagination and filtering do not silently prune valid off-page selections.
Generation reconciliation removes only keys that no longer exist.

## Sources Page Inputs

Sources presents only the SQLite DB and Path add forms, in that order.
It does not present an input-table form, snapshot upload, or a replacement empty
card. Workspace snapshots remain available only from the export menu.

Harbor configuration is a separate section rather than another ordinary source
form. It shows each explicit mount's ID, Jobs root, and ordered Dataset IDs;
supports add, edit, and remove; and labels configuration changes as
workspace-only. An empty add form remains available when no Harbor mount exists.

## Harbor Trial Semantics

Leaderboard places Job immediately before the compact Task / Alias cell in its
canonical column order and keeps the canonical Session identifier as its final
data column. Task is the default; a user alias becomes primary while Task
remains secondary. Job, Provider, and Reward are first-class columns. Reward
preserves numeric zero, identifies a dimension-only result without inventing a
scalar, and is absent only when no numeric reward evidence exists.

Tags combine read-only live Task keywords with editable custom tags. Editing
changes only custom tags; clearing an edit restores the keyword-only display.
Summary and Saved Views may group by Task, Job, or Provider and include scalar
Reward statistics. Selected Trial includes a compact Harbor Evidence section
for identities, reward dimensions, phase timing, versions, digests, result and
regrade provenance, and live Task metadata status.

Search and every report/export surface preserve Task, Job, Trial, Provider,
Reward, display values, and Harbor provenance. Live Task metadata is always
labelled as current mounted metadata, never historical Job evidence.

Selected Trial Analysis renders the selected Harbor
`artifacts/logs/**/analysis.md` and the workspace
`harbor/<mount-id>/<job>/<trial>/analysis.md` overlay as separate
source-labelled Markdown blocks in that order. Each missing or blank document
removes only its own block. When both Markdown documents are absent, structured
`analysis.json` content and automatic analysis metrics retain their existing
behavior. JSON reports and workspace snapshots preserve the same source order.
Administrator payloads may show the Trial- or workspace-relative document path;
guest payloads omit that path while retaining the source and Markdown body.

Leaderboard names its analysis column `#Analysis` and displays an integer source
count. A displayable Harbor analysis contributes one; workspace analysis
contributes one when its overlay contains `analysis.json`, `analysis.md`, or
both. The range is therefore 0–2 for Harbor Trials and 0–1 for other sources.
The count, rather than a boolean label, is preserved in static reports,
workspace snapshots, and table XLSX exports.

## Inference Metrics and Columns

Leaderboard exposes per-Trial Avg TTFT, Decode TPS, and Cache Hit columns using
the shared inference rules in
[020. Model Inference Telemetry](../020-state-and-data-model/spec.md#model-inference-telemetry).
Missing values render as absent rather than zero. A separate inference summary
shows the three ratio-of-sums values and `covered / matched Trials` for the
complete current search and filter result, independent of pagination.

Every non-structural Leaderboard column is automatically hidden when its
semantic value is absent for every row in that complete result. Pagination
does not change the automatic set; search or filter changes may. Null, missing,
blank-string, empty-list, and the renderer's `-` missing-value sentinel are
empty, while numeric zero and false are present. Static reports and workspace
snapshots apply the same rule to all of their embedded rows. Provider is hidden
by default even when present, but the Columns control may explicitly show it.

Column presence follows the displayed semantic field rather than an unrelated
row identity. In particular, Session is absent when the canonical session ID is
blank, while `#Analysis = 0` remains a present numeric value. The presence
object retains its complete key shape even before the catalog has a valid
generation, with zero counts for every column.

Live serve and workspace snapshots provide one Columns control for manual
visibility and left-to-right order. The selection column remains fixed. Manual
show and hide overrides take precedence over automatic visibility, including a
manual show of a column marked as having no data. Users may hide every
non-structural column, leaving the fixed selection column by itself. Reset
restores canonical order and clears overrides. Hiding a sorted or filtered
column does not clear that condition. Reordering uses explicit earlier/later
actions and does not change the existing header-driven row sort. Re-rendering a
draft after visibility, ordering, or reset actions restores focus to the
corresponding control; applying the draft returns focus to the Columns
disclosure. Sort state uses the canonical mapping between browser column keys
and Catalog API keys, including on initial load.

Live column preferences are versioned browser-local presentation state scoped
by an opaque workspace identifier. Unknown, duplicate, or malformed entries
fall back safely, and newly introduced columns enter at their canonical
position. When more than one column is introduced, the new columns retain their
canonical relative order while stored columns retain their saved relative
order. A stored manual order remains authoritative when the default canonical
order changes. Workspace snapshots embed the resolved manual order and overrides and
do not depend on browser-local state. Ordinary static reports perform only
automatic hiding. Screen visibility and order do not remove or reorder fields
in data exports.

## Export Scope

- **Table `.xlsx`:** all rows matching the complete unpaginated catalog query;
  Leaderboard selection is ignored.
- **JSON Report:** all retained selected keys when selection exists, otherwise
  the current catalog page; the existing 100-cell limit applies.
- **Workspace snapshot `.html`:** the complete query when there is no selection,
  otherwise `query ∩ retained selection`; the 100-row limit applies to the final
  matched rows.
- **Summary `.xlsx`:** the current visible Leaderboard page; selection does not
  change its scope.

Table XLSX and JSON retain the complete inference fields regardless of screen
visibility. Summary XLSX additionally carries the complete-query inference
overview shown in live serve while retaining its existing page-scoped
distribution content. Workspace snapshots reproduce the embedded column layout.

An embedded report preview in a workspace snapshot is decoded only within the
same 20 MiB per-report limit used by the report library. Malformed or oversized
preview data fails closed inside the report reader with a visible error; it does
not abort the workspace UI or create a preview object URL.

The serve export menu exposes Table XLSX, JSON Report, and Workspace snapshot.
It does not expose a legacy HTML Report action.

## Related Topics

- [Evaluation Workspace](spec.md)
- [Access Control](access.md)
- [Harbor Dataset Management](harbor-datasets.md)
- [Saved Views](saved-views.md)
- [Storage](storage.md)
- [HTTP Interface](http.md)
- [300. Reports](../300-peval-py/reports.md)
