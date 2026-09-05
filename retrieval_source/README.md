# My Retrieval Implementations

I provide the core code used to generate the original rankings, retaining the relative structure of `src/` and the supplementary experiment directory. Readers can follow the method descriptions directly to the scoring, candidate construction, selection, and output procedures.

Using source-project version `e5d96e11b5b282998a509580be625099f86a70f4` as the basis, I standardized the wording of comments and docstrings and changed one descriptive `reason` metadata value in the MMR reranking program to describe the actual configuration. Computational statements retain their original logic. [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) records each file's source path, original file hash, release file hash, and syntax-tree comparison. The complete original version remains preserved in the project's historical materials.

## Implementations I Provide

| File | Contents available for inspection |
|---|---|
| [common.py](src/common.py) | Data paths, parameters, title/abstract representation, tokenization, and query and qrel loading |
| [bm25_index.py](src/bm25_index.py) | Sparse BM25Okapi, IDF and term-frequency scoring, and comparison with the reference implementation under specified tolerances |
| [build_artifacts.py](src/build_artifacts.py) | Corpus ID order, tokenization cache, BM25 index, and MPNet document vectors |
| [retrieval.py](src/retrieval.py) | BM25, MPNet, the two Direct normalizations, random selection, MMR, and Query Expansion |
| [run_retrieval.py](src/run_retrieval.py) | Full 50-query runs of the basic methods and Direct min-max, with NPZ output |
| [run_secondary.py](src/run_secondary.py) | Separate five-query runs of the three supplementary selection methods |
| [ext_common.py](extension_retrieval_methods/scripts/ext_common.py) | Supplementary experiment paths, model identifiers, run output, and resource records |
| [run_tier_a.py](extension_retrieval_methods/scripts/run_tier_a.py) | 50-query runs of the three supplementary methods and checks against their corresponding five-query results |
| [run_tier_b.py](extension_retrieval_methods/scripts/run_tier_b.py) | SPLADE and BGE indexing/encoding and retrieval, and BM25 + CrossEncoder reranking |
| [run_mmr_variant.py](extension_retrieval_methods/scripts/run_mmr_variant.py) | Complete MMR reranking within the Direct top-1000 set |
| [requirements.txt](requirements.txt) | The complete dependency-version list recorded for the original runtime environment |

The ten Python files include all local Python imports among the selected programs. The correspondence between model configurations, ordering semantics, and released results is described in the [methods documentation](../docs/METHODS.md) and [method registry](../data/method_registry.json). The definition and saved rankings of the supplementary nonempty-abstract experiment are also listed separately in that documentation and the data directory.

## Source Verification and Result Reproduction

I performed three checks for the source release: SHA-256 hashes of the original and released files, syntax compilation of all ten Python files, and comparison of abstract syntax trees after removing docstrings. For the sole change to descriptive metadata, the comparison normalizes only the `reason` string within the `dict` argument of `save_run` to a shared placeholder. The manifest records this location, the hash of the original value, and the released value individually. The remaining executable syntax trees are identical.

From the repository root, the released files can be checked again with:

```bash
python3 retrieval_source/verify_source.py
```

Readers with access to the original project can also provide `--source-root` to check the original file hashes and compare the original and released syntax trees directly. These checks parse and compile the source without executing model construction.

The result reproduction performed for this release takes the saved rankings and original labels as input. Its entry point remains:

```bash
python3 scripts/verify_release.py
```

It reconstructs the result tables using the standard library; this directory provides the original method implementations that generated those rankings. The complete execution record is available in the [release validation](../provenance/RELEASE_VALIDATION.md).

## Environment and Input Conventions for Original Ranking Generation

The recorded original runtime environment is Python 3.11.15 on macOS arm64. The principal direct dependencies include NumPy, SciPy, pandas, NLTK, PyTorch, sentence-transformers, transformers, and rank-bm25; their specific versions appear in the original dependency list in this directory. NLTK English stopwords are a separately acquired data resource. Models are downloaded from their respective services. The original construction calls load models by name without passing a revision hash. Input lengths, prefixes, and the fixed versions of saved rankings are documented in the [methods documentation](../docs/METHODS.md).

I retain the code's original relative-path conventions:

- `src/common.py` treats this directory as the original project root and reads the adjacent `trec-covid/` directory, which must contain `corpus.jsonl`, `queries.jsonl`, and `qrels/test.tsv`. Public data acquisition is described in the [data documentation](../data/README.md).
- The basic run entry points read the `query_id` column in `config/queries_stage1.csv`. The corresponding five queries in this release are 9, 13, 34, 45, and 48, listed in the [five-query file](../data/pilot_queries.csv).
- `build_artifacts.py` builds the corpus ID, title, and tokenization caches, the BM25 index, and the MPNet vectors. The basic methods and three five-query selection methods subsequently save NPZ files in the original format.
- `run_tier_a.py` reads these existing indices/vectors and uses the three five-query NPZ files to check cross-stage correspondence. `run_tier_b.py` reads the existing corpus ID mapping and BM25 NPZ, then generates rankings for the supplementary models.
- The model code selects MPS or CPU according to the environment. Memory units in the resource-statistics functions are interpreted according to the original macOS environment. Acquisition and construction of models, the full-text corpus, and index/vector caches belong to the ranking-generation stage.

This directory preserves inspectable method implementations and the original input conventions. Verification for this release covers source equivalence and recalculation of results from saved rankings. Readers wishing to regenerate rankings from the full-text corpus can prepare a separate generation directory using the dependencies and paths described above.
