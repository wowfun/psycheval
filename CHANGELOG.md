# Changelog

## 2026-07-13

- Improved serve report browsing with resizable previews, sandbox-preserving
  new-tab opening, read-only session Tags, and richer Leaderboard grouping and
  charts.
- Reworked `peval-py serve` around a rebuildable SQLite catalog with incremental
  reconciliation, literal search and facets, paginated summaries, on-demand
  details, cross-page selection, serialized mutations, and bounded exports.

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
