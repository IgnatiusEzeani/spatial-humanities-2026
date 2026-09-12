# SH2026 public demonstrator

This directory contains the Spatial Humanities 2026 conference demonstrator built on the reusable `spatio-textual` package.

The humanities-facing product question is:

> Given a narrative, what spatial information can different computational methods recover, what do they disagree about, and what evidence should a human inspect before using the output for research?

## Run locally

From the repository root, the offline-safe/default path is:

```bash
python -m pip install -e '.[app]'
python -m spacy download en_core_web_sm
streamlit run demo/streamlit_app.py
```

For optional live OpenAI journey extraction, also install the OpenAI client or install the repository `requirements.txt`:

```bash
python -m pip install 'openai>=1.0.0'
```

The hosted/default demo path remains fully useful without a provider API key.

## Reliability modes

### Local/default path

The following remain available without live LLM access:

- contextual spatial entity recognition;
- transparent rule/gazetteer comparison;
- place-resolution ambiguity and unresolved-state inspection;
- rule-based sentiment/emotion signals;
- highlighted source evidence;
- comparison and review views;
- maps where resolved coordinates are available;
- co-occurrence output;
- frozen artifact-backed benchmark snapshot.

### Structured journey layer

The Analyse page offers four modes:

1. **Off**: no structured journey layer.
2. **Automatic**: use live extraction when the server is configured; otherwise use an eligible curated teaching fallback.
3. **Teaching fallback**: force the offline-safe curated path for supported unchanged examples.
4. **Live LLM**: use only the server-configured live provider path.

The app never asks a visitor to paste an API key into the interface.

`fallback_journeys_v1.json` contains instructor-curated, public-safe records used only to demonstrate the journey schema, local evidence grounding, explicit/contextual/missing field provenance, and human review. They are **not model predictions** and **not benchmark results**. The fallback is only used when the selected teaching passage is unchanged, so a cached example is never silently attached to edited text.

### Workshop transformer fallbacks

The workshop now includes two genuine precomputed machine-output fallbacks for heavyweight optional sections:

- `affect_transformer_teaching_fallback_v1.json` for Notebook 05, generated with the exact pinned Cardiff sentiment and Hartmann emotion model revisions used by the SH2026 transformer affect condition;
- `ner_transformer_teaching_fallback_v1.json` for Notebook 03, generated with `dslim/bert-base-NER` at revision `0b95561fd0c304538b5eb8a0ee532ca24dd009b9`.

Both files retain their source passages, exact model revisions, generation commits and telemetry. They are **precomputed model outputs for teaching continuity**, not formal holdout benchmark results. Notebook 03 and Notebook 05 use these files on their default fast path and can reproduce the same revision-pinned model conditions live when the heavyweight path is enabled.

`fallback_manifest_v1.json` is the compact provenance index for all conference fallback assets. It explicitly distinguishes instructor-curated journey examples from precomputed transformer output and from benchmark evidence.

## Evidence and review behaviour

The demo keeps original source text visible and highlights character-grounded annotations. Structured journey cards display the exact evidence quote, evidence-grounding state, per-field provenance, confidence when supplied, and review requirement.

Human review uses accept/edit/reject actions. Review events are append-only: edits preserve the original machine value in the audit event rather than silently overwriting provenance.

## Benchmark display

The Home-page benchmark table reads `benchmarks/results_snapshot_v1.json` and displays only rows marked `reportable`.

Synthetic controlled results are separated from CLDW source-derived validation. A model/task condition without a complete provenance-backed formal result must remain excluded rather than being represented by provisional or manually copied numbers.

## Public-data boundary

The hosted demo uses distributable Lake District material and instructor-created synthetic examples. It must not package controlled-access Holocaust testimony transcript content.

## Release rehearsal

Before a public deployment:

- run the app with no `OPENAI_API_KEY` and exercise all six pages;
- test at least one curated journey fallback and one example with no fallback;
- execute Notebook 03 and Notebook 05 on their default precomputed paths and confirm the provenance labels are visible;
- verify highlighted spans and affect charts render on a phone/tablet-sized browser as well as desktop;
- test one ambiguous/unresolved place through accept/edit/reject review;
- confirm map failure/unresolved cases remain visible rather than disappearing;
- if live LLM extraction is enabled, verify the provider key is server-side only and never printed in provenance;
- test the deployed URL from a private/incognito browser session;
- retain screenshots or a short recorded walkthrough as the no-network presentation fallback.
