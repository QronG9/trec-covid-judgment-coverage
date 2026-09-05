"""I generate rankings for all 50 queries using SPLADE, BGE, and BM25 + CrossEncoder.
BM25 + CrossEncoder preserves the BM25 top-1000 candidate set and recomputes the document order."""
from __future__ import annotations

import json
import pathlib

import numpy as np
import scipy.sparse as sp

from ext_common import (BGE_MODEL, BGE_QUERY_PREFIX, CROSS_ENCODER_MODEL, EXT_CACHE,
                        EXT_RUNS, K_DEPTHS, N_SELECT, ROOT, SPLADE_MODEL, Timer, device,
                        dir_size_mb, log, peak_rss_gb, record_actual, save_run, top_k)

SPLADE_NPZ = EXT_CACHE / "splade_doc_index.npz"
SPLADE_META = EXT_CACHE / "splade_doc_index.meta.json"
BGE_NPY = EXT_CACHE / "bge_doc_emb.npy"
BGE_META = EXT_CACHE / "bge_doc_emb.meta.json"

N_DOCS = int(np.load(ROOT / "cache" / "doc_ids.npy", allow_pickle=True).shape[0])

def reuse_cache(artifact: pathlib.Path, meta: pathlib.Path, model: str, n_docs: int) -> bool:

    if not artifact.exists():
        return False
    if not meta.exists():
        raise RuntimeError(
            f"{artifact.name} exists but {meta.name} does not, so the model that "
            f"produced it cannot be verified. Move the artifact aside and re-run to "
            f"rebuild it; do not assume it came from {model}.")
    rec = json.load(open(meta))
    if rec.get("model") != model or int(rec.get("n", -1)) != n_docs:
        raise RuntimeError(
            f"{artifact.name} was built by model={rec.get('model')!r} over "
            f"n={rec.get('n')} documents, but this run requests model={model!r} over "
            f"n={n_docs}. Refusing to reuse it.")
    return True

def corpus_texts():

    from common import doc_repr, load_corpus
    _, titles, texts = load_corpus()
    return [doc_repr(t, x) for t, x in zip(titles, texts)]

def build_splade_index(batch_size: int = 32):
    if reuse_cache(SPLADE_NPZ, SPLADE_META, SPLADE_MODEL, N_DOCS):
        log("SPLADE document index cached")
        return
    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    dev = device()
    log(f"SPLADE: loading {SPLADE_MODEL} on {dev}")
    tok = AutoTokenizer.from_pretrained(SPLADE_MODEL)
    model = AutoModelForMaskedLM.from_pretrained(SPLADE_MODEL).to(dev).eval()
    docs = corpus_texts()
    V = model.config.vocab_size

    rows, cols, vals = [], [], []
    with Timer("SPLADE corpus pass") as t, torch.inference_mode():
        for start in range(0, len(docs), batch_size):
            chunk = docs[start:start + batch_size]
            enc = tok(chunk, padding=True, truncation=True, max_length=256,
                      return_tensors="pt").to(dev)
            logits = model(**enc).logits

            act = torch.log1p(torch.relu(logits)) * enc["attention_mask"].unsqueeze(-1)
            vecs = act.max(dim=1).values
            vecs = vecs.to("cpu").float().numpy()
            for i, v in enumerate(vecs):
                nz = np.flatnonzero(v)
                rows.append(np.full(nz.size, start + i, dtype=np.int32))
                cols.append(nz.astype(np.int32))
                vals.append(v[nz].astype(np.float32))
            if (start // batch_size) % 200 == 0:
                log(f"  SPLADE {start + len(chunk):,}/{len(docs):,} docs")
    M = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                      shape=(len(docs), V))
    sp.save_npz(SPLADE_NPZ, M)
    json.dump(dict(model=SPLADE_MODEL, n=int(M.shape[0]), vocab=int(M.shape[1]),
                   nnz=int(M.nnz), terms_per_doc=round(M.nnz / M.shape[0], 1),
                   device=dev, max_length=256, pooling="max over log(1+relu(logits))",
                   dtype="float32/int32 CSR", seconds=round(t.seconds, 1)),
              open(SPLADE_META, "w"), indent=2)
    log(f"  SPLADE index: {M.shape}, nnz={M.nnz:,} "
        f"({M.nnz / M.shape[0]:.0f} terms/doc), {dir_size_mb(SPLADE_NPZ):.0f} MB")
    record_actual("tierB::splade_index", seconds=round(t.seconds, 1),
                  peak_rss_gb=round(peak_rss_gb(), 2), disk_mb=round(dir_size_mb(SPLADE_NPZ), 1),
                  nnz=int(M.nnz), terms_per_doc=round(M.nnz / M.shape[0], 1),
                  model=SPLADE_MODEL, device=device(), max_length=256)

def run_splade(qids, queries):
    if (EXT_RUNS / "splade.npz").exists():
        log("SPLADE run cached")
        return
    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    dev = device()
    tok = AutoTokenizer.from_pretrained(SPLADE_MODEL)
    model = AutoModelForMaskedLM.from_pretrained(SPLADE_MODEL).to(dev).eval()
    M = sp.load_npz(SPLADE_NPZ).tocsc()
    I, S = [], []
    with Timer("SPLADE retrieval") as t, torch.inference_mode():
        for q in qids:
            enc = tok([queries[q]["text"]], padding=True, truncation=True,
                      max_length=256, return_tensors="pt").to(dev)
            logits = model(**enc).logits
            act = torch.log1p(torch.relu(logits)) * enc["attention_mask"].unsqueeze(-1)
            qv = act.max(dim=1).values[0].to("cpu").float().numpy()
            nz = np.flatnonzero(qv)
            scores = np.zeros(M.shape[0], dtype=np.float64)
            for j in nz:
                lo, hi = M.indptr[j], M.indptr[j + 1]
                scores[M.indices[lo:hi]] += float(qv[j]) * M.data[lo:hi]
            idx = top_k(scores, N_SELECT)
            I.append(idx)
            S.append(scores[idx])
    save_run("SPLADE", qids, I, S,
             dict(model=SPLADE_MODEL, device=dev, max_length=256,
                  pooling="max over log(1+relu(logits)), attention-masked",
                  scoring="sparse dot product in vocabulary space",
                  seconds=round(t.seconds, 1)))
    record_actual("tierB::splade_run", seconds=round(t.seconds, 1),
                  peak_rss_gb=round(peak_rss_gb(), 2))

def build_bge_embeddings(batch_size: int = 96):
    if reuse_cache(BGE_NPY, BGE_META, BGE_MODEL, N_DOCS):
        log("BGE document embeddings cached")
        return
    from sentence_transformers import SentenceTransformer

    dev = device()
    log(f"BGE: loading {BGE_MODEL} on {dev}")
    model = SentenceTransformer(BGE_MODEL, device=dev)
    docs = corpus_texts()
    with Timer("BGE corpus pass") as t:
        emb = model.encode(docs, batch_size=batch_size, convert_to_numpy=True,
                           normalize_embeddings=True, show_progress_bar=True)
    emb = np.ascontiguousarray(emb.astype(np.float32))
    assert np.isfinite(emb).all(), "non-finite BGE embeddings"
    np.save(BGE_NPY, emb)
    json.dump(dict(model=BGE_MODEL, n=int(emb.shape[0]), dim=int(emb.shape[1]),
                   device=dev, normalized=True,
                   max_seq_length=int(model.max_seq_length),
                   doc_prefix="(none — BGE v1.5 documents take no prefix)",
                   query_prefix=BGE_QUERY_PREFIX, seconds=round(t.seconds, 1)),
              open(BGE_META, "w"), indent=2)
    log(f"  BGE embeddings {emb.shape}, {dir_size_mb(BGE_NPY):.0f} MB")
    record_actual("tierB::bge_embeddings", seconds=round(t.seconds, 1),
                  peak_rss_gb=round(peak_rss_gb(), 2), disk_mb=round(dir_size_mb(BGE_NPY), 1),
                  model=BGE_MODEL, device=dev, shape=list(emb.shape))

def run_bge(qids, queries):
    if (EXT_RUNS / "bge.npz").exists():
        log("BGE run cached")
        return
    from sentence_transformers import SentenceTransformer

    dev = device()
    model = SentenceTransformer(BGE_MODEL, device=dev)
    emb = np.load(BGE_NPY, mmap_mode="r")
    I, S = [], []
    with Timer("BGE retrieval") as t:
        for q in qids:
            qv = model.encode([BGE_QUERY_PREFIX + queries[q]["text"]],
                              convert_to_numpy=True, normalize_embeddings=True,
                              show_progress_bar=False)[0].astype(np.float32)
            scores = np.asarray(emb @ qv, dtype=np.float64)
            idx = top_k(scores, N_SELECT)
            I.append(idx)
            S.append(scores[idx])
    save_run("BGE (dense #2)", qids, I, S,
             dict(model=BGE_MODEL, device=dev, query_prefix=BGE_QUERY_PREFIX,
                  similarity="cosine (L2-normalised dot product)",
                  seconds=round(t.seconds, 1)))
    record_actual("tierB::bge_run", seconds=round(t.seconds, 1),
                  peak_rss_gb=round(peak_rss_gb(), 2))

def run_bm25_crossencoder(qids, queries, cand_depth: int = N_SELECT, batch_size: int = 128):
    if (EXT_RUNS / "bm25_ce.npz").exists():
        log("BM25+CrossEncoder run cached")
        return
    from sentence_transformers import CrossEncoder

    from ext_common import load_run as _lr
    bm25 = _lr("BM25")
    docs = corpus_texts()
    dev = device()
    log(f"CrossEncoder: loading {CROSS_ENCODER_MODEL} on {dev}")
    ce = CrossEncoder(CROSS_ENCODER_MODEL, device=dev, max_length=512)

    I, S = [], []
    with Timer("BM25+CrossEncoder reranking") as t:
        for n, q in enumerate(qids, 1):
            cand = bm25[q][0][:cand_depth]
            pairs = [(queries[q]["text"], docs[d]) for d in cand]
            scores = np.asarray(ce.predict(pairs, batch_size=batch_size,
                                           show_progress_bar=False), dtype=np.float64)

            order = np.lexsort((cand, -scores))
            I.append(cand[order])
            S.append(scores[order])
            if n % 10 == 0:
                log(f"  reranked {n}/{len(qids)} queries")
    save_run("BM25 + CrossEncoder", qids, I, S,
             dict(model=CROSS_ENCODER_MODEL, device=dev, max_length=512,
                  candidate_source="frozen Stage-1 BM25 run", candidate_depth=cand_depth,
                  note=("candidate universe is held fixed at BM25's top-1000; only the "
                        "ranking function changes"),
                  seconds=round(t.seconds, 1)))
    record_actual("tierB::bm25_ce", seconds=round(t.seconds, 1),
                  peak_rss_gb=round(peak_rss_gb(), 2), model=CROSS_ENCODER_MODEL,
                  n_pairs=len(qids) * cand_depth, candidate_depth=cand_depth)

def main():
    from common import load_queries

    queries = load_queries()
    qids = sorted(queries, key=lambda x: int(x))
    assert len(qids) == 50

    log("=== B3: BM25 + CrossEncoder (cheapest, no corpus pass) ===")
    run_bm25_crossencoder(qids, queries)

    log("=== B1: SPLADE ===")
    build_splade_index()
    run_splade(qids, queries)

    log("=== B2: BGE ===")
    build_bge_embeddings()
    run_bge(qids, queries)

    log("Tier B complete")

if __name__ == "__main__":
    main()
