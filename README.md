# TREC-COVID Document-Selection Experiments

Reproducible document-selection experiments on the BEIR version of TREC-COVID, covering **171,332 documents, all 50 queries, and 12 retrieval / selection configurations**.

This repository contains fixed rankings, evaluation code, result tables, figures, and provenance records for studying how retrieval choices affect **judgment coverage** and observed retrieval effectiveness.

**Release:** v2.0.0 · 2026-09-05  
**Author:** Rongrong Liu

[Research Note](docs/RESEARCH_NOTE.md) · [Methods](docs/METHODS.md) · [Contributions and Tool Use](docs/CONTRIBUTIONS.md)

## Overview

The experiments compare the documents selected by different retrieval and reranking methods and measure how much of each ranked output is covered by the existing TREC-COVID relevance judgments.

The release includes:

- fixed top-1000 rankings for 12 retrieval and selection configurations;
- all 50 BEIR TREC-COVID queries and the corresponding qrels;
- document metadata used by the analyses;
- coverage and observed retrieval metrics at multiple cutoffs;
- document-set, abstract-availability, and fixed-candidate reranking analyses;
- paired precision bounds for rankings containing unjudged documents;
- offline analysis and verification scripts.

The main release contains **600,000 ranking records** across the 12 configurations. Including the earlier five-query stage and nonempty-abstract experiments, the repository contains **740,000 saved ranking positions**.

## Main Results

All values are equally weighted means over the 50 queries.

`Hole@k` is the proportion of retrieved documents without an existing relevance judgment. `Observed P@20` treats `qrel=2` as relevant and unjudged documents as not observed relevant.

| Method / configuration | Hole@20 | Hole@100 | Observed P@20 |
|---|---:|---:|---:|
| BM25 | 0.0720 | 0.1960 | 0.487 |
| MPNet | 0.4030 | 0.4918 | 0.426 |
| Direct: max-sum | 0.0540 | 0.1464 | 0.630 |
| Direct: min-max | 0.0570 | 0.1508 | 0.628 |
| Random Uniform | 0.9960 | 0.9934 | 0.001 |
| Direct + MMR: select 1000 from 5000 | 0.8510 | 0.8760 | 0.035 |
| Direct + MMR: rerank existing 1000 | 0.6600 | 0.6630 | 0.078 |
| Query Expansion | 0.0600 | 0.1570 | 0.622 |
| Retrieval Random | 0.1470 | 0.4228 | 0.503 |
| SPLADE | 0.1080 | 0.2636 | 0.600 |
| BGE | 0.1180 | 0.2788 | 0.668 |
| BM25 + CrossEncoder | 0.0880 | 0.2416 | 0.581 |

Full results are available in:

- [coverage_summary.csv](results/extensions/coverage_summary.csv)
- [observed_ir_summary.csv](results/extensions/observed_ir_summary.csv)
- [paired_precision_bounds_summary.csv](results/extensions/paired_precision_bounds_summary.csv)

The exact model inputs, normalization choices, candidate pools, prefixes, and scoring settings are documented in [METHODS.md](docs/METHODS.md). Results should therefore be interpreted as properties of these specific configurations on this benchmark rather than as generic properties of model families.

### Selected observations

**Judgment coverage can differ substantially even within the same broad retrieval family.**  
For example, BGE and MPNet have Hole@20 values of 0.118 and 0.403, respectively.

**Candidate selection and reranking should be distinguished.**  
BM25 + CrossEncoder preserves the complete BM25 top-1000 document set, so set-level coverage and recall at @1000 remain unchanged while prefix metrics change after reranking. The two MMR configurations similarly separate selection from a larger candidate pool from reranking a fixed set.

**Document eligibility affects measured coverage.**  
When the top-20 documents are reselected from documents with nonempty abstracts using the existing scores, the MPNet–BM25 Hole@20 difference decreases from 33.1 to 16.2 percentage points.

**Unjudged documents do not always make pairwise conclusions indeterminate.**  
Under `qrel=2` relevance, the sharp mean Direct−BM25 P@20 interval is **[0.092, 0.176]**. The corresponding intervals for BGE−BM25, SPLADE−BM25, and BM25 + CrossEncoder−BM25 are also entirely positive.

![Judgment coverage and observed P@20 across twelve configurations](figures/method_comparison.png)

A second figure with the three-baseline analysis, abstract-eligibility condition, and paired bounds is available at [figures/research_summary.png](figures/research_summary.png).

## Reproduction

Python **3.9+** is required.

Run the complete offline verification from the repository root:

```bash
python3 scripts/verify_release.py
```

This verifies release-file hashes, recomputes the released result tables in a temporary directory, compares regenerated outputs with the frozen release, runs input-validation and computational-semantics tests, and checks documentation and figure-source references.

The current release contains:

- 34 regenerable result files;
- 10,274 numerical comparisons against frozen historical outputs;
- 21 tests.

The validation record is available in [provenance/RELEASE_VALIDATION.md](provenance/RELEASE_VALIDATION.md).

To regenerate the analysis outputs:

```bash
python3 scripts/analyze.py --output-dir build/results
python3 scripts/analyze_extensions.py \
  --data-dir data \
  --output-dir build/results/extensions
```

The first script reproduces the detailed three-baseline and nonempty-abstract analyses. The second reproduces coverage, observed retrieval metrics, and set analyses for the 12 full-query configurations and the earlier five-query experiments.

Offline reproduction uses the released rankings. Ranking-generation configurations and implementation provenance are documented in [retrieval_source/README.md](retrieval_source/README.md) and [docs/METHODS.md](docs/METHODS.md).

### Figures

Install the optional plotting dependencies:

```bash
python3 -m pip install -r requirements-figures.txt
```

Then regenerate the figures:

```bash
python3 scripts/plot_results.py \
  --results-dir build/results \
  --output-dir build/figures
```

## Repository Guide

| Path | Contents |
|---|---|
| [docs/RESEARCH_NOTE.md](docs/RESEARCH_NOTE.md) | Research questions, experimental stages, interpretation, and full analysis |
| [docs/METHODS.md](docs/METHODS.md) | Method configurations, formulas, label semantics, randomization, and reproduction levels |
| [docs/CONTRIBUTIONS.md](docs/CONTRIBUTIONS.md) | Author contributions and AI-assistance statement |
| [retrieval_source/](retrieval_source/) | Ranking-generation implementations and run configurations |
| [data/](data/) | Queries, qrels, document metadata, formats, and data provenance |
| [results/](results/) | Frozen result tables and derived analyses |
| [figures/](figures/) | Released figures |
| [scripts/](scripts/) | Analysis, verification, and plotting entry points |
| [tests/](tests/) | Input-validation and computational-semantics tests |
| [provenance/](provenance/) | Validation records, hashes, configuration history, and version correspondence |
| [archive/](archive/) | Historical materials retained from earlier stages |

The primary relevance definition used in the README and main bounds is `label_rule=strict_eq2`. Results under `relaxed_ge1` are provided separately as a supplementary threshold.

## Research Context

This work started from a reimplementation of the document-selection study by Rangreji, Zhong, and Field and uses BEIR/TREC-COVID as the evaluation setting.

The repository focuses specifically on the reproducible experimental artifact: retrieval outputs, judgment coverage, observed metrics, document-set analyses, and uncertainty induced by unjudged labels.

References to the upstream work, datasets, and their relationship to the experiments are documented in [docs/RESEARCH_NOTE.md](docs/RESEARCH_NOTE.md) and [data/README.md](data/README.md).

## Citation

Citation metadata is provided in [CITATION.cff](CITATION.cff).

If you use this release, please cite the archived release corresponding to the version used. A Zenodo DOI can be added here after the GitHub release is archived.

## License

See [LICENSE](LICENSE) and [LICENSE-CODE.txt](LICENSE-CODE.txt) for the licensing scope of the repository and included materials.

Third-party datasets and upstream resources remain subject to their original terms.
