# Evaluation Workspace Presentation

## Summary Availability

- Live serve shows Summary for zero, one, or multiple report rows; zero rows use
  an empty Summary shell.
- Workspace snapshot export requires at least one matched row and shows Summary
  for one or multiple rows.
- Static-report behavior is specified separately in
  [300. Reports](../300-peval-py/reports.md).

## Selection

Leaderboard and Source Manager maintain independent selections. A table-header
checkbox adds or removes only the current page's keys, while actions consume the
entire retained selection unless their specific contract says otherwise.

Pagination and filtering do not silently prune valid off-page selections.
Generation reconciliation removes only keys that no longer exist.

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

The serve export menu exposes Table XLSX, JSON Report, and Workspace snapshot.
It does not expose a legacy HTML Report action.

## Related Topics

- [Evaluation Workspace](spec.md)
- [Storage](storage.md)
- [HTTP Interface](http.md)
- [300. Reports](../300-peval-py/reports.md)
