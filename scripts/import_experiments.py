#!/usr/bin/env python3
"""Export my completed full-query and pilot configurations as portable ranking files."""
import argparse
import csv
import gzip
import json
import math
from pathlib import Path

from import_source import sha256, write_gzip_csv

PILOT = ["9", "13", "34", "45", "48"]
REGISTRY = [
    ("bm25", "BM25", "lexical", "cache/runs/bm25.npz", "score_descending", "BM25 score"),
    ("mpnet", "MPNet", "dense", "cache/runs/sbert.npz", "score_descending", "normalized dot product"),
    ("direct", "Direct", "hybrid", "cache/runs/direct.npz", "score_descending", "max-normalized component sum"),
    ("direct_minmax", "Direct minmax", "hybrid_variant", "cache/runs/direct_minmax.npz", "score_descending", "minmax-normalized component sum"),
    ("uniform_random", "Random Uniform", "random", "cache/runs/random.npz", "sample_order", "unscored"),
    ("direct_mmr", "Direct + MMR (5000 to 1000)", "diversity_selection", "extension_retrieval_methods/cache/runs/direct_mmr.npz", "greedy_selection_order", "query-document cosine, not the MMR objective"),
    ("direct_mmr_rerank", "Direct + MMR (reorder 1000)", "diversity_rerank", "extension_retrieval_methods/cache/runs/direct_mmr_rerank.npz", "greedy_selection_order", "query-document cosine, not the MMR objective"),
    ("query_expansion", "Query Expansion", "query_expansion", "extension_retrieval_methods/cache/runs/qryexp.npz", "score_descending", "weighted reciprocal-rank fusion"),
    ("retrieval_random", "Retrieval Random", "subset_sampling", "extension_retrieval_methods/cache/runs/retrieval_random.npz", "sample_then_candidate_order", "Direct score after subset sampling"),
    ("splade", "SPLADE", "learned_sparse", "extension_retrieval_methods/cache/runs/splade.npz", "score_descending", "sparse vocabulary dot product"),
    ("bge", "BGE", "dense", "extension_retrieval_methods/cache/runs/bge.npz", "score_descending", "normalized dot product"),
    ("bm25_ce", "BM25 + CrossEncoder", "reranker", "extension_retrieval_methods/cache/runs/bm25_ce.npz", "score_descending", "cross-encoder score"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    import numpy as np
    source, root = args.source.resolve(), args.root.resolve()
    ids = np.load(source / "cache/doc_ids.npy", allow_pickle=True).tolist()
    with gzip.open(root / "data/corpus_metadata.csv.gz", "rt") as handle:
        portable_ids = [r["doc_id"] for r in csv.DictReader(handle)]
    if ids != portable_ids:
        raise ValueError("Corpus ID ordering mismatch")
    provenance = []

    def export(path, dest, subset=None):
        z = np.load(path, allow_pickle=True)
        qids = list(map(str, z["qids"]))
        selected = [i for i, q in enumerate(qids) if subset is None or q in subset]
        if subset is not None and {qids[i] for i in selected} != set(subset):
            raise ValueError("Pilot query set missing from " + str(path))
        rows = []
        blank = 0
        for i in selected:
            for rank, (idx, score) in enumerate(zip(z["idx"][i], z["scores"][i]), 1):
                value = float(score)
                if math.isnan(value):
                    formatted = ""
                    blank += 1
                elif math.isfinite(value):
                    formatted = format(value, ".17g")
                else:
                    raise ValueError("Infinite score in source run")
                rows.append((qids[i], ids[int(idx)], rank, formatted))
        write_gzip_csv(dest, ["query_id", "doc_id", "rank", "score"], rows, "\t")
        provenance.append({"source_path": str(path.relative_to(source)), "source_sha256": sha256(path),
                           "export_path": str(dest.relative_to(root)), "export_sha256": sha256(dest),
                           "n_queries": len(selected), "n_ranked_pairs": len(rows), "n_blank_scores": blank,
                           "score_conversion": "Original NaN for unscored random draws becomes empty; finite scores use 17 significant digits; stored rank order retained."})

    registry = []
    for method, name, family, source_path, order, score_kind in REGISTRY:
        if method in ("bm25", "mpnet", "direct"):
            run_file = "runs/" + method + ".tsv.gz"
        else:
            run_file = "runs/extensions/" + method + ".tsv.gz"
            export(source / source_path, root / "data" / run_file)
        registry.append({"method": method, "display_name": name, "family": family,
                         "run_file": run_file, "n_queries": 50, "depth": 1000,
                         "ordering": order, "score_kind": score_kind})
    pilot_sources = {"bm25": "bm25", "mpnet": "sbert", "direct": "direct",
                     "uniform_random": "random", "direct_minmax": "direct_minmax",
                     "direct_mmr": "direct_mmr", "query_expansion": "qryexp", "retrieval_random": "retrieval_random"}
    for method, stem in pilot_sources.items():
        export(source / "cache/runs" / (stem + ".npz"), root / "data/runs/pilot" / (method + ".tsv.gz"), PILOT)
    (root / "data/method_registry.json").write_text(json.dumps({"format_version": 1, "methods": registry,
        "pilot_query_ids": PILOT, "pilot_methods": list(pilot_sources),
        "pilot_primary_origin": "The five pilot queries selected from the preserved full-query base runs; the three secondary pilot files retain their original query-specific outputs."}, indent=2) + "\n")
    queries = {r["_id"]: r for r in map(json.loads, (root / "data/trec-covid/queries.jsonl").read_text().splitlines())}
    with (root / "data/pilot_queries.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n");w.writerow(["query_id", "query_text"])
        w.writerows((q, queries[q]["text"]) for q in PILOT)
    metadata_dir = root / "data/experiment_metadata"
    metadata_dir.mkdir(exist_ok=True)
    # Preserve actual selected keyword lists, with computation settings kept in METHODS.
    for stage, path in [("full50", source / "extension_retrieval_methods/cache/runs/qryexp.meta.json"),
                        ("pilot", source / "cache/runs/qryexp.meta.json")]:
        value = json.loads(path.read_text())
        (metadata_dir / ("query_expansion_keywords_" + stage + ".json")).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    (root / "provenance/experiment_imports.json").write_text(json.dumps({"inputs_and_exports": provenance}, indent=2) + "\n")
    print(f"Exported {len(registry)} full-query configurations and {len(pilot_sources)} pilot configurations.")


if __name__ == "__main__":
    main()
