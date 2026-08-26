# 报告

[English](../../../../user/peval/reports.md)

可用 `--steps`、`--tool-call` 或 `--source` 缩小证据范围；需要完整 JSON
报告时使用 `-m raw`，需要浏览器展示时使用 `peval serve`。

```console
peval view tr -m raw \
  -d ~/.psychevo/state.db \
  -s <session-a> -s <session-b> \
  -n 0="报告上下文" \
  --source-alias 2="候选版本" -o
```

编号 `0` 的 note 属于整份报告，正整数按展开后的会话顺序对应各行。Alias 只改变展示，不改变证据身份。

只有在输出位置与读者均可信时才使用 `--no-redact`。输出行为由
[CLI reference](../../../../reference/cli.md) 负责；证据与展示的分界由
[state and data reference](../../../../reference/state-and-data.md) 负责。
