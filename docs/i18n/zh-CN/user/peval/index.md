# Peval 用户指南

[English](../../../../user/peval/index.md)

`peval` 是 Psycheval CLI 的命令简称。它处理保留的证据，不运行 Agent。

## 快速开始

```console
peval view tr -p <harbor-trial-dir>
peval view tr -m raw -d ~/.psychevo/state.db -o
peval init -r .local/evaluation
peval serve -r .local/evaluation
```

选择来源时使用[输入与 Adapter](inputs-and-adapters.md)，生成输出时使用
[报告](reports.md)，使用 serve mode 时查看[工作区](workspace.md)。稳定语义由
[CLI reference](../../../../reference/cli.md) 负责。
