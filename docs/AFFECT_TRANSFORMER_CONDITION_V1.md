# SH2026 Transformer Affect Condition v1

## Status

This document freezes the off-the-shelf transformer affect condition before formal holdout scoring. No transformer fine-tuning is performed on the SH2026 affect development or holdout corpora.

## Sentiment condition

- Model: `cardiffnlp/twitter-roberta-base-sentiment-latest`
- Revision: `3216a57f2a0d9c45a2e6c20157c20c49fb4bf9c7`
- Native labels: negative, neutral, positive
- SH2026 labels: positive, negative, neutral, mixed
- Mixed post-processing: return `mixed` only when positive and negative probabilities are both at least `0.25` and their absolute probability gap is at most `0.20`.

The model was trained/fine-tuned for English Twitter sentiment. This domain mismatch must be disclosed when interpreting performance on spatial-historical prose or synthetic historical-style passages.

## Emotion condition

- Model: `j-hartmann/emotion-english-distilroberta-base`
- Revision: `0e1cd914e3d46199ed785853e12b57304e04178b`
- Native labels: anger, disgust, fear, joy, neutral, sadness, surprise
- SH2026 v1 emotion labels: fear, sadness, anger, joy, anxiety, despair, gratitude, surprise

Directly representable SH2026 labels are:

`anger`, `fear`, `joy`, `sadness`, `surprise`

The following SH2026 labels are outside the frozen model's native ontology and are not silently remapped:

`anxiety`, `despair`, `gratitude`

`disgust` is a native model label but is outside the SH2026 v1 reference ontology. `neutral` is not treated as an emotion label in SH2026.

The model is a seven-class softmax classifier rather than a native multi-label system. For the SH2026 comparison, supported labels with probability at least `0.25` are emitted. If none reach that threshold, a single supported top label is emitted only when its score is at least `0.50` and exceeds the neutral score. Otherwise the prediction is an empty emotion-label set.

## Evidence limitation

These classifiers do not natively return source-grounded rationale spans. Their affect predictions therefore have `evidence_quote = null`, and evidence-grounding rate is marked not applicable rather than zero. This is a methodological limitation to report alongside classification metrics.

## Evaluation discipline

Formal evaluation uses the frozen SH2026 affect holdout and reports:

- sentiment macro F1 and per-label metrics;
- emotion multi-label micro/macro F1 and per-label metrics;
- exact-set accuracy;
- representational ceiling induced by the native emotion ontology;
- latency;
- evidence-grounding applicability.

The unsupported anxiety/despair/gratitude labels are counted in the full eight-label benchmark rather than removed. A supported-label sensitivity analysis may be reported separately, but it must not replace the full-schema result.

## Claim boundary

This condition tests what two established off-the-shelf transformer classifiers can represent under a frozen mapping. It does not measure a purpose-trained historical affect model, and the result must not be generalized to survivor testimony without separate controlled-domain validation.
