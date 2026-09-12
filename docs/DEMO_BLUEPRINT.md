# SH2026 Public Demo Blueprint

Working product name: **spatio-textual lab**

Primary audience: Spatial/Digital Humanities researchers rather than NLP developers.

## Product question

Given a narrative, what spatial information can different computational methods recover, what do they disagree about, and what evidence should a human inspect before using the output for research?

## Core UX

### 1. Home

Purpose: orient a non-technical visitor in under 30 seconds.

Show:

- one-sentence project statement;
- three example cards: Lake District narrative, synthetic oral-history Q/A, spatial-relation challenge;
- `Try guided analysis` primary button;
- `Expert settings` secondary option;
- a compact pipeline: `Text -> Methods -> Review -> Map/Explore`.

Do not show model/provider settings before the visitor chooses a task.

### 2. Annotate

Two-column layout:

**Left:** original source text.

**Right:** colour-highlighted annotations with filter chips:

- named places;
- geo-nouns;
- date/time;
- person;
- spatial/movement cues;
- sentiment/emotion.

Selecting an annotation should display:

- exact source span;
- label/type;
- model/backend;
- confidence where available;
- resolution candidate/coordinates;
- ambiguity status;
- review state.

Original text must remain unchanged.

### 3. Compare

This is the signature SH2026 view.

Run matched methods on the same passage and show:

| Reference/manual | Rules/resources | spaCy | HF transformer | LLM (optional) |
|---|---|---|---|---|

Comparison modes:

- entity spans;
- label disagreements;
- affect labels/distributions;
- structured journey fields;
- latency/API dependence;
- review burden.

Use disagreement highlighting rather than simply marking one model `wrong`.

### 4. Explore

Humanities-facing outputs:

- interactive point map for resolved named places;
- unresolved/non-mappable spatial items listed alongside the map;
- co-occurrence network;
- narrative segment timeline;
- affect trajectory/distribution;
- journey list and simple ordered-route map when journey extraction is enabled.

Every visual must support return to the source segment/evidence.

### 5. Review

A single queue for:

- model disagreement;
- ambiguous location;
- unresolved location;
- low confidence;
- contextual LLM inference;
- unsupported/missing evidence;
- backend error.

Minimum edit controls:

- Accept
- Edit
- Reject

For places, `Edit` should allow selecting a resolution candidate or preserving the place as unresolved/non-cartographic.

Human decisions must be added to export rather than overwriting machine output silently.

### 6. About / Methods

Explain method families, not vendor marketing.

Include:

- manual/reference annotation;
- rules/resources;
- spaCy statistical/transformer NLP;
- HF transformer NLP;
- LLM structured extraction;
- hybrid/adjudication.

For each show: strengths, typical failure modes, reproducibility and data-governance considerations.

## Guided presets

### Preset A: `Find spatial entities`

Fast model, linking enabled, no affect/LLM.

### Preset B: `Compare NLP models`

Short text only, spaCy small vs transformer/HF where environment allows.

### Preset C: `Trace affect across a narrative`

Segment text, compare rule/HF affect, show sequence plot.

### Preset D: `Extract a journey`

Optional LLM or precomputed output, evidence required.

### Preset E: `Inspect uncertainty`

Curated example designed to trigger ambiguous/unresolved places and model disagreement.

## Expert mode

Retain current controls:

- primary NER model;
- MoE/voting models;
- segmentation;
- linking;
- sentiment/emotion backends;
- LLM provider/model;
- event extraction;
- export format.

Expert mode should be behind an expander/toggle.

## Architecture proposal for one-week sprint

Avoid a full multi-page rewrite unless necessary. Refactor the current `app.py` into view functions first:

```text
app.py
spatio_textual/ui/
  home.py
  annotate_view.py
  compare_view.py
  explore_view.py
  review_view.py
  about_view.py
  components.py
```

If time becomes tight, keep a single Streamlit script but enforce the same logical sections with top-level tabs/navigation.

## Visualisation priority

### Must-have

1. Folium/Streamlit map for `to_geojson()` output.
2. Entity-highlighted source view.
3. Side-by-side model comparison table.
4. Affect distribution/sequence chart.
5. Evidence card for journeys/LLM claims.

### Should-have

6. Journey route polyline when both endpoints resolve.
7. Co-occurrence network visual instead of edge table only.
8. Human review counters/status filters.

## Current-code changes required

### `app.py`

- introduce guided/expert modes;
- replace raw developer-first sidebar flow;
- change `Interpretation` default from on to off, or rename to baseline summaries/themes;
- add highlighted source display;
- add real map;
- add editable review workflow;
- expose model comparison as a first-class view.

### `analysis.py`

Current keyword themes/first-two-sentence summary must not be presented as research-grade interpretation.

Short-term:

- rename functions/UI as baseline summary/theme hints;
- retain source evidence;
- make method metadata explicit.

Longer-term:

- controlled vocabulary support;
- evidence-bearing theme suggestions;
- optional LLM interpretation with schema and review.

### `viz.py`

Extend with:

- segment-affect dataframe helper;
- journey GeoJSON/line helper;
- reusable map builder for Streamlit;
- optional co-occurrence graph object/data.

### new `journeys.py`

Implement evidence-first structured journey extraction and validation according to `COMMON_SCHEMA.md`.

## Failure-mode behaviour

The demo must remain useful when:

- no internet;
- no API key;
- transformer dependencies unavailable;
- a model fails to download;
- geocoder returns no candidate;
- an LLM returns malformed JSON.

Expected behaviour: fall back visibly, never silently.

Examples:

- `Transformer model unavailable -> showing precomputed comparison output.`
- `No API key -> live LLM extraction disabled; inspect a saved research example.`
- `Place unresolved -> retained as textual place; no coordinate assigned.`

## Public-data guardrail

Do not package controlled VHA/USHMM transcript content in the hosted app. The public demo should use distributable Lake District material, synthetic oral-history examples and aggregate/cleared research outputs.

## Definition of done for RC1

A first-time visitor can:

1. select an example;
2. run a lightweight analysis;
3. see highlighted spatial evidence;
4. compare at least two methods;
5. inspect a map plus non-mappable/unresolved items;
6. encounter and resolve one review item;
7. export an audit-ready result;
8. understand which outputs are rules, model predictions, inferences and human decisions.
