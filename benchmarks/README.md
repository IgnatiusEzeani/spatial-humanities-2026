# SH2026 Frozen Held-Out Benchmark v1

This directory contains the frozen **synthetic held-out benchmark** used to generate the first reproducible Spatial Humanities 2026 comparison results.

## Why a separate holdout exists

The teaching reference in `workshop/data/gold_reference_v0.1.jsonl` has already influenced notebook design, rules, examples and prompts. It is therefore a development set, not an unbiased benchmark.

`holdout_v1` was created only after the annotation policy and comparison protocol had been defined. It must not be used for subsequent prompt/rule tuning while continuing to be described as held out.

## Reproducible generation

The benchmark is generated deterministically from the frozen `holdout_spec_v1.py` specification:

```bash
python benchmarks/build_holdout_v1.py
```

Expected output:

```text
benchmarks/holdout_v1.jsonl
```

Expected SHA-256:

```text
fcd985d1727bb924d1b01a91166a1f792f7e15cf2ebf6f126d85eff1ac195453
```

The same checksum is stored in `holdout_v1.sha256` and enforced by CI.

## Composition

- 30 instructor-authored synthetic passages
- 145 reference spans
- 41 TOPONYM spans
- 27 GEONOUN spans
- 20 TIME spans
- 18 MOVEMENT_CUE spans
- 16 SPATIAL_RELATION spans
- 18 structured reference journeys
- 12 journeys containing at least one contextual-inference field

The set deliberately includes named-place recognition, geo-nouns, distance, direction, spatial relations, ambiguous/historical place-name cases, explicit journeys, context-dependent journeys, deictic references and sense-of-place descriptors.

## Scope of claims

This benchmark is useful for **controlled method comparison** and for generating reproducible conference figures. Because all v1 passages are synthetic, results from it must not be presented as direct evidence about the distribution or difficulty of CLDW, Holocaust survivor testimony, or another historical corpus.

Historical/source-derived external validation remains a separate release task. Public-domain or appropriately licensed passages must carry exact source citations before they are added to a future benchmark version.

## Freeze rule

Any content change to the benchmark requires a new version (`holdout_v2`, etc.) and a new checksum. Do not modify `holdout_v1` after formal model runs have begun.

The canonical annotation policy is `docs/GOLD_ANNOTATION_GUIDE.md`; the evaluation policy is `docs/BENCHMARK_PROTOCOL.md`.

The v1 records retain their recorded annotation-policy metadata for reproducibility; the live policy is maintained under `docs/`.
