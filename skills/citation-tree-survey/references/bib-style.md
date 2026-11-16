# bib 条目写法与年份陷阱

## 条目类型

| 情况 | 类型 | 必备字段 |
|---|---|---|
| 已正式发表（会议） | `@inproceedings` | title, author, booktitle（全称 + 括号缩写）, pages, year |
| 已正式发表（期刊） | `@article` | title, author, journal, volume, number, pages, year |
| 仅预印本 | `@misc` | title, author, year, eprint, archivePrefix, url |
| 代码/数据仓库 | `@misc` | title, author, howpublished, year, url |

venue 用全称并带缩写，和项目里已有条目保持一致：

```
booktitle = {Advances in Neural Information Processing Systems (NeurIPS)}
booktitle = {International Conference on Learning Representations (ICLR)}
booktitle = {Conference on Robot Learning (CoRL)}
booktitle = {Robotics: Science and Systems (RSS)}
```

`mkbib.py` 的 `VENUES` 表覆盖 CV/ML/RO 常见会议；用 `--venue-map my.json` 扩展
（格式 `{"semantic scholar 返回的 venue 串": ["inproceedings", "全称 (缩写)"]}`）。

## 作者

- 超过 8 位时写 `and others`；CVPR/NeurIPS 的 ieeenat 样式会自行截断，但保留前 8 位便于核对。
- 团体作者用双花括号保护，否则会被当成 `姓, 名`：

```
author = {{Open X-Embodiment Collaboration}}
author = {{NVIDIA} and Bjorck, Johan and ... and others}
author = {{Octo Model Team} and Ghosh, Dibya and ...}
```

- 复姓与前缀：`de Vries, Harm`、`van Elteren, ...`，不要把前缀当名字。
- 带重音的姓：`Sch{\"o}lkopf`、`Casta{\~n}eda`、`Mart{\'i}n-Mart{\'i}n`。

## 标题

- 冒号前的缩写用花括号锁住大小写：`{{RT-2}: Vision-Language-Action ...}`、`{{DINOv2}: ...}`。
- 样式文件会把标题转成句首大写，没有保护的专有名词会被压成小写（`smolvla`）。
- 标题含数学（`$\pi_{0.5}$`）时，审计工具会因为剥掉 LaTeX 而匹配失败，属于已知误报；用 arXiv id 核对。
- 短横线统一用 `--`，不要留 Unicode en dash。

## 年份陷阱（最容易出错的一项）

Semantic Scholar 的 `year` 常常是**首次出现年份**，不是会议年份：

| 论文 | arXiv | 真实发表 | S2 给的 |
|---|---|---|---|
| Flow Matching | 2022-10 | ICLR 2023 | 2022 |
| GCN (Kipf) | 2016-09 | ICLR 2017 | 2016 |
| DINOv2 | 2023-02 | TMLR 2024 | 2023 |

规律：**ICLR 在 9 月截稿、次年 4–5 月开会**，所以凡是 9 月及以后挂到 arXiv 的 ICLR 论文，会议年份 = arXiv 年份 + 1。`mkbib.py` 已实现该规则并在输出里打 `% TODO: CHECK year`。

其他情况：

- 期刊版晚于会议版：引正式发表的那一版，年份用期刊年。
- 只有 arXiv 版：年份用 arXiv 首次提交年，不要写"to appear"。
- 预印本年与发表年差 ≤3 年时，参考审计报告会判"预印本→正式发表"，这是正常差异，不是错误。

## 页数

- 会议论文的 pages 从 S2 的 `journal.pages` 取，格式 `起始--结束`。
- 取不到就省略，不要编。省略 pages 在很多样式里是可接受的，编错页码不是。

## 合并前自检

1. 缩写是否被花括号保护？
2. 团体作者是否被当成人名（`Team, Octo Model` 就是错的）？
3. `CHECK year` 行是否逐条确认？
4. 有没有和已有条目重复（同一工作的不同版本）？
5. `check_paper.py` 是否报告"条目从未被引用"？
