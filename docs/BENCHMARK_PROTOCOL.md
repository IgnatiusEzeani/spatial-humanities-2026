# SH2026 Comparative Benchmark Protocol

Status: **protocol frozen; synthetic holdout and CLDW external-validation layers frozen; remaining LLM/journey/affect conditions to be run under this protocol**

Purpose: generate defensible empirical evidence for the workshop, hosted demo and keynote without turning the comparison into a simplistic model leaderboard.

The overarching task-by-method design is defined in `docs/EVALUATION_FRAMEWORK.md`.

## 1. Research questions

The benchmark asks three related but distinct questions:

1. **Within-task performance:** how accurately does each method perform the same bounded task?
2. **Representational reach:** what kinds of spatial or interpretive information can the method's output schema represent?
3. **Audit burden:** what evidence checking, uncertainty handling and human review are created by richer outputs?

A high NER F1, a structured journey extractor and an affect classifier answer different questions. They must not be collapsed into one score.

## 2. Core task families

The SH2026 comparison has three first-class task families:

1. **Spatial NER / spatial mention extraction** — recognition.
2. **Journey extraction** — event reconstruction.
3. **Affect** — sentiment/emotion interpretation.

Conceptually:

`recognition -> event reconstruction -> interpretation`

Affect remains a core evaluated task, not merely a downstream visualisation.

## 3. Method families to compare

Target methodological families:

1. human reference/manual annotation;
2. deterministic rules/gazetteers and symbolic heuristics;
3. contextual/statistical NLP;
4. discriminative transformer NLP;
5. schema-constrained LLM extraction/classification;
6. hybrid/adjudicated human-in-the-loop workflows where relevant.

The target comparison matrix is:

| Task | Rules / symbolic | Contextual / transformer | LLM | Hybrid + human review |
|---|---|---|---|---|
| Spatial NER / mentions | gazetteers + phrase/regex rules | spaCy NER; pinned HF NER | TOPONYM-only LLM; full spatial-schema LLM | optional adjudication |
| Journey extraction | movement/dependency/event rules | transformer event/argument extraction | structured evidence-first LLM | grounded review/edit/reject |
| Affect | transparent lexicon/rules | sentiment/emotion classifiers | constrained affect classification | optional adjudication |

Record exact backend/model/version at runtime. Do not use labels such as simply `AI`, `transformer` or `LLM` in benchmark tables when a specific model was used.

## 4. Data separation

### Teaching/development set

`workshop/data/gold_reference_v0.1.jsonl` is a **development/teaching reference**. It has already influenced rules, examples, notebook design and validation utilities. It must therefore **not be reported as an unbiased final benchmark**.

### Frozen synthetic holdout

`benchmarks/holdout_v1.jsonl` is the frozen synthetic SH2026 holdout. Its deterministic generation and SHA-256 are documented in `benchmarks/README.md` and enforced by CI.

The set was frozen before the remaining LLM comparison conditions. Do not inspect formal holdout errors and tune the tested system while continuing to describe the same set as held out.

### Source-derived external validation

Historical/source-derived validation is reported separately from synthetic stress testing. The current CLDW external-validation layer is source-pinned and checksum-verified.

Synthetic benchmark behaviour must not be presented as evidence about the distribution or difficulty of CLDW, Holocaust survivor testimony or another historical corpus.

### Future journey-development data

A discriminative transformer journey/event extractor requires a **separate development/training corpus**. The frozen SH2026 holdout must not be used as training data.

Controlled-access Holocaust testimony transcripts must **not** be copied into the public benchmark. Permitted aggregate results or separately cleared examples remain governed separately.

## 5. Annotation and adjudication

Each reference example follows `docs/GOLD_ANNOTATION_GUIDE.md`.

Minimum process:

1. primary human annotation;
2. second-pass review against the written policy;
3. record unresolved scholarly disagreement rather than forcing consensus;
4. validate offsets/schema automatically;
5. freeze the adjudicated record before formal system runs.

The term **reference annotation** is preferred to language implying interpretation-free ground truth.

## 6. Metrics

### 6.1 Spatial NER / span tasks

For apples-to-apples named-place recognition, compare methods under the same harmonised `TOPONYM` task and report:

- exact-span precision, recall and F1;
- overlap-span scores as a secondary boundary analysis where useful;
- per-label/support counts;
- unsupported or ungrounded span rate where applicable;
- representative error cases.

A separate full-spatial-schema LLM condition may use the wider SH2026 ontology. Results from that condition answer a **representational reach** question and must not be presented as directly comparable accuracy to TOPONYM-only NER without label-aligned scoring.

### 6.2 Representational reach

Before model inference, calculate the proportion of the broader reference ontology the method's output schema could represent.

This is an **ontology ceiling**, not empirical recall.

For example, a named-entity recogniser may achieve high TOPONYM F1 while having no output category for distance, movement, deictic reference or sense-of-place description.

### 6.3 Entity resolution

Report where relevant:

- resolved rate;
- ambiguous rate;
- unresolved rate;
- candidate-list availability;
- anachronistic/unsafe-normalisation errors found during human review.

Do not score a resolver as correct merely because it returned coordinates.

### 6.4 Structured journeys

Journey evaluation uses the frozen journey-matching and field policies already implemented in the project.

Report:

- journey detection precision/recall/F1;
- field-level precision/recall/completeness;
- evidence-grounded rate;
- unsupported evidence/field rate;
- contextual-inference rate;
- requires-review rate;
- schema/parse failure rate;
- missing-field rate;
- latency/token telemetry;
- estimated cost where a dated and reproducible calculation is available.

Where both reference and prediction leave a field missing, that null agreement must not artificially inflate field precision/recall.

### 6.5 Affect

Keep **sentiment** and **emotion** distinct where the available references/models permit.

Report as appropriate:

- sentiment accuracy and/or macro F1;
- emotion micro/macro/multi-label F1;
- human-reference agreement;
- label-inventory mapping/harmonisation;
- evidence-grounded rate for evidence-returning systems;
- unsupported interpretation rate;
- explicit/contextual-inference rate;
- review/correction burden;
- latency, tokens and cost.

A model-labelled emotion is an interpretation of textual evidence, not a direct measurement of a historical person's psychological state.

### 6.6 Human work

Distinguish:

- **review burden:** proportion of suggestions inspected;
- **correction burden:** proportion edited or rejected;
- number of edit events;
- fields/labels most frequently corrected;
- optional review time if measured under a consistent protocol.

Accepting a model suggestion still consumes review effort but is not a correction.

## 7. Evidence grounding for generative methods

For LLM span, journey and affect conditions, the model may propose verbatim evidence text, but **software computes and validates source offsets**.

Core principle:

> **LLM proposes -> software grounds -> human reviews.**

If returned evidence cannot be found in the source text, record it as unsupported/ungrounded rather than silently repairing it.

## 8. Telemetry and cost

For every empirical run preserve, where available:

- task;
- backend;
- provider;
- exact model identifier;
- latency;
- input/output token counts or clearly labelled estimates;
- success/error;
- estimated monetary cost;
- timestamp;
- package/Git commit;
- prompt/schema version and hashes for generative models;
- benchmark/source hash.

If price data are incomplete or model billing cannot be reconstructed, leave cost `null`. Do not coerce missing cost to zero.

## 9. Repetition and non-determinism

Deterministic rules should normally be run once per frozen environment.

For stochastic/generative APIs, the formal condition must record:

- exact model/provider;
- reasoning/decoding/sampling settings where exposed;
- number of repeated runs;
- whether results are scored per-run or under a predefined aggregation/adjudication rule.

If only one API run is feasible for the conference sprint, state that limitation explicitly and do not generalise stability claims beyond the observed run.

## 10. Benchmark output

Write tidy per-example rows compatible with `docs/COMMON_SCHEMA.md` and the benchmark utilities.

Core cross-task columns should include where meaningful:

```text
example_id
method
backend
model
task
precision
recall
f1
representational_reach
unsupported_rate
ambiguous_rate
review_required
human_edits_required
latency_ms
cost_usd_est
notes
```

Task-specific audit fields are expected. Missing/not-applicable measures remain `null`, not zero.

## 11. Planned keynote figures

Only generate final figures from frozen, provenance-preserved outputs.

Priority figures:

1. **Method × task matrix** — NER, journeys and affect across rules, transformers and LLMs.
2. **Accuracy vs representational reach** — distinguish bounded-task performance from breadth.
3. **Task complexity vs method capability** — recognition -> event reconstruction -> interpretation.
4. **Capability vs audit burden** — grounding, inference, review and correction alongside richer representation.
5. **Latency/cost vs task richness** — only with measured values.
6. **Error taxonomy** — transparent rule failure, ontology ceiling, historical/ambiguity failure, unsupported generative inference and affect over-interpretation.

Avoid a single overall winner score.

## 12. Release gates for benchmark claims

A result may be labelled **SH2026 benchmark result** only when:

- [x] synthetic holdout examples are frozen;
- [x] synthetic holdout annotation validation passes;
- [x] CLDW source-derived validation provenance/checksums are fixed;
- [ ] each remaining method configuration is recorded before its formal run;
- [ ] LLM prompt/schema/configuration is frozen before inspecting formal outputs;
- [ ] run manifest is stored;
- [ ] output evidence/offset validation passes where applicable;
- [ ] results were not manually altered outside the recorded review mechanism;
- [ ] missing metrics remain null;
- [ ] figures can be regenerated from committed tidy result data;
- [ ] synthetic and historical/source-derived results remain distinguishable;
- [ ] affect claims use an explicitly documented reference/label policy;
- [ ] any trained transformer journey condition uses development data separate from the frozen holdout.

Until a condition satisfies its gates, its output remains a **teaching/development demonstration**, not a final empirical claim.
