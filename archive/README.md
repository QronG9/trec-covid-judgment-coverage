# Historical material

The original project remains unchanged. Its initial frozen reports contain
claims superseded by [ERRATA](../docs/ERRATA.md); use the
[revised research note](../docs/RESEARCH_NOTE.md) for current conclusions.

The **local working folder only** contains `archive/local-original/`:

- `source-history.bundle`: a complete Git bundle of the original repository's
  refs, including all four freeze/extension tags and source HEAD `e5d96e1`.
- Exact copies of the original pilot/full reports, original README and freeze
  manifest, audit report, audit evidence and numerical/reference ledgers.
- `source_state_before.json`: original source status and file hashes before
  release packaging. Audit files were already staged; that state is preserved.
- `audit_scores/`: copies of the original audit's full-corpus BM25 score matrix
  and CPU query vectors, so the nonempty-abstract export does not depend on
  transient `/tmp` files being retained. Original document vectors remain in
  the source project's ignored cache, with their hash recorded.

This local archive is ignored by Git and excluded from the GitHub upload zip.
It preserves obsolete prose, local paths, and historical working material
without presenting those files as the current scientific report. This public
repository contains the corresponding source inventory, freeze checks and
reproduction inputs under `provenance/` and `data/`.

To inspect the local bundle without changing the original project:

```bash
git bundle verify archive/local-original/source-history.bundle
git clone archive/local-original/source-history.bundle /path/to/restored-original
```

The bundle preserves committed history. The separately copied audit files
preserve the staged audit additions not present in that history. The large
ignored caches remain at their original location; their recorded hashes are
retained in the original freeze manifest. The local raw corpus copy is under
`data/trec-covid/corpus.jsonl` and is also ignored by Git.
