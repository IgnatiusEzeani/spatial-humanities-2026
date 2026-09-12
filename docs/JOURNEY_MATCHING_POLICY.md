# SH2026 Journey Matching and Field Evaluation Policy

Status: **frozen before formal LLM journey runs**

Purpose: define how structured journey proposals are matched to human reference journeys without pretending that one exact serialized JSON object is the only valid representation of a narrative movement.

## 1. Unit of evaluation

The evaluation unit is a **journey hypothesis grounded in source evidence**, not a place entity and not an unconstrained generated answer.

A reference journey may contain:

- `start_location`
- `end_location`
- `transport_mode`
- `date`
- `journey_reason`
- an evidence quotation and source offsets
- per-field `explicit_or_inferred` status

Missing fields are legitimate reference outcomes. A system is not rewarded for filling them.

## 2. Why exact JSON equality is unsuitable

Two valid journey records may use different evidence-span boundaries while referring to the same movement. Conversely, two records can mention the same destination but describe different movements in a passage. Matching therefore combines endpoint agreement with overlap in source evidence.

The policy deliberately avoids geocoding or modern-place normalization during matching. Historical/source strings remain the comparison surface.

## 3. Normalization

For matching only:

- strings are Unicode-preserved, whitespace-collapsed and case-folded;
- location strings are **not** replaced by gazetteer canonical names;
- transport uses a small transparent alias map (`walking`/`on foot` -> `foot`, `plane`/`flight` -> `air`, etc.);
- date and reason values receive only whitespace/case normalization.

This is lexical normalization, not semantic adjudication.

## 4. Evidence overlap

When both reference and prediction expose integer evidence offsets, calculate character-span intersection over union (IoU).

A candidate receives evidence support when:

`evidence_iou >= 0.50`

An exact evidence quotation is not required because a model may legitimately return a smaller supporting substring than the human reference. The runtime extractor must still independently verify that its own evidence quotation is an exact substring of the source.

## 5. Candidate journey match

A predicted journey is eligible to match a reference journey when **either**:

1. every non-missing reference endpoint (`start_location`, `end_location`) matches the corresponding predicted endpoint; or
2. evidence IoU is at least 0.50 **and** at least one non-missing reference endpoint matches.

At least one reference endpoint must be non-missing for endpoint-based matching. This benchmark does not currently contain endpoint-free reference journeys.

This policy lets a partially incorrect proposal match the correct reference record so that the incorrect field is measured as a field error rather than automatically becoming one false positive plus one false negative.

## 6. One-to-one adjudication

All eligible prediction/reference pairs receive a deterministic candidate score based on:

- number of matching non-missing endpoints;
- evidence IoU;
- exact evidence-quote equality as a small tie-breaker.

Pairs are sorted by descending score and greedily accepted one-to-one. Remaining predictions are false positives; remaining references are false negatives.

The matcher returns the selected indices and scores so every pairing can be inspected.

## 7. Journey-level metrics

Report:

- matched journeys (`TP`)
- unmatched predicted journeys (`FP`)
- unmatched reference journeys (`FN`)
- journey precision
- journey recall
- journey F1

These are record-level metrics under this explicit matching policy. They must be reported with the policy version.

## 8. Field-level metrics

For matched journeys, evaluate the five structured fields separately.

For each field, count:

- `correct`: reference and prediction contain the same normalized non-missing value;
- `missing_prediction`: reference has a value but prediction is missing;
- `unsupported_prediction`: prediction has a value but reference is missing;
- `mismatch`: both have non-missing values but they differ;
- `both_missing`: both are missing.

Also report:

- field precision = correct / predicted non-missing values;
- field recall = correct / reference non-missing values;
- unsupported-field rate = (unsupported_prediction + mismatch) / predicted non-missing values.

`both_missing` is recorded but does not inflate precision or recall.

## 9. Evidence and inference metrics remain separate

Journey matching does not replace the existing audit metrics. Continue to report independently:

- evidence-grounded rate;
- unsupported evidence rate;
- contextual-inference rate;
- field contextual-inference rate;
- requires-review rate;
- schema/parse failures;
- latency/tokens/cost where available;
- human review and correction burden.

A journey can match the reference and still require review because one field was inferred from context.

## 10. Human-review rule

Do not manually repair raw LLM output before automatic scoring. If human correction is part of an evaluated workflow, retain both states:

1. raw machine proposal;
2. reviewed/edited record with append-only edit events.

Score them as separate workflow conditions if both are reported.

## 11. Versioning

This is **SH2026 journey matching policy v1**. Any material change to eligibility, evidence threshold, normalization, field scoring or one-to-one selection requires a new policy version and new result set.

The policy is intentionally conservative and inspectable. It does not claim to solve general event coreference or semantic equivalence.
