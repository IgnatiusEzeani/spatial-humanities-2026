# Spatial Humanities 2026: Day 1 Technical and Scholarly Audit

Branch: `spatial-humanities-2026`

Date: 2026-09-07

## Executive assessment

The repository is already a strong research prototype. The core architecture needed for SH2026 exists: segmentation, spaCy/HF entity annotation, rule/HF/LLM affect backends, place linking, model adjudication, telemetry, export and a Streamlit front end.

The main work is not to add many more algorithms. It is to make the package methodologically honest, pedagogically coherent and visually useful for Spatial Humanities researchers.

The most important finding from this audit is that the current public-facing app exposes several components at different levels of maturity. The SH2026 release should therefore distinguish clearly between:

1. **production-ready teaching components**: segmentation, entity annotation, model comparison, review flags, telemetry, export;
2. **research baselines**: rule sentiment/emotion and narrator-centred action extraction;
3. **prototype/placeholder interpretation**: current summaries/themes in `analysis.py`;
4. **not yet integrated**: evidence-first journey extraction of the form used in the Holocaust journey research.

## What is already usable

### Segmentation

`spatio_textual.qa.segment_testimony()` supports role-aware Q/A turns with character offsets, role, turn ID, question/answer flags and Q/A pair IDs.

`split_into_segments()` supports sentence-safe character-budget or fixed-count segmentation with source offsets.

**SH2026 use:** strong for teaching the importance of unit-of-analysis choice and provenance.

**Important caveat:** the current implementation is turn-level. It does not yet implement the richer topic-aware grouping described in earlier project presentations (for example, grouping a run of short biographical Q/As into an ID block or detecting topic shifts automatically). Do not claim this in the keynote/demo until implemented.

### Spatial entity annotation

The package supports:

- spaCy `en_core_web_sm` and `en_core_web_trf`;
- Hugging Face token-classification models;
- EntityRuler resources for project-specific categories;
- place classification and optional coordinate linking;
- character/token offsets;
- telemetry.

**SH2026 use:** strong basis for a controlled method comparison.

### Model comparison and adjudication

`moe.py` can run multiple NER models, calculate entity votes and flag disagreements for review.

**SH2026 use:** excellent conceptual device for demonstrating that model disagreement is evidence, not merely an error to hide.

**Caveat:** adjudication currently depends on near-exact character spans, labels and text. It does not yet robustly reconcile partial spans, synonymous labels or nested entities. Call this *model voting/adjudication*, not a sophisticated mixture-of-experts architecture.

### Affect analysis

Rule, HF and LLM-capable sentiment/emotion interfaces share a common output shape and telemetry.

**SH2026 use:** very useful for demonstrating interchangeable backends.

**Caveat:** the current rule lexicons are deliberately small baselines. Some domain terms directly encode affect (for example `camp` and `deported` contribute to negative/fear rules). That makes the rule backend useful as a transparent teaching baseline, but not as an unbiased research measurement. It must be labelled as such.

### Place linking

`GeoResolver` gives an offline-safe resolver using `geonamescache`, country/continent matches and ambiguity flags.

**SH2026 use:** useful for explaining that NER and entity resolution are separate tasks.

**Critical caveat for historical humanities:** the resolver is not historically aware. Current aliases include mappings such as `England -> United Kingdom` and `Czechoslovakia -> Czechia`. These may be acceptable conveniences in a demo but are historically and conceptually lossy. Public demo output should expose the original string and resolution source, and historical-sensitive examples should be flagged for human review rather than silently normalised.

### Telemetry

The pipeline records backend, provider, model, latency, token estimates, cost estimate and success/error information.

**SH2026 use:** this is a signature feature. Use it to compare not only quality, but also speed, computational burden, API dependence and reproducibility.

**Caveat:** current cost fields are estimates/offline placeholders and LLM costs may be `null`. Do not present them as billing-accurate unless provider-specific accounting is added.

## Components that need work before the public demo

### 1. Current `Interpretation` output is too weak

`analysis.py` currently:

- creates a summary from the first two sentences;
- creates an interpretation string from sentiment/emotion labels and entity count;
- assigns themes using a small keyword dictionary.

This is acceptable as a test fixture, but not strong enough to present publicly as substantive scholarly interpretation.

**Decision:** rename it in the UI to **Baseline summary/themes** or disable it by default until a stronger, evidence-aware implementation is added.

### 2. The app does not yet integrate research-grade journey extraction

The Holocaust journey research uses structured records such as:

- start location;
- end location;
- transport mode;
- date;
- journey reason;
- evidence quote;
- start/end offsets;
- source chunk ID;
- confidence/uncertainty.

The current app does not expose this. `event_data` is currently narrator-centred verb/action extraction and `events.py` contains a separate richer event pipeline, but neither is equivalent to the evidence-first journey schema.

**Decision:** implement a small, schema-constrained `journeys.py` module for SH2026. It can be optional and demonstrated on short, public-safe texts. Every extracted journey must retain verbatim evidence and source offsets.

### 3. Visualisation is still developer-facing

The current Streamlit Visualisation tab shows:

- a co-occurrence edge dataframe;
- raw GeoJSON JSON.

That is not yet a humanities-facing exploration interface.

**Must add:**

- actual interactive map;
- narrative/segment sequence chart;
- sentiment/emotion distribution or trajectory;
- clickable evidence/source display;
- method-comparison view.

### 4. Review is visible but not editable

The review queue surfaces disagreements and unresolved locations, but there are no correction/adjudication controls.

**Must add for SH2026 demo:** allow a user to accept/edit/reject at least entity text/type/resolution and store the correction in session state/export.

### 5. The app has too many expert controls at first contact

The sidebar exposes model/provider/segmentation/MoE settings before users understand the task.

**Decision:** create two modes:

- **Guided mode**: task presets and sensible defaults for humanities users;
- **Expert mode**: current low-level controls.

## Methodological risks to surface rather than hide

### Rule-based methods

Strengths:

- deterministic;
- inspectable;
- fast;
- domain knowledge can be encoded directly;
- excellent baseline for bounded tasks.

Risks:

- brittle vocabulary/forms;
- maintenance burden;
- domain assumptions are encoded in rules;
- poor transfer to new corpora.

### Statistical/transformer NLP

Strengths:

- contextual generalisation;
- scalable;
- reproducible with fixed models/configurations;
- probabilistic confidence.

Risks:

- training-domain mismatch;
- label ontology limits what can be seen;
- historical spelling and genre variation;
- model confidence is not scholarly certainty.

### LLMs

Strengths:

- flexible schema-constrained extraction;
- implicit relations and long-range cues;
- fast adaptation to new tasks;
- natural bridge from extraction to richer semantic structure.

Risks:

- unsupported inference/hallucination;
- non-determinism;
- provider/version drift;
- cost and latency;
- data-governance concerns;
- temptation to collapse uncertainty into fluent output.

### Manual annotation

Strengths:

- domain expertise;
- close contextual interpretation;
- explicit negotiation of ambiguity.

Risks:

- expensive and slow;
- inter-annotator disagreement;
- difficult to scale;
- annotation guidelines themselves encode theoretical commitments.

## SH2026 benchmark design

Do not frame the experiment as a race with one winner. Compare approaches along multiple dimensions.

### Primary task set

1. **Explicit toponym extraction**
   - best dataset: CLDW gold-standard place annotations.
   - metrics: precision, recall, F1.

2. **Geo-noun and qualitative spatial expression extraction**
   - examples: road, lake, hill, camp, ghetto, `near`, `on the left`, `at the foot of`.
   - metrics: precision/recall on a small SH2026 hand-labelled set plus qualitative error categories.

3. **Spatial relation / nearness extraction**
   - Lake District examples can connect textual nearness to actual distance.
   - compare rule/pattern extraction with LLM structured extraction.

4. **Affect classification**
   - compare rule, HF and LLM outputs.
   - emphasise disagreement and interpretive return to text rather than treating emotion labels as psychological ground truth.

5. **Journey extraction**
   - compare manual reference records with a constrained LLM extractor.
   - require source evidence and offsets.
   - measure field completeness and unsupported-field rate, not only record recall.

### Cross-cutting measures

- task accuracy/coverage;
- latency;
- computational requirements;
- API dependence/cost;
- deterministic reproducibility;
- portability across corpora;
- evidence traceability;
- human correction effort;
- unresolved/ambiguous rate;
- governance/sensitivity risk.

## Public-safe teaching data plan

### Use openly in Colab/demo

1. **Corpus of Lake District Writing** examples where repository/licensing permits reuse.
   - primary morning workshop corpus;
   - supports classic GTA, rules, NER, semantic descriptors and nearness.

2. **Synthetic oral-history/testimony examples** that reproduce Q/A structure and spatial ambiguity without reproducing controlled testimony content.

3. **Small instructor-created spatial narratives** designed to expose specific failure modes: ambiguous cities, historical place names, relative spatial language and implicit journeys.

### Use as precomputed/aggregate research results only

Controlled-access Holocaust testimony transcripts.

The public materials may show aggregate counts, schemas, diagrams and suitably cleared examples, but should not bundle controlled transcript files.

## Priority implementation list

### Must-have for SH2026 release candidate

- freeze common schema (`COMMON_SCHEMA.md`);
- Colab landing/setup notebook;
- manual/rule/spaCy comparison notebook;
- HF/LLM comparison notebook with precomputed fallbacks;
- guided Streamlit mode;
- highlighted source-text/entity view;
- interactive map;
- method comparison page;
- editable review/adjudication;
- disable/rename placeholder `Interpretation` output;
- public-safe examples;
- journey schema + evidence-first short-text extractor;
- smoke tests for lightweight tutorial/demo path.

### Should-have

- narrative affect trajectory chart;
- geocoding candidate selector;
- benchmark runner that writes a single comparison dataframe;
- export of human corrections/provenance;
- precomputed results for HF/LLM sections;
- projector-friendly demo preset.

### Stretch

- historical gazetteer support;
- richer spatial relation ontology;
- journey map with ordered route edges;
- semantic model adjudication;
- provider-specific exact cost accounting;
- full archival/copilot workflow.

## Key keynote conclusion emerging from the audit

The repository supports a stronger argument than `LLMs beat NLP`:

> The important transition is from extracting what is explicitly named to constructing richer, machine-readable accounts of spatial experience. As representation becomes richer, verification, uncertainty, provenance and human judgement become more important, not less.

The SH2026 demonstrator should make that principle visible in every output.
