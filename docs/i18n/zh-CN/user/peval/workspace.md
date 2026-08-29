# 工作区

[English](../../../../user/peval/workspace.md)

初始化并启动工作区：

```console
peval init -r .local/evaluation
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
**恢复默认**会移除该覆盖。Dataset ID 与路径可直接在注册表格中编辑。注册已有 Dataset 时
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

## Psycheval Copilot

在配置页按上例把 OpenCode 等 Agent 加入白名单后，点击管理员页头中的
**Copilot**。连接 Agent，并使用 `pretty-aui` 的会话控件新建、选择或关闭对话。
通过输入框上方的**添加上下文**可以同时附加多个来源、Task 或报告：先选择评测
对象再添加，重复以上操作；使用各 chip 上有明确名称的关闭按钮可逐项移除。
重复添加同一引用不会产生副本。切换工作台页面时抽屉保持打开；请使用关闭按钮、
背景或 Escape 显式关闭。页面选择变化不会静默修改已附加引用。每次发送 Prompt
时都会按可见 chip 顺序重新解析所有引用，因此 Agent 会收到当前且有大小限制的内容。
未配置 Agent 时，连接控件会直接跳转到**配置**页中的 ACP Agent 表单。
输入区可以载入任一已配置的 Markdown 提示词资产；添加来源、Task 或报告时只会
选中对应的建议资产，不会自动发送。

请先在 Psycheval 外部配置 Agent。以 OpenCode 为例，Provider 需要认证时，应在
终端运行 `opencode auth login`。面板会展示消息、计划、工具进度、权限和信息请求、
模式、配置、用量以及 Agent 持有的会话历史；不同会话可以并行工作，同一会话只
接受一个活动 Prompt。断开连接或关闭 `peval serve` 会终止网关子进程。对话只
保留在 Agent 状态中，不会导入为评测证据。

ACP Agent 会继承 serve 进程的环境变量与操作系统权限。请只配置可信可执行文件，
也不要把抽屉中的权限卡片当作文件系统或进程沙箱。完整访问和持久化规则见
[workspace reference](../../../../reference/workspace.md)。

## Serve 访问

绑定非本地地址前，遵循
[workspace reference](../../../../reference/workspace.md) 中的访问规则。

将分析报告导入指定 source reference：

```console
peval import analysis -r .local/evaluation \
  --source-ref runs/default/psychevo/<session>/<cell> \
  -p analysis.json -p analysis.md
```
