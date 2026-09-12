# SH2026 Spatial NER Results v1

Status: **frozen observed results for the Spatial NER row of the SH2026 comparative framework**

These results complete the first task row in `docs/EVALUATION_FRAMEWORK.md`: named-place recognition under a common TOPONYM ontology, followed by a separate broader spatial-span LLM condition.

The results below are artifact-backed. They supersede any earlier provisional numbers quoted during development.

## 1. Frozen data and model conditions

### Synthetic controlled holdout

- 30 passages
- 41 TOPONYM reference spans
- 145 reference spans across the full SH2026 span ontology
- SHA-256: `be9c526af68230f22cb92507af69d8aacea8cbb5bd7ad5dfcf3d7c16767fdb9b`

### Historical external validation

- 10 source-derived CLDW passages
- 43 TOPONYM reference spans
- upstream CLDW commit: `9042811cf590f694f9b635c4bc656ed4f81ca422`
- derived-data SHA-256: `257a463e8dd5b154edb7951c8b8bb6d05f609043db17adaa2324d7290b06836c`

### LLM condition

- provider: OpenAI
- model: `gpt-5.6-sol`
- API: Responses API
- structured output: strict JSON Schema
- reasoning effort: `none`
- offsets: computed locally from model-returned literal evidence, never accepted from the model
- repetitions: 1 observed run

A single generative run supports an observed-performance claim, not a stability claim.

## 2. Apples-to-apples TOPONYM recognition: synthetic holdout

All four methods are scored on exactly the same 41 TOPONYM reference mentions using exact character-span + label matching.

| Method | Micro precision | Micro recall | Micro F1 | Broader-ontology coverage ceiling | Mean latency / example |
|---|---:|---:|---:|---:|---:|
| Rules + frozen teaching gazetteer | 1.000 | 0.073 | 0.136 | 0.299 | 0.275 ms |
| spaCy `en_core_web_sm` | 0.962 | 0.610 | 0.746 | 0.299 | 7.878 ms |
| HF `dslim/bert-base-NER` pinned at `0b95561...` | 0.952 | 0.976 | 0.964 | 0.299 | 64.554 ms |
| OpenAI `gpt-5.6-sol` constrained TOPONYM | 0.976 | 1.000 | **0.988** | 0.299 | 2162.085 ms |

The rule baseline is deliberately not tuned against holdout errors. Its perfect precision but very low recall reflects the bounded pre-holdout gazetteer, not a claim about the ceiling of all symbolic NER systems.

The constrained LLM recovered all 41 reference TOPONYMs and produced one additional grounded prediction. That additional prediction was `Adriatic coast` in `holdout_007`; the reference policy annotated `Yugoslavia` as TOPONYM and `coast` as GEONOUN. The output is therefore scored as a false positive under the frozen TOPONYM ontology rather than being repaired after inspection.

### Interpretation

On this controlled named-place task, the pinned transformer already performs very strongly. The LLM improves micro F1 from 0.964 to 0.988, but at substantially greater latency. This is evidence against presenting LLMs as automatically necessary for bounded NER: the incremental accuracy gain is small relative to the computational difference in this observed run.

Crucially, all four TOPONYM-only systems have the same representational ceiling of approximately 0.299 against the broader SH2026 span inventory. Better named-place recognition does not by itself expand what kinds of spatial meaning the system can encode.

## 3. TOPONYM recognition: source-derived CLDW validation

The CLDW layer tests historical-language transfer under the existing source-derived place annotations. It is not validation of journeys, affect, or the full SH2026 ontology.

| Method | Micro precision | Micro recall | Micro F1 |
|---|---:|---:|---:|
| Rules + frozen gazetteer | 0.667 | 0.047 | 0.087 |
| spaCy `en_core_web_sm` | 0.556 | 0.233 | 0.328 |
| spaCy + project resources | 0.393 | 0.256 | 0.310 |
| HF `dslim/bert-base-NER` | 0.448 | 0.605 | 0.515 |
| OpenAI `gpt-5.6-sol` constrained TOPONYM | **0.829** | **0.791** | **0.810** |

The LLM result is markedly stronger on this ten-passage historical check. Boundary conventions remain part of the exact-span score rather than being silently relaxed. Because the CLDW sample is small and purposively selected, these values should be described as a source-derived external validation check, not a population-level estimate for the whole corpus.

## 4. Full SH2026 spatial-span LLM condition

A second, deliberately different experiment allowed the same LLM to use all eleven SH2026 span labels rather than TOPONYM alone.

Observed exact-span aggregate performance on the synthetic holdout:

- micro precision: **0.573**
- micro recall: **0.786**
- micro F1: **0.663**
- macro F1: **0.672**
- ontology coverage ceiling: **1.000**
- evidence-grounded rate: **1.000**
- unsupported prediction rate: **0.019**
- requires-review rate: **0.049**
- contextual-inference rate: **0.029**
- mean latency: **3809.573 ms/example**

Boundary-sensitive evaluation matters here. When label-preserving span overlap is used as the secondary measure and counts are pooled per example, micro overlap precision is 0.673, recall 0.924 and F1 0.779. This secondary score does not replace exact-span scoring; it shows that a substantial share of disagreement concerns span boundaries rather than the complete absence of the relevant phenomenon.

The largest exact-boundary difficulties occur in categories such as `SPATIAL_RELATION`, `DIRECTION`, `TRANSPORT_CUE`, `DEICTIC_REFERENCE`, and some temporal/movement expressions. Named places and geo-nouns remain much stronger. This is precisely why the broader condition must not be described simply as "LLM NER accuracy": it tests a richer annotation problem.

## 5. Main empirical reading

The NER row now supports three distinct observations:

1. **Within a fixed named-place ontology, newer architecture does not automatically imply a proportionate practical gain.** A pinned transformer nearly matches the constrained LLM on the controlled synthetic task.
2. **Historical transfer changes the picture.** On the small frozen CLDW check, the LLM is substantially stronger than the tested conventional models.
3. **Representational reach and recognition accuracy are different axes.** Expanding the LLM to the full spatial ontology increases the representational ceiling from 0.299 to 1.000, while exact-span F1 falls because the system is solving a materially richer and more boundary-sensitive task.

This supports the keynote claim that the progression from rules to transformers to LLMs should not be narrated as a single accuracy ladder. The more revealing comparison is **accuracy × representational reach × audit burden**.

## 6. Formal run provenance

### Constrained synthetic TOPONYM LLM

- workflow run: `34543618472`
- feature-branch commit: `2f2644d615c17839f4884741289a349ace861a5b`
- artifact ID: `10178234989`
- artifact SHA-256 digest: `1f3d4e4148aba8f3e9064cca44f24a0e27ecbc51cd53cebbf8a3434ee9853b6c`

### CLDW TOPONYM LLM

- workflow run: `34543842973`
- feature-branch commit: `741bfac2f0d7c036b9b599c56046f30568840dc3`
- artifact ID: `10178304419`
- artifact SHA-256 digest: `bd5a1a729fee8fe90abfa02f4221ccbf078fa582b264a3057f103ca57cd25140`

### Full-spatial synthetic LLM

- workflow run: `34543992524`
- feature-branch commit: `b224c929576108604b6e3dfa38b6314419a97d2e`
- artifact ID: `10178384697`
- artifact SHA-256 digest: `d4570a00899f3d0c8e8a34bf112f7b26a1e9cc005964cbe50fc2dd0b42555e2b`

### TOPONYM-only rule baseline

- workflow run: `34544322593`
- feature-branch commit: `1f0b4b5a539b99f75a7eb790b64c08729c0518ad`
- artifact ID: `10178455297`
- artifact SHA-256 digest: `c4d64dfd1599980485712efef4ea97b840884ec4c29e1ca35962e14685d72481`

Raw predictions, normalized grounded outputs, telemetry, manifests and evaluation rows are preserved in the corresponding workflow artifacts. The LLM artifacts contain no API key.
