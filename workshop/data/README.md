# SH2026 Teaching and Reference Data

This directory contains only material intended for the public Spatial Humanities 2026 teaching/demo workflow.

## Files

### `examples.json`

Small teaching examples used across notebooks and the demo.

Current categories:

- Lake District historical travel writing development example;
- synthetic oral-history Q/A journey;
- synthetic ambiguous place-resolution example;
- synthetic historical-polity example;
- synthetic relational/non-cartographic spatial example.

### `gold_reference_v0.1.jsonl`

Human reference annotations following `docs/GOLD_ANNOTATION_GUIDE.md`.

Each JSONL line contains:

- exact source text;
- source/distribution metadata;
- span annotations and offsets;
- relation annotations and evidence;
- structured journeys where warranted;
- explicit-vs-inferred field status;
- adjudication notes.

This is a **teaching/development reference**, not the final keynote holdout benchmark.

## Distribution and provenance rules

### Synthetic examples

Records whose source note says `Instructor-created synthetic example` are safe to distribute. They must remain clearly labelled synthetic in notebooks, demos and talks. In particular, the synthetic oral-history material must never be presented as an authentic survivor testimony.

### Lake District development example

The Penrith/Pooley Bridge passage is currently marked:

`public_domain_example_pending_exact_citation`

and the gold record is:

`provisional_until_source_citation_verified`

Before the final public release, verify and add the exact CLDW source/edition citation. Do not remove the provisional flag merely because the text is already used in development materials.

### Controlled Holocaust testimony text

Do **not** add controlled-access testimony transcripts to this directory.

Use only:

- cleared/publicly distributable excerpts with explicit permission;
- instructor-created synthetic examples;
- aggregate/precomputed research outputs that do not reproduce controlled text.

## Validation

The package provides lightweight validation/scoring helpers in:

`spatio_textual.gold`

The CI test `tests/test_gold_reference.py` verifies, among other things:

- source-offset integrity;
- evidence quotation integrity;
- unique IDs;
- explicit/inferred/missing journey status;
- review requirements for contextual inference;
- preservation of the historical `Czechoslovakia` source form;
- the distinction between textual recognition and ambiguous resolution;
- exact vs overlap span scoring behaviour.

## Benchmark-development rule

Do not repeatedly tune every rule/prompt/model against all reference examples and then describe performance on the same examples as an unbiased benchmark.

For the final keynote experiment, create a second independently annotated set and partition it into at least:

- a visible teaching/development set;
- a final held-out comparison set that is frozen before the last prompt/rule tuning.

## Versioning

Current reference schema: `spatio-textual-gold-0.1`

If annotation policy changes in a way that affects labels, boundaries, relation semantics or journey-field interpretation, update the version and document the change in `docs/GOLD_ANNOTATION_GUIDE.md`.
