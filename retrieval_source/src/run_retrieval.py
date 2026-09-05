"""I generate and save NPZ rankings for all 50 queries using the four baseline methods and Direct min-max.
The same saved runs support both the initial five-query analysis and the complete-query analysis."""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from common import CONFIG, N_SELECT, SEED, load_queries, log
from retrieval import RUNS, Engine

METHOD_FILES = {
    "BM25": "bm25",
    "SBERT": "sbert",
    "Direct Retrieval": "direct",
    "Random Uniform": "random",
    "Direct Retrieval + MMR": "direct_mmr",
    "Query Expansion": "qryexp",
    "Retrieval Random": "retrieval_random",
    "Direct Retrieval (minmax)": "direct_minmax",
}

def run_path(method: str):
    return RUNS / f"{METHOD_FILES[method]}.npz"

def load_run(method: str):
    z = np.load(run_path(method), allow_pickle=True)
    return {str(q): (z["idx"][i], z["scores"][i]) for i, q in enumerate(z["qids"])}

def save_run(method: str, qids, idx, scores, extra=None):
    np.savez_compressed(run_path(method), qids=np.array(qids, dtype=object),
                        idx=np.asarray(idx, dtype=np.int32),
                        scores=np.asarray(scores, dtype=np.float64))
    if extra:
        json.dump(extra, open(RUNS / f"{METHOD_FILES[method]}.meta.json", "w"), indent=2)
    log(f"  saved run: {method} ({len(qids)} queries) -> {run_path(method).name}")

def execute(methods, qids, engine: Engine, n: int = N_SELECT, force: bool = False):
    for method in methods:
        if run_path(method).exists() and not force:
            log(f"  cached: {method}")
            continue
        t0 = time.time()

        rng = np.random.default_rng(SEED)
        I, S, extra = [], [], {}
        for qid in qids:
            if method == "BM25":
                i, s = engine.run_bm25(qid, n)
            elif method == "SBERT":
                i, s = engine.run_sbert(qid, n)
            elif method == "Direct Retrieval":
                i, s = engine.run_direct(qid, n)
            elif method == "Direct Retrieval (minmax)":
                i, s = engine.run_direct(qid, n, variant="minmax")
            elif method == "Random Uniform":
                i, s = engine.run_random(qid, n, rng=rng)
            elif method == "Direct Retrieval + MMR":
                i, s = engine.run_direct_mmr(qid, n)
            elif method == "Query Expansion":
                i, s, kws = engine.run_query_expansion(qid, n)
                extra[qid] = kws
            elif method == "Retrieval Random":
                i, s = engine.run_retrieval_random(qid, n, rng=rng)
            else:
                raise ValueError(method)
            assert len(i) == n, f"{method} q{qid}: got {len(i)} docs, expected {n}"
            assert len(set(i.tolist())) == n, f"{method} q{qid}: duplicate doc indices"
            I.append(i)
            S.append(s)
        save_run(method, qids, I, S, extra or None)
        log(f"  {method} done in {time.time()-t0:.1f}s")

def main(force: bool = False):
    engine = Engine()
    all_qids = sorted(load_queries(), key=lambda x: int(x))
    stage1 = pd.read_csv(CONFIG / "queries_stage1.csv", dtype={"query_id": str})
    stage1_qids = sorted(stage1.query_id.tolist(), key=lambda x: int(x))
    log(f"stage-1 frozen queries: {stage1_qids}")

    log("PRIMARY methods over all 50 queries ...")
    execute(["BM25", "SBERT", "Direct Retrieval", "Random Uniform"],
            all_qids, engine, force=force)
    log("robustness variant (min-max fusion) ...")
    execute(["Direct Retrieval (minmax)"], all_qids, engine, force=force)
    log("done")

if __name__ == "__main__":
    import sys
    main(force="--force" in sys.argv)
