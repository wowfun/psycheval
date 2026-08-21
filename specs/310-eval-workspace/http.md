# Evaluation Workspace HTTP Interface

Authentication, route authorization, and role-dependent response projection
are specified by [Access Control](access.md).

Browser-local Saved View query, summary, conflict, and export payload behavior
is specified by [Saved Views](saved-views.md).

## Initial Load

Live serve has real page routes: `GET /`, `GET /datasets`, `GET /reports`, and
administrator-only `GET /sources`. Each returns the shared shell with one
active page and a `serve_page` render option; direct refresh and browser history
therefore retain the page. Home lazily loads the catalog and report detail,
Datasets loads only Harbor inventory, Reports loads its report catalog plus
administrator binding data when applicable, and Sources loads its source page.
Inactive management markup is not embedded in Home.

Guests may call `GET /api/harbor/datasets`, `GET /api/harbor/tasks`,
`GET /api/harbor/task`, and non-download `GET /api/harbor/files` through the
projection specified by Access Control. Guest `download=1` and every Harbor
POST return `403`.

Shell, authentication, and API responses are not cacheable. A versioned static
asset may instead use a long-lived immutable cache policy while retaining
`nosniff` and referrer protections.

Only explicitly classified request-validation failures return `4xx`. An
unexpected exception, including an unclassified `ValueError`, returns `500`;
guest responses use the generic projected error while administrator responses
may retain the diagnostic.

## Mutation Results

Synchronous single-source mutations return a compact envelope containing the
resulting `generation`, changed source information or keys, and an optional
operation-specific result. They do not return complete `sources` or `report`
payloads.

Bulk reload, archive, activate, and delete operations return HTTP `202` with an
operation status that the client polls. Validation failures use an appropriate
4xx response and do not enqueue work.

## Source Inputs

The Sources-page HTTP interface accepts only Path and DB sources. These JSON
interfaces may accept an initial alias even though the corresponding browser
forms omit it. It has no input-table or snapshot-upload mutation. Adapter
handling and the export-only workspace snapshot format are specified in
[300. Inputs and Adapters](../300-peval-py/inputs.md).

The Harbor mount configuration mutation replaces, updates, or removes one
explicit mount in workspace `peval-py.toml`. It accepts a mount ID, one Jobs
root, and ordered Dataset IDs, then reloads the derived catalog through the new
configuration. Dataset registration and Task/file interfaces are specified by
[Harbor Dataset Management](harbor-datasets.md). Mount mutation never writes to
a Jobs root.

Catalog queries accept repeatable `task`, `job`, and `provider` refinements in
addition to the existing filters and return matching Task, Job, and Provider
facets. Task, Job, Provider, and scalar Reward are sortable. Saved View and
workspace-snapshot query payloads use the plural `tasks`, `jobs`, and
`providers` arrays; absent arrays remain empty so existing Saved Views continue
to load.

Catalog rows expose Avg TTFT, Decode TPS, Cache Hit, the sufficient statistics
needed to recompute them, and `analysis_count` as the 0–2 count of distinct
Harbor/workspace analysis sources. The three inference display values are
sortable with nulls last. A catalog page also returns, from the same generation
and unpaginated query predicate, a model-inference aggregate with matched and
covered Trial counts and a canonical-column non-empty count map. These values
drive the query-wide summary and stable automatic column visibility.

## Exports

The generic export interface accepts normalized JSON and table XLSX kinds. It
rejects legacy `kind=html`. Workspace snapshot HTML is a separate strict
payload that includes resolved query scope, presentation, saved views, and
attached reports. Snapshot presentation includes the versioned Leaderboard
column order and manual visibility overrides.

A Leaderboard Summary XLSX request carries both the ordered source keys for its
current-page distribution and the normalized complete catalog query, including
applied Saved View names. The server derives the inference overview from that
query in the same catalog generation rather than inferring complete-query scope
from the page keys.

## Related Topics

- [Evaluation Workspace](spec.md)
- [Access Control](access.md)
- [Harbor Dataset Management](harbor-datasets.md)
- [Saved Views](saved-views.md)
- [Storage](storage.md)
- [Presentation](presentation.md)
