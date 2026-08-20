# Evaluation Workspace Saved Views

## Authority and Identity

Saved Views have two independent authorities. Workspace views are shared,
server-owned records; browser views are device-local records and never mutate,
sync to, or automatically become workspace state. Both kinds use the same view
definition and Catalog query semantics.

The browser identifies a view as `server:<name>` or `browser:<name>` so selected,
applied, and expanded state cannot silently change authority. Names conflict by
exact string equality. A server view wins presentation conflicts: a browser view
with the same name remains stored but is hidden, and becomes visible again if the
server view disappears. If a browser view being applied becomes hidden, it is
removed from the applied set; remaining views are reloaded, or the default
Catalog conditions are restored. It is never replaced with the same-named server
definition.

## Browser Storage

Browser views are stored under `peval-py.saved-views.v1.<workspace_id>` in the
current origin's browser storage, as `{version: 1, views: [...]}`. The opaque
workspace identifier provides workspace isolation within an origin. Browser
views survive login and logout and are available to guests and administrators.

Each entry contains `name`, normalized `filters`, `group_by`, and `notes` and
obeys the same name, filter, grouping, and 1 MiB notes constraints as a workspace
view. A workspace may have at most 100 browser views. Unsupported versions,
malformed stored values, storage read failures, storage write failures, and
quota failures do not produce an in-memory success; the browser reports an
actionable error. Creating or renaming a browser view to a current server name
is rejected. Replacing an existing browser name requires confirmation.

Browser view persistence and merging live behind one repository interface. UI
callers do not access browser storage or branch persistence behavior by role.
The repository owns the server HTTP adapter, browser storage adapter, validation,
conflict filtering, source-aware mutation ordering, and construction of query
payloads.

## Query and Summary Semantics

`POST /api/catalog/query` accepts a normalized Catalog query containing server
view names plus `browser_views` containing the applied browser definitions, and
returns the same Catalog page as `GET /api/catalog`. The browser keeps using GET
when no browser view is applied. The complete predicate is `(server view OR
browser view) AND current refinement`.

`POST /api/views/summary` accepts `browser_views` and returns the same summary
shape as the existing server-view GET summary. The browser merges the server GET
and browser POST results. Every server entry point validates browser definitions
with the workspace-view validation rules, rejects duplicate names, unknown
fields, invalid values, and requests exceeding 100 definitions with HTTP 400,
and rejects a definition whose name now conflicts with a server view with HTTP
409.

Export queries and Saved Views Summary requests carry server names and browser
definitions separately. Table XLSX, Leaderboard Summary, Saved Views XLSX, and
workspace snapshots use the same complete query predicate. A snapshot embeds
the browser definitions, notes, and summaries needed to reproduce its view
library without browser storage.

The POST query and summary routes are read-only guest routes and retain the
serve same-origin JSON check, no-store policy, and guest response projection.

## Presentation and Mutation

The Saved Views list is sorted by display name. Browser rows carry a compact
local marker and can be edited or deleted by guests and administrators; server
rows are editable only by administrators. Browser saving is enabled only after
the server directory has loaded successfully, because absence of a conflicting
server name must be known.

Guests save only to this browser. Administrators choose Workspace or This
browser, with Workspace as the default. A guest mixed selection deletes only
the local subset, labels the exact deletable count, and retains server
selection. An administrator deletion dispatches by authority and completes the
server deletion before committing local deletion, preventing partial local
deletion when the server request fails.

## Related Topics

- [Evaluation Workspace](spec.md)
- [Access Control](access.md)
- [Storage](storage.md)
- [HTTP Interface](http.md)
- [Presentation](presentation.md)
- [Testing](testing.md)
