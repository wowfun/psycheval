---
name: Evaluation Workspace
---

# Evaluation Workspace

The Evaluation Workspace is peval-py's serve mode for importing sources,
organizing them, comparing results, and exporting reproducible views.

## Scope

This topic owns workspace storage, source and report catalogs, the HTTP
interface, browser presentation, saved state, selection, and export behavior.
It does not own source-format conversion rules or Harbor Trial execution.

## Core Requirements

- The browser starts from an empty application shell and lazily loads catalog
  and report data.
- Source keys remain stable across filtering, pagination, alias changes,
  active/archive transitions, report attachment, and exports.
- Workspace mutations expose generation-aware results and never require clients
  to replace the entire workspace from one response.
- Separate Leaderboard and Sources-page selections persist across pages and
  are reconciled only with sources that no longer exist.
- Saved views, report attachments, aliases, and presentation settings remain
  user-authored overlays over rebuildable report data.

## Acceptance Criteria

- A workspace can be rebuilt from its sources without losing user-authored
  overlays.
- HTTP, storage, and browser tests agree on mutation, selection, Summary, and
  export scope.
- Static reports, live serve, and workspace snapshots retain their explicitly
  different row-count behavior.

## Attachments

- [Access Control](access.md)
- [Harbor Dataset Management](harbor-datasets.md)
- [Saved Views](saved-views.md)
- [Storage](storage.md)
- [HTTP Interface](http.md)
- [Presentation](presentation.md)
- [Testing](testing.md)

## Related Topics

- [020. State and Data Model](../020-state-and-data-model/spec.md)
- [300. peval-py](../300-peval-py/spec.md)
