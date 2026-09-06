# 输入与 Adapter

[English](../../../../user/peval/inputs-and-adapters.md)

## 文件与 ATIF

JSONL 每行包含一个 JSON 对象。每行可以是直接消息，也可以是带有
message、usage、metadata、accounting 和会话顺序的包装对象。CLI 还可读取
严格校验的 ATIF JSON、受支持的 Adapter JSON、Trial cell 及其中的轨迹工件。

## Harbor Trial 目录

传入 Harbor Trial 根目录，可在轨迹之外保留评测结果与 provenance：

```console
peval view tr -p <harbor-trial-dir>
```

该输入不需要 Adapter selector。MultiStepTrial 根目录会按 result 中的顺序，
为每个 Harbor step 生成一个 source。默认 inspect 可以表示尚无轨迹的失败或
运行中 step；完整报告要求选中的每个 source 都具有 ATIF 证据。直接传入
`agent/trajectory.json` 时只读取该 ATIF 文件，不推断其父 Trial。

管理员可在工作区详情中点击 **刷新来源**，重读已关联 Harbor Trial 的证据。
复制导入的快照不提供刷新操作。

## 通过 Harbor 运行 WorkBuddy Office

WorkBuddy Office v1.0 bundle 的 `tasks/` 已包含 50 个原生 Harbor Task 目录，
无需转换或复制。可在 **Configuration** 页面注册 bundle 根目录，也可在
`peval.toml` 中加入只读注册：

```toml
[[harbor.datasets]]
id = "workbuddy-office"
path = "/path/to/wb-bench-office-v1.0"
format = "workbuddy.v1"
```

注册裁剪包时，在该表中增加 `allow_partial = true`，并保留原 manifest、共享
verifier 和剩余 Task 的完整目录。默认注册仍要求声明的全部 Task 都存在。

在 Psycheval 所在环境中安装受支持的外部 `workbuddy-bench` 源码版本：

```console
uv pip install --no-deps \
  "workbuddy-bench @ git+https://github.com/Tencent/workbuddy-bench.git@625b2233093ae4f23e76be28c1f341d41cc70373"
```

`--no-deps` 会保留现有的 Harbor 0.21.0 依赖环境。下游项目的依赖声明和锁文件
配置见 [WorkBuddy 运行时安装说明](../../../../user/downstream-vendoring.md#install-the-workbuddy-runtime)。

然后创建仅含一个 Agent 的 Harbor Job 基础配置。下面的例子显式选择
Psycheval 的可信 Linux host environment，并使用 OpenCode：

```yaml
job_name: workbuddy-base
n_concurrent_trials: 1
agents:
  - name: opencode
    model_name: xiaomi-token-plan-cn/mimo-v2.5-pro
environment:
  import_path: psycheval.harbor.environment:HostEnvironment
  kwargs:
    allow_host_execution: true
```

生成相互隔离的两个 Job 配置，运行命令输出中的两个 Harbor 命令，并在两者
结束后计算官方聚合指标：

```console
peval harbor prepare -r .local/evaluation \
  --dataset workbuddy-office --config workbuddy-base.yaml
PEVAL_CONFIG=.local/evaluation/peval.toml harbor run -c <输出的-normal-config>
PEVAL_CONFIG=.local/evaluation/peval.toml harbor run -c <输出的-special-config>
peval harbor summarize -r .local/evaluation --plan <输出的-plan-id>
```

运行单题或子集时，在 prepare 后增加可重复的 `--task/-t`，或正整数
`--limit/-l`。选题使用精确的 Task 目录名，排序后再应用数量限制。运行返回的
全部配置，可能只有一个 Job。汇总会区分子集范围和未完成的 `--provisional` 状态。

Windows Host 会自动选用无需 Bash 的 Office verifier。Agent 或 harness 需要
支持 Windows，具体配置见 [原生 Windows 工作流](../../../../user/downstream-vendoring.md#run-on-native-windows)。
Windows 上的 CLI 会输出 PowerShell 运行命令。

Host execution 会展开每个 Task 的 workspace archive 并建立干净的 Git
baseline，但它不是 sandbox，也不能复现容器的资源和网络隔离。仅应在 Linux 或 Windows
上对可信 Task 使用；可运行 Docker 的 Harbor environment 仍是可移植路径。
特殊 recruiting Task 虽有已知的缺少输入、网络契约和 sanity-check 源数据
缺陷，选中时仍保留在分母中；prepare 会输出相应警告。**Datasets** 页面允许
浏览此注册，但不提供任何修改操作。Trial 详情以 `verifier/score.json` 作为
WorkBuddy 分数，单独保留 Harbor reward，并且只展示有界的 verifier 证据。
精确的 runtime、verifier LLM 与聚合契约见
[Harbor reference](../../../../reference/harbor.md)。

```console
peval export tr -a opencode -p session.jsonl -o
peval view tr -m raw -p trajectory-opencode-session.json -o
```

内置 Adapter 的选择语义由 [CLI reference](../../../../reference/cli.md) 负责。
使用 `-d @adapter` 展开已配置的默认数据库，并通过 `--list`、
`--list-interactive` 和可重复的 `-s` 选择会话：

```console
peval view tr -d @opencode --list
peval view tr -m raw -d @hermes -s '#2' -o
```

多个数据库可使用从一开始计数的 DB 编号绑定 Adapter 和 session ID：

```console
peval view tr -m raw \
  -d ~/.hermes/state.db \
  -d ~/.local/share/opencode/opencode.db \
  -a d1=hermes -a d2=opencode \
  -s d1=<hermes-id> -s d2=<opencode-id> -o
```

## Claude Code

指定 adapter 后可按 ID 导入，也可直接读取会话文件；两者都会包含明确关联的子 Agent：

```console
peval view tr -a claude -s <session-id>
peval export tr -a claude -s <session-id> -o
```

ID 默认从 `~/.claude/projects/` 查找。可在 `peval.toml` 中设置其他根目录，
相对路径以该配置文件所在目录为基准：

```toml
[adapters.claude]
default_session_root = "/path/to/claude/projects"
```

复制到该根目录之外的会话也可通过文件路径读取：

```console
peval view tr -a claude -p ~/.claude/projects/<project>/<session-id>.jsonl
```

列出项目的主会话，再按 ID 或列表序号选择：

```console
peval view tr -a claude -p ~/.claude/projects/<project> --list
peval view tr -a claude -p ~/.claude/projects/<project> -s '#1'
peval export tr -a claude -p ~/.claude/projects/<project> -s <session-id> -o
```

省略 `-s` 时选择最近活跃的会话。多个会话目录使用 `-s p1=<id>`、
`-s p2=<id>` 绑定选择；数据库继续使用 `dN`。
`--list-interactive` 提供终端交互选择。

在 **Configuration** 页的 **Session ID 或文件 / 目录路径** 输入框中，
每行填写一项；ID 与路径可以混合输入，每行分别报告导入结果。填写 ID 或
无法识别 adapter 的路径时，选择 **claude**。点击 **添加来源** 可直接导入。

需要选择会话时，填写一个 ID 或项目目录，点击 **检查会话**，再点击
**添加选中**。目录列出主会话，ID 则显示匹配的会话。已有路径优先按路径识别；
相对路径可加 `./` 前缀，即使不存在也会按路径处理。更改输入或 adapter
会清除之前的选择。列表会同时显示被排除文件的诊断。
会话表格显示 UTC 更新时间，便于识别最近活跃的会话。
一个主会话保持为一条评价来源；有子轨迹时，详情和侧栏显示树形导航，
支持主子轨迹切换，以及父工具结果与子轨迹之间的跳转。各轨迹展示自己的指标。
点击树形导航每行右侧的 **复制**，可复制该会话中 Agent 的最后一条 message。
每个 step 的 block 卡片右侧也提供 **复制**，用于复制该卡片的内容。
详情中的 **刷新来源** 会重读原生 Claude 来源的已选文件及其关联子会话，
导出则生成自包含的 ATIF 树。

目录与计量语义见 [CLI reference](../../../../reference/cli.md) 和
[轨迹契约](../../../../reference/state-and-data.md#trajectories-and-sidecars)。

## 自定义 Adapter

在提供 Adapter 的 distribution 的 `pyproject.toml` 中注册：

```toml
[project.entry-points."psycheval.adapters"]
custom = "custom_adapter:CustomAdapter"
```

Adapter 实现受支持的记录、路径或数据库转换方法；精确协议以源码和测试为准。
设置放在 `peval.toml` 的 `[adapters.<id>]` 下。
