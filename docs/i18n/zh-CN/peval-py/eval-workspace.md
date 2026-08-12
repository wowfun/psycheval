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

Source Manager 只导入 Session/ATIF path 和受支持的 SQLite DB，不再提供 input
table 或 snapshot upload 表单。Path 与 DB 表单支持多个带引号 path，保留
Windows/UNC path，并在 POSIX 上解析可用的 WSL mount path。

Serve 只会从显式挂载的 jobs root 直接读取单步 Harbor Trial，不再隐式扫描
workspace 或 `workspace/jobs`。每个 mount 都需要稳定的小写 ID；相对路径以
`peval-py.toml` 所在目录为基准：

```toml
[[harbor.mounts]]
id = "jobs-2026-08-08"
path = "../harbor/jobs"
task_paths = ["../datasets/pbench-v1.0"]
```

Source Manager 的 Harbor 区域可以添加、编辑和移除这些挂载。每个挂载包含一个
Jobs root，以及可选且有序的 Task 或本地 Dataset 路径。修改只写入 workspace
`peval-py.toml`，不会修改配置指向的 Harbor 文件。

来源引用固定为 `harbor/<mount-id>/<job-name>/<trial-name>`。Reload 直接从
Harbor 当前文件读取 trajectory、config、lock、result、reward 和运行状态，不会在
workspace 中复制这些内容。多步 Trial 显示 unsupported；无效 Trial 只显示当前错误，
不会回退到 last-good trajectory。已删除且没有用户 overlay 或 report binding 的 Trial
会直接消失；有引用的 Trial 保留 missing 行，并在相同 source reference 恢复后自动重连。

对每条可读 Trial，工作台会把 Task、Job、Trial、provider、完整 reward dimensions、
阶段 timing、Harbor 版本、result/regrade 标识和历史 Task provenance 投影到 catalog
与报告。Task identity 按 result、lock、config 顺序解析。Provider 只接受 Harbor 的
显式记录或明确的 `provider/model` 模型格式；不会从 agent 名或无前缀模型名猜测。

Task metadata 只会从 mount 的 `task_paths` 解析：优先匹配 lock/config 中的 Task path，
否则用完整 Task name 匹配 Dataset 的直接子目录。缺失或多解只产生诊断，不会隐藏
Trial。description、version、keywords 和 digest 来自当前白名单 Task，明确属于
**live metadata**，不是历史 Job 证据。Digest 不匹配时仍采用这些字段，并在 Selected
Trial 的 Harbor Evidence 区显示 mismatch。Package 或 Git artifact 的 `ref` 仍作为
历史 provenance 保留，但由于它与本地 live Task digest 覆盖的 artifact 范围不同，
两者会标记为不可比较。

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

Leaderboard 保留 canonical Session ID，并使用独立的紧凑 Task / 别名列。没有自定义
alias 时显示 Task name；存在 alias 时以 alias 为主，同时保留 Task 作为次级证据。
Tags 合并只读 Task keywords 与可编辑 custom tags，保持顺序并按大小写不敏感去重；
清空 alias 或 tags 后恢复 Task 派生显示。Job、Provider、Reward 可筛选；Task、Job、
Provider、Reward 可排序；Saved Views 与 Summary 可按 Task、Job、Provider 分组。
多维 reward 始终保持独立，只有 `reward` 维度或唯一维度会进入数值分布。

JSON report、静态/workspace snapshot、Source inspect、Table/Summary XLSX 导出会同步
携带 Task、Job、Trial、provider、reward dimensions、display/custom overlay 与 Harbor
provenance。

Path 和 DB 的 `auto` 要求唯一推断。浏览器新增表单有意不展示 alias；CLI、JSON
interface 和已保存行的内联编辑支持 alias。

Archive/delete 只修改 workspace state，不删除原始文件或数据库。关联的 Harbor
Trial 不能删除，应使用 Archive 隐藏。可刷新 Harbor source 更新 overlay
`notes.md`；不可变的本地 snapshot artifact 保持只读。`peval-py import analysis --source-ref ...`
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
