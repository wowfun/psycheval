# peval-py Inputs and Adapters

## Input Forms

peval-py inputs accept source paths and supported SQLite databases. Original
inputs are read-only. Directory inputs expand deterministically and invalid
entries report their own failure rather than silently changing source identity.

The Evaluation Workspace Source Manager accepts only Path and supported SQLite
DB sources. It does not expose input-table or file-upload inputs. The CLI does
not accept input-table manifests. Workspace snapshots are an export format
rather than an import format.

Serve-mode linked Harbor sources use the discovery and persistence contract in
[310. Evaluation Workspace Storage](../310-eval-workspace/storage.md).

## Built-in Adapters

The built-in adapter set is:

- `opencode`
- `hermes`
- `psychevo`
- `deepagents`

Deepagents is a path-based JSON adapter. One input file is a top-level object
whose session fields include `session_id`, `started_at`, `query`, `llm_steps`,
and `tool_steps`. It supports JSON file and directory discovery, has no dedicated
database conversion, and has no default database path.

## Automatic Selection

Automatic adapter behavior is intentionally surface-specific:

- Direct CLI path input without an explicit bare `-a` first uses path-token
  inference; when no adapter is inferred, it falls back to configured/default
  adapter selection.
- Evaluation Workspace Path and DB sources treat omitted or `auto` as
  infer-or-fail. Ambiguous or absent inference is a client error rather than a
  default fallback.

An explicit adapter always wins when it supports the selected input form.

## Alias Surfaces

The CLI `serve --source-alias` and JSON Path/DB source interfaces accept an
initial alias. Browser Path and DB add forms intentionally omit an alias field.
After import, aliases may be edited inline in Source Manager and Leaderboard
surfaces.

## Related Topics

- [peval-py](spec.md)
- [310. Workspace HTTP](../310-eval-workspace/http.md)
- [310. Workspace Presentation](../310-eval-workspace/presentation.md)
