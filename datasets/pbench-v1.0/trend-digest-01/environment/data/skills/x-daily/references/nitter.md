# Nitter RSS contract

- 每个账号依次尝试 skill 内置的公共 Nitter 实例列表。
- RSS 成功但时间窗口内没有 item 是 `no_updates`，不是网络失败。
- RSS 无法提供可靠的 like、repost 或 reply 指标，因此快照不伪造这些指标。
- 输出链接统一为 `https://x.com/<handle>/status/<id>`，RSS 实例地址只作为抓取遥测保留。
