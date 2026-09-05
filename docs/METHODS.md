# 我的实验方法与复算定义

我在这里记录 12 个全查询配置、初始五查询实验和两个非空摘要配置的输入、评分与计算公式。快速复算以保存的排名为输入；原始语料到排名的模型运行配置另行列明，[检索源码附录](../retrieval_source/README.md)提供实际实现、依赖、原文件哈希和计算逻辑一致性检查。这样，读者可以按需要检查数据、排名生成或统计计算中的任一环节。

## 1. 数据、版本与排名

我使用 BEIR 版 TREC-COVID：171,332 篇文档、50 个查询、66,336 行 qrels。其中 66,334 个查询—文档对的标签为 0、1、2；Q38/`9hbib8b3` 和 Q50/`svo94kuo` 的原始标签为 −1。我原样保留 qrels，计算时将 −1 及缺少有效标签的对记为 U。

我把查询和文档 ID 作为字符串保存，以原语料顺序映射文档 ID，并保留排名中的 `rank`。12 个全查询配置每题各有 1000 个不同文档，共 600,000 条主排名。初始五查询材料有八个配置、40,000 条排名；其中 BM25、MPNet、Direct、Random Uniform、Direct min-max 按查询从已保存的全 50 题排名截取，MMR、Query Expansion、Retrieval Random 保留当时单独的五题运行。前五个配置的 25,000 条排名同时出现在主排名中。两个非空摘要配置另有 100,000 条。配置名、文件和排序语义集中列在[方法注册表](../data/method_registry.json)。历史 `SBERT` 在本版对应 `mpnet`。

我使用以下共同输入定义：

- **查询：**BEIR `queries.jsonl` 的自然语言 `text` 字段。
- **文档：**`title` 与 `text` 分别去除首尾空白；两者非空时拼为 `title + '. ' + text`，否则取非空字段。
- **摘要状态：**`text` 空值回退为空字符串，`strip()` 后为空即记为无摘要。全库无摘要 42,140 篇，非空摘要 129,192 篇。
- **文件版本：**原始查询、qrels、语料来源、元数据与排名由发布清单中的 SHA-256 固定。数据格式与获取入口见[数据说明](../data/README.md)。

## 2. 十二个检索与选择配置

以下参数定义我实际运行的实现。每个配置使用对应的输入和评分设置，结果比较以这一组已记录配置为单位。

| 配置 ID | 我的实现 |
|---|---|
| `bm25` | BM25Okapi；`k1=1.5, b=0.75, epsilon=0.25`；全库词项索引；取 top-1000。 |
| `mpnet` | `sentence-transformers/all-mpnet-base-v2`；768 维、最大 384 tokens；float32、L2 归一化向量点积；全库检索。 |
| `direct` | BM25 和 MPNet 各 top-1000 的并集；两组件分别除以候选集内最大分数后相加，取 top-1000。 |
| `direct_minmax` | 同样的候选构造；各组件采用 `(score−min)/(max−min)` 后相加，取 top-1000。 |
| `uniform_random` | 从全库均匀无放回抽取 1000 篇，保留抽样次序；种子 42；无检索评分。 |
| `direct_mmr` | 先产生 Direct top-5000；用 MPNet 余弦相似度和 `λ=0.3`，按贪心 MMR 顺序选取 1000 篇。 |
| `direct_mmr_rerank` | 在 Direct top-1000 集合内运行相同 MMR，输出全部 1000 篇的重排顺序。 |
| `query_expansion` | MPNet 的 KeyBERT 式关键词选择，diversity=0.7，每题最多五个关键词；原查询及关键词各运行 Direct top-1000，随后 weighted RRF，`k=60`。 |
| `retrieval_random` | 从 Direct top-5000 均匀无放回抽取 1000 篇，种子 42；按抽中文档在 Direct 候选池中的相对位置输出。 |
| `splade` | `naver/splade-cocondenser-ensembledistil`；最大 256 word-pieces；对 attention-mask 有效位置的 `log(1+relu(logits))` 做逐词汇维最大池化，按稀疏点积全库检索。 |
| `bge` | `BAAI/bge-base-en-v1.5`；768 维、最大 512 tokens；文档无指令前缀，查询前缀为 `Represent this sentence for searching relevant passages: `；L2 归一化向量点积，全库检索。 |
| `bm25_ce` | `cross-encoder/ms-marco-MiniLM-L-6-v2`；最大 512 tokens；对已保存 BM25 top-1000 的全部查询—文档对评分，再在同一集合内重排。 |

BM25 的分词顺序是小写、正则 `[a-z0-9]+`、NLTK 英文停用词 198 项、Porter stemming。查询采用相同处理，重复查询词累计贡献。IDF 定义为 `ln((N−df+0.5)/(df+0.5))`，负值替换为 `0.25 × 全词表平均 IDF`；全库平均词项长度约 113.296722。

我保存模型标识、输入设置和生成后的排名哈希。原生成程序按模型名加载；模型版本记录的精度见[来源说明](../provenance/README.md)。核心复算直接读取本版固定排名。MPNet、SPLADE、BGE、CrossEncoder 分别使用 384、256、512、512 的长度设置，这些设置与模型、前缀及评分方式一起构成本实验配置。

### Direct 的候选深度与归一化

对输出深度 n，我分别取得 BM25 top-n 和 MPNet top-n，组成并集，再计算融合分数并输出 n 篇。组件在并集内为所有候选计算分数；最大值为零的组件贡献零。

```text
max_sum(d) = BM25(d)/max(BM25) + MPNet(d)/max(MPNet)
minmax_sum(d) = (BM25(d)−min(BM25))/(max(BM25)−min(BM25))
              + (MPNet(d)−min(MPNet))/(max(MPNet)−min(MPNet))
```

min-max 中分母为零的组件贡献零。用于 MMR 和 Retrieval Random 的 Direct top-5000 以 `n=5000` 重新构造两个 top-5000 的并集，再选出 5000；其候选并集最多有 10,000 篇。常规 Direct 行使用 `n=1000`。

### MMR 的选择顺序

我先取与查询余弦相似度最高的候选作为首篇，然后迭代计算：

```text
MMR(d) = 0.3 × cosine(d,query)
       − 0.7 × max[cosine(d,a), a in already_selected]
```

每一步选择最高值，并列时选择在当前 Direct 候选池中位置最靠前的文档。输出 `rank` 是贪心选择顺序。保存的 `score` 为查询—文档余弦相似度，读者应直接使用 `rank` 复算 MMR 列表。

### Query Expansion 的实际关键词与权重

我先去除停用词，再形成去重的一元和二元短语候选。首个关键词取查询相似度最高者，后续按 diversity=0.7 的 MMR 选择，最多五个。实际运行中 Q1 和 Q32 各有三个关键词，其余查询各五个，完整列表见[全查询关键词](../data/experiment_metadata/query_expansion_keywords_full50.json)和[五查询关键词](../data/experiment_metadata/query_expansion_keywords_pilot.json)。

原查询权重为 0.5；若实际关键词数为 t，每个关键词权重为 `0.5/t`。每个查询文本或关键词产生一份 Direct top-1000，文档从所在列表的名次获得 `weight/(60+rank)`，跨列表求和后取 top-1000。

### 随机协议与并列规则

我为每种随机方法各建一个种子为 42 的 NumPy Generator，按查询 ID 数值升序推进随机流。Random Uniform 保留抽样次序；Retrieval Random 抽取文档集合后，按 Direct 候选池位置升序排列。后者的前列评价同时取决于抽样集合和保留的 Direct 顺序。

Retrieval Random 的五查询与 50 查询运行分别推进随机流，同一查询因此对应不同的抽样；五题的平均 top-1000 集合重合率为 0.1902。Random Uniform 的五查询材料则直接截取同一全 50 查询运行，两者在对应查询上完全一致。发布中各阶段的保存排名分别作为该阶段的复算输入。MMR 和 Query Expansion 的五查询确定性结果另有跨阶段对应记录。

一般按评分排序的配置采用分数降序、原语料索引升序打破并列；MMR 使用上文的候选池位置规则，Random Uniform 使用抽样次序。浮点评分与名次的固定值以本版排名文件为准。

## 3. 判断覆盖、集合与观察相关性

对查询 q、文档 d，我定义 `J(q,d)=1` 当且仅当原 qrel 属于 `{0,1,2}`，其余为 0，显示标签为 U。每个方法 m 的固定 top-k 集合记为 `S(m,q,k)`。

```text
Hole(m,q,k) = count(U in S(m,q,k)) / k
Judged(m,q,k) = 1 − Hole(m,q,k)
mean_Hole(m,k) = sum[Hole(m,q,k), q in the query set] / number_of_queries
```

我发布 @20、@50、@100、@1000 的结果。主全查询表使用全部 50 个查询；五查询表使用其对应五题。每题恰有 k 条，因而这些覆盖率的查询平均与全部检索位置汇总比例相等。

对同深度集合 A 和 B，我计算 `|A∩B|/k` 的重合率及 `|A∩B|/|A∪B|` 的 Jaccard，并分别计数交集、A 独有和 B 独有文档的判断状态。摘要分层同样按每种方法实际检索到的文档分组。分层表分别记录总数、pooled 比例和有非空分母的查询；跨层与跨方法计算使用各自分母。

候选成员分析把各配置返回的文档分成“在该查询已保存的 BM25 top-1000 内”与“在其外”。我将候选深度固定在 1000，使读者能够直接核查成员关系。集合保持检查逐题比较 BM25 与 BM25 + CrossEncoder、Direct 与 MMR rerank 的 top-1000 集合。

### 观察 precision 与 recall

主相关性规则为 `strict_eq2`：qrel=2 计相关。`relaxed_ge1` 作为补充，把 1、2 均计相关。U 在观察指标中贡献零个已知相关命中，其数据状态仍为 U。

```text
P_observed(m,q,k) = count(existing relevant labels in S(m,q,k)) / k
Recall_observed(m,q,1000)
    = count(existing relevant labels in S(m,q,1000))
      / count(existing relevant labels for q in the qrels)
```

我将两个阈值分别写入输出行。计算 recall 时，分母对应同一查询和同一相关性规则。正文中的“观察”指现有 qrels 确认的相关项；标签补全后的 precision 另由下一节界定。

## 4. 配对 precision 的严格可达界限

我固定当前排名和已有标签，允许每个 U 在所选相关性阈值下取 0 或 1，并让同一查询—文档对在各方法间共享标签。对两个固定 top-k 集合 A、B，令 `δ_obs=P_obs(A)−P_obs(B)`，`U_Aonly` 和 `U_Bonly` 分别为 A、B 独有的 U 数。

```text
lower(q) = δ_obs(q) − U_Bonly(q)/k
upper(q) = δ_obs(q) + U_Aonly(q)/k
mean_lower = average[lower(q)]
mean_upper = average[upper(q)]
```

共享 U 的贡献在差值中抵消。把 B 独有 U 全设为相关、A 独有 U 全设为不相关，即达到下界；反向赋值达到上界。同一文档在不同查询下对应不同的相关性标签。每个配对区间的端点分别可达，计算条件是固定列表、既有标签不变，以及 U 可任意二值补全。

我在三基线深入分析中发布 MPNet−BM25、Direct−BM25、MPNet−Direct 三组；扩展分析发布其余 11 个配置分别相对 BM25 的比较。所有比较覆盖 @20、@100 和两个相关性规则。这些区间表示未知标签赋值的范围；使用它们时应保持相同的排名与相关性定义。

## 5. 非空摘要条件与 top-20 清单

我从原全库筛出 `text.strip()` 非空的 129,192 篇文档，再在该集合内按既有评分定义分别取 BM25、MPNet top-1000。BM25 使用原全库索引的词频、IDF 和平均文档长度；MPNet 使用既有文档向量与对应查询向量。随后在筛选后的完整 top-k 中计算覆盖。

该实验比较不同的可入选文档总体，保持每题 k 的分母和已有评分定义。发布中两种非空摘要排名与主排名分别存放，便于独立复算和追踪来源。

我另对 BM25、MPNet、Direct 的 top-20 建立查询—文档对并集。同一查询内跨方法合并重复对；同一文档跨查询分别保留。该并集为 2,170 对，其中 U 为 492 对，涉及 461 篇不同文档。清单记录现有判断状态和方法名次；其覆盖范围是这三个基线的 top-20。[清单](../results/top20_unjudged_frame.csv)

## 6. 如何运行与核验

在仓库根目录运行：

```bash
python3 scripts/analyze.py --output-dir build/results
python3 scripts/analyze_extensions.py --data-dir data --output-dir build/results/extensions
python3 scripts/verify_release.py
```

第一个脚本重算三个基线的深入分析和两个非空摘要配置；第二个脚本重算 12 个全查询配置与八个五查询配置，并产生下列结果：

| 文件组，位于 `results/extensions/` | 计算内容 |
|---|---|
| `coverage_*`、`observed_ir_*` | 全查询覆盖、观察 P@20 与 Recall@1000 |
| `pilot_coverage_*`、`pilot_observed_ir_*` | 五查询阶段的覆盖与观察指标 |
| `pilot_full50_overlap_*` | 五查询与全查询阶段的集合重合及名次对应 |
| `overlap_vs_bm25_*` | 各配置相对 BM25 的集合重合 |
| `judged_shared_exclusive_*` | 共享及独有文档的判断覆盖分层 |
| `bm25_candidate_membership_*` | BM25 top-1000 内外的返回文档组成 |
| `paired_precision_bounds_*` | 相对 BM25 的配对 precision 严格可达界限 |
| `set_invariance_checks.csv` | 固定候选集重排的逐查询集合检查 |
| `reproduction_checks.json` | 本次计算的输入、数量与检查记录 |

`*_by_query.csv` 保留逐查询记录，`*_summary.csv` 汇总这些结果。`verify_release.py` 在临时目录重新计算并比较发布文件，同时检查哈希、程序测试和文档来源。本次实际执行结果见[验证记录](../provenance/RELEASE_VALIDATION.md)。

我将验证范围分成三层：文件哈希记录具体版本；固定输入复算核查统计计算；生成配置与源代码记录原始排名的产生过程。离线结果复算使用标准库和本版小型输入，原语料获取和模型运行则按其单独记录的依赖与来源执行。

## 7. 参考来源

- Rangreji、Zhong、Field：[The Effect of Document Selection on Query-focused Text Analysis](https://arxiv.org/abs/2604.12099v1)，文档选择方法与检索验证的复现起点。
- Thakur 等：[BEIR](https://arxiv.org/abs/2104.08663)，基准版本与判断覆盖的评估背景。
- NIST：[TREC-COVID 数据说明](https://ir.nist.gov/covidSubmit/data.html)，原始任务与判断资料。
- Reimers、Gurevych：[Sentence-BERT](https://aclanthology.org/D19-1410/)，句向量框架来源；具体 checkpoint 为上述 MPNet 模型。
- 模型卡：[MPNet](https://huggingface.co/sentence-transformers/all-mpnet-base-v2)、[SPLADE](https://huggingface.co/naver/splade-cocondenser-ensembledistil)、[BGE](https://huggingface.co/BAAI/bge-base-en-v1.5)、[CrossEncoder](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2)。
