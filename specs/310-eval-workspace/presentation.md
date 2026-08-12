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

## Source Manager Inputs

Source Manager presents only the SQLite DB and Path add forms, in that order.
It does not present an input-table form, snapshot upload, or a replacement empty
card. Workspace snapshots remain available only from the export menu.

Harbor configuration is a separate section rather than another ordinary source
form. It shows each explicit mount's ID, Jobs root, and ordered Task/Dataset
paths; supports add, edit, and remove; and labels configuration changes as
workspace-only. An empty add form remains available when no Harbor mount exists.

## Harbor Trial Semantics

Leaderboard keeps the canonical Session identifier and replaces the separate
alias presentation with a compact Task / Alias cell. Task is the default; a
user alias becomes primary while Task remains secondary. Job, Provider, and
Reward are first-class columns. Reward preserves numeric zero, identifies a
dimension-only result without inventing a scalar, and is absent only when no
numeric reward evidence exists.

Tags combine read-only live Task keywords with editable custom tags. Editing
changes only custom tags; clearing an edit restores the keyword-only display.
Summary and Saved Views may group by Task, Job, or Provider and include scalar
Reward statistics. Selected Trial includes a compact Harbor Evidence section
for identities, reward dimensions, phase timing, versions, digests, result and
regrade provenance, and live Task metadata status.

Search and every report/export surface preserve Task, Job, Trial, Provider,
Reward, display values, and Harbor provenance. Live Task metadata is always
labelled as current mounted metadata, never historical Job evidence.

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
