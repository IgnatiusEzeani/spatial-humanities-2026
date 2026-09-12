# SH2026 source-derived external validation protocol

## Purpose

The primary SH2026 holdout is synthetic by design: it gives us controlled coverage of named places, geo-nouns, vague and relational space, historical geography, journeys, temporal context and contextual inference without distributing controlled testimony text.

A synthetic benchmark alone, however, cannot establish that a method generalises to historical writing. This protocol therefore defines a deliberately narrower **external validation check** using the public Corpus of Lake District Writing (CLDW).

The external check answers one question only:

> Do the named-place recognition findings from the synthetic benchmark remain plausible on independently sourced historical Lake District writing?

It is not a second development set and must not be used to tune the gazetteer, rule patterns, label mappings or model prompts before reporting the external result.

## Upstream source and provenance

The source is `UCREL/LakeDistrictCorpus` at commit:

`9042811cf590f694f9b635c4bc656ed4f81ca422`

The CLDW repository describes 80 manually digitised/annotated texts (more than 1.5 million tokens) and a 28-text hand-checked gold-standard subcorpus of approximately 242,000 tokens. Gold place names are marked with `<cdplace>`.

The upstream repository states a **CC BY-NC-SA 4.0** licence. Any distributed derivative excerpt must therefore preserve appropriate attribution/licensing. To minimise unnecessary redistribution, the preferred SH2026 workflow reconstructs the validation passages from the pinned upstream repository at run time and stores them as benchmark artefacts with provenance.

Dataset reference:

Rayson, P., Reinhold, A., Butler, J., Donaldson, C. E., Gregory, I. N., & Taylor, J. E. (2017). *A deeply annotated testbed for geographical text analysis: The Corpus of Lake District Writing*. GeoHumanities'17, ACM SIGSPATIAL.

## Source selection and derived-data freeze

The exact ten source files are recorded in:

`benchmarks/cldw_external_manifest_v1.json`

They provide a chronological spread within the already curated CLDW gold-standard subcorpus. This is a purposive source-derived validation sample, not a claim of random sampling or statistical representativeness of all historical writing.

The source-file list and deterministic passage-selection rule were frozen before running the SH2026 methods. Selection must not be changed because a method performs badly on a chosen text.

The first successful deterministic construction produced 10 passages containing **43 gold `<cdplace>` mentions** and the following SHA-256 checksum:

`257a463e8dd5b154edb7951c8b8bb6d05f609043db17adaa2324d7290b06836c`

That checksum is now a release invariant. CI must fail if reconstruction from the pinned CLDW source, fixed source list and fixed extraction rule produces different bytes. The checksum was recorded after deterministic construction; no source file or passage was replaced in response to model performance.

## Deterministic passage selection

For each fixed source file:

1. Read paragraphs in source order.
2. Select the first paragraph containing at least two gold `<cdplace>` annotations and between 80 and 1200 normalized plain-text characters.
3. If no paragraph meets that condition, select the first paragraph in the same length range containing at least one `<cdplace>` annotation.
4. Preserve the paragraph's normalized plain text and derive exact character offsets for every `<cdplace>` mention from the markup.
5. Record upstream repository, commit, path, blob SHA, passage ordinal and extraction-rule version.

The builder must fail loudly if a pinned file is absent, a source blob differs from the manifest, no eligible passage exists, or a derived gold span does not reproduce the exact source substring.

## Evaluation scope and primary matching policy

This external check is deliberately **TOPONYM recognition only**. It may compare:

- contextual spaCy NER;
- the same spaCy model plus frozen project resources;
- the revision-pinned Hugging Face NER condition;
- the deterministic/gazetteer condition only where its declared toponym support makes the comparison interpretable.

Precision, recall and F1 use the same CLDW `<cdplace>`-derived reference denominator for methods presented side by side as named-place recognition systems.

The **primary matching policy is exact character-span + harmonized `TOPONYM` label**. We keep this strict policy because it is objective and reproducible. It also means that a prediction such as `Oxford` does not count as an exact match for a CLDW gold span such as `Queen's College, Oxford`; such boundary conventions are part of what the audit must expose rather than silently relax after observing results.

The JSONL result artefact therefore preserves the full reference and predicted spans for each method/passage. Any later overlap or boundary-tolerant analysis must be reported as a **supplementary sensitivity analysis**, never substituted post hoc for the frozen exact-span primary result.

This check must **not** be used to claim external validation for geo-nouns, qualitative relations, affect, journey extraction or LLM interpretation. Those require different annotations and evidence.

## Separation from the synthetic holdout

The two evaluation layers serve different purposes:

- **Synthetic frozen holdout:** controlled representational breadth and auditability across the richer SH2026 ontology.
- **CLDW external validation:** source-derived historical-language check for named-place recognition.

Results must be reported separately before any combined interpretation. A strong result on one cannot erase limitations on the other.

## Anti-contamination rules

After the external passages are generated:

- do not add their missed names to the teaching gazetteer before the reported run;
- do not edit rule patterns in response to their errors;
- do not change label harmonisation because of their predictions;
- do not replace difficult passages;
- do not select only the best-performing source files;
- do not replace exact matching with a more favourable metric after inspecting results;
- preserve the exact generated dataset checksum, branch-head SHA, model revision and software environment with every result artefact.

Any later tuning creates a **post-validation development condition** and must be labelled as such.

## Reporting language

Appropriate:

> On a ten-passage source-derived CLDW check frozen before model execution, the named-place recognition pattern was ...

Avoid:

> The model is validated on historical texts.

The latter is too broad for this sample and task.

## Release gate

The external-validation result becomes keynote-ready only when all of the following are true: the builder is deterministic; upstream provenance and licence are included; generated gold offsets validate; the derived dataset matches SHA-256 `257a463e8dd5b154edb7951c8b8bb6d05f609043db17adaa2324d7290b06836c`; all compared NER conditions use the common TOPONYM denominator; exact-span matching is identified as the primary policy; full predicted/reference spans are retained for audit; environment/model revisions and the actual feature-branch head are recorded; and no post-hoc tuning has occurred.
