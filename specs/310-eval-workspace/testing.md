# Evaluation Workspace Testing

## Scope

This attachment defines deterministic validation for storage, HTTP, browser
state, report rendering, selection, mutation, and export behavior.

## Required Coverage

- Initial-load tests assert an empty shell followed by lazy catalog and report
  requests.
- Direct HTTP tests assert compact synchronous mutations, queued `202`
  operations, validation errors, and the absence of full report payloads.
- Source tests cover each surface-specific adapter rule and every supported
  alias interface. Rendering and HTTP tests prove Source Manager exposes only
  DB and Path inputs and rejects the removed input-table and snapshot-upload
  mutations, while CLI tests reject `--input-table` and snapshot export remains
  covered by its owning suite.
- Harbor configuration tests cover add, edit, remove, preservation of unrelated
  TOML, catalog reload, Task/Dataset path ordering, missing paths, duplicate
  paths and IDs, symlink rejection, and zero writes under Harbor-owned roots.
- Harbor evidence tests cover result-lock-config Task-name precedence; Job and
  Trial identity; provider evidence; complete rewards and phase timing; regrade
  provenance; allowlisted path and name resolution; ambiguity, missing roots,
  invalid metadata, and symlink diagnostics; path-scoped live-digest mismatch;
  non-comparable package/Git refs; per-mount Task-index reuse; and parent Job or
  Task changes invalidating the catalog fingerprint.
- Linked-source tests cover explicit jobs-root mounts; mount ID and path
  validation; relative and Windows-mapped paths; duplicate and symlink
  rejection; absence of implicit discovery; running, completed, errored, and
  reward states; schema-only compatible older Harbor ATIF; deterministic
  aggregate/result metric derivation; structurally aligned Psychevo database and
  runtime-trace telemetry, OpenCode database telemetry, and Hermes session-export
  telemetry; exact and source-attributed estimated model duration; supplemental
  telemetry fallback; result-only diagnostics without synthetic steps; stable
  structured identity; multi-step diagnostics; bounded read consistency; and
  current-error behavior without a last-good fallback.
- Storage tests prove Harbor-owned files are unchanged, browsing creates no
  overlay, the first edit creates only minimal overlay state, clearing the last
  value reclaims empty directories, deleting the catalog is recoverable, and
  a missing Trial is retained only by an overlay or report `source_refs`
  binding before reconnecting to the same source reference.
- HTTP, report, export, and analysis-import tests resolve Harbor content through
  source keys and source references without a Harbor `artifact_dir`.
- Catalog, HTTP, and rendering tests additionally cover Task, Job, and Provider
  filters/facets/sorts; scalar Reward sorting and distributions; Saved View and
  Summary grouping; Task/Alias fallback; derived/custom tag editing; Harbor
  Evidence; and Task/Job/Reward/provenance in reports, snapshots, inspection,
  and XLSX exports.
- UI-state tests prove both selections survive pagination, header toggles affect
  only the current page, and each action uses and clears the correct selection.
- Rendering tests cover the complete static/live/snapshot Summary row-count
  matrix.
- Export tests assert the exact query, page, selection, intersection, and limit
  rules for every export kind and reject legacy HTML Report requests.
- Storage and HTTP tests use isolated temporary workspaces and do not read real
  user configuration or persistent host state.

## Acceptance Criteria

- Python serve/catalog/report tests and Node UI-state tests pass.
- Browser-equivalent interaction tests pass for changed presentation behavior.
- No test helper-generated legacy view is treated as the actual HTTP wire
  contract.

## Related Topics

- [Evaluation Workspace](spec.md)
- [300. peval-py Testing](../300-peval-py/testing.md)
