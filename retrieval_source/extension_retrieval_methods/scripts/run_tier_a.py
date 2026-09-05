"""我把 MMR、Query Expansion 和 Retrieval Random 运行到全部 50 查询。
程序分别检查确定性方法的五查询对应关系，以及随机选择的候选成员和集合重合。"""
from __future__ import annotations

import numpy as np

from ext_common import (EXT_RUNS, N_SELECT, ROOT, SEED, Timer, log, peak_rss_gb,
                        record_actual, save_run)

PILOT = ["9", "13", "34", "45", "48"]

def main():
    from common import load_queries
    from retrieval import Engine

    eng = Engine()
    qids = sorted(load_queries(), key=lambda x: int(x))
    assert len(qids) == 50, f"expected 50 queries, got {len(qids)}"

    jobs = [
        ("Direct + MMR", "direct_mmr", lambda q: eng.run_direct_mmr(q, N_SELECT)),
        ("Query Expansion", "qryexp", None),
        ("Retrieval Random", "retrieval_random", None),
    ]

    results = {}
    for method, stem, fn in jobs:
        out = EXT_RUNS / f"{stem}.npz"
        if out.exists():
            log(f"{method}: cached, skipping")
            continue
        log(f"{method}: running over all 50 queries ...")
        rng = np.random.default_rng(SEED)
        I, S, extra = [], [], {}
        with Timer(method) as t:
            for q in qids:
                if method == "Direct + MMR":
                    i, s = eng.run_direct_mmr(q, N_SELECT)
                elif method == "Query Expansion":
                    i, s, kws = eng.run_query_expansion(q, N_SELECT)
                    extra[q] = kws
                else:
                    i, s = eng.run_retrieval_random(q, N_SELECT, rng=rng)
                assert len(i) == N_SELECT, f"{method} q{q}: {len(i)} docs"
                assert len(set(i.tolist())) == N_SELECT, f"{method} q{q}: duplicates"
                I.append(i)
                S.append(s)
        meta = dict(source="source paper App. B.5/B.6/B.7 via frozen src/retrieval.py",
                    n_queries=len(qids), depth=N_SELECT, seed=SEED,
                    seconds=round(t.seconds, 1))
        if extra:
            meta["keywords_per_query"] = extra
        save_run(method, qids, I, S, meta)
        results[method] = t.seconds
        record_actual(f"tierA::{stem}", seconds=round(t.seconds, 1),
                      peak_rss_gb=round(peak_rss_gb(), 2), n_queries=len(qids),
                      new_disk_mb=round(out.stat().st_size / (1 << 20), 3))

    log("checking the 5 pilot queries against the frozen pilot runs ...")
    ok = True
    for method, stem in [("Direct + MMR", "direct_mmr"), ("Query Expansion", "qryexp")]:
        new = np.load(EXT_RUNS / f"{stem}.npz", allow_pickle=True)
        old = np.load(ROOT / "cache" / "runs" / f"{stem}.npz", allow_pickle=True)
        nmap = {str(q): new["idx"][i] for i, q in enumerate(new["qids"])}
        omap = {str(q): old["idx"][i] for i, q in enumerate(old["qids"])}
        same = all(np.array_equal(nmap[q], omap[q]) for q in PILOT)
        ok &= same
        log(f"  {method}: {'reproduces the pilot exactly' if same else 'DRIFTED'}")
    assert ok, ("a deterministic Tier-A method no longer reproduces the frozen pilot run; "
                "refusing to publish drifted numbers")

    new = np.load(EXT_RUNS / "retrieval_random.npz", allow_pickle=True)
    old = np.load(ROOT / "cache" / "runs" / "retrieval_random.npz", allow_pickle=True)
    nmap = {str(q): new["idx"][i] for i, q in enumerate(new["qids"])}
    omap = {str(q): old["idx"][i] for i, q in enumerate(old["qids"])}
    overlaps = []
    for q in PILOT:
        pool = set(eng.run_direct(q, 5000)[0].tolist())
        assert all(int(d) in pool for d in nmap[q]), \
            f"Retrieval Random q{q}: sampled outside Direct Retrieval's top-5000"
        overlaps.append(len(set(nmap[q].tolist()) & set(omap[q].tolist())) / N_SELECT)
    mean_ov = float(np.mean(overlaps))
    log(f"  Retrieval Random: all samples inside the App. B.7 pool; mean overlap with the "
        f"pilot draw {mean_ov:.3f} (independent-draw expectation 0.200)")
    assert 0.15 <= mean_ov <= 0.25, \
        f"Retrieval Random overlap {mean_ov:.3f} is not consistent with independent uniform draws"
    log("Tier A complete")

if __name__ == "__main__":
    main()
