# Evaluation: place recognition on historical prose

The experiment behind the results reported in the SH2026 keynote and shown in the
workshop's third block.

**Task.** Detect place-name spans in 399 passages from the Corpus of Lake District
Writing, scored against 789 human-annotated `<cdplace>` spans from its gold
standard, with 95% bootstrap confidence intervals resampled over passages.

**Systems.** Four large language models, a pinned transformer NER model, and a
transformer-plus-gazetteer hybrid, aggregated with Dawid-Skene.

**Data.** The gold standard is not redistributed here. Obtain it from
[UCREL/LakeDistrictCorpus](https://github.com/UCREL/LakeDistrictCorpus) and
extract passages with `extract_ld80_gold.py`. The 399 sampled passages and their
annotations are committed as `ld80_keep.jsonl` so the reported numbers can be
checked without re-running extraction.

**Results.** `results_snapshot_v2.json`. `PANEL_PLAN.md` describes the design.

| Stage | Script |
|---|---|
| Extract passages and gold | `extract_ld80_gold.py` |
| Resolve exact model versions | `discover_revisions.py` |
| Check every system responds | `preflight.py` |
| Run the systems | `run_panel_sh2026.py` |
| Score against gold | `score_against_gold.py` |

Model calls require an OpenRouter key and incur cost; everything else runs
offline.
