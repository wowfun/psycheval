# Evaluation Workspace HTTP Interface

## Initial Load

`GET /` returns the self-contained application shell without embedding a full
active report. The client then loads the catalog and requests report detail by
source key as needed.

## Mutation Results

Synchronous single-source mutations return a compact envelope containing the
resulting `generation`, changed source information or keys, and an optional
operation-specific result. They do not return complete `sources` or `report`
payloads.

Bulk reload, archive, activate, and delete operations return HTTP `202` with an
operation status that the client polls. Validation failures use an appropriate
4xx response and do not enqueue work.

## Source Inputs

JSON Path, DB, input-table, and upload interfaces may accept an initial alias
even though the corresponding browser add forms omit it. Adapter handling uses
the surface-specific rules in
[300. Inputs and Adapters](../300-peval-py/inputs.md).

## Exports

The generic export interface accepts normalized JSON and table XLSX kinds. It
rejects legacy `kind=html`. Workspace snapshot HTML is a separate strict
payload that includes resolved query scope, presentation, saved views, and
attached reports.

## Related Topics

- [Evaluation Workspace](spec.md)
- [Storage](storage.md)
- [Presentation](presentation.md)
