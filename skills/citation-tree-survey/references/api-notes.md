# 接口行为与配额（2026-11 实测）

## Semantic Scholar Graph API

基础路径 `https://api.semanticscholar.org/graph/v1`，无需 key。

| 用途 | 端点 |
|---|---|
| 参考文献 | `/paper/arXiv:{id}/references?fields=title,year,venue,citationCount,authors,externalIds&limit=100` |
| 被引 | `/paper/arXiv:{id}/citations?...&limit=200` |
| 批量元数据 | `POST /paper/batch?fields=title,venue,year,journal,publicationVenue`，body `{"ids":["ARXIV:xxxx"]}` |
| 标题检索 | `/paper/search?query=...&limit=3&fields=title,externalIds` |

**关键限制：`citations` 按时间倒序返回。** 取 200 条拿到的是最近发表的论文，绝大多数是零引用的新预印本，用它找"重要下游"会完全失败。这就是前向必须换 OpenAlex 的原因。

其余：

- 无 key 时约 1 req/s，超了直接 429。必须带缓存 + 限速 + 有上限的退避（本技能默认单请求最多等 25 s）。
- `citationCount` 字段可用，但同一篇论文在不同记录里可能不一致。
- batch 接口最多 500 个 id，一次调用返回全部 venue/year/pages，是省配额的正确姿势。

## OpenAlex

`https://api.openalex.org`，无需 key。

**前向引文（唯一能按影响力排序的免费源）：**

```
/works?filter=cites:W4385403811&sort=cited_by_count:desc&per-page=40
```

其他要点：

- arXiv 论文的 work id 用 DOI 过滤拿：`filter=doi:10.48550/arxiv.2304.13705`。
- `filter=ids.openalex:arxiv:2304.13705` **是非法语法**，会返回 400 `'arxiv:...' is not a valid OpenAlex ID`。
- 免费额度按 **IP 共享**，约 $0.10/天，单请求约 $0.001，即一天 100 次上下。额度耗尽后所有请求失败，且不会自动恢复。批量任务先跑 `--no-forward`，确定要前向时再跑。
- 返回体里有 `cost_usd` 和 `meta.notice`，可用来判断还剩多少额度。

## arXiv API

`https://export.arxiv.org/api/query`，返回 Atom XML。

- **标题→ID 的首选源**：`search_query=ti:"..."`，结果带精确标题，便于做相似度校验。比 S2 检索稳定得多。
- 限速约 3 s/请求，高频会直接断连（不是 429，是空响应）。本技能默认 `pause=3.0`。
- 支持 `id_list=` 批量取元数据（标题、作者顺序、首次提交日期）。
- `journal_ref` 字段**不能依赖**：多数论文为空，有值也常是作者手写的自由文本。

## Crossref / DBLP

- Crossref 对会议论文覆盖率低：ICLR/NeurIPS/CoRL 大量条目查不到或只有 SSRN 副本，标题匹配容易命中错版本。**不要用它定 venue。**
- DBLP 数据最干净，但有 bot 校验（返回 "Making sure you're not a bot"），脚本化访问会失败。需要 DBLP 时让人工去网页确认。
- 判断 venue 的现实方案：S2 的 `venue` 字段 + 本地 venue 映射表（`mkbib.py` 的 `VENUES`），映射不到就退化成 arXiv 条目并标注。

## 常见失败模式

| 现象 | 原因 | 处理 |
|---|---|---|
| `citations` 全是 2026 年新论文 | S2 按时间倒序 | 换 OpenAlex `sort=cited_by_count:desc` |
| 单条请求卡几分钟后被杀 | 429 无上限退避 | `get_json(max_wait=25)`，逐条容错继续 |
| OpenAlex 全部 400 | 用了 `ids.openalex:arxiv:` 语法 | 改 `doi:10.48550/arxiv.<id>` |
| arXiv 返回空 body | 请求过快 | 加 3 s 间隔 |
| 标题解析到别人的论文 | 同名/系列论文 | 相似度阈值 0.90，且用返回标题二次核验 |
