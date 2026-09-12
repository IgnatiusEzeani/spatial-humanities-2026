# SH2026 Gold Annotation Guide

Status: **working reference policy for the SH2026 tutorial/benchmark**

Schema version: `spatio-textual-gold-0.1`

This guide defines the human reference annotations used in the Spatial Humanities 2026 workshop, demo and comparative experiments. The purpose is not to manufacture an interpretation-free `ground truth`. It is to make the human decisions against which computational methods are compared **explicit, inspectable and reproducible**.

The common audit/export vocabulary remains defined in `docs/COMMON_SCHEMA.md`. This document specifies how a small human reference set is created before model evaluation.

## 1. Why a human reference set is needed

A benchmark is only useful if the task being scored has been defined independently of the system being tested. The reference set therefore records:

- what strings a human annotator considers spatially relevant;
- where those strings occur in the source text;
- which conceptual layer they belong to;
- which relations are supported by the text;
- which journey fields are explicit, inferred or missing;
- what remains ambiguous or historically contingent;
- where an adjudicator made a policy choice rather than discovering an objective fact.

The reference set is deliberately small enough to inspect manually. It is a teaching and diagnostic benchmark, not a claim to corpus-scale representativeness.

## 2. Non-negotiable principles

1. **Source text is primary.** Every span and evidence quotation must point back to the exact source string.
2. **Offsets are half-open.** `start_char` is inclusive and `end_char` is exclusive, so Python `text[start_char:end_char]` must reproduce the annotated string exactly.
3. **Do not silently normalize.** Historical spellings, historical polities, variant forms and ambiguous place names remain as written in `text`.
4. **Recognition and resolution are different tasks.** A toponym can be correctly recognized while remaining geographically unresolved or ambiguous.
5. **Inference must be marked.** An inferred origin, date, reason, antecedent or place relation is not equivalent to an explicit string.
6. **Missing is a valid result.** Do not invent a value merely to complete a schema.
7. **Evidence is required for journeys.** A retained journey record must carry an exact evidence quotation and recoverable offsets.
8. **Human disagreement is data.** Boundary and ontology disagreements should be discussed and, where useful, retained in adjudication notes.
9. **No controlled testimony text is added to the public benchmark.** Public notebooks use distributable historical material and instructor-created synthetic examples.
10. **The reference is versioned.** Changes to annotation policy must result in a new schema/reference version or a documented adjudication change.

## 3. Record structure

Each JSONL line is one document/example:

```json
{
  "schema_version": "spatio-textual-gold-0.1",
  "example_id": "example_001",
  "title": "...",
  "text": "...",
  "source": {
    "genre": "...",
    "source_note": "...",
    "distribution_status": "safe_to_distribute"
  },
  "annotation_policy": "docs/GOLD_ANNOTATION_GUIDE.md",
  "reference_status": "adjudicated_reference",
  "spans": [],
  "relations": [],
  "journeys": [],
  "adjudication_notes": []
}
```

### `reference_status`

Use one of:

- `draft`
- `adjudicated_reference`
- `provisional_until_source_citation_verified`
- `deprecated`

A provisional record may be used during development but must not be presented as release-ready until the source/citation issue is resolved.

## 4. Span annotation vocabulary

Span annotations use a fine-grained label plus a broader `layer`. This avoids forcing every kind of spatial evidence into an entity-recognition ontology.

### 4.1 `TOPONYM`

A proper-name place expression as written in the source.

Examples include settlements, rivers, lakes, camps, regions and historical polities.

Recommended layer: `entity`  
Recommended conceptual level: `location`

Rules:

- preserve historical/variant spelling exactly;
- do not encode a modern resolved place in the `text` field;
- if the place is known to be ambiguous, record that in `attributes` rather than selecting a location without evidence.

### 4.2 `GEONOUN`

A common noun or noun phrase denoting a geographical/spatial setting or feature, such as `village`, `road`, `river`, `lake`, `woods`, `camp` or `border`.

Recommended layer: `entity`  
Recommended conceptual level: `locale`

A geo-noun does not have to be directly geocodable.

### 4.3 `SPATIAL_RELATION`

A lexical cue encoding a spatial relation, for example `near`, `beyond the river` or a comparable relational expression.

Recommended layer: `spatial_cue`

When a relation has identifiable arguments, also create a relation record. The span records the wording; the relation record records the interpreted relation.

### 4.4 `DISTANCE`

Quantitative or qualitative distance wording.

Examples:

- `about six miles distant`
- `nearest`

Recommended layer: `spatial_cue`

Where possible, attributes may store a value/unit or mark the expression as qualitative/approximate. Do not coerce vague language into a false precision.

### 4.5 `DIRECTION`

Directional wording, including narrator-relative frames such as `to our left`.

Recommended layer: `spatial_cue`

Do not translate narrator-relative direction into a compass bearing unless the source supplies the necessary frame of reference.

### 4.6 `TIME`

Absolute or relative temporal cues relevant to spatial/narrative interpretation.

Examples include years, durations and expressions such as `before dawn`, `Years later` or `after liberation`.

Recommended layer: `temporal_cue`

Do not normalize relative expressions to a date unless enough contextual evidence exists.

### 4.7 `MOVEMENT_CUE`

A lexical action/experience cue relevant to movement or spatial transition, such as `left`, `travelled`, `deported` or `hid`.

Recommended layer: `event_cue`

This label does **not** by itself assert a complete journey.

### 4.8 `TRANSPORT_CUE`

Text explicitly identifying a transport mode, such as `by train`.

Recommended layer: `journey_cue`

### 4.9 `SUBJECTIVE_DESCRIPTOR`

A subjective evaluative description associated with place/landscape, for example terms such as `picturesque` or `wild` when used evaluatively.

Recommended layer: `sense_of_place`

### 4.10 `SENSORY_DESCRIPTOR`

A sensory/embodied description relevant to sense of place, such as `very cold`.

Recommended layer: `sense_of_place`

A sensory descriptor must not automatically be converted into a psychological emotion label.

### 4.11 `DEICTIC_REFERENCE`

A place-referring expression such as `there` whose referent depends on discourse context.

Recommended layer: `spatial_cue`

The span can be explicit while the link to its referent is a contextual inference.

## 5. Span boundaries

Boundary policy is intentionally conservative:

- annotate the smallest span that captures the intended concept **unless** the full phrase is required to preserve the relation meaning;
- preserve modifiers when they are part of the spatial semantics, e.g. `about six miles distant`;
- nested spans are allowed when they represent different layers, e.g. `river` (`GEONOUN`) inside `beyond the river` (`SPATIAL_RELATION`);
- overlapping spans of the same label should be avoided unless a documented annotation reason exists;
- punctuation is normally excluded unless it is semantically necessary.

Boundary disagreement is expected. Exact-match and overlap-match scores should therefore both be reported in teaching experiments where boundary choices materially affect the result.

## 6. Certainty vocabulary

Use:

- `explicit`: directly expressed in the source wording;
- `contextual_inference`: recoverable only by discourse/anaphoric/contextual reasoning;
- `ambiguous`: the source supports more than one reasonable interpretation/resolution;
- `human_supplied`: added during review from documented external/human knowledge;
- `missing`: used for structured journey fields when the source does not provide a value.

For ordinary span annotations, `explicit` is the default. A deictic span such as `there` is explicitly present, but its relation to `London` is contextual inference.

## 7. Relation annotation

A relation record separates **what wording is present** from **what relation the annotator interprets**.

```json
{
  "relation_id": "r001",
  "type": "CONNECTS",
  "source_span_id": "s001",
  "target_span_id": "s002",
  "source_ref": null,
  "target_ref": null,
  "evidence_quote": "...",
  "evidence_start_char": 0,
  "evidence_end_char": 42,
  "certainty": "explicit",
  "attributes": {},
  "notes": null
}
```

If one argument is not represented by an annotated span, use `source_ref` or `target_ref`, for example `narrator_group` or `mother's family`.

Initial relation types used in the teaching set include:

- `CONNECTS`
- `APPROX_DISTANCE`
- `SPANS`
- `OUTFLOWS_FROM`
- `NEAR`
- `DEICTIC_REFERS_TO`
- `MOVES_FROM_TO`
- `BEYOND`
- `LEFT_OF`

This list may grow, but additions should be documented rather than introduced silently.

## 8. Journey annotation

Journey records follow `docs/COMMON_SCHEMA.md`.

A human reference journey must include:

- `start_location`
- `end_location`
- `transport_mode`
- `date`
- `journey_reason`
- exact `evidence_quote`
- `evidence_start_char`
- `evidence_end_char`
- `explicit_or_inferred` status for every structured field
- `requires_review`
- review notes where inference or ambiguity is present.

### Journey field policy

For each structured field, use one of:

- `explicit`
- `contextual_inference`
- `missing`
- `human_supplied`

If a field is marked `missing`, its value should remain null/empty.

If **any** field is `contextual_inference`, the journey must have `requires_review: true` in the public/demo workflow.

A textual place can be explicit while its geographic resolution remains ambiguous. For example, `Cambridge` can be an explicit journey origin while still requiring place-linking review.

## 9. Annotation procedure

### Pass 1: unconstrained reading

Annotators read the passage once and mark anything they regard as spatially meaningful without consulting model output.

Purpose: expose intuitive differences before an ontology constrains them.

### Pass 2: guided span annotation

Annotators apply the label guide above and record exact offsets.

### Pass 3: relations

Annotators connect supported arguments and copy the smallest sufficient evidence quotation.

### Pass 4: journeys

Where a movement can be represented as a structured journey, fill only the fields supported by the source/context and mark field status explicitly.

### Pass 5: adjudication

A second reader/adjudicator reviews:

- span boundaries;
- label disagreements;
- relation arguments;
- historical/place-resolution assumptions;
- contextual inference;
- evidence offsets;
- whether a proposed journey is warranted at all.

Disagreements that reveal a meaningful methodological choice should be documented in `adjudication_notes` rather than erased from the teaching narrative.

## 10. Inter-annotator agreement and benchmark reporting

For a workshop-sized set, report at least:

1. exact span precision/recall/F1;
2. overlap span precision/recall/F1;
3. label-sensitive disagreement examples;
4. relation agreement where applicable;
5. journey-field agreement (`explicit`, `inferred`, `missing`);
6. number of adjudication edits.

Do **not** use a single agreement number as evidence that the ontology is objective. The disagreement analysis is part of the scholarly result.

## 11. Evaluation boundary

The reference set should be created/frozen before running the methods being evaluated on it.

During development, examples may be used to debug code. For the final keynote experiment, create a small held-out subset or a second independently annotated batch so that prompt/rule/model choices are not repeatedly tuned on every reference example.

Suggested final structure:

- `teaching_reference`: visible examples used in notebooks;
- `benchmark_dev`: examples used to debug scoring/integration;
- `benchmark_holdout`: examples annotated before the final comparison and not used for prompt/rule tuning.

The initial `gold_reference_v0.1.jsonl` is a teaching/development reference, not yet the final keynote holdout set.

## 12. Historical geography

Historical place names require special care.

- preserve the source expression;
- record modern candidate mappings separately, if needed;
- never overwrite a historical polity with a present-day country label;
- distinguish historical-geographic interpretation from textual extraction;
- surface uncertain mappings for review.

For the current synthetic example, `Czechoslovakia` is intentionally retained as a historical polity. A resolver may propose modern candidates, but that proposal is not the gold textual label.

## 13. Sensitive collections

The public reference set must not contain controlled-access Holocaust testimony transcripts.

For sensitive research demonstrations use only:

- cleared/publicly distributable excerpts where permission is explicit;
- synthetic examples that are clearly labelled synthetic;
- aggregate/precomputed results that do not reproduce controlled text.

Synthetic oral-history examples must never be presented as authentic survivor testimony.

## 14. Quality-control checklist

Before a gold/reference file is accepted:

- [ ] `schema_version` present;
- [ ] unique `example_id`;
- [ ] source/distribution status present;
- [ ] exact text retained;
- [ ] every span offset reproduces its `text` exactly;
- [ ] span IDs unique within document;
- [ ] every relation endpoint ID resolves or uses an explicit external `*_ref`;
- [ ] every relation evidence quote matches its offsets;
- [ ] every journey evidence quote matches its offsets;
- [ ] every journey field has an explicit/inferred/missing/human-supplied status;
- [ ] contextual inference triggers review;
- [ ] historical/ambiguous place assumptions are documented;
- [ ] no controlled text is present in the public teaching set;
- [ ] provisional source citations are clearly flagged.

## 15. Release gate for the Lake District example

The current Penrith/Pooley Bridge passage is retained because it is already used in the SH2026 development materials, but its record is marked `provisional_until_source_citation_verified`.

Before the public workshop release, verify and add the exact CLDW source/edition citation. Until then, the benchmark must not imply that the citation has been resolved.

## 16. Core teaching message

**Gold annotations are not discovered facts handed down by a neutral human oracle. They are documented scholarly decisions.**

That is precisely why comparing manual, rule-based, statistical/transformer and LLM workflows is useful: the comparison should reveal not only which system matches a reference, but also which assumptions each method makes visible or hides.
