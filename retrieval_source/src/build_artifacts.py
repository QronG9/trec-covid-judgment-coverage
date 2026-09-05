"""我在这里构建语料顺序映射、分词缓存、BM25 索引和 MPNet 文档向量。"""
from __future__ import annotations

import json
import pickle
import time

import numpy as np

from bm25_index import SparseBM25Okapi, verify_against_rank_bm25
from common import (CACHE, SBERT_MODEL, doc_repr, load_corpus, load_queries,
                    make_tokenizer, log)

DOC_IDS = CACHE / "doc_ids.npy"
DOC_TITLES = CACHE / "doc_titles.pkl"
TOK_CORPUS = CACHE / "tokenized_corpus.pkl"
BM25_PKL = CACHE / "bm25_index.pkl"
EMB_NPY = CACHE / "doc_emb_mpnet.npy"
EMB_META = CACHE / "doc_emb_mpnet.meta.json"

def build_corpus_artifacts():
    if DOC_IDS.exists() and DOC_TITLES.exists() and TOK_CORPUS.exists():
        ids = np.load(DOC_IDS, allow_pickle=True)
        log(f"corpus artifacts cached ({len(ids)} docs)")
        return
    log("loading corpus ...")
    ids, titles, texts = load_corpus()
    np.save(DOC_IDS, np.array(ids, dtype=object), allow_pickle=True)
    with open(DOC_TITLES, "wb") as f:
        pickle.dump(titles, f, protocol=4)

    log("tokenizing corpus (Porter stem + English stopword removal) ...")
    tok = make_tokenizer()
    t0 = time.time()
    tokenized = []
    for i, (ti, tx) in enumerate(zip(titles, texts)):
        tokenized.append(tok(doc_repr(ti, tx)))
        if (i + 1) % 25000 == 0:
            log(f"  tokenized {i+1}/{len(ids)}  ({time.time()-t0:.0f}s)")
    with open(TOK_CORPUS, "wb") as f:
        pickle.dump(tokenized, f, protocol=4)
    log(f"tokenization done in {time.time()-t0:.0f}s")

def build_bm25():
    if BM25_PKL.exists():
        log("BM25 index cached")
        return
    with open(TOK_CORPUS, "rb") as f:
        tokenized = pickle.load(f)
    queries = load_queries()
    tok = make_tokenizer()
    tq = [tok(q["text"]) for q in queries.values()]

    log("verifying sparse BM25 against rank_bm25 on a 3,000-doc subsample ...")
    verify_against_rank_bm25(tokenized[:3000], tq[:10])

    log("building full BM25 index ...")
    t0 = time.time()
    idx = SparseBM25Okapi(tokenized)
    log(f"  vocab={len(idx.vocab):,} avgdl={idx.avgdl:.2f} nnz={idx.tf.nnz:,} "
        f"({time.time()-t0:.0f}s)")
    idx.save(BM25_PKL)

def build_embeddings(batch_size: int = 128):
    ids = np.load(DOC_IDS, allow_pickle=True)
    if EMB_NPY.exists() and EMB_META.exists():
        meta = json.load(open(EMB_META))
        if meta.get("n") == len(ids) and meta.get("model") == SBERT_MODEL:
            log(f"SBERT embeddings cached ({meta['n']} x {meta['dim']}, "
                f"device={meta.get('device')})")
            return
    import torch
    from sentence_transformers import SentenceTransformer

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    log(f"loading {SBERT_MODEL} on device={device}")
    model = SentenceTransformer(SBERT_MODEL, device=device)

    _, titles, texts = load_corpus()
    docs = [doc_repr(t, x) for t, x in zip(titles, texts)]

    if device == "mps":
        try:
            probe = docs[:16]
            a = model.encode(probe, convert_to_numpy=True, normalize_embeddings=True,
                             show_progress_bar=False)
            cpu_model = SentenceTransformer(SBERT_MODEL, device="cpu")
            b = cpu_model.encode(probe, convert_to_numpy=True, normalize_embeddings=True,
                                 show_progress_bar=False)
            diff = float(np.abs(a - b).max())
            log(f"  MPS-vs-CPU max abs embedding diff on 16 docs: {diff:.2e}")
            del cpu_model
            if not np.isfinite(diff) or diff > 5e-3:
                log("  MPS deviates too much -> falling back to CPU")
                device = "cpu"
                model = SentenceTransformer(SBERT_MODEL, device="cpu")
        except Exception as e:
            log(f"  MPS probe failed ({e}) -> falling back to CPU")
            device = "cpu"
            model = SentenceTransformer(SBERT_MODEL, device="cpu")

    log(f"encoding {len(docs):,} documents (batch={batch_size}) ...")
    t0 = time.time()
    emb = model.encode(docs, batch_size=batch_size, convert_to_numpy=True,
                       normalize_embeddings=True, show_progress_bar=True)
    emb = np.ascontiguousarray(emb.astype(np.float32))
    assert emb.shape[0] == len(ids)
    assert np.isfinite(emb).all(), "non-finite embeddings produced"
    np.save(EMB_NPY, emb)
    json.dump(dict(model=SBERT_MODEL, n=int(emb.shape[0]), dim=int(emb.shape[1]),
                   device=device, normalized=True, max_seq_length=int(model.max_seq_length),
                   seconds=round(time.time() - t0, 1)), open(EMB_META, "w"), indent=2)
    log(f"embeddings done in {time.time()-t0:.0f}s -> {EMB_NPY}")

def main():
    build_corpus_artifacts()
    build_bm25()
    build_embeddings()
    log("all artifacts ready")

if __name__ == "__main__":
    main()
