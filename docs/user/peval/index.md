# Peval User Guide

[简体中文](../../i18n/zh-CN/user/peval/index.md)

`peval` is the short command name for the Psycheval CLI. It works with retained
evidence rather than running an Agent.

## Quick start

```console
peval view tr -p <harbor-trial-dir>
peval view tr -m raw -d ~/.psychevo/state.db -o
peval init -r .local/evaluation
peval serve -r .local/evaluation
```

Use [Inputs and adapters](inputs-and-adapters.md) for source selection,
[Reports](reports.md) for output workflows, and [Workspaces](workspace.md) for
serve mode. Stable semantics live in the [CLI reference](../../reference/cli.md).
