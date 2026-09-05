# TREC-COVID 文档选择方法：部分复现与判断覆盖诊断

**先读：[修订研究短报告](docs/RESEARCH_NOTE.md)** · [简短勘误](docs/ERRATA.md) · [复算方法](docs/METHODS.md)

一份已收敛研究范围的科研起步作品：从三个固定检索排名和 BEIR 原始 qrels
复算判断覆盖、摘要可用性敏感性及配对 P@20 的严格界限。覆盖全部 50 个查询。
本项目的结论限于当前 BM25、MPNet 和 Direct 实现；未证明新的 pooling bias
机制，未进行人工补评，也未复现源论文的下游主题分析。

**English:** A partial reimplementation and judgment-coverage diagnostic on
BEIR TREC-COVID. The release contains portable saved rankings, original query
and judgment files, text-free corpus metadata, and an offline analysis pipeline.
It reproduces descriptive differences and sharp paired precision bounds under
fixed rankings and retained labels. It does not establish a causal pooling-bias
mechanism, a general dense-retriever deficit, or downstream research distortion.

![Core diagnostics from the regenerated result tables](figures/research_summary.png)

## 可复算的核心结果

| 全部 50 查询等权平均 | BM25 | MPNet | Direct |
|---|---:|---:|---:|
| Hole@20（未判断比例） | 0.0720 | 0.4030 | 0.0540 |
| Hole@100 | 0.1960 | 0.4918 | 0.1464 |
| 观察 P@20，QREL=2 | 0.487 | 0.426 | 0.630 |

- 在非空摘要文档总体中沿既有评分重新取 top-20，MPNet−BM25 的 Hole
  差从 33.1 缩至 16.2 个百分点。这是 eligibility 敏感性，不是因果贡献比例。
- 固定排名、保留已有标签并采用 QREL=2 时，Direct−BM25 的平均 P@20
  差的严格可达范围为 **[0.092, 0.176]**；当前 holes 的任何二值补全均不能
  翻转这一对方法的顺序。MPNet 的相对顺序仍未确定。
- 三个 top-20 列表的并集中有 **492 个未判断查询—文档对**。附带清单只界定
  缺少的证据，不是新的相关性标签或已批准的医学标注方案。

BEIR 已在同库研究 Hole 与补评后的排序变化。本项目将先行工作作为定位依据，
不把这些已知现象声称为新发现。详见短报告中的文献与局限。

## 快速复算：离线、无需模型或第三方 Python 包

需要 Python **3.9 或更新版本**。在仓库根目录运行：

```bash
python3 scripts/verify_release.py
```

它验证发布文件 SHA-256，在独立临时目录重算全部 14 个 CSV/JSON 文件并
与发布结果逐字节比较，进行 2,572 项原输出/审计数值对照，运行数学语义与
输入错误测试，并检查相对链接及图表数据是否过期。不会改写已发布的结果。

如果希望保留自己重算的结果：

```bash
python3 scripts/analyze.py --output-dir build/results
```

全部小型输入已随仓库提供，详见[数据来源与格式](data/README.md)。核心复算
不依赖原项目目录、个人电脑路径、旧虚拟环境或模型下载。正常执行约需数秒，
实际时间随机器变化；测试会增加少量耗时。

## 结果导航

| 产出 | 含义 |
|---|---|
| [coverage_summary.csv](results/coverage_summary.csv) | 各方法、深度的判断覆盖与未判断比例 |
| [paired_coverage_summary.csv](results/paired_coverage_summary.csv) | 配对差及正、平、负查询数；Hole 与 Judged 字段明确区分 |
| [observed_precision_summary.csv](results/observed_precision_summary.csv) | 已知相关项计算的观察 precision |
| [paired_precision_bounds_summary.csv](results/paired_precision_bounds_summary.csv) | 共享 U 抵消后的配对严格可达界限 |
| [abstract_strata.csv](results/abstract_strata.csv) | 各方法自己检索集合中的摘要状态、比例与条件覆盖 |
| [nonempty_coverage_summary.csv](results/nonempty_coverage_summary.csv) | 全库非空摘要 eligibility 排名的覆盖敏感性 |
| [top20_unjudged_frame.csv](results/top20_unjudged_frame.csv) | 492 对清单及在各方法中的排名，无新相关性标签 |
| [data_audit.json](results/data_audit.json) | 数据计数、约束校验、输入哈希与假设 |

结果比例使用 0–1，图中百分点使用 ×100。正文 precision/bounds 采用
`label_rule=strict_eq2`；`relaxed_ge1` 是单独提供的补充阈值敏感性。
每个主要汇总表均有对应 `*_by_query.csv`，便于追踪查询层面的反例。

## 复算范围

| 层级 | 提供了什么 | 不能据此声称什么 |
|---|---|---|
| 固定排名 → 结果 | 原始 qrels、查询、排名与独立标准库脚本；离线验证 | 不验证已有人工标签是否正确 |
| 原始语料 → 元数据 | 原始下载入口、SHA-256 与元数据重建/比较脚本 | 不将摘要缺失当作随机处理 |
| 原始模型 → 排名 | 原始排名、输入来源哈希与完整方法说明；原检索历史本地保留 | 未在本 release 完成整个语料的模型冷启动复现 |

原始语料和完整审计的背景见 [METHODS](docs/METHODS.md)。可用
`python3 scripts/fetch_corpus.py` 获取并验证原始语料；这一步需要网络，
但不是运行核心分析的前提。

图的 PNG/SVG 已包含。重新绘图需要额外安装 `requirements-figures.txt`，
再运行 `python3 scripts/plot_results.py`。其源表哈希保存在
[figure_sources.json](figures/figure_sources.json)。

## 按 ACM 的研究材料要求组织

| 要求 | 本仓库对应材料 |
|---|---|
| Documented：有充分说明 | 本页、[短报告](docs/RESEARCH_NOTE.md)、[方法](docs/METHODS.md)、[数据字典](data/README.md) |
| Consistent：材料支持结论 | 原始标签与排名、逐查询结果、参考值比对、三列勘误 |
| Complete：范围内必要组件齐全 | 离线小型输入、脚本、测试；未分发的大型/第三方材料有来源与边界说明 |
| Exercisable：能够执行 | `verify_release.py`、从干净目录重算、GitHub Actions 配置 |

这是对 [ACM Artifact Review and Badging](https://www.acm.org/publications/policies/artifact-review-and-badging-current)
基本要求的自查与组织方式，**不表示已获得 ACM 评审或徽章**。此次验证记录见
[RELEASE_VALIDATION](provenance/RELEASE_VALIDATION.md)。

## 历史、署名和许可

原项目及冻结标签保持原状；原审计针对 `6a7415f`，封装时原项目 HEAD 已为
`e5d96e1`，含后续其他检索器扩展。本 release 的核心结论只使用三个已审计方法。
原有 72 项冻结文件校验全部通过；来源和对照见 [provenance](provenance/README.md)。

原稿与完整历史精确保存在本地 `archive/local-original/`，被 Git 忽略；
旧稿的不足由[勘误](docs/ERRATA.md)明确更正。详见[归档说明](archive/README.md)。
默认阅读入口始终为修订短报告，旧稿不作为当前研究结论。

- [贡献、AI 工具使用和复核范围](docs/CONTRIBUTIONS.md)
- [引用信息](CITATION.cff)：引用本 artifact 时同时引用 BEIR、TREC-COVID 和源研究。
- [许可范围](LICENSE)：代码 MIT；文档、资料与数据各自的许可范围明确分开。
- [GitHub 上传说明](docs/GITHUB_RELEASE.md)：本仓库准备完成后再选择远程仓库与可见性。

