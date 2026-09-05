"""我在五个指定查询上运行 MMR、Query Expansion 和 Retrieval Random，并保存运行状态。"""
from __future__ import annotations

import json

import pandas as pd

from common import CONFIG, OUT, SECONDARY_METHODS, log
from retrieval import Engine
from run_retrieval import execute, run_path

def main(force: bool = False):
    stage1 = pd.read_csv(CONFIG / "queries_stage1.csv", dtype={"query_id": str})
    qids = sorted(stage1.query_id.tolist(), key=lambda x: int(x))
    engine = Engine()
    ok, notes = [], {}
    for m in SECONDARY_METHODS:
        try:
            execute([m], qids, engine, force=force)
            assert run_path(m).exists()
            ok.append(m)
        except Exception as e:
            notes[m] = f"{type(e).__name__}: {e}"
            log(f"  SECONDARY method failed and is skipped: {m} -> {notes[m]}")
    json.dump(dict(succeeded=ok, failed=notes),
              open(OUT / "secondary_methods_status.json", "w"), indent=2)
    return tuple(ok)

if __name__ == "__main__":
    print(main())
