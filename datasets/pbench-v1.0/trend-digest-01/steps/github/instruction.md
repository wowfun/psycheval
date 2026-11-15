帮我查看 GitHub 最近一周的热门项目，把 weekly 页面前 10 个仓库的排名、指标、链接和中文摘要整理到 github-YYYYMMDDTHHMMSSZ.md，文首 front matter 请写明 platform、generated_at、source 和 window（weekly）。

直接获取 https://github.com/trending?since=weekly 的当前来源证据。摘要应忠实于来源，具体说明项目的用途和有证据支持的关注点，不要仅重复“热门项目”等模板；信息不足时明确说明，不编造细节。用清楚的中文保留关键限定。将唯一报告放入环境变量 TREND_ARTIFACTS_DIR 指定的目录，最终回答写明确切文件名。

保持榜单顺序，每个仓库使用一个独立小节、编号条目或表格行，让排名、仓库链接、指标及摘要属于同一项；不要把全部链接堆在一项或用重复仓库凑十项。来源没有给出的指标或细节应明确标为未提供，不猜测。补充来源链接可以保留，但不能代替逐仓库内容。
