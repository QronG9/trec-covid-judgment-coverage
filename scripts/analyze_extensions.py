#!/usr/bin/env python3
"""Recompute the twelve completed retrieval conditions from saved rankings.

I preserve the saved rank order, compare each condition with BM25, and calculate
coverage, observed retrieval metrics, overlap, strata, and fixed-ranking bounds
directly from the released query-document judgments. Python standard library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import analyze as core


METHODS = (
    "bm25", "mpnet", "direct", "direct_minmax", "uniform_random", "direct_mmr",
    "direct_mmr_rerank", "query_expansion", "retrieval_random", "splade",
    "bge", "bm25_ce",
)
CUTOFFS = (20, 50, 100, 1000)
ORDERING = {
    "bm25": "Descending BM25 score; exact ties use corpus index.",
    "mpnet": "Descending query cosine similarity; exact ties use corpus index.",
    "direct": "Descending normalized BM25-plus-MPNet score; exact ties use corpus index.",
    "direct_minmax": "Descending minmax-normalized BM25-plus-MPNet score; exact ties use corpus index.",
    "uniform_random": "Saved sample order. Empty score preserves the absence of a defined score in the source random run.",
    "direct_mmr": "Greedy MMR selection order from Direct top-5000; stored score is query cosine, not the changing MMR objective.",
    "direct_mmr_rerank": "Greedy MMR order of the same Direct top-1000 set; stored score is query cosine, not the changing MMR objective.",
    "query_expansion": "Descending weighted reciprocal-rank-fusion score; exact ties use corpus index.",
    "retrieval_random": "Random subset of Direct top-5000, retaining Direct relative order and fused scores.",
    "splade": "Descending sparse neural retrieval score; exact ties use corpus index.",
    "bge": "Descending dense query cosine similarity; exact ties use corpus index.",
    "bm25_ce": "Descending cross-encoder score within the saved BM25 top-1000 set; exact ties use corpus index.",
}


def read_saved_run(path, queries, metadata, depth=1000, allow_unscored=False):
    """Validate an explicit saved ranking without re-sorting its score column.

    Greedy MMR scores and random sample order are not ordinary score-sorted runs.
    Scored methods must have finite scores; only the explicitly unscored uniform
    random method permits an empty score. Every run must have known IDs, distinct
    documents, and contiguous ranks 1..depth for the benchmark query set.
    """
    result, seen = {}, {}
    with core.open_text(path) as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        core.require({"query_id", "doc_id", "rank", "score"}.issubset(reader.fieldnames or ()), f"{path}: missing run columns")
        for number, row in enumerate(reader, 2):
            context = f"{path}:{number}"
            qid, doc = row["query_id"], row["doc_id"]
            core.require(qid in queries, f"{context}: unknown query_id {qid}")
            core.require(doc in metadata, f"{context}: unknown doc_id {doc}")
            docs, known = result.setdefault(qid, []), seen.setdefault(qid, set())
            core.require(doc not in known, f"{context}: duplicate run pair {qid}/{doc}")
            rank = core.integer(row["rank"], context)
            core.require(rank == len(docs) + 1 and rank <= depth, f"{context}: noncontiguous/out-of-range rank {rank}")
            if not (allow_unscored and row["score"] == ""):
                try:
                    score = float(row["score"])
                except (ValueError, TypeError) as exc:
                    raise core.DataError(f"{context}: invalid score") from exc
                core.require(math.isfinite(score), f"{context}: nonfinite score")
            docs.append(doc)
            known.add(doc)
    core.require(set(result) == set(queries), f"{path}: inconsistent query set")
    for qid, docs in result.items():
        core.require(len(docs) == depth, f"{path}: query {qid} has {len(docs)} rows; expected {depth}")
    return result


def mean_defined(values):
    values = [value for value in values if value is not None]
    return core.average(values) if values else None


def observed_ir_tables(runs, labels, precision_k=20, recall_k=1000):
    by_query, summary = [], []
    for method, run in runs.items():
        for rule, threshold in core.THRESHOLDS:
            rows = []
            for qid in sorted(run, key=core.query_key):
                docs, qlabels = run[qid], labels[qid]
                core.require(len(docs) >= max(precision_k, recall_k), f"Short run {method}/{qid}")
                n_relevant = sum(core.relevant(value, threshold) for value in qlabels.values())
                p_hits = sum(core.relevant(qlabels.get(doc), threshold) for doc in docs[:precision_k])
                r_hits = sum(core.relevant(qlabels.get(doc), threshold) for doc in docs[:recall_k])
                rows.append({
                    "method": method, "query_id": qid, "label_rule": rule,
                    "precision_k": precision_k, "recall_k": recall_k,
                    "n_qrel_relevant": n_relevant,
                    "n_observed_relevant_at_precision_k": p_hits,
                    "n_observed_relevant_at_recall_k": r_hits,
                    "observed_precision": p_hits / precision_k,
                    "observed_recall": r_hits / n_relevant if n_relevant else None,
                })
            by_query.extend(rows)
            summary.append({
                "method": method, "label_rule": rule, "precision_k": precision_k,
                "recall_k": recall_k, "n_queries": len(rows),
                "n_queries_with_relevant_qrels": sum(row["n_qrel_relevant"] > 0 for row in rows),
                "mean_observed_precision": core.average(row["observed_precision"] for row in rows),
                "mean_observed_recall": mean_defined(row["observed_recall"] for row in rows),
                "n_observed_relevant_at_precision_k": sum(row["n_observed_relevant_at_precision_k"] for row in rows),
                "n_observed_relevant_at_recall_k": sum(row["n_observed_relevant_at_recall_k"] for row in rows),
                "n_qrel_relevant": sum(row["n_qrel_relevant"] for row in rows),
            })
    return by_query, summary


def overlap_tables(runs, cutoffs=CUTOFFS):
    by_query, summary = [], []
    for method, run in runs.items():
        if method == "bm25":
            continue
        for k in cutoffs:
            rows = []
            for qid in sorted(run, key=core.query_key):
                a, b = set(run[qid][:k]), set(runs["bm25"][qid][:k])
                core.require(len(a) == len(b) == k, f"Invalid depth or duplicate document at {method}/{qid}/{k}")
                shared, union = len(a & b), len(a | b)
                rows.append({
                    "method": method, "baseline": "bm25", "query_id": qid, "k": k,
                    "n_shared": shared, "n_method_only": len(a - b), "n_bm25_only": len(b - a),
                    "n_union": union, "overlap_fraction": shared / k, "jaccard": shared / union,
                })
            by_query.extend(rows)
            summary.append({
                "method": method, "baseline": "bm25", "k": k, "n_queries": len(rows),
                "total_shared": sum(row["n_shared"] for row in rows),
                "mean_overlap_fraction": core.average(row["overlap_fraction"] for row in rows),
                "mean_jaccard": core.average(row["jaccard"] for row in rows),
                "n_queries_identical_sets": sum(row["n_shared"] == k for row in rows),
            })
    return by_query, summary


def strata_tables(runs, labels, cutoffs=CUTOFFS):
    """Count shared and exclusive sets; report pooled and nonempty-query means."""
    by_query, summary = [], []
    counts = ("n_pairs", "n_judged", "n_unjudged", "n_explicit_minus1", "n_relevant_strict", "n_relevant_relaxed")
    fractions = ("judged_fraction", "hole_fraction", "observed_precision_strict", "observed_precision_relaxed")
    for method, run in runs.items():
        if method == "bm25":
            continue
        for k in cutoffs:
            groups = {name: [] for name in ("shared", "method_only", "bm25_only")}
            for qid in sorted(run, key=core.query_key):
                a, b = set(run[qid][:k]), set(runs["bm25"][qid][:k])
                core.require(len(a) == len(b) == k, f"Invalid ranking {method}/{qid}/{k}")
                for name, docs in (("shared", a & b), ("method_only", a - b), ("bm25_only", b - a)):
                    n = len(docs)
                    qlabels = labels[qid]
                    judged = sum(core.is_judged(qlabels.get(doc)) for doc in docs)
                    strict = sum(core.relevant(qlabels.get(doc), 2) for doc in docs)
                    relaxed = sum(core.relevant(qlabels.get(doc), 1) for doc in docs)
                    row = {
                        "method": method, "baseline": "bm25", "query_id": qid, "k": k,
                        "stratum": name, "n_pairs": n, "n_judged": judged,
                        "n_unjudged": n - judged,
                        "n_explicit_minus1": sum(qlabels.get(doc) == -1 for doc in docs),
                        "n_relevant_strict": strict, "n_relevant_relaxed": relaxed,
                        "judged_fraction": judged / n if n else None,
                        "hole_fraction": (n - judged) / n if n else None,
                        "observed_precision_strict": strict / n if n else None,
                        "observed_precision_relaxed": relaxed / n if n else None,
                    }
                    groups[name].append(row)
                    by_query.append(row)
            for name, rows in groups.items():
                totals = {field: sum(row[field] for row in rows) for field in counts}
                n = totals["n_pairs"]
                summary.append({
                    "method": method, "baseline": "bm25", "k": k, "stratum": name,
                    "n_queries": len(rows), "n_nonempty_queries": sum(row["n_pairs"] > 0 for row in rows),
                    **totals,
                    "pooled_judged_fraction": totals["n_judged"] / n if n else None,
                    "pooled_hole_fraction": totals["n_unjudged"] / n if n else None,
                    "pooled_observed_precision_strict": totals["n_relevant_strict"] / n if n else None,
                    "pooled_observed_precision_relaxed": totals["n_relevant_relaxed"] / n if n else None,
                    **{f"macro_nonempty_{field}": mean_defined(row[field] for row in rows) for field in fractions},
                })
    return by_query, summary


def bound_tables(runs, labels, cutoffs=(20, 100)):
    by_query, summary = [], []
    for method, run in runs.items():
        if method == "bm25":
            continue
        for k in cutoffs:
            for rule, threshold in core.THRESHOLDS:
                rows = []
                for qid in sorted(run, key=core.query_key):
                    core.require(len(run[qid]) >= k and len(runs["bm25"][qid]) >= k, f"Short run {method}/{qid}")
                    rows.append({
                        "method_a": method, "method_b": "bm25", "query_id": qid,
                        "k": k, "label_rule": rule,
                        **core.paired_precision_bounds(run[qid][:k], runs["bm25"][qid][:k], labels[qid], threshold),
                    })
                by_query.extend(rows)
                summary.append({
                    "method_a": method, "method_b": "bm25", "k": k, "label_rule": rule,
                    "n_queries": len(rows),
                    **{f"mean_{field}": core.average(row[field] for row in rows) for field in ("observed_delta", "lower_bound", "upper_bound")},
                    **{f"total_{field}": sum(row[field] for row in rows) for field in ("unjudged_a", "unjudged_b", "unjudged_shared", "unjudged_a_only", "unjudged_b_only")},
                    "n_queries_a_guaranteed_higher": sum(row["lower_bound"] > 0 for row in rows),
                    "n_queries_b_guaranteed_higher": sum(row["upper_bound"] < 0 for row in rows),
                    "n_queries_tie_possible": sum(row["lower_bound"] <= 0 <= row["upper_bound"] for row in rows),
                })
    return by_query, summary


def set_invariance_checks(runs, labels, depth=1000):
    rows = []
    for method, source in (("bm25_ce", "bm25"), ("direct_mmr_rerank", "direct")):
        for qid in sorted(runs[source], key=core.query_key):
            a, b = runs[method][qid][:depth], runs[source][qid][:depth]
            core.require(len(a) == len(b) == depth, f"Short set check for {method}/{qid}")
            identical = set(a) == set(b)
            core.require(identical, f"{method}/{qid}: saved candidate set differs from {source} at {depth}")
            qlabels = labels[qid]
            rows.append({
                "method": method, "candidate_source": source, "query_id": qid, "k": depth,
                "n_method_only": len(set(a) - set(b)), "n_source_only": len(set(b) - set(a)),
                "identical_sets": int(identical),
                "n_positions_changed": sum(x != y for x, y in zip(a, b)),
                "judged_count_delta": sum(core.is_judged(qlabels.get(doc)) for doc in a) - sum(core.is_judged(qlabels.get(doc)) for doc in b),
                "relevant_count_delta_strict": sum(core.relevant(qlabels.get(doc), 2) for doc in a) - sum(core.relevant(qlabels.get(doc), 2) for doc in b),
                "relevant_count_delta_relaxed": sum(core.relevant(qlabels.get(doc), 1) for doc in a) - sum(core.relevant(qlabels.get(doc), 1) for doc in b),
            })
    return rows


def pilot_full50_overlap_tables(pilot_runs, full_runs, cutoffs=CUTOFFS):
    """Compare each preserved pilot sequence with the corresponding full run."""
    by_query, summary = [], []
    for method, run in pilot_runs.items():
        core.require(method in full_runs, f"Missing full-query run for pilot method {method}")
        for k in cutoffs:
            rows = []
            for qid in sorted(run, key=core.query_key):
                core.require(qid in full_runs[method], f"Missing full-query ranking {method}/{qid}")
                pilot, full = run[qid][:k], full_runs[method][qid][:k]
                core.require(len(pilot) == len(full) == k, f"Short pilot/full comparison {method}/{qid}/{k}")
                a, b = set(pilot), set(full)
                core.require(len(a) == len(b) == k, f"Duplicate pilot/full document {method}/{qid}/{k}")
                shared = len(a & b)
                rows.append({
                    "method": method, "query_id": qid, "k": k,
                    "n_shared": shared, "n_pilot_only": len(a - b), "n_full50_only": len(b - a),
                    "overlap_fraction": shared / k,
                    "same_sequence": int(pilot == full),
                    "n_same_positions": sum(x == y for x, y in zip(pilot, full)),
                })
            by_query.extend(rows)
            summary.append({
                "method": method, "k": k, "n_queries": len(rows),
                "total_shared": sum(row["n_shared"] for row in rows),
                "mean_overlap_fraction": core.average(row["overlap_fraction"] for row in rows),
                "n_identical_sets": sum(row["n_shared"] == k for row in rows),
                "n_same_sequence": sum(row["same_sequence"] for row in rows),
                "total_same_positions": sum(row["n_same_positions"] for row in rows),
            })
    return by_query, summary


def candidate_membership_tables(runs, labels, cutoffs=CUTOFFS, baseline_depth=1000):
    """Membership in the saved BM25 candidate set, not full lexical reachability."""
    by_query, summary = [], []
    for method, run in runs.items():
        if method == "bm25":
            continue
        for k in cutoffs:
            inside_name, outside_name = f"in_bm25_top{baseline_depth}", f"outside_bm25_top{baseline_depth}"
            groups = {inside_name: [], outside_name: []}
            for qid in sorted(run, key=core.query_key):
                candidates = set(runs["bm25"][qid][:baseline_depth])
                core.require(len(candidates) == baseline_depth, f"Short BM25 candidate set for {qid}")
                core.require(len(run[qid]) >= k, f"Short run {method}/{qid}")
                for inside, name in ((True, inside_name), (False, outside_name)):
                    docs = [doc for doc in run[qid][:k] if (doc in candidates) == inside]
                    n = len(docs)
                    judged = sum(core.is_judged(labels[qid].get(doc)) for doc in docs)
                    row = {
                        "method": method, "query_id": qid, "k": k,
                        "bm25_candidate_depth": baseline_depth, "stratum": name,
                        "n_pairs": n, "n_judged": judged, "n_unjudged": n - judged,
                        "retrieved_fraction": n / k,
                        "judged_fraction": judged / n if n else None,
                    }
                    by_query.append(row)
                    groups[name].append(row)
            for name, rows in groups.items():
                n = sum(row["n_pairs"] for row in rows)
                judged = sum(row["n_judged"] for row in rows)
                summary.append({
                    "method": method, "k": k, "bm25_candidate_depth": baseline_depth,
                    "stratum": name, "n_queries": len(rows),
                    "n_nonempty_queries": sum(row["n_pairs"] > 0 for row in rows),
                    "n_pairs": n, "n_judged": judged, "n_unjudged": n - judged,
                    "mean_retrieved_fraction": core.average(row["retrieved_fraction"] for row in rows),
                    "pooled_judged_fraction": judged / n if n else None,
                    "macro_nonempty_judged_fraction": mean_defined(row["judged_fraction"] for row in rows),
                })
    return by_query, summary


def analyze(data_dir, output_dir):
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    query_path = data_dir / "trec-covid/queries.jsonl"
    qrel_path = data_dir / "trec-covid/qrels/test.tsv"
    metadata_path = data_dir / "corpus_metadata.csv.gz"
    queries = core.read_queries(query_path)
    metadata = core.read_metadata(metadata_path)
    core.require(len(queries) == 50, f"Expected 50 queries, found {len(queries)}")
    core.require(len(metadata) == 171332, f"Expected 171332 documents, found {len(metadata)}")
    labels = core.read_qrels(qrel_path, queries, metadata)
    registry_path = data_dir / "method_registry.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise core.DataError(f"{registry_path}: malformed JSON") from exc
    core.require(isinstance(registry, dict) and isinstance(registry.get("methods"), list), "Method registry must contain a methods list")
    records = registry["methods"]
    core.require(all(isinstance(row, dict) for row in records), "Invalid method record")
    core.require([row.get("method") for row in records] == list(METHODS), "Method registry must list the twelve release methods in expected order")
    paths, runs = [query_path, qrel_path, metadata_path, registry_path], {}
    for record in records:
        method = record["method"]
        core.require(record.get("n_queries") == 50 and record.get("depth") == 1000, f"Invalid dimensions for {method}")
        core.require(isinstance(record.get("run_file"), str), f"Missing run_file for {method}")
        relative = Path(record["run_file"])
        core.require(not relative.is_absolute() and ".." not in relative.parts, f"run_file must be within data: {relative}")
        core.require(bool(record.get("ordering")) and bool(record.get("score_kind")), f"Missing score/order semantics for {method}")
        path = data_dir / relative
        if record["ordering"] == "score_descending":
            runs[method] = core.read_run(path, queries, metadata)
        else:
            runs[method] = read_saved_run(path, queries, metadata, allow_unscored=method == "uniform_random")
        paths.append(path)

    pilot_ids = registry.get("pilot_query_ids")
    pilot_methods = registry.get("pilot_methods")
    core.require(pilot_ids == ["9", "13", "34", "45", "48"], "Unexpected pilot query set")
    core.require(isinstance(pilot_methods, list) and len(pilot_methods) == 8 and len(set(pilot_methods)) == 8 and all(method in METHODS for method in pilot_methods), "Expected eight distinct known pilot methods")
    pilot_queries = {qid: queries[qid] for qid in pilot_ids}
    pilot_labels = {qid: labels[qid] for qid in pilot_ids}
    pilot_runs = {}
    for method in pilot_methods:
        path = data_dir / f"runs/pilot/{method}.tsv.gz"
        record = next(row for row in records if row["method"] == method)
        if record["ordering"] == "score_descending":
            pilot_runs[method] = core.read_run(path, pilot_queries, metadata)
        else:
            pilot_runs[method] = read_saved_run(path, pilot_queries, metadata, allow_unscored=method == "uniform_random")
        paths.append(path)

    outputs = {}
    jobs = (
        ("coverage", lambda: core.coverage_tables(runs, labels)),
        ("observed_ir", lambda: observed_ir_tables(runs, labels)),
        ("overlap_vs_bm25", lambda: overlap_tables(runs)),
        ("judged_shared_exclusive", lambda: strata_tables(runs, labels)),
        ("paired_precision_bounds", lambda: bound_tables(runs, labels)),
        ("bm25_candidate_membership", lambda: candidate_membership_tables(runs, labels)),
        ("pilot_coverage", lambda: core.coverage_tables(pilot_runs, pilot_labels)),
        ("pilot_observed_ir", lambda: observed_ir_tables(pilot_runs, pilot_labels)),
        ("pilot_full50_overlap", lambda: pilot_full50_overlap_tables(pilot_runs, runs)),
    )
    for stem, job in jobs:
        per_query, summary = job()
        outputs[f"{stem}_by_query.csv"] = per_query
        outputs[f"{stem}_summary.csv"] = summary
    outputs["set_invariance_checks.csv"] = set_invariance_checks(runs, labels)
    checks = {
        "schema_version": 1,
        "scope": "I recompute twelve completed full-query conditions and eight five-query pilot conditions from saved ranks and released qrels; this command does not rerun retrieval or generate new labels.",
        "n_queries": len(queries), "n_corpus_documents": len(metadata),
        "methods_in_output_order": list(METHODS), "run_depth": 1000,
        "run_rows": {method: sum(len(docs) for docs in run.values()) for method, run in runs.items()},
        "pilot_query_ids": pilot_ids,
        "pilot_run_rows": {method: sum(len(docs) for docs in run.values()) for method, run in pilot_runs.items()},
        "pilot_full50_comparison": "I compare the saved pilot rankings with the same query IDs in the full-query runs at each cutoff, reporting document-set overlap and exact rank-sequence agreement.",
        "cutoffs": list(CUTOFFS), "label_rules": [name for name, _ in core.THRESHOLDS],
        "judged_labels": [0, 1, 2], "unjudged": "Absent qrel or explicit -1.",
        "ranking_order": ORDERING,
        "method_registry": records,
        "observed_metric_convention": "Precision = known relevant count / k; recall = known relevant retrieved count / all known relevant qrels for the query. Unjudged pairs contribute zero observed hits. Recall for a query with no known relevant qrels is undefined and omitted from the macro mean; the included query count is reported.",
        "strata_convention": "Shared, method-only, and BM25-only sets at equal depth; pooled fractions weight query-document pairs, macro_nonempty fractions average only nonempty query strata. Empty denominators are blank, not zero.",
        "candidate_membership_convention": "Inside/outside the released BM25 top-1000 set only. Outside does not imply zero lexical score or non-retrievability by a larger candidate pool.",
        "bounds_assumptions": "Rankings and existing 0/1/2 labels fixed; one binary relevance value per unjudged query-document pair, shared across methods. Bounds are on method-minus-BM25 precision and are sharp under these assumptions.",
        "validation": {"known_ids": True, "unique_run_pairs": True, "contiguous_ranks": True,
                       "finite_scores_or_empty_uniform_random_score": True, "equal_query_sets": True,
                       "descending_score_order_and_corpus_ties_verified": [row["method"] for row in records if row["ordering"] == "score_descending"],
                       "extension_order_preserved_as_saved": True,
                       "set_invariance_checked_query_pairs": len(outputs["set_invariance_checks.csv"]),
                       "set_invariance_all_passed": True},
        "input_sha256": {str(path.relative_to(data_dir)): core.sha256(path) for path in sorted(paths)},
        "output_rows": {name: len(rows) for name, rows in outputs.items()},
    }
    # Input and invariance failures above leave the output directory untouched.
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in outputs.items():
        core.write_csv(output_dir / name, rows)
    core.write_json(output_dir / "reproduction_checks.json", checks)
    return len(outputs) + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("results/extensions"))
    args = parser.parse_args()
    try:
        count = analyze(args.data_dir, args.output_dir)
    except (core.DataError, OSError, csv.Error) as exc:
        print(f"Input/analysis error: {exc}", file=sys.stderr)
        return 1
    print(f"Validated twelve full-query and eight pilot conditions; wrote {count} result files to {args.output_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
