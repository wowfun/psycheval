# 评测工作台

## 初始化与启动

```bash
peval-py init --root .local/peval-py
peval-py serve --root .local/peval-py
```

`init` 只创建 `peval-py.toml` 和 `state.db`，并保留已有的有效 state path。
`serve` 按显式 root、`PEVAL_ROOT` 或当前/父级配置解析 workspace。首页先加载空壳，
再按需请求 catalog 和选中的 report。

本地页面使用缓存的 ECharts 6.0.0；只有本地 asset 加载失败时才回退到固定 CDN。

## Source

Source Manager 可导入 Session/ATIF path、受支持的 SQLite DB、input table、
JSONL、ATIF JSON 和规范化 report JSON。Path 与 DB 表单支持多个带引号 path，
保留 Windows/UNC path，并在 POSIX 上解析可用的 WSL mount path。

Serve 只会从显式挂载的 jobs root 直接读取单步 Harbor Trial，不再隐式扫描
workspace 或 `workspace/jobs`。每个 mount 都需要稳定的小写 ID；相对路径以
`peval-py.toml` 所在目录为基准：

```toml
[[harbor.mounts]]
id = "jobs-2026-08-08"
path = "../harbor/jobs"
```

来源引用固定为 `harbor/<mount-id>/<job-name>/<trial-name>`。Reload 直接从
Harbor 当前文件读取 trajectory、config、lock、result、reward 和运行状态，不会在
workspace 中复制这些内容。多步 Trial 显示 unsupported；无效 Trial 只显示当前错误，
不会回退到 last-good trajectory。已删除且没有用户 overlay 或 report binding 的 Trial
会直接消失；有引用的 Trial 保留 missing 行，并在相同 source reference 恢复后自动重连。

旧版 Harbor ATIF-v1.x 只有在“仅替换 schema 标识”后能通过当前完整校验时，才会以
内存兼容视图读取。Serve 从 canonical steps 派生缺失的聚合计数，并可从匹配的 Harbor
result 或结构一致的 Trial telemetry 补充缺失的耗时与计费字段，包括 OpenCode Trial
database、Psychevo Trial 独占 database 与 runtime trace，以及 Hermes session export。
共享同一命名空间时，session、step、message 和 tool-call identity 必须一致。Harbor 的
Hermes wrapper 与原生 Hermes export 使用不同 session ID，因此用“同一 Trial 内文件”加
step/message/tool-call 精确对齐作为证明。trajectory 中已有的值始终优先。精确 runtime
timing 优先于有界的模型调用边界估算；估算值会参与模型耗时汇总，同时保留
`duration_source` 来源标识。失败且没有 trajectory 的 Trial 会在 Source Manager 中显示
当前 Harbor 异常，但不能作为 trajectory report 打开或导出。

Archive、alias、category、tags、notes 和 analysis 会按需写入
`harbor/<mount-id>/<job-name>/<trial-name>/` overlay。仅浏览或 Reload 不会创建该目录。
`[harbor].roots` 与 `harbor-link.json` 属于不兼容的旧 projection layout；请初始化新
workspace，不要原地迁移。

Path、DB 和 input-table 的 `auto` 要求唯一推断。JSONL upload 回退到 workspace
配置；ATIF/report upload 不需要 adapter。浏览器新增表单有意不展示 alias；CLI、
manifest、JSON interface 和已保存行的内联编辑支持 alias。

Archive/delete 只修改 workspace state，不删除原始文件或数据库。关联的 Harbor
Trial 不能删除，应使用 Archive 隐藏。可刷新 Harbor source 更新 overlay
`notes.md`；上传的 snapshot 保持只读。`peval-py import analysis --source-ref ...`
通过 source reference 定位本地 Trial artifact 或 Harbor overlay。

## 选择与 Summary

Leaderboard 和 Source Manager 各自维护跨页 selection。表头 checkbox 只切换当前
页，action 使用完整 retained selection；已不存在的 source 才会被 reconcile 清除。

Live serve 在 0、1、多行时都显示 Summary，0 行显示 empty shell。Workspace
snapshot 至少要匹配 1 行，并从 1 行开始显示 Summary。

## 导出

| 导出 | 范围 |
| --- | --- |
| Table `.xlsx` | 完整、未分页 query 的所有行；忽略 selection。 |
| JSON Report | 有选择时使用全部 retained key，否则使用当前 catalog 页；最多 100 个 cell。 |
| Workspace snapshot `.html` | 无选择时使用完整 query，否则使用 query 与 retained selection 的交集；最终最多 100 行。 |
| Summary `.xlsx` | 当前可见 Leaderboard 页；忽略 selection。 |

Serve 菜单只包含 Table、JSON Report 和 Workspace snapshot，不存在旧 HTML Report。
Snapshot HTML 是独立的自包含 workspace 导出。

同步单 source mutation 返回紧凑的 generation/change 数据。批量 reload、state 和
delete 返回 queued status 并由客户端轮询；两类响应都不嵌入完整 report。
