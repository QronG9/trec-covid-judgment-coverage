# 我保存的数据与实验运行

我使用 BEIR 分发的 TREC-COVID：171,332 篇文档、50 个查询、66,336 行原始
判断记录。我把文档标识、保存的排序和原始判断分开存放，使每个统计结果都能
回到具体查询、文档和名次。

## 数据清单

| 文件 | 我保存的内容 | 用途 |
|---|---|---|
| `trec-covid/queries.jsonl` | 原样保存的 50 个查询 | 查询文本及 ID |
| `trec-covid/qrels/test.tsv` | 原样保存的判断记录 | 0、1、2、−1 标签 |
| `corpus_metadata.csv.gz` | 全语料 ID、顺序、标题/摘要可用性及字符数 | 数据检查及表示敏感性 |
| `runs/{bm25,mpnet,direct}.tsv.gz` | 初始三个方法，各 50×1000 行 | 基础比较 |
| `runs/extensions/*.tsv.gz` | 其余九个全量配置，各 50×1000 行 | 归一化、随机、MMR、扩展、稀疏、向量及重排比较 |
| `runs/pilot/*.tsv.gz` | 八个初始配置，各 5×1000 行 | 保留早期实验状态 |
| `runs/nonempty_abstract/*.tsv.gz` | BM25、MPNet 非空摘要条件，各 50×1000 行 | 可入选总体敏感性 |
| `method_registry.json` | 12 个配置的名称、类别、文件和排序语义 | 程序与文档共用的配置清单 |
| `pilot_queries.csv` | 查询 9、13、34、45、48 | 初始实验查询范围 |
| `experiment_metadata/` | 初始及 50 查询实验实际使用的关键词 | Query Expansion 的输入记录 |

全量配置共保存 **600,000 个排序位置**；加上初始实验的 40,000 行和非空摘要
条件的 100,000 行，共 740,000 行。这些是不同配置和阶段中的位置记录，存在共享文档；五查询材料中的五个基础配置取自全查询排名的对应子集。

我把原 numpy 排名转换为 `query_id, doc_id, rank, score` 四列 TSV，使用确定性
gzip 压缩。有限分数保留 17 位有效数字，文档顺序保持原样。Random Uniform
原本没有相关性分数，我用空字符串保留这一状态；其名次是抽样顺序。MMR
文件的分数是查询—文档余弦值，名次是贪心选择顺序，读取时按 `rank` 使用。
Retrieval Random 从候选池抽取子集后保留 Direct 的相对顺序。

元数据列为 `corpus_index, doc_id, has_title, has_abstract, title_chars,
abstract_chars`。索引从 0 开始；布尔量为 0/1；字符计数和可用性由原字符串
去除首尾空白后计算。我保留了原始 BEIR 文件的字节与换行格式。

## 我采用的标签定义

0、1、2 为有效判断；−1 和没有记录的查询—文档对属于 U。计算观察 P@k 时，
我用已知达到相关阈值的命中数除以 k，并把该指标与判断覆盖率分别保存。
正文使用 QREL=2；QREL≥1 作为独立阈值行保存。

## 来源与许可

我引用并保留以下数据来源的署名：

- [BEIR 论文](https://arxiv.org/abs/2104.08663)及[官方数据列表](https://github.com/beir-cellar/beir)。
- [BEIR TREC-COVID 数据卡](https://huggingface.co/datasets/BeIR/trec-covid)，标注为 CC BY-SA 4.0。
- [NIST TREC-COVID](https://ir.nist.gov/covidSubmit/)，提供底层评估任务。
- [CORD-19](https://github.com/allenai/cord19)，提供底层科学文献集合；文章保留各自来源的权利。
- [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)。

我原样保存查询和判断文件，将语料转换为标识及数值元数据，将实验缓存转换
为 TSV，再重新计算汇总结果。公开 Git 文件包含这些可直接复算的材料；文章
标题/摘要全文、模型权重及大型向量缓存保留在本地或按原始来源获取。

## 从原始语料检查元数据

```bash
python3 scripts/fetch_corpus.py
# 我也可以使用已经下载的原始 BEIR 压缩包：
python3 scripts/fetch_corpus.py --archive /path/to/trec-covid.zip
# 本地已有语料时：
python3 scripts/fetch_corpus.py --verify-only
```

程序检查 BEIR 包的 MD5 `ce62140cb23feb9becf6270d0d1fe6d1`、三个原始文件的
SHA-256，并从语料重新生成元数据进行比较。[输入哈希](../provenance/import_inputs.json)
记录了这些来源。日常结果复算直接读取本仓库的小型输入，可离线执行。

