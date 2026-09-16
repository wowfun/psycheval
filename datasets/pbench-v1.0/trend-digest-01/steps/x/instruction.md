用 x-daily 看看 Excel 里这些账号过去 24 小时的动态，把每个账号的状态和全部新推文整理到 x-YYYYMMDDTHHMMSSZ.md，文首 front matter 请写明 platform、generated_at、source、window_start 和 window_end。

窗口以实际抓取时刻为准；将快照保存到 .trend-digest/x.json，按 Excel 的 11 个账号分别使用包含 @handle 的二级标题。逐账号明确写出“状态：成功”“无新推文”或“抓取失败”，成功时保留窗口内全部推文的原文和链接，并附忠实、具体的中文摘要。区分无更新、抓取失败和证据不足，不把未获取的信息说成不存在，不用空泛模板替代内容。将唯一报告放入环境变量 TREND_ARTIFACTS_DIR 指定的目录，最终回答写明确切文件名。
