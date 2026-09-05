# TREC-COVID Document-Selection Experiments: Method Reimplementation and Evaluation

**My Research Note · QronG9 · v2.0.0 · 2026-09-05**

Taking a document-selection study as my starting point, I reimplemented retrieval and selection methods on the BEIR version of TREC-COVID and examined judgment coverage, observed relevance, document composition, and candidate sets in fixed rankings. My analysis began with five queries, expanded to all 50 queries, and subsequently incorporated additional models and selection configurations. This version brings together 12 configurations evaluated on all queries, the initial five-query results, supplementary nonempty-abstract experiments, and paired precision bounds, with inputs and programs for offline recomputation.

**Reading path:** This report → [Methods and Computational Definitions](METHODS.md) → [Research Process](RESEARCH_PROCESS.md) → [Repository Run Instructions](../README.md). This report is the default reading entry point for the current version.

## 1. My Research Questions and Experimental Progression

The study by Rangreji, Zhong, and Field examines how document selection affects query-oriented text analysis. I chose its TREC-COVID retrieval-validation component as the starting point for my reimplementation and organized the experiments around three concrete questions: which documents different selection methods return; how much of their output is covered by the existing qrels; and which retrieval metrics and comparative bounds can be calculated from fixed results and existing labels. [Source study](https://arxiv.org/abs/2604.12099v1)

I use BEIR's data organization and evaluation context. BEIR's discussion of Hole and supplementary relevance judgments informs my distinction between judgment coverage and observed quality. Within this context, I implemented specific methods, compared their results across all queries, and analyzed input conditions and candidate sets. [BEIR](https://arxiv.org/abs/2104.08663)

My work proceeded through four connected stages:

| Stage | Work I completed | Results preserved in this version |
|---|---|---|
| Initial five-query analysis | Queries 9, 13, 34, 45, and 48; four basic methods, Direct min-max, and three additional selection methods | Eight configurations × five queries × 1000 ranking positions, totaling 40,000 positions |
| Baselines evaluated on all queries | BM25, MPNet, Direct, Random Uniform, and Direct min-max | Rankings and evaluations for all 50 queries in the five configurations |
| Post-freeze extensions | MMR, Query Expansion, and Retrieval Random evaluated on all queries; addition of the MMR reranking variant, SPLADE, BGE, and BM25 + CrossEncoder | A total of 12 configurations evaluated on all queries, with 600,000 main ranking positions |
| Evaluation analyses and release | Abstract strata, nonempty-abstract rankings, unknown-label bounds, portable file exports, and recomputation workflow | A further 100,000 ranking positions in two nonempty-abstract configurations, together with complete results and validation materials |

The five base configurations already had rankings for all 50 queries in the initial stage; the five-query materials select the corresponding queries from those rankings. MMR, Query Expansion, and Retrieval Random were initially saved as five-query runs and subsequently extended to all queries.

Each group of ranking files can be read separately; together they contain **740,000 saved ranking positions**. I preserve the stage-specific outputs through the original freeze records and incorporate the completed supplementary runs into this version. Here, “freeze” refers to file-version and hash records; the specific sources are documented in the [research process](RESEARCH_PROCESS.md) and [version records](../provenance/README.md).

I also retain correspondence checks between the five-query runs and the runs covering all queries. MMR and Query Expansion have identical top-1000 sequences for each of these five queries. Retrieval Random produces different samples across the two stages because query traversal advances the random stream initialized with the same seed; the mean set overlap across the five queries is 0.1902. I preserve the stage-specific results and computational protocols separately so that readers can examine which inputs and outputs remain consistent as the experiments expand, and how the random process maps to the actual documents. [Cross-stage correspondence table](../results/extensions/pilot_full50_overlap_summary.csv)

## 2. How I Define the Data and Comparisons

I use 171,332 documents, 50 queries, and 66,336 qrels rows. Of these, 66,334 query–document pairs have labels of 0, 1, or 2; the remaining two rows labeled −1, together with cases lacking a valid label, are represented as U in the calculations. I preserve the original qrels so that **judged 0 and unjudged U** remain distinguishable in both the data and the coverage statistics. U refers specifically to the availability of a valid judgment in this data version.

I use the natural-language `text` field for each query and concatenate the title and abstract for each document. Rankings are generated using the length, prefix, and scoring settings recorded for each model. Each configuration evaluated on all queries retains 1000 distinct documents per query. MPNet in the tables denotes `sentence-transformers/all-mpnet-base-v2`; Direct refers by default to max-sum fusion of BM25 and MPNet. The normalization variants, candidate depths, random streams, and tie handling are specified in the [methods documentation](METHODS.md).

I calculate Hole at four depths, @20, @50, @100, and @1000, as the proportion of U among the first k documents. Observed precision counts relevance according to the existing labels: the main text uses `qrel=2`, with U contributing no relevant hits in this calculation; supplementary tables also provide `qrel≥1`. All main tables use equally weighted means over these 50 queries and describe the complete query set of this fixed benchmark.

## 3. Results from the Comparison Across All Queries

### 3.1 Coverage and Observed Metrics for Twelve Configurations

| Configuration | Hole@20 | Hole@100 | Observed P@20 | Observed Recall@1000 |
|---|---:|---:|---:|---:|
| BM25 | 0.0720 | 0.1960 | 0.487 | 0.509803 |
| MPNet | 0.4030 | 0.4918 | 0.426 | 0.497134 |
| Direct: max-sum | 0.0540 | 0.1464 | 0.630 | 0.611844 |
| Direct: min-max | 0.0570 | 0.1508 | 0.628 | 0.612986 |
| Random Uniform | 0.9960 | 0.9934 | 0.001 | 0.006417 |
| Direct + MMR: select 1000 from 5000 | 0.8510 | 0.8760 | 0.035 | 0.162314 |
| Direct + MMR: rerank the existing 1000 | 0.6600 | 0.6630 | 0.078 | 0.611844 |
| Query Expansion | 0.0600 | 0.1570 | 0.622 | 0.568064 |
| Retrieval Random | 0.1470 | 0.4228 | 0.503 | 0.173305 |
| SPLADE | 0.1080 | 0.2636 | 0.600 | 0.512628 |
| BGE | 0.1180 | 0.2788 | 0.668 | 0.566764 |
| BM25 + CrossEncoder | 0.0880 | 0.2416 | 0.581 | 0.509803 |

Sources: [coverage summary](../results/extensions/coverage_summary.csv) and [observed-metric summary](../results/extensions/observed_ir_summary.csv). Precision and recall above use the strict relevance threshold; the CSV files retain values at greater numerical precision and per-query results.

I present coverage and observed metrics alongside one another because they convey different information. For example, BM25 has Hole@20 of 0.072 and BGE has 0.118; their corresponding observed P@20 values are 0.487 and 0.668. Readers can examine both judgment availability and the relevant hits confirmed by existing labels without substituting one metric for the other.

The extended results also allow me to report dense-retrieval performance by specific model: MPNet and BGE have Hole@20 values of 0.403 and 0.118, respectively. They use different models, training sources, and input settings; this comparison describes the results of these recorded configurations. SPLADE and BM25 + CrossEncoder provide two additional neural retrieval or reranking configurations for individual comparison under the same data and labels.

![Judgment coverage and observed precision for my twelve configurations](../figures/method_comparison.png)

### 3.2 Examining Document Sets and Ranking Prefixes Separately

I designed two directly testable conditions that preserve document sets. BM25 + CrossEncoder rescores every document in BM25 top-1000, and the final sets are identical for each query. Both therefore have Hole@1000 of 0.6278 and Recall@1000 of approximately 0.509803; observed P@20 for the first 20 items changes from 0.487 to 0.581.

Similarly, the MMR reranking variant preserves the Direct top-1000 set, and both have Hole@1000 of 0.59564 and Recall@1000 of approximately 0.611844. MMR's sequential selection order changes the composition of the ranking prefix, yielding Hole@20 of 0.660. The other MMR configuration selects 1000 documents from Direct top-5000, allowing the final set to change; its Hole@1000 is 0.86392. By preserving both configurations, I make candidate-set selection and within-set ordering changes available for per-query examination. [Set-invariance checks](../results/extensions/set_invariance_checks.csv)

I also calculate each configuration's overlap with BM25 at the same depth, judgment coverage among shared and exclusive documents, and the composition of returned documents inside and outside BM25 top-1000. The candidate boundary in the last analysis is explicitly the saved BM25 top-1000, enabling readers to inspect which documents are included at this candidate depth. [Set overlap](../results/extensions/overlap_vs_bm25_summary.csv) · [Set strata](../results/extensions/judged_shared_exclusive_summary.csv) · [Candidate membership](../results/extensions/bm25_candidate_membership_summary.csv)

For Query Expansion, I also save the keywords actually used for each query. Retrieval Random samples 1000 documents uniformly without replacement from Direct top-5000 and preserves their relative Direct order. These records connect each method name to its specific inputs, selection procedure, and ordering procedure.

### 3.3 Supplementary Analyses of Normalization and Abstract Availability

I ran Direct with max-sum and min-max normalization separately, obtaining observed P@20 values of 0.630 and 0.628 and Hole@20 values of 0.054 and 0.057, respectively. The two fixed rankings allow readers to further examine the changes in ranks and document sets associated with the normalization change.

I also examined the composition of BM25 and MPNet results through their document inputs. Documents without abstracts account for 3.8% and 64.2% of their respective top-20 results. These proportions are calculated from the documents actually returned by each method; the stratified table also provides document counts, valid-judgment counts, and relevant hits. [Abstract strata](../results/abstract_strata.csv)

I then reselected the top-ranked documents from all 129,192 corpus documents with nonempty abstracts, retaining the existing scoring definitions. BM25 retains the original full-corpus IDF and average document length; MPNet reuses the existing document vectors. Each query still receives a complete top-k list. The resulting Hole@20 values are 0.064 and 0.226, a difference of 16.2 percentage points, compared with the original full-corpus difference of 33.1 percentage points. At @100, the difference under the nonempty-abstract condition is 17.78 percentage points. [Nonempty-abstract results](../results/nonempty_coverage_summary.csv)

I report this result as a sensitivity comparison for document eligibility. I retain both the original full-corpus results and the filtered rankings, showing how the same scoring definitions yield different coverage results when the eligible document population changes.

## 4. How I Quantify the Effect of Unknown Labels on Method Comparisons

For two fixed top-k lists, I assign a shared binary relevance label across methods to each U query–document pair and retain all existing labels. Shared U pairs cancel in the precision difference between methods; only U pairs exclusive to either method can alter the paired difference. I use this property to compute sharp attainable lower and upper bounds for each query and for the mean across queries.

The results for the three baselines at P@20 with QREL=2 are:

| Mean P@20 difference | Observed value | Attainable lower bound | Attainable upper bound |
|---|---:|---:|---:|
| MPNet−BM25 | −0.061 | −0.132 | 0.341 |
| Direct−BM25 | 0.143 | 0.092 | 0.176 |
| MPNet−Direct | −0.204 | −0.242 | 0.183 |

The entire Direct−BM25 interval is positive: with fixed rankings, existing labels retained, and the current relevance threshold, every binary completion of U preserves Direct's mean advantage. The other two intervals span zero and explicitly give the attainable range for each comparison. These are mathematical bounds over assignments of unknown labels, and specific assignments attain their endpoints. The formulas and conditions of applicability are provided in the [methods documentation](METHODS.md).

I extend this calculation to comparisons of the remaining configurations against BM25, releasing per-query bounds at @20 and @100 under both relevance thresholds. Under the same P@20 and QREL=2 conditions, the ranges are **[0.113, 0.295]** for BGE−BM25, **[0.045, 0.217]** for SPLADE−BM25, **[0.028, 0.176]** for BM25 + CrossEncoder−BM25, and **[0.084, 0.174]** for Query Expansion−BM25. All of these intervals are positive, explicitly quantifying which mean comparisons in the saved rankings retain their direction under every admissible completion of U. In addition, the top-20 union of the three baselines contains 2,170 query–document pairs, of which 492 are U, involving 461 distinct documents. I export these pairs and their method-specific ranks as a label-availability inventory for further inspection. [Three-baseline bounds](../results/paired_precision_bounds_summary.csv) · [Extended bounds](../results/extensions/paired_precision_bounds_summary.csv) · [Inventory of 492 pairs](../results/top20_unjudged_frame.csv)

## 5. Reproducible Outputs I Provide

My contributions form a traceable sequence from specific methods, saved rankings, and original judgments to result tables: method comparisons across all queries, candidate-set and ordering comparisons, document-availability sensitivity analyses, unknown-label bounds, and stage-specific version records.

I make offline recomputation from fixed rankings to results the release entry point: the tables can be regenerated using only the Python standard library. I separately preserve the configurations, code provenance, model identifiers, and run records for generating rankings from the original corpus; hashes fix the rankings and input files. The validation records for this version separately document file integrity, computational consistency, and program tests. [Recomputation instructions](../README.md) · [Validation for this version](../provenance/RELEASE_VALIDATION.md)

I organize the repository with reference to ACM's criteria that research artifacts be documented, consistent, complete within their stated scope, and exercisable. References, data, third-party models, and code each retain their source attribution. I use AI assistance for implementation, verification, and writing, and I take responsibility for the research scope and released materials. [ACM artifact criteria](https://www.acm.org/publications/policies/artifact-review-and-badging-current) · [My contributions and tool use](CONTRIBUTIONS.md)
