"""I implement BM25Okapi scoring with sparse matrices and provide a comparison against rank_bm25 at a specified tolerance."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import scipy.sparse as sp

from common import BM25_B, BM25_EPSILON, BM25_K1, CACHE, log

class SparseBM25Okapi:
    def __init__(self, tokenized_corpus, k1=BM25_K1, b=BM25_B, epsilon=BM25_EPSILON):
        self.k1, self.b, self.epsilon = k1, b, epsilon
        vocab: dict[str, int] = {}
        indptr = [0]
        indices: list[int] = []
        data: list[int] = []
        doc_len = np.empty(len(tokenized_corpus), dtype=np.float64)

        for i, doc in enumerate(tokenized_corpus):
            doc_len[i] = len(doc)
            freqs: dict[int, int] = {}
            for w in doc:
                j = vocab.get(w)
                if j is None:
                    j = len(vocab)
                    vocab[w] = j
                freqs[j] = freqs.get(j, 0) + 1
            indices.extend(freqs.keys())
            data.extend(freqs.values())
            indptr.append(len(indices))

        self.vocab = vocab
        self.corpus_size = len(tokenized_corpus)
        self.doc_len = doc_len
        self.avgdl = float(doc_len.sum() / self.corpus_size)
        tf = sp.csr_matrix(
            (np.asarray(data, dtype=np.float32), np.asarray(indices, dtype=np.int32),
             np.asarray(indptr, dtype=np.int64)),
            shape=(self.corpus_size, len(vocab)),
        )
        self.tf = tf.tocsc()

        nd = np.diff(self.tf.indptr).astype(np.float64)
        idf = np.log(self.corpus_size - nd + 0.5) - np.log(nd + 0.5)
        average_idf = idf.sum() / len(idf)
        idf[idf < 0] = self.epsilon * average_idf
        self.idf = idf
        self.average_idf = average_idf

        self.k1_norm = self.k1 * (1 - self.b + self.b * self.doc_len / self.avgdl)

    def get_scores(self, query_tokens) -> np.ndarray:

        score = np.zeros(self.corpus_size, dtype=np.float64)
        counts: dict[str, int] = {}
        for q in query_tokens:
            counts[q] = counts.get(q, 0) + 1
        for term, mult in counts.items():
            j = self.vocab.get(term)
            if j is None:
                continue
            lo, hi = self.tf.indptr[j], self.tf.indptr[j + 1]
            rows = self.tf.indices[lo:hi]
            qf = self.tf.data[lo:hi].astype(np.float64)
            contrib = self.idf[j] * (qf * (self.k1 + 1.0) / (qf + self.k1_norm[rows]))
            score[rows] += mult * contrib
        return score

    def save(self, path: Path):
        with open(path, "wb") as f:
            pickle.dump(dict(vocab=self.vocab, tf=self.tf, doc_len=self.doc_len,
                             avgdl=self.avgdl, idf=self.idf, average_idf=self.average_idf,
                             k1=self.k1, b=self.b, epsilon=self.epsilon,
                             corpus_size=self.corpus_size), f, protocol=4)

    @classmethod
    def load(cls, path: Path) -> "SparseBM25Okapi":
        with open(path, "rb") as f:
            d = pickle.load(f)
        o = cls.__new__(cls)
        o.vocab, o.tf, o.doc_len = d["vocab"], d["tf"], d["doc_len"]
        o.avgdl, o.idf, o.average_idf = d["avgdl"], d["idf"], d["average_idf"]
        o.k1, o.b, o.epsilon, o.corpus_size = d["k1"], d["b"], d["epsilon"], d["corpus_size"]
        o.k1_norm = o.k1 * (1 - o.b + o.b * o.doc_len / o.avgdl)
        return o

def verify_against_rank_bm25(tokenized_subcorpus, tokenized_queries, tol=1e-9):

    from rank_bm25 import BM25Okapi

    ref = BM25Okapi(tokenized_subcorpus, k1=BM25_K1, b=BM25_B, epsilon=BM25_EPSILON)
    ours = SparseBM25Okapi(tokenized_subcorpus)
    worst = 0.0
    for q in tokenized_queries:
        a = np.asarray(ref.get_scores(q), dtype=np.float64)
        b = ours.get_scores(q)
        worst = max(worst, float(np.max(np.abs(a - b))))
    log(f"BM25 equivalence check vs rank_bm25: max abs score diff = {worst:.3e}")
    assert worst < tol, f"BM25 implementations diverge (max diff {worst})"
    return worst
