# SH2026 Transformer Journey Results v1

## Status

This document records the first formal evaluation of the frozen non-generative transformer journey condition on the untouched SH2026 synthetic holdout.

The fine-tuned checkpoint was selected and frozen using the separate journey development corpus before formal holdout scoring. The immediately preceding workflow attempt failed at CLI argument parsing and did not execute model inference on the holdout. The scored run below is therefore the first model evaluation of the formal holdout for this frozen checkpoint.

## Frozen condition

- Formal workflow run: `34577285699`
- Evaluation commit: `e82c7e5480cc84e2e314a5a89c95df6aec574940`
- Formal holdout SHA-256: `be9c526af68230f22cb92507af69d8aacea8cbb5bd7ad5dfcf3d7c16767fdb9b`
- Development corpus SHA-256: `a5b89a40d0d0f7be1b3994852fa041c262ee56535d9ef400e50558d00666421b`
- Development workflow run: `34576524677`
- Base model: `distilbert/distilbert-base-cased`
- Base model revision: `6ea81172465e8b0ad3fddeed32b986cdcdcffcf0`
- Fine-tuned `model.safetensors` SHA-256: `6ebb3961b644fd471a695a1533f69ce4ebaa336acfd38e27bf78daed39b8e1e1`
- Training: 5 epochs, batch size 8, learning rate `5e-5`, seed 2026, max length 256
- Journey matching policy: `sh2026-journey-match-v1`
- Field scoring policy: `sh2026-journey-field-v1`

## Formal holdout result

The 30-example holdout contains 18 reference journeys. The frozen transformer predicted 17 journeys, of which 15 matched reference journeys under the frozen matching policy.

| Metric | Result |
|---|---:|
| True positives | 15 |
| False positives | 2 |
| False negatives | 3 |
| Journey precision | 0.882353 |
| Journey recall | 0.833333 |
| Journey F1 | **0.857143** |
| Evidence-grounded rate | **1.000000** |
| Review-required rate | 0.352941 |
| Contextual-inference rate | 0.352941 |
| Mean latency per passage | 34.1 ms |

## Field-level result

| Field | Precision | Recall |
|---|---:|---:|
| start_location | 1.000000 | 0.785714 |
| end_location | 1.000000 | 1.000000 |
| transport_mode | 0.888889 | 0.727273 |
| date | 0.875000 | 0.700000 |
| journey_reason | 1.000000 | 0.400000 |
| **Pooled non-missing fields** | **0.955556** | **0.781818** |

The pooled field counts were 43 correct, 10 missing predictions and 2 mismatches. The aggregate unsupported-field rate was 0.044444.

## Interpretation boundary

The result is a controlled synthetic-holdout measurement, not evidence of archival or testimony-domain performance. The perfect development score must not be reported as formal generalisation performance: on the untouched holdout the journey F1 fell to 0.857143. This difference is itself useful evidence that development-fit performance and held-out performance are not interchangeable.

The transformer remains fully evidence-grounded in this run, but it misses some journey events and especially some optional interpretive arguments such as journey reason. These observations should be compared with the rule and LLM conditions under the same frozen journey scorer rather than presented as a standalone leaderboard claim.
