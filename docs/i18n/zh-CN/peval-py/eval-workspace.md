# 评测工作台

## 初始化与启动

```bash
peval-py init --root .local/peval-py
peval-py serve --root .local/peval-py
```

`init` 只创建 `peval-py.toml` 和 `state.db`，并保留已有的有效 state path。
`serve` 按显式 root、`PEVAL_ROOT` 或当前/父级配置解析 workspace。首页先加载空壳，
再按需请求 catalog 和选中的 report。

可以在 `peval-py.toml` 顶层添加可选的 `description`，用 Markdown 在主页内容上方右侧
显示简短说明：

```toml
description = "**夜间评测**工作台 — 发布候选检查"
```

字段缺失或仅含空白时不会占位。说明对访客和管理员均可见，原始 HTML 会被转义，
Workspace snapshot 导出也会保留这段内容。

本地页面使用缓存的 ECharts 6.0.0；只有本地 asset 加载失败时才回退到固定 CDN。

## 访客与管理员访问

Serve 提供匿名访客角色和一个 workspace 级共享管理员密码。访客可以浏览、筛选、
打开完整轨迹、笔记、分析、Saved Views、已导入报告，以及已注册的 Harbor Dataset 与
Task。Dataset 的访客权限包括 Task 文件树和不超过 2 MiB 的 UTF-8 文本（含 solution 与
verifier），但不允许下载，也不会返回 Dataset 物理路径、revision、回收区、mount 配置或
写入动作。访客还可以执行全部只读评测导出。Source
位置与诊断、刷新与操作状态、source 管理、配置、笔记编辑、工作区 Saved View 修改和
报告绑定必须先以管理员身份登录。

localhost 未配置密码时自动拥有管理员权限。监听非本机地址必须配置
`PEVAL_PY_ADMIN_PASSWORD`。Serve 依次采用非空进程环境变量和
`<workspace>/.env`：

```dotenv
PEVAL_PY_ADMIN_PASSWORD='请替换为足够长的随机密码'
```

在多用户 POSIX 主机上，应把文件权限限制为仅 workspace 所有者可读：

```bash
chmod 600 .local/peval-py/.env
```

```bash
peval-py serve --root .local/peval-py --host 0.0.0.0
```

`.env` 仅由 `serve` 读取；peval-py 不会创建、修改该文件，也不会把它加载进进程
环境。修改密码后需要重启。管理员 session 使用浏览器 session Cookie 和进程内存，
空闲 12 小时后过期，重启或退出登录也会立即失效。

非本机模式是直接 HTTP，只能用于受信私有网络，不能作为公网服务直接暴露。访客
响应和导出会删除结构化服务器 path 与运维诊断；提示词、工具证据、笔记正文、分析
正文以及管理员主动导入报告中的 path 仍属于评测内容，不会被改写。

## 浏览器本地 Saved Views

访客和管理员都可以把当前筛选、搜索、source 状态、分组和备注保存到当前浏览器。
这些视图按 origin 与不透明 workspace ID 隔离，登录状态变化后仍会保留，且不会上传或
共享。本地视图与工作区视图一样支持应用、OR 组合、摘要、Table/Leaderboard/Saved
Views XLSX 导出和 workspace snapshot。管理员保存时选择“工作区”或“此浏览器”；访客
始终保存到本地。

完全同名时工作区视图优先，本地副本保留但暂时隐藏，工作区名称消失后自动恢复。
浏览器存储或配额失败会显示错误，不会伪装成保存成功。Workspace snapshot 会嵌入所含
本地视图的定义、备注和摘要，打开导出页面时不依赖原浏览器。

## Source

Live serve 提供四个可直接访问的页面：主页 `/`、数据集 `/datasets`、报告 `/reports`
和来源 `/sources`。共享的顶部左侧导航会标记当前页面，并支持刷新、收藏和浏览器前进
后退。访客只看到主页、数据集和报告；来源入口不渲染，直接访问返回 `403`。每个页面只
加载自身初始数据。主页从可选的右对齐说明和 Leaderboard 开始，不重复显示主页标题、
来源计数或页面级刷新动作；打开数据集页面不会启动 Leaderboard catalog 请求。

来源页面只导入 Session/ATIF path 和受支持的 SQLite DB，不再提供 input
table 或 snapshot upload 表单。Path 与 DB 表单支持多个带引号 path，保留
Windows/UNC path，并在 POSIX 上解析可用的 WSL mount path。

Serve 只会从显式挂载的 jobs root 直接读取单步 Harbor Trial，不再隐式扫描
workspace 或 `workspace/jobs`。每个 mount 都需要稳定的小写 ID；相对路径以
`peval-py.toml` 所在目录为基准：

```toml
[[harbor.datasets]]
id = "pbench"
path = "../datasets/pbench-v1.0"

[[harbor.mounts]]
id = "jobs-2026-08-08"
path = "../harbor/jobs"
dataset_ids = ["pbench"]
```

来源页面的 Harbor 区域可以添加、编辑和移除这些挂载。每个挂载包含一个
Jobs root 和一组有序的已注册 Dataset ID。Dataset ID 与规范化路径全局唯一。已删除的
`task_paths` 字段不会自动迁移；加载时会明确报错，并给出替代格式示例。挂载修改只写入
workspace `peval-py.toml`。

数据集页面可以新建
包含 `dataset.toml` 与 `README.md` 的 Dataset、注册已有 Dataset、修改 ID/路径，以及
只解除注册而不删除文件。注册和普通浏览不会解析或校验 `dataset.toml`，因此 manifest
缺失或无效不会隐藏 Dataset 或其中的 Task；仍被 mount 引用的 Dataset 不能解除注册。

工作台使用 Harbor 1.4 创建单步或多步 Task 脚手架，并复用可排序、筛选的共享表格：
每个 live Task 占一行，没有 Task 的 Dataset 保留一条空占位行。搜索会匹配 Dataset、
Task、package、状态和诊断字段，并保持第一条可见记录被选中。回收区是仅供
管理员使用的独立视图，不混入 live 总览。选中行后，下方显示文件树和纯文本编辑器。
文件通过按钮或 Ctrl/Cmd+S 显式保存，切换页面、行或文件前会保护未保存内容。
无效编辑保留为带 Harbor 精确诊断的 Draft，并从实时 Task evidence 中排除。文本编辑上限
为 2 MiB、Base64 上传为 16 MiB、下载为 20 MiB；链接、特殊文件、路径穿越和保留控制
路径均会被拒绝。删除 Task 会把整个目录移到 Dataset 内的回收区，可恢复或永久清空；
单个文件删除是永久操作。

普通 Dataset 和 Task 操作不会解析或改写 `dataset.toml`。只有显式同步 manifest 才会
校验它，再使用 Harbor digest 添加或更新有效 Task，并移除已回收 Task 的引用。每次写入
都携带 revision；浏览器状态过期或外部并发修改会返回 `409`，不会覆盖。Task 磁盘变化
会触发一个后台 catalog reconcile，工作台持续显示进度和失败；仅同步 manifest 不刷新
Trial。

报告页面展示导入报告列表，并为管理员提供 session 关联管理。加载后默认选中第一份
报告，原有可调整宽度的 Report Reader 和新标签页预览行为保持不变。

来源引用固定为 `harbor/<mount-id>/<job-name>/<trial-name>`。Reload 直接从
Harbor 当前文件读取 trajectory、config、lock、result、reward 和运行状态，不会在
workspace 中复制这些内容。多步 Trial 显示 unsupported；无效 Trial 只显示当前错误，
不会回退到 last-good trajectory。已删除且没有用户 overlay 或 report binding 的 Trial
会直接消失；有引用的 Trial 保留 missing 行，并在相同 source reference 恢复后自动重连。

对每条可读 Trial，工作台会把 Task、Job、Trial、provider、完整 reward dimensions、
阶段 timing、Harbor 版本、result/regrade 标识和历史 Task provenance 投影到 catalog
与报告。Task identity 按 result、lock、config 顺序解析。Provider 只接受 Harbor 的
显式记录或明确的 `provider/model` 模型格式；不会从 agent 名或无前缀模型名猜测。

Task metadata 只会从 mount 注册的 `dataset_ids` 解析：优先匹配 lock/config 中的 Task path，
否则用完整 Task name 匹配 Harbor 校验有效的 Dataset 直接子目录；Draft 会被排除。缺失或多解只产生诊断，不会隐藏
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

对于可读的已挂载 Trial，工作台还会只读查找
`artifacts/logs/**/analysis.md`：标准路径 `artifacts/logs/analysis.md` 优先，
否则使用相对路径字典序中的第一个嵌套匹配。选中的 UTF-8 普通文件最大为 20 MiB。
Selected Trial 的 Analysis 会先显示这份 Harbor 文档，再显示 workspace
`analysis.md` overlay，并以来源标题分成两个区块。缺失、空白、无效或超限文档只隐藏
自身区块；Reload 与 Refresh 能发现文件新增、修改、删除和候选切换，但不会复制或
修改 Harbor 文件。

Leaderboard 将 Job 放在紧凑的 Task / 别名列之前，并将 canonical Session ID 保留为
最后一个数据列。没有自定义 alias 时显示 Task name；存在 alias 时以 alias 为主，同时
保留 Task 作为次级证据。
Tags 合并只读 Task keywords 与可编辑 custom tags，保持顺序并按大小写不敏感去重；
清空 alias 或 tags 后恢复 Task 派生显示。Job、Provider、Reward 可筛选；Task、Job、
Provider、Reward 可排序；Saved Views 与 Summary 可按 Task、Job、Provider 分组。
多维 reward 始终保持独立，只有 `reward` 维度或唯一维度会进入数值分布。

`#Analysis` 显示每条 Trial 的分析来源数量。Harbor 分析计 1，workspace overlay
无论包含 `analysis.json`、`analysis.md` 还是两者都只计 1，因此挂载的 Harbor Trial
取值为 0–2，其他来源为 0–1。

Columns 控件可以隐藏或调整所有数据列；即使数据列全部隐藏，行选择列仍固定保留。

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

Summary XLSX 的分布仍以当前页为范围，同时附带不受分页影响的完整当前 query 推理概览。

Serve 菜单只包含 Table、JSON Report 和 Workspace snapshot，不存在旧 HTML Report。
Snapshot HTML 是独立的自包含 workspace 导出。

同步单 source mutation 返回紧凑的 generation/change 数据。批量 reload、state 和
delete 返回 queued status 并由客户端轮询；两类响应都不嵌入完整 report。
