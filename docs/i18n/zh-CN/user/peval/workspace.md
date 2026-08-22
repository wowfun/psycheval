# 工作区

[English](../../../../user/peval/workspace.md)

初始化并启动工作区：

```console
peval init -r .local/evaluation
peval serve -r .local/evaluation
```

工作区发现与初始化语义由
[workspace reference](../../../../reference/workspace.md) 负责。

## 统一配置

同一份文件可以配置 Psycheval CLI 与 Harbor host execution：

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

配置所有权与路径语义由
[workspace reference](../../../../reference/workspace.md) 负责。

## Serve 访问

绑定非本地地址前，遵循
[workspace reference](../../../../reference/workspace.md) 中的访问规则。

将分析报告导入指定 source reference：

```console
peval import analysis -r .local/evaluation \
  --source-ref runs/default/psychevo/<session>/<cell> \
  -p analysis.json -p analysis.md
```
