from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from spatio_textual.affect_llm import affect_response_schema, extract_audited_affect
from spatio_textual.openai_responses import OpenAIResponsesJSONClient

INPUT_USD_PER_MTOK = 4.0
OUTPUT_USD_PER_MTOK = 20.0
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


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _failure_messages(result: dict[str, Any]) -> list[str]:
    telemetry = [row for row in result.get("telemetry", []) if isinstance(row, dict)]
    return [str(row.get("error") or "") for row in telemetry if row.get("success") is False]


def _is_transient_failure(messages: list[str]) -> bool:
    joined = " ".join(messages).lower()
    return bool(messages) and any(marker in joined for marker in TRANSIENT_ERROR_MARKERS)


def _extract_with_retry(
    client: OpenAIResponsesJSONClient,
    text: str,
    *,
    example_id: str,
) -> tuple[dict[str, Any], int, list[str]]:
    attempts = 0
    transient_failures: list[str] = []
    while True:
        attempts += 1
        result = extract_audited_affect(client, text, example_id=example_id)
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


def _actual_usage(telemetry: list[dict[str, Any]]) -> tuple[int | None, int | None, int | None]:
    input_values = [row.get("input_tokens") for row in telemetry]
    output_values = [row.get("output_tokens") for row in telemetry]
    reasoning_values = [row.get("reasoning_tokens") for row in telemetry]
    input_total = sum(int(v) for v in input_values) if input_values and all(isinstance(v, int) for v in input_values) else None
    output_total = sum(int(v) for v in output_values) if output_values and all(isinstance(v, int) for v in output_values) else None
    reasoning_total = sum(int(v) for v in reasoning_values) if reasoning_values and all(isinstance(v, int) for v in reasoning_values) else None
    return input_total, output_total, reasoning_total


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate frozen evidence-grounded SH2026 LLM affect predictions.")
    p.add_argument("input", type=Path)
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/llm_affect_formal/inference"))
    p.add_argument("--model", required=True)
    p.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh", "max"],
        default="medium",
    )
    p.add_argument("--max-output-tokens", type=int, default=2048)
    p.add_argument("--base-url", default=None)
    p.add_argument("--benchmark-mode", action="store_true")
    p.add_argument("--expected-sha256", default=None)
    p.add_argument("--frozen-at-commit", default=None)
    p.add_argument("--max-examples", type=int, default=None)
    return p.parse_args()


def _assert_formal(args: argparse.Namespace, records: list[dict[str, Any]]) -> str:
    if not args.expected_sha256 or not args.frozen_at_commit:
        raise SystemExit("--benchmark-mode requires --expected-sha256 and --frozen-at-commit")
    if args.max_examples is not None:
        raise SystemExit("--max-examples cannot be used in --benchmark-mode")
    if args.model != "gpt-5.6-sol":
        raise SystemExit("SH2026 affect v1 formal run requires --model gpt-5.6-sol")
    if args.reasoning_effort != "medium":
        raise SystemExit("SH2026 affect v1 formal run requires --reasoning-effort medium")
    if args.max_output_tokens != 2048:
        raise SystemExit("SH2026 affect v1 formal run requires --max-output-tokens 2048")
    actual = _sha256_path(args.input)
    if actual.lower() != args.expected_sha256.strip().lower():
        raise SystemExit(f"Affect benchmark checksum mismatch: expected {args.expected_sha256}, got {actual}")
    bad = [
        str(r.get("example_id"))
        for r in records
        if "provisional" in str(r.get("reference_status") or "").lower()
        or "pending" in str((r.get("source") or {}).get("distribution_status") or "").lower()
    ]
    if bad:
        raise SystemExit("Formal affect benchmark refused provisional/pending records: " + ", ".join(bad))
    return actual


def main() -> None:
    args = _parse_args()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY must be supplied through the environment; CLI secrets are not accepted")
    if args.max_output_tokens < 1:
        raise SystemExit("--max-output-tokens must be >= 1")

    records = _load_jsonl(args.input)
    benchmark_sha = _sha256_path(args.input)
    if args.benchmark_mode:
        benchmark_sha = _assert_formal(args, records)
    if args.max_examples is not None:
        if args.max_examples < 1:
            raise SystemExit("--max-examples must be >= 1")
        records = records[: args.max_examples]

    schema = affect_response_schema()
    schema_sha = _sha256_text(json.dumps(schema, sort_keys=True, separators=(",", ":")))
    client = OpenAIResponsesJSONClient(
        model=args.model,
        response_schema=schema,
        schema_name="sh2026_affect_v1",
        reasoning_effort=args.reasoning_effort,
        max_output_tokens=args.max_output_tokens,
        base_url=args.base_url,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = args.out_dir / "affect_predictions.jsonl"
    predictions: list[dict[str, Any]] = []
    telemetry_all: list[dict[str, Any]] = []
    resolved_models: set[str] = set()
    total_attempts = 0
    transient_failure_count = 0

    for ref in records:
        example_id = str(ref["example_id"])
        text = str(ref["text"])
        result, attempts, transient_failures = _extract_with_retry(client, text, example_id=example_id)
        total_attempts += attempts
        transient_failure_count += len(transient_failures)
        telemetry = [row for row in result.get("telemetry", []) if isinstance(row, dict)]
        telemetry_all.extend(telemetry)
        metadata = result.get("response_metadata") or {}
        resolved_model = str(metadata.get("resolved_model") or args.model)
        resolved_models.add(resolved_model)
        prompt = str(result.get("prompt") or "")
        predictions.append(
            {
                "schema_version": "sh2026-affect-prediction-v1",
                "example_id": example_id,
                "benchmark_sha256": benchmark_sha,
                "source_sha256": _sha256_text(text),
                "prompt_sha256": _sha256_text(prompt),
                "response_schema_sha256": schema_sha,
                "provider": "openai",
                "requested_model": args.model,
                "model": resolved_model,
                "reasoning_effort": args.reasoning_effort,
                "max_output_tokens": args.max_output_tokens,
                "provider_attempts": attempts,
                "transient_provider_failures": transient_failures,
                "sentiment_label": result["sentiment_label"],
                "emotion_labels": result["emotion_labels"],
                "evidence_quote": result["evidence_quote"],
                "evidence_start_char": result["evidence_start_char"],
                "evidence_end_char": result["evidence_end_char"],
                "evidence_grounding_status": result["evidence_grounding_status"],
                "explicit_or_inferred": result["explicit_or_inferred"],
                "confidence": result["confidence"],
                "notes": result["notes"],
                "requires_review": result["requires_review"],
                "review_notes": result["review_notes"],
                "telemetry": telemetry,
                "raw_structured_response": result.get("raw_structured_response"),
                "raw_response_text": result.get("raw_response_text"),
                "response_metadata": metadata,
            }
        )

    with prediction_path.open("w", encoding="utf-8") as fh:
        for row in predictions:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    input_tokens, output_tokens, reasoning_tokens = _actual_usage(telemetry_all)
    cost = None
    if input_tokens is not None and output_tokens is not None:
        cost = round(
            input_tokens * INPUT_USD_PER_MTOK / 1_000_000
            + output_tokens * OUTPUT_USD_PER_MTOK / 1_000_000,
            6,
        )

    manifest = {
        "schema_version": "sh2026-llm-affect-inference-v1",
        "run_mode": "benchmark" if args.benchmark_mode else "development",
        "benchmark_sha256": benchmark_sha,
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
        "response_schema_sha256": schema_sha,
        "prompt_policy": "spatio_textual.affect_llm.build_affect_prompt",
        "offset_policy": "model_returns_verbatim_evidence; software_computes_offsets",
        "repetitions": 1,
        "transient_retry_policy_seconds": list(TRANSIENT_RETRY_DELAYS_SECONDS),
        "total_provider_attempts": total_attempts,
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
        "estimated_run_cost_usd": cost,
        "claim_boundary": (
            "This is one completed observed run on the frozen public-safe synthetic SH2026 affect holdout. "
            "Labels are interpretations of textual evidence, not measurements of a person's psychological state, "
            "and the result does not establish archival-domain validity or stochastic stability."
        ),
    }
    (args.out_dir / "inference_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Wrote {len(predictions)} predictions to {prediction_path}")


if __name__ == "__main__":
    main()
