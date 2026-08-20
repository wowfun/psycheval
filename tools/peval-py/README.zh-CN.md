# peval-py

语言：简体中文 | [English](README.md)

`peval-py` 是 `peval` 的轻量 Python 版本，用于查看已保留的 agent
轨迹。它读取 JSONL session 或 adapter 拥有的 SQLite database，并输出 ATIF JSON
或静态 peval 风格报告。

## 从 Checkout 安装

用 `uv` 安装本地 Python 工具：

```bash
uv tool install --editable ./tools/peval-py
```

之后可以直接使用短命令：

```bash
peval-py --help
peval-py view tr --help
```

CLI 使用纯文本帮助，并在根命令提供 Typer 的 shell 补全配置入口。可以先查看
补全脚本，再显式安装；普通命令不会修改 shell 配置：

```bash
peval-py --show-completion
peval-py --install-completion
```

也可以不安装，直接从源码树运行：

```bash
uv run --project tools/peval-py peval-py --help
```

## 构建本地二进制

`peval-py` 使用 `pandas` 为 inspect 模式提供表格化分析；`uv` 会根据
`tools/peval-py/pyproject.toml` 安装该运行时依赖。请在目标操作系统和 CPU 架构上构建。生成物建议放在
`.local/` 下，仓库会忽略这个目录。

PyInstaller 是最简单的单文件打包方式：

```bash
cd /path/to/psycheval

uv run --project tools/peval-py --with pyinstaller pyinstaller \
  --onefile \
  --name peval-py \
  --paths tools/peval-py/src \
  --distpath .local/peval-py-build/dist \
  --workpath .local/peval-py-build/work \
  --specpath .local/peval-py-build/spec \
  tools/peval-py/src/peval_py/cli/__main__.py
```

运行打包后的命令，并用 fixture 生成一份报告做检查：

```bash
.local/peval-py-build/dist/peval-py --help

.local/peval-py-build/dist/peval-py view tr \
  -m raw \
  -a opencode \
  -p tools/peval-py/tests/fixtures/common_session.jsonl \
  -o .local/peval-py-build/report.json

python3 -m json.tool .local/peval-py-build/report.json >/dev/null
```

Nuitka 也是一种选择，适合想做 compiled-Python 构建并且本机有 C 编译器的场景。
选择前建议在目标平台上比较输出大小和启动表现。

## 使用指南

用 `-a ADAPTER` 为所有输入设置默认 adapter。生成对比报告时，可以重复传入
`-a pN=ADAPTER` 或 `-a dN=ADAPTER`，让单个 path 或 DB 输入使用不同 adapter。

`view tr` 默认使用 bounded inspect 模式，适合先探索大文件：

```bash
peval-py view tr -a opencode -p session.jsonl
```

Inspect 输出是固定的紧凑 JSON digest，包含 session 身份、token totals、秒级
active duration、step/tool duration distributions、最耗时或 token-heavy 的行，以及
可用的 tool errors。`--head` 和 `--tail` 默认都是 2，`--top` 默认是 5；
`--steps <ids>` 会加入指定 step 证据，并支持 `1,3:5` 这样的逗号和 range
selector；`--tool-call <tool_call_id>` 可独立显示对应 tool call 及其匹配的 tool
result。`--max-content-chars` 会限制 inspect preview 文本长度。裸 `-o` 会写入
带时间戳的报告文件，并在 stdout 打印保存路径。

需要完整 peval JSON 或 HTML report 时使用 `-m raw`：

```bash
peval-py view tr -m raw -a opencode -p session.jsonl -f html -o report.html
```

Raw report 模式还接受 `--agent-name`、`--agent-version`、`--model` 和
`--no-redact` 这类转换/展示覆盖；默认 inspect 模式会拒绝这些 flags。

adapter TOML 表可以设置 `default_db_path`；相对路径按定义该值的 TOML 文件解析。
使用 `-d @adapter` 可以展开这个默认 DB 路径，并把该 DB 输入绑定到同一个 adapter。

当需要从 workspace 外读取已有 peval-py workspace 的 `peval-py.toml` 时，可以在
`view tr` 或 `export tr` 中使用 `-r, --root DIR`。这会选择 workspace 配置，例如
locale、可选的 Markdown `description`、`analysis_eval_slug`、adapter defaults 和
`default_db_path`；不会初始化或
修改 workspace。如果该目录还没有 `peval-py.toml`，请先运行 `peval-py init -r DIR`。

```toml
description = "**夜间评测**工作台 — 发布候选检查"
```

`serve` 会在工作台顶部中央为访客和管理员显示非空说明，并转义原始 HTML；
Workspace snapshot 导出也会保留这段 Markdown 内容。

```bash
peval-py view tr -r .local/peval-py -d @opencode --list
peval-py export tr -r .local/peval-py -d @opencode -s <session-id> -o
```

### 在受信局域网共享评测工作台

`serve` 提供匿名访客和登录后的管理员两种角色。localhost 未配置密码时直接以
管理员权限打开。要监听其他网卡，需先在进程环境变量或 `<workspace>/.env` 中设置
非空管理员密码，然后重启服务：

```bash
cat >.local/peval-py/.env <<'EOF'
PEVAL_PY_ADMIN_PASSWORD='请替换为足够长的随机密码'
EOF
chmod 600 .local/peval-py/.env

peval-py serve --root .local/peval-py --host 0.0.0.0
```

进程环境变量优先于 `.env`；空进程变量会回退到文件值。peval-py 只读取这个键，
不会创建或修改 `.env`。管理员 session 仅保存在进程内存中，空闲 12 小时后过期。
在多用户 POSIX 主机上，应确保 `.env` 仅 workspace 所有者可读。
访客可以浏览完整评测内容、Saved Views 和已导入报告，也可以使用全部只读导出；
source path、诊断、刷新、配置和 workspace 编辑仅对管理员开放。

访客还可以把当前 Catalog 条件保存为浏览器本地 Saved View。本地视图按站点和
workspace 隔离，登录或退出后仍会保留，并可参与组合筛选、摘要和导出，但不会上传。
管理员保存时可选择“工作区”（默认）或“此浏览器”。两处出现完全同名视图时优先显示
工作区视图，本地副本仍保留，名称冲突消失后会重新出现。

非本机监听使用直接 HTTP，只适合受信私有网络；不要直接暴露到公网。

使用 `--source-alias N=TEXT` 可以给来源添加仅用于显示的名称。Alias 只提升报告
可读性，不改变 session id、trial key、source identity 或 Evidence/Input Source 路径。
在 Leaderboard 中，canonical Session 列保持不变。Harbor 行使用独立的 Task / 别名列；
没有自定义 alias 时回退到 Task name，存在 alias 时仍在次级信息中保留 Task。

在对比报告中，Leaderboard 的 Duration 列和 JSON `duration_ms` 字段表示 active
agent/tool work time。已保留 session 中较长的空闲间隔会单独保存在
`wall_duration_ms` 字段中。Leaderboard 和 `serve` Source Manager 也会显示来自
`trajectory_meta.finished_at_ms` 的 Last Turn End。

当通过 `view tr -r <workspace>` 选择 workspace root，或从当前目录向上发现
workspace 时，报告还会尝试读取 peval cell cached analysis：
`runs/<analysis_eval_slug>/<agent-id>/<session-id>/<cell_key>/analysis.json`
和 `analysis.md`。默认 slug 是 `default`；匹配到的 summary 和 Markdown report 会
显示在 selected Trial 的 Analysis section，并写入 JSON `annotations.analysis[]`。

同一个 task 目录树也可以提供 manual Trial notes：
`runs/<analysis_eval_slug>/<agent-id>/<session-id>/<cell_key>/notes.md`。这些内容会写入
JSON `annotations.notes[]`，并排在 CLI notes 前面。在 `peval-py serve` 中，
本地 Trial artifact 使用这个 cell-local `notes.md`；Harbor source 则使用 workspace
中的 `harbor/<mount-id>/<job>/<trial>/notes.md`；不可变的本地 snapshot artifact 保持只读。
Serve 展示 snapshot 或已挂载 Harbor Trial 时，会在 active report 组合阶段叠加当前 workspace 里的
`analysis.json`、`analysis.md` 和 `notes.md`；因此 reload 或 Refresh 即使遇到原始
source DB/file 无法成功刷新，也能显示 notes/analysis 的更新。
已挂载 Harbor Trial 的只读 `artifacts/logs/**/analysis.md` 也会显示在 Selected Trial
的 Analysis 中：标准路径 `artifacts/logs/analysis.md` 优先，否则选择相对路径字典序
中的第一个嵌套匹配，文件上限为 20 MiB。当 workspace overlay 同时存在
`analysis.md` 时，Harbor 文档排在前面；缺失、空白或无效文档只隐藏自身带来源标题
的区块。
Leaderboard 的 `#Analysis` 列按来源计数：Harbor 分析计 1，workspace overlay
无论包含 JSON、Markdown 还是两者都只计 1，最大值为 2。

`peval-py serve` 保持静态报告继续使用 CDN，但在 serve 页面中会优先从
`<workspace>/.cache/echarts/6.0.0/echarts.min.js` 提供 ECharts，本地脚本失败时
回退到固定 CDN URL。Source Manager 会在 SQLite DB 表单内提供默认 DB 的保存/清除
操作，并提供 source alias 编辑、Last Turn End 排序和 English/简体中文选择器；语言选择
会把顶层 `locale` 持久化到 `peval-py.toml`。Harbor 区域可以按稳定 ID 添加、编辑和移除
只读挂载，并配置一个 Jobs root 与可选的 Task/Dataset 路径。Path 来源字段也可以输入
另一个 workspace root、
`runs/`、`runs/<analysis_eval_slug>`，或 Trial cell 上层目录；serve 会递归导入完整
cell 到当前 workspace 作为 snapshot，并保持外部 workspace 不变。

白名单 Harbor Task 的 live keywords 会进入 display tags。Leaderboard、Saved Views、
Summary、Selected Trial evidence、JSON/snapshot report、inspect 与 XLSX 也会同步展示或
导出 Task、Job、Trial、provider、reward dimensions、timing 与 provenance。Live Task
metadata 与历史 Trial lock 的 digest 不一致时仍可使用，并会明确标记。Package 或 Git
artifact ref 仍保留在 provenance 中，但不会与本地 live Task digest 比较。

`peval-py serve` 也可以把已有的 Markdown 或 HTML 分析报告绑定到一个或多个
session。先勾选 Leaderboard 中当前可见的行，再点击 `Attach report (N)`，并选择一个
本地 `.md`、`.markdown`、`.html` 或 `.htm` 文件。Reports 列会在左侧的沙箱预览器中
打开已绑定的报告。工具栏中的 Reports Manager 可以预览导入的报告、替换它们与
active 或 archived 可读 session 的绑定，或永久删除报告。这个工作流只在 serve
页面中提供，不会修改导出的 report JSON 或静态 HTML 报告。

每个导入的报告都会复制到 `<workspace>/reports/<id>/`。其中的 `state.json` 只包含
逻辑 source reference：

```json
{
  "source_refs": [
    "runs/default/agent-a/c2/c2_t001"
  ]
}
```

reference 也可以是 `harbor/<mount-id>/<job>/<trial>`。你可以直接编辑这些绑定。
找不到某个 source 时，serve 会保留关联且不会改写 `state.json`；相同的 source
reference 恢复可读后，关联也会恢复。每次只能导入一个不超过
20 MiB 的 UTF-8 文件，并且只复制所选文件。报告引用的相对 sibling 图片、样式、
脚本或其他资源不会随报告导入；需要时请把资源嵌入报告，或使用外部 URL。

报告生成、session 对比和自定义 adapter 示例见
[peval-py 文档](../../docs/i18n/zh-CN/peval-py/README.md)。
