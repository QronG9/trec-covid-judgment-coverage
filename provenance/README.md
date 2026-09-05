# My Provenance and Version Records

I connect the experimental stages through project-relative paths, original file hashes, and itemized reference values. The current research report covers 12 complete-query configurations, the initial five-query materials, and two nonempty-abstract conditions.

| Record | Information I preserve |
|---|---|
| [source_state.json](source_state.json) | Source-project HEAD, frozen tags, and the experimental scope of this release |
| [source_inventory.csv](source_inventory.csv) | Relative paths and SHA-256 hashes for the 246 tracked or staged files in the original project at packaging time |
| [original_freeze_verification.json](original_freeze_verification.json) | Hash comparisons for the 72 entries in the original frozen manifest |
| [source_preservation_check.json](source_preservation_check.json) | Preservation checks for the original files, HEAD, and staging state |
| [import_inputs.json](import_inputs.json) | Sources of the raw data, baseline rankings, index mapping, and scoring inputs for the nonempty-abstract condition |
| [experiment_imports.json](experiment_imports.json) | Sources, export conventions, row counts, and hashes for subsequent configurations and initial five-query rankings |
| [nonempty_export_validation.json](nonempty_export_validation.json) | Correspondence between 400 query/cutoff coverage cells in the nonempty-abstract conditions and their saved results |
| [reference_values.json](reference_values.json) | 1,324 source-reference rows and 2,572 numerical comparisons for the detailed three-baseline analyses |
| [extension_reference_values.json](extension_reference_values.json) | 2,571 reference rows and 7,702 numerical comparisons for the complete-query and initial five-query analyses |
| [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) | Release checks I executed and the execution environments |

The two reference files provide **3,895 rows and 10,274 numerical comparisons** in total. I extracted these values from result tables saved in the original project; each record retains its actual historical source filename. The new analysis programs recompute results from the released rankings and qrels, then compare them individually with these reference values.

I preserve the method implementations and dependency documentation in the [ranking-generation source code](../retrieval_source/README.md). The original programs load checkpoints by model identifier; their loading calls specify model names. This release fixes the inputs to the present calculations through saved rankings and SHA-256 hashes. Model names, input lengths, query prefixes, and scoring definitions are documented in the [methods](../docs/METHODS.md).

`MANIFEST.sha256` fixes the public files in this release, and Git tags identify release versions. I retain article text, model caches, virtual environments, and the complete original project history locally; the public package uses portable rankings and metadata without document text. Counts of saved ranking positions include repeated materials across stages: the five baseline configurations in the initial five-query materials are subsets of their complete-query rankings.

When preparing a subsequent version, I first stage the intended release files, run `python3 scripts/build_manifest.py`, and then run `python3 scripts/verify_release.py`. I commit the verified contents and add a new tag. The standard recomputation entry point reads the manifest and reference values without modifying them and writes calculated results to an isolated temporary directory.
