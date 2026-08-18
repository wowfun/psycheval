---
name: hackernews-daily
description: 使用 Hacker News 官方 API 抓取当前 topstories，并按 API 顺序输出前 12 条有效 story 的规范化 JSON 快照。
---

# Hacker News Daily

本 skill 只负责确定性抓取和规范化，不生成最终 Markdown。

运行：

```bash
python /app/skills/hackernews-daily/scripts/fetch.py \
  --output /app/.trend-digest/hacker-news.json
```

成功快照包含 `generated_at`、官方 `source_url` 和按 topstories 顺序排列的 `stories`。每条 story 包含排名、ID、原始标题、文章 URL、讨论 URL、作者、score、评论数和发布时间。

无法取得 12 条有效 story 时命令退出非零，不生成伪造条目。API 说明见 `references/api.md`。
