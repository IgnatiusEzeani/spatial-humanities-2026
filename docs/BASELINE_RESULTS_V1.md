# SH2026 Baseline Results v1

Status: **measured on frozen synthetic holdout; suitable for internal/keynote development with the claim boundaries below**

Benchmark: `benchmarks/holdout_v1.jsonl`

Holdout SHA-256: `be9c526af68230f22cb92507af69d8aacea8cbb5bd7ad5dfcf3d7c16767fdb9b`

Successful benchmark workflow run: `34299197632`

Workflow artifact: `sh2026-benchmark-v1-34299197632` (artifact ID `10084286373`)

Run produced **90 per-example comparison rows**: 30 examples × 3 baseline conditions.

## 1. Measured baseline summary

| Method | Accuracy task | Micro P | Micro R | Micro F1 | Macro F1 | Representational coverage* | Mean latency/example |
|---|---|---:|---:|---:|---:|---:|---:|
| Contextual spaCy NER | TOPONYM | 0.962 | 0.610 | 0.746 | 0.761 | 0.299 | 6.96 ms |
| spaCy + project resources | TOPONYM + GEONOUN | 0.969 | 0.456 | 0.620 | 0.578 | 0.471 | 6.97 ms |
| Deterministic rules/gazetteer | labels supported by the rule system | 0.841 | 0.268 | 0.407 | 0.366 | 0.959 | 0.38 ms |

\* `Representational coverage` is **not accuracy**. It is the fraction of all reference span phenomena whose label types the condition is designed to represent on each example, macro-averaged across the 30 examples.

Pooled exact-span counts:

| Method | TP | FP | FN |
|---|---:|---:|---:|
| Contextual spaCy NER | 25 | 1 | 16 |
| spaCy + project resources | 31 | 1 | 37 |
| Deterministic rules/gazetteer | 37 | 7 | 101 |

All three local conditions had estimated API cost `0.0`.

## 2. The comparison must not be read as a leaderboard

The three F1 scores have **different denominators/tasks**:

- contextual spaCy is evaluated only against reference `TOPONYM` spans;
- spaCy + project resources is evaluated against `TOPONYM + GEONOUN`;
- the rule system is evaluated against the larger set of span labels it explicitly claims to support.

Therefore statements such as “spaCy beats rules by 34 F1 points” are not defensible. The purpose of this experiment is to separate at least two axes that are often collapsed:

1. **accuracy within the method's declared task**;
2. **how much of the wider Spatial Humanities annotation space the method can represent at all**.

## 3. First empirical finding: accuracy and representational reach are orthogonal

The contextual NER condition is extremely precise on the named-place task (micro precision `0.962`) and achieves the strongest micro F1 (`0.746`) of these three conditions. Yet its mean representational coverage is only `0.299`, because a conventional named-entity inventory cannot encode most of the broader benchmark phenomena such as distance, direction, relational space, movement cues, transport, deictic reference, or sense-of-place descriptors.

The deterministic rule condition shows almost the inverse pattern. Its rule inventory is capable, in principle, of representing most of the benchmark's annotated span types (`0.959` representational coverage), but its pooled exact-span recall is only `0.268`. The problem is therefore not merely ontology: the system often lacks the lexical form, inflection, phrase pattern or place name required to fire the relevant rule.

This supports a central SH2026 distinction:

> **A system can have a broad schema but weak empirical coverage, or strong accuracy inside a narrow schema but limited representational reach.**

## 4. What the hybrid condition tells us

Adding the pre-existing project EntityRuler/resources to the same spaCy model expands mean representational coverage from `0.299` to `0.471`, because the condition now explicitly targets geo-nouns as well as named places.

Its micro precision remains very high (`0.969`), but micro recall over the harder `TOPONYM + GEONOUN` task is `0.456` and micro F1 is `0.620`.

This should **not** be interpreted as “adding rules makes spaCy worse”. The evaluated task has changed: the hybrid system is being asked to recover a wider class of spatial expressions. The result instead demonstrates the cost of expanding the ontology without a correspondingly complete resource inventory.

## 5. Runtime finding

On this small CPU benchmark, the deterministic rule condition averaged about `0.38 ms` per example versus about `6.96 ms` for both spaCy conditions, approximately an order of magnitude faster.

These timings are useful as **relative measurements for this run**, not universal performance claims. They depend on runner hardware, text length, package/model version, caching and instrumentation.

## 6. Error patterns already visible

The per-example results show several useful stress cases:

- the rule baseline reaches zero recall on some examples containing unseen place names and forms even though the relevant label types are inside its nominal schema;
- contextual NER misses complete named-place sets in several short route examples, while retaining very few false positives overall;
- the project-resource hybrid still misses many geo-nouns that are linguistically valid but absent from its frozen resource lists;
- examples dominated by relational, deictic or sense-of-place information expose the limitation of named-entity-centric evaluation even when a model finds every named place correctly.

We should retain these failures as teaching/keynote evidence rather than tuning the frozen v1 resources against them.

## 7. What this result does and does not establish

### Supported

- named-place NER can be highly precise while representing only a narrow portion of the wider spatial-information ontology;
- a deterministic system can declare support for many phenomena yet remain lexically brittle;
- combining contextual NER with project resources expands representational scope but does not eliminate resource-coverage problems;
- runtime/cost and representational reach are separate dimensions from task accuracy.

### Not supported by v1 alone

- that one methodological family is universally better than another;
- that these exact scores generalize to CLDW or another historical corpus;
- that they describe Holocaust survivor testimony performance;
- any conclusion about LLM journey quality, hallucination or cost;
- any claim about transformer NER beyond the tested spaCy small model;
- any archive-scale throughput claim.

All 30 v1 passages are instructor-authored synthetic stress cases. Historical/source-derived external validation remains a separate stage.

## 8. Next experimental conditions

Before the keynote figures are frozen, add:

1. a frozen transformer NER condition with exact model/version metadata;
2. evidence-first LLM journey extraction using the frozen journey matching policy;
3. LLM audit metrics: evidence grounding, unsupported fields, contextual inference, review requirement, latency/token/cost;
4. human accept/edit/reject evaluation on a defined subset to estimate correction burden;
5. a small source-derived external-validation set with verified public-domain/licensed citations.

The keynote figure should visualize **task accuracy, representational reach and audit burden as separate axes**, not collapse them into one score.
