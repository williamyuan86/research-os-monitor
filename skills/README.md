# Skills

WorkBuddy 技能包，每个子目录是一个自包含技能（`SKILL.md` + `scripts/` + `references/`）。
安装方式：把子目录整体复制到 `~/.workbuddy/skills/`，重启会话后生效。

```bash
cp -R skills/citation-tree-survey ~/.workbuddy/skills/
```

## 索引

| 技能 | 作用 | 触发场景 |
|---|---|---|
| [`citation-tree-survey`](citation-tree-survey/SKILL.md) | 用引文树（backward + forward snowballing）重新调研并补全论文参考文献：排序候选缺口、核实元数据、生成 bib、检查页数与引用一致性 | 参考文献太少、related work 覆盖不足、投稿前确认重要工作没漏引 |

## citation-tree-survey 速览

```bash
# 1. 从现有 bib 生成种子（缺 arXiv id 的按标题解析）
python skills/citation-tree-survey/scripts/seeds_from_bib.py main.bib -o seeds.json --workdir lit_work

# 2. 双向雪球
python skills/citation-tree-survey/scripts/snowball.py seeds.json --workdir lit_work

# 3. 排序：谁被最多自己的种子引用，谁同时引用最多自己的种子
python skills/citation-tree-survey/scripts/rank.py lit_work/graph.json --bib main.bib -o lit_work

# 4. 生成 bib 条目（元数据取自 arXiv + Semantic Scholar）
python skills/citation-tree-survey/scripts/mkbib.py rt2:2307.15818 -o additions.bib --workdir lit_work

# 5. 验证：cite 一致性、未引用条目、正文页数上限
python skills/citation-tree-survey/scripts/check_paper.py --tex main.tex --bib main.bib --limit 8
```

设计要点见 [`references/selection-rules.md`](citation-tree-survey/references/selection-rules.md)：
候选按"跨种子共现"排序而非被引量，每条新增文献必须能挂到正文一句已有论断上。
