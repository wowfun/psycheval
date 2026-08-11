# Evaluation Workspace Storage

## Authority

Workspace storage owns source records and their stable keys, aliases,
active/archive state, saved views, attached reports, and presentation metadata.
Imported normalized report bodies, derived summaries, and catalog indexes are
rebuildable.

### Linked Harbor Trials

`serve -r` continues to select an initialized peval-py workspace. Harbor sources
come only from explicit `[[harbor.mounts]]` entries in `peval-py.toml`; there is
no implicit workspace or `jobs/` discovery. Each mount has a unique lowercase
path-safe ID and a path, relative to the configuration file when not absolute,
that identifies a Harbor jobs root with the exact shape
`<root>/<job-name>/<trial-name>`. Initial load, explicit Reload, and single-source
Refresh rescan mounts. There is no background watcher.

Configured paths remain lexical until every existing component has been checked
for symbolic links. A mount that is itself a link, traverses a linked component,
or discovers a linked Job or Trial is rejected before canonical identity is
calculated. Duplicate IDs, duplicate canonical paths, missing roots, direct Job
or Trial mounts, and paths outside the declared root are rejected with an
explicit configuration or refresh error.

A linked source reference is
`harbor/<mount-id>/<job-name>/<trial-name>`. The source key is derived from that
structured reference. peval-py reads the Harbor Trial directly and applies the
[shared Harbor ATIF compatibility and derivation rules](../020-state-and-data-model/spec.md#atif-and-peval-py-sidecar-ownership)
in memory. It never writes to the Harbor root and never durably copies a linked
trajectory, metadata sidecar, signature, or link manifest into `runs/`.

User-authored state is created lazily under the matching workspace reference:

```text
harbor/<mount-id>/<job-name>/<trial-name>/
  state.json
  notes.md
  analysis.json
  analysis.md
```

`state.json` contains a schema version and only non-default `active`, alias,
category, and tags values. Derived source paths, identities, lifecycle status,
errors, model facts, rewards, timing, and metrics are forbidden. Removing the
last state value removes the file and every empty overlay directory; notes or
analysis keep their containing directory. Report packages independently bind
stable source references rather than artifact directories.

The SQLite catalog stores only rebuildable source fingerprints, summaries,
search fields, and query state. A refresh that observes partial or invalid ATIF
replaces the readable row with the current diagnostic and never serves a
last-good trajectory. A missing Trial with no user-authored state or report
binding disappears. A retained missing Trial remains as a diagnostic and
reattaches when the same source reference reappears. Linked rows cannot be
deleted; archive remains the supported hide operation.

A discovered Trial that has a lifecycle result but no trajectory remains a
catalog diagnostic rather than disappearing. Its result and source identity are
queryable, but report/detail operations still reject it as trajectory-unreadable.

Legacy `[harbor].roots` configuration and `harbor-link.json` projections are not
migrated or read. They produce an incompatibility error instructing the user to
initialize a new workspace; peval-py never deletes legacy data automatically.

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
