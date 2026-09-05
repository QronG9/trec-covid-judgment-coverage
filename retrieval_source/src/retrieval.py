"""I implement BM25, MPNet, Direct, two random-selection methods, MMR, and query expansion.
MMR uses greedy selection order and candidate-pool position to resolve ties; ordinary score-based rankings resolve ties by corpus index."""
from __future__ import annotations

import json
import pickle

import numpy as np

from bm25_index import SparseBM25Okapi
from build_artifacts import BM25_PKL, DOC_IDS, DOC_TITLES, EMB_META, EMB_NPY
from common import (CACHE, MMR_LAMBDA, MMR_POOL, N_SELECT, RETRIEVAL_RANDOM_POOL, RRF_K,
                    SBERT_MODEL, SEED, load_queries, make_tokenizer, log)

RUNS = CACHE / "runs"
RUNS.mkdir(exist_ok=True)

def top_k(scores: np.ndarray, k: int) -> np.ndarray:

    k = min(k, scores.shape[0])
    order = np.lexsort((np.arange(scores.shape[0]), -scores))
    return order[:k]

class Engine:

    def __init__(self):
        self.doc_ids = np.load(DOC_IDS, allow_pickle=True)
        with open(DOC_TITLES, "rb") as f:
            self.titles = pickle.load(f)
        self.n_docs = len(self.doc_ids)
        self.bm25 = SparseBM25Okapi.load(BM25_PKL)
        self._emb = None
        self.emb_meta = json.load(open(EMB_META)) if EMB_META.exists() else {}
        self.tok = make_tokenizer()
        self.queries = load_queries()
        self._qmodel = None
        log(f"Engine ready: {self.n_docs:,} docs, bm25 vocab {len(self.bm25.vocab):,}, "
            f"embeddings {'cached' if EMB_NPY.exists() else 'NOT BUILT YET'}")

    @property
    def emb(self):

        if self._emb is None:
            self._emb = np.load(EMB_NPY, mmap_mode="r")
        return self._emb

    def bm25_scores(self, text: str) -> np.ndarray:
        return self.bm25.get_scores(self.tok(text))

    def _query_model(self):
        if self._qmodel is None:
            import torch
            from sentence_transformers import SentenceTransformer
            dev = self.emb_meta.get("device", "cpu")
            if dev == "mps" and not torch.backends.mps.is_available():
                dev = "cpu"
            self._qmodel = SentenceTransformer(SBERT_MODEL, device=dev)
        return self._qmodel

    def embed_query(self, text: str) -> np.ndarray:
        v = self._query_model().encode([text], convert_to_numpy=True,
                                       normalize_embeddings=True, show_progress_bar=False)
        return np.ascontiguousarray(v[0].astype(np.float32))

    def sbert_scores(self, text: str) -> np.ndarray:

        return np.asarray(self.emb @ self.embed_query(text), dtype=np.float64)

    def run_bm25(self, qid: str, n: int = N_SELECT):
        s = self.bm25_scores(self.queries[qid]["text"])
        idx = top_k(s, n)
        return idx, s[idx]

    def run_sbert(self, qid: str, n: int = N_SELECT):
        s = self.sbert_scores(self.queries[qid]["text"])
        idx = top_k(s, n)
        return idx, s[idx]

    def run_direct(self, qid: str, n: int = N_SELECT, variant: str = "max"):

        qt = self.queries[qid]["text"]
        bs = self.bm25_scores(qt)
        ss = self.sbert_scores(qt)
        cand = np.union1d(top_k(bs, n), top_k(ss, n))
        b, s = bs[cand], ss[cand]
        if variant == "max":
            bn = b / b.max() if b.max() != 0 else np.zeros_like(b)
            sn = s / s.max() if s.max() != 0 else np.zeros_like(s)
        elif variant == "minmax":
            bn = (b - b.min()) / (b.max() - b.min()) if b.max() > b.min() else np.zeros_like(b)
            sn = (s - s.min()) / (s.max() - s.min()) if s.max() > s.min() else np.zeros_like(s)
        else:
            raise ValueError(variant)
        fused = bn + sn

        order = np.lexsort((cand, -fused))[:n]
        return cand[order], fused[order]

    def run_random(self, qid: str, n: int = N_SELECT, rng: np.random.Generator | None = None):
        rng = rng if rng is not None else np.random.default_rng(SEED)
        idx = rng.choice(self.n_docs, size=n, replace=False)
        return idx, np.full(n, np.nan)

    def run_direct_mmr(self, qid: str, n: int = N_SELECT, pool: int = MMR_POOL,
                       lam: float = MMR_LAMBDA):

        cand, _ = self.run_direct(qid, n=pool)
        q = self.embed_query(self.queries[qid]["text"])
        D = np.ascontiguousarray(self.emb[cand])
        rel = D @ q
        selected: list[int] = []
        best_sim = np.full(len(cand), -np.inf)
        avail = np.ones(len(cand), dtype=bool)
        for _ in range(min(n, len(cand))):
            if not selected:
                mmr = rel.copy()
            else:
                mmr = lam * rel - (1 - lam) * best_sim
            mmr_masked = np.where(avail, mmr, -np.inf)

            j = int(np.lexsort((np.arange(len(cand)), -mmr_masked))[0])
            selected.append(j)
            avail[j] = False
            sims = D @ D[j]
            best_sim = np.maximum(best_sim, sims) if selected[:-1] else sims
        sel = np.array(selected)

        return cand[sel], rel[sel].astype(np.float64)

    def keybert_keywords(self, qid: str, top_k_kw: int = 5, diversity: float = 0.7):

        import re
        from nltk.corpus import stopwords
        sw = set(stopwords.words("english"))
        text = self.queries[qid]["text"]

        words = [w.lower() for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]*", text)
                 if w.lower() not in sw]
        cands = []
        for i in range(len(words)):
            for size in (1, 2):
                if i + size > len(words):
                    continue
                c = " ".join(words[i:i + size])
                if c not in cands:
                    cands.append(c)
        if not cands:
            return []
        m = self._query_model()
        cv = m.encode(cands, convert_to_numpy=True, normalize_embeddings=True,
                      show_progress_bar=False)
        qv = self.embed_query(text)
        sim_q = cv @ qv
        sim_c = cv @ cv.T
        chosen = [int(np.argmax(sim_q))]
        while len(chosen) < min(top_k_kw, len(cands)):
            rest = [i for i in range(len(cands)) if i not in chosen]
            mmr = [(1 - diversity) * sim_q[i] - diversity * max(sim_c[i][c] for c in chosen)
                   for i in rest]
            chosen.append(rest[int(np.argmax(mmr))])
        return [cands[i] for i in chosen]

    def run_query_expansion(self, qid: str, n: int = N_SELECT):

        kws = self.keybert_keywords(qid)
        runs = [(0.5, self._direct_for_text(self.queries[qid]["text"], n))]
        w_i = 0.5 / len(kws) if kws else 0.0
        for kw in kws:
            runs.append((w_i, self._direct_for_text(kw, n)))
        fused: dict[int, float] = {}
        for w, (idx, _) in runs:
            for rank, d in enumerate(idx, start=1):
                fused[int(d)] = fused.get(int(d), 0.0) + w / (RRF_K + rank)
        docs = np.array(list(fused.keys()))
        sc = np.array([fused[int(d)] for d in docs])
        order = np.lexsort((docs, -sc))[:n]
        return docs[order], sc[order], kws

    def _direct_for_text(self, text: str, n: int):
        bs = self.bm25_scores(text)
        ss = self.sbert_scores(text)
        cand = np.union1d(top_k(bs, n), top_k(ss, n))
        b, s = bs[cand], ss[cand]
        bn = b / b.max() if b.max() != 0 else np.zeros_like(b)
        sn = s / s.max() if s.max() != 0 else np.zeros_like(s)
        fused = bn + sn
        order = np.lexsort((cand, -fused))[:n]
        return cand[order], fused[order]

    def run_retrieval_random(self, qid: str, n: int = N_SELECT,
                             pool: int = RETRIEVAL_RANDOM_POOL,
                             rng: np.random.Generator | None = None):

        cand, sc = self.run_direct(qid, n=pool)
        rng = rng if rng is not None else np.random.default_rng(SEED)
        pick = rng.choice(len(cand), size=min(n, len(cand)), replace=False)
        pick = np.sort(pick)
        return cand[pick], sc[pick]
