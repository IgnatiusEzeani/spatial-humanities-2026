# SH2026 Instructor Guide

Workshop: **AI and NLP for Spatial Humanities: From Manual Annotation to LLM-Assisted Interpretation**

Companion keynote: **From Coordinates to Context: Rethinking Spatial Humanities in the Age of Large Language Models**

This guide is for the facilitator. It is intentionally more operational than `README.md`.

## 1. Teaching objective

The workshop should leave participants with a methodological framework, not merely familiarity with a Python package.

The central progression is:

`manual reading -> deterministic rules -> contextual NLP -> resolution -> affect/events -> evidence-first LLM extraction -> adjudication -> mapping -> responsible Spatial AI`

At every stage ask the same questions:

1. What can this method represent?
2. What does it miss?
3. What assumptions does it encode?
4. What evidence remains attached to the output?
5. What needs human review?
6. What would be lost if we exported only the clean final result?

Do not teach the sequence as an evolutionary story in which each later method supersedes the earlier one.

## 2. Room and participant requirements

The organisers have been told that the workshop requires:

- a room suitable for participants using their own laptops (or a computer room);
- reliable Wi-Fi;
- accessible power sockets;
- projection facilities.

The default workshop path is Google Colab/CPU-oriented. Participants should not require specialist local installations, GPUs or paid LLM accounts.

Recommended participant preparation email, 48–72 hours before the workshop:

- bring a laptop and charger;
- use a modern browser;
- have access to a Google account if they intend to use Colab;
- no API key is required;
- optional advanced participants may use their own provider credentials through documented secret handling, but this is not necessary for completing the workshop.

## 3. Instructor preparation checklist

### 72 hours before

- [ ] Open every notebook from a clean Colab session.
- [ ] Confirm the branch/release tag used by install cells.
- [ ] Record the exact Git commit used for the workshop.
- [ ] Verify all public teaching-source citations and licences.
- [ ] Confirm that no controlled-access testimony appears in the notebooks or outputs.
- [ ] Generate precomputed outputs for optional HF/LLM sections.
- [ ] Store a provenance manifest beside each precomputed output.
- [ ] Test the hosted demo from an incognito/private browser session.
- [ ] Prepare a local/offline copy of slides, notebooks and precomputed outputs.

### Morning of workshop

- [ ] Re-open the landing notebook in a fresh runtime.
- [ ] Test Wi-Fi and projector resolution.
- [ ] Open the hosted demo and a backup screenshot/PDF sequence.
- [ ] Verify the repository/Colab links and QR codes.
- [ ] Confirm no API key is visible in browser history, notebook output or shell history.
- [ ] Have the public-safe teaching text ready as a plain-text fallback.

## 4. Recommended teaching schedule

| Time | Notebook | Activity | Instructor priority |
|---|---|---|---|
| 09:30–10:00 | 00 | Setup + spatial framing | Establish location / locale / sense of place |
| 10:00–10:35 | 01 | Manual annotation | Get disagreement before showing a model |
| 10:35–11:20 | 02 | Rules/gazetteers | Make transparency and brittleness visible |
| 11:20–11:35 | — | Break | |
| 11:35–12:30 | 03 | Contextual NER | Separate accuracy from ontology ceiling |
| 12:30–13:10 | 04 | Linking/ambiguity | Treat coordinates as interpretive decisions |
| 13:10–14:00 | — | Lunch | |
| 14:00–14:50 | 05 | Affect/events | Audit domain assumptions and taxonomy limits |
| 14:50–15:50 | 06 | LLM structured extraction | Evidence grounding is the centrepiece |
| 15:50–16:05 | — | Break | |
| 16:05–16:50 | 07 | Compare/adjudicate | Measure human work explicitly |
| 16:50–17:25 | 08 | Text to map | Show mapped and *unmapped* evidence |
| 17:25–17:45 | 09 | Responsible Spatial AI | Finish with reusable audit questions |

Do not rush the manual annotation discussion to gain coding time later. It establishes the reference against which every automated method is interpreted.

## 5. Notebook-by-notebook facilitation notes

### 00 · Setup and orientation

**Must land:** Spatial Humanities is not equivalent to geoparsing. Named places are only one layer.

Use the distinction:

- **location** — where something can be geographically located;
- **locale** — the material/social setting associated with place;
- **sense of place** — experiential, affective and interpretive dimensions.

Avoid overpromising the package as a general GIS system.

### 01 · Manual annotation

Ask participants to annotate *before* revealing the instructor reference.

When disagreements appear, classify them:

- selection disagreement;
- span-boundary disagreement;
- ontology disagreement;
- contextual-inference disagreement.

Teaching line:

> Before a model can be wrong, researchers have already decided what counts as an answer.

The instructor reference is a documented judgement, not interpretation-free ground truth.

### 02 · Rules and gazetteers

Highlight a successful bounded case first. Then deliberately expose failure.

Useful examples include:

- spelling/inflection differences;
- written-number distance expressions;
- relational language outside the rule inventory;
- domain vocabulary.

Do not caricature rule systems as primitive. The scholarly point is that they can be extremely strong on carefully bounded tasks and remain unusually inspectable.

### 03 · Contextual NER

Keep two quantities separate on the board/slides:

**Within-ontology accuracy**

versus

**Representational reach**.

A model can achieve excellent TOPONYM F1 while having no representational category for distance, direction, movement, deictic space or sense of place.

Make clear whether project `EntityRuler` resources are enabled. The contextual-only condition must not be mislabeled if domain rules were added.

### 04 · Linking, ambiguity and historical geography

The key conceptual move is from:

`Cambridge = place mention`

to

`Which Cambridge?`

Then introduce the historical-polity case. Do not turn `unresolved` into a failure by default.

Teaching line:

> Sometimes unresolved is a more defensible computational result than confidently anachronistic.

### 05 · Affect and events

The `summer camp` stress example is deliberately chosen to expose domain-assumption leakage in a transparent lexicon.

Use careful language:

- “model-labelled affect”;
- “affective signal”;
- “the passage was classified as…”.

Avoid treating classifier outputs as direct psychological measurements.

For sensitive historical material, stay at the methodological/aggregate level in the public workshop.

### 06 · Evidence-first LLM structured extraction

This is the main afternoon technical argument.

Write on the board:

`LLM proposes -> software grounds -> human reviews`

Contrast with:

`LLM generates -> database accepts`

Make participants inspect the evidence quote and Python-computed offsets.

Emphasise that the model is not permitted to generate authoritative-looking offsets.

Then use the bad-evidence example. The central result is that **high confidence does not override failed provenance**.

Finally show the null-friendly example:

> Null is a scholarly result when the source is silent.

### 07 · Compare and adjudicate

Explain that majority voting is a routing heuristic, not a theory of truth.

Distinguish:

- **review burden** — how much machine output humans must inspect;
- **correction burden** — how much inspected output humans must edit or reject.

These become keynote metrics rather than invisible post-processing labour.

### 08 · From text to map

Show both the map and the route `audit` table.

Ask participants which of these they would force onto a point map:

- home;
- the village;
- beyond the river;
- to our left;
- a historical polity with no time-aware geometry.

The correct teaching outcome is not a universal answer; it is recognition that mapping involves representational choices.

### 09 · Responsible Spatial AI

Use this as synthesis, not a compliance lecture.

Return to the central keynote proposition:

> Increasing representational capability shifts the bottleneck from extraction toward validation, provenance, interpretation and governance.

Have participants choose three audit questions they will adopt in their own work.

## 6. Contingency modes

### Mode A — full network available

Run all default notebook paths. Demonstrate optional heavyweight/HF output if time permits. Run a live LLM call only if it adds pedagogical value and credentials are handled safely.

### Mode B — slow/unreliable network

- Use already-open Colab sessions where possible.
- Skip heavyweight model downloads.
- Use precomputed HF/LLM outputs.
- Continue all validation, adjudication and mapping exercises locally against those outputs.

The intellectual content should remain intact.

### Mode C — no external API access

No change to the core workshop. Notebook 06's deterministic teaching clients demonstrate the full evidence-validation machinery without an external provider.

### Mode D — Colab unavailable

Use a prebuilt local/Jupyter environment or instructor demonstration. Participant exercises can still use the annotation/reference tables and precomputed outputs.

### Mode E — hosted demo unavailable

Use screenshots/recorded interaction only. The workshop notebooks are the canonical teaching artifact; the demo is supplementary.

## 7. Five-minute contingency exercises

Use when a block finishes early or a model download stalls.

1. **Map or not?** Classify six spatial expressions as map directly / map with uncertainty / preserve as text / human review.
2. **Null or infer?** Given a journey sentence with no transport/date/reason, decide what should remain null.
3. **Ontology ceiling.** List spatial phenomena a standard NER inventory cannot encode.
4. **Evidence audit.** Compare a model claim with an evidence quote and decide whether the quote really supports each field.
5. **Rule repair.** Inspect one rule false positive and propose a fix, then discuss the new brittleness introduced.

## 8. Fifteen-minute contingency exercises

1. **Human adjudication mini-lab:** groups review the same three disputed outputs and compare reasons, not only final labels.
2. **Benchmark design:** ask groups to choose five metrics for comparing rules, NER and LLMs; then reveal the SH2026 multidimensional matrix.
3. **Historical map challenge:** discuss what a modern coordinate does and does not capture about a historical place name.

## 9. Precomputed output policy

Precomputed outputs are necessary for workshop reliability but must not become opaque screenshots.

Each precomputed result should include or be accompanied by:

- exact method/backend/model;
- generation date;
- Git commit;
- prompt/schema version where relevant;
- source example identifier;
- telemetry where available;
- whether the result came from synthetic or source-derived data;
- a run manifest with secrets redacted.

Do not manually tidy a model output and present it as raw/precomputed output. Human corrections belong in the recorded review layer.

## 10. Troubleshooting principles

### Installation/model unavailable

Prefer a clearly labelled fallback over silent substitution. A blank spaCy pipeline is acceptable for a tutorial fallback only when the output is explicitly identified as fallback behaviour; it is not acceptable as an empirical benchmark condition.

### API failure

Do not spend workshop time debugging provider accounts. Switch to precomputed output and continue the evidence-validation exercise.

### Geocoder returns an unexpected candidate

Treat this as a teaching opportunity. Inspect candidate metadata and ambiguity rather than silently forcing the expected answer.

### Notebook re-run produces state/path errors

Reset to a fresh runtime while noting the failure for the release audit. Before final release all notebook setup cells must be re-run-safe.

### Participant asks for a single “best” method

Return to the research question. The strongest method depends on the target phenomenon, acceptable audit burden, source restrictions, portability requirements and evidence standard.

## 11. Sensitive-data boundary

The public workshop must not expose controlled-access testimony transcripts. Use:

- synthetic structural examples;
- public-domain/appropriately licensed historical texts;
- aggregate research findings;
- cleared excerpts only where permission is explicit.

Do not invite participants to upload sensitive personal or controlled archival data to an external LLM provider during the workshop.

## 12. End-of-day success criteria

Participants should be able to explain, in their own words:

- why place recognition and place resolution are different;
- why NER accuracy and representational reach are different;
- why LLM evidence must be grounded against the source;
- why an unresolved/null value can be the correct scholarly output;
- why human review labour should be measured;
- why a map is an interpretation of spatial evidence rather than the end of analysis.

If those six ideas land, the workshop has succeeded even if an optional model call fails.
