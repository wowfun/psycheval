# Evaluation Workspace Storage

## Authority

Workspace storage owns source records and their stable keys, aliases,
active/archive state, saved views, attached reports, and presentation metadata.
Imported normalized report bodies, derived summaries, and catalog indexes are
rebuildable.

### Linked Harbor Trials

`serve -r` continues to select an initialized peval-py workspace. On initial
load, explicit Reload, and single-source Refresh, the workspace discovers
single-step Harbor Trials under the root, the conventional `jobs/` directory,
and supplemental `[harbor].roots` configured relative to `peval-py.toml`.
There is no background watcher.

Configured roots remain lexical until every existing path component has been
checked for symbolic links. A root that is itself a link, traverses a linked
component, or discovers a linked Job or Trial is excluded before canonical
identity is calculated. Missing and excluded configured roots are reported as
source diagnostics rather than followed.

Each valid Trial is materialized under the normal `runs/` hierarchy as an
atomic local projection. The source ATIF is validated without repair before the
trajectory, peval sidecar, and rebuildable link manifest replace the previous
projection. Refresh preserves `.peval/state.json`, notes, and analysis files.
Every projection path is scanned without following directory links and is
accepted for reads or writes only when both its lexical and canonical cell paths
remain inside the selected run root. A source-signature cache hit is valid only
while the local trajectory and sidecar both exist, validate, and still form the
canonical ATIF projection; otherwise Reload rebuilds them from the source.

If a refresh observes a partial or invalid ATIF, the last valid projection is
kept and marked stale with the current diagnostic. A first invalid observation
creates a catalog diagnostic without fabricating a trajectory. A missing
source likewise preserves the projection and overlays until it reappears.
Linked rows are refreshable non-snapshots and cannot be deleted; archive is the
supported hide operation.

Each missing or symlink-excluded configured root produces a stable unreadable
`harbor-root` catalog row with the rejected lexical path and reason. This row is
a rebuildable source diagnostic, not a Trial or evaluation artifact, and is
removed when that configured root becomes valid or leaves the configuration.

Storage changes increment a generation used by clients to reconcile stale
state. Reconciliation removes selections whose source keys no longer exist; it
does not discard still-valid cross-page selections.

## Source Mutations

Add, reload, alias, state, and delete operations resolve exact source keys.
Single-source synchronous changes expose a compact mutation result. Potentially
long-running bulk work is represented as an operation that is polled to a
terminal state.

Leaderboard Archive and Activate reload the original query after completion and
do not clear retained Leaderboard selection or automatically switch catalog
mode. Source Manager bulk state clears its own selection on success; bulk delete
clears it when the operation is submitted. Report attachment uses the retained
Leaderboard selection and clears it after successful attachment.

## Related Topics

- [Evaluation Workspace](spec.md)
- [HTTP Interface](http.md)
- [Presentation](presentation.md)
