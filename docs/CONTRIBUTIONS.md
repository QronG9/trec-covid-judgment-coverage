# My Contributions and Use of Tools

**Author and maintainer: QronG9**

I conducted this study to understand document-selection methods through practical reimplementation and to make three questions separately verifiable: which documents were retrieved, how many had existing judgments, and how many were identified as relevant by those judgments.

## Research Work I Completed

1. **Translating the literature into executable experiments.** Taking the document-selection study by Rangreji, Zhong, and Field as my starting point, I documented the implementation configurations for query fields, document concatenation, BM25 scoring, MPNet encoding, Direct fusion, MMR, query expansion, and random selection, and retained their specific parameters and run outputs.
2. **Extending the initial five-query analysis to all 50 queries.** I began with queries 9, 13, 34, 45, and 48, then assembled the baseline analysis for all 50 queries and added method extensions. The five-query results for the basic methods were extracted from saved full-query runs; I also retained separate five-query runs for three supplementary selection methods. This release brings together 12 retrieval/selection configurations and 600,000 primary ranking records, while preserving the provenance relationships between stages.
3. **Reporting judgment coverage and observed retrieval quality separately.** I explicitly retained the qrel states 0, 1, 2, and U, and computed Hole at multiple depths, observed precision/recall, per-query differences, and set overlap between methods. These calculations allow readers to examine judgment coverage separately from retrieval results under the existing labels.
4. **Specifying concrete configurations for method comparisons.** I added SPLADE, BGE, and BM25 + CrossEncoder, retained two normalization variants of Direct, and ran separate MMR configurations that select 1000 documents from the Direct top-5000 and rerank the Direct top-1000. By documenting candidate-set definitions, preserving the final document sets and rankings, and recording model parameters, I can examine the results associated with set selection and reranking separately.
5. **Adding analyses of document availability and unknown labels.** I documented title/abstract inputs, stratification by abstract availability, and rankings restricted to all documents in the corpus with nonempty abstracts. For fixed lists, I computed sharp attainable bounds on paired precision differences under shared U labels and exported the unjudged query–document pairs in the BM25, MPNet, and Direct top-20 results.
6. **Organizing the experiments into research materials that support recomputation.** I exported compressed rankings in a common format and metadata without document text, implemented a standard-library analysis pipeline, input checks, and tests of mathematical semantics, and assembled reference comparisons, a hash manifest, version records, documentation, and an automated verification entry point.

These contributions consist of the method implementations, experimental comparisons, evaluation analyses, and executable materials in this repository. I attribute BM25, Sentence-BERT/MPNet, MMR, RRF, SPLADE, BGE, CrossEncoder, Hole, and the other methods and metrics to their respective upstream work; my outputs are the experimental configurations, analyses, and recomputable results documented here.

## Outputs by Stage

| Stage | My work | Corresponding release contents |
|---|---|---|
| Initial five-query analysis | Analysis and checks for five queries and eight configurations, with five configurations extracted from full-query runs and three retained as separate five-query runs | Initial results, frozen source materials, and stage records |
| Full-query baselines | Runs for all 50 queries using BM25, MPNet, Direct, and Random Uniform, supplemented by Direct min-max | Fixed primary rankings, coverage metrics, and observed metrics |
| Subsequent method extensions | Extension of MMR, Query Expansion, and Retrieval Random to 50 queries; addition of a second MMR configuration, SPLADE, BGE, and BM25 + CrossEncoder | Full-query comparison tables, set and order analyses, and model configurations |
| Evaluation analysis and release | Abstract stratification, the nonempty-abstract condition, paired bounds, exports in common formats, and offline recomputation | Detailed analyses, inventories, scripts, tests, and documentation for this release |

The correspondence between methods and files is detailed in [METHODS](METHODS.md), the [data documentation](../data/README.md), and the [provenance records](../provenance/README.md). I also release the [retrieval implementation source code](../retrieval_source/README.md), connecting the actual scoring, candidate selection, model calls, and run-saving procedures to the result materials. Source hashes and abstract syntax tree checks document the correspondence between the original implementation and the source code in this release.

## How I Use Tools

I use AI tools, including Codex, to assist with code implementation, result verification, organization of research materials, and documentation. I am responsible for the research questions, experimental scope, interpretive decisions, and public materials. I retain scripts, inputs, run outputs, and verification records so that readers can directly inspect the computations underlying my contributions.

The relevance labels come from the BEIR TREC-COVID qrels included in this repository. Here, “verification” refers to checks of inputs, program computations, result consistency, and version provenance. The label sources and model-based generation stage are documented in the data and methods files, respectively.
