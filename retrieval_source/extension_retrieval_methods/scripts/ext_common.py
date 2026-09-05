"""我在这里定义补充方法的路径、模型标识、运行保存方式和资源记录。
模型按名称加载；具体 revision 的使用方式以模型构造调用为准。"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

EXT = Path(__file__).resolve().parents[1]
ROOT = EXT.parent
sys.path.insert(0, str(ROOT / "src"))

EXT_CACHE = EXT / "cache"
EXT_OUT = EXT / "outputs"
EXT_FIG = EXT / "figures"
EXT_LOG = EXT / "logs"
EXT_VAL = EXT / "validation"
EXT_CFG = EXT / "config"
for _d in (EXT_CACHE, EXT_OUT, EXT_FIG, EXT_LOG, EXT_VAL, EXT_CFG):
    _d.mkdir(parents=True, exist_ok=True)
EXT_RUNS = EXT_CACHE / "runs"
EXT_RUNS.mkdir(exist_ok=True)

N_SELECT = 1000
K_DEPTHS = [20, 50, 100, 1000]
SEED = 42

SPLADE_MODEL = "naver/splade-cocondenser-ensembledistil"
BGE_MODEL = "BAAI/bge-base-en-v1.5"
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

METHODS = {

    "Random Uniform":        dict(file="../random",  family="random",       frozen=True),
    "BM25":                  dict(file="../bm25",    family="lexical",      frozen=True),
    "SBERT (mpnet)":         dict(file="../sbert",   family="dense",        frozen=True),
    "Direct Retrieval":      dict(file="../direct",  family="hybrid",       frozen=True),

    "Retrieval Random":      dict(file="retrieval_random", family="random",  frozen=False),
    "Query Expansion":       dict(file="qryexp",           family="hybrid",  frozen=False),
    "Direct + MMR":          dict(file="direct_mmr",       family="hybrid",  frozen=False),

    "Direct + MMR (rerank-1000)": dict(file="direct_mmr_rerank", family="hybrid",
                                       frozen=False),

    "SPLADE":                dict(file="splade",           family="sparse-neural", frozen=False),
    "BGE (dense #2)":        dict(file="bge",              family="dense",   frozen=False),
    "BM25 + CrossEncoder":   dict(file="bm25_ce",          family="rerank",  frozen=False),
}

FAMILY_ORDER = ["random", "lexical", "sparse-neural", "hybrid", "rerank", "dense"]

def log(msg: str):
    import datetime as _dt
    line = f"[{_dt.datetime.now().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(EXT_LOG / "extension.log", "a") as f:
        f.write(line + "\n")

def device() -> str:
    import torch
    return "mps" if torch.backends.mps.is_available() else "cpu"

def peak_rss_gb() -> float:
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1 << 30)

def run_path(method: str) -> Path:
    stem = METHODS[method]["file"]
    return (EXT_RUNS / f"{stem}.npz") if not stem.startswith("../") \
        else (ROOT / "cache" / "runs" / f"{stem[3:]}.npz")

def save_run(method: str, qids, idx, scores, meta=None):
    p = run_path(method)
    assert not METHODS[method]["frozen"], f"refusing to write a frozen Stage-1 run: {p}"
    np.savez_compressed(p, qids=np.array(qids, dtype=object),
                        idx=np.asarray(idx, dtype=np.int32),
                        scores=np.asarray(scores, dtype=np.float64))
    if meta:
        json.dump(meta, open(p.with_suffix(".meta.json"), "w"), indent=2)
    log(f"  saved {method} -> {p.name} ({len(qids)} queries)")

def load_run(method: str):
    z = np.load(run_path(method), allow_pickle=True)
    return {str(q): (z["idx"][i], z["scores"][i]) for i, q in enumerate(z["qids"])}

def top_k(scores: np.ndarray, k: int) -> np.ndarray:

    k = min(k, scores.shape[0])
    order = np.lexsort((np.arange(scores.shape[0]), -scores))
    return order[:k]

class Timer:
    def __init__(self, label):
        self.label = label

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *a):
        self.seconds = time.time() - self.t0
        log(f"  {self.label}: {self.seconds:.1f}s")

def record_actual(name: str, **kw):

    p = EXT_OUT / "resource_actuals.json"
    data = json.load(open(p)) if p.exists() else {}
    data[name] = kw
    json.dump(data, open(p, "w"), indent=2)

def dir_size_mb(path: Path) -> float:
    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_size / (1 << 20)
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / (1 << 20)
