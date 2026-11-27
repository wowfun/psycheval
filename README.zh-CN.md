# Psycheval

[English](README.md)

Psycheval 用于运行兼容 Harbor 的评测、将 Agent 会话转换为 ATIF，并检视评测工作区。
安装后的命令行工具名为 `peval`；它只是命令简称，不是 Python 包命名空间。

## 安装

Psycheval 支持 Python 3.12–3.14。在下游项目中安装：

```console
uv add "psycheval==0.1.0rc1"
```

如需独立命令行工具，同时暴露 Psycheval 及其 Harbor 依赖：

```console
uv tool install --python 3.14 --with-executables-from harbor "psycheval==0.1.0rc1"
```

在项目环境中使用 `uv run peval` 和 `uv run harbor`；独立工具安装则直接提供
`peval` 和 `harbor`。源码可编辑安装见[开发指南](docs/development.md)，可选的
WorkBuddy 运行时安装或源码拷贝方式见[集成工作流](docs/user/downstream-vendoring.md)。

当前为预发布版本，不提供兼容性保证，请锁定精确版本号。公开集成界面仅限于文档中定义的
[Harbor 接口](docs/reference/harbor.md)、独立 ATIF 校验器、`psycheval.cli.main`
以及 [Harness 插件协议](docs/reference/jobs.md#harness-interface)。其他可导入模块与
本地浏览器 HTTP API 均为内部实现。完整包会安装 [pyproject.toml](pyproject.toml) 中声明的
依赖约束，包括精确锁定的 Harbor 与 ACP 版本。

## 快速开始

初始化工作区并查看命令树：

```console
peval init -r .local/evaluation
peval --help
peval view trajectory --help
peval view tr -p <harbor-trial-dir>
```

第一条命令仅在 `.local/evaluation` 下初始化工作区状态。可选的
[Agent Skill](skills/peval/SKILL.md) 随对应版本 tag 的源码单独分发，不包含在 Python 包内。
下载已安装发行版对应的源码压缩包并解压后，执行
`peval init -r .local/evaluation --skill <source-directory>/skills/peval`，
即可显式安装或替换该工作区的 Skill。图表视图会在首次使用时下载固定版本的 ECharts 资源，
并缓存在工作区中。

## 文档

建议先阅读[架构说明](docs/architecture.md)。CLI 工作流请参阅
[`peval` 用户指南](docs/i18n/zh-CN/user/peval/index.md)，修改本仓库代码时请参阅
[开发指南](docs/development.md)。
