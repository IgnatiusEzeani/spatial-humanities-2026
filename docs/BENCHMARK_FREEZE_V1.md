# SH2026 Benchmark Freeze v1

Status: **frozen for formal baseline runs**

The first SH2026 held-out benchmark has now been frozen as a deterministic, distributable synthetic stress-test set. It is separate from the workshop/development examples that influenced implementation.

## Frozen object

Generator:

`benchmarks/build_holdout_v1.py`

Generated reference file:

`benchmarks/holdout_v1.jsonl`

Expected SHA-256:

`be9c526af68230f22cb92507af69d8aacea8cbb5bd7ad5dfcf3d7c16767fdb9b`

The checksum is enforced by `tests/test_sh2026_holdout.py` and by the dedicated `SH2026 benchmark smoke` GitHub Actions workflow. Formal benchmark mode also refuses to run without an expected checksum and a recorded Git commit.

## Composition

The v1 set contains 30 instructor-authored synthetic passages and 145 annotated spans. It includes 41 toponyms, 27 geo-nouns, 20 temporal cues, 18 movement cues, 16 spatial-relation spans, plus distance, direction, transport, deictic and sense-of-place phenomena. Eighteen examples contain a structured reference journey; twelve of those contain at least one contextual-inference field.

The examples were deliberately stratified to stress different methodological layers:

- explicit named-place recognition;
- geo-nouns and locale;
- distance, direction and relational language;
- ambiguity and historical/variant place naming;
- explicit journeys;
- context-dependent journeys and Q/A context;
- non-cartographic/deictic space;
- subjective and sensory place description.

## Independence rule

The existing `workshop/data/gold_reference_v0.1.jsonl` is a development/teaching set and has already influenced rules, prompts and notebook design. It is not part of the held-out benchmark.

From this freeze onward:

1. do not add holdout-specific gazetteer entries after inspecting benchmark errors;
2. do not alter rules or prompts in response to v1 errors and continue calling v1 held out;
3. any content correction requires a new benchmark version and checksum;
4. preserve all raw comparison rows and run metadata;
5. distinguish within-task accuracy from representational reach and audit burden.

The deterministic rule condition intentionally uses the pre-existing teaching/development gazetteer rather than a gazetteer expanded from holdout place names. Low unseen-toponym coverage is therefore meaningful evidence about portability, not a reason to retrofit the benchmark dictionary after seeing results.

## Claim boundary

All v1 passages are synthetic. This makes the benchmark safe to distribute and useful for controlled comparison, but it also imposes a strict interpretation limit:

**v1 results are evidence about the tested methods on controlled SH2026 stress cases, not direct evidence about CLDW, Holocaust survivor testimony, or the prevalence of phenomena in a historical archive.**

Historical/source-derived external validation should be added separately using public-domain or appropriately licensed passages with exact citations. Controlled-access testimony text must remain outside the public benchmark.

## First formal run

The first automated run is configured to compare:

- deterministic rule/gazetteer annotation, using the pre-holdout project/teaching resources;
- contextual spaCy `en_core_web_sm` NER without project EntityRuler augmentation.

The workflow generates the holdout, verifies the byte-level checksum, validates the reference schema, runs both baselines and uploads the per-example and aggregate results as auditable workflow artifacts.

Transformer and LLM conditions should be added only after their exact model identifiers, decoding settings, prompt/schema versions and evidence-validation rules are frozen.
