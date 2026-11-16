---
name: citation-tree-survey
description: 用引文树（citation chaining / snowballing）重新调研并补全论文参考文献：先取论文现有核心文献作种子，向后拉它们的参考文献、向前拉引用它们且被引最高的下游工作，按跨种子共现排序找出真正缺失的重要研究，再核实元数据、生成 bib 条目、插回正文并检查页数与引用一致性。当用户说参考文献太少/调研不充分/达不到评审预期（例如"怎么也得有 70 多篇"）、要求补引用、重做 related work、或用"参考文献的参考文献树/snowballing/citation chaining"找文献时使用。
agent_created: true
---

# 引文树补全参考文献

## 何时使用

- 审稿意见或用户指出参考文献数量不足、覆盖面窄、"一眼没调研"。
- 准备投稿，需要确认本领域公认的重要工作没有被漏掉。
- 写/改 Related Work，需要给一段已经有论断的文字补上恰当出处。
- 明确要求用"引文树""参考文献的参考文献""snowballing""citation chaining"调研。

## 先立规矩：这不是凑数量

补文献的目标是**让每一篇都能挂到一句已有的论断上**。三条硬规则：

1. **双信号排序，被引量只做 tie-break**。`back`（你的多少个种子引用它）说明它是领域前置工作；`fwd`（它同时引用你的多少个种子）说明它卡在论证路径上。两万引但与本文无关的论文是堆数量。
2. **挂不上论断就不加**。新增条目必须在正文里找到一句需要它支撑的话；找不到就说明它对这篇文章不重要。
3. **数量是结果不是指标**。一次真实的扩容是 50 → 76（正文 74），加 26 条；如果调研下来只缺 12 条，就加 12 条。

## 工作流

### Step 0 — 从现有 bib 生成种子

```bash
python scripts/seeds_from_bib.py main.bib -o seeds.json --workdir lit_work
```

- 条目里带 arXiv id（`eprint`/`url`/`journal` 中的 `arXiv:xxxx`）的直接采用。
- 其余按标题查 arXiv API 解析，相似度低于 `--min-sim`（默认 0.90）的留空并列出，不猜。
- 种子选择顺序：三根骨架（主方法/基线模型/评测基准）→ 每个 related-work 段落各 2–3 篇（适配器、鲁棒性、图/关系、一致性训练）→ 有争议的对照工作。
- 20–30 个种子足够。少于 10 个时 `back` 信号没意义。

### Step 1 — 双向雪球

```bash
python scripts/snowball.py seeds.json --workdir lit_work --forward-top 40
```

- 后向（S2 references）+ 前向（OpenAlex 按 `cited_by_count` 排序）。
- 全部请求落盘缓存，中断后重跑不重复花钱；加 `--only key1,key2` 只补跑个别种子。
- OpenAlex 免费额度很小，见 `references/api-notes.md`；额度紧时用 `--no-forward` 只做后向。

### Step 2 — 排序、筛选（本技能的核心判断环节）

```bash
python scripts/rank.py lit_work/graph.json --bib main.bib --min-back 3 -o lit_work
```

输出三块：backward hubs、forward hubs、每个种子的高被引下游；明细写入 `candidates.csv`。
按 `references/selection-rules.md` 逐条过：

1. `back >= 3` 且不在 bib 里 → 大概率是真缺口，优先看。
2. `fwd >= 3` 且被引高 → 说明它是这个方向的重要下游，判断是否需要出现在 related work 的谱系里。
3. 每个候选问一句：**它支撑我哪句话？** 答不出就跳过。
4. 按段落归类（方法谱系 / 评测与协议 / 表征 / 一致性 / 基准），保证每段都有增量，而不是全堆在一段。

### Step 3 — 核实元数据并生成条目

```bash
python scripts/mkbib.py rt2:2307.15818 octo:2405.12213 -o additions.bib --workdir lit_work
```

- 标题与作者顺序取 arXiv API（权威），venue/year/pages 取 Semantic Scholar。
- 未映射的 venue 会退化成 arXiv `@misc` 并打 `% TODO`；**不要**自己编 venue。
- `% TODO: CHECK year` 必须逐条看：S2 记的是首次出现年份，ICLR 类（9 月截稿、次年春季开会）常差一年，脚本已按规则修正并标注。
- 生成后人工扫一遍：缩写是否需要加花括号、团体作者是否被当成人名、venue 串是否符合本项目风格（见 `references/bib-style.md`）。

### Step 4 — 插回正文

- **贴着已有论断插，不要新开一段**。新增措辞控制在几行内，引用本身几乎不占版面。
- 组引是正当的：一句 "generalist policies [1,2,3,4,5,6]" 比六句话更符合版面经济学。
- 时间线要顺：一致性训练从 Temporal Ensembling → Mean Teacher → UDA → FixMatch，不要写反。
- 同一篇在 related work 出现两次可以接受，但不要在同一句里重复。

### Step 5 — 验证

```bash
latexmk -pdf -interaction=nonstopmode main.tex
python scripts/check_paper.py --tex main.tex --bib main.bib --limit 8
python scripts/audit_bib.py main.bib --outdir audit_out
```

- `check_paper.py` 抓三类编译不会报的错：cite 键缺失、bib 条目从未被引用（BibTeX 静默丢弃）、正文超出页数上限。
- `audit_bib.py` 跑 reference-audit 并打印四类固定误报的判读方法（标题含数学、团体作者、GitHub 仓库、早期会议论文集）。
- 收尾必须亲眼确认：PDF 里没有 `??`，正文仍在上限页内，参考文献从正文结束处开始。

## 脚本

| 脚本 | 作用 |
|---|---|
| `seeds_from_bib.py` | 从 .bib 抽种子；缺 arXiv id 的按标题解析（arXiv 优先，S2 兜底） |
| `snowball.py` | 双向雪球，落 `graph.json`，全程缓存 |
| `rank.py` | 聚合排序，出 `candidates.csv` 与三类榜单 |
| `mkbib.py` | 取权威元数据生成 bib 条目，标注待人工确认项 |
| `check_paper.py` | cite/bib 一致性 + 正文页数上限 |
| `audit_bib.py` | 封装 reference-audit，附误报判读清单 |

## 参考

- `references/api-notes.md` — 各接口的真实行为、配额、坑（前向为什么必须用 OpenAlex）。
- `references/selection-rules.md` — 筛选与归类的判断标准，含一次真实调研的分布数据。
- `references/bib-style.md` — bib 条目写法约定与年份陷阱。
