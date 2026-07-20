# Changelog

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
