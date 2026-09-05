# My Archived Experimental History

I preserve the experiments by stage so that I can compare the initial query subset, the complete query set, and subsequent method extensions. The original project files and frozen tags remain unchanged; saved rankings and source hashes connect these stages to the present repository.

The local `archive/local-original/` directory contains the complete original Git bundle, stage reports, input and output inventories, verification records, and the full-corpus BM25 scores and query embeddings used for the nonempty-abstract condition. The Git bundle includes all branches and frozen tags from the original project. The large document embeddings remain in the original project's cache, with their SHA-256 hashes recorded.

```bash
git bundle verify archive/local-original/source-history.bundle
git clone archive/local-original/source-history.bundle /path/to/restored-experiments
```

I retain the historical directory in the local workspace and exclude it from version control through `.gitignore`. The public release provides executable research materials through `data/`, `results/`, and `provenance/`. The experimental stages are described in [my research process](../docs/RESEARCH_PROCESS.md).

The current Git repository preserves the release history. Version v2.0.0 integrates the complete-query configurations and initial experiments, presented in my first-person research account. The v1.0.0 and v2.0.0 upload archives are retained separately.
