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

## 通过 Harbor 运行 WorkBuddy

符合 WorkBuddy verifier 契约的 Harbor Task 均可在兼容环境中运行。按
[运行时安装说明](../../../../user/downstream-vendoring.md#install-the-workbuddy-runtime)
安装固定版本，并准备 Task 和 Agent 的依赖。执行不要求先注册 Psycheval Dataset。

下面的 Python 工作流使用已安装的 OpenCode CLI 和可信本机 Host。
将任务集合路径和模型名称替换为实际值：

```python
import subprocess
from pathlib import Path

import yaml
from harbor.models.job.config import DatasetConfig, JobConfig
from harbor.models.trial.config import AgentConfig, EnvironmentConfig
from psycheval.harbor.workbuddy import compute_official_metrics, prepare_workbuddy_job

base = JobConfig(
    datasets=[DatasetConfig(path=Path("path/to/tasks").resolve())],
    agents=[
        AgentConfig(
            import_path="psycheval.harbor.opencode:HostOpenCodeAgent",
            model_name="provider/model",
        )
    ],
    environment=EnvironmentConfig(
        import_path="psycheval.harbor.environment:HostEnvironment",
        kwargs={"host_access": {"filesystem": True, "process": True}},
    ),
)
config = prepare_workbuddy_job(base)
yaml_path = Path("job.yaml")
yaml_path.write_text(yaml.safe_dump(config.model_dump(mode="json")), encoding="utf-8")
subprocess.run(["harbor", "run", "-c", str(yaml_path)], check=True)
job_dir = config.jobs_dir / config.job_name
print(compute_official_metrics(job_dir))
```

Harbor 默认运行一次，超时倍率为 1.0，结果保存到 `./jobs/<job_name>`。
需要复现对应的 WorkBuddy 基准配置时，在准备前设置 `base.n_attempts = 3`
和 `base.timeout_multiplier = 2.0`。Host 工作区默认为 `~/workspaces`。
准备函数返回独立模型，不写文件；示例中的 YAML 导出与运行由应用负责。

单题使用 `JobConfig.tasks`；子集使用 Harbor 的 `DatasetConfig.task_names`、
`exclude_task_names` 和 `n_tasks`。Skills 与 MCP 通过原生 Task/Agent 字段声明，
任务名称不会触发特殊配置。指标函数从留存的 Job lock 获取选中任务分母，包含
缺失结果，并按需返回当前快照。

浏览结果时，在 **Configuration** 注册 Dataset，并将 `config.jobs_dir` 添加为
关联该 Dataset 的 Jobs 挂载。WorkBuddy 注册使用 `format = "workbuddy.v1"`；
裁剪后的 bundle 少于 manifest 声明的题数时，设置 `allow_partial = true`。
参见[工作区操作](workspace.md)。Trial 详情直接读取权威 verifier 分数和 Harbor
reward，不另存 WorkBuddy summary。

Host 采用可信本机执行。评分材料暂存在 Agent 工作区外，自动生成的路径采用
中性名称，尽力减少评测线索。它不复现容器构建，也不隔离访问权限。Task 仍须
满足自身的平台和依赖要求；已识别的 Windows Python/pytest 格式提供无 Bash
适配，参见[Windows 工作流](../../../../user/downstream-vendoring.md#run-on-native-windows)。
精确语义由 [Harbor 契约](../../../../reference/harbor.md#workbuddy-tasks) 负责。

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
