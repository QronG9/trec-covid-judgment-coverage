# My Preserved Data and Experimental Runs

I use the BEIR distribution of TREC-COVID: 171,332 documents, 50 queries, and 66,336
rows of original judgment records. I store document identifiers, saved rankings,
and original judgments separately so that each statistic can be traced to specific
queries, documents, and ranks.

## Data Inventory

| File | Contents I preserve | Purpose |
|---|---|---|
| `trec-covid/queries.jsonl` | The 50 queries, preserved without modification | Query texts and IDs |
| `trec-covid/qrels/test.tsv` | Judgment records, preserved without modification | Labels 0, 1, 2, and −1 |
| `corpus_metadata.csv.gz` | IDs and order for the full corpus, title/abstract availability, and character counts | Data checks and representation sensitivity |
| `runs/{bm25,mpnet,direct}.tsv.gz` | The initial three methods, each with 50×1000 rows | Baseline comparisons |
| `runs/extensions/*.tsv.gz` | The other nine full-query configurations, each with 50×1000 rows | Comparisons of normalization, random selection, MMR, expansion, sparse retrieval, vector retrieval, and reranking |
| `runs/pilot/*.tsv.gz` | Eight initial configurations, each with 5×1000 rows | Preservation of the early experimental state |
| `runs/nonempty_abstract/*.tsv.gz` | BM25 and MPNet under the nonempty-abstract condition, each with 50×1000 rows | Sensitivity to the eligible document population |
| `method_registry.json` | Names, categories, files, and ranking semantics for the 12 configurations | A configuration inventory shared by the programs and documentation |
| `pilot_queries.csv` | Queries 9, 13, 34, 45, and 48 | Query scope of the initial experiments |
| `experiment_metadata/` | Keywords actually used in the initial and 50-query experiments | Input records for Query Expansion |

The full-query configurations contain **600,000 ranking positions**. Together with
the 40,000 rows from the initial experiments and the 100,000 rows under the
nonempty-abstract condition, the release contains 740,000 rows. These are position
records across configurations and stages, with shared documents; the five basic
configurations in the five-query materials are the corresponding subsets of the
full-query rankings.

I converted the original NumPy rankings into four-column TSV files with
`query_id, doc_id, rank, score`, using deterministic gzip compression. Finite scores
retain 17 significant digits, and document order is unchanged. Random Uniform
originally had no relevance scores; I preserve that state using empty strings, and
its ranks represent sampling order. The scores in the MMR files are query–document
cosine similarities, whereas ranks represent greedy selection order; these files
are read using `rank`. Retrieval Random preserves Direct's relative order after
sampling a subset from the candidate pool.

The metadata columns are `corpus_index, doc_id, has_title, has_abstract, title_chars,
abstract_chars`. The index starts at 0, and Boolean values are encoded as 0/1.
Character counts and availability are computed after stripping leading and trailing
whitespace from the original strings. I preserve the bytes and line-ending formats
of the original BEIR files.

## Label Definitions I Use

Labels 0, 1, and 2 are valid judgments; −1 and query–document pairs without a record
belong to U. To calculate observed P@k, I divide the number of retrieved documents
known to meet the relevance threshold by k and store this metric separately from
judgment coverage. The main text uses QREL=2; QREL≥1 is retained in separate
threshold rows.

## Sources and Licensing

I cite and retain attribution to the following data sources:

- The [BEIR paper](https://arxiv.org/abs/2104.08663) and [official dataset list](https://github.com/beir-cellar/beir).
- The [BEIR TREC-COVID dataset card](https://huggingface.co/datasets/BeIR/trec-covid), which specifies CC BY-SA 4.0.
- [NIST TREC-COVID](https://ir.nist.gov/covidSubmit/), which provides the underlying evaluation task.
- [CORD-19](https://github.com/allenai/cord19), which provides the underlying scientific literature collection; articles retain the rights of their respective sources.
- [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

I preserve the query and judgment files without modification, convert the corpus
into identifiers and numerical metadata, convert the experimental caches into TSV,
and recompute the summary results. The public Git files contain these directly
recomputable materials. Full article titles and abstracts, model weights, and large
vector caches are retained locally or obtained from their original sources.

## Checking Metadata Against the Original Corpus

```bash
python3 scripts/fetch_corpus.py
# I can also use an original BEIR archive that has already been downloaded:
python3 scripts/fetch_corpus.py --archive /path/to/trec-covid.zip
# If the corpus is already available locally:
python3 scripts/fetch_corpus.py --verify-only
```

The program checks the BEIR archive's MD5, `ce62140cb23feb9becf6270d0d1fe6d1`, and
the SHA-256 hashes of the three original files, then regenerates the metadata from
the corpus for comparison. The [input hashes](../provenance/import_inputs.json)
record these sources. Routine result recomputation reads the compact inputs in
this repository directly and can run offline.
