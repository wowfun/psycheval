用 hackernews-daily 获取 Hacker News 当前热门，按快照顺序把前 12 条的标题、指标、原文和讨论链接整理到 hacker-news-YYYYMMDDTHHMMSSZ.md，文首 front matter 请写明 platform、generated_at、source 和 snapshot_at。

快照时间以实际抓取时刻为准，保存到 .trend-digest/hacker-news.json。每条附忠实、具体的中文摘要，保留来源的含义和限定；只有标题或元数据时明确证据范围，不编造未读原文的结论，也不要用“热门新闻”等空泛模板替代信息。清楚说明抓取失败或证据不足。将唯一报告放入环境变量 TREND_ARTIFACTS_DIR 指定的目录，最终回答写明确切文件名。
