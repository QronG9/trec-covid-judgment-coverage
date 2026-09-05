# 方法、数据语义与复算边界

本说明定义[修订短报告](RESEARCH_NOTE.md)的目标量和输入。默认入口复算保存的固定排名；从头获取模型、编码完整语料并重建排名属于另一层工作，不能用快速复算成功代替。

## 输入与版本

数据来自 BEIR 版 TREC-COVID：171,332 篇文档、50 个查询、66,336 行 qrels。正式判断为 0/1/2，共 66,334 个查询—文档对；两行 −1 为 Q38/`9hbib8b3`、Q50/`svo94kuo`。本包保留原始 qrels，不把 −1 或缺失行重写为 0。版本及校验和以仓库数据说明和 manifest 为准；不要用另一版 NIST qrels 直接替换 BEIR qrels。

查询和文档 ID 始终作为字符串。排名中的文档 ID 通过原语料顺序映射导出，不重新按 ID 排序改变名次。主要方法是 `bm25`、`mpnet`、`direct`，每题各 1000 个不同文档，共 150,000 条排名记录。历史 `sbert` 名称对应当前 `mpnet`，不是额外的第四个方法。

原始语料文本通过上游下载获取；仓库跟踪用于核查的文档元数据及其来源校验信息，不以本仓库许可覆盖原文章内容。摘要缺失定义为 BEIR `text` 字段在空值回退为空字符串并 `strip()` 后为空。全库该条件为 42,140 篇；非空摘要文档为 129,192 篇。

## 排名如何产生

以下复述当前本地实现，不把源论文未说明的细节视为作者原始配置。

| 环节 | 本地实现 | 与源方法的边界 |
|---|---|---|
| 文档输入 | `title` 和 `text` 各自去除首尾空白；两者非空时拼成 `title + '. ' + text`，否则使用非空字段。 | 标题/摘要具体拼接未由源文充分固定；相同输入不代表两类方法受它的影响相同。 |
| 查询输入 | BEIR `queries.jsonl` 的自然语言 `text` 字段。 | 不使用 `metadata.query` 的关键词式文本或 `metadata.narrative` 扩展。 |
| BM25 分词 | 小写 → 正则 `[a-z0-9]+` → NLTK 英文停用词 198 项 → NLTK PorterStemmer；查询同样处理，重复查询词仍累计贡献。 | 源文说明 stemming/停用词，但未固定 tokenizer、停用词快照或全部运行环境。 |
| BM25 计分 | BM25Okapi 语义；k1=1.5，b=0.75，epsilon=0.25；全库平均词项长度约 113.296722。 | IDF 为 `ln((N-df+0.5)/(df+0.5))`，负值替换为 `0.25 × 全词表平均 IDF`，不是 Lucene IDF。 |
| MPNet | `sentence-transformers/all-mpnet-base-v2`，768 维；最大长度 384 tokens；float32、L2 归一化向量点积。 | 截断等选择并非均由源文指定；仅代表这个 checkpoint，不代表所有 dense 检索器。 |
| Direct | 各组件 top-1000 的并集；在并集内计算 `BM25/max(BM25) + MPNet/max(MPNet)`，再取 1000。 | 源文正文称 min-max，但公式为除以最大值；候选深度未明确。本发布选择公式的 max-sum 版本，不认证唯一源实现。 |
| 并列处理 | 分数降序，随后按原语料索引升序。 | 不以文档 ID 字典序打破并列；浮点平台差异仍可能交换近并列位置。 |

审计核查到的本地 MPNet 快照 revision 为 `e8c3b32edf5434bc2275fc9bab85f82640a19130`。原运行脚本未明确固定 revision，因此这条记录描述核验到的快照，不是重新证明最初模型下载过程。模型来源见[模型卡](https://huggingface.co/sentence-transformers/all-mpnet-base-v2/tree/e8c3b32edf5434bc2275fc9bab85f82640a19130)。

现存审计曾独立重建全部 50 个 BM25 排名，并在浮点容差内验证分数；MPNet 则重新编码全部 50 条查询与 16 篇抽样文档，复用全库文档向量检查排名。CPU/MPS 在近并列处出现位置交换，审计中的 MPNet top-1000 集合不变。该记录不等于全部 171,332 篇文档的冷启动重编码，也不保证任意设备逐名次相等。本包固定排名是核心结果的权威输入。

## 判断状态与覆盖

对查询 q、文档 d，令 `J(q,d)=1` 当且仅当原 qrel 属于 `{0,1,2}`，其余为 0。J=0 的显示标签记为 U。每个方法 m 的固定 top-k 集合记为 `S(m,q,k)`。

```text
Hole(m,q,k) = sum[1 - J(q,d), d in S(m,q,k)] / k
Judged(m,q,k) = 1 - Hole(m,q,k)
mean_Hole(m,k) = sum[Hole(m,q,k), q in all 50 queries] / 50
```

主深度为 20、100；同时发布 50、1000 的补充描述。这里“主”表示修订报告的呈现重点，不表示存在已核实的事前预注册。每题恰有 k 条时，query macro 与所有检索位置 pooled 的覆盖率相等。

[摘要分层表](../results/abstract_strata.csv)按各方法自己的排名分层；不同层/方法的文档集合和分母不等。层内 pooled Hole 是 U 总数除以该层检索对总数；不能不加说明地与逐查询条件率的等权平均互换。没有文档的条件层不能补 0 来制造观察值。

[配对覆盖表](../results/paired_coverage_by_query.csv)逐题计算方法 A−B 的 Hole 差，汇总时查询等权。正、负、平局由未判断整数计数差决定，避免浮点误差将理论平局拆开。本报告不采用将检索位置当相互独立样本的置信区间。

## 观察 precision

主相关性定义为 qrel=2。qrel 0/1 是已判断但未达到此阈值；U 暂未贡献相关命中。

CSV 中正文对应 `label_rule=strict_eq2`。另行发布的 `relaxed_ge1` 将 qrel=1、2 均计为相关，仅作为阈值敏感性的补充；其 precision 与界限应单独读取，不与正文的严格定义混合。

```text
P_observed(m,q,k) = count(qrel = 2 in S(m,q,k)) / k
```

这是传统观察指标约定，不是给 U 新增不相关标签。若保留已有标签且全部 U 后续可获正确二值标签，设 top-k 中 U 数为 u、其中达到相关阈值的比例为 p，则 `P_true = P_observed + (u/k) × p`。u=0 时增量为 0，无需定义 p。U 内相关率未知，不能仅凭 Hole 推断漏计量。

### 配对 P@k 的严格可达界限

对同一查询，设 A、B 为两个固定 top-k 集合，`δ_obs=P_obs(A)−P_obs(B)`；`U_Aonly` 为 A\B 中的 U 数，`U_Bonly` 为 B\A 中的 U 数。

```text
lower(q) = δ_obs(q) - U_Bonly(q) / k
upper(q) = δ_obs(q) + U_Aonly(q) / k
mean_lower = sum[lower(q)] / 50
mean_upper = sum[upper(q)] / 50
```

同一查询—文档对的未知标签在两方法间共享，因此交集中的 U 在差值里抵消。令所有 B 独有 U 相关、A 独有 U 不相关达到下界；反向赋值达到上界。同一文档在不同查询下是不同相关性判断，允许其标签随查询变化。没有再添加相关数量、主题或医学内容约束，所以每个配对区间在这些假设下严格可达；不同配对的所有端点不要求同时由同一标签赋值达到。

这些是未知标签赋值的界限，不是抽样置信区间。改变排名、把 qrel=1 也列为相关、修改已判断标签或将 condensed 列表作为新排名，均会改变目标量，不能继续引用当前界限。完整逐题与汇总结果见[配对 precision 界限](../results/paired_precision_bounds_summary.csv)。

## 非空摘要的 eligibility 敏感性

在原全库筛出 `text.strip()` 非空的 129,192 个文档，在该集合内按既有评分定义各取 top-1000，而非对原 top-k 简单删除。BM25 继续使用原全库索引的词频、IDF 及平均文档长度，没有对筛后语料重建索引；MPNet 复用既有全库文档向量及核验查询向量计算分数。并列规则相同，随后使用原 qrels 重算所有 k 的 Hole。

发布中的非空摘要排名用于独立复算覆盖表；其生成链与原始主排名应在数据来源记录中区分。该检查的可入选总体发生变化，不是随机干预或因果控制，也不是新文本表示、重新训练或新模型实验。由于采用既有向量和查询核验路径，不能把它描述为从零完整重跑。

## 复算路径和验证范围

在仓库根目录运行：

```bash
python3 scripts/analyze.py --output-dir results
```

此入口只用 Python 标准库，读取已打包的固定输入，重建覆盖、配对差值、观察 precision、严格界限、摘要分层及非空摘要敏感性表格。具体环境与核验命令以[仓库 README](../README.md)为准。输出字段直接来自输入计数和明确公式，不依赖历史论文的汇总表反推。

为了核查三方法 top-20 的标签缺口，另导出并集与 U 清单。每行表示查询—文档对；三个方法内的重复对合并，同文跨查询不合并。预期 top-20 并集为 2,170 对、U 为 492 对、U 涉及 461 篇独特文档。清单是待判断框架，不是已经取得的标注结果。

校验和能检查文件是否改变，不能保证事实真值；数值复算能检查固定输入的运算，不能证明模型检索全链已经重建；代码核验也不是人工专家同行评审。原始冻结、现存审计和当前复算记录分别保留，便于追踪每个结论的来源。

## 参考依据

- Rangreji、Zhong、Field：[The Effect of Document Selection on Query-focused Text Analysis](https://arxiv.org/abs/2604.12099v1)，2026，v1。仅借用其部分检索验证设定，具体歧义如上。
- Thakur 等：[BEIR](https://arxiv.org/pdf/2104.08663)，2021。§6、Table 4 为同库 Hole 与补评先例；§5、Figure 4 涉及长度偏好。
- NIST：[TREC-COVID 数据与评判说明](https://ir.nist.gov/covidSubmit/data.html)。本包使用其 BEIR 整理版本，不声称完整恢复两版本的 ID 与标签变换。
- Reimers、Gurevych：[Sentence-BERT](https://aclanthology.org/D19-1410/)，2019。框架论文与上述 MPNet checkpoint 来源分开引用。
