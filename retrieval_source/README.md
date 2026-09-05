# 我的检索实现源码

我在这里提供生成原始排名所用的核心代码，保留 `src/` 与补充实验目录的相对结构，方便读者从方法说明直接查看评分、候选构造、选择和保存过程。

我以源项目版本 `e5d96e11b5b282998a509580be625099f86a70f4` 为基础，统一了注释与文档字符串的表述，并把 MMR 重排程序的一项描述性 `reason` 元数据改为实际配置说明。计算语句保持原有逻辑。每个文件的来源路径、原文件哈希、发布文件哈希和语法树比较记录保存在 [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)。原始完整版本继续保留在项目历史材料中。

## 我提供哪些实现

| 文件 | 可以查看的内容 |
|---|---|
| [common.py](src/common.py) | 数据路径、参数、标题/摘要表示、分词、查询和 qrels 读取 |
| [bm25_index.py](src/bm25_index.py) | 稀疏 BM25Okapi、IDF 与词频计分、给定容差下的参考实现比较 |
| [build_artifacts.py](src/build_artifacts.py) | 语料 ID 顺序、分词缓存、BM25 索引、MPNet 文档向量 |
| [retrieval.py](src/retrieval.py) | BM25、MPNet、Direct 两种归一化、随机选择、MMR 与 Query Expansion |
| [run_retrieval.py](src/run_retrieval.py) | 基本方法与 Direct min-max 的全部 50 查询运行与 NPZ 保存 |
| [run_secondary.py](src/run_secondary.py) | 三个补充选择方法的单独五查询运行 |
| [ext_common.py](extension_retrieval_methods/scripts/ext_common.py) | 补充实验路径、模型标识、运行保存与资源记录 |
| [run_tier_a.py](extension_retrieval_methods/scripts/run_tier_a.py) | 三个补充方法的 50 查询运行，以及对应五查询结果检查 |
| [run_tier_b.py](extension_retrieval_methods/scripts/run_tier_b.py) | SPLADE、BGE 的索引 / 编码与检索，以及 BM25 + CrossEncoder 重排 |
| [run_mmr_variant.py](extension_retrieval_methods/scripts/run_mmr_variant.py) | 在 Direct top-1000 集合内输出完整 MMR 重排顺序 |
| [requirements.txt](requirements.txt) | 原运行环境记录的完整依赖版本清单 |

十个 Python 文件包含所选程序之间的全部本地 Python 导入。模型配置、排序语义与发布结果对应见[方法说明](../docs/METHODS.md)和[方法注册表](../data/method_registry.json)。非空摘要补充实验的定义与保存排名也在上述说明和数据目录中单独列出。

## 源码核验与结果复算

我为源码发布做了三项检查：原文件和发布文件 SHA-256、全部十个 Python 文件的语法编译，以及移除文档字符串后的抽象语法树比较。对于唯一改变的描述性元数据，比较仅将 `save_run` 的 `dict` 参数内 `reason` 字符串规范为同一占位值；该位置、原值哈希和发布值在清单中逐项记录。其余可执行语法树一致。

在仓库根目录可重复检查已发布文件：

```bash
python3 retrieval_source/verify_source.py
```

若持有原项目，还可向该脚本提供 `--source-root`，直接核查原文件哈希和原始 / 发布语法树。上述检查只解析和编译源码，不执行模型构建。

本版已经执行的结果复算以保存排名和原始标签为输入，入口仍为：

```bash
python3 scripts/verify_release.py
```

它使用标准库重建结果表；本目录用于追踪这些排名的原始方法实现。完整执行记录见[本版验证](../provenance/RELEASE_VALIDATION.md)。

## 原始生成流程的环境与读取约定

原运行环境记录为 Python 3.11.15、macOS arm64，主要直接依赖包括 NumPy、SciPy、pandas、NLTK、PyTorch、sentence-transformers、transformers 和 rank-bm25；具体版本见本目录的原始依赖清单。NLTK English stopwords 是另行获取的数据资源。模型由对应服务下载，原构造调用按模型名称加载，未传入 revision 哈希。输入长度、前缀和已保存排名的固定版本见[方法说明](../docs/METHODS.md)。

我保留代码原有的相对路径约定：

- `src/common.py` 把本目录视为原项目根目录，读取与其相邻的 `trec-covid/`，其中需要 `corpus.jsonl`、`queries.jsonl` 与 `qrels/test.tsv`。公开数据获取方式见[数据说明](../data/README.md)。
- 基础运行入口读取 `config/queries_stage1.csv` 的 `query_id` 列。发布中的对应五题为 9、13、34、45、48，保存在[五查询列表](../data/pilot_queries.csv)。
- `build_artifacts.py` 建立语料 ID、标题和分词缓存、BM25 索引与 MPNet 向量；随后基本方法和三种五题选择方法保存原格式 NPZ。
- `run_tier_a.py` 读取这些已有索引 / 向量，并使用三个五查询 NPZ 检查跨阶段对应关系。`run_tier_b.py` 读取已有语料 ID 映射与 BM25 NPZ，再生成补充模型的排名。
- 模型代码按环境选择 MPS 或 CPU；资源统计函数中的内存单位按原 macOS 环境解释。模型、全文语料和索引 / 向量缓存的获取与构建属于排名生成步骤。

这个目录保存可检查的方法实现与原始读取约定；本次发布核验覆盖源码一致性和保存排名到结果的复算。需要从全文语料重新生成排名时，可依据上述依赖和路径准备独立的生成工作目录。
