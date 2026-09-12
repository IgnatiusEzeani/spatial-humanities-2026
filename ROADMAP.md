# Spatial Humanities 2026: Keynote, Tutorial and Demo Roadmap

Current cleanup branch: `spatial-humanities-2026-cleanup-work`  
Target release branch: `spatial-humanities-2026`

## Goal

Turn `spatio-textual` into one coherent Spatial Humanities 2026 package with three public-facing outputs:

1. a full-day Google Colab tutorial/workshop;
2. a hosted interactive demo;
3. a keynote lecture comparing manual annotation, rule-based NLP, statistical/transformer NLP and LLM-assisted workflows.

The three outputs should share the same examples, data schema, evaluation language and visual identity rather than becoming separate projects.

## Core principle

Use one end-to-end research story:

`text -> segmentation -> annotation -> entity linking -> affect/event extraction -> validation/review -> spatial analysis -> visualisation -> interpretation`

At each stage, expose at least two methodological choices and their trade-offs. Preserve source evidence and provenance throughout.

## Current project state

The repository disaggregation and validation phase is complete on the cleanup branch.

- SH2026-specific research, teaching, benchmark, demo and test assets are consolidated under ``.
- `spatio-textual` remains a separately versioned reusable package; this repository is tested only against its public API.
- All ten workshop notebooks are present under `workshop/`.
- The clean CPU/default notebook path has passed the SH2026 Colab smoke workflow.
- The reusable package tests and Python compatibility matrix are green.
- SH2026 benchmark, rules, Hugging Face, journey, affect and CLDW external-validation workflows are green at the current PR head.
- `holdout_v1` is frozen and checksum-protected. It is a synthetic held-out benchmark and must not be used for further tuning while still being described as held out.
- Paid LLM workflows remain explicitly guarded and are not run automatically by routine package/refactor changes.
- The conference demo has one canonical entry point: `demo/streamlit_app.py`.
- A draft pull request targets `spatial-humanities-2026`; no merge has been performed.

## Deliverables

### A. Full-day Colab tutorial

Current notebook sequence:

1. `00_setup_and_orientation.ipynb`
2. `01_manual_annotation.ipynb`
3. `02_rules_and_gazetteers.ipynb`
4. `03_contextual_ner.ipynb`
5. `04_linking_and_ambiguity.ipynb`
6. `05_affect_and_events.ipynb`
7. `06_llm_structured_extraction.ipynb`
8. `07_compare_and_adjudicate.ipynb`
9. `08_from_text_to_map.ipynb`
10. `09_responsible_spatial_ai.ipynb`

The workshop core is implemented and smoke-tested. Remaining tutorial work is release hardening rather than basic notebook construction:

- create/finalise the instructor guide and troubleshooting material;
- freeze expected outputs/reference artefacts;
- generate provenance-bearing precomputed transformer/LLM fallbacks;
- prepare offline/lightweight contingency material;
- rehearse timing and shorten exercises where needed.

### B. Hosted demo

The canonical conference application is:

```bash
streamlit run demo/streamlit_app.py
```

The public-safe default path must work without an API key.

Priority additions for the next implementation phase:

- clear Home / Annotate / Compare / Explore / Review / About workflow;
- side-by-side source text and extracted annotations;
- visible method comparison for rule/spaCy/HF/LLM outputs;
- interactive map rather than raw GeoJSON only;
- per-segment affect plots and narrative sequence views;
- evidence/provenance display for every interpretive output;
- human correction/adjudication controls;
- curated public-safe example texts and presets;
- hosted deployment with cached models, graceful API-key handling and a lightweight default mode.

Stretch goal: schema-constrained journey extraction with origin, destination, transport, date/reason and evidence quote.

### C. Keynote lecture

Provisional thesis:

> AI does not make traditional Spatial Humanities methods obsolete. It changes where the bottlenecks lie: from finding explicit spatial signals to validating, interpreting and governing increasingly rich machine-generated representations of human experience.

Comparative spine:

1. Manual annotation: interpretively rich, transparent, expensive and difficult to scale.
2. Rule/gazetteer methods: deterministic, fast, reproducible and excellent on bounded tasks, but brittle outside anticipated vocabulary and forms.
3. Statistical/transformer NLP: contextual and scalable, but dependent on training domains, label inventories and benchmark assumptions.
4. LLMs: flexible structured extraction, implicit relations and rapid adaptation, but with hallucination, opacity, cost, non-determinism and governance risks.
5. Hybrid/human-in-the-loop workflows: use each method where it is strongest and retain evidence, disagreement and provenance.

Anchor case studies:

- Lake District writing: named places, geo-nouns, picturesque/wild descriptions and textual proximity.
- Holocaust survivor testimonies: Q/A-aware segmentation, journeys, affect and evidence-grounded extraction.
- Curatorial/archival workflow: AI as review and discovery support rather than automated historical authority.

## Evaluation matrix for the keynote and tutorial

Compare methods on:

- annotation effort;
- precision/recall where gold labels exist;
- ability to capture explicit vs implicit spatial information;
- robustness to spelling, ambiguity and historical language;
- portability across corpora;
- reproducibility/determinism;
- latency and computational requirements;
- financial/API cost;
- explainability and evidence traceability;
- ease of correction;
- privacy/data-governance risk;
- suitability for sensitive collections.

Avoid presenting the methods as a simple linear progression from "old" to "better". The stronger argument is methodological complementarity.

## Immediate next implementation block

### 1. Demo integration

Refactor the canonical Streamlit app around the conference user journey, while reusing the same schema, benchmark terminology, review events and provenance structures already used by the workshop.

Exit criterion: a non-technical humanities researcher can understand what happened to a text without reading raw JSON.

### 2. Workshop release package

Create the instructor guide, expected outputs, precomputed fallback artefacts, troubleshooting notes and contingency exercises.

Exit criterion: the workshop remains usable when network, GPU or paid APIs are unavailable.

### 3. Keynote evidence pack

Turn validated benchmark/external-validation outputs into a small set of defensible tables and signature figures. Separate synthetic holdout evidence from source-derived external validation explicitly.

Exit criterion: every quantitative keynote claim points to a reproducible experiment/result record and does not over-generalise from synthetic data.

### 4. Public deployment and rehearsal

Deploy the demo, test it from a fresh browser/session, run the workshop as a participant, rehearse keynote transitions around live/demo fallback states, and freeze QR codes/links.

Exit criterion: tutorial, demo and keynote tell one coherent story and survive network/API/model failure.

## Scope guardrails

Do not turn the project into a general-purpose GIS platform, full RAG copilot, multimodal audio/video pipeline or archive-scale production system before the conference release. The target is a polished research/teaching demonstrator with clear provenance and defensible comparisons.

Controlled-access Holocaust testimony text must not be bundled into the public repository or Colab notebooks. Use public-safe excerpts where permissions allow, synthetic structurally realistic examples, or precomputed aggregate outputs.

## Release target

The integrated release should only be tagged after the tutorial release package, hosted demo and keynote evidence pack pass their final rehearsal checks. Suggested milestone name: `sh2026-rc1`.
