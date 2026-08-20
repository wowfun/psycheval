# Evaluation Workspace Testing

## Scope

This attachment defines deterministic validation for storage, HTTP, browser
state, report rendering, selection, mutation, and export behavior.

## Required Coverage

- Access tests cover credential precedence, dotenv symlink rejection, local and
  non-local activation, login throttling and successful-login reset, session
  expiry, idempotent logout, centralized guest/admin authorization, stale
  authentication-state reclamation, guest-safe shell/data/export projection,
  expired-session download handling, and role-specific presentation.
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
- Harbor analysis tests cover Trial-only, overlay-only, and combined Markdown;
  stable Harbor-before-workspace ordering; canonical-path priority and
  lexicographically stable nested fallback selection; creation, change,
  removal, and selection changes invalidating the source fingerprint; missing
  and blank block hiding; oversized, invalid UTF-8, symlink, and non-regular
  inputs failing closed without making the Trial unreadable; adversarially deep
  fallback directories without call-stack failure; nested guest-path
  projection; and zero writes under Harbor roots.
- Catalog, rendering, snapshot, and XLSX tests cover `#Analysis` source counts
  of 0, 1, and 2, treating JSON and Markdown in one workspace overlay as one
  source and keeping Harbor plus workspace analysis as two sources.
- Config and rendering tests cover an optional top-level workspace description,
  normal config precedence, non-string rejection, blank hiding, escaped
  Markdown in the centered live toolbar for both roles, snapshot preservation,
  and absence from ordinary static reports.
- HTTP, report, export, and analysis-import tests resolve Harbor content through
  source keys and source references without a Harbor `artifact_dir`.
- Catalog, HTTP, and rendering tests additionally cover Task, Job, and Provider
  filters/facets/sorts; scalar Reward sorting and distributions; Saved View and
  Summary grouping; Task/Alias fallback; derived/custom tag editing; Harbor
  Evidence; and Task/Job/Reward/provenance in reports, snapshots, inspection,
  and XLSX exports.
- Catalog and rendering tests cover inference sufficient-statistic projection,
  weighted complete-query summaries and coverage, null-last inference sorting,
  query-wide column presence, stable invalid-generation presence shape,
  pagination stability, blank Session IDs, semantic zero values,
  exclusion of non-finite and zero-decode evidence, and static/live/snapshot
  parity. Catalog query tests also prove that complete-query summaries do not
  deserialize unpaginated report JSON or retain an unpaginated source-key
  collection.
- UI-state tests prove both selections survive pagination, header toggles affect
  only the current page, and each action uses and clears the correct selection.
- Saved View tests cover browser storage isolation and recovery, shared
  validation and limits, server-name precedence, role-specific mutation,
  source-aware selection and deletion, mixed query/summary/export predicates,
  conflict races, and self-contained snapshot reproduction as specified by
  [Saved Views](saved-views.md).
- Column-control tests cover draft apply/cancel/reset, explicit no-data show,
  manual hide precedence, hiding every non-structural column, earlier/later
  ordering, retained hidden conditions, versioned browser storage recovery,
  multi-column canonical migration, snapshot precedence, per-action focus
  restoration, initial Catalog sort-key mapping shared by the Columns panel and
  header `aria-sort`, and sortable-header accessibility.
- Rendering tests cover the complete static/live/snapshot Summary row-count
  matrix, non-JSON serve responses, and malformed or oversized embedded report
  previews failing inside the reader without aborting the workspace UI.
- Export tests assert the exact query, page, selection, intersection, and limit
  rules for every export kind, prove Table XLSX retains every inference
  sufficient-statistic field, prove Summary XLSX combines page-scoped
  distributions with the complete-query inference overview, and reject legacy
  HTML Report requests. Guest HTTP tests exercise attached-report preview/open,
  Saved View reads and summaries, and Summary XLSX rather than only their policy
  classifications.
- Storage and HTTP tests use isolated temporary workspaces and do not read real
  user configuration or persistent host state.
- Guest UI tests invoke administrator-only action functions directly and prove
  they issue no requests, independently of whether their controls were rendered.
- Guest projection tests inject unknown path-bearing fields into internal Task
  metadata and Harbor provenance and prove those fields are excluded from live
  and export projections until explicitly allowlisted.

## Acceptance Criteria

- Python serve/catalog/report tests and Node UI-state tests pass.
- Browser-equivalent interaction tests pass for changed presentation behavior.
- No test helper-generated legacy view is treated as the actual HTTP wire
  contract.

## Related Topics

- [Evaluation Workspace](spec.md)
- [Access Control](access.md)
- [Saved Views](saved-views.md)
- [300. peval-py Testing](../300-peval-py/testing.md)
