# SH2026 Full-Day Colab Workshop

Official title: **AI and NLP for Spatial Humanities: From Manual Annotation to LLM-Assisted Interpretation**

Keynote companion: **From Coordinates to Context: Rethinking Spatial Humanities in the Age of Large Language Models**

## Teaching philosophy

This is not a package walkthrough and not an argument that newer methods simply replace older ones. Participants should understand what each methodological family can and cannot represent, then use `spatio-textual` as the shared implementation environment.

The workshop follows one repeated pattern:

`source text -> method -> output -> error/disagreement -> validation -> interpretation`

Across the day, the methodological sequence is:

`manual annotation -> rules/gazetteers -> contextual NLP -> entity resolution -> affect/events -> evidence-first LLM extraction -> adjudication -> mapping -> responsible Spatial AI`

Every notebook should run independently after setup and should contain or point to a fallback path for heavyweight/API-dependent sections.

## Audience assumptions

- Spatial/Digital Humanities researchers;
- mixed coding experience;
- Python familiarity helpful but not required;
- no assumption of GPU access;
- no requirement for paid LLM API keys.

## Learning outcomes

By the end of the day, participants should be able to:

1. explain why spatial information in text extends beyond named mappable places;
2. manually define and annotate a small spatial-information task;
3. compare rule/gazetteer, spaCy and transformer NER approaches;
4. distinguish recognition, resolution, relation and interpretation;
5. inspect ambiguity and model disagreement rather than hiding them;
6. compare rule, HF and LLM-capable affect pipelines critically;
7. understand schema-constrained LLM extraction and evidence requirements;
8. construct and inspect structured journey records;
9. record human accept/edit/reject decisions in an auditable way;
10. export auditable annotations to JSONL/CSV/GeoJSON;
11. explain why some spatial evidence should not be forced onto a point map;
12. document provenance, uncertainty, model drift and data-governance constraints.

## Notebook status

| Notebook | Topic | Status |
|---|---|---|
| `00_setup_and_orientation.ipynb` | Setup, location/locale/sense of place, common schema | Implemented |
| `01_manual_annotation.ipynb` | Human reference annotation and disagreement | Implemented |
| `02_rules_and_gazetteers.ipynb` | Deterministic baseline and rule failure analysis | Implemented |
| `03_contextual_ner.ipynb` | spaCy/HF NER, ontology ceiling, representational reach | Implemented + pinned HF fallback |
| `04_linking_and_ambiguity.ipynb` | Entity resolution, ambiguity, historical geography | Implemented |
| `05_affect_and_events.ipynb` | Sentiment, emotion and narrator-centred events | Implemented + pinned transformer fallback |
| `06_llm_structured_extraction.ipynb` | Evidence-first structured journey extraction | Implemented + deterministic no-API teaching route |
| `07_compare_and_adjudicate.ipynb` | Model disagreement, human review and correction burden | Implemented |
| `08_from_text_to_map.ipynb` | Entity/journey GeoJSON, route audit and mapping | Implemented |
| `09_responsible_spatial_ai.ipynb` | Provenance, uncertainty, governance and release audit | Implemented |

**Important:** “Implemented” means the notebook content and code path exist. It does not by itself mean a fresh manual Google Colab rehearsal has been completed for the final release candidate.

## Notebook sequence and teaching messages

### 00 · Setup and orientation — 30 min

Introduce location, locale and sense of place; install the SH2026 branch; load public-safe teaching examples; introduce the common audit schema; and show the end-to-end destination.

**Message:** spatial information in text is broader than named coordinates.

### 01 · Manual annotation — 35 min

Annotate places, geo-nouns, relations, distance/time and subjective descriptors; compare participant judgements with a documented reference; expose span, ontology and selection disagreement.

**Message:** human annotation is interpretive too.

### 02 · Rules and gazetteers — 45 min

Use bounded gazetteers/project resources, a deterministic EntityRuler/regex baseline, transparent failure analysis and latency/coverage measurements.

**Message:** transparent and reproducible does not mean complete.

### 03 · Contextual NER — 55 min

Separate contextual spaCy NER from spaCy + project resources; compare a revision-pinned HF NER condition through either the default precomputed teaching fallback or the optional live heavyweight route; harmonise labels; distinguish within-ontology accuracy from representational reach.

**Message:** context helps, but the training ontology still constrains what the model can see.

### 04 · Linking, ambiguity and historical geography — 40 min

Separate NER from entity resolution; inspect offline `GeoResolver` output, candidate ambiguity and historical polities; append human review rather than silently overwriting model output.

**Message:** a coordinate is an interpretation, not simply an annotation.

### 05 · Affect and narrator-centred events — 50 min

Compare sentiment/emotion rule baselines with a revision-pinned transformer condition, using a genuine precomputed teaching fallback on the default route and the same pinned models on the optional live route; inspect lexical cues and domain assumptions; and examine narrator-centred movement/action events.

**Message:** model-labelled affect is an analytical signal, not psychological ground truth.

### 06 · Evidence-first LLM structured extraction — 60 min

Inspect the journey JSON contract, require verbatim source evidence, compute offsets locally, distinguish `explicit`, `contextual_inference` and `missing`, expose unsupported/schema-invalid output, and optionally make a live provider call. The default path already uses deterministic teaching clients and therefore does not require an API key or pretend that a simulated response is empirical LLM evidence.

**Message:** the useful LLM pattern is constrained extraction + evidence + validation, not fluent generation.

### 07 · Compare, disagree and adjudicate — 45 min

Use model voting without erasing disagreement; accept/edit/reject review events; compare review burden with correction burden; and construct tidy comparison tables.

**Message:** there is no single method winner across all dimensions.

### 08 · From text to map — 35–45 min

Create point and journey GeoJSON, inspect route audits, build a Folium map, compare textual nearness with Euclidean distance, and retain spatial evidence that should not be forced onto a point map.

**Message:** mapping is one possible representation of spatial evidence, not its endpoint.

### 09 · Responsible Spatial AI — 20–30 min

Inspect provenance, uncertainty, data governance, model/provider drift and the release checklist.

**Message:** the more interpretive power delegated to AI, the stronger the audit trail must become.

## Proposed day schedule

| Time | Activity |
|---|---|
| 09:30-10:00 | Setup and conceptual framing |
| 10:00-10:35 | Manual annotation |
| 10:35-11:20 | Rules and gazetteers |
| 11:20-11:35 | Break |
| 11:35-12:30 | Contextual NER |
| 12:30-13:10 | Linking and ambiguity |
| 13:10-14:00 | Lunch |
| 14:00-14:50 | Affect and events |
| 14:50-15:50 | LLM structured extraction |
| 15:50-16:05 | Break |
| 16:05-16:50 | Compare and adjudicate |
| 16:50-17:25 | Text to map |
| 17:25-17:45 | Responsible Spatial AI + wrap-up |

The schedule is deliberately modular. If earlier discussion runs long, Notebook 09 can be used as a concise closing checklist and parts of Notebook 08 can be demonstrated rather than completed hands-on.

## Teaching datasets

**Primary:** Lake District examples that can be distributed under their source terms, for named places, geo-nouns, landscape descriptors, textual nearness and map comparison.

**Secondary:** instructor-created public-safe oral-history/travel examples with Q/A structure, movement, ambiguity, affect and missing fields.

**Research demonstration only:** controlled-access Holocaust testimony results should be represented through aggregate statistics, diagrams, schemas and cleared/precomputed material where permitted. Do **not** bundle controlled transcripts in the public notebooks or repository.

## Shared outputs

Notebooks write under:

```text
sh2026_outputs/
  annotations/
  comparisons/
  geojson/
  figures/
  human_review/
```

Outputs should follow `docs/COMMON_SCHEMA.md` so selected tables and figures can be reused directly in the hosted demo and keynote.

## Instructor and fallback package

`INSTRUCTOR_GUIDE.md` provides the delivery sequence, troubleshooting guidance, no-network/no-API routes and 5-minute/15-minute contingencies. The fallback package is now explicit and provenance-indexed in `demo/fallback_manifest_v1.json`:

- `fallback_journeys_v1.json`: instructor-curated journey examples for schema/evidence/review teaching, not model predictions;
- `ner_transformer_teaching_fallback_v1.json`: real revision-pinned Hugging Face NER output for Notebook 03;
- `affect_transformer_teaching_fallback_v1.json`: real revision-pinned transformer affect output for Notebook 05.

Notebook 06 uses a deterministic no-API teaching client and clearly distinguishes
that teaching mechanism from empirical LLM output.


## Open and test in Colab

These buttons open the current standalone release candidate on `main`. Start with a fresh Colab runtime. An existing checkout is reused, so restart with a fresh runtime when testing a new candidate. The package dependency is pinned to the exact commit reviewed in `spatio-textual` PR #4; no API key is needed for the default path.

| Notebook | Open |
|---|---|
| 00 setup and orientation | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/00_setup_and_orientation.ipynb) |
| 01 manual annotation | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/01_manual_annotation.ipynb) |
| 02 rules and gazetteers | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/02_rules_and_gazetteers.ipynb) |
| 03 contextual ner | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/03_contextual_ner.ipynb) |
| 04 linking and ambiguity | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/04_linking_and_ambiguity.ipynb) |
| 05 affect and events | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/05_affect_and_events.ipynb) |
| 06 llm structured extraction | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/06_llm_structured_extraction.ipynb) |
| 07 compare and adjudicate | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/07_compare_and_adjudicate.ipynb) |
| 08 from text to map | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/08_from_text_to_map.ipynb) |
| 09 responsible spatial ai | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/IgnatiusEzeani/spatial-humanities-2026/blob/main/workshop/09_responsible_spatial_ai.ipynb) |

After setup, record the installed commit with `!git rev-parse HEAD`. Manual rehearsal remains pending until the results are reported.
