"""I define data paths, document representations, tokenization, query and judgment loading, and experimental parameters."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPL_ROOT = PROJECT_ROOT.parent
DATA_DIR = REPL_ROOT / "trec-covid"
CORPUS_JSONL = DATA_DIR / "corpus.jsonl"
QUERIES_JSONL = DATA_DIR / "queries.jsonl"
QRELS_TSV = DATA_DIR / "qrels" / "test.tsv"

CACHE = PROJECT_ROOT / "cache"
OUT = PROJECT_ROOT / "outputs"
FIG = PROJECT_ROOT / "figures"
CONFIG = PROJECT_ROOT / "config"
LOGS = PROJECT_ROOT / "logs"
for _d in (CACHE, OUT, FIG, CONFIG, LOGS):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 42
N_SELECT = 1000
K_DEPTHS = [20, 50, 100, 1000]
SBERT_MODEL = "sentence-transformers/all-mpnet-base-v2"
BM25_K1 = 1.5
BM25_B = 0.75
BM25_EPSILON = 0.25
RRF_K = 60
MMR_LAMBDA = 0.3
MMR_POOL = 5000
RETRIEVAL_RANDOM_POOL = 5000

PRIMARY_METHODS = ["Random Uniform", "BM25", "SBERT", "Direct Retrieval"]
SECONDARY_METHODS = ["Direct Retrieval + MMR", "Query Expansion", "Retrieval Random"]

PAPER_15_QUERIES = [2, 9, 10, 13, 18, 21, 23, 24, 26, 27, 34, 43, 45, 47, 48]

UNJUDGED = "U"

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STEM_CACHE: dict[str, str] = {}

def _stopwords() -> set[str]:
    from nltk.corpus import stopwords
    return set(stopwords.words("english"))

def make_tokenizer():

    from nltk.stem import PorterStemmer

    stemmer = PorterStemmer()
    sw = _stopwords()
    cache = _STEM_CACHE

    def tok(text: str) -> list[str]:
        out = []
        for w in _TOKEN_RE.findall(text.lower()):
            if w in sw:
                continue
            s = cache.get(w)
            if s is None:
                s = stemmer.stem(w)
                cache[w] = s
            if s:
                out.append(s)
        return out

    return tok

def load_corpus():

    ids, titles, texts = [], [], []
    with open(CORPUS_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            ids.append(o["_id"])
            titles.append(o.get("title") or "")
            texts.append(o.get("text") or "")
    return ids, titles, texts

def doc_repr(title: str, text: str) -> str:

    title = (title or "").strip()
    text = (text or "").strip()
    if title and text:
        return f"{title}. {text}"
    return title or text

def load_queries():

    q = {}
    with open(QUERIES_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            md = o.get("metadata") or {}
            q[str(o["_id"])] = {
                "text": o["text"],
                "query": md.get("query", ""),
                "narrative": md.get("narrative", ""),
            }
    return q

def load_qrels(return_anomalies: bool = False):

    qrels: dict[tuple[str, str], int] = {}
    anomalies: list[tuple[str, str, int]] = []
    with open(QRELS_TSV, "r", encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        assert header[:3] == ["query-id", "corpus-id", "score"], header
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            a, b, c = line.split("\t")[:3]
            v = int(c)
            if v not in (0, 1, 2):
                anomalies.append((str(a).strip(), str(b).strip(), v))
                continue
            qrels[(str(a).strip(), str(b).strip())] = v
    return (qrels, anomalies) if return_anomalies else qrels

def qrel_status(qrels, qid: str, did: str) -> str:

    v = qrels.get((qid, did))
    return UNJUDGED if v is None else str(v)

def set_seed(seed: int = SEED):
    import random
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)

def log(msg: str):
    import datetime as _dt
    print(f"[{_dt.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)
