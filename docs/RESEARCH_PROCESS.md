# How I Conducted and Preserved These Experiments

## Beginning with the Queries

I began by analyzing five TREC-COVID queries: 9, 13, 34, 45, and 48. Rankings for BM25, MPNet,
Direct, uniform random selection, and Direct minmax had been generated for all 50 queries;
the initial materials use the corresponding five-query subsets. For MMR, Query Expansion,
and Retrieval Random, I first saved separate five-query runs. The inputs to the initial
analysis of these eight configurations are preserved in `data/runs/pilot/`; the query texts
are available in `data/pilot_queries.csv`.

## Extending the Analysis to All 50 Queries

I extended the coverage analysis of the basic methods to every query in the benchmark,
reusing the saved rankings. I retained 1000 documents per query for each configuration
and computed a common set of metrics at @20, @50, @100, and @1000. This allows me to
examine both aggregate values and the specific differences for individual queries.

## Adding Methods and Experimental Conditions

I extended MMR, Query Expansion, and Retrieval Random to all 50 queries and added
SPLADE, BGE, and BM25+CrossEncoder. I also retained an MMR run that only reranks the
Direct top-1000, alongside the configuration that selects 1000 documents from the
Direct top-5000. Including Direct minmax, the complete experiment contains 12
full-query configurations.

The saved sequences for MMR and Query Expansion on the original five queries can be
compared item by item. Retrieval Random uses a random-number stream with seed=42;
because queries occupy different positions in the 5-query and 50-query runs,
I preserve the actual samples from both runs and compare their intersections.

## Examining Document Representations and Metric Definitions

I extracted title and abstract availability and character counts from the original
corpus and compared the retrieved sets across methods. I also selected the top-k
documents by their existing scores from all documents with nonempty abstracts and
retained the resulting rankings for recomputation.

For precision, I computed QREL=2 and QREL≥1 separately. Under fixed rankings and
existing labels, I used the cancellation of shared U labels to calculate the attainable
range of each paired method difference. I retain the assumptions, formulas, and
per-query results for each range.

## Making the Computational Path Traceable

I exported these runs in a common TSV format, preserved the actual keywords and
ranking semantics as metadata, generated result tables from the original qrels using
a common program, and compared them with the saved reference tables. I also tested
the mathematical bounds using small label-assignment cases that can be enumerated
exhaustively, and checked input identifiers, ranks, shared sets, and file hashes.

My version records preserve the inputs and outputs of each stage. Readers can begin
with the [research report](RESEARCH_NOTE.md) or regenerate the tables directly using
the commands on the [repository home page](../README.md).
