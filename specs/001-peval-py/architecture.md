# peval-py Architecture

## Module Shape

`peval-py` keeps adapters isolated under `peval_py.adapters`. Non-adapter code
is organized around deep modules whose public interfaces match user-visible
workflows:

- command dispatch parses CLI arguments and delegates to trajectory, import,
  init, and serve workflows.
- input loading turns CLI or serve source selections into loaded session
  descriptors without owning conversion, report building, or workspace state.
- workspace state owns peval-py workspace discovery, cell-local source overlays,
  Trial cell artifacts, snapshot discovery, source lifecycle mutations, and
  report composition over persisted artifacts.
- workspace catalog owns the serve-only fixed-depth run scan, artifact
  fingerprints, disposable SQLite projection, generation publication,
  server-side summary queries, single-cell detail loading, source-key
  resolution, and serialized writer operations behind one interface.
- workspace reports owns imported report packages, time-ordered identities,
  exact source bindings, tolerant catalog projection, content reads,
  rebinding, and deletion behind one filesystem-backed interface.
- workspace views owns saved-view Markdown frontmatter/body validation,
  traversal-safe atomic create/update/rename/delete, tolerant discovery, and
  definitions used for catalog-wide summary and OR-query projections.
- report building owns report JSON v19 assembly, timing metadata, annotations,
  automatic analysis metrics, and input data references.
- analysis owns cached analysis and notes reads, analysis import compilation,
  note writes, and path safety for Trial cell annotation artifacts.
- HTML rendering owns package asset loading, safe payload injection, serve shell
  markup, token estimates, and the offline workspace-snapshot projection and
  renderer. Snapshot rendering is independent from report JSON v19 and live
  serve polling.
- serve owns local HTTP protocol handling, startup background loading, route
  controllers, request payload validation, source mutation response envelopes,
  ECharts cache serving, catalog-generation snapshot scope resolution, and
  in-memory Excel summary workbook composition.
- the browser application owns embedded bootstrap parsing, normalized report and
  catalog projections, UI state, common report rendering, and the three
  static/serve/workspace-snapshot mode adapters behind one application interface.

Adapters must not import the refactored internals directly. The adapter-facing
modules `peval_py.config`, `peval_py.sources`, and `peval_py.redaction` remain
stable import surfaces for built-in and third-party adapters.

## Dependency Direction

Shared dataclasses for loaded inputs, adapter assignments, report sessions, and
notes live in a neutral model module. Workflow modules may depend on these
models, but storage and report modules must not import the CLI parser or the
input loader.

The intended dependency flow is:

```text
cli/serve workflows -> inputs, workspace, report, html
inputs              -> adapters, input tables, workspace snapshot reader
workspace           -> repository, artifacts, report, analysis overlays
workspace catalog   -> workspace artifacts, report, SQLite
workspace reports   -> local filesystem and current source-key projection
workspace views     -> local filesystem and CatalogQuery-compatible values
serve Excel export  -> workspace catalog summaries, workspace views, XlsxWriter
workspace snapshot  -> workspace catalog, report building, workspace views,
                       workspace reports, HTML rendering, cached ECharts
report              -> analysis schema/cache interfaces, redaction
html                -> assets and i18n
```

This prevents cycles where workspace state imports input loading while input
loading imports workspace snapshot state.

Browser startup and packaging use these explicit seams:

```text
entry -> application lifecycle + selected mode runtime
entry -> shared report runtime + workspace rail effects
shared runtime <-> focused render/interaction modules through named ESM imports
focused modal lifecycle -> DOM/focus primitives only
```

The first ESM migration preserves existing render coordination while replacing
implicit file order and last-declaration-wins behavior. Follow-up extractions
should move shared state and pure selectors toward leaf modules and reduce cycles;
they must not recreate a global concatenation contract to do so.

The browser entry is the only module with startup side effects. Browser modules
communicate through explicit imports rather than concatenation-order globals and
must not redeclare a symbol to override an earlier asset. Shared report state is
owned by the runtime module; focused modules own their rendering and event
binding behavior behind named exports.

## Browser Application Interface

`createReportApp({ platform, bootstrap, modeRuntime })` is the browser
application seam. It returns `start()` and `destroy()`; tests use the same
interface as the production entry. The platform owns the document/window
lifecycle, while focused browser tests install isolated jsdom globals and fake
network or timing behavior before importing modules that read browser APIs.

Static report, workspace snapshot, and live serve are selected explicitly at the
mode seam. Static report performs local report interactions only. Workspace
snapshot projects embedded data and must not start runtime requests. Live serve
enables catalog/detail requests, polling, mutations, downloads, and stale-response
rejection in the shared runtime modules. Catalog rows keep separate UI key,
`source_key`, and canonical report `trial_key` identities; a catalog identity
must never be written into the report identity field.

## Package Facades

Public imports may continue to use the package-level facades
`peval_py.analysis`, `peval_py.cli`, `peval_py.html`, `peval_py.inputs`,
`peval_py.report`, `peval_py.serve`, and `peval_py.state`. Their implementations
are split into focused internal modules for parsing, payload validation,
artifact IO, report assembly, serve handlers, and state mutations. New code
should import the deepest stable module it owns when working inside the package,
but external callers should prefer the facade unless a lower-level module is
documented as an extension point.

## Workspace Catalog Interface

`WorkspaceCatalog` is the only serve seam that exposes catalog behavior. Its
public interface provides `reconcile()`, `query(CatalogQuery)`,
`load_detail(source_key)`, `resolve_keys(keys)`, whole-query saved-view summary
projection, and `start_operation(...)`.
Callers do not traverse `runs/` or issue SQLite directly. The module is deep:
it hides fixed-depth discovery, fingerprinting, parsing, schema/version checks,
FTS, transaction boundaries, generation publication, operation serialization,
and detail report composition. Tests exercise this interface with real
temporary Trial files and SQLite rather than a test-only storage port.

The shared value types are:

- `CatalogQuery`: source state, page, page size, literal search, sort and
  direction, Tags/Agent/Model/Result facets, and optional saved-view OR
  predicates resolved by the serve runtime.
- `CatalogPage`: generation, checking/stale flags, total, page, page size,
  summary items, and low-cardinality facets.
- `CatalogRow`: source and Leaderboard summary fields, `artifact_revision`,
  and a compact `step_outline[]` of `{step_id, source, duration_ms?}` for
  Trajectory Overview. It contains no step body content and is distinct from a
  one-cell detail report.
- `DetailEnvelope`: generation, artifact revision, source key, and one-cell
  report.
- `OperationStatus`: operation id/type/state, completed/total counts, successes,
  and failures.

## Serve HTTP Envelopes

`GET /` returns only the serve shell. `GET /api/catalog` returns a
`CatalogPage`; repeated saved-view names are resolved by the serve runtime and
passed to the catalog as one OR predicate plus the ordinary AND refinement.
`GET /api/report?source_key=...` returns one `DetailEnvelope`, and
`GET /api/reports` returns the compact workspace-report catalog. The browser
mode lifecycle renders the shell first, then loads the source and report
catalogs in parallel; each projection rerenders its owning Leaderboard state so
response order cannot hide existing report bindings.
`POST /api/exports` validates the existing table/report export payloads, a
summary-workbook payload, or the workspace-snapshot payload. Summary export
resolves every requested source or saved view against one committed catalog
generation before passing compact grouped statistics to the Excel writer. The
writer does not scan workspace artifacts or reinterpret saved-view predicates.
Workspace-snapshot export holds one non-blocking catalog read guard for scope
resolution, full Trial loading, saved-view summaries, and report bindings. Its
projection records the exact `source_key` to uniquified report `trial_key`
mapping so duplicate raw Trial keys remain navigable offline. A concurrent
writer produces a clear busy response rather than a mixed-generation file.
Source mutations return only the committed generation and compact change
metadata. Reload and multi-item writer requests return `202` with an operation
id, whose progress is read from `GET /api/operations/<id>`. Browser code then
requeries the current catalog page and refreshes only a changed selected detail.
Browser interactions identify catalog rows and overview nodes by `source_key`.
After a detail response arrives, the browser resolves a selected Step against
that report's canonical `trial_key`; callers must not use the catalog identity
as a drawer trial key.

A valid old generation remains readable while the catalog reports
`checking = true` and the next generation is built in one transaction. Without
a valid catalog, APIs expose an empty loading generation until the first commit.
Handlers must not synchronously scan the workspace or construct an all-source
report for the page shell.

## Assets

Browser JavaScript source is an explicit ESM graph under `tools/peval-py/web`.
One side-effect entry is bundled with pinned esbuild tooling into a deterministic,
unminified, single-file ESM package asset. The generated `report.js` is committed,
contains no external import or chunk, and is verified byte-for-byte against the
source graph. Wheels include the generated asset but not the source graph;
sdists include both. Building or running the Python package never invokes Node.

CSS remains split into ordered package assets and concatenated by the Python
asset loader. HTML rendering inlines CSS and the JavaScript bundle. The bundle
runs through `<script type="module">`, follows ECharts initialization in the
document, and must not contain a literal closing script tag.

Asset refactors must preserve static report mode and serve mode over the same
report body. Serve-only code may add source management and export controls, but
static report output must not show serve controls. Workspace-snapshot output
must remain a single offline file and issue no application network request.
