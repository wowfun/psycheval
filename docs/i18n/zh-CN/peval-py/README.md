# peval-py

语言：[English](../../../peval-py/README.md) | 简体中文

peval-py 用于将保留的 Agent session 转换为 ATIF、生成静态对比报告，以及
提供本地评测工作台。它不运行 Agent，也不为 Task 评分。

独立工具的安装和源码运行方式见
[`tools/peval-py/README.zh-CN.md`](../../../../tools/peval-py/README.zh-CN.md)。

## 快速开始

导出一个 JSONL session：

```bash
peval-py export tr -p session.jsonl -o
```

为最近的 Psychevo session 生成静态报告：

```bash
peval-py view tr -m raw -d ~/.psychevo/state.db -o
```

创建并启动本地工作台：

```bash
peval-py init --root .local/peval-py
peval-py serve --root .local/peval-py
```

## 指南

- [输入与 Adapter](inputs-and-adapters.md)：JSONL、ATIF、SQLite 和自定义
  adapter。
- [报告](reports.md)：对比、备注、别名、时间、本地化和 cached analysis。
- [评测工作台](eval-workspace.md)：source、存储、跨页选择和导出。

稳定行为由 [`specs/300-peval-py`](../../../../specs/300-peval-py/spec.md) 和
[`specs/310-eval-workspace`](../../../../specs/310-eval-workspace/spec.md) 定义。
