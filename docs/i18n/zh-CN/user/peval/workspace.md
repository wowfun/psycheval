# 工作区

[English](../../../../user/peval/workspace.md)

初始化并启动工作区：

```console
peval init -r .local/evaluation
peval init -r .local/evaluation --skill skills/peval
peval serve -r .local/evaluation
```

工作区发现与初始化语义由
[workspace reference](../../../../reference/workspace.md) 负责。

## 统一配置

同一份文件可以配置 Psycheval CLI 与 Harbor host execution：

```toml
description = "Nightly evaluation workspace"

[adapters.psychevo]
default_db_path = "~/.psychevo/state.db"

[harbor.host]
workdir_root = "../workspaces"

[[harbor.datasets]]
id = "pbench"
path = "../datasets/pbench-v1.0"

[[harbor.mounts]]
id = "nightly"
path = "../jobs"
dataset_ids = ["pbench"]

[[acp.agents]]
id = "opencode"
title = "OpenCode"
command = "opencode"
args = ["acp"]
```

使用 `-r`/`--root` 选择工作区。未指定时，`peval` 会从当前目录及其父目录
（或 `PEVAL_ROOT`）发现 `peval.toml`。该文件会经过严格校验，因此应删除
已废弃或拼写错误的字段，而不是依赖它们被忽略。

配置所有权与路径语义由
[workspace reference](../../../../reference/workspace.md) 负责。

仅管理员可访问的**配置**页（`/config`）统一管理轨迹接入、ACP Agent、提示词
资产、Dataset 注册与 Harbor 挂载。点击**添加 ACP Agent**会打开预填 OpenCode
模板的表单面板；已有配置仍可直接编辑可执行文件与参数数组。保存后立即生效，
修改或移除已连接的 Agent 会停止对应进程。仓库 Markdown 文件提供
默认提示词；在配置页编辑后，会在工作区 `prompts/` 目录写入同名覆盖文件；点击
**恢复默认**会移除该覆盖。四份英文提示词及其四份简体中文版是彼此独立的资产，
每一份都能单独自定义或恢复，不会连带修改对应译文。Dataset ID 与路径可直接在注册表格中编辑。注册已有 Dataset 时
只需输入路径，添加 Jobs 挂载时也只需输入 Jobs 路径。目录 basename 合法且未
占用时会直接作为 ID；basename 非法或已冲突时则生成带随机字符串的 path-safe
ID。新挂载默认不关联 Dataset。两个注册区都使用可编辑表格：双击挂载 ID、
Jobs 路径或有序 Datasets 单元格即可编辑，也可编辑 Dataset 的 Harbor 挂载列
调整关联。关联编辑器只补全并接受已注册 ID；从 Dataset 表格新增关联时，该
Dataset 会追加到相应挂载的 evidence 查找顺序末尾。所选挂载可原子移除且不会
删除 Jobs 文件。解除注册同样不会删除 Dataset 文件；如果仍有挂载引用该
Dataset，操作会被拒绝。手写 `peval.toml` 时仍需显式填写 ID。

**数据集**页只管理 Task。双击 Task 单元格可重命名，勾选多行可归档、恢复或
永久删除；只有明确点击**同步 manifest** 时才会更新 `dataset.toml`。
**Leaderboard** 负责对应的轨迹生命周期，包括已归档视图与来源永久删除。

主页、数据集、报告和配置共享同一个持久浏览器文档。直接 URL 仍会打开指定
页面，而站内导航及浏览器前进/后退会在不重新加载文档的情况下切换页面。
访问过的页面会保留选择、滚动位置，以及未保存的 Dataset 文件或 Report 绑定
草稿。外部文件系统发生变化时，请使用各页面的重新加载或重新扫描操作；在其他
页面完成的相关变更会让旧页面失效，并在下次进入时刷新。重新加载或关闭浏览器
前，系统仍会对未保存草稿给出警告。

**报告**页会将规范评测报告与导入的报告包分开管理。**评测报告**是只读的目录
投影，提供**预览**、**打开**和**查看来源**操作。系统会从当前来源的
`analysis.md` 读取报告，不会将正文复制到 `reports/`。**导入报告**保留面向
管理员的报告绑定与删除操作。访客可以通过同一个有大小限制的渲染器预览两类
报告，但不会获得来源路径或修订元数据。

## Psycheval Copilot

在配置页按上例把 OpenCode 等 Agent 加入白名单后，点击管理员页头中的
**Copilot**。连接 Agent，并使用 `pretty-aui` 的会话控件新建、选择或关闭对话。
在输入区选择模型后，新对话会继承当前模型；同一工作区和 Agent 的偏好在页面
刷新后仍会保留。打开已有对话时，仍使用 Agent 为该对话保存的模型。
每个新对话都会以 Agent 的 `plan` 模式启动，打开已有对话时则保留其 Agent 管理的模式。
通过输入框上方的**添加上下文**可以同时附加多个来源、Task 或报告：先选择评测
对象再添加，重复以上操作；使用各 chip 上有明确名称的关闭按钮可逐项移除。
重复添加同一引用不会产生副本。切换工作台页面时抽屉保持打开；请使用关闭按钮、
背景或 Escape 显式关闭。页面选择变化不会静默修改已附加引用。每次发送 Prompt
时都会按可见 chip 顺序重新解析所有引用，因此 Agent 会收到当前且有大小限制的内容。
来源上下文还会包含当前规范报告的有界正文（如果存在）。该报告只是分析材料，
不构成发布保护条件。任何回合进入终止状态后，包括已取消的回合，工作区都会刷新
目录，因为 Agent 工具可能已经提交了报告。

连接成功、附加上下文、重复附加、移除及相关错误会按发生顺序显示为所属会话转录中的
低权重文本行。这些行只存在于当前浏览器 controller 中，不会发送给 Agent，也不会从
会话历史恢复。聊天尚不可用时发生的错误会显示在空聊天占位区；连接进度和正常断开不会
新增通知行。

在实时对话中，转录会把每个已提交项目显示为**上下文注入**活动，而用户气泡及其
复制操作只保留原始 Prompt。客户端会在模型侧为该 Prompt 加上明确边界，因此重新
打开由当前客户端写入的对话时，即使 Agent 已把上下文和 Prompt 展平为纯文本，也能
恢复用户原文。恢复历史还会尽力从 Prompt 前缀重建**上下文注入**活动：保留下来的
元数据可恢复独立项目，已展平的内容则显示为一条恢复项目。这些历史记录不会重新成为
工作台中的实时引用。采用该边界格式之前创建的对话会严格按 Agent 回放内容显示，因为
无法安全区分其中的上下文和用户输入。

未配置 Agent 时，连接控件会直接跳转到**配置**页中的 ACP Agent 表单。
输入区可以载入任一已配置的 Markdown 提示词资产。附加上下文不会填写或发送
消息，附加来源也不会选择故障诊断提示词。只有用户输入非空白消息后，发送按钮才
可用。八个语言版本始终都可选择。中文页面首次打开时默认使用中文版评测复盘，
并按上下文推荐中文提示词；其他语言页面使用英文版本。只要已保存的选择仍然有效，
就始终优先保留该选择，不会按页面语言替换。

请先在 Psycheval 外部配置 Agent。以 OpenCode 为例，Provider 需要认证时，应在
终端运行 `opencode auth login`。面板会展示消息、计划、工具进度、权限和信息请求、
模式、配置、用量以及 Agent 持有的会话历史；不同会话可以并行工作，同一会话只
接受一个活动 Prompt。断开连接或关闭 `peval serve` 会终止网关子进程。对话只
保留在 Agent 状态中，不会导入为评测证据。

展开工具行可以检查结构化结果。可识别的 Execute、Read 和文件变更调用会分别
显示为终端、源码和 Diff 卡片；其他调用仍保留独立的输入与输出区域。较长的源码
和 Diff 正文会先保留头尾，展开后显示全部内容。每个可用的**复制**操作只复制该
区域的语义正文，例如原始命令输出或文件文本，不包含卡片标签、行号 gutter 或命令
展示信息。

ACP Agent 会继承 serve 进程的环境变量与操作系统权限。请只配置可信可执行文件，
也不要把抽屉中的权限卡片当作文件系统或进程沙箱。完整访问和持久化规则见
[workspace reference](../../../../reference/workspace.md)。

## 自由评测报告

在 Psycheval checkout 根目录中，通过 `peval init -r .local/evaluation
--skill skills/peval` 显式安装仓库 Skill。该参数会完整替换工作区中的同名副本；
普通 `peval init` 不会安装 Skill。安装或替换后，请新建一个 Copilot 会话，附加
Harbor Trial 或导入的本地会话。输入非空白的评测要求，并在消息或附加上下文中
提供有用依据，例如 Task、报告、分析时读取的 Task 上下文或 Skill 路径。
Psycheval 不会发现、校验这些材料，也不会判定其评测权威性。一个回合包含多个
来源且发布目标不明确时，Skill 会先询问目标来源。批量评测需要逐份审阅和发布。

Skill 会在 plan 模式下生成标准 Markdown 报告草稿。模板包含评测要求与所提供的
依据、结论摘要、评测问题与覆盖范围、发现、已观察到的优点、改进建议、指标，
以及局限性与置信度。报告会区分保留的 Trial 证据、分析时读取的实时上下文、用户
提供的材料和分析推断，不会声称实时内容等同于 Trial 运行时状态。

每次修改后都应重新审阅完整草稿。发布前，请手动切换到 execute/build 模式，并
明确确认当前草稿。这项审阅由 Skill 工作流保证，不是服务端审批凭据。发布器会
原样保存已审阅的 Markdown：

```console
peval publish evaluation-report -r .local/evaluation \
  --source-ref <ref> -p <approved-draft.md>
```

Harbor parent Trial 与 MultiStep 阶段引用共用 parent Trial 的 `analysis.md`；
导入的本地会话使用对应 cell 的 `analysis.md`。发布不使用修订标识，也没有单独的
替换参数。已有报告会由本次已确认的发布原子替换；并发发布会串行完成，最后完成的
写入生效。目录刷新后，主页 Trial 详情与只读的**评测报告**列表都会读取这份规范
文件。

## Serve 访问

绑定非本地地址前，遵循
[workspace reference](../../../../reference/workspace.md) 中的访问规则。

将分析报告导入指定的本地 Trial-cell source reference：

```console
peval import analysis -r .local/evaluation \
  --source-ref runs/default/psychevo/<session>/<cell> \
  -p analysis.json -p analysis.md
```
