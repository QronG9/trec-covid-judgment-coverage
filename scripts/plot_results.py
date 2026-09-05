#!/usr/bin/env python3
"""Render the release summary directly from regenerated CSV tables (matplotlib)."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("results"))
    parser.add_argument("--output-dir", type=Path, default=Path("figures"))
    args = parser.parse_args()
    os.environ.setdefault("MPLCONFIGDIR", str(args.output_dir.resolve().parent / ".matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def read(name):
        with (args.results_dir / name).open() as f:
            return list(csv.DictReader(f))
    coverage = read("coverage_summary.csv")
    eligible = read("nonempty_coverage_summary.csv")
    bounds = read("paired_precision_bounds_summary.csv")
    lookup = {(r["method"], int(r["k"])): float(r["mean_hole_fraction"]) for r in coverage}
    nonempty = {(r["method"], int(r["k"])): float(r["mean_hole_fraction"]) for r in eligible}
    pairs = [("mpnet", "bm25"), ("direct", "bm25"), ("mpnet", "direct")]
    bound_lookup = {(r["method_a"], r["method_b"]): r for r in bounds if r["k"] == "20" and r["label_rule"] == "strict_eq2"}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "svg.hashsalt": "trec-covid-judgment-coverage-v1"})
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.6), gridspec_kw={"width_ratios": [1, 1.05, 1.45]})
    colors = ["#37688C", "#D48135", "#3D8471"]
    methods = ["bm25", "mpnet", "direct"]
    vals = [lookup[m, 20] * 100 for m in methods]
    axes[0].bar(["BM25", "MPNet", "Direct"], vals, color=colors, width=.65)
    axes[0].set_ylim(0, 50)
    axes[0].set_ylabel("Unjudged share of top-20 (%)")
    axes[0].set_title("A  Judgment coverage", loc="left", fontweight="bold", pad=15)
    for i, v in enumerate(vals):
        axes[0].text(i, v + 1.3, f"{v:.1f}%", ha="center", fontweight="bold")
    gaps = [(lookup["mpnet", 20] - lookup["bm25", 20]) * 100,
            (nonempty["mpnet", 20] - nonempty["bm25", 20]) * 100]
    axes[1].bar(["All documents", "Nonempty\nabstracts only"], gaps, color=["#D48135", "#E4B780"], width=.6)
    axes[1].set_ylim(0, 42)
    axes[1].set_ylabel("MPNet minus BM25 Hole@20 (pp)")
    axes[1].set_title("B  Eligibility sensitivity", loc="left", fontweight="bold", pad=15)
    for i, v in enumerate(gaps):
        axes[1].text(i, v + 1.2, f"{v:.1f} pp", ha="center", fontweight="bold")
    ax = axes[2]
    ax.axvline(0, color="#92989E", lw=1, linestyle="--")
    for i, pair in enumerate(pairs):
        r = bound_lookup[pair]
        lo, hi, obs = [float(r[n]) * 100 for n in ["mean_lower_bound", "mean_upper_bound", "mean_observed_delta"]]
        color = "#3D8471" if lo > 0 else "#687680"
        ax.plot([lo, hi], [i, i], lw=4, color=color, solid_capstyle="round")
        ax.scatter([obs], [i], color="#1E2933", s=38, zorder=3)
        ax.text((lo + hi) / 2, i - .16, f"[{lo:.1f}, {hi:.1f}]", ha="center", fontsize=9)
    ax.set_yticks(range(3), ["MPNet - BM25", "Direct - BM25", "MPNet - Direct"])
    ax.set_xlim(-29, 39)
    ax.set_ylim(2.45, -.5)
    ax.set_xlabel("Mean P@20 difference (percentage points)")
    ax.set_title("C  Sharp bounds, fixed rankings", loc="left", fontweight="bold", pad=15)
    fig.suptitle("TREC-COVID: a diagnostic of three saved retrieval runs", x=.045, ha="left", fontsize=15, fontweight="bold")
    fig.subplots_adjust(left=.065, right=.985, bottom=.32, top=.80, wspace=.72)
    b = axes[1].get_position()
    c = axes[2].get_position()
    fig.text((b.x0 + b.x1) / 2, .06, "Changed eligible population;\nnot a causal attribution.", ha="center", fontsize=9, color="#555555")
    fig.text((c.x0 + c.x1) / 2, .045, "QREL=2; existing labels retained.\nDots: observed differences.\nLines: attainable bounds, not confidence intervals.", ha="center", fontsize=8.5, color="#555555")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_dir / "research_summary.png", dpi=180, facecolor="white")
    fig.savefig(args.output_dir / "research_summary.svg", metadata={"Date": None}, facecolor="white")
    plt.close(fig)
    inputs = {name: hashlib.sha256((args.results_dir / name).read_bytes()).hexdigest()
              for name in ["coverage_summary.csv", "nonempty_coverage_summary.csv", "paired_precision_bounds_summary.csv"]}
    (args.output_dir / "figure_sources.json").write_text(json.dumps({"matplotlib_version": matplotlib.__version__, "source_table_sha256": inputs}, indent=2) + "\n")
    print("Wrote research_summary.png, research_summary.svg and source hashes.")


if __name__ == "__main__":
    main()
