---
name: x-daily
description: 从 Excel 中读取关注账号，通过 Nitter RSS 抓取滚动 24 小时内的 X posts，并输出规范化 JSON 快照。
---

# X Daily

本 skill 只负责确定性抓取和规范化，不生成最终 Markdown。

运行：

```bash
python /app/skills/x-daily/scripts/fetch.py \
  --users /app/input/x-users.xlsx \
  --output /app/.trend-digest/x.json
```

成功后读取 JSON 中的 `generated_at`、`window_start`、`window_end` 和按 Excel 顺序排列的 `accounts`。每个账号状态只能是：

- `success`：`posts` 非空；
- `no_updates`：RSS 抓取成功，但窗口内无 post；
- `fetch_failed`：所有配置的 Nitter 实例均失败。

至少一个账号成功抓取时命令退出 0。所有账号失败时仍会写快照，但命令退出非零。报告必须保留失败状态，不能把它改写为无更新。

Nitter RSS 的限制与来源说明见 `references/nitter.md`。
