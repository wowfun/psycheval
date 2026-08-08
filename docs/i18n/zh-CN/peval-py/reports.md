# 报告

## 对比 Session

`view tr` 默认输出有界的 inspect digest；完整 JSON 或 HTML 报告必须加
`-m raw`。Raw mode 接受重复的 path、DB 和 session 输入；每个展开后的 session
成为一行，拥有稳定 source key 和一个可选择的 Trial。

```bash
peval-py view tr -m raw \
  -d ~/.psychevo/state.db \
  -s <session-a> -s <session-b> \
  -n 0="报告背景" \
  -n 2="Session B 备注" \
  --source-alias 2="Candidate" \
  -o
```

备注索引 `0` 属于报告；正数按展开后的 session 顺序对应。别名只影响显示，不会
改变 session、trajectory、Trial、source 或 evidence identity。

静态报告在 0 行时没有 comparison；1 行显示 Leaderboard 和 Overview，但不显示
Summary；从 2 行开始显示 Summary。

## 输出与脱敏

未指定 `--format` 时由后缀选择 JSON 或自包含 HTML。裸 `-o` 使用派生文件名。
`export tr` 只接受一个 session；重复输入用于 `view tr`。

默认脱敏明显的 secret key、Authorization header、Bearer token 和常见 token
赋值文本；`--no-redact` 会显式关闭保护。数字形式的 usage/accounting 总量仍保留。
`--max-content-chars` 可限制超大 message 和 tool payload。

没有匹配 tool call 的结果仍作为独立 observation step 显示，并生成转换 warning。
报告将 matching observation 放回发起调用的 Agent step；失败调用不会被隐藏。

源数据没有逐 step token 时，HTML 可显示带 `≈` 的视觉估算；时间填充同样只是
视觉提示。两者都不会写入 ATIF 或报告 JSON。

## Cached Analysis 与 Cell Notes

选择 workspace root 后，peval-py 从精确 Trial cell 只读加载：

```text
runs/<eval>/<agent>/<session>/<cell>/analysis.json
runs/<eval>/<agent>/<session>/<cell>/analysis.md
runs/<eval>/<agent>/<session>/<cell>/notes.md
```

匹配 analysis 写入 `annotations.analysis`；cell notes 以 `source = "cell"`
写入 `annotations.notes`。缺失或格式错误的可选 analysis 会被忽略。session 根级
analysis/notes 保留，不投影到 Trial 报告。

## 本地化

在配置或 workspace `peval-py.toml` 中设置 `locale = "zh-CN"`。`zh` 是
`zh-CN` 的别名，`en-US` 归一为 `en`。Serve 的中英文选择器会持久化 workspace
locale；静态报告使用生成时配置。
