# Workspaces

[简体中文](../../i18n/zh-CN/user/peval/workspace.md)

Initialize and serve a workspace:

```console
peval init -r .local/evaluation
peval serve -r .local/evaluation
```

Workspace discovery and initialization semantics live in the
[workspace reference](../../reference/workspace.md).

## Unified configuration

One file may configure both the CLI and Harbor host execution:

```toml
description = "Nightly evaluation workspace"

[adapters.psychevo]
default_db_path = "~/.psychevo/state.db"

[harbor.host]
workdir_root = "../workspaces"

[[harbor.datasets]]
id = "pbench"
path = "../datasets/pbench-v1.0"

[[harbor.mounts]]
id = "nightly"
path = "../jobs"
dataset_ids = ["pbench"]
```

Configuration ownership and path semantics live in the
[workspace reference](../../reference/workspace.md).

## Serve access

Before binding to a non-local address, follow the access rules in the
[workspace reference](../../reference/workspace.md).

Import authored analysis into a selected source reference with:

```console
peval import analysis -r .local/evaluation \
  --source-ref runs/default/psychevo/<session>/<cell> \
  -p analysis.json -p analysis.md
```
