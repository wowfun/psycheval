# Evaluation Workspace Reference

The Psycheval workspace organizes retained sources, overlays, reports, Saved Views,
Harbor mounts, and browser presentation without taking ownership of source
evidence.

## Configuration ownership

An initialized root contains `peval.toml`. The CLI discovers it through explicit
`-r`/`--root`, the current directory and its parents, or `PEVAL_ROOT`.
The Psycheval CLI owns top-level workspace presentation, `[adapters.*]`,
`[[acp.agents]]`, `[[harbor.datasets]]`, and `[[harbor.mounts]]`. `psycheval.harbor` owns
`[harbor.host]`; each parser accepts the sibling section without copying its
semantics. Harbor host callers name the file with `PEVAL_CONFIG`.

Dataset and mount paths may be relative to the config. Mounts name explicit
Harbor Jobs roots and ordered Dataset IDs; there is no implicit Jobs discovery.
Harbor evidence and registered Dataset files remain read-only to source/catalog
operations except explicit administrator Dataset workbench mutations.
Dataset registration and mount configuration share one revisioned configuration
snapshot. Unregister is atomic across the requested Dataset IDs, preserves their
directories, and fails if any requested ID is still mounted. Task archive,
restore, rename, and permanent deletion do not rewrite `dataset.toml`; manifest
contents change only through explicit synchronization.
Mount removal is likewise atomic across the requested Mount IDs and preserves
the referenced Jobs directories. Dataset-to-Mount membership edits update the
Mount-owned `dataset_ids`; adding a Dataset through the reverse Dataset view
appends it after that Mount's existing evidence lookup order.

ACP agents form an executable allowlist. Each entry names a path-safe identity,
display title, executable, and argument array. Serve starts that array directly,
without a shell, in the workspace root and with the serve process environment.
Connection and session requests name only an Agent ID; serve resolves its array
from the current workspace configuration. Administrators may edit that allowlist
through the separate configuration API. The client first probes the pinned ACP
v2 draft and restarts with an ACP v1 handshake when the Agent negotiates v1 or
rejects the v2 initialize shape.

Repository Markdown assets own the default ACP prompt text. The workspace
`prompts/` directory may contain a same-name Markdown file for any known asset;
that file is the workspace override. Removing an override restores the
repository default. Prompt writes are revision-checked, bounded UTF-8 text
mutations and do not modify evaluation evidence.

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

ACP routes are administrator-only because an allowlisted Agent runs with the OS
authority of `peval serve`; an ACP permission card is Agent protocol state, not
an operating-system sandbox. Agent credentials must already be provisioned in
the inherited environment or Agent profile. Psycheval neither collects those
secrets nor exposes Agent authentication commands in the browser.

Workspace configuration and prompt asset APIs are also administrator-only.
Changing or removing a connected Agent immediately stops that process;
unchanged Agent configurations keep their current connections.

ACP session transcripts and pending permissions remain process-local and are
not evaluation evidence, workspace overlays, or reports. The browser persists
only drawer, Agent, and session selection. Attaching the current source, Task,
or report is an explicit per-prompt action; the server resolves and bounds the
selected content according to `max_content_chars` before sending it to the
Agent.

Sessions are process-local, idle-expiring cookies. Direct HTTP is intended for
a trusted private network; the cookie is not marked `Secure` in this mode.
