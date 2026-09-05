
"""我在 Direct top-1000 集合内运行 MMR，保留完整候选集合并生成贪心重排次序。
此配置与从 Direct top-5000 选取 1000 篇的配置分别保存。"""
from __future__ import annotations
import numpy as np
from ext_common import EXT_RUNS, N_SELECT, Timer, log, save_run

def main():
    from common import load_queries
    from retrieval import Engine
    out = EXT_RUNS / "direct_mmr_rerank.npz"
    if out.exists():
        log("MMR rerank-1000 variant cached"); return
    eng = Engine()
    qids = sorted(load_queries(), key=lambda x: int(x))
    lam = 0.3
    I, S = [], []
    with Timer("MMR rerank-1000 variant") as t:
        for q in qids:
            cand, _ = eng.run_direct(q, N_SELECT)
            D = np.ascontiguousarray(eng.emb[cand])
            qv = eng.embed_query(eng.queries[q]["text"])
            rel = D @ qv
            sel, avail = [], np.ones(len(cand), dtype=bool)
            best = np.full(len(cand), -np.inf)
            for _ in range(len(cand)):
                mmr = rel.copy() if not sel else lam * rel - (1 - lam) * best
                m = np.where(avail, mmr, -np.inf)
                j = int(np.lexsort((np.arange(len(cand)), -m))[0])
                sel.append(j); avail[j] = False
                sims = D @ D[j]
                best = np.maximum(best, sims) if len(sel) > 1 else sims
            sel = np.array(sel)
            I.append(cand[sel]); S.append(rel[sel].astype(np.float64))
    save_run("Direct + MMR (rerank-1000)", qids, I, S,
             dict(variant="reorder Direct Retrieval's top-1000 (set unchanged)",
                  reason=('MMR reorders the complete Direct top-1000 candidate set; lambda=0.3.'),
                  lambda_=lam, seconds=round(t.seconds, 1)))

if __name__ == "__main__":
    main()
