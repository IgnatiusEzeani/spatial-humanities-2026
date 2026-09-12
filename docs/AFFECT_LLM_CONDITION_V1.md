# SH2026 LLM Affect Condition v1

## Research question

How does a constrained generative LLM compare with the transparent lexical baseline and the pinned off-the-shelf transformer condition when sentiment and emotion are evaluated against the same public-safe affect references?

The LLM condition is designed to test contextual interpretive reach while preserving evidence, provenance and review signals. It does not treat generated labels as measurements of a person's inner psychological state.

## Frozen formal condition

- Provider: OpenAI
- API: Responses API
- Requested model: `gpt-5.6-sol`
- Reasoning effort: `medium`
- Maximum output tokens: `2048`
- Temperature: not set; API/model default
- Storage: `store=False`
- Output contract: strict JSON Schema
- Repetitions: one completed prediction per reference record
- Prompt policy: `spatio_textual.affect_llm.build_affect_prompt`
- Formal affect holdout SHA-256: `7f5007218934855e1c5e6cd941c8099ca855d70a85819e569837e8da6b85cd4d`
- Sentiment labels: positive, negative, neutral, mixed
- Emotion labels: fear, sadness, anger, joy, anxiety, despair, gratitude, surprise

The same GPT-5.6 Sol / medium-reasoning family used for the formal LLM journey condition is retained here so task complexity changes while the principal LLM condition remains comparable.

## Structured response

Every response must return:

- `sentiment`
- `emotion_labels`
- `evidence_quote`
- `explicit_or_inferred`
- `confidence`
- `notes`

The emotion label field is multi-label. An empty list is valid. `evidence_quote` may be null only when the classification is neutral with no assigned emotion.

## Evidence policy

The model returns a verbatim quotation rather than source offsets. Local software locates the quotation in the source text and computes half-open character offsets. Unmatched or multiply occurring quotations are not silently accepted as grounded evidence.

Contextual inference is retained as a result but automatically requires review. This deliberately separates the model's capacity to interpret implicit affect from the scholarly decision to accept that interpretation.

## Prompt constraints

The frozen prompt explicitly instructs the model to:

- keep sentiment and emotion conceptually separate;
- respect negation, questions, quotations and metalinguistic mentions;
- avoid assigning emotion solely from historical/domain terms such as `camp`, `ghetto`, place names or journey vocabulary;
- distinguish explicit from contextual inference;
- avoid inventing motives, events or feelings;
- treat confidence as confidence in the textual classification, not historical truth.

## Provider reliability

Transient provider failures may be retried at 5, 10, 20 and 40 seconds with the source text, prompt, schema, model and reasoning configuration unchanged. Provider-attempt counts and failure messages are preserved. Non-transient errors abort the run.

## Metrics

Formal scoring uses cached prediction records so evaluation never causes a second API call. The principal metrics are:

- sentiment macro F1 and per-label precision/recall/F1;
- emotion multi-label micro and macro F1;
- emotion exact-set accuracy;
- evidence-grounding rate;
- contextual-inference rate;
- review-required rate;
- latency;
- actual input/output/reasoning-token usage when reported;
- estimated API cost.

## Claim boundary

The formal v1 score is a controlled result on 48 instructor-authored public-safe synthetic passages. It can be compared with the frozen rule and transformer conditions on exactly those references. It does not establish performance on CLDW, Holocaust survivor testimony or any other archival collection.

Where later controlled testimony is evaluated, only aggregate/public-safe results should enter the public keynote materials unless the underlying text has been explicitly cleared for release.
