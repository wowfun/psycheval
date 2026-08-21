# peval-py

Language: English | [简体中文](../i18n/zh-CN/peval-py/README.md)

peval-py converts retained Agent sessions to ATIF, builds static comparison
reports, and provides an Eval Workspace. It does not run Agents or score
Tasks.

Install and invoke the independently packaged tool as described in
[`tools/peval-py/README.md`](../../tools/peval-py/README.md).

## Quick Start

Export one JSONL session to ATIF:

```bash
peval-py export tr -p session.jsonl -o
```

Build a static report from the latest Psychevo session:

```bash
peval-py view tr -m raw -d ~/.psychevo/state.db -o
```

Create and serve a workspace:

```bash
peval-py init --root .local/peval-py
peval-py serve --root .local/peval-py
```

## Guides

- [Inputs and Adapters](inputs-and-adapters.md): JSONL, ATIF, SQLite,
  built-in and custom adapters.
- [Reports](reports.md): comparisons, notes, aliases, timing, localization, and
  cached analysis.
- [Eval Workspace](eval-workspace.md): guest/admin access, Harbor Dataset and
  Task management, browser-local Saved Views, sources, selection, and exports.

Stable behavior is specified by [`specs/300-peval-py`](../../specs/300-peval-py/spec.md)
and [`specs/310-eval-workspace`](../../specs/310-eval-workspace/spec.md).
