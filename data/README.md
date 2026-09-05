# Data inventory and attribution

This release uses the **BEIR distribution of TREC-COVID**, not a direct join
to the original NIST Complete qrels. Query/document IDs are strings.

| Included file | Origin / contents | Use |
|---|---|---|
| `trec-covid/queries.jsonl` | Unmodified BEIR query file, 50 records | Query inventory |
| `trec-covid/qrels/test.tsv` | Unmodified BEIR test qrels, 66,336 rows | Original relevance judgments |
| `corpus_metadata.csv.gz` | Derived from all 171,332 raw corpus records | ID/order map and title/abstract availability; no article text |
| `runs/bm25.tsv.gz`, `runs/mpnet.tsv.gz`, `runs/direct.tsv.gz` | Lossless conversion of the original three 50-query top-1000 caches | Fixed-ranking primary analysis |
| `runs/nonempty_abstract/*.tsv.gz` | Original audit score orders restricted to nonempty abstracts and replenished to top-1000 | Eligibility sensitivity, not a rebuilt index |

Run columns are `query_id, doc_id, rank, score` (tab separated). Rank starts at
one. Scores retain 17 significant digits. Metadata columns are `corpus_index,
doc_id, has_title, has_abstract, title_chars, abstract_chars`; booleans are 0/1.
Character counts and nonempty status use stripped source strings. Corpus index
is zero based and records raw JSONL order. Gzip files have a deterministic zero
timestamp and can be read without executing serialized Python objects.

Qrel labels 0, 1 and 2 are valid judgments. The two -1 rows are preserved in
the raw file but treated as **unjudged**, as are absent query–document pairs.
The analysis never turns an unjudged pair into a human-assigned zero label.
Observed precision gives credit only for known relevant hits, an explicit
scoring convention separate from label semantics.

## Original sources

- Nandan Thakur et al. (2021), [BEIR](https://arxiv.org/abs/2104.08663).
- [Official BEIR repository and dataset list](https://github.com/beir-cellar/beir).
- [BEIR TREC-COVID dataset card](https://huggingface.co/datasets/BeIR/trec-covid),
  accessed 2026-09-05; the card identifies **CC BY-SA 4.0**.
- [NIST TREC-COVID](https://ir.nist.gov/covidSubmit/), the underlying evaluation.
- [CORD-19](https://github.com/allenai/cord19), underlying scientific literature.
  Article licenses vary; consult the source collection and original providers.
- [CC BY-SA 4.0 terms](https://creativecommons.org/licenses/by-sa/4.0/).

Changes made here: raw queries/qrels are unchanged; corpus text was transformed
to IDs and numeric metadata; original local rankings were converted to TSV;
aggregate diagnostics were independently recomputed. This project is not
affiliated with or endorsed by these source organizations.

## Optional full corpus verification

Article titles/abstracts, model weights, large vector caches, and the original
BEIR zip are **not included in the Git release**. A local copy of the original
`corpus.jsonl` is retained in the working folder but ignored by Git.

```bash
python3 scripts/fetch_corpus.py
# Or supply a previously downloaded original BEIR zip:
python3 scripts/fetch_corpus.py --archive /path/to/trec-covid.zip
# Verify local files without network access:
python3 scripts/fetch_corpus.py --verify-only
```

The script validates the original archive MD5
`ce62140cb23feb9becf6270d0d1fe6d1`, validates each extracted file's SHA-256,
then regenerates and compares `corpus_metadata.csv.gz`. File SHA-256 values
are recorded in [import_inputs.json](../provenance/import_inputs.json).
MD5 is used only to identify the published BEIR archive; extracted data
integrity is additionally checked with SHA-256.

The normal analysis needs only the included small files and is offline.
Downloading the corpus verifies metadata provenance; it does not regenerate
the original dense rankings. See [methods and reproduction boundaries](../docs/METHODS.md).

