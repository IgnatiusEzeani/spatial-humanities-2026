# SH2026 Journey Development Protocol

Status: **development corpus and rule-baseline design frozen before formal journey holdout scoring**

## Purpose

The formal SH2026 journey holdout already exists and must not become a tuning set. This protocol therefore introduces a separate, public-safe synthetic development corpus for building and debugging non-LLM journey extractors before they are scored on the frozen holdout.

The development corpus is not evidence about historical testimony or CLDW distributions. Its role is methodological: expose known structural cases, support implementation and prevent repeated tuning against the formal benchmark.

## Corpus v1

Builder: `benchmarks/build_journey_dev_v1.py`

Expected SHA-256:

`a5b89a40d0d0f7be1b3994852fa041c262ee56535d9ef400e50558d00666421b`

Composition:

- 180 synthetic passages;
- 120 positive passages and 60 hard negatives;
- 135 reference journeys;
- 15 passages in each positive structural pattern;
- 15 passages in each negative structural pattern.

Positive patterns:

- explicit two-endpoint train journeys;
- movement verbs with implied transport;
- destination-only arrival;
- origin-only departure;
- context-inherited origin;
- relocation with contextual reason;
- flight plus purpose;
- two journeys in one passage.

Hard negatives:

- static location descriptions;
- planned but cancelled travel;
- explicitly negated travel;
- passages that compare places without narrating movement.

## Separation from the formal benchmark

The existing frozen SH2026 holdout remains unchanged and must not be modified after observing development or model errors.

Rules for v1:

1. Implement and debug the rule/dependency extractor only against the journey-development corpus and ordinary unit tests.
2. Freeze the extractor implementation and its configuration before formal holdout scoring.
3. Run the frozen holdout once for the reportable rule-baseline result.
4. Do not change the v1 rule baseline in response to holdout errors while continuing to report the same condition.
5. Any post-hoc improvement must become a separately named/versioned condition.
6. Transformer journey training must use a development/training split derived from this corpus or another separately documented training source, never the frozen holdout.
7. LLM journey prompting is independently frozen before formal inference and is evaluated through the same journey matching and field-scoring policy.

## Common output schema

Every journey method should emit the same core fields where applicable:

- `start_location`
- `end_location`
- `transport_mode`
- `date`
- `journey_reason`
- `evidence_quote`
- software-derived evidence offsets
- per-field `explicit_or_inferred` status
- `requires_review`

Null/missing values are legitimate outputs. A method must not fabricate a field merely to make its structured record complete.

## Common evaluation

All formal journey methods use:

- journey matching policy `sh2026-journey-match-v1`;
- field scoring policy `sh2026-journey-field-v1`;
- pooled detection precision/recall/F1;
- per-field precision/recall and unsupported-field rate;
- evidence-grounding rate;
- contextual-inference rate;
- review burden;
- latency and cost/compute metadata where available.

The primary comparison is therefore not just one F1 number. It asks separately whether a system detects the journey, reconstructs the fields correctly, remains grounded in evidence, and creates additional audit burden.

## Method families

### Rule/dependency baseline

A transparent deterministic extractor using movement cues, syntactic/spatial patterns, local named-place recognition, explicit transport/time cues, bounded contextual inheritance and hard-negative guards.

### Transformer event baseline

A non-generative event extraction condition trained only on separately designated development/training data. The intended event roles are SOURCE, DESTINATION, TRANSPORT, TIME and REASON around a movement trigger.

### LLM structured extraction

Evidence-first structured generation using the frozen journey prompt/schema. The model proposes fields/evidence; software grounds evidence and the common evaluator scores the result.

## Claim boundary

A synthetic-development score measures how well a method fits the deliberately constructed development cases. It is **not** a headline scientific result. Only the frozen holdout result, plus any separately defined external validation, is reportable as the SH2026 journey comparison.
