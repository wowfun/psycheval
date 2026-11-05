# Evaluation Workspace Reference

The Psycheval workspace organizes retained sources, overlays, reports, Saved Views,
Harbor mounts, and browser presentation without taking ownership of source
evidence.

The shared header uses the same width, inset, and navigation layout across
Home, Datasets, Jobs, Reports, and Configuration at a fixed viewport and sidebar
state. Changes in page height reserve scrollbar space without shifting it.

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
semantics. Applications can pass a selected file to Harbor's explicit
host-settings parser; the [host contract](harbor.md#host-configuration) owns
workspace allocation and Job configuration precedence.
WorkBuddy preparation uses the Python interface and does not discover workspace
settings or register a Jobs mount. Applications pass parsed Host settings
explicitly and use the existing workspace mount controls to associate the
Harbor `JobConfig.jobs_dir`. Host settings are applied only to Host Jobs.

`[adapters.claude].default_session_root` selects the retained-session lookup root
and defaults to `~/.claude/projects/`, including in an existing configuration
that omits the field. Relative overrides resolve against the defining
`peval.toml`; `~` expands to the user's home. Lookup scope and ambiguity rules
belong to the [input contract](cli.md#inputs-and-adapters).
Adapter path preferences shorten paths beneath the native home to `~` when
writing configuration. Other Windows drive and UNC paths retain their spelling.
When resolving paths on native Windows, configuration and server paths are
normalized to native absolute form even if the target does not exist yet.
Lexical resolution preserves symbolic links; physical resolution follows an
existing target. Non-Windows hosts preserve unmapped Windows path spelling and
never bind it to a coincidentally named relative entry under the current directory.

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
symlink traversal. Each Task file entry separates text-preview capability from
editability: regular UTF-8 files within the text-size limit can be previewed even
in read-only Datasets. Binary and oversized files expose metadata only. Clients
enable editing only when both the file and the current view permit it.
The Home and Dataset Task browsers share the Verification browser's Markdown
preview: complete `.md` and `.markdown` files open rendered, with a raw-text
toggle. Task editing uses the raw view and preserves drafts when switching views.
Embedded HTML remains literal text. These file browsers expose no per-file
download controls.
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
display title, executable, and argument array. On Windows, serve resolves commands
without a directory component through its current PATH and PATHEXT at each
launch. The resolved executable is not written back to configuration; explicit
paths retain their native subprocess behavior. A command that cannot be found
fails the connection attempt and releases its reserved connection slot.
Serve passes the executable and argument array to the subprocess API in the
workspace root with the serve process environment. Psycheval does not construct
a shell command; Windows `.cmd` and `.bat` launchers run through the system batch
interpreter, so their arguments follow Windows batch syntax.
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

Configuration controls accept interaction after their event handlers are bound.
Copilot's Connect button stays disabled until the Agent catalog is available.

### Metric descriptions

Optional `[metrics."<ID>"]` entries describe values without changing them. IDs
and discovery belong to the [metric contract](state-and-data.md#numeric-metrics).
At most 128 entries are accepted. Each supports `label`, `unit`, and `direction`
(`higher`, `lower`, `neutral`). Built-in labels and directions may be overridden;
their units cannot be reinterpreted. Custom metrics default to ordinary numbers
and neutral direction. `ms`, `ratio`, and `USD` select duration, percentage and
currency formatting; other units are literal suffixes. No values are converted.
Invalid IDs, unknown built-in IDs, invalid fields and incompatible built-in units
fail validation. Valid custom IDs not observed yet remain pending with a diagnostic.

```toml
[metrics."atif.extra:energy_wh"]
label = "Energy"
unit = "Wh"
direction = "lower"

[metrics."reward:llm_score"]
label = "LLM Judge"
unit = "ratio"
direction = "higher"
```

### Display timezone

The optional top-level `timezone` in `peval.toml` accepts an IANA timezone name
(for example, `timezone = "Asia/Shanghai"`) or `UTC`. Names are matched without
regard to case and saved with the timezone database's spelling. The `Factory`
placeholder represents an unknown timezone and is rejected. If omitted, Serve resolves
the server's system local timezone with `tzlocal`; `zoneinfo` validates names and
retains daylight-saving rules. Unresolvable zones fail with an explicit
configuration hint. Timezone data is a declared runtime dependency.

Administrators can search for a display timezone in Configuration or select
server local time, which removes the field. The revisioned `/api/config` response
includes nullable `timezone` and resolved `effective_timezone`; PATCH accepts a
name or `null`, with the existing administrator, ETag and atomic-save rules.
HTML bootstrap includes the effective timezone for every visitor.

Leaderboard, Trial details, phase times, timeline cells and tooltips, and session
import lists share this timezone. Full timestamps use
`YYYY-MM-DD HH:mm:ss.SSS ±HH:mm`; timeline clocks retain milliseconds and include
the offset. Missing values display `-`; invalid or timezone-less strings remain
literal. Source data, sorting, durations, and JSON/XLSX export semantics do not
change. Copilot chat timestamps are outside this setting.

Saving updates time nodes in all loaded pages of the current document without
reloading evaluation data or resetting navigation, filters, pagination, drafts,
or Copilot. Other browser documents read the new setting on full reload; manual
file changes require a service restart. There is no cross-client push.

## Browser input and feedback

Human-entered filesystem paths remove surrounding whitespace, one matching pair
of ASCII single or double quotes, and whitespace immediately inside that pair
before path resolution or identifier derivation. Remaining characters, including
spaces within a path, are literal; this is not shell parsing. Empty
quoted paths are invalid. Report imports use the same token normalization.
Source `path` inputs use LF or CRLF separators; other control characters and
Unicode line separators are rejected before token normalization. Empty and quoted-empty lines are
ignored consistently for batch selection and execution. Source `db` inputs use
non-POSIX shell token splitting before removing one quote pair per token.
Dataset and Jobs paths remain relative to the
configuration directory; source imports retain their workspace-relative rules.
This input convenience does not reinterpret hand-authored TOML, Task-relative
file paths, or ACP commands and argument arrays.

Action feedback belongs to its form, editor, or resource region. Field errors
use structured Problem Details pointers when available; other failures remain
at the form or action level. Failed submissions retain input. An unrelated
refresh, navigation, or an older request cannot clear a newer action's error.
Page loading, scan progress, source-mode text, and shell failures have their own
feedback scopes. Neutral page status stays inline without completion notifications. Notifications
outside the visible action region provide a summary and a return action without
automatically scrolling or taking focus. Errors and actionable notifications
remain until resolved or dismissed; transient success feedback expires, releasing
its state, and pauses while read. Independent actions retain independent results.
These rules do not replace Copilot's transcript-owned notices.

Input dialogs keep a failed draft open and prevent duplicate submissions.
Backdrop dismissal requires the same primary pointer to press and release on
the backdrop before its click. Dragging or selecting text from inside a dialog
to the backdrop does not dismiss it. Cancelled gestures and gestures interrupted
by closing, suspending, or reopening a dialog cannot dismiss it later.
Enter submits the primary action; destructive secondary actions require explicit
activation. Opening another dialog suspends an input dialog and preserves its
draft; closing the newer dialog returns to the suspended one.
Cancelling a suspended reference picker settles its action and removes it;
closing the newer dialog must not revive that cancelled picker.
Accepted writes followed by background reconciliation report those two phases
separately: reconciliation failure offers a refresh, not a repeated write.
Reading the displayed data again cannot turn a failed background operation into
a success. Read and refresh retries hold the same busy gate as the initial
observation; repeated activation cannot start overlapping retries.
An operation has one active observer per document. Replacing that observer,
disposing its feedback, or unloading the document stops its reads and timers.
Completing a source refresh invalidates the catalog again, independently of the
notification sent when the scan was accepted. The active page reloads affected
catalog data; inactive catalog views reload on their next activation. A reload waits
for any in-flight catalog request and preserves filters, sorting, and pagination.
Pages without catalog data only leave the affected views invalidated; scan success
does not imply that an inactive view has already loaded. Home rows, pagination
totals and controls, summaries, and category suggestions use the refreshed catalog.
Refresh failures remain retryable without submitting another scan, and refreshing
cannot clear a failed scan's result. If both the scan and the refresh fail, feedback
retains the scan diagnostics alongside the refresh error. Superseded or destroyed
page activations cannot publish stale failures. Page stale markers record read
state; the initiating operation owns its refresh-error feedback and retry.
Post-save refresh errors have one reporting owner. A failed retry retains its
Refresh action, and a successful retry clears that action's error.
Batch results retain failed items and their input; import forms reset only after
all items succeed. A failed operation-status read offers another read of the
same operation, never an automatic replay. Revision conflicts retain the draft
and expose the current saved configuration in the action's details;
prompt and file conflicts expose the current saved text in the error details
as a bounded preview for review before another explicit submission. Truncated
previews are labelled; the complete file remains available in the file editor.
A failed conflict refresh keeps
the original conflict visible. Task mutations do not discard edits made while
their request is pending.

Clearing feedback ends that action and releases its entry; another attempt
starts fresh feedback. Empty status containers are hidden. Filesystem path
tokens reject control characters after normalization, including source imports;
line breaks separating imported paths are not part of a path token.

## Catalog refresh

The Home Leaderboard's administrator-only Refresh action checks the entire
workspace, independently of the current query or page. It updates new, changed,
or damaged index entries rather than forcing every source to be read again.
Configuration ingestion has no separate Reload or Rescan action. Refresh does
not reload server configuration from disk.

Startup displays the last valid catalog immediately while checking sources in
the background. Without a valid cache, the table waits for the initial build.
A separate progress region reports discovery counts, checked root
Trials against the discovered total, and index publication. A multi-step Trial
counts once, after all its entries have been processed. Unknown totals are not
shown as percentages. Assistive technology announces phase changes and can
read the current count on demand. Progress survives detail selection and independent action
feedback. Conflicting writes and duplicate refresh submissions remain disabled
from submission through operation completion and the resulting data refresh.
A Home page read that finds a scan in progress resumes status polling.

The internal read-only catalog-status resource reports generation, checking,
staleness, phase, counts, and errors without waiting for readiness or reading
evidence. Checking covers source reconciliation. An archive or delete reports
item progress through its operation until its reconciliation starts. Home observes
scan status every 250 milliseconds while checking instead of
repeatedly loading catalog pages. A locally initiated refresh supplies the same
status through its existing operation observer, avoiding a second polling loop.
Leaving Home stops that page's observation;
returning reads current status. Operation completion and generation changes
share one refresh owner, preserving filters, sorting, pagination, and detail
selection. A failed status read retries observation, never the refresh write.
Scan failure retains the last valid data and remains visible after read retries.
Administrators receive the operation ID of the current or most recent scan when
a manual refresh owns it. Guests receive progress and redacted errors without
the operation ID.

## Storage and identity

Saved View Markdown frontmatter owns the exact display name. Files use a fixed
length lowercase digest of that name, so distinct names remain distinct on
case-insensitive filesystems and accepted Unicode names fit filesystem component
limits. Reads verify that the name matches the file identity. Rename writes the
new identity before removing the old file; filters and notes remain editable.
If removing the old file fails, rename rolls back the new file and reports the
error. This two-file operation is not crash-atomic. Invalid or unsupported view
files remain untouched and produce a warning when omitted from listing.
Explicit overwrite or deletion by display name can recover a corrupt file at
that name's current storage identity without parsing its old contents. Linked
or non-regular targets remain rejected. Unsupported legacy storage layouts are
not migrated automatically.

Linked Trial references use
`harbor/<mount-id>/<job-name>/<trial-name>`. Workspace-authored Harbor overlays
contain only state, notes, and analysis. Catalog SQLite data, imported report
bodies, summaries, and render projections are rebuildable. Deleting a linked
source is unsupported; archive is the reversible hide operation.

Source keys remain stable across alias edits, queries, pages, state changes,
and report attachment. Mutations are generation-aware. Original databases,
trajectory inputs, and Harbor roots are never rewritten by report or catalog
rebuilds.
Catalog connections are closed even when connection initialization fails, before
any damaged cache files are removed for rebuilding.
Reconciliation reloads a source when its cached row is malformed, even when the
source fingerprint has not changed.
Wide timeline detail tables scroll within their own container; they do not
expand the workspace beyond the viewport on narrow screens.

In tables with a row action, clicking an editable cell's display content invokes
the same row action as other cells. A double click edits that cell without
triggering the row action or replacing its DOM. Row actions on editable content
wait briefly to distinguish the two gestures; a new pointer press cancels a
pending row action before release. Editor controls, links, buttons,
and selection checkboxes retain their own interactions; Enter on a focused
editable cell opens its editor.
Focused rows support Enter and Space for their row action. On an editable Saved
View cell, Enter edits and Space navigates to its summary. Keyboard row actions
are immediate and do not consume keystrokes from nested controls.

## Access model

The Reports page uses one report table and a right-hand detail area with Preview
and Associations tabs. The table shows report name, format, associations, and update
time. Reports are searched and filtered by their associations without a source-type
column or filter. Administrators can import a server-side Markdown or HTML
file without selecting a session, then add associations independently. Guests can
browse and filter the same library but cannot import, delete, or change associations.
Import shows a waiting message while the native file chooser is open on the
server's desktop. The chooser stays above other windows while active; cancelling
clears the waiting message without showing a cancellation notice, leaves the
library unchanged, and makes import available again. Selection failures remain
visible and allow retry.
Report filters open one menu at a time. Clicking outside or pressing Escape closes
the menu without clearing selected filters; Escape returns focus to its trigger.
The existing UTF-8, 20 MiB import limit and sandboxed HTML reader apply.
Report selection, pagination, and refresh preserve per-report association drafts;
responses for an older selection or draft cannot overwrite newer edits.
If the selected report's metadata returns 404 on refresh, its detail closes and
the active selection is cleared. A late response for another report cannot clear
the current selection. Temporary read failures retain the selection for retry;
association drafts remain available if a missing report reappears.
Escape closes report details and restores focus to the selected report's button.
Page navigation closes details without moving focus back to the previous page.
Saving associations and deleting the same report are mutually exclusive; a failed
deletion keeps the report and its draft available for retry.
Canonical source associations are read-only, while imported reports may also change
their directly associated sessions. Only imported report packages can be deleted here.
Dataset and Job associations follow the [report data contract](state-and-data.md#evaluation-reports).

The Home Trial sidebar keeps run status, score, and score source visible above
the applicable tabs, ordered Verification, Task, and Trajectory. Non-Harbor
Trials show only Trajectory. Harbor Trials always offer
Verification and Trajectory; Task is offered when the root Trial has a Task
name and its live Task metadata is not `not_configured`. Task resolution or
read errors remain visible within Task rather than hiding that tab.
Verification uses a searchable file tree and on-demand previews under the
[evaluation evidence contract](evaluation.md).
The preview content pane fills the remaining sidebar height and owns scrolling;
raw file text has no separate height cap or nested scroll area.
Complete JSON files offer a key-based collapsible view for nonempty objects,
arrays, and long strings. Small trees open initially; larger or deeply nested
trees defer branches until expanded, with collections loaded in batches and
bounded work per expansion. Existing score summaries remain available alongside
the JSON view, which is built only when selected. The verification browser opens
`verifier/score.json` first when available, then falls back to reward files and
the Trial result. This selection does not change the authoritative Trial score.
Recorded weighted formulas include normalization when weights do not sum to one.
Evidence links use retained manifest mappings, or the score's declared
verifier-relative evidence URI when no usable mapping exists, including when the
manifest cannot be fetched or parsed. Only safe paths already
present in the current Trial's retained file tree can be opened.
Switching to raw text preserves
expansion state, and copying uses the original file text. Malformed or truncated
JSON remains raw text.
Each new Trial selection opens Verification when applicable, otherwise
Trajectory; an explicitly requested applicable tab is honored, while selecting a
trajectory step opens Trajectory. An inapplicable tab in a shared location or
current selection falls back to the Trial's default and replaces the location
without adding browser history. Only applicable tabs and panels are mounted;
keyboard navigation visits those tabs, including a single Trajectory tab.
Inapplicable browsers are not initialized or loaded, and becoming inapplicable
invalidates their previous reads and state. Subagent navigation changes the
trajectory only; tab applicability and verification remain owned by the root
Trial or Harbor Step. Task availability does not control verification access.
Harbor Trials without retained verification files show their existing score
summary and an explicit empty or not-yet-generated state.
For a missing or removed source (HTTP 404/410), the sidebar uses the catalog's
existing summary and marks the trajectory unavailable. Temporary server or
network failures remain errors and do not fabricate missing evidence.

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

On Windows, the serve event loop retains Proactor support for ACP subprocess
pipes. A peer reset reported as WinError 10054 during socket shutdown is treated
as an already-disconnected peer, allowing socket closure and transport cleanup
to finish. Other socket and callback errors remain visible. This handling is
local to serve's socket transports and does not change the process-wide asyncio
policy or standard-library classes.

The ACP WebSocket and reference-candidate API are administrator-only and same-origin
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
overlays, or reports. On wide screens the Copilot drawer stays alongside the
workspace while navigating and while opening or closing a configuration dialog.
On narrow screens its Configure agents link dismisses the full-screen drawer
so the Agent settings are accessible. Navigation preserves the chat controller.
Copilot uses the workspace's light palette for its native controls and scrollbars
regardless of the operating system theme. The browser persists drawer and Agent
preferences and reconnect session identity. Text and images belong to the live
controller's session instance. In-page navigation, session selection and
same-controller reconnection preserve drafts; explicit disconnect, Agent change,
page reload and controller destruction end that guarantee. Old persistent
context and prompt-selection fields are removed without resetting other
preferences.
The host connection controls follow controller connection state, including
recovery initiated by the chat's Retry action.

The composer places References and Prompts above the input. References follows
the current workspace object, including automatic Home selections. A change
while its picker is open invalidates that selection. Each prompt shows a
single-line preview beside its name. Hovering the row reveals the full template.
The add button precedes Mode and groups images and Agent commands. The model
control beside Send shows the model name and effort. The model list groups
choices by provider. Separate Model and
Effort rows open the choices advertised by the Agent. Larger model lists
support search. Completed turns group
their intermediate steps behind a disclosure. Local submission and final-answer
times remain visible when known. History replay supplies no substitute for
missing original times.

Administrators share session pins, archives and display aliases within the workspace, scoped to the configured Agent and session ID. The session drawer reloads these preferences on open. Its row actions expose archive and pin directly on hover or keyboard focus and in the menu on touch. Pins sort first, and reading history preserves activity order and age. Archiving a session leaves its work accessible from Archived. The Agent owns its original title, messages and deletion. The stored activity
time and Agent title are display hints for off-page sessions. An edit from an
older session listing preserves newer dated hints. Concurrent changes to different preference fields merge,
and the last write to the same field wins. A damaged or oversized organization
file produces a drawer-local error and is preserved for recovery.

Inserting references or templates appends editable
text after a blank paragraph, preserves existing text, and never sends it.
Nothing is automatically attached on a later turn. Commands replace only an
exactly recognized leading command or are prefixed to the existing body;
missing argument hints do not discard arguments. Both template languages remain
available, with the interface language first and workspace overrides identified.

Reference candidates are administrator-only. Source references contain the
workspace, source_ref, `peval view tr` reading guidance and actual evidence
locations. A selected step includes trajectory_id and step_id; a Harbor phase
also supplies its directory. Imported sources and managed Jobs use their actual
artifact or Job output location and declared trajectory path, without inventing
Trial directories. Task candidates include both Task and Dataset roots. Task
resolution and digest comparisons are cached catalog observations identified by
their observation version, not a fresh validation. Canonical reports carry a
read-only path and owning source; imported packages carry their actual report
file and offer associated sources separately. Related candidates are optional;
missing or ambiguous locations explain why they are unavailable. No current
object means no workbench reference candidates.
Association lookup failures leave the report usable and appear as unavailable
candidates. Report associations are resolved in batches; the picker offers a
bounded set with an explicit truncation notice. Labels follow the interface
language, while reference text remains editable. Text previews can be selected
without changing the checkboxes; insertion requires an available selection.
Changing the current object or chat session while loading or choosing references
cannot append stale text to a draft.

Candidate generation reads only location metadata for the selected identities;
it never loads trajectory/report bodies, recomputes Task digests or reconciles
the whole workspace. Generated Windows paths use `/`, including `//server/share`
for UNC. Paths containing control characters are rejected; other field values
escape control characters. User-edited text is preserved verbatim.
POSIX paths preserve literal backslashes. Missing Task directories are reported
as unavailable without re-reading Task contents or updating cached observations.

An administrator inserting a reference intentionally discloses real paths to
the configured local Agent. This does not enlarge guest or ordinary browser
projections. Direct Agent filesystem access bypasses HTTP evidence redaction;
content is not promised to be sanitized or exempt from Agent permission checks.
A read-only label is guidance, not an OS sandbox. Canonical reports are still
published through `peval publish evaluation-report`.

Images retain original bytes and support selection, paste and composer drop;
ordinary files are not uploaded. Mixed text/image clipboard content prefers
text. File drops elsewhere never navigate the page. Unsupported images or Agent
capabilities leave the draft intact. Image admission, delivery uncertainty and
memory ownership follow the upstream composer contract. The gateway advertises
its message byte budget to the connector; subprocess lines, bidirectional frames
and the WebSocket server enforce that same value. Provider-specific and
conversation-wide image limits remain Agent/provider decisions.

Sessions are process-local, idle-expiring cookies. Direct HTTP is intended for
a trusted private network; the cookie is not marked `Secure` in this mode.
