# SH2026 Comparative Evaluation Framework

Status: **core framework frozen for the SH2026 conference experiments**

This document defines the common experimental structure for the Spatial Humanities 2026 workshop, demo and keynote. It deliberately compares **method families across task families**, rather than treating methods as a single ladder from older to newer or collapsing different tasks into one leaderboard.

## 1. Core research design

The SH2026 evaluation has three core task families:

1. **Spatial NER / spatial mention extraction** — recognition of named and, where the schema permits, non-named spatial expressions.
2. **Journey extraction** — reconstruction of structured movement events and their arguments.
3. **Affect** — classification of sentiment/emotion expressed in text, with evidence and uncertainty where supported.

These tasks represent progressively greater interpretive distance from literal surface forms:

`recognition -> event reconstruction -> interpretation`

The principal method families are:

1. **Rules / symbolic NLP** — gazetteers, regex/patterns, dependency/event heuristics and transparent lexicons.
2. **Contextual / transformer NLP** — spaCy statistical NER, Hugging Face transformer NER, and discriminative transformer classifiers/event extractors.
3. **LLMs** — schema-constrained generative extraction/classification with locally grounded evidence.
4. **Hybrid + human review** — optional applied condition combining model proposals, deterministic validation and explicit human adjudication.

The key question is not "Which method wins?" but:

> **Which computational paradigm works best for which level of spatial-humanities analysis, and at what cost in representation, evidence, uncertainty, computation and scholarly review?**

## 2. Method × task matrix

| Task | Rules / symbolic | Contextual / transformer | LLM | Hybrid + human review |
|---|---|---|---|---|
| Spatial NER / mentions | gazetteers + phrase/regex rules | spaCy NER; pinned HF NER | constrained TOPONYM-only NER; full spatial-schema extraction | optional adjudicated union/comparison |
| Journey extraction | movement triggers + dependency/event rules | discriminative transformer event/argument extraction | schema-constrained structured journey extraction | grounded proposal + review/edit/reject |
| Affect | transparent sentiment/emotion lexicons/rules | sentiment and emotion classifiers | schema-constrained affect classification with evidence | optional adjudicated affect interpretation |

Not every cell has the same output ontology. Therefore **within-task accuracy** and **representational reach** must be reported separately.

## 3. Spatial NER experiments

### 3.1 Apples-to-apples named-place recognition

Compare the following under the same `TOPONYM` reference task:

- rules/gazetteer;
- contextual spaCy NER;
- pinned Hugging Face transformer NER;
- constrained LLM TOPONYM-only extraction.

Primary metrics:

- exact-span precision, recall and F1;
- overlap-span precision, recall and F1 as secondary boundary analysis;
- unsupported/ungrounded span rate where applicable;
- latency and computational/API cost;
- review burden where a human-review condition is run.

### 3.2 Expanded spatial representation

Run a second LLM condition using the broader SH2026 span ontology, including where relevant:

`TOPONYM`, `GEONOUN`, `SPATIAL_RELATION`, `DISTANCE`, `DIRECTION`, `TIME`, `MOVEMENT_CUE`, `TRANSPORT_CUE`, `SUBJECTIVE_DESCRIPTOR`, `SENSORY_DESCRIPTOR`, `DEICTIC_REFERENCE`.

This experiment answers a different question from TOPONYM-only NER: **how much of the broader spatial-humanities reference ontology can the method represent?**

Do not claim that a method is "more accurate" merely because it was allowed to output a richer ontology.

## 4. Journey extraction experiments

All journey methods should, as far as possible, emit the common journey schema:

- `start_location`;
- `end_location`;
- `transport_mode`;
- `date`;
- `journey_reason`;
- source-grounded `evidence_quote` and locally computed offsets;
- field status/certainty;
- review flag/reason where applicable.

### 4.1 Rules / dependency baseline

Build a deterministic baseline around:

`movement trigger -> candidate source/destination -> transport -> time -> reason`

Use named/spatial mentions, dependency/local-context patterns, Q/A-aware heuristics where explicitly defined, and conservative nulls where a field cannot be supported.

The baseline is intended to be serious and auditable, not a straw man.

### 4.2 Transformer event-extraction baseline

Frame journeys as movement events with argument roles such as:

- `SOURCE`;
- `DESTINATION`;
- `TRANSPORT`;
- `TIME`;
- `REASON`;
- `NONE`.

A discriminative transformer may detect movement triggers and classify trigger–span argument relations. Training/development material must be kept separate from the frozen held-out benchmark.

### 4.3 LLM structured extraction

The LLM proposes structured journey fields and verbatim evidence. Software, not the LLM, computes evidence offsets and validates grounding.

Core principle:

> **LLM proposes -> software grounds -> human reviews.**

Primary metrics:

- journey detection precision/recall/F1 under the frozen matching policy;
- field precision/recall/completeness;
- unsupported-field rate;
- evidence-grounded rate;
- contextual-inference rate;
- requires-review rate;
- review and correction burden;
- latency, tokens and estimated cost.

## 5. Affect experiments

Affect is retained as a first-class task, not a decorative downstream visualisation.

### 5.1 Separate sentiment from emotion

Where feasible, evaluate:

- **sentiment** as a polarity/evaluative task;
- **emotion** as a distinct, potentially multi-label task.

Do not silently translate one into the other.

### 5.2 Rule/lexicon baseline

Use transparent lexicons/rules as a teaching and interpretability baseline. Document domain-sensitive lexical assumptions explicitly. A lexicon that encodes terms strongly associated with a historical domain must not be presented as a neutral measure of psychological state.

### 5.3 Transformer affect baseline

Use pinned sentiment/emotion classifiers with exact model identifiers and label mappings recorded. If a model's label inventory differs from the SH2026 reference inventory, record the harmonisation rather than hiding it.

### 5.4 LLM affect condition

Use a constrained schema containing, where appropriate:

- sentiment label;
- emotion label(s);
- evidence quote;
- explicit vs inferred status;
- confidence/uncertainty;
- concise explanation for review.

Evidence must be grounded locally when a quoted span is returned.

Primary metrics may include:

- sentiment accuracy/F1;
- emotion micro/macro/multi-label F1 as appropriate;
- human-reference agreement;
- unsupported interpretation rate;
- evidence-grounded rate;
- inference rate;
- review/correction burden;
- latency, tokens and estimated cost.

Interpretive safeguard:

> **A model-labelled emotion is an interpretation of textual evidence, not a direct measurement of a historical person's psychological state.**

## 6. Shared evaluation dimensions

Across all three task families, report the dimensions that are meaningful for that task rather than forcing every cell to have every metric:

- within-task precision/recall/F1 or classification agreement;
- representational reach / ontology ceiling;
- explicit vs contextual/inferred information;
- evidence grounding and traceability;
- ambiguity/unresolved/null rate;
- unsupported prediction/interpretation rate;
- robustness to spelling, historical language and discourse context;
- reproducibility/determinism;
- latency and computational requirements;
- financial/API cost where reproducibly estimable;
- review burden;
- correction burden;
- privacy/data-governance implications.

Missing or inapplicable values remain `null`, not zero.

## 7. Data separation

Use three clearly separated evidence layers:

1. **Teaching/development examples** — may be inspected and iterated on; never reported as unbiased held-out results.
2. **Frozen synthetic SH2026 holdout** — controlled stress tests across the wider ontology and structured journeys.
3. **Source-derived external validation** — independently sourced historical material, such as CLDW, used to test transfer beyond synthetic examples.

A future journey-development corpus used to train a discriminative event extractor must be separate from the frozen SH2026 holdout. The held-out examples must not be used for prompt/rule/model tuning while retaining the label "held out".

Controlled-access Holocaust testimony text must not be placed in the public benchmark. Permitted aggregate results or separately cleared examples may be reported under their own governance conditions.

## 8. LLM comparison discipline

For formal LLM conditions preserve:

- exact provider and model identifier;
- API/model revision information where available;
- prompt/schema version and prompt hash;
- benchmark/source hash;
- decoding/reasoning configuration;
- raw structured response;
- normalized grounded output;
- telemetry and errors;
- run/commit provenance.

Do not tune prompts against the frozen holdout after inspecting formal errors and continue to describe the same run as an unbiased held-out evaluation.

## 9. Keynote analytical structure

The experimental story should be presented along two orthogonal axes:

### Task complexity

`spatial recognition -> journey/event reconstruction -> affective interpretation`

### Method family

`rules/symbolic -> contextual/transformer -> LLM -> hybrid human review`

The central SH2026 claim to test is:

> **Increasing model sophistication is not identical to increasing representational reach. As computational representations become richer and more interpretive, evidence, uncertainty, provenance and human judgement become more important, not less.**

This framing explicitly avoids a simple "old -> new -> better" story and leaves room for rules or transformers to outperform LLMs on bounded tasks or on cost, determinism, grounding and correction burden.

## 10. Implementation order

Proceed in this order so each layer is frozen before the next comparison is interpreted:

1. formalise the three-task framework and shared schemas;
2. add constrained LLM TOPONYM-only NER;
3. add LLM full spatial-schema extraction;
4. implement rule/dependency journey baseline;
5. create separate journey development data and transformer event-extraction baseline;
6. run frozen LLM journey extraction;
7. define/freeze affect reference policy and affect benchmark subset;
8. run rule, transformer and LLM affect conditions;
9. add human-review/correction measurements where feasible;
10. generate keynote figures only from frozen, provenance-preserved outputs.

The resulting keynote comparison should answer not merely **what AI can extract**, but **which method is appropriate for which scholarly question and what new verification burden accompanies richer computational interpretation**.
