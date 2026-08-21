# Changelog

## 2026-08-21

- Split `peval-py serve` into bookmarkable Home, Datasets, Reports, and Sources
  pages with shared navigation, page-scoped loading, guest-safe Dataset/Task
  browsing, and administrator-only Sources access and writes.
- Added a Harbor Dataset and Task workbench with searchable tables, registered
  Dataset configuration, Harbor 1.4 scaffolding and validation, revision-checked
  editing, drafts, Dataset-local trash, explicit manifest synchronization, and
  background catalog reconciliation.
- Replaced per-mount `task_paths` with the global `[[harbor.datasets]]` registry
  and ordered `dataset_ids`; legacy configuration now fails instead of being
  migrated implicitly. Standalone peval-py now targets Python 3.12 and pins
  `harbor==0.21.0`.
- Hardened Harbor operations and guest boundaries, including missing scaffold
  data, overlapping selections, file growth, restore cleanup, browser uploads,
  invalid step counts, and guest-side action invocation.
- Reworked manifest validation and the Dataset, Report, and Source layouts;
  simplified Home and refined the canonical Leaderboard columns while retaining
  report reading and dirty guards.

## 2026-08-19

- Added guest and administrator access to `peval-py serve`, with password
  discovery, idle sessions, throttled login, fail-closed authorization,
  guest-safe projections and exports, and trusted-LAN listening.
- Added browser-local Saved Views, workspace descriptions, Harbor Markdown
  analysis overlays, `#Analysis` origin counts, and workspace-scoped Leaderboard
  column visibility/order with snapshot and XLSX support.
- Added versioned Harbor model-inference telemetry and peval-py Avg TTFT, Decode
  TPS, and Cache Hit metrics with exact sufficient statistics, ratio-of-sums
  aggregation, query-wide coverage, and explicit unknown-value handling.
- Hardened serve caching, session and binding lifecycle, error handling, export
  scope, metadata projection, nested analysis discovery, and snapshot previews;
  fixed static/snapshot counts, sorting, column migration, and telemetry sample
  accounting.

## 2026-08-15

- Added Harbor multi-step support for External Harness, Psychevo, and Hermes,
  including fresh/resumed sessions, step-local evidence, persistence, verifier
  transfer, reward aggregation/termination, and artifact archival.
- Added isolated per-Trial HostEnvironment workspaces configured through
  user-owned `PEVAL_CONFIG`, with cross-platform ExternalHarnessAgent binding,
  path mapping, and safe write-through semantics.
- Added the three-step PBench Trend Digest task and deterministic coverage for
  session/workspace persistence, evidence isolation, rewards, artifacts, exact
  output metadata, and required skill calls.
- Hardened Harbor verification with safe artifact globs, exact final-answer
  references, call-evidence constraints, and fail-closed session/process
  handling; removed legacy Psychevo runtime variables and public canned-harness
  entry points.
- Updated Browser Control, harness examples, documentation, specifications, and
  internal synthetic fixtures for the new runtime and verification contracts.

## 2026-08-13

- Kept completed Hermes runs successful when best-effort exact-session telemetry
  export fails, while retaining strict session-identity validation.
- Reused per-mount Harbor Task metadata and digests during catalog refreshes,
  with clearer handling of live Task status.

## 2026-08-12

- Simplified peval-py source management to Path and DB inputs, adding read-only
  Harbor Job and Task/Dataset mounts while removing input-table and snapshot-
  upload flows.
- Added first-class Harbor Task, Job, Trial, Provider, Reward, timing, and
  provenance data across catalog, filters, views, summaries, evidence, reports,
  snapshots, inspection, and exports.
- Added trusted-host Agent XDG path support, Hermes compatibility, and robust
  Windows harness handling including quoted entrypoints with spaces.
- Added independent Python and Web CI coverage for the peval-py suites.

## 2026-08-11

- Migrated Psycheval and PBench to Harbor 0.21.0 and Task schema 1.4, with
  stable `-01` Task names across the base and Plus Datasets.
- Added native Linux/Windows HostEnvironment and verifier paths, with Windows
  CI coverage that keeps PBench as a regular Dataset.
- Made PBench tool alternatives explicit and exposed reward dimensions for
  calls, observations, forbidden tools, final answers, artifacts, and totals.
- Rebuilt the peval-py CLI on Typer with plain-text help and explicit shell
  completion setup while preserving its command and short-alias workflows.

## 2026-08-10

- Added explicit Harbor source mounts and stable `harbor/...` references with
  direct reads, lazy overlays, and missing-source reconnection.
- Made workspace catalog, reports, and analysis source-ref based and rebuildable
  without copying Harbor Trial projections into the workspace.
- Hardened Trial ingestion and telemetry recovery across compatible ATIF,
  OpenCode, Psychevo, and Hermes data, while isolating Psychevo state per Trial
  and retaining trajectory-less failures with diagnostics.

## 2026-08-08

- Reorganized the repository around a root `psycheval` distribution with the
  `psycheval.harbor` interface, Harbor 0.20.0, an independent root lockfile, and
  package-local tests while preserving Harbor's direct CLI workflow.
- Added the versioned `pbench-v1.0` Dataset with maintained Search, Fetch, and
  Browser Tasks, plus an example Task scaffold.
- Rebuilt the specifications and product documentation, including mirrored
  peval-py guides, corrected PyInstaller entrypoint, and inspect/raw report
  guidance.
- Hardened peval-py trajectory exports and Harbor Trial integration with strict
  ATIF-v1.7 artifacts, complete portable facts, read-only projections, status
  reporting, workspace overlays, and actionable diagnostics.
- Fixed token accounting, sidecar and linked-cell metadata, symlink and archive
  safety, bulk deletion, PBench HostEnvironment execution, and root Ruff/test
  boundaries.

## 2026-08-07

- Added Harbor 0.18.0-compatible Web Agent evaluation support for trusted host
  execution, external ATIF harnesses, and binary outcome-and-evidence grading.
- Added deterministic search, fetch, and browser-control Tasks, opt-in live
  Psychevo web Tasks, typed transcript conversion, diagnostics, tests, and
  usage documentation.

## 2026-08-03

- Moved the Source Manager SQLite DB import area to the top of the left column.
- Fixed the desktop Step drawer layout so complete inline Steps remain reachable
  and can be expanded without closing the drawer or resetting analysis scroll.

## 2026-07-25

- Added editable single-value session Categories across serve surfaces,
  workspace snapshots, and XLSX exports, with catalog filtering and Summary
  grouping; fixed cold-scan suggestions, comma-bearing filters, missing-value
  grouping, and literal `overall` labels.
- Improved report binding workflows with reliable multi-report selection,
  final-binding clearing, and immediate Leaderboard refresh after saving.

## 2026-07-21

- Tightened Serve workspace layout: the localized heading stays beside source
  status, source tables retain horizontal access, and wide Saved Views content
  scrolls without pushing rail controls out of view.

## 2026-07-20

- Fixed serve startup to load existing workspace-report bindings into the
  Leaderboard automatically.
- Unified ordinary serve actions into responsive button types so toolbar,
  modal, and Saved Views rail controls stay inside narrow or zoomed layouts.

## 2026-07-19

- Fixed Reports Manager binding selection to preserve list scroll and focus while
  updating controls in place.
- Improved workspace report and analysis layout with fit-to-pane HTML previews,
  normally scrolling Leaderboard content, and intrinsic-height Saved View cards.

## 2026-07-16

- Replaced ordered browser-script concatenation with a pinned deterministic ESM
  build, an explicit application/mode lifecycle, native Node/jsdom checks, and a
  committed Python package bundle that keeps Node out of the runtime path.
- Improved serve workspace behavior with clearer manager and modal states,
  cross-page Source Manager bulk actions, editable Saved Views and analysis
  interactions, shared type-driven tables and persistence adapters, adaptive
  truncation, fixed desktop analysis/Saved Views scrolling, and restored
  focus/scroll positions across workspace sessions.
- Reworked serve Saved Views around an editable index with draft multi-selection,
  batch deletion, OR-composed filtering, shared data-table controls, and a
  two-chart analysis rail.
- Added atomic view mutations, complete-catalog queries, Leaderboard reset and
  layout fixes, and reversible archived-view switching.
- Added serve-only XLSX exports for Leaderboard Summary and Saved Views, plus a
  bounded read-only HTML workspace snapshot with catalog, analysis, views,
  previews, and cached ECharts.

## 2026-07-15

- Added durable Leaderboard saved views with Markdown notes, persisted filters
  and grouping, atomic overwrite, full-catalog summaries, and an apply/cancel
  workspace rail.
- Improved serve filtering and browsing with draft Apply menus, complete-catalog
  facet candidates, and race-safe saved-view refresh and selection handling.
- Renamed the `peval-py serve` homepage to Eval Workspace / 评测工作台 while
  keeping exported static HTML reports distinct.

## 2026-07-14

- Fixed later-row selection in serve Leaderboard and Trajectory Overview so
  loading Trial details no longer resets either panel to its first row.

## 2026-07-13

- Improved serve report browsing with resizable previews, sandbox-preserving
  new-tab opening, read-only session Tags, and richer Leaderboard grouping and
  charts.
- Reworked `peval-py serve` around a rebuildable SQLite catalog with incremental
  reconciliation, literal search and facets, paginated summaries, on-demand
  details, cross-page selection, serialized mutations, and bounded exports.
- Fixed canonical Step selection for Leaderboard and Trajectory Overview,
  added compact catalog outlines, and moved session search below the Leaderboard
  title.

## 2026-07-11

- Refined the serve UI with denser report sections, compact Leaderboard
  actions, a Reports Manager, inline Source Manager aliases, and in-place
  adapter default DB controls.
- Fixed the first `peval-py serve -r` invocation for a new workspace so the
  generated adapter default DB paths are immediately available without
  restarting the server.

## 2026-07-10

- Added serve-only workspace reports with Leaderboard bindings, sandboxed
  Markdown/HTML previews, Reports Manager controls, and durable relative
  Trial-cell bindings under `<workspace>/reports/`.

## 2026-07-09

- Migrated `peval-py` tool, skill, specs, and user docs into the standalone
  `psycheval` repository.
