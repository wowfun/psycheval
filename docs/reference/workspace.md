# Evaluation Workspace Reference

The Psycheval workspace organizes retained sources, overlays, reports, Saved Views,
Harbor mounts, and browser presentation without taking ownership of source
evidence.

## Configuration ownership

An initialized root contains `peval.toml`. The CLI discovers it through explicit
`-r`/`--root`, the current directory and its parents, or `PEVAL_ROOT`.
The Psycheval CLI owns top-level workspace presentation, `[adapters.*]`,
`[[harbor.datasets]]`, and `[[harbor.mounts]]`. `psycheval.harbor` owns
`[harbor.host]`; each parser accepts the sibling section without copying its
semantics. Harbor host callers name the file with `PEVAL_CONFIG`.

Dataset and mount paths may be relative to the config. Mounts name explicit
Harbor Jobs roots and ordered Dataset IDs; there is no implicit Jobs discovery.
Harbor evidence and registered Dataset files remain read-only to source/catalog
operations except explicit administrator Dataset workbench mutations.

## Storage and identity

Linked Trial references use
`harbor/<mount-id>/<job-name>/<trial-name>`. Workspace-authored Harbor overlays
contain only state, notes, and analysis. Catalog SQLite data, imported report
bodies, summaries, and render projections are rebuildable. Deleting a linked
source is unsupported; archive is the reversible hide operation.

Source keys remain stable across alias edits, queries, pages, state changes,
and report attachment. Mutations are generation-aware. Original databases,
trajectory inputs, and Harbor roots are never rewritten by report or catalog
rebuilds.

## Access model

Serve has anonymous `guest` and authenticated `admin` roles. Without
authentication, only a local listener is allowed and requests act as admin. A
non-local bind requires `PEVAL_ADMIN_PASSWORD`, read first from the process and
then from a regular non-symlink workspace `.env` file.

Guests receive allowlisted, path-safe projections and read-only exports.
Administrators may inspect source locations, refresh, and mutate workspace or
Dataset state. Authorization is centralized and unclassified routes fail
closed; hiding a browser control is not an access check.

Sessions are process-local, idle-expiring cookies. Direct HTTP is intended for
a trusted private network; the cookie is not marked `Secure` in this mode.
