# SH2026 LLM Journey Experiment v1

## Research question

How does a constrained generative LLM compare with the frozen rule/dependency and discriminative transformer journey extractors when all three methods are evaluated against the same journey reference schema and matching policy?

This is a method comparison, not a claim that any model recovers historical truth. The LLM produces structured hypotheses about textual evidence; software grounds quotations and computes character offsets; the frozen scorer evaluates the resulting journey records.

## Frozen formal condition

The v1 formal LLM journey condition is fixed before holdout inference as follows:

- Provider: OpenAI
- API: Responses API
- Requested model: `gpt-5.6-sol`
- Reasoning effort: `medium`
- Maximum output tokens: `4096`
- Temperature: not set; API/model default
- Storage: `store=False`
- Output contract: strict JSON Schema
- Repetitions: 1 completed prediction per benchmark record
- Prompt policy: `spatio_textual.journeys.build_journey_prompt`
- Evidence policy: model returns a verbatim quotation; Python grounds the quotation and computes offsets
- Formal holdout SHA-256: `be9c526af68230f22cb92507af69d8aacea8cbb5bd7ad5dfcf3d7c16767fdb9b`
- Journey matching policy: `sh2026-journey-match-v1`
- Field scoring policy: `sh2026-journey-field-v1`
- Transient infrastructure retry delays: 5, 10, 20 and 40 seconds, with the request unchanged

The public OpenAI model identifier is pinned in the experiment manifest. A dated model snapshot is not invented or assumed. The actual model string returned by the API is preserved for every prediction so later readers can distinguish the requested alias from the provider-reported resolved model.

The retry policy does not change the model, prompt, reasoning effort, schema or source text. It is used only when the provider returns a transport/service failure and no usable structured response. The completed artefact records provider-attempt counts and transient failures.

## Response schema

Each response is one JSON object containing a `journeys` array. Each journey must contain:

- `start_location`
- `end_location`
- `transport_mode`
- `date`
- `journey_reason`
- `evidence_quote`
- `explicit_or_inferred` for every journey field, using only `explicit`, `contextual_inference`, or `missing`
- `confidence`
- `notes`

Nullable journey fields remain null when not supported by the source. The response schema itself is hashed and recorded in the inference manifest.

## Evidence and audit rules

The LLM is never trusted to supply offsets. For every proposed journey, local software searches for the returned evidence quotation in the source text and computes the offsets. Unsupported evidence, multiple evidence matches, contextual inference, invalid statuses, or other provenance problems route the record to review.

The inference artefact preserves the raw structured response, raw response text, response identifier, requested and resolved model names, actual token usage when supplied by the API, reasoning-token usage when supplied, latency, prompt hash, schema hash, source hash, benchmark hash, provider-attempt count and any transient provider-failure messages.

## Scoring

The formal run is scored from the cached prediction artefact rather than by making a second API call. This separates generation from evaluation and makes the reported metrics exactly reproducible from preserved predictions.

Primary metrics are journey precision, recall and F1 under the frozen one-to-one matching policy. Secondary metrics include per-field precision/recall, unsupported-field rate, evidence-grounded rate, contextual-inference rate, review-required rate, latency, token usage and estimated API cost.

## Cost snapshot

For reproducibility, the inference manifest records the GPT-5.6 Sol pricing visible in the OpenAI model documentation on 2026-09-11: USD 4 per million input tokens and USD 20 per million output tokens. Token counts are preserved so cost can be recomputed if pricing changes.

## Formal-run incident record

The first armed workflow attempt, run `34578230359`, retained the frozen condition but was aborted by a provider-side HTTP 503 overload response while processing `holdout_007`. No completed prediction artefact was produced or scored, and no model output from that aborted attempt was inspected for prompt/model tuning.

The subsequent infrastructure change adds bounded retries for transient provider failures. This is treated as an execution-reliability change, not a change to the experimental condition. The successful complete run, once available, is the run from which metrics will be reported.

## Claim boundaries

The completed formal evaluation is one observed prediction per record on 30 instructor-authored synthetic passages containing 18 reference journeys. It can support comparison of the configured rule, transformer and LLM conditions on this frozen benchmark. It does not establish stochastic stability, performance on CLDW, performance on Holocaust survivor testimony, or the truth of any inferred historical interpretation.

Any later controlled-domain testimony evaluation must be reported separately and in a form consistent with data governance and public-release constraints.

## Official API references used when freezing the condition

- OpenAI model catalogue: https://platform.openai.com/docs/models
- OpenAI Responses API reference: https://platform.openai.com/docs/api-reference/responses

The implementation deliberately does not set `temperature` for the reasoning-model condition and records `reasoning_effort`, `max_output_tokens`, strict JSON Schema, `store=False`, and provider-reported usage/provenance.
