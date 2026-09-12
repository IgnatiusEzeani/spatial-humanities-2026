# SH2026 Common Annotation and Audit Schema

Status: **frozen for tutorial/demo integration unless a breaking issue is found**

Purpose: provide one output model shared by the Colab tutorial, Streamlit demo and keynote experiments.

## Design principles

1. Preserve the original text and stable source identifiers.
2. Preserve character offsets wherever extraction is grounded in source text.
3. Distinguish model output from human correction.
4. Distinguish unresolved/ambiguous values from missing values.
5. Preserve backend/model/provider telemetry.
6. Never treat inferred LLM fields as equivalent to verbatim evidence.
7. Keep raw model results available where practical so aggregate findings remain auditable.

## 1. Segment record

Each text-processing unit should use the following top-level structure.

```json
{
  "fileId": "example_001",
  "segId": 1,
  "segCount": 4,
  "segStartChar": 0,
  "segEndChar": 512,
  "segTextCharLength": 512,
  "text": "...",

  "role": "witness",
  "turnId": 2,
  "qaPairId": 1,
  "isQuestion": false,
  "isAnswer": true,

  "entities": [],
  "event_data": [],
  "journeys": [],

  "sentiment": {},
  "emotion": {},

  "themes": [],
  "summary": null,

  "telemetry": [],
  "requires_review": false,
  "review_notes": [],
  "human_edits": []
}
```

### Backwards compatibility

Until package internals are refactored, existing flattened affect keys remain valid:

- `sentiment_label`
- `sentiment_score`
- `sentiment_distribution`
- `emotion_label`
- `emotion_score`
- `emotion_dist`

The tutorial/demo may convert these to nested display objects, but exports should retain the current v0.3 fields during the SH2026 sprint to avoid unnecessary breakage.

## 2. Entity record

```json
{
  "entityId": "optional-stable-id",
  "text": "Amsterdam",
  "label": "GPE",
  "place_type": "PLACE",
  "start_char": 26,
  "end_char": 35,
  "start_token": 5,
  "end_token": 6,

  "confidence": 0.97,
  "source": "spacy:en_core_web_trf",

  "resolved_name": "Amsterdam",
  "lat": 52.3676,
  "lon": 4.9041,
  "resolution_status": "resolved",
  "geo_source": "geonamescache:city",
  "geo_confidence": 0.88,
  "ambiguous": false,
  "candidates": [],

  "vote_count": null,
  "vote_ratio": null,
  "voters": [],

  "requires_review": false
}
```

### Resolution status vocabulary

Use only:

- `resolved`
- `resolved_ambiguous`
- `unresolved`
- `not_applicable`
- `human_resolved`

Original entity text must never be overwritten by a normalized/resolved name.

## 3. Affect record

### Sentiment

```json
{
  "label": "mixed",
  "score": 0.45,
  "distribution": {
    "positive": 0.35,
    "neutral": 0.20,
    "negative": 0.45
  },
  "backend": "hf",
  "model": "...",
  "explanation": null
}
```

### Emotion

```json
{
  "label": "Fear",
  "score": 0.61,
  "distribution": {
    "Neutral": 0.05,
    "Joy": 0.02,
    "Surprise": 0.04,
    "Sadness": 0.21,
    "Fear": 0.61,
    "Anger": 0.05,
    "Disgust": 0.02
  },
  "backend": "hf",
  "model": "...",
  "explanation": null
}
```

### Interpretive rule

Affect labels are computational annotations, not claims about a narrator's psychological state. In tutorial/demo prose use formulations such as:

- `model-labelled affect`
- `affective signal`
- `passage classified as ...`

Avoid formulations such as `the survivor was afraid` when the system has only classified the textual segment.

## 4. Narrator-centred event record

Keep the existing lightweight event/action layer conceptually distinct from journeys.

```json
{
  "event": "travelled",
  "lemma": "travel",
  "event_type": "narrator_action",
  "subject": ["I"],
  "start_char": 120,
  "end_char": 129,
  "confidence": 0.75,
  "source": "spacy-rule"
}
```

This record answers: **what action/experience cue appears in the segment?**

It does not by itself answer: **what structured journey took place?**

## 5. Journey record

This is the key SH2026 addition.

```json
{
  "journeyId": "example_001-j0001",
  "fileId": "example_001",
  "segId": 3,

  "start_location": "Amsterdam",
  "end_location": "Auschwitz",
  "transport_mode": "train",
  "date": null,
  "journey_reason": "deportation",

  "evidence_quote": "Later we were deported by train to Auschwitz.",
  "evidence_start_char": 102,
  "evidence_end_char": 149,

  "explicit_or_inferred": {
    "start_location": "contextual_inference",
    "end_location": "explicit",
    "transport_mode": "explicit",
    "date": "missing",
    "journey_reason": "explicit"
  },

  "confidence": 0.78,
  "model": "...",
  "provider": "...",
  "requires_review": true,
  "review_notes": ["Start location is inherited from prior context."],

  "human_status": "unreviewed",
  "human_edits": []
}
```

### Required rules for journey extraction

- `evidence_quote` is mandatory for any retained journey record.
- Evidence must be copied from source text, not paraphrased.
- Evidence offsets must be recoverable where possible.
- `unknown` must not be replaced with guessed values.
- Each structured field should be marked as `explicit`, `contextual_inference`, `missing` or `human_supplied`.
- A contextual inference must trigger review in the public demo.

## 6. Human edit record

```json
{
  "timestamp": "2026-09-07T20:30:00Z",
  "field": "end_location",
  "old_value": "London",
  "new_value": "London, England",
  "action": "edit",
  "reason": "disambiguation",
  "editor": "session_user"
}
```

For the public demo, no identity collection is required. `session_user` is sufficient.

## 7. Review record

Use a consistent review vocabulary.

### Reasons

- `model_disagreement`
- `ambiguous_place`
- `unresolved_place`
- `low_confidence`
- `contextual_inference`
- `unsupported_llm_field`
- `segmentation_exception`
- `backend_error`
- `human_flag`

### Human status

- `unreviewed`
- `accepted`
- `edited`
- `rejected`

## 8. Telemetry record

Retain the current package format:

```json
{
  "task": "spatial_entity_recognition",
  "backend": "spacy",
  "provider": "local",
  "model": "en_core_web_trf",
  "latency_ms": 123.4,
  "input_chars": 1000,
  "input_tokens_est": 250,
  "output_tokens_est": 40,
  "cost_usd_est": 0.0,
  "success": true,
  "error": null
}
```

### SH2026 reporting rule

Unless exact provider usage and a dated price table are available, label monetary values as **estimated computational/API cost** rather than actual cost.

## 9. Comparison record

For keynote/tutorial benchmarking, produce one tidy table per task:

```text
example_id
method
backend
model
task
precision
recall
f1
coverage
unsupported_rate
ambiguous_rate
human_edits_required
latency_ms
cost_usd_est
notes
```

Not every metric applies to every task. Missing metrics should remain null rather than being coerced to zero.

## 10. Schema invariants

The following are non-negotiable for SH2026:

1. Source text remains available to the researcher.
2. Original strings are never silently overwritten by normalization.
3. Machine inference and source evidence remain distinguishable.
4. Human corrections are additive and auditable.
5. Uncertainty is exported, not only displayed.
6. The same core record vocabulary is used in notebooks, app and keynote figures.
