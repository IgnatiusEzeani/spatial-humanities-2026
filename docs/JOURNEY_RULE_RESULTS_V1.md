# SH2026 Rule/Dependency Journey Baseline v1

Status: **formal frozen-holdout result recorded; no post-hoc v1 tuning permitted**

This note records the first reportable non-LLM journey-extraction condition in the SH2026 method × task framework.

## Method

`rule_dependency_v1` combines:

- `en_core_web_sm` dependency parsing / NER;
- transparent movement-verb and locative-preposition rules;
- explicit transport and time patterns;
- bounded contextual origin inheritance;
- hard-negative guards for cancelled and negated travel;
- evidence-first character offsets;
- explicit / contextual-inference / missing field statuses.

It does not use an LLM, geocoder, hidden retrieval source or controlled testimony data.

The implementation was developed only against the separately frozen journey-development corpus (`journey_dev_v1`). The development corpus contains 180 synthetic passages and has SHA-256:

`a5b89a40d0d0f7be1b3994852fa041c262ee56535d9ef400e50558d00666421b`

The final development condition reached perfect fit on those deliberately constructed development cases. That value is **not** a scientific headline result; it shows only that the deterministic v1 rules cover the patterns for which that development set was designed.

## Formal benchmark

Formal data: frozen SH2026 30-passage holdout

SHA-256:

`be9c526af68230f22cb92507af69d8aacea8cbb5bd7ad5dfcf3d7c16767fdb9b`

Formal run:

- workflow: `SH2026 rule journey formal`
- run ID: `34549062408`
- branch commit: `ffbdb02a65d5d310f7eca2018c4537c6881eedde`
- artifact: `sh2026-journey-rules-formal-34549062408`
- artifact digest: `sha256:48a2f555a9af4520a9edd90f9e4a8f53d48ae13e0f860f9ea076b00578d8e213`
- journey matching: `sh2026-journey-match-v1`
- field scoring: `sh2026-journey-field-v1`

The formal trigger was consumed and then disarmed. Later duplicate/diagnostic runs must not replace this artifact as the v1 reportable condition.

## Formal result

### Journey detection

| Metric | Value |
|---|---:|
| Reference journeys | 18 |
| Predicted journeys | 18 |
| TP | 17 |
| FP | 1 |
| FN | 1 |
| Precision | 0.944 |
| Recall | 0.944 |
| F1 | **0.944** |

### Structured fields

| Field | Precision | Recall | Unsupported/wrong field rate |
|---|---:|---:|---:|
| Start location | 0.923 | 0.800 | 0.077 |
| End location | **1.000** | 0.941 | 0.000 |
| Transport mode | 0.900 | 0.818 | 0.100 |
| Date | **1.000** | 0.500 | 0.000 |
| Journey reason | 0.833 | 0.833 | 0.167 |
| **All nonmissing fields** | **0.941** | **0.787** | **0.059** |

`both_missing` cases are excluded from precision/recall denominators under the frozen field policy.

### Audit and computational characteristics

- evidence-grounded rate: **1.000**;
- journeys triggering review: **7 / 18 = 0.389**;
- journeys containing bounded contextual inference: **7 / 18 = 0.389**;
- mean local latency: **4.797 ms per passage** on the CI runner;
- API cost: **0**.

## Interpretation

The rule/dependency baseline is already highly competitive for **journey detection** on the controlled holdout: 17 of 18 reference journeys were matched while producing only one unmatched prediction. Its main weakness is not detecting that movement occurred, but reconstructing every structured attribute. In particular, date recall is 0.500, and start-location / transport reconstruction also leave information unfilled or mismatched.

This distinction is important for the keynote. A transparent deterministic system can be strong at recognising explicit movement structure while remaining deliberately conservative about fields that require broader context. High journey-detection F1 therefore does not imply complete narrative reconstruction.

The system also provides a useful audit baseline: all emitted journey evidence is directly grounded, inference is bounded and visible, latency is very low, and there is no API cost.

## Claim boundary

This is a 30-passage synthetic controlled benchmark, not evidence that the rule baseline will achieve the same performance on full survivor testimonies or other archival corpora. The value of this condition is comparative: it supplies a frozen, auditable non-LLM reference point against which the transformer event extractor and evidence-first LLM journey extractor can be evaluated under the same matching and field-scoring policies.

No v1 rule changes should now be made in response to the formal holdout errors. Any later rule refinement must be named as a new post-hoc condition and must not replace this result.
