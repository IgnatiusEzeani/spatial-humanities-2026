# SH2026 Release Candidate Checklist

Purpose: one operational gate for the Spatial Humanities 2026 tutorial, demo and keynote evidence package.

This checklist applies to an SH2026 release candidate such as `sh2026-rc1`. It is intentionally stricter than ordinary package development because the public workshop, hosted demo and keynote must all point to the same reproducible state.

## 1. Freeze the release identity

- [ ] Record the release branch/tag and exact Git commit.
- [ ] Record the `spatio-textual` package version/commit used by SH2026.
- [ ] Confirm this repository contains no vendored `spatio_textual/` package tree.
- [ ] Confirm every environment installs the recorded tagged package release.
- [ ] Confirm generated outputs and local secrets remain ignored.

Release record:

```text
SH2026 tag:
Git commit:
spatio-textual version/commit:
Release date:
Validated by:
```

## 2. Automated validation

The release candidate is not ready while a required current-head check is red or missing.

- [ ] Project tests pass against the recorded package release.
- [ ] The corresponding `spatio-textual` package release has green compatibility CI.
- [ ] `SH2026 release smoke` passes.
- [ ] `SH2026 benchmark smoke` passes.
- [ ] `SH2026 rules TOPONYM benchmark` passes.
- [ ] `SH2026 Hugging Face benchmark` passes.
- [ ] `SH2026 rule journey development` passes.
- [ ] `SH2026 transformer journey development` passes.
- [ ] `SH2026 affect rule benchmark` passes.
- [ ] `SH2026 affect transformer benchmark` passes.
- [ ] `SH2026 CLDW external validation` passes.
- [ ] `SH2026 affect teaching fallback` passes and regenerates the pinned Notebook 05 fallback successfully.
- [ ] `SH2026 NER teaching fallback` passes and regenerates the pinned Notebook 03 fallback successfully.
- [ ] `SH2026 Colab notebook smoke` passes all ten default notebooks.
- [ ] Notebook smoke is verified to execute the checked-out candidate commit, not a previously published branch.

Paid/formal LLM workflows remain separately guarded. A release should record whether they were intentionally run and which model/provider/version produced the retained outputs.

## 3. Workshop notebooks

- [ ] All ten notebooks open in Google Colab from a fresh browser session.
- [ ] Notebook `00` installs the intended release branch/tag.
- [ ] Every notebook can run independently or clearly states its prerequisite.
- [ ] Default participant path is CPU-capable.
- [ ] Default participant path does not require an API key.
- [ ] Notebook `03` loads the revision-pinned NER teaching fallback on the default fast path and identifies it as precomputed rather than benchmark evidence.
- [ ] Notebook `03` live/heavy path uses `dslim/bert-base-NER` at revision `0b95561fd0c304538b5eb8a0ee532ca24dd009b9`.
- [ ] Notebook `05` loads the revision-pinned affect teaching fallback on the default fast path and identifies it as precomputed rather than benchmark evidence.
- [ ] Notebook `05` live/heavy path uses the same pinned Cardiff/Hartmann model revisions recorded in the fallback.
- [ ] Notebook `06` default route remains deterministic/no-API and clearly distinguishes teaching simulation from empirical LLM output.
- [ ] Re-running cells from the top does not corrupt paths or state.
- [ ] Output directories remain under `sh2026_outputs/`.
- [ ] No notebook prints, stores or commits credentials.
- [ ] Links to `COMMON_SCHEMA.md`, annotation guidance and benchmark protocol resolve.

Manual Colab record:

```text
Date:
Browser:
Runtime/Python:
00: PASS/FAIL
01: PASS/FAIL
02: PASS/FAIL
03: PASS/FAIL
04: PASS/FAIL
05: PASS/FAIL
06: PASS/FAIL
07: PASS/FAIL
08: PASS/FAIL
09: PASS/FAIL
Notes:
```

## 4. Fallback and contingency pack

Fallback material must be explicit about what it is. A curated teaching example is not a model prediction; a cached model output is not a live run; neither is automatically benchmark evidence.

The canonical fallback index is `demo/fallback_manifest_v1.json`. It currently distinguishes three assets:

- `fallback_journeys_v1.json`: instructor-curated journey teaching material;
- `ner_transformer_teaching_fallback_v1.json`: real revision-pinned Hugging Face NER output for Notebook 03;
- `affect_transformer_teaching_fallback_v1.json`: real revision-pinned transformer affect output for Notebook 05.

Release checks:

- [ ] `fallback_manifest_v1.json` resolves every retained fallback file.
- [ ] Every manifest entry states whether it is curated teaching material or precomputed machine output.
- [ ] Every manifest entry states `benchmark_result: false`; formal benchmark claims continue to come from the benchmark evidence path.

For **curated teaching fallbacks**:

- [ ] source example identifier is recorded;
- [ ] source text is public-safe and distribution status is recorded;
- [ ] evidence quotations are exact substrings of the source;
- [ ] schema/version is recorded;
- [ ] the UI/notebook labels the output as instructor-curated and not benchmark evidence;
- [ ] edited source text never silently receives a fallback prepared for the original passage.

For every retained **transformer or LLM model-output fallback**:

- [ ] source example identifier is recorded;
- [ ] backend/provider/model is recorded;
- [ ] exact model revision is recorded where available;
- [ ] generation date is recorded;
- [ ] Git commit is recorded;
- [ ] prompt/schema version is recorded where relevant;
- [ ] telemetry is retained where available;
- [ ] human edits, if any, are stored separately from raw output;
- [ ] secrets are absent;
- [ ] the fallback is clearly labelled as precomputed in the notebook/demo.

Do not hand-edit a machine output and continue to describe it as raw model output. Do not create a synthetic/fabricated LLM output merely to fill a fallback slot; Notebook 06's deterministic teaching client is intentionally labelled as a teaching mechanism rather than empirical LLM evidence.

## 5. Hosted demo

- [ ] `streamlit run demo/streamlit_app.py` starts successfully in the release environment.
- [ ] Home, Analyse, Compare, Explore, Review and About pages load.
- [ ] Public-safe examples load correctly.
- [ ] Source spans render as highlighted evidence rather than only raw JSON/tables.
- [ ] Affect distributions render as readable charts and retain the model-signal caveat.
- [ ] Structured journeys render as evidence cards with explicit/contextual/missing provenance.
- [ ] The no-API-key path is fully usable.
- [ ] The curated journey fallback is visibly labelled as teaching material, not an LLM result.
- [ ] Missing/failed optional LLM access degrades gracefully.
- [ ] Named-place resolution exposes ambiguity/unresolved state rather than silently forcing a coordinate.
- [ ] Affect is described as model-labelled signal, not psychological fact.
- [ ] Human review exposes accept/edit/reject and produces an additive audit trail.
- [ ] Map view preserves unresolved/unmappable evidence in an audit table or accompanying textual view.
- [ ] Provenance page reports run manifest and telemetry without secrets.
- [ ] Hosted deployment is tested from an incognito/private browser session.
- [ ] A screenshot or recorded walkthrough exists as a presentation fallback.

## 6. Benchmark and keynote evidence

- [ ] `holdout_v1` checksum matches the frozen value.
- [ ] Frozen benchmark data have not been tuned against after formal evaluation began.
- [ ] Synthetic benchmark results are labelled synthetic and are not generalized to historical corpora.
- [ ] CLDW external-validation claims match the documented external-validation protocol.
- [ ] NER, journey and affect results used in slides can be traced to a results document/run artifact.
- [ ] Every keynote metric has task, dataset, method/model and evaluation definition attached.
- [ ] `results_snapshot_v1.json` remains the single reportable feed used by the demo/keynote figure generator.
- [ ] Teaching fallback metrics are not copied into `results_snapshot_v1.json` merely because they are convenient or visually useful.
- [ ] Any condition marked `not_reportable` remains excluded from scored public tables/figures.
- [ ] The talk distinguishes within-ontology accuracy from representational reach.
- [ ] Review/correction burden is discussed where richer methods increase human validation work.
- [ ] No method is presented as a universal winner based on a single metric.

## 7. Data governance and sensitive material

- [ ] No controlled-access Holocaust testimony transcript is bundled in the public repository, notebooks or hosted demo.
- [ ] Public teaching passages have source/licence/distribution status recorded.
- [ ] Synthetic oral-history-style passages are explicitly labelled synthetic.
- [ ] Public workshop instructions do not ask participants to send sensitive archival or personal data to an external LLM provider.
- [ ] No API keys, tokens, local `.env` files or private endpoints are committed.
- [ ] Screenshots and slides have been checked for accidental sensitive text or credentials.

## 8. Instructor and contingency package

- [ ] `workshop/INSTRUCTOR_GUIDE.md` reflects the final notebook sequence and timings.
- [ ] Five-minute contingency exercises are available.
- [ ] Fifteen-minute contingency exercises are available.
- [ ] Troubleshooting guidance is available.
- [ ] A no-live-API teaching route has been rehearsed.
- [ ] A no-demo/network-failure presentation route has been rehearsed.
- [ ] The instructor has local copies of critical notebooks, figures and fallback outputs.

## 9. Public links and presentation integration

- [ ] Repository link resolves to the release state participants should use.
- [ ] Colab links resolve to the intended notebooks.
- [ ] Demo URL resolves and has been tested on a second device/network.
- [ ] QR codes in slides/handouts point to stable public landing pages rather than transient branch URLs.
- [ ] Keynote screenshots/figures correspond to the same release candidate as the demo/tutorial.
- [ ] Any displayed model name/version matches the provenance record.

## 10. Final go/no-go

**GO** only when:

1. required automated checks are green at the release commit;
2. all ten default notebook paths have both automated CPU validation and at least one fresh manual Colab rehearsal;
3. the hosted demo works without an API key;
4. fallback/contingency material is provenance-complete and correctly labelled;
5. benchmark/keynote claims are traceable to frozen evidence;
6. public-safe data boundaries have been checked;
7. presentation fallbacks have been rehearsed.

If one of these fails, keep the candidate as a pre-release and fix or explicitly narrow the advertised capability before tagging the conference release.
