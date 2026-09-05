#!/usr/bin/env python3
"""Recompute descriptive diagnostics from saved rankings and raw TREC-COVID qrels.

Python standard library only. Existing labels are held fixed; absent qrels and
explicit -1 labels are unjudged. Precision bounds concern these saved rankings,
not a hypothetical reranking, mechanism of missingness, or downstream outcome.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
import sys
from collections import Counter
from pathlib import Path


METHODS = ("bm25", "mpnet", "direct")
CUTOFFS = (20, 50, 100, 1000)
PAIRINGS = (("mpnet", "bm25"), ("direct", "bm25"), ("mpnet", "direct"))
JUDGED_LABELS = frozenset((0, 1, 2))
ALLOWED_LABELS = JUDGED_LABELS | {-1}
THRESHOLDS = (("strict_eq2", 2), ("relaxed_ge1", 1))


class DataError(ValueError):
    """An input violates the release data contract."""


def query_key(value):
    return (0, int(value), value) if value.isdecimal() else (1, value, value)


def require(condition, message):
    if not condition:
        raise DataError(message)


def open_text(path):
    path = Path(path)
    return gzip.open(path, "rt", encoding="utf-8", newline="") if path.suffix == ".gz" else path.open(encoding="utf-8", newline="")


def integer(value, context):
    try:
        return int(value)
    except (ValueError, TypeError) as exc:
        raise DataError(f"{context}: invalid integer {value!r}") from exc


def boolean(value, context):
    if value.lower() in ("true", "1"):
        return True
    if value.lower() in ("false", "0"):
        return False
    raise DataError(f"{context}: invalid boolean {value!r}")


def read_queries(path):
    result = {}
    with open_text(path) as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DataError(f"{path}:{line_number}: malformed JSON") from exc
            require(isinstance(row, dict), f"{path}:{line_number}: query must be an object")
            query_id = row.get("_id")
            require(isinstance(query_id, str) and bool(query_id), f"{path}:{line_number}: missing string _id")
            require(query_id not in result, f"{path}:{line_number}: duplicate query {query_id}")
            require(isinstance(row.get("text"), str), f"{path}:{line_number}: missing query text")
            result[query_id] = row
    require(bool(result), f"{path}: no queries")
    return result


def read_metadata(path):
    result = {}
    indices = set()
    with open_text(path) as stream:
        reader = csv.DictReader(stream)
        fields = {"corpus_index", "doc_id", "has_title", "has_abstract", "title_chars", "abstract_chars"}
        require(fields.issubset(reader.fieldnames or ()), f"{path}: missing metadata columns")
        for line_number, row in enumerate(reader, 2):
            context = f"{path}:{line_number}"
            doc_id = row["doc_id"]
            require(bool(doc_id), f"{context}: empty doc_id")
            require(doc_id not in result, f"{context}: duplicate doc_id {doc_id}")
            index = integer(row["corpus_index"], context)
            require(index >= 0 and index not in indices, f"{context}: invalid/duplicate corpus_index {index}")
            indices.add(index)
            item = {"corpus_index": index}
            for field in ("title_chars", "abstract_chars"):
                item[field] = integer(row[field], context)
                require(item[field] >= 0, f"{context}: negative {field}")
            item["has_title"] = boolean(row["has_title"], context)
            item["has_abstract"] = boolean(row["has_abstract"], context)
            require(item["has_title"] == (item["title_chars"] > 0), f"{context}: inconsistent title flags")
            require(item["has_abstract"] == (item["abstract_chars"] > 0), f"{context}: inconsistent abstract flags")
            result[doc_id] = item
    require(bool(result), f"{path}: no metadata")
    require(indices == set(range(len(result))), f"{path}: corpus_index must cover 0..N-1")
    return result


def read_qrels(path, queries, metadata):
    result = {query_id: {} for query_id in queries}
    with open_text(path) as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        require({"query-id", "corpus-id", "score"}.issubset(reader.fieldnames or ()), f"{path}: missing BEIR qrel columns")
        for line_number, row in enumerate(reader, 2):
            context = f"{path}:{line_number}"
            query_id, doc_id = row["query-id"], row["corpus-id"]
            require(query_id in queries, f"{context}: unknown query_id {query_id}")
            require(doc_id in metadata, f"{context}: unknown doc_id {doc_id}")
            require(doc_id not in result[query_id], f"{context}: duplicate qrel pair {query_id}/{doc_id}")
            label = integer(row["score"], context)
            require(label in ALLOWED_LABELS, f"{context}: unsupported qrel label {label}")
            result[query_id][doc_id] = label
    return result


def read_run(path, queries, metadata, depth=1000, require_abstract=False):
    """Read ranks 1..depth, with descending scores and corpus-index tie breaks."""
    result = {}
    seen = {}
    previous_scores = {}
    with open_text(path) as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        require({"query_id", "doc_id", "rank", "score"}.issubset(reader.fieldnames or ()), f"{path}: missing run columns")
        for line_number, row in enumerate(reader, 2):
            context = f"{path}:{line_number}"
            query_id, doc_id = row["query_id"], row["doc_id"]
            require(query_id in queries, f"{context}: unknown query_id {query_id}")
            require(doc_id in metadata, f"{context}: unknown doc_id {doc_id}")
            docs = result.setdefault(query_id, [])
            query_seen = seen.setdefault(query_id, set())
            require(doc_id not in query_seen, f"{context}: duplicate run pair {query_id}/{doc_id}")
            rank = integer(row["rank"], context)
            require(rank == len(docs) + 1 and rank <= depth, f"{context}: noncontiguous/out-of-range rank {rank}")
            try:
                score = float(row["score"])
            except (ValueError, TypeError) as exc:
                raise DataError(f"{context}: invalid score") from exc
            require(math.isfinite(score), f"{context}: nonfinite score")
            if docs:
                previous_score = previous_scores[query_id]
                require(score <= previous_score, f"{context}: score increases with rank")
                if score == previous_score:
                    require(metadata[docs[-1]]["corpus_index"] < metadata[doc_id]["corpus_index"], f"{context}: exact-score tie is not ordered by ascending corpus_index")
            if require_abstract:
                require(metadata[doc_id]["has_abstract"], f"{context}: empty abstract in nonempty-abstract run")
            docs.append(doc_id)
            query_seen.add(doc_id)
            previous_scores[query_id] = score
    require(set(result) == set(queries), f"{path}: inconsistent query set")
    for query_id, docs in result.items():
        require(len(docs) == depth, f"{path}: query {query_id} has {len(docs)} rows, expected {depth}")
    return result


def is_judged(label):
    return label in JUDGED_LABELS


def relevant(label, threshold):
    require(threshold in (1, 2), "Relevance threshold must be 1 or 2")
    return is_judged(label) and label >= threshold


def paired_precision_bounds(docs_a, docs_b, labels, threshold=2):
    """Sharp bound for P@k(A)-P@k(B), fixing known labels and each ranking.

    Every unjudged query-document pair has one binary relevance variable shared
    across methods. Shared unjudged documents cancel in the difference. Exclusive
    B documents minimize it; exclusive A documents maximize it. Any endpoint is
    jointly attainable under these assumptions, independently across queries.
    """
    require(len(docs_a) == len(docs_b) and len(docs_a) > 0, "Bounds require nonempty equal-depth rankings")
    require(len(set(docs_a)) == len(docs_a) and len(set(docs_b)) == len(docs_b), "Bounds do not permit duplicate documents")
    require(all(label in ALLOWED_LABELS for label in labels.values()), "Unsupported qrel label")
    k = len(docs_a)
    set_a, set_b = set(docs_a), set(docs_b)
    unjudged_a = {doc for doc in set_a if not is_judged(labels.get(doc))}
    unjudged_b = {doc for doc in set_b if not is_judged(labels.get(doc))}
    observed_count_delta = sum(relevant(labels.get(doc), threshold) for doc in set_a) - sum(relevant(labels.get(doc), threshold) for doc in set_b)
    a_only, b_only = len(unjudged_a - unjudged_b), len(unjudged_b - unjudged_a)
    return {
        "observed_delta": observed_count_delta / k,
        "lower_bound": (observed_count_delta - b_only) / k,
        "upper_bound": (observed_count_delta + a_only) / k,
        "unjudged_a": len(unjudged_a),
        "unjudged_b": len(unjudged_b),
        "unjudged_shared": len(unjudged_a & unjudged_b),
        "unjudged_a_only": a_only,
        "unjudged_b_only": b_only,
    }


def average(values):
    values = list(values)
    return math.fsum(values) / len(values)


def coverage_tables(runs, labels, cutoffs=CUTOFFS):
    by_query, summary = [], []
    for method, run in runs.items():
        for k in cutoffs:
            rows = []
            for query_id in sorted(run, key=query_key):
                docs = run[query_id][:k]
                require(len(docs) == k, f"Run {method}/{query_id} is too short for k={k}")
                judged = sum(is_judged(labels[query_id].get(doc)) for doc in docs)
                row = {
                    "method": method, "query_id": query_id, "k": k,
                    "n_retrieved": k, "n_judged": judged, "n_unjudged": k - judged,
                    "n_explicit_minus1": sum(labels[query_id].get(doc) == -1 for doc in docs),
                    "judged_fraction": judged / k, "hole_fraction": (k - judged) / k,
                }
                rows.append(row)
            by_query.extend(rows)
            summary.append({
                "method": method, "k": k, "n_queries": len(rows),
                "n_retrieved": sum(row["n_retrieved"] for row in rows),
                "n_judged": sum(row["n_judged"] for row in rows),
                "n_unjudged": sum(row["n_unjudged"] for row in rows),
                "n_explicit_minus1": sum(row["n_explicit_minus1"] for row in rows),
                "mean_judged_fraction": average(row["judged_fraction"] for row in rows),
                "mean_hole_fraction": average(row["hole_fraction"] for row in rows),
            })
    return by_query, summary


def paired_coverage_tables(coverage):
    by_query, summary = [], []
    lookup = {(row["method"], row["query_id"], row["k"]): row for row in coverage}
    queries = sorted({row["query_id"] for row in coverage}, key=query_key)
    for method_a, method_b in PAIRINGS:
        for k in CUTOFFS:
            rows = []
            for query_id in queries:
                a, b = lookup[method_a, query_id, k], lookup[method_b, query_id, k]
                delta_count = a["n_judged"] - b["n_judged"]
                rows.append({
                    "method_a": method_a, "method_b": method_b, "query_id": query_id, "k": k,
                    "judged_count_delta_a_minus_b": delta_count,
                    "judged_fraction_delta_a_minus_b": delta_count / k,
                    "hole_count_delta_a_minus_b": -delta_count,
                    "hole_fraction_delta_a_minus_b": -delta_count / k,
                })
            by_query.extend(rows)
            summary.append({
                "method_a": method_a, "method_b": method_b, "k": k, "n_queries": len(rows),
                "mean_judged_fraction_delta_a_minus_b": average(row["judged_fraction_delta_a_minus_b"] for row in rows),
                "mean_hole_fraction_delta_a_minus_b": average(row["hole_fraction_delta_a_minus_b"] for row in rows),
                "n_a_higher": sum(row["judged_count_delta_a_minus_b"] > 0 for row in rows),
                "n_tied": sum(row["judged_count_delta_a_minus_b"] == 0 for row in rows),
                "n_b_higher": sum(row["judged_count_delta_a_minus_b"] < 0 for row in rows),
                "n_a_higher_hole": sum(row["hole_count_delta_a_minus_b"] > 0 for row in rows),
                "n_tied_hole": sum(row["hole_count_delta_a_minus_b"] == 0 for row in rows),
                "n_b_higher_hole": sum(row["hole_count_delta_a_minus_b"] < 0 for row in rows),
            })
    return by_query, summary


def precision_tables(runs, labels):
    by_query, summary = [], []
    for method, run in runs.items():
        for k in CUTOFFS:
            for label_rule, threshold in THRESHOLDS:
                rows = []
                for query_id in sorted(run, key=query_key):
                    count = sum(relevant(labels[query_id].get(doc), threshold) for doc in run[query_id][:k])
                    rows.append({"method": method, "query_id": query_id, "k": k, "label_rule": label_rule, "n_observed_relevant": count, "observed_precision": count / k})
                by_query.extend(rows)
                summary.append({"method": method, "k": k, "label_rule": label_rule, "n_queries": len(rows), "n_observed_relevant": sum(row["n_observed_relevant"] for row in rows), "mean_observed_precision": average(row["observed_precision"] for row in rows)})
    return by_query, summary


def bound_tables(runs, labels):
    by_query, summary = [], []
    for method_a, method_b in PAIRINGS:
        for k in (20, 100):
            for label_rule, threshold in THRESHOLDS:
                rows = []
                for query_id in sorted(labels, key=query_key):
                    values = paired_precision_bounds(runs[method_a][query_id][:k], runs[method_b][query_id][:k], labels[query_id], threshold)
                    rows.append({"method_a": method_a, "method_b": method_b, "query_id": query_id, "k": k, "label_rule": label_rule, **values})
                by_query.extend(rows)
                summary.append({
                    "method_a": method_a, "method_b": method_b, "k": k, "label_rule": label_rule, "n_queries": len(rows),
                    **{f"mean_{field}": average(row[field] for row in rows) for field in ("observed_delta", "lower_bound", "upper_bound")},
                    **{f"total_{field}": sum(row[field] for row in rows) for field in ("unjudged_a", "unjudged_b", "unjudged_shared", "unjudged_a_only", "unjudged_b_only")},
                    "n_queries_a_guaranteed_higher": sum(row["lower_bound"] > 0 for row in rows),
                    "n_queries_b_guaranteed_higher": sum(row["upper_bound"] < 0 for row in rows),
                    "n_queries_tie_possible": sum(row["lower_bound"] <= 0 <= row["upper_bound"] for row in rows),
                })
    return by_query, summary


def abstract_strata(runs, labels, metadata):
    result = []
    for method, run in runs.items():
        for k in CUTOFFS:
            for has_abstract in (False, True):
                selected = [(query_id, doc) for query_id in sorted(run, key=query_key) for doc in run[query_id][:k] if metadata[doc]["has_abstract"] == has_abstract]
                n = len(selected)
                judged = sum(is_judged(labels[query_id].get(doc)) for query_id, doc in selected)
                strict = sum(relevant(labels[query_id].get(doc), 2) for query_id, doc in selected)
                relaxed = sum(relevant(labels[query_id].get(doc), 1) for query_id, doc in selected)
                result.append({
                    "method": method, "k": k, "has_abstract": int(has_abstract),
                    "n_query_document_pairs": n, "n_judged": judged, "n_unjudged": n - judged,
                    "retrieved_share": n / (len(run) * k),
                    "n_observed_relevant_strict": strict, "n_observed_relevant_relaxed": relaxed,
                    "pooled_judged_fraction": judged / n if n else None,
                    "pooled_hole_fraction": (n - judged) / n if n else None,
                    "pooled_observed_precision_strict": strict / n if n else None,
                    "pooled_observed_precision_relaxed": relaxed / n if n else None,
                })
    return result


def unjudged_frame(runs, labels, metadata):
    frame = []
    all_union_pairs = 0
    method_pairs = {method: set() for method in METHODS}
    for query_id in sorted(labels, key=query_key):
        ranks = {method: {doc: rank for rank, doc in enumerate(runs[method][query_id][:20], 1)} for method in METHODS}
        union = set().union(*(set(items) for items in ranks.values()))
        all_union_pairs += len(union)
        for doc in sorted(union):
            if is_judged(labels[query_id].get(doc)):
                continue
            methods = [method for method in METHODS if doc in ranks[method]]
            for method in methods:
                method_pairs[method].add((query_id, doc))
            frame.append({
                "query_id": query_id, "doc_id": doc,
                **{f"{method}_rank": ranks[method].get(doc) for method in METHODS},
                "methods": ";".join(methods), "n_methods": len(methods),
                "judgment_status": "unjudged_minus1" if labels[query_id].get(doc) == -1 else "unjudged_absent_qrel",
                "has_title": int(metadata[doc]["has_title"]), "has_abstract": int(metadata[doc]["has_abstract"]),
            })
    counts = Counter(row["n_methods"] for row in frame)
    summary = {
        "scope": "Union of unjudged query-document pairs in the three saved top-20 rankings; diagnostic frame only, not a validated annotation protocol.",
        "n_unique_query_document_pairs": len(frame),
        "n_unique_documents": len({row["doc_id"] for row in frame}),
        "n_queries": len({row["query_id"] for row in frame}),
        "n_queries_with_unjudged": len({row["query_id"] for row in frame}),
        "n_total_queries": len(labels),
        "n_all_top20_union_pairs": all_union_pairs,
        "n_empty_abstract_pairs": sum(not row["has_abstract"] for row in frame),
        "n_explicit_minus1_pairs": sum(row["judgment_status"] == "unjudged_minus1" for row in frame),
        "by_method": {method: len(pairs) for method, pairs in method_pairs.items()},
        "by_number_of_methods": {str(n): counts[n] for n in (1, 2, 3)},
        "pairwise_intersections": {f"{a}__{b}": len(method_pairs[a] & method_pairs[b]) for a, b in itertools.combinations(METHODS, 2)},
        "by_exact_method_combination": dict(sorted(Counter(row["methods"] for row in frame).items())),
        "n_judged_controls": 0,
    }
    return frame, summary


def write_csv(path, rows):
    require(bool(rows), f"No rows generated for {path.name}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format(value, ".12g") if isinstance(value, float) else value for key, value in row.items()})


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze(data_dir, output_dir):
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    query_path = data_dir / "trec-covid/queries.jsonl"
    qrel_path = data_dir / "trec-covid/qrels/test.tsv"
    metadata_path = data_dir / "corpus_metadata.csv.gz"
    queries = read_queries(query_path)
    metadata = read_metadata(metadata_path)
    require(len(queries) == 50, f"Expected 50 benchmark queries, found {len(queries)}")
    require(len(metadata) == 171332, f"Expected 171332 corpus documents, found {len(metadata)}")
    labels = read_qrels(qrel_path, queries, metadata)
    input_paths = [query_path, qrel_path, metadata_path]
    runs = {}
    for method in METHODS:
        path = data_dir / f"runs/{method}.tsv.gz"
        runs[method] = read_run(path, queries, metadata)
        input_paths.append(path)
    optional_paths = {method: data_dir / f"runs/nonempty_abstract/{method}.tsv.gz" for method in ("bm25", "mpnet")}
    optional_present = [path.exists() for path in optional_paths.values()]
    require(all(optional_present) or not any(optional_present), "Supply both nonempty-abstract runs or neither")
    nonempty_runs = {}
    if all(optional_present):
        for method, path in optional_paths.items():
            nonempty_runs[method] = read_run(path, queries, metadata, require_abstract=True)
            input_paths.append(path)

    # Calculate everything before publishing outputs, so input failures write no results.
    coverage, coverage_summary = coverage_tables(runs, labels)
    paired, paired_summary = paired_coverage_tables(coverage)
    precision, precision_summary = precision_tables(runs, labels)
    bounds, bounds_summary = bound_tables(runs, labels)
    frame, union_summary = unjudged_frame(runs, labels, metadata)
    csv_outputs = {
        "coverage_by_query.csv": coverage, "coverage_summary.csv": coverage_summary,
        "paired_coverage_by_query.csv": paired, "paired_coverage_summary.csv": paired_summary,
        "observed_precision_by_query.csv": precision, "observed_precision_summary.csv": precision_summary,
        "paired_precision_bounds_by_query.csv": bounds, "paired_precision_bounds_summary.csv": bounds_summary,
        "abstract_strata.csv": abstract_strata(runs, labels, metadata),
        "top20_unjudged_frame.csv": frame,
    }
    if nonempty_runs:
        nonempty, nonempty_summary = coverage_tables(nonempty_runs, labels)
        csv_outputs["nonempty_coverage_by_query.csv"] = nonempty
        csv_outputs["nonempty_coverage_summary.csv"] = nonempty_summary
    label_counts = Counter(label for query_labels in labels.values() for label in query_labels.values())
    audit = {
        "schema_version": 1,
        "scope": "Descriptive reanalysis of fixed saved rankings; this command does not rerun retrieval.",
        "n_queries": len(queries), "n_corpus_documents": len(metadata),
        "n_documents_with_title": sum(row["has_title"] for row in metadata.values()),
        "n_documents_with_abstract": sum(row["has_abstract"] for row in metadata.values()),
        "n_documents_without_abstract": sum(not row["has_abstract"] for row in metadata.values()),
        "n_qrel_rows": sum(label_counts.values()),
        "qrel_label_counts": {str(label): label_counts[label] for label in sorted(ALLOWED_LABELS)},
        "n_judged_pairs": sum(label_counts[label] for label in JUDGED_LABELS),
        "n_unjudged_pairs_in_full_query_corpus_product": len(queries) * len(metadata) - sum(label_counts[label] for label in JUDGED_LABELS),
        "run_rows": {method: sum(len(docs) for docs in run.values()) for method, run in runs.items()},
        "nonempty_abstract_run_rows": {method: sum(len(docs) for docs in run.values()) for method, run in nonempty_runs.items()},
        "judged_labels": sorted(JUDGED_LABELS), "unjudged": "absent qrel or explicit label -1",
        "precision_convention": "Observed precision divides known relevant count by k; unjudged contributes zero to this conventional observed score, without asserting nonrelevance.",
        "bound_assumptions": "Fixed rankings; all existing 0/1/2 labels retained; each unjudged query-document pair may have either binary relevance value under the chosen threshold; values are shared across methods, independent across pairs.",
        "abstract_strata_convention": "Pooled retrieved query-document pairs within each abstract-presence stratum; descriptive associations, not causal effects.",
        "validation": {"known_ids": True, "unique_query_ids": True, "unique_corpus_ids_and_indices": True, "unique_qrel_pairs": True, "allowed_qrel_labels": True, "unique_run_pairs": True, "contiguous_ranks": True, "nonincreasing_finite_scores": True, "ascending_corpus_index_for_exact_ties": True, "equal_query_sets": True, "run_depth": 1000},
        "input_sha256": {str(path.relative_to(data_dir)): sha256(path) for path in sorted(input_paths)},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in csv_outputs.items():
        write_csv(output_dir / name, rows)
    write_json(output_dir / "data_audit.json", audit)
    write_json(output_dir / "top20_unjudged_union.json", union_summary)
    return len(csv_outputs) + 2


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, default=Path("data"), help="Release inputs (default: data).")
    parser.add_argument("--output-dir", type=Path, default=Path("results"), help="Write deterministic CSV/JSON here (default: results).")
    args = parser.parse_args()
    try:
        count = analyze(args.data_dir, args.output_dir)
    except (DataError, OSError, csv.Error) as exc:
        print(f"Input/analysis error: {exc}", file=sys.stderr)
        return 1
    print(f"Validated release inputs; wrote {count} result files to {args.output_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
