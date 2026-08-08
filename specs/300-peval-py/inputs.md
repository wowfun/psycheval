# peval-py Inputs and Adapters

## Input Forms

peval-py accepts source paths, supported SQLite databases, JSON/JSONL report or
trajectory uploads, and CSV/JSON/XLSX input-table manifests. Original inputs are
read-only. Directory inputs expand deterministically and invalid entries report
their own failure rather than silently changing source identity.

Serve-mode linked Harbor sources use the discovery and persistence contract in
[310. Evaluation Workspace Storage](../310-eval-workspace/storage.md).

Input-table rows may provide the documented path, adapter, alias/label, and
source metadata columns. `alias`, `label`, and `source_alias` are accepted alias
forms at this machine-readable interface.

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
- Evaluation Workspace Path, DB, and input-table sources treat omitted or
  `auto` as infer-or-fail. Ambiguous or absent inference is a client error rather
  than a default fallback.
- Workspace JSONL upload with omitted or `auto` adapter falls back to the current
  configured adapter.
- ATIF and normalized report JSON uploads are adapter-free.

An explicit adapter always wins when it supports the selected input form.

## Alias Surfaces

The CLI `serve --source-alias`, input-table manifests, and JSON source/upload
interfaces accept an initial alias. Browser Path, DB, input-table, and upload add
forms intentionally omit an alias field. After import, aliases may be edited
inline in Source Manager and Leaderboard surfaces.

## Related Topics

- [peval-py](spec.md)
- [310. Workspace HTTP](../310-eval-workspace/http.md)
- [310. Workspace Presentation](../310-eval-workspace/presentation.md)
