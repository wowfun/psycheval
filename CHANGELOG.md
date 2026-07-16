# Changelog

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
