# Evaluation Workspace Access Control

## Roles and Activation

Serve has two workspace-wide roles: anonymous `guest` and authenticated
`admin`. A guest may browse workspace data and create read-only exports; only
an admin may inspect server-side source locations, start refresh operations, or
change workspace state and configuration. There are no named users or
per-source permissions.

Guests may browse live Dataset and Task identities, Task diagnostics, file
trees, and bounded UTF-8 Task file content. This intentionally includes
solution and verifier text. Guests cannot inspect Dataset locations, revisions,
trash, mount configuration, binary content, oversized content, or downloads.
Every Dataset, Task, manifest, and file mutation remains administrator-only;
direct browser action functions fail closed before issuing a request.

`PEVAL_PY_ADMIN_PASSWORD` is resolved for serve only. The first non-empty value
from the process environment and then the workspace-root `.env` file enables
authentication. The dotenv file is read but never loaded into the process or
written by peval-py. Operators restrict that file to the workspace owner's
account on multi-user hosts. Password and dotenv changes require a serve
restart. The dotenv input must be a regular non-symlink file; a symlink or other
file type is rejected rather than read.

When authentication is disabled, a localhost listener treats every request as
admin. A non-local listener without a configured password is rejected before
binding. Direct non-local HTTP is intended only for a trusted private network.

## Sessions

Login creates an opaque 32-byte random token held only in process memory. The
browser receives a host-only session cookie with `HttpOnly`, `SameSite=Strict`,
and `Path=/`; it has no persistent expiry or `Secure` attribute in direct HTTP
mode. Sessions expire after twelve hours without an authenticated request and
all sessions disappear when serve stops. Expired session records are reclaimed
during later authentication activity rather than accumulating until restart.
Logout revokes the presented token.

Password comparisons are constant-time. Five failed logins from one client
address in a rolling minute cause subsequent attempts in that window to return
HTTP 429. A successful login clears that client's failures, and expired client
failure buckets are reclaimed during later login attempts.

## HTTP Authorization

`GET /api/auth/session` reports whether authentication is enabled and the
request's current role. `POST /api/auth/login` accepts one `password` string;
success returns the admin role and sets the session cookie, while invalid
credentials return HTTP 401. `POST /api/auth/logout` is idempotent and clears
the session cookie.

Guest access includes the Home, Datasets, and Reports pages; assets; catalog
and detail reads; the projected Harbor Dataset reads above; Saved View reads
and summaries; browser-local Saved View mutation; attached report inventory and
readers; catalog selection resolution; and every existing export kind. Guest
access excludes the Sources page, source inventory, DB and path inspection,
operation status, refresh/reload, and every workspace or configuration
mutation. Admin access includes all serve behavior. Browser-local mutation is
not a workspace mutation and follows [Saved Views](saved-views.md). Route
authorization is centralized and unclassified routes fail closed;
presentation hiding is not an authorization control.

JSON POSTs, including login and logout, retain the same-origin requirement.
Application, authentication, and data responses are not cacheable and carry
the serve security headers.

## Guest Projection

Every guest page, JSON response, and export uses a guest projection. Catalog
rows omit `path`, `input_path`, `db_path`, `source_ref`, `artifact_dir`,
`last_error`, and equivalent server-only source fields. Report metadata omits input and analysis artifact
paths, live Task paths and diagnostics, regrade paths, and equivalent source
references; a path-bearing source label becomes a basename suitable for
display. Guest startup payloads never contain adapter DB defaults, Harbor mount
configuration, or detailed startup errors, and guest HTTP errors do not expose
internal exception text. Ordinary client-facing validation, including public
API request targets, remains visible when it contains no server location.
Internal Task metadata and Harbor provenance containers are projected through
explicit public-field allowlists so newly introduced metadata is private until
classified for guest display.

Guest Dataset projection independently allowlists Dataset ID, live Task
directory, package identity, status, sanitized diagnostics, and Task file
metadata. It removes physical roots, revisions, root-file inventory, manifest
state, and trash. The text-file endpoint returns bounded content but rejects its
download mode for guests.

The projection does not rewrite paths contained inside prompts, tool arguments,
tool results, notes, analysis prose, or administrator-published Markdown/HTML
reports. Existing report secret-redaction configuration, including explicit
`--no-redact`, remains authoritative.

## Presentation

The serve shell exposes `role`, `authentication_enabled`, and the active serve
page. Its global navigation contains Home, Datasets, and Reports for guests and
adds Sources for administrators. Guests see login, read-only Dataset browsing,
and read-only report browsing while global locale changes, refresh, inline
source and notes editing, workspace Saved View mutation, and report
import/binding/deletion are absent. Admins see the complete controls plus
logout. An expired administrator on Sources returns to Home; other pages reload
into their guest presentation.

## Related Topics

- [Evaluation Workspace](spec.md)
- [Harbor Dataset Management](harbor-datasets.md)
- [Saved Views](saved-views.md)
- [HTTP Interface](http.md)
- [Presentation](presentation.md)
- [Testing](testing.md)
