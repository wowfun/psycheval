# Inputs and Adapters

## Paths and ATIF

JSONL accepts one object per line. A line may be a direct message or a wrapper
with `message`, `usage`, `metadata`, `accounting`, and `session_seq`.

```bash
peval-py export tr -a opencode -p session.jsonl -o
peval-py view tr -m raw -p trajectory-opencode-session.json -o
```

Exported ATIF JSON is adapter-free and appears with adapter `atif` in report
metadata.

## Built-in Adapters

- `psychevo`: JSONL and Psychevo `state.db`; default DB
  `~/.psychevo/state.db`.
- `opencode`: JSONL and OpenCode SQLite; default DB
  `~/.local/share/opencode/opencode.db`.
- `hermes`: JSONL and Hermes SQLite; default DB `~/.hermes/state.db`.
- `deepagents`: one top-level JSON object using `session_id`, `started_at`,
  `query`, `llm_steps`, and `tool_steps`; path only, with no default DB.

Use `-d @adapter` to expand a configured default DB path. List and select DB
sessions with `--list`, `--list-interactive`, `-s ID`, or `-s #N`:

```bash
peval-py view tr -d @opencode --list
peval-py view tr -m raw -d @hermes -s '#2' -o
```

For multiple DBs, bind adapters and sessions by one-based DB index:

```bash
peval-py view tr -m raw \
  -d ~/.hermes/state.db \
  -d ~/.local/share/opencode/opencode.db \
  -a d1=hermes -a d2=opencode \
  -s d1=<hermes-id> -s d2=<opencode-id> \
  -o
```

## Automatic Adapter Selection

For direct CLI paths, peval-py first infers an adapter from full path-component
or filename tokens. Ambiguity fails; no match falls back to configured/default
adapter selection. Eval Workspace Path and DB forms instead require unique
inference when `auto` is selected. peval-py has no input-table CLI or Source
Manager snapshot upload; combine repeatable `-p` and `-d` inputs directly.

## Custom Adapters

Register an installed entry point whose name becomes the adapter id:

```toml
[project.entry-points."peval_py.adapters"]
custom = "custom_peval_adapter:CustomAdapter"
```

An adapter implements at least one of `convert(records, config)`,
`convert_path(path, config)`, or `convert_db(path, session_id, config)`.
Adapter-specific TOML belongs under `[adapters.<id>]`. Reserved
`default_db_path` values expand `~` and resolve relative paths against their
defining config file; they are not passed to adapter code.
