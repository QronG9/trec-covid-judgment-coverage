# My Release Verification

**v2.0.0 · 2026-09-05**

I performed the following checks on the saved rankings, original judgments, and analysis programs in this release. The verification entry point regenerates results in an isolated temporary directory so that the published tables can be checked against their computational inputs.

| Check | Result of my execution |
|---|---|
| Original-project preservation | SHA-256 hashes for 246 tracked or staged files, the original HEAD, and the staging state are unchanged |
| Original frozen version | All 72 entries in the original frozen manifest match |
| Raw BEIR data | Corpus, query, and qrel SHA-256 hashes match; the original corpus regenerates identical metadata without document text |
| Ranking inputs | 12 complete-query configurations, 8 five-query configurations, and 2 nonempty-abstract conditions contain 740,000 saved ranking positions |
| Clean-directory recomputation | 14 detailed baseline-analysis files and 20 complete-configuration or cross-stage comparison files, totaling 34 CSV/JSON files, match byte for byte |
| Historical numerical correspondence | All 10,274 numerical comparisons across 3,895 reference rows match |
| Nonempty-abstract export | 400 query/cutoff coverage cells match the saved results |
| Program and mathematical semantics | All 21 tests pass in both normal and optimized modes, covering shared-U cancellation, exhaustive label completions, MMR ordering, empty random scores, set preservation, and input checks |
| Ranking-generation code | 10 original implementation files pass syntax checks and computational abstract syntax tree comparisons; source and published file hashes are recorded separately |
| Research text | Reported metrics for all 12 configurations, paired bounds, abstract conditions, and inventory counts match the computed results |
| Figures | Two figures present the 12-configuration comparison and detailed three-baseline analyses; both were generated from CSV tables, source hashes were recorded, and their visual presentation was inspected |
| Documentation | The verification entry point checks relative links in the public Markdown files |

I executed offline recomputation with Python **3.9.6** and **3.11.15**. The core calculations use only the standard library. Figures were generated with matplotlib **3.11.1**; the source tables and version are recorded in [figure_sources.json](../figures/figure_sources.json).

```bash
python3 scripts/verify_release.py
```

This entry point checks the release manifest, recomputes and compares all 34 result files in a temporary directory, and then checks numerical correspondence, tests, documentation links, and figure sources. It preserves the existing reference values and result tables so that the executed version and recomputed contents can be identified directly.

In the local environment containing the original corpus, I also ran:

```bash
python3 scripts/fetch_corpus.py --verify-only
```

I define the verification scope as fixed-input recomputation, historical numerical correspondence, and file integrity. The [implementation documentation](../retrieval_source/README.md) records the original ranking-generation code, model dependencies, configurations, and provenance. The complete recomputation performed for this release begins with the published saved rankings; the model-inference stage is represented by the previously saved run outputs.

I have prepared GitHub Actions to execute the same verification entry point after upload, on push, pull request, or manual triggers. This record reports actual local execution; remote outcomes will be recorded by the workflow after upload. The public package contains scripts, portable inputs, results, figures, and version manifests. I retain the original article text and historical backups locally.
