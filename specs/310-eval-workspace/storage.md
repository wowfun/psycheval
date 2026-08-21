# Evaluation Workspace Storage

## Authority

Workspace storage owns source records and their stable keys, aliases,
active/archive state, saved views, attached reports, and presentation metadata.
Imported normalized report bodies, derived summaries, and catalog indexes are
rebuildable.

Workspace `peval-py.toml` accepts an optional top-level `description` string.
The effective configuration follows the existing workspace-then-explicit-config
overlay order; a blank value is equivalent to omission. The value is public
workspace presentation content rather than source or catalog state.

Leaderboard column order and visibility are device-local browser presentation
state keyed by an opaque workspace identifier rather than source or catalog
state. A workspace snapshot explicitly embeds a copy when reproducibility is
requested; automatically derived empty-column visibility is never persisted.

Browser-local Saved Views are independently stored presentation/query state;
their authority, isolation, limits, and merge behavior are specified by
[Saved Views](saved-views.md).

### Linked Harbor Trials

`serve -r` continues to select an initialized peval-py workspace. Harbor sources
come only from explicit `[[harbor.mounts]]` entries in `peval-py.toml`; there is
no implicit workspace or `jobs/` discovery. Each mount has a unique lowercase
path-safe ID, a `path` that identifies a Harbor jobs root with the exact shape
`<root>/<job-name>/<trial-name>`, and ordered `dataset_ids` entries referencing
the Dataset registry owned by [Harbor Dataset Management](harbor-datasets.md).
Relative paths resolve from the configuration file. Initial load,
explicit Reload, single-source Refresh, and Sources-page configuration changes
rescan mounts. There is no background watcher.

Configured paths remain lexical until every existing component has been checked
for symbolic links. A mount or Dataset path that is itself a link or traverses
a linked component is rejected before canonical identity is calculated. Jobs
discovery also rejects linked Job or Trial children. Duplicate IDs, duplicate
canonical Jobs or Dataset paths, missing roots, unresolved Dataset references,
direct Job or Trial mounts, invalid Dataset roots, and paths outside the
declared root are rejected with an explicit configuration or refresh error.

The Sources page edits only the Harbor mount array in workspace `peval-py.toml`,
preserves unrelated configuration, and validates the complete proposed array
before writing. Dataset configuration is owned by the Dataset workbench.
Removing a mount detaches its derived catalog rows but does not delete Harbor
files or workspace overlays.

A linked source reference is
`harbor/<mount-id>/<job-name>/<trial-name>`. The source key is derived from that
structured reference. peval-py reads the Harbor Trial directly and applies the
[shared Harbor ATIF compatibility and derivation rules](../020-state-and-data-model/spec.md#atif-and-peval-py-sidecar-ownership)
in memory. It never writes to the Harbor root and never durably copies a linked
trajectory, metadata sidecar, signature, or link manifest into `runs/`.

An optional Trial-owned Markdown file under `artifacts/logs/**/analysis.md` is
supplemental read-only analysis. The canonical `artifacts/logs/analysis.md`
wins when present; otherwise peval-py chooses the first containment-safe regular
file in lexicographic relative-path order. Only that selected candidate
participates in the linked-source fingerprint, updated time, and input size so
explicit Reload and Refresh observe its creation, changes, removal, or a change
in selection. peval-py reads at most 20 MiB from the selected candidate through
a containment-checked, no-follow UTF-8 reader and never copies or modifies it.
A missing, blank, oversized, undecodable, linked, or non-regular candidate
contributes no analysis document and does not make an otherwise readable Trial
fail. Selection happens before content validation, so an invalid canonical or
first candidate does not fall through to a later match.
Directory depth alone does not fail Trial or Catalog discovery; nested fallback
scanning does not depend on the Python call stack.

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
search fields, and query state. Page queries derive complete-query counts,
inference aggregates, and column presence inside SQLite without materializing
every matched report JSON object or retaining every matched source key in
application memory. Report-binding references used by that query are reused
until a report import, binding replacement, or deletion invalidates them, and
their filtered count uses one set-valued SQLite query rather than a query per
chunk. A refresh that observes partial or invalid ATIF
replaces the readable row with the current diagnostic and never serves a
last-good trajectory. A missing Trial with no user-authored state or report
binding disappears. A retained missing Trial remains as a diagnostic and
reattaches when the same source reference reappears. Linked rows cannot be
deleted; archive remains the supported hide operation.

The linked-source projection reads the parent Job config, lock, and result; the
Trial config, lock, result, and trajectory; and a uniquely resolved allowlisted
Task definition through one bounded no-follow evidence reader. It exposes Task,
Job, Trial, provider, rewards, phase timing, and reproduction provenance without
copying raw environment, agent kwargs, commands, or credentials. Task metadata
resolution and live-digest state remain explicit diagnostics rather than hidden
fallbacks. Discovery builds one Task allowlist index per mount and reuses it,
including selected-Task content digests, across the mount's Trials.

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
mode. Sources-page bulk state clears its own selection on success; bulk delete
clears it when the operation is submitted. Report attachment uses the retained
Leaderboard selection and clears it after successful attachment.

## Related Topics

- [Evaluation Workspace](spec.md)
- [Harbor Dataset Management](harbor-datasets.md)
- [Saved Views](saved-views.md)
- [HTTP Interface](http.md)
- [Presentation](presentation.md)
