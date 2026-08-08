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

Serve 还会关联 workspace root 本身或惯例 `jobs/` 目录下的单步 Harbor Trial。
只要 `agent/trajectory.json` 可读，Trial 就会显示；Reload 会投影后续 trajectory
和 `result.json` 变化，但不会修改 Harbor 文件。如需关联外部 Trial、Job 或 jobs
root，可在 `peval-py.toml` 中配置相对路径：

```toml
[harbor]
roots = ["../harbor/jobs"]
```

多步 Trial 会显示 unsupported 诊断。关联来源无效或消失时，工作台保留最后一个
有效投影和 workspace annotation。

Path、DB 和 input-table 的 `auto` 要求唯一推断。JSONL upload 回退到 workspace
配置；ATIF/report upload 不需要 adapter。浏览器新增表单有意不展示 alias；CLI、
manifest、JSON interface 和已保存行的内联编辑支持 alias。

Archive/delete 只修改 workspace state，不删除原始文件或数据库。关联的 Harbor
Trial 不能删除，应使用 Archive 隐藏。可刷新 source 能够更新 cell-local
`notes.md`；上传的 snapshot 保持只读。

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
