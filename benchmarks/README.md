# SH2026 benchmarks

This directory contains the reproducible evaluation datasets and result snapshot
used for Spatial Humanities 2026. Development material, held-out evaluation and
source-derived validation are kept separate because they support different
claims.

## Dataset inventory

| Resource | Purpose | Status |
|---|---|---|
| `holdout_v1` | Controlled evaluation of spatial spans and journeys on 30 instructor-authored synthetic passages | Frozen held-out benchmark |
| `affect_dev_v1` and `affect_holdout_v1` | Development and evaluation material for affect extraction | Deterministically generated; keep the two splits separate |
| `journey_dev_v1` | Development material for journey extraction | Development only; not benchmark evidence |
| `cldw_external_v1` | TOPONYM validation on 10 historical CLDW passages containing 43 gold mentions | Frozen source-derived external validation |
| `results_snapshot_v1.json` | Conference-safe results with synthetic and source-derived datasets identified separately | Includes reportable rows only |

The teaching reference at `workshop/data/gold_reference_v0.1.jsonl` has already
influenced notebook design, rules, examples and prompts. It is a visible
development set and must not be presented as held-out benchmark evidence.

## Synthetic holdout v1

Generate the benchmark from its frozen specification:

```bash
python benchmarks/build_holdout_v1.py
(cd benchmarks && sha256sum -c holdout_v1.sha256)
```

The current standalone-repository serialization has SHA-256:

```text
fcd985d1727bb924d1b01a91166a1f792f7e15cf2ebf6f126d85eff1ac195453
```

CI reconstructs the dataset and enforces this checksum. The benchmark contains
30 synthetic passages, 145 reference spans and 18 structured journeys. Twelve
journeys contain at least one contextual-inference field.

The original formal result documents cite the pre-migration serialization
checksum `be9c526af68230f22cb92507af69d8aacea8cbb5bd7ad5dfcf3d7c16767fdb9b`.
The checksum changed when project-specific schema identifiers were migrated to
the `spatio-textual-*` namespace during repository separation. The underlying
passages did not change. See
[`docs/BENCHMARK_PROVENANCE.md`](../docs/BENCHMARK_PROVENANCE.md) before
comparing or regenerating results across the two serializations.

## Other deterministic datasets

```bash
# Affect development and holdout splits
python benchmarks/build_affect_v1.py

# Synthetic journey-development set
python benchmarks/build_journey_dev_v1.py
```

The CLDW external set is reconstructed from the upstream corpus and the frozen
source manifest:

```bash
python benchmarks/build_cldw_external_v1.py --help
```

Its manifest pins the upstream commit, source files, extraction rule, licence
and derived checksum. It evaluates TOPONYM recognition only; it does not
validate journeys, affect or the full synthetic annotation ontology.

## Results and reportability

The consolidated reportable rows are in `results_snapshot_v1.json`. Detailed
methods and provenance are linked from each row's `source_document` field.

Synthetic and CLDW results must remain separately labelled. The formal LLM
journey run is omitted from the reportable rows because it ended with an HTTP
503 before producing a complete scored artefact. Absence of that row is not a
zero score.

## Claim boundaries

- Use the synthetic holdout for controlled, reproducible method comparison.
- Use the CLDW set only as a limited historical-language external check.
- Do not generalise either dataset directly to Holocaust survivor testimony or
  another historical corpus.
- Do not tune prompts, rules or resources on a held-out set while continuing to
  call it held out.
- Any content change requires a new dataset version and checksum.

The annotation policy is in
[`docs/GOLD_ANNOTATION_GUIDE.md`](../docs/GOLD_ANNOTATION_GUIDE.md), the
evaluation policy in
[`docs/BENCHMARK_PROTOCOL.md`](../docs/BENCHMARK_PROTOCOL.md), and the external
validation design in
[`docs/EXTERNAL_VALIDATION_PROTOCOL.md`](../docs/EXTERNAL_VALIDATION_PROTOCOL.md).
