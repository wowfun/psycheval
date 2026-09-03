# Evaluation Workspace Reference

The Psycheval workspace organizes retained sources, overlays, reports, Saved Views,
Harbor mounts, and browser presentation without taking ownership of source
evidence.

## Configuration ownership

An initialized root contains `peval.toml`. The CLI discovers it through explicit
`-r`/`--root`, the current directory and its parents, or `PEVAL_ROOT`; there is
no separate config-file option. Workspace configuration is strict: unknown
Psycheval-owned fields, removed defaults, invalid types, duplicate identities,
and dangling Dataset references fail before any command or mutation runs.

Plain `peval init` creates or validates only the workspace configuration and log
directory. `peval init --skill <skill-dir>` additionally validates one local
Agent Skill, using the Skill directory name and matching `SKILL.md` frontmatter,
then stages and installs it at `.agents/skills/<name>/`. A relative Skill path is
resolved from the command's current directory, not from the workspace root.
Explicit installations in one workspace are serialized. Every installation
replaces the complete same-name destination, including local edits and stale
files; a caught replacement failure restores the prior destination, and a later
explicit installation recovers a uniquely identifiable backup left by an
interrupted replacement. No managed manifest or revision guard is created.
Serialization uses the persistent `.agents/skills/.peval-install.lock`
coordination file; it is not Skill ownership metadata and does not affect the
installed tree.
Invalid, linked, special-file, or source/destination-overlapping Skill trees
fail before workspace initialization writes.

The Psycheval CLI owns top-level workspace presentation, `[adapters.*]`,
`[[acp.agents]]`, `[[harbor.datasets]]`, and `[[harbor.mounts]]`. Each Dataset
registration has a resolved format: `harbor` for immediate-child Task
directories or `workbuddy.v1` for a validated WorkBuddy bundle. `psycheval.harbor` owns
`[harbor.host]`; each parser accepts the sibling section without copying its
semantics. Harbor host callers name the file with `PEVAL_CONFIG`.

Dataset and mount paths may be relative to the config. Mounts name explicit
Harbor Jobs roots and ordered Dataset IDs; there is no implicit Jobs discovery.
Harbor evidence and registered Dataset files remain read-only to source/catalog
operations except explicit administrator Dataset workbench mutations.
Dataset registration and mount configuration share one revisioned configuration
snapshot. HTTP reads expose its strong ETag and writes require `If-Match` so a
stale browser cannot overwrite a newer file. Unregister is atomic across the
requested Dataset IDs, preserves their
directories, and fails if any requested ID is still mounted. Task archive,
restore, rename, and permanent deletion do not rewrite `dataset.toml`; manifest
contents change only through explicit synchronization.
WorkBuddy registrations expose their manifest metadata and nested Tasks in the
same inventory, but the entire Dataset workbench is read-only: Task creation,
rename, archive, restore, deletion, file writes, and manifest synchronization are
rejected at the server boundary. A Dataset selected through a symlink is stored
as its strict physical directory; hand-authored configured paths still reject
symlink traversal. Read-only capability is also carried by each Task tree entry,
so clients never advertise an editable text node that the server will reject.
WorkBuddy inventory rows report registration identity without recursively
validating or hashing every Task tree. Opening a Task detail validates that
selected Task against its current files and exposes the resulting diagnostic
status; explicit Dataset registration and preparation remain the full-bundle
validation gates.
Mount removal is likewise atomic across the requested Mount IDs and preserves
the referenced Jobs directories. Dataset-to-Mount membership edits update the
Mount-owned `dataset_ids`; adding a Dataset through the reverse Dataset view
appends it after that Mount's existing evidence lookup order.

ACP agents form an executable allowlist. Each entry names a path-safe identity,
display title, executable, and argument array. Serve starts that array directly,
without a shell, in the workspace root and with the serve process environment.
Each administrator WebSocket names only an Agent ID; serve resolves its array
from the current workspace configuration and gives that socket one child
process. The gateway transports bounded text frames and does not interpret or
retain ACP sessions. The vendored `pretty-aui` client first probes ACP v2 and
opens a fresh gateway connection for ACP v1 fallback when required.
Administrators may edit the allowlist through the separate configuration API.

Repository Markdown assets own the default ACP prompt text. The workspace
`prompts/` directory may contain a same-name Markdown file for any known asset;
that file is the workspace override. Removing an override restores the
repository default. English and Simplified Chinese variants are independent
assets and are all present in the catalog. A fresh Chinese workspace view uses
the Chinese evaluation-review asset and Chinese context recommendations; other
locales use the English counterparts. A valid saved selection remains selected
regardless of locale. Prompt writes are revision-checked, bounded UTF-8 text
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

The bundled UI uses the unversioned `/api` resource interface. Successful
responses are direct resource representations; HTTP errors use Problem Details.
Potentially slow and batch mutations return an operation resource for polling.
This interface, its disabled API documentation, and its single-process server
are local workspace implementation details rather than an external service
contract.

The ACP WebSocket and context resolver are administrator-only and same-origin
because an allowlisted Agent runs with the OS authority of `peval serve`; an ACP
permission card is Agent protocol state, not an operating-system sandbox.
Binary WebSocket messages, oversized frames, excess concurrent connections, and
unconfigured Agent IDs fail at the gateway boundary. Agent credentials must
already be provisioned in the inherited environment or Agent profile.
Psycheval disables Agent-advertised browser authentication and neither collects
those secrets nor exposes Agent authentication commands in the browser.

Workspace configuration and prompt asset APIs are also administrator-only.
Changing or removing a connected Agent immediately stops that process;
unchanged Agent configurations keep their current connections.

ACP session transcripts and pending interactions remain inside the Agent and
the live `pretty-aui` controller; they are not evaluation evidence, workspace
overlays, or reports. Workspace page navigation leaves the live drawer open and
does not remount its controller. The browser persists drawer and Agent
selection, the ordered set of attached evaluation references, and the last
Agent session identity used for reconnect. Adding the current source, Task, or
report is explicit and duplicate references are ignored; each attachment can be
removed independently. On each later prompt, the context provider asks the
server to resolve and bound every frozen reference according to
`max_content_chars`. Agents without embedded-context support receive bounded
text fallbacks. Each item actually submitted is shown by `pretty-aui` as a
collapsed Context injection activity after the user message; expanding it
shows a bounded literal view of the content and inert resource metadata. These
activities remain with the loaded browser controller across in-page session
selection and reconnect, but Psycheval does not persist a second resolved-
content log for restoration after a full page reload.

Sessions are process-local, idle-expiring cookies. Direct HTTP is intended for
a trusted private network; the cookie is not marked `Secure` in this mode.
