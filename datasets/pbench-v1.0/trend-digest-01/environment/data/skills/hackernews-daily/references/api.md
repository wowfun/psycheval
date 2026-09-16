# Hacker News API contract

- 热门列表：`https://hacker-news.firebaseio.com/v0/topstories.json`
- Story：`https://hacker-news.firebaseio.com/v0/item/<id>.json`
- 只接受 `type = story` 且未标记 `deleted` 或 `dead` 的对象。
- 排名沿用 topstories ID 的原始顺序，不按 score 重新排序。
