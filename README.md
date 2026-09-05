# TREC-COVID Document-Selection Experiments: Method Reimplementation and Evaluation

**Author: QronG9 · v2.0.0 · 2026-09-05**

**Start here: [My Research Note](docs/RESEARCH_NOTE.md)** · [Methods and Computational Definitions](docs/METHODS.md) · [My Contributions](docs/CONTRIBUTIONS.md)

I conducted a series of reproducible experiments to examine which documents different selection methods retrieve and how much of their output can be evaluated using existing relevance judgments. Using **171,332 documents and all 50 queries** in the BEIR version of TREC-COVID, I reimplemented retrieval methods, saved their rankings, and calculated judgment coverage and observed retrieval metrics separately. This repository brings together my initial five-query experiments, frozen baselines evaluated on all queries, and subsequent method extensions and evaluation analyses.

I release **fixed top-1000 rankings for each query in 12 retrieval and selection configurations**, together with the original queries, qrels, document metadata, analysis code, and result tables. Including the five-query stage and nonempty-abstract experiments, this version contains **740,000 saved ranking positions**. Readers can recompute the results offline and examine each experimental stage through the method configurations and provenance records.

**Summary:** I reimplemented document-selection methods and evaluated 12 retrieval and selection configurations on all 50 BEIR TREC-COVID queries. I report judgment coverage and observed retrieval effectiveness separately, examine document eligibility and fixed-candidate reranking, and compute sharp paired precision bounds. This repository includes saved rankings, original judgments, analysis code, and reproducible outputs from my initial experiments and subsequent extensions.

## My Experiments and Outputs

| Work | Verifiable materials I release |
|---|---|
| Method reimplementation and extension | BM25, MPNet, two Direct normalization variants, two forms of random selection, Query Expansion, two MMR settings, SPLADE, BGE, and BM25 + CrossEncoder; 600,000 main ranking records in total |
| Evaluation across all queries | Coverage and observed relevant proportions at @20, @50, @100, and @1000 for 12 configurations, together with P@20, Recall@1000, and per-query tables |
| Document-set analysis | Set overlap between methods, set strata relative to BM25, document composition inside and outside BM25 top-1000, and set-invariance checks for fixed-candidate reranking |
| Document-availability analysis | Title-and-abstract input definitions, stratification by abstract availability, and reselection of top-ranked BM25/MPNet documents from all corpus documents with nonempty abstracts |
| Analysis of unjudged labels | Sharp bounds on paired precision differences for fixed lists, and an inventory of 492 unjudged query–document pairs in the top-20 union of the three baselines |
| Reproducible release | Portable compressed rankings, a data dictionary, versions and hashes, standard-library analysis entry points, tests, and GitHub Actions |

## Main Results

All values below are **equally weighted means over 50 queries**. Hole is the unjudged proportion; observed P@20 treats `qrel=2` as relevant, while U contributes no relevant hits in this calculation. These metrics address two distinct questions: how much output is covered by judgments, and how many relevant items the existing labels confirm.

| Method / experimental configuration | Hole@20 | Hole@100 | Observed P@20 |
|---|---:|---:|---:|
| BM25 | 0.0720 | 0.1960 | 0.487 |
| MPNet | 0.4030 | 0.4918 | 0.426 |
| Direct: max-sum | 0.0540 | 0.1464 | 0.630 |
| Direct: min-max | 0.0570 | 0.1508 | 0.628 |
| Random Uniform | 0.9960 | 0.9934 | 0.001 |
| Direct + MMR: select 1000 from 5000 | 0.8510 | 0.8760 | 0.035 |
| Direct + MMR: rerank the existing 1000 | 0.6600 | 0.6630 | 0.078 |
| Query Expansion | 0.0600 | 0.1570 | 0.622 |
| Retrieval Random | 0.1470 | 0.4228 | 0.503 |
| SPLADE | 0.1080 | 0.2636 | 0.600 |
| BGE | 0.1180 | 0.2788 | 0.668 |
| BM25 + CrossEncoder | 0.0880 | 0.2416 | 0.581 |

I recompute both Direct normalization configurations alongside the other methods. Sources: [coverage summary for all configurations](results/extensions/coverage_summary.csv) and [observed retrieval metrics](results/extensions/observed_ir_summary.csv). The [methods documentation](docs/METHODS.md) maps names to configurations. Models use their respective recorded input lengths, prefixes, and scoring settings; I interpret the differences as the performance of these specific configurations on this fixed benchmark.

I identify four observations that can be checked directly against these results:

- **Methods within the same family can produce different results.** BGE and MPNet both use dense-vector retrieval, with Hole@20 values of 0.118 and 0.403, respectively. I therefore report results by specific model and configuration.
- **Candidate sets and ranking prefixes can be examined separately.** BM25 + CrossEncoder retains the entire BM25 top-1000 set, so their coverage and recall at @1000 are identical; prefix metrics change with reranking. The two MMR settings further distinguish selection from a larger pool from reranking the same set.
- **Document eligibility is associated with coverage.** When I reselect the top-20 from all corpus documents with nonempty abstracts using the existing scores, the MPNet−BM25 Hole difference changes from 33.1 to 16.2 percentage points. I also release the filtering definition, rankings, and stratified counts.
- **The effect of unknown labels can be bounded exactly for fixed rankings.** With existing labels retained and QREL=2, the sharp range for the mean Direct−BM25 P@20 difference is **[0.092, 0.176]**, which is entirely positive. Among the additional configurations, the intervals for BGE−BM25, SPLADE−BM25, and BM25 + CrossEncoder−BM25 are also entirely positive; see the [extended bounds table](results/extensions/paired_precision_bounds_summary.csv).

![My twelve document-selection configurations: judgment coverage and observed P@20](figures/method_comparison.png)

All configurations use the same 50 queries. The [detailed three-baseline figure](figures/research_summary.png) further presents the abstract-eligibility condition and paired bounds.

## Quick Reproduction

Python **3.9 or later** is required. Run the following from the repository root:

```bash
python3 scripts/verify_release.py
```

I implemented the core analysis as an offline workflow that uses only the Python standard library. The verification entry point checks release-file hashes, recomputes results in a separate temporary directory and compares them byte for byte with the released tables, runs input-validation and computational-semantics tests, and checks documentation links and figure sources. This version includes 34 regenerable result files, 10,274 numerical comparisons with historical outputs, and 21 tests. The record of this validation run is available in [RELEASE_VALIDATION](provenance/RELEASE_VALIDATION.md).

To save your own recomputed results:

```bash
python3 scripts/analyze.py --output-dir build/results
python3 scripts/analyze_extensions.py --data-dir data --output-dir build/results/extensions
```

The first entry point recomputes the detailed three-baseline analysis and the nonempty-abstract experiments. The second recomputes coverage, observed metrics, and set analyses for the 12 configurations evaluated on all queries and the initial five-query experiments. Offline reproduction uses the released rankings; the configurations, code provenance, and model records for generating rankings from the original corpus are documented separately in the [methods documentation](docs/METHODS.md).

I also provide a figure-generation entry point. After installing the optional plotting dependencies, you can generate both figures from your own recomputed tables:

```bash
python3 -m pip install -r requirements-figures.txt
python3 scripts/plot_results.py --results-dir build/results --output-dir build/figures
```

## Reading and File Guide

| Entry point | Contents |
|---|---|
| [Research note](docs/RESEARCH_NOTE.md) | My research questions, experimental stages, complete method comparison, and main analyses |
| [Methods and computational definitions](docs/METHODS.md) | Implementation of the 12 configurations, 0/1/2/U semantics, formulas, randomization protocols, and reproduction levels |
| [Ranking-generation code](retrieval_source/README.md) | Original method implementations, run configurations, dependencies, and code provenance |
| [My contributions and tool use](docs/CONTRIBUTIONS.md) | My experimental work, released materials, and AI-assistance statement |
| [Data documentation](data/README.md) | Original data, ranking format, document metadata, and data acquisition |
| [Extension results](results/extensions/) | Per-query and aggregate results for the configurations evaluated on all queries and initial five-query experiments |
| [Three-baseline coverage table](results/coverage_summary.csv) | Judgment coverage for BM25, MPNet, and Direct at four depths |
| [Abstract strata](results/abstract_strata.csv) / [nonempty-abstract experiments](results/nonempty_coverage_summary.csv) | Analyses of document composition and eligibility |
| [Paired precision bounds](results/paired_precision_bounds_summary.csv) | Sharp intervals for the three baselines after cancellation of shared unknown labels |
| [Top-20 unjudged inventory](results/top20_unjudged_frame.csv) | Query, document, abstract status, and ranks in the three baselines |
| [Research process](docs/RESEARCH_PROCESS.md) | Experimental stages, subsequent additions, and the definitions used in this version |
| [Provenance and version records](provenance/README.md) / [historical materials](archive/README.md) | Correspondence among the initial experiments, freeze records, and subsequent additions |

Proportions are expressed on a 0–1 scale; percentage-point differences are proportional differences multiplied by 100. Precision values and bounds in the main text use `label_rule=strict_eq2`; `relaxed_ge1` is provided separately as a supplementary relevance threshold.

## How I Organize the Research Materials

I organize the repository with reference to the documented, consistent, complete, and exercisable criteria in [ACM Artifact Review and Badging](https://www.acm.org/publications/policies/artifact-review-and-badging-current):

| Criterion | Corresponding materials |
|---|---|
| Documented | README, research note, method configurations, and data dictionary |
| Consistent | Original labels, saved rankings, per-query tables, provenance comparisons, and hashes |
| Complete within the stated research scope | Offline inputs, analysis scripts, tests, figures, and sources of third-party materials |
| Exercisable | Reproduction in a clean directory, an automated verification entry point, and GitHub Actions |

These four criteria guide the organization of this repository. I assembled and computationally validated this release; I have not submitted an ACM badge application.

## Citation, Licensing, and Release

I use the document-selection study by Rangreji, Zhong, and Field as the starting point for my reimplementation, together with the data and evaluation context of BEIR/TREC-COVID. BEIR's discussion of judgment coverage and supplementary judgments informs my analysis; references and their specific relationship to this work are provided in the [research note](docs/RESEARCH_NOTE.md).

- [CITATION.cff](CITATION.cff): citation information for this project; upstream sources are listed in the research note and data documentation.
- [LICENSE](LICENSE): licensing scope for code, documentation, and third-party data.
- [GitHub release instructions](docs/GITHUB_RELEASE.md): pre-upload checks and repository publication steps.

The original frozen materials retain their original versions. This version incorporates the completed subsequent runs as verifiable research outputs, with the research note above serving as the default reading entry point.
