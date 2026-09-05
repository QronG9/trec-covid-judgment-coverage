# Release verification — 2026-09-05

This record concerns **v1.0.0 of the new artifact**, not a new scientific
assessment of all historical or later extension claims.

| Check | Result and scope |
|---|---|
| Original source preservation | 246 tracked/staged source files have unchanged SHA-256; original HEAD and pre-existing staged audit status unchanged |
| Original freeze | All 72 entries in the original frozen manifest match |
| Raw BEIR files | Corpus, queries and test qrels match recorded SHA-256; raw corpus regenerates byte-identical text-free metadata |
| Primary analysis | 14 CSV/JSON result files independently generated from raw qrels and portable saved rankings |
| Clean recomputation | All 14 files match byte for byte when generated in a fresh temporary directory |
| Numerical continuity | 2,572 numeric comparisons against 1,324 reference rows from original outputs and separate audit evidence pass |
| Nonempty-abstract export | 400 query/cutoff Hole cells match the original audit when recomputed with raw qrels |
| Mathematical/input tests | 12 tests pass under normal Python and `python -O`, including exhaustive small-case label completions for sharp bounds and shared-U cancellation |
| Documentation | Relative links resolve; short report, precision threshold and comparison directions agree with the result tables |
| Figure | Generated from CSV tables, source hashes recorded, visual inspection completed |

Local core verification was exercised with Python **3.9.6** and **3.11.15**.
The core path needs only the standard library. Optional plotting used
matplotlib **3.11.1**, with the version and source table hashes in
`figures/figure_sources.json`.

Run the checks with:

```bash
python3 scripts/verify_release.py
```

The command reads the release manifest, then writes only to an isolated
temporary output directory; it does not update expected values or waive failed
checks. For the local full corpus, `python3 scripts/fetch_corpus.py --verify-only`
also verifies its original hashes and regenerated metadata. The optional import
script converted trusted original local numpy caches; it is not part of normal
offline reproduction.

The public Git export contains the same small inputs and verification scripts;
it excludes original article text, model weights, local historical copies,
virtual environments and machine-specific paths. `.gitattributes` preserves
exact artifact bytes across checkout platforms. The new GitHub workflow is
prepared but has not run remotely; its outcome can only be observed after an
upload. The current work does not provide a new cold-start retrieval run,
medical relevance labels, external peer review, or an ACM badge.

