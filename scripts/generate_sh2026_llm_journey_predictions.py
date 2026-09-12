from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from spatio_textual.gold import load_gold_jsonl
from spatio_textual.journey_llm import extract_audited_journeys, journey_response_schema
from spatio_textual.openai_responses import OpenAIResponsesJSONClient

# Pricing snapshot for GPT-5.6 Sol on 2026-09-11. Keep the token counts even if
# pricing changes so cost can always be recomputed from the preserved artefact.
INPUT_USD_PER_MTOK = 4.0
OUTPUT_USD_PER_MTOK = 20.0

# Infrastructure retry policy. This does not alter the frozen prompt, model,
# reasoning setting or schema. It only retries transient transport/provider
# failures that produced no usable model response.
TRANSIENT_RETRY_DELAYS_SECONDS = (5, 10, 20, 40)
TRANSIENT_ERROR_MARKERS = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "rate_limit",
    "rate limit",
    "service_unavailable",
    "server_is_overloaded",
    "overloaded",
    "timeout",
    "timed out",
    "connection error",
    "connection reset",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Generate frozen, evidence-first SH2026 OpenAI journey predictions."
    )
    p.add_argument("input", type=Path, help="Frozen SH2026 reference JSONL")
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/llm_journey_formal/inference"))
    p.add_argument("--model", required=True)
    p.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh", "max"],
        default="medium",
    )
    p.add_argument("--max-output-tokens", type=int, default=4096)
    p.add_argument("--base-url", default=None)
    p.add_argument("--benchmark-mode", action="store_true")
    p.add_argument("--frozen-at-commit", default=None)
    p.add_argument("--expected-sha256", default=None)
    p.add_argument("--max-examples", type=int, default=None, help="Development-only convenience")
    return p.parse_args()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def assert_benchmark_ready(args: argparse.Namespace, records: list[dict[str, Any]]) -> str:
    if not args.frozen_at_commit:
        raise SystemExit("--benchmark-mode requires --frozen-at-commit")
    if not args.expected_sha256:
        raise SystemExit("--benchmark-mode requires --expected-sha256")
    if args.max_examples is not None:
        raise SystemExit("--max-examples cannot be used in --benchmark-mode")
    if args.reasoning_effort != "medium":
        raise SystemExit("SH2026 LLM journey v1 formal runs require --reasoning-effort medium")
    if args.max_output_tokens != 4096:
        raise SystemExit("SH2026 LLM journey v1 formal runs require --max-output-tokens 4096")
    if args.model != "gpt-5.6-sol":
        raise SystemExit("SH2026 LLM journey v1 formal runs require --model gpt-5.6-sol")

    actual = sha256_path(args.input)
    if actual.lower() != args.expected_sha256.strip().lower():
        raise SystemExit(f"Benchmark checksum mismatch: expected {args.expected_sha256}, got {actual}")

    bad: list[str] = []
    for record in records:
        status = str(record.get("reference_status") or "").lower()
        distribution = str((record.get("source") or {}).get("distribution_status") or "").lower()
        if "provisional" in status or "pending" in distribution:
            bad.append(str(record.get("example_id")))
    if bad:
        raise SystemExit("Formal LLM journey benchmark refused provisional/pending records: " + ", ".join(bad))
    return actual


def actual_usage(telemetry: list[dict[str, Any]]) -> tuple[int | None, int | None, int | None]:
    input_values = [row.get("input_tokens") for row in telemetry]
    output_values = [row.get("output_tokens") for row in telemetry]
    reasoning_values = [row.get("reasoning_tokens") for row in telemetry]
    input_total = sum(int(v) for v in input_values if isinstance(v, int)) if all(isinstance(v, int) for v in input_values) else None
    output_total = sum(int(v) for v in output_values if isinstance(v, int)) if all(isinstance(v, int) for v in output_values) else None
    reasoning_total = (
        sum(int(v) for v in reasoning_values if isinstance(v, int))
        if reasoning_values and all(isinstance(v, int) for v in reasoning_values)
        else None
    )
    return input_total, output_total, reasoning_total


def _failure_messages(result: dict[str, Any]) -> list[str]:
    telemetry = [row for row in result.get("telemetry", []) if isinstance(row, dict)]
    return [str(row.get("error") or "") for row in telemetry if row.get("success") is False]


def _is_transient_failure(messages: list[str]) -> bool:
    if not messages:
        return False
    joined = " ".join(messages).lower()
    return any(marker in joined for marker in TRANSIENT_ERROR_MARKERS)


def _extract_with_transient_retry(
    client: OpenAIResponsesJSONClient,
    text: str,
    *,
    example_id: str,
) -> tuple[dict[str, Any], int, list[str]]:
    transient_failures: list[str] = []
    attempts = 0
    while True:
        attempts += 1
        result = extract_audited_journeys(client, text, file_id=example_id, seg_id=0)
        failures = _failure_messages(result)
        if not failures:
            return result, attempts, transient_failures
        if not _is_transient_failure(failures):
            raise SystemExit(f"Provider failure for {example_id}: " + "; ".join(failures))
        transient_failures.extend(failures)
        retry_index = attempts - 1
        if retry_index >= len(TRANSIENT_RETRY_DELAYS_SECONDS):
            raise SystemExit(
                f"Provider failure for {example_id} after {attempts} attempts: " + "; ".join(failures)
            )
        delay = TRANSIENT_RETRY_DELAYS_SECONDS[retry_index]
        print(
            f"Transient provider failure for {example_id} on attempt {attempts}; "
            f"retrying unchanged request in {delay}s."
        )
        time.sleep(delay)


def main() -> None:
    args = parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY must be supplied through the environment; CLI secrets are not accepted")
    if args.max_output_tokens < 1:
        raise SystemExit("--max-output-tokens must be >= 1")

    records = load_gold_jsonl(args.input)
    benchmark_sha256 = sha256_path(args.input)
    if args.benchmark_mode:
        benchmark_sha256 = assert_benchmark_ready(args, records)
    if args.max_examples is not None:
        if args.max_examples < 1:
            raise SystemExit("--max-examples must be >= 1")
        records = records[: args.max_examples]

    schema = journey_response_schema()
    schema_sha256 = sha256_text(json.dumps(schema, sort_keys=True, separators=(",", ":")))
    client = OpenAIResponsesJSONClient(
        model=args.model,
        response_schema=schema,
        schema_name="sh2026_journey_v1",
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.max_output_tokens,
        base_url=args.base_url,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = args.out_dir / "journey_predictions.jsonl"
    predictions: list[dict[str, Any]] = []
    all_telemetry: list[dict[str, Any]] = []
    resolved_models: set[str] = set()
    total_provider_attempts = 0
    transient_failure_count = 0

    for record in records:
        text = str(record["text"])
        example_id = str(record["example_id"])
        result, provider_attempts, transient_failures = _extract_with_transient_retry(
            client, text, example_id=example_id
        )
        total_provider_attempts += provider_attempts
        transient_failure_count += len(transient_failures)
        telemetry = [row for row in result.get("telemetry", []) if isinstance(row, dict)]
        all_telemetry.extend(telemetry)
        response_metadata = result.get("response_metadata") or {}
        resolved_model = str(response_metadata.get("resolved_model") or args.model)
        resolved_models.add(resolved_model)
        prompt = str(result.get("prompt") or "")
        predictions.append(
            {
                "schema_version": "sh2026-journey-prediction-v1",
                "example_id": example_id,
                "benchmark_sha256": benchmark_sha256,
                "source_sha256": sha256_text(text),
                "prompt_sha256": sha256_text(prompt),
                "prompt_policy": "spatio_textual.journeys.build_journey_prompt",
                "response_schema_sha256": schema_sha256,
                "provider": "openai",
                "model": resolved_model,
                "requested_model": args.model,
                "reasoning_effort": args.reasoning_effort,
                "max_output_tokens": args.max_output_tokens,
                "provider_attempts": provider_attempts,
                "transient_provider_failures": transient_failures,
                "journeys": result.get("journeys", []),
                "telemetry": telemetry,
                "raw_structured_response": result.get("raw_structured_response"),
                "raw_response_text": result.get("raw_response_text"),
                "response_metadata": response_metadata,
                "requires_review": result.get("requires_review"),
                "review_notes": result.get("review_notes", []),
            }
        )

    with prediction_path.open("w", encoding="utf-8") as fh:
        for row in predictions:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    input_tokens, output_tokens, reasoning_tokens = actual_usage(all_telemetry)
    cost_usd = None
    if input_tokens is not None and output_tokens is not None:
        cost_usd = round(
            input_tokens * INPUT_USD_PER_MTOK / 1_000_000
            + output_tokens * OUTPUT_USD_PER_MTOK / 1_000_000,
            6,
        )

    manifest = {
        "schema_version": "sh2026-llm-journey-inference-v1",
        "run_mode": "benchmark" if args.benchmark_mode else "development",
        "input": str(args.input),
        "benchmark_sha256": benchmark_sha256,
        "frozen_at_commit": args.frozen_at_commit,
        "examples": len(records),
        "provider": "openai",
        "api": "responses",
        "requested_model": args.model,
        "resolved_models": sorted(resolved_models),
        "reasoning_effort": args.reasoning_effort,
        "max_output_tokens": args.max_output_tokens,
        "temperature": "not_set_api_default",
        "structured_output": "strict_json_schema",
        "response_schema_sha256": schema_sha256,
        "prompt_policy": "spatio_textual.journeys.build_journey_prompt",
        "offset_policy": "model_returns_verbatim_evidence; software_computes_offsets",
        "repetitions": 1,
        "transient_retry_policy_seconds": list(TRANSIENT_RETRY_DELAYS_SECONDS),
        "total_provider_attempts": total_provider_attempts,
        "transient_provider_failure_count": transient_failure_count,
        "actual_input_tokens": input_tokens,
        "actual_output_tokens": output_tokens,
        "actual_reasoning_tokens": reasoning_tokens,
        "pricing_snapshot": {
            "date": "2026-09-11",
            "model": "gpt-5.6-sol",
            "input_usd_per_million_tokens": INPUT_USD_PER_MTOK,
            "output_usd_per_million_tokens": OUTPUT_USD_PER_MTOK,
        },
        "estimated_run_cost_usd": cost_usd,
        "model_version_note": (
            "The formal condition pins the public model ID gpt-5.6-sol. The resolved model string returned by the API is "
            "preserved per prediction because a dated snapshot identifier was not assumed."
        ),
        "claim_boundary": (
            "This is one completed observed run on the frozen synthetic SH2026 holdout. Transient provider failures may be retried "
            "with the unchanged request under the recorded infrastructure retry policy. The run measures the configured extraction "
            "condition; it does not establish stochastic stability or archival-domain validity."
        ),
    }
    (args.out_dir / "inference_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Wrote {len(predictions)} predictions to {prediction_path}")


if __name__ == "__main__":
    main()
