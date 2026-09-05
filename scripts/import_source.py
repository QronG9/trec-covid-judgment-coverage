#!/usr/bin/env python3
"""Export portable, text-free ranking artifacts from the local research workspace.

This optional provenance step requires numpy and the original trusted local caches.
The normal reproduction path (analyze.py) does not use pickle, numpy, or this script.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_gzip_csv(path, columns, rows, delimiter=","):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as out:
                writer = csv.writer(out, delimiter=delimiter, lineterminator="\n")
                writer.writerow(columns)
                writer.writerows(rows)


def export_metadata(corpus_path, output):
    def rows():
        with corpus_path.open(encoding="utf-8") as handle:
            for i, line in enumerate(handle):
                doc = json.loads(line)
                title = (doc.get("title") or "").strip()
                abstract = (doc.get("text") or "").strip()
                yield i, doc["_id"], int(bool(title)), int(bool(abstract)), len(title), len(abstract)
    write_gzip_csv(output, ["corpus_index", "doc_id", "has_title", "has_abstract", "title_chars", "abstract_chars"], rows())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Original stage1_pooling_bias directory")
    parser.add_argument("--score-workdir", type=Path, help="Saved full-corpus scores and query embeddings")
    parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    import numpy as np
    source, root = args.source.resolve(), args.output_root.resolve()
    dataset = source.parent / "trec-covid"
    data = root / "data"
    raw = data / "trec-covid"
    (raw / "qrels").mkdir(parents=True, exist_ok=True)
    inputs = []

    def record(path, label):
        inputs.append({"source_artifact": label, "bytes": path.stat().st_size, "sha256": sha256(path)})

    for name in ["corpus.jsonl", "queries.jsonl", "qrels/test.tsv"]:
        shutil.copy2(dataset / name, raw / name)
        record(dataset / name, "trec-covid/" + name)
    export_metadata(raw / "corpus.jsonl", data / "corpus_metadata.csv.gz")
    with gzip.open(data / "corpus_metadata.csv.gz", "rt", encoding="utf-8") as handle:
        metadata = list(csv.DictReader(handle))
    ids = [r["doc_id"] for r in metadata]
    # Original caches are local trusted research inputs, not downloaded pickle files.
    original_ids = np.load(source / "cache/doc_ids.npy", allow_pickle=True).tolist()
    if ids != original_ids:
        raise ValueError("Original document map differs from raw corpus order")
    record(source / "cache/doc_ids.npy", "stage1_pooling_bias/cache/doc_ids.npy")
    columns = ["query_id", "doc_id", "rank", "score"]
    for name, original in [("bm25", "bm25"), ("mpnet", "sbert"), ("direct", "direct")]:
        path = source / "cache/runs" / (original + ".npz")
        record(path, "stage1_pooling_bias/cache/runs/" + path.name)
        z = np.load(path, allow_pickle=True)
        rows = ((str(q), ids[int(idx)], rank, format(float(score), ".17g"))
                for q, indices, scores in zip(z["qids"], z["idx"], z["scores"])
                for rank, (idx, score) in enumerate(zip(indices, scores), 1))
        write_gzip_csv(data / "runs" / (name + ".tsv.gz"), columns, rows, "\t")

    if args.score_workdir:
        score_dir = args.score_workdir.resolve()
        score_path = score_dir / "bm25_all_scores.npy"
        query_path = score_dir / "query_embeddings_cpu.npy"
        embedding_path = source / "cache/doc_emb_mpnet.npy"
        for path, label in [(score_path, "representation_scores/bm25_all_scores.npy"),
                            (query_path, "representation_scores/query_embeddings_cpu.npy"),
                            (embedding_path, "stage1_pooling_bias/cache/doc_emb_mpnet.npy")]:
            record(path, label)
        scores = np.load(score_path, mmap_mode="r")
        queries = np.load(query_path)
        embeddings = np.load(embedding_path, mmap_mode="r")
        qids = sorted([json.loads(line)["_id"] for line in (raw / "queries.jsonl").read_text().splitlines()], key=int)
        eligible = np.asarray([i for i, r in enumerate(metadata) if r["has_abstract"] == "1"])
        rows_by_method = {"bm25": [], "mpnet": []}
        for qi, qid in enumerate(qids):
            for name, sc in [("bm25", scores[qi]), ("mpnet", np.asarray(embeddings @ queries[qi], float))]:
                top = eligible[np.lexsort((eligible, -sc[eligible]))[:1000]]
                rows_by_method[name].extend((qid, ids[int(idx)], rank, format(float(sc[idx]), ".17g"))
                                           for rank, idx in enumerate(top, 1))
        for name, rows in rows_by_method.items():
            write_gzip_csv(data / "runs/nonempty_abstract" / (name + ".tsv.gz"), columns, rows, "\t")
    provenance = root / "provenance"
    provenance.mkdir(exist_ok=True)
    (provenance / "import_inputs.json").write_text(json.dumps({
        "format_version": 1,
        "description": "Input hashes for converting original local artifacts into portable rankings and metadata. No new model was trained or new relevance label assigned.",
        "nonempty_rankings": "Saved full-corpus BM25 scores and CPU query vectors with original document vectors; original score order restricted to documents with nonempty abstracts, tie-break by corpus index.",
        "inputs": inputs,
    }, indent=2) + "\n", encoding="utf-8")
    print("Exported raw labels, queries, corpus metadata and portable rankings.")


if __name__ == "__main__":
    main()
