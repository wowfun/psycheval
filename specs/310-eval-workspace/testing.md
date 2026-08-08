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
  alias interface.
- Linked-source tests cover Harbor Trial, Job, and jobs-root discovery; custom
  roots; lexical and Windows-mapped symlink rejection; configured-root catalog
  diagnostics; running and completed results; stable identity; reward
  projection; canonical-to-sidecar nested identity; multi-step rejection;
  source disappearance and recovery; restoration of missing or invalid cached
  projections; and preservation of last-good artifacts and user overlays after
  invalid refreshes.
- Storage tests prove Harbor-owned files are unchanged, projection writes are
  atomic, linked cells cannot escape the run root, linked-source deletion is
  rejected, and archive remains available.
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
