# SH2026 teaching and reference data

This directory contains the public data used by the Spatial Humanities 2026
workshop and demonstrator. It deliberately separates teaching/development
references, workshop passages and cached system outputs from the frozen
benchmarks in [`benchmarks/`](../../benchmarks/README.md).

## File inventory

| File | Role | Evidence status |
|---|---|---|
| `examples.json` | Small historical and synthetic teaching examples | Development/teaching only |
| `gold_reference_v0.1.jsonl` | Instructor-adjudicated annotations for the teaching examples | Development reference, not held-out evidence |
| `gold_schema_v0.1.json` | Schema for the teaching reference | Validation support |
| `workshop_passages.json` | Six CLDW passages used in the three-hour workshop, including one negative passage | Human `<cdplace>` annotations retained for teaching and comparison |
| `panel_cache.json` | Cached outputs from the LD80 evaluation panel for the workshop passages | Precomputed model output, regenerated from committed panel artefacts |
| `teaching_gazetteer.csv` | Compact transparent gazetteer used in exercises | Teaching resource, not benchmark evidence |

The complete benchmark inventory, including the synthetic held-out sets and
CLDW external validation, is documented in
[`benchmarks/README.md`](../../benchmarks/README.md).

## Provenance and distribution

### CLDW material

The Penrith/Pooley Bridge example is verified against Corpus of Lake District
Writing record `1857_b`:

> Anon.-Nelson (pub.). *The English Lakes*. London: Thomas Nelson & Sons,
> 1859, p. 4.

The committed record identifies the upstream path
`LD80_transcribed/Anon1857_b.xml`, metadata row 66 and source commit
`9042811cf590f694f9b635c4bc656ed4f81ca422`. Its current status is
`public_domain_source_verified`; the corresponding gold annotation is an
`adjudicated_reference`.

The six workshop passages retain author, title, publication year, source file,
source offsets and gold `<cdplace>` spans. CLDW-derived material remains subject
to the upstream
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 licence](https://creativecommons.org/licenses/by-nc-sa/4.0/).
Cite the corpus and its source repository when reusing it.

### Synthetic examples

Records labelled `Instructor-created synthetic example` are safe to distribute
as teaching material. They must remain clearly labelled synthetic. In
particular, the oral-history-style example is not an authentic survivor
testimony and must never be presented as one.

### Controlled testimony

Do not add controlled-access Holocaust testimony transcripts to this directory.
Use only:

- material explicitly cleared for public redistribution;
- instructor-created synthetic examples; or
- aggregate or precomputed research outputs that do not reproduce controlled
  transcript text.

## Evidence boundaries

The teaching reference influenced notebook design, rules, examples and prompts.
It is therefore development material, not an unbiased benchmark.

For formal claims:

- use the frozen datasets described in
  [`benchmarks/README.md`](../../benchmarks/README.md);
- keep synthetic and source-derived evaluation results separately labelled;
- do not tune on held-out data while continuing to describe it as held out; and
- do not generalise the CLDW checks directly to Holocaust survivor testimony or
  another historical corpus.

The annotation policy is
[`docs/GOLD_ANNOTATION_GUIDE.md`](../../docs/GOLD_ANNOTATION_GUIDE.md), and
benchmark provenance is documented in
[`docs/BENCHMARK_PROVENANCE.md`](../../docs/BENCHMARK_PROVENANCE.md).

## Reproducibility

The panel cache is rebuilt from committed panel results without an API key:

```bash
python workshop/tools/make_workshop_cache.py \
  --panel panel/panel_panel_v1_openrouter.jsonl \
  --results panel/results_snapshot_v2.json \
  --passages workshop/data/workshop_passages.json \
  --out workshop/data/panel_cache.json
```

CI verifies that this command reproduces the committed cache byte-for-byte and
also validates source offsets, evidence quotations, identifiers and structured
journey fields.

Current teaching-reference schema: `spatio-textual-gold-0.1`. Any change to
labels, boundaries, relation semantics or journey-field interpretation requires
a version update and corresponding annotation-policy revision.
