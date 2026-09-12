# SH2026 Affect Experiment v1

## Purpose

Affect is the third core SH2026 task family alongside spatial recognition and journey extraction. It tests the progression from relatively literal recognition, through event reconstruction, to interpretation.

The experiment asks how rule-based, transformer and LLM methods differ when classifying affective evidence in text, while keeping sentiment and emotion conceptually separate and requiring interpretable evidence where the method supports it.

## Lineage from the Spatial Narratives / Geography of Emotions work

Earlier project materials used several related but non-identical affect label sets. The human-annotation slides include `fear`, `sadness`, `anger`, `joy`, `despair`, `anxiety`, `gratitude`, and `surprise`. A DistilRoBERTa classifier used in the earlier pipeline was trained for Ekman-style `fear`, `anger`, `disgust`, `joy`, `sadness`, `surprise`, plus `neutral`, while one reported analysis concentrated on four labels: `fear`, `anger`, `sadness`, and `joy`. Later presentation material describes a modified set including sadness, joy, anger, fear, gratitude, anxiety and surprise.

SH2026 does not silently treat these historical variants as one ontology. Version 1 freezes a new evaluation schema explicitly for this benchmark.

## Frozen v1 task schema

### Sentiment

Sentiment is a single-label classification task with the following labels:

- `positive`
- `negative`
- `neutral`
- `mixed`

Sentiment is not used as a proxy for emotion. A passage can be sentiment-neutral while containing an emotion cue, and an emotion such as surprise can occur with different sentiment polarities.

### Emotion

Emotion is a multi-label task. The permitted v1 emotion labels are:

- `fear`
- `sadness`
- `anger`
- `joy`
- `anxiety`
- `despair`
- `gratitude`
- `surprise`

An empty emotion-label list is valid and means that the reference annotator did not identify sufficient textual evidence for one of the frozen emotion categories. `neutral` is therefore not treated as a ninth emotion label.

`disgust` is not included in v1 despite its presence in the earlier off-the-shelf classifier ontology. This is a deliberate benchmark choice intended to align the principal SH2026 emotion task with the richer human-annotation set documented in the Geography of Emotions materials. The omission must be disclosed whenever results are compared with models whose native ontology includes disgust.

## Reference unit

The public benchmark should use sentence or short-passage units with enough surrounding context to interpret negation, reported speech and discourse carry-over. The development/reference corpus must remain separate from the final holdout.

Each reference record should contain:

- `example_id`
- `text`
- `sentiment_label`
- `emotion_labels`
- `evidence_spans` where feasible
- `explicit_or_inferred`
- `annotation_notes`
- `reference_status`
- source/provenance metadata

The reference is a documented scholarly annotation decision, not direct access to a historical person's internal psychological state.

## Development corpus design

Create a public-safe development corpus before model tuning. It should cover:

- explicit affect words;
- implicit affect without a canonical emotion word;
- negation;
- mixed or conflicting affect;
- reported speech and quoted affect;
- interviewer/question context where relevant;
- place-associated affect;
- journey-associated affect;
- neutral/no-affect examples;
- multiple simultaneous emotion labels;
- cases where domain terms such as `camp` or `ghetto` occur without sufficient affective evidence.

The development set must not be reused as the formal holdout.

## Method conditions

### 1. Rule / lexicon baseline

Retain the existing transparent lexicon/rule approach as a teaching and interpretability baseline. It must be described as an encoded heuristic, not as a neutral measure of emotion.

The v1 baseline must avoid circular domain assumptions. A term such as `camp` must not itself trigger fear, sadness or negative sentiment without independent affective evidence.

### 2. Transformer condition

Use pinned transformer models for sentiment and emotion. The selected checkpoints, revisions, native label mappings and training-domain limitations must be recorded before formal evaluation.

If the emotion model's native ontology differs from the frozen SH2026 labels, the mapping must be explicit. Labels that cannot be mapped defensibly should remain unsupported rather than being forced into the SH2026 ontology.

### 3. LLM condition

Use constrained structured output. The formal schema should return:

- `sentiment`
- `emotion_labels`
- `evidence_quote`
- `explicit_or_inferred`
- `confidence`
- optional short `notes`

The LLM proposes the interpretation. Software grounds the verbatim evidence quotation and computes offsets. Unsupported evidence or contextual inference routes the result to review.

### 4. Human review

For a fixed adjudication subset, record accept/edit/reject decisions and correction time. Human review is part of the experimental design rather than an afterthought.

## Metrics

Sentiment should report macro F1 and per-label precision/recall/F1. Emotion should report multi-label micro and macro precision/recall/F1 plus per-label metrics.

Across methods, also report where available:

- exact evidence-grounding rate;
- unsupported interpretation rate;
- contextual-inference rate;
- review-required rate;
- confidence/calibration measures when method outputs make them defensible;
- latency;
- token usage/API cost;
- correction burden.

Do not present accuracy numbers from incompatible ontologies as a single simple leaderboard.

## Scholarly language rule

Model outputs are classifications of textual evidence. They are not direct measurements of a person's psychological state.

Preferred phrasing includes:

- "the passage was classified as expressing fear";
- "the text contains evidence associated with sadness";
- "the model assigned the labels fear and anxiety".

Avoid asserting that a historical person *was* afraid, sad or angry solely because a classifier returned that label.

This distinction is mandatory for survivor testimony.

## Controlled testimony data

Public benchmark development and formal evaluation must use synthetic/public-safe or otherwise cleared material. Controlled survivor testimony may later be evaluated separately for research validity, but transcript text must not be released as part of the public benchmark unless explicitly cleared.

Any controlled-domain result must be reported separately from the public benchmark and preferably in aggregate/public-safe form.

## Keynote interpretation

Affect deliberately sits further from literal surface recognition than TOPONYM NER and usually further than explicit journey extraction. It therefore provides the strongest test of the keynote claim that richer machine-readable representation increases both interpretive reach and the burden of validation.

The intended progression is:

`Spatial entities -> Journeys -> Affect`

across:

`Rules -> Transformers -> LLMs -> Human review`

The experiment should test that progression rather than assume that the final method is automatically better.
