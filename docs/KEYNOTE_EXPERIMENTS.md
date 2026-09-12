# SH2026 Keynote: Comparative Experiment Plan

Purpose: generate evidence for the keynote from the same code/data used in the workshop and demo.

## Central claim to test

The keynote should not assume that LLMs are simply superior. It should test a more useful claim:

> As computational methods move from explicit lexical matching toward richer contextual and generative representation, they can recover more implicit spatial meaning, but the burden shifts toward validation, provenance, uncertainty management and human correction.

## Experiment 1: Explicit place-name extraction

### Question

How much do we gain by moving from curated resources/rules to contextual NLP for a well-defined toponym task?

### Data

CLDW gold-standard place annotations or a small representative subset for live/tutorial use.

### Methods

- project resources/EntityRuler;
- spaCy small;
- spaCy transformer;
- HF NER model(s).

### Measures

- precision;
- recall;
- F1;
- latency;
- unresolved/ambiguous linking rate.

### Keynote visual

**Accuracy vs computational complexity** scatter/strip plot.

### Expected intellectual point

A bounded, well-curated domain can make rules surprisingly competitive. Contextual models are useful, but the comparison should expose what each method adds rather than assume a linear march of progress.

## Experiment 2: Beyond toponyms: qualitative spatial language

### Question

Which methods can recover spatial evidence that is not a named place?

### Example categories

- geo-nouns: `road`, `lake`, `hill`, `camp`, `ghetto`;
- relative location: `near`, `on the left`, `north of`, `at the foot of`;
- vague/relational references: `the camp`, `our home`, `the hills in the distance`;
- movement/distance expressions.

### Methods

- curated resources/rules;
- spaCy/HF entity models;
- schema-constrained LLM extraction.

### Measures

- coverage by category;
- precision on a small hand-labelled SH2026 set;
- unsupported extraction rate;
- human edits required.

### Keynote visual

A **capability matrix** with categories on rows and methods on columns.

### Keynote point

Traditional NER is often excellent at the task it was trained to do, but the research question may be wider than its label ontology.

## Experiment 3: `Picturesque` and `wild`

### Question

What changes when we move from lexical/co-occurrence approaches to latent/statistical and LLM interpretations of sense of place?

### Existing research basis

Lake District work already compares:

- direct geographical text analysis using co-occurrence with `picturesque` and `wild`;
- PCA over adjective co-occurrence;
- LLM scoring/association of places with the two concepts across historical periods.

### Re-analysis for keynote

Use a small matched set of passages/places and produce outputs from:

1. lexical span counts;
2. adjective/co-occurrence features;
3. LLM structured score with evidence excerpt.

### Measures

- interpretive granularity;
- transparency;
- consistency across repeated runs;
- evidence traceability;
- human judgement on plausibility.

### Keynote visual

Three panels titled:

**Count -> Pattern -> Interpretation**

The point is not that the third supersedes the first two, but that each changes the unit of analysis and therefore the kind of claim a scholar can make.

## Experiment 4: Textual nearness vs Euclidean distance

### Question

Can computational methods recover relational geography that does not reduce immediately to coordinates?

### Data

Lake District place-pair/nearness examples already used in project work.

### Methods

- pattern/rule extraction of nearness expressions;
- LLM pair/relation extraction with verbatim evidence;
- actual geodesic distance after entity linking.

### Measures

- relation extraction accuracy;
- evidence availability;
- frequency of textual-near / geographically-far mismatches.

### Keynote visual

A network/map showing relations such as `close to`, `at the foot of`, `in the vicinity of` and selected mismatches with actual distance.

### Keynote point

Spatial Humanities studies *experienced and narrated relations*, not only metric geometry. A mismatch is potentially interpretation, not necessarily extraction error.

## Experiment 5: Affect: rules vs HF vs LLM

### Question

What do richer models add to affective spatial analysis, and where do their assumptions become dangerous?

### Data

Use public/synthetic examples for live benchmarking and aggregate Holocaust research results as the substantive case study.

### Methods

- transparent lexicon/rule baseline;
- HF emotion/sentiment model;
- LLM structured classification.

### Measures

- agreement/disagreement;
- distribution entropy/uncertainty;
- stability across paraphrase/context changes;
- human plausibility judgement;
- latency/cost.

### Critical control

Explicitly demonstrate that lexical rules can encode circular domain assumptions. For example, a domain word such as `camp` should not by itself be treated as proof of a narrator's emotional state.

### Keynote visual

One passage, three distributions, plus a highlighted disagreement.

### Keynote point

Emotion labels should serve as navigational/interpretive scaffolds that return scholars to passages, not as direct measurements of an individual's psychology.

## Experiment 6: Evidence-first journey extraction

### Question

Where do LLMs provide a genuinely new capability over classic entity extraction?

### Task

Recover structured journey records:

- start location;
- end location;
- transport;
- date;
- reason;
- evidence;
- explicit vs inferred status.

### Methods

- manual reference;
- rule/NER cues as baseline;
- constrained LLM extraction.

### Measures

- journey record recall on a small manually checked set;
- field completeness;
- unsupported-field rate;
- evidence quote validity;
- evidence-offset validity;
- contextual-inference rate;
- human corrections per record.

### Existing research benchmark

The Holocaust journey research gives a substantive backdrop: 85,348 reconciled journey records across 892 testimonies, with evidence quotes and recoverable offsets for all retained records, alongside substantial missingness in dates/transport and some spatial endpoints.

### Keynote visual

One source passage -> one structured journey card -> one map edge -> `Review required` flag on an inferred field.

### Keynote point

The LLM's value is not fluency. It is its ability to assemble dispersed narrative cues into structured hypotheses. The scholarly requirement is that those hypotheses remain inspectable and contestable.

## Experiment 7: Human correction burden

### Question

Does higher automatic coverage actually save scholarly labour?

### Procedure

For a fixed sample, ask a reviewer to accept/edit/reject outputs from each method.

### Measures

- number of accepted outputs;
- edits;
- rejections;
- time-to-adjudicate;
- severe errors vs trivial corrections.

### Keynote visual

**Automation is not the same as labour saved** chart.

### Keynote point

A method with higher recall but expensive correction may be less useful than a narrower method with predictable errors.

## Experiment 8: Cost / latency / reproducibility

### Question

What do richer methods cost in practice?

### Inputs

Use package telemetry.

### Measures

- latency per 1,000 characters;
- local compute vs API dependency;
- estimated tokens/cost where available;
- deterministic repeatability;
- model/provider/version dependence.

### Keynote visual

A radar chart is tempting but difficult to read. Prefer a compact comparison table plus one 2D plot:

**interpretive reach vs audit burden**, with point size representing latency/cost.

## Experiment 9: Curatorial utility

### Question

Can AI create practical value without claiming interpretive authority?

### Institutional task

Simulate an oral-history intake scenario:

- identify likely geographical subjects;
- timeframe;
- actors;
- candidate themes;
- uncertainties;
- evidence pointers.

### Evaluation

Ask: does this reduce the time needed to locate relevant sections while leaving acquisition significance to curators?

### Keynote point

This is a strong counterexample to the idea that the only valuable AI output is a final answer. In archival work, **better navigation and prioritisation may be the safer and more useful objective**.

## Final synthesis figure

Build one reusable figure with methods on a continuum:

```text
Manual annotation
      |
Rules / gazetteers
      |
Statistical / transformer NLP
      |
LLM structured extraction
      |
Hybrid + human adjudication
```

Do not label the vertical axis `better`.

Instead annotate the changes:

- scale increases;
- contextual/implicit representation increases;
- flexibility increases;
- validation burden increases;
- opacity/provider dependence can increase;
- human judgement remains necessary.

## Proposed keynote evidence rule

Every strong empirical claim in the talk should be classed as one of:

- **Measured in SH2026 benchmark**;
- **Previously published/project result**;
- **Illustrative demo**;
- **Future research hypothesis**.

Use a small visual marker in speaker notes or slide footers during preparation. This prevents demo observations from silently becoming research claims.
