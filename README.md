# TREC-COVID 文档选择实验：方法复现与评估分析

**作者：QronG9 · v2.0.0 · 2026-09-05**

**从这里开始：[我的研究短报告](docs/RESEARCH_NOTE.md)** · [方法与计算定义](docs/METHODS.md) · [我的贡献](docs/CONTRIBUTIONS.md)

我围绕“不同文档选择方法取到了什么，以及现有相关性判断能够评价其中多少内容”开展了一组可复算实验。我以 BEIR 版 TREC-COVID 的 **171,332 篇文档、全部 50 个查询**为基础，重建检索方法，保存排名，并分别计算判断覆盖和观察到的检索指标。本仓库汇集我的初始五查询实验、冻结的全查询基线，以及冻结后完成的方法扩展与评估分析。

我发布 **12 个检索 / 选择配置、每配置每查询 top-1000 的固定排名**，连同原始查询、qrels、文档元数据、分析代码和结果表。加上五查询阶段与非空摘要实验，本版共保存 **740,000 条排名位置**。读者可以离线重算结果，也可以沿方法配置和来源记录核查各阶段的实验过程。

**English:** I reimplemented document-selection methods and evaluated 12 retrieval and selection configurations on all 50 BEIR TREC-COVID queries. I report judgment coverage and observed retrieval effectiveness separately, examine document eligibility and fixed-candidate reranking, and compute sharp paired precision bounds. This repository includes saved rankings, original judgments, analysis code, and reproducible outputs from my initial experiments and subsequent extensions.

## 我完成的实验与产出

| 工作 | 我发布的可验证内容 |
|---|---|
| 方法复现与扩展 | BM25、MPNet、两种 Direct 归一化、两类随机选择、Query Expansion、两种 MMR 设置、SPLADE、BGE、BM25 + CrossEncoder；共 600,000 条主排名记录 |
| 全查询评估 | 12 个配置在 @20、@50、@100、@1000 的覆盖与观察相关比例，以及 P@20、Recall@1000 和逐查询表 |
| 文档集合分析 | 方法间集合重合、相对 BM25 的集合分层、BM25 top-1000 内外的文档组成，以及固定候选集重排的集合一致性检查 |
| 文档可用性分析 | 标题与摘要输入定义、空摘要分层，以及 BM25/MPNet 在全库非空摘要文档中的重新取前列实验 |
| 未判断标签分析 | 固定列表的配对 precision 严格可达界限，以及三个基线 top-20 并集内 492 个未判断查询—文档对清单 |
| 可复算发布 | 通用压缩排名、数据字典、版本与哈希、标准库分析入口、测试和 GitHub Actions |

## 主要结果

以下均为 **50 个查询等权平均**。Hole 是未判断比例；观察 P@20 按 `qrel=2` 计相关，U 暂不贡献相关命中。这两类指标分别回答“判断覆盖多少”和“现有标签确认多少相关项”。

| 方法 / 实验配置 | Hole@20 | Hole@100 | 观察 P@20 |
|---|---:|---:|---:|
| BM25 | 0.0720 | 0.1960 | 0.487 |
| MPNet | 0.4030 | 0.4918 | 0.426 |
| Direct：max-sum | 0.0540 | 0.1464 | 0.630 |
| Direct：min-max | 0.0570 | 0.1508 | 0.628 |
| Random Uniform | 0.9960 | 0.9934 | 0.001 |
| Direct + MMR：从 5000 选 1000 | 0.8510 | 0.8760 | 0.035 |
| Direct + MMR：重排既有 1000 | 0.6600 | 0.6630 | 0.078 |
| Query Expansion | 0.0600 | 0.1570 | 0.622 |
| Retrieval Random | 0.1470 | 0.4228 | 0.503 |
| SPLADE | 0.1080 | 0.2636 | 0.600 |
| BGE | 0.1180 | 0.2788 | 0.668 |
| BM25 + CrossEncoder | 0.0880 | 0.2416 | 0.581 |

我将 Direct 的两种归一化配置与其他方法并列复算。来源：[全配置覆盖汇总](results/extensions/coverage_summary.csv)和[观察检索指标](results/extensions/observed_ir_summary.csv)。配置和名称对应见[方法说明](docs/METHODS.md)。模型使用各自记录的输入长度、前缀与评分设置；我将差异解释为这些具体配置在该固定基准上的表现。

我从这些结果中整理出四项可以直接核查的观察：

- **同一类方法也呈现不同结果。** BGE 与 MPNet 都使用稠密向量检索，其 Hole@20 分别为 0.118 和 0.403；我因此按具体模型和配置报告结果。
- **候选集合与前列顺序可以分别检查。** BM25 + CrossEncoder 保留 BM25 的全部 top-1000，因此两者 @1000 的覆盖和召回一致；前列指标随重排变化。两种 MMR 设置进一步区分了“从更大池选文档”与“重排同一集合”。
- **文档可入选条件与覆盖相关。** 在全库非空摘要文档中沿既有评分重新取 top-20，MPNet−BM25 的 Hole 差从 33.1 变为 16.2 个百分点。我同时发布筛选定义、排名和分层计数。
- **固定排名下可以精确界定未知标签的影响。** 保留既有标签并采用 QREL=2 时，Direct−BM25 的平均 P@20 差的严格可达范围为 **[0.092, 0.176]**，整个范围为正。补充配置中，BGE−BM25、SPLADE−BM25、BM25 + CrossEncoder−BM25 的区间也全部为正，详见[扩展界限表](results/extensions/paired_precision_bounds_summary.csv)。

![我的十二个文档选择配置：判断覆盖与观察 P@20](figures/method_comparison.png)

全部配置使用同一组 50 个查询。[三基线深入分析图](figures/research_summary.png)进一步展示摘要条件与配对界限。

## 快速复算

需要 Python **3.9 或更新版本**。在仓库根目录运行：

```bash
python3 scripts/verify_release.py
```

我把核心分析做成仅使用 Python 标准库的离线流程。验证入口检查发布文件哈希，在独立临时目录重算结果并与发布表逐字节比较，运行输入与计算语义测试，检查文档链接和图表来源。本版包含 34 个可重新生成的结果文件、10,274 项历史数值对照和 21 项测试。具体本次运行记录见 [RELEASE_VALIDATION](provenance/RELEASE_VALIDATION.md)。

保存自己复算的结果：

```bash
python3 scripts/analyze.py --output-dir build/results
python3 scripts/analyze_extensions.py --data-dir data --output-dir build/results/extensions
```

第一个入口复算三个基线的深入分析和非空摘要实验；第二个入口复算 12 个全查询配置与初始五查询实验的覆盖、观察指标和集合分析。离线复算使用已发布排名；原始语料到排名的生成配置、代码来源和模型记录在[方法说明](docs/METHODS.md)中单独列出。

我另提供图表重建入口；安装可选绘图依赖后，可从自己的复算表生成两张图：

```bash
python3 -m pip install -r requirements-figures.txt
python3 scripts/plot_results.py --results-dir build/results --output-dir build/figures
```

## 阅读与文件导航

| 入口 | 内容 |
|---|---|
| [研究短报告](docs/RESEARCH_NOTE.md) | 我研究的问题、分阶段工作、完整方法比较和主要分析 |
| [方法与计算定义](docs/METHODS.md) | 12 个配置的实现、0/1/2/U 语义、公式、随机协议和复算层级 |
| [排名生成代码](retrieval_source/README.md) | 原始方法实现、运行配置、依赖及代码来源 |
| [我的贡献与工具使用](docs/CONTRIBUTIONS.md) | 我的实验工作、材料产出和 AI 辅助说明 |
| [数据说明](data/README.md) | 原始数据、排名格式、文档元数据及获取方法 |
| [扩展结果](results/extensions/) | 全查询配置、初始五查询实验的逐查询与汇总结果 |
| [三个基线的覆盖表](results/coverage_summary.csv) | BM25、MPNet、Direct 在四个深度的判断覆盖 |
| [摘要分层](results/abstract_strata.csv) / [非空摘要实验](results/nonempty_coverage_summary.csv) | 文档组成与可入选条件分析 |
| [配对 precision 界限](results/paired_precision_bounds_summary.csv) | 三个基线共享未知标签抵消后的严格可达区间 |
| [top-20 未判断清单](results/top20_unjudged_frame.csv) | 查询、文档、摘要状态及三个基线中的名次 |
| [研究过程](docs/RESEARCH_PROCESS.md) | 分阶段做法、后续补充与本版采用的定义 |
| [来源与版本记录](provenance/README.md) / [历史材料](archive/README.md) | 初始实验、冻结记录和后续补充的对应关系 |

结果比例使用 0–1；百分点为比例差乘 100。正文 precision 和界限采用 `label_rule=strict_eq2`；`relaxed_ge1` 是单独提供的相关性阈值补充。

## 我如何组织研究材料

我参考 [ACM Artifact Review and Badging](https://www.acm.org/publications/policies/artifact-review-and-badging-current) 对 documented、consistent、complete、exercisable 的要求组织仓库：

| 要求 | 对应材料 |
|---|---|
| 说明充分 | README、研究短报告、方法配置和数据字典 |
| 结果与材料一致 | 原始标签、保存排名、逐查询表、来源对照和哈希 |
| 研究范围内组件齐全 | 离线输入、分析脚本、测试、图表及第三方材料来源 |
| 可执行 | 干净目录复算、自动验证入口和 GitHub Actions |

上述四项是本仓库的材料组织标准；发布状态为作者整理和计算验证，ACM 徽章状态为未申请。

## 引用、许可与发布

我以 Rangreji、Zhong、Field 的文档选择研究为复现起点，并使用 BEIR/TREC-COVID 的数据与评估背景。BEIR 关于判断覆盖和补充判断的研究为我的分析提供了参考，文献与具体关系见[短报告](docs/RESEARCH_NOTE.md)。

- [CITATION.cff](CITATION.cff)：本项目引用信息；上游来源见短报告和数据说明。
- [LICENSE](LICENSE)：代码、文档及第三方数据的许可范围。
- [GitHub 上传说明](docs/GITHUB_RELEASE.md)：上传前检查及仓库发布步骤。

原始冻结材料保留原有版本；本版把完成的后续运行结果一并整理为可核验的研究成果，默认阅读入口是上方的研究短报告。
