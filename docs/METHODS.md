# My Experimental Methods and Reproduction Definitions

I document the inputs, scoring procedures, and calculation formulas for the 12 full-query configurations, the initial five-query experiments, and the two nonempty-abstract configurations. The quick reproduction workflow uses the saved rankings as input. I describe the model configurations used to generate rankings from the original corpus separately; the [retrieval source appendix](../retrieval_source/README.md) provides the implementations, dependencies, original file hashes, and checks of computational equivalence. Readers can therefore examine the data, ranking generation, or statistical calculations as needed.

## 1. Data, Versions, and Rankings

I use the BEIR version of TREC-COVID: 171,332 documents, 50 queries, and 66,336 qrel rows. Of these, 66,334 query–document pairs have labels of 0, 1, or 2; the original labels for Q38/`9hbib8b3` and Q50/`svo94kuo` are −1. I preserve the qrels unchanged and treat −1 and pairs without a valid label as U in the calculations.

I store query and document IDs as strings, map document IDs according to the original corpus order, and preserve the `rank` field in the rankings. Each of the 12 full-query configurations contains 1000 distinct documents per query, yielding 600,000 primary ranking entries. The initial five-query materials contain eight configurations and 40,000 ranking entries. For BM25, MPNet, Direct, Random Uniform, and Direct min-max, I select the corresponding queries from the saved full 50-query rankings; for MMR, Query Expansion, and Retrieval Random, I retain the separate five-query runs from that stage. The 25,000 ranking entries for the first five configurations also appear in the primary rankings. The two nonempty-abstract configurations contain a further 100,000 entries. Configuration names, files, and ordering semantics are listed in the [method registry](../data/method_registry.json). The historical name `SBERT` corresponds to `mpnet` in this release.

I use the following common input definitions:

- **Queries:** the natural-language `text` field in BEIR's `queries.jsonl`.
- **Documents:** I strip leading and trailing whitespace from `title` and `text` separately. When both are nonempty, I concatenate them as `title + '. ' + text`; otherwise, I use the nonempty field.
- **Abstract status:** a null `text` value defaults to an empty string. I classify a document as having no abstract if the result is empty after `strip()`. The full corpus contains 42,140 documents without abstracts and 129,192 with nonempty abstracts.
- **File versions:** SHA-256 hashes in the release manifest fix the versions of the original queries, qrels, corpus source, metadata, and rankings. File formats and data access are described in the [data documentation](../data/README.md).

## 2. Twelve Retrieval and Selection Configurations

The following parameters define the implementations I ran. Each configuration uses its corresponding input and scoring settings, and comparisons refer to this set of documented configurations.

| Configuration ID | My implementation |
|---|---|
| `bm25` | BM25Okapi; `k1=1.5, b=0.75, epsilon=0.25`; a corpus-wide term index; top-1000 retrieval. |
| `mpnet` | `sentence-transformers/all-mpnet-base-v2`; 768 dimensions and a maximum of 384 tokens; float32 dot products of L2-normalized vectors; corpus-wide retrieval. |
| `direct` | The union of the BM25 and MPNet top-1000 lists; I divide each component score by its maximum within the candidate set, sum the normalized scores, and retain the top-1000. |
| `direct_minmax` | The same candidate construction; I apply `(score−min)/(max−min)` to each component, sum the normalized scores, and retain the top-1000. |
| `uniform_random` | Uniform sampling of 1000 documents from the full corpus without replacement, preserving sampling order; seed 42; no retrieval score. |
| `direct_mmr` | I first produce the Direct top-5000, then select 1000 documents in greedy MMR order using MPNet cosine similarity and `λ=0.3`. |
| `direct_mmr_rerank` | I apply the same MMR procedure within the Direct top-1000 set and return all 1000 documents in the resulting order. |
| `query_expansion` | KeyBERT-style keyword selection with MPNet, diversity=0.7, and up to five keywords per query; I run Direct top-1000 for the original query and each keyword, then combine the lists with weighted RRF, `k=60`. |
| `retrieval_random` | Uniform sampling of 1000 documents from the Direct top-5000 without replacement, with seed 42; output follows the selected documents' relative positions in the Direct candidate pool. |
| `splade` | `naver/splade-cocondenser-ensembledistil`; a maximum of 256 word-pieces; maximum pooling of `log(1+relu(logits))` over positions admitted by the attention mask, separately for each vocabulary dimension; corpus-wide retrieval by sparse dot product. |
| `bge` | `BAAI/bge-base-en-v1.5`; 768 dimensions and a maximum of 512 tokens; no instruction prefix for documents, and the query prefix `Represent this sentence for searching relevant passages: `; corpus-wide retrieval by dot product of L2-normalized vectors. |
| `bm25_ce` | `cross-encoder/ms-marco-MiniLM-L-6-v2`; a maximum of 512 tokens; scoring of every query–document pair in the saved BM25 top-1000, followed by reranking within that same set. |

BM25 tokenization applies lowercasing, the regular expression `[a-z0-9]+`, removal of the 198 NLTK English stopwords, and Porter stemming, in that order. Queries undergo the same processing, and repeated query terms contribute cumulatively. IDF is defined as `ln((N−df+0.5)/(df+0.5))`; negative values are replaced by `0.25 × mean IDF over the entire vocabulary`. The corpus-wide mean document length is approximately 113.296722 terms.

I retain model identifiers, input settings, and hashes of the generated rankings. The original generation programs load models by name; the precision of the model version records is described in the [provenance documentation](../provenance/README.md). The core reproduction reads the rankings fixed in this release directly. MPNet, SPLADE, BGE, and CrossEncoder use length settings of 384, 256, 512, and 512, respectively. Together with the models, prefixes, and scoring procedures, these settings define the experimental configurations.

### Direct Candidate Depth and Normalization

For an output depth of n, I obtain the BM25 top-n and MPNet top-n lists, form their union, compute the fusion scores, and return n documents. Each component scores all candidates in the union; a component with a maximum score of zero contributes zero.

```text
max_sum(d) = BM25(d)/max(BM25) + MPNet(d)/max(MPNet)
minmax_sum(d) = (BM25(d)−min(BM25))/(max(BM25)−min(BM25))
              + (MPNet(d)−min(MPNet))/(max(MPNet)−min(MPNet))
```

For min-max normalization, a component with a zero denominator contributes zero. The Direct top-5000 used by MMR and Retrieval Random is constructed afresh with `n=5000`: I form the union of the two top-5000 lists and select 5000 documents. This candidate union contains at most 10,000 documents. The standard Direct configuration uses `n=1000`.

### MMR Selection Order

I select the candidate with the highest query cosine similarity first, then iteratively compute:

```text
MMR(d) = 0.3 × cosine(d,query)
       − 0.7 × max[cosine(d,a), a in already_selected]
```

At each step, I select the highest value, breaking ties by the earliest position in the current Direct candidate pool. The output `rank` records the greedy selection order. The saved `score` is the query–document cosine similarity; readers should use `rank` directly when reproducing the MMR lists.

### Query Expansion Keywords and Weights

I remove stopwords, then form a deduplicated set of unigram and bigram phrase candidates. I select the keyword with the highest query similarity first, then use MMR with diversity=0.7 to select subsequent keywords, up to a maximum of five. In the actual runs, Q1 and Q32 each have three keywords, and the remaining queries each have five. The complete lists are available in the [full-query keyword file](../data/experiment_metadata/query_expansion_keywords_full50.json) and the [five-query keyword file](../data/experiment_metadata/query_expansion_keywords_pilot.json).

The original query receives a weight of 0.5. If the actual number of keywords is t, each keyword receives a weight of `0.5/t`. Each query text or keyword produces a Direct top-1000 list. A document receives `weight/(60+rank)` from each list in which it appears; I sum these contributions across lists and retain the top-1000.

### Randomization Protocols and Tie-Breaking

I create a separate NumPy Generator with seed 42 for each random method and advance its random stream in ascending numerical query-ID order. Random Uniform preserves sampling order. After Retrieval Random samples a document set, it sorts the documents by ascending position in the Direct candidate pool. Its evaluation at shallow depths therefore depends on both the sampled set and the retained Direct order.

The five-query and 50-query Retrieval Random runs advance their random streams separately, so the same query receives different samples. Across the five queries, the mean top-1000 set overlap is 0.1902. The five-query Random Uniform materials, by contrast, are selected directly from the same full 50-query run and are identical for the corresponding queries. The saved rankings for each stage serve as that stage's reproduction inputs. Cross-stage correspondence is also recorded for the deterministic five-query MMR and Query Expansion results.

Configurations that ordinarily sort by score use descending scores and break ties by ascending original corpus index. MMR uses the candidate-pool position rule described above, and Random Uniform uses sampling order. The ranking files in this release provide the fixed floating-point scores and ranks.

## 3. Judgment Coverage, Sets, and Observed Relevance

For query q and document d, I define `J(q,d)=1` if and only if the original qrel belongs to `{0,1,2}`; otherwise, it is 0 and the displayed label is U. I denote method m's fixed top-k set by `S(m,q,k)`.

```text
Hole(m,q,k) = count(U in S(m,q,k)) / k
Judged(m,q,k) = 1 − Hole(m,q,k)
mean_Hole(m,k) = sum[Hole(m,q,k), q in the query set] / number_of_queries
```

I report results at @20, @50, @100, and @1000. The primary full-query tables use all 50 queries, while the five-query tables use their corresponding five queries. Every query has exactly k entries, so the query-averaged coverage rates equal the proportions pooled over all retrieved positions.

For sets A and B at the same depth, I calculate the overlap fraction `|A∩B|/k` and Jaccard similarity `|A∩B|/|A∪B|`. I also count judgment status separately for the intersection, documents exclusive to A, and documents exclusive to B. Abstract strata likewise group the documents actually retrieved by each method. The stratified tables record counts, pooled proportions, and queries with nonzero denominators separately. Calculations across strata and methods use their respective denominators.

The candidate-membership analysis divides each configuration's returned documents into those inside and outside the saved BM25 top-1000 for that query. I fix the candidate depth at 1000 so that readers can verify membership directly. The set-invariance checks compare the top-1000 sets query by query for BM25 versus BM25 + CrossEncoder and Direct versus MMR rerank.

### Observed Precision and Recall

The primary relevance rule is `strict_eq2`: qrel=2 counts as relevant. The supplementary rule, `relaxed_ge1`, counts both 1 and 2 as relevant. U contributes zero known relevant hits to the observed metrics while retaining its data status as U.

```text
P_observed(m,q,k) = count(existing relevant labels in S(m,q,k)) / k
Recall_observed(m,q,1000)
    = count(existing relevant labels in S(m,q,1000))
      / count(existing relevant labels for q in the qrels)
```

I record the two thresholds in separate output rows. The recall denominator corresponds to the same query and relevance rule as the numerator. In the main text, “observed” refers to relevant items confirmed by the existing qrels. The following section bounds precision under completions of the missing labels.

## 4. Sharp Bounds on Paired Precision Differences

I hold the current rankings and existing labels fixed, allow each U to take a value of 0 or 1 under the selected relevance threshold, and require the same query–document pair to share a label across methods. For two fixed top-k sets A and B, let `δ_obs=P_obs(A)−P_obs(B)`, and let `U_Aonly` and `U_Bonly` be the numbers of U items exclusive to A and B, respectively.

```text
lower(q) = δ_obs(q) − U_Bonly(q)/k
upper(q) = δ_obs(q) + U_Aonly(q)/k
mean_lower = average[lower(q)]
mean_upper = average[upper(q)]
```

The contributions of shared U items cancel in the difference. Assigning all U items exclusive to B as relevant and all U items exclusive to A as nonrelevant attains the lower bound; reversing these assignments attains the upper bound. The same document has distinct relevance labels for different queries. Each endpoint of each paired interval is individually attainable, conditional on fixed lists, unchanged existing labels, and unrestricted binary completion of U.

In the detailed three-baseline analysis, I report MPNet−BM25, Direct−BM25, and MPNet−Direct. The extension analysis compares each of the other 11 configurations with BM25. All comparisons cover @20 and @100 under both relevance rules. These intervals represent the range over assignments of unknown labels and should be used with the same rankings and relevance definitions.

## 5. Nonempty-Abstract Conditions and the Top-20 Inventory

I select the 129,192 documents for which `text.strip()` is nonempty from the original full corpus, then obtain the BM25 and MPNet top-1000 within this set using the existing scoring definitions. BM25 uses term frequencies, IDF, and average document length from the original corpus-wide index. MPNet uses the existing document vectors and corresponding query vectors. I then calculate coverage over each complete top-k list from the restricted corpus.

This experiment compares different populations of eligible documents while preserving the denominator k for each query and the existing scoring definitions. I store the two nonempty-abstract rankings separately from the primary rankings to support independent reproduction and provenance tracking.

I also construct the union of query–document pairs in the BM25, MPNet, and Direct top-20 lists. I merge duplicate pairs across methods within a query and retain separate entries for the same document across queries. This union contains 2,170 pairs, of which 492 are U, involving 461 distinct documents. The inventory records existing judgment status and method-specific ranks; its scope is the top-20 of these three baselines. [Inventory](../results/top20_unjudged_frame.csv)

## 6. Running and Verifying the Calculations

From the repository root, run:

```bash
python3 scripts/analyze.py --output-dir build/results
python3 scripts/analyze_extensions.py --data-dir data --output-dir build/results/extensions
python3 scripts/verify_release.py
```

The first script recalculates the detailed analysis of the three baselines and the two nonempty-abstract configurations. The second recalculates the 12 full-query configurations and eight five-query configurations, producing the following outputs:

| File group in `results/extensions/` | Calculation |
|---|---|
| `coverage_*`, `observed_ir_*` | Full-query coverage, observed P@20, and Recall@1000 |
| `pilot_coverage_*`, `pilot_observed_ir_*` | Coverage and observed metrics for the five-query stage |
| `pilot_full50_overlap_*` | Set overlap and rank correspondence between the five-query and full-query stages |
| `overlap_vs_bm25_*` | Set overlap between each configuration and BM25 |
| `judged_shared_exclusive_*` | Judgment-coverage strata for shared and exclusive documents |
| `bm25_candidate_membership_*` | Composition of returned documents inside and outside the BM25 top-1000 |
| `paired_precision_bounds_*` | Sharp bounds on paired precision differences relative to BM25 |
| `set_invariance_checks.csv` | Query-level set checks for reranking within fixed candidate sets |
| `reproduction_checks.json` | Inputs, counts, and checks recorded for the calculation |

`*_by_query.csv` files retain query-level records, and `*_summary.csv` files summarize them. `verify_release.py` recalculates results in a temporary directory and compares them with the release files, while also checking hashes, program tests, and documentation sources. The actual execution results for this release are recorded in the [validation record](../provenance/RELEASE_VALIDATION.md).

I distinguish three levels of verification: file hashes identify specific versions; recalculation from fixed inputs verifies statistical calculations; and generation configurations and source code document how the original rankings were produced. Offline reproduction uses the standard library and the small inputs included in this release. Acquisition of the original corpus and execution of the models follow their separately documented dependencies and sources.

## 7. References

- Rangreji, Zhong, and Field: [The Effect of Document Selection on Query-focused Text Analysis](https://arxiv.org/abs/2604.12099v1), the starting point for my reimplementation of document-selection methods and retrieval validation.
- Thakur et al.: [BEIR](https://arxiv.org/abs/2104.08663), the benchmark version and evaluation context for judgment coverage.
- NIST: [TREC-COVID data documentation](https://ir.nist.gov/covidSubmit/data.html), the original task and judgment materials.
- Reimers and Gurevych: [Sentence-BERT](https://aclanthology.org/D19-1410/), the source of the sentence-embedding framework; the specific checkpoint is the MPNet model listed above.
- Model cards: [MPNet](https://huggingface.co/sentence-transformers/all-mpnet-base-v2), [SPLADE](https://huggingface.co/naver/splade-cocondenser-ensembledistil), [BGE](https://huggingface.co/BAAI/bge-base-en-v1.5), and [CrossEncoder](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2).
