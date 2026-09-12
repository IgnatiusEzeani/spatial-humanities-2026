from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from spatio_textual.gold import load_gold_jsonl
from spatio_textual.journey_benchmark import (
    aggregate_journey_benchmark_rows,
    journey_benchmark_row,
)
from spatio_textual.journeys import JourneyExtractor, build_journey_prompt
from spatio_textual.llm import LLMClient

REMOTE_PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "azure_openai": "AZURE_OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google_gemini": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "huggingface_inference": "HF_TOKEN",
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Run or re-score the evidence-first SH2026 journey benchmark. "
            "Use --predictions to reproduce evaluation without an API key."
        )
    )
    p.add_argument("input", type=Path, help="Frozen SH2026 reference JSONL")
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/journey_benchmark"))
    p.add_argument("--predictions", type=Path, default=None, help="Cached normalized prediction JSONL; skips live model calls")
    p.add_argument("--provider", default="openai")
    p.add_argument("--model", default=None)
    p.add_argument("--base-url", default=None)
    p.add_argument("--benchmark-mode", action="store_true")
    p.add_argument("--frozen-at-commit", default=None)
    p.add_argument("--expected-sha256", default=None)
    p.add_argument(
        "--max-examples",
        type=int,
        default=None,
        help="Development-only convenience. Formal benchmark mode refuses subsets.",
    )
    return p.parse_args()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _assert_benchmark_ready(args: argparse.Namespace, records: list[dict[str, Any]]) -> str:
    if not args.frozen_at_commit:
        raise SystemExit("--benchmark-mode requires --frozen-at-commit")
    if not args.expected_sha256:
        raise SystemExit("--benchmark-mode requires --expected-sha256")
    if args.max_examples is not None:
        raise SystemExit("--max-examples is development-only and cannot be used in --benchmark-mode")
    actual = _sha256_path(args.input)
    if actual.lower() != args.expected_sha256.strip().lower():
        raise SystemExit(f"Benchmark checksum mismatch: expected {args.expected_sha256}, got {actual}")
    bad = []
    for record in records:
        status = str(record.get("reference_status") or "").lower()
        distribution = str((record.get("source") or {}).get("distribution_status") or "").lower()
        if "provisional" in status or "pending" in distribution:
            bad.append(record.get("example_id"))
    if bad:
        raise SystemExit("Formal journey benchmark refused provisional/pending records: " + ", ".join(map(str, bad)))
    return actual


def _load_prediction_rows(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            example_id = str(row.get("example_id") or "")
            if not example_id:
                raise SystemExit(f"{path}:{line_no}: cached prediction lacks example_id")
            if example_id in out:
                raise SystemExit(f"{path}:{line_no}: duplicate cached example_id {example_id!r}")
            if not isinstance(row.get("journeys", []), list):
                raise SystemExit(f"{path}:{line_no}: journeys must be a list")
            out[example_id] = row
    return out


def _validate_cached_predictions(
    cached: dict[str, dict[str, Any]],
    records: list[dict[str, Any]],
    *,
    benchmark_sha256: str,
    formal: bool,
) -> None:
    expected_ids = {str(record["example_id"]) for record in records}
    cached_ids = set(cached)
    if formal and cached_ids != expected_ids:
        missing = sorted(expected_ids - cached_ids)
        extra = sorted(cached_ids - expected_ids)
        raise SystemExit(f"Cached prediction coverage mismatch. missing={missing}, extra={extra}")

    by_id = {str(record["example_id"]): record for record in records}
    for example_id, row in cached.items():
        if example_id not in by_id:
            if formal:
                raise SystemExit(f"Cached prediction {example_id!r} is not in the frozen benchmark")
            continue
        expected_source_sha = _sha256_text(str(by_id[example_id]["text"]))
        if row.get("source_sha256") != expected_source_sha:
            raise SystemExit(f"Cached prediction source hash mismatch for {example_id}")
        if formal and row.get("benchmark_sha256") != benchmark_sha256:
            raise SystemExit(f"Cached prediction benchmark hash mismatch for {example_id}")


def _require_live_provider_configuration(provider: str, base_url: str | None) -> None:
    if provider == "ollama":
        return
    key_name = REMOTE_PROVIDER_KEYS.get(provider)
    if key_name and not os.getenv(key_name):
        # HF inference also accepts the alternative standard variable.
        if provider == "huggingface_inference" and os.getenv("HUGGINGFACEHUB_API_TOKEN"):
            return
        raise SystemExit(
            f"Live provider {provider!r} requires {key_name} in the environment. "
            "API keys are intentionally not accepted as command-line arguments."
        )
    if provider == "azure_openai" and not (base_url or os.getenv("AZURE_OPENAI_ENDPOINT")):
        raise SystemExit("azure_openai requires --base-url or AZURE_OPENAI_ENDPOINT")


def _live_prediction(
    record: dict[str, Any],
    *,
    extractor: JourneyExtractor,
    provider: str,
    model: str,
    benchmark_sha256: str,
) -> dict[str, Any]:
    text = str(record["text"])
    prompt = build_journey_prompt(text)
    result = extractor.extract(text, file_id=str(record["example_id"]), seg_id=0)
    telemetry = result.get("telemetry", [])
    failures = [item for item in telemetry if isinstance(item, dict) and item.get("success") is False]
    if failures:
        raise SystemExit(
            f"Provider failure for {record['example_id']}: "
            + "; ".join(str(item.get("error")) for item in failures)
        )
    return {
        "schema_version": "sh2026-journey-prediction-v1",
        "example_id": record["example_id"],
        "benchmark_sha256": benchmark_sha256,
        "source_sha256": _sha256_text(text),
        "prompt_sha256": _sha256_text(prompt),
        "prompt_policy": "spatio_textual.journeys.build_journey_prompt",
        "provider": provider,
        "model": model,
        "journeys": result.get("journeys", []),
        "telemetry": telemetry,
        "requires_review": result.get("requires_review"),
        "review_notes": result.get("review_notes", []),
    }


def _prediction_for_record(
    record: dict[str, Any],
    *,
    cached: dict[str, dict[str, Any]] | None,
    extractor: JourneyExtractor | None,
    provider: str,
    model: str,
    benchmark_sha256: str,
) -> dict[str, Any]:
    example_id = str(record["example_id"])
    if cached is not None:
        if example_id not in cached:
            return {
                "schema_version": "sh2026-journey-prediction-v1",
                "example_id": example_id,
                "benchmark_sha256": benchmark_sha256,
                "source_sha256": _sha256_text(str(record["text"])),
                "prompt_sha256": _sha256_text(build_journey_prompt(str(record["text"]))),
                "provider": "missing_cached_prediction",
                "model": None,
                "journeys": [],
                "telemetry": [],
            }
        return cached[example_id]
    assert extractor is not None
    return _live_prediction(
        record,
        extractor=extractor,
        provider=provider,
        model=model,
        benchmark_sha256=benchmark_sha256,
    )


def main() -> None:
    args = _parse_args()
    records = load_gold_jsonl(args.input)
    benchmark_sha256 = _sha256_path(args.input)
    if args.benchmark_mode:
        benchmark_sha256 = _assert_benchmark_ready(args, records)
    if args.max_examples is not None:
        if args.max_examples < 1:
            raise SystemExit("--max-examples must be >= 1")
        records = records[: args.max_examples]

    cached = _load_prediction_rows(args.predictions) if args.predictions else None
    if cached is not None:
        _validate_cached_predictions(
            cached,
            records,
            benchmark_sha256=benchmark_sha256,
            formal=args.benchmark_mode,
        )
        provider = "cached"
        model = "cached"
        extractor = None
    else:
        _require_live_provider_configuration(args.provider, args.base_url)
        client = LLMClient(provider=args.provider, model=args.model, base_url=args.base_url)
        provider = client.provider
        model = client.model
        extractor = JourneyExtractor(client)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = args.out_dir / "journey_predictions.jsonl"
    evaluation_path = args.out_dir / "journey_evaluation_rows.jsonl"

    prediction_rows: list[dict[str, Any]] = []
    evaluation_rows: list[dict[str, Any]] = []
    for record in records:
        prediction = _prediction_for_record(
            record,
            cached=cached,
            extractor=extractor,
            provider=provider,
            model=model,
            benchmark_sha256=benchmark_sha256,
        )
        prediction_rows.append(prediction)
        predicted_journeys = prediction.get("journeys", [])
        reference_journeys = record.get("journeys", [])
        evaluation_rows.append(
            journey_benchmark_row(
                example_id=str(record["example_id"]),
                predicted=predicted_journeys,
                reference=reference_journeys,
                telemetry=prediction.get("telemetry", []),
                provider=str(prediction.get("provider") or provider),
                model=prediction.get("model") or model,
            )
        )

    with prediction_path.open("w", encoding="utf-8") as fh:
        for row in prediction_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with evaluation_path.open("w", encoding="utf-8") as fh:
        for row in evaluation_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_rows = []
    for row in evaluation_rows:
        field_totals = (row.get("field_scoring") or {}).get("totals") or {}
        tel = row.get("telemetry_summary") or {}
        csv_rows.append({
            "example_id": row["example_id"],
            "provider": row.get("provider"),
            "model": row.get("model"),
            "predicted_journeys": row.get("predicted_journeys"),
            "reference_journeys": row.get("reference_journeys"),
            "tp": row.get("tp"),
            "fp": row.get("fp"),
            "fn": row.get("fn"),
            "precision": row.get("precision"),
            "recall": row.get("recall"),
            "f1": row.get("f1"),
            "field_precision": field_totals.get("precision"),
            "field_recall": field_totals.get("recall"),
            "unsupported_field_rate": field_totals.get("unsupported_field_rate"),
            "evidence_grounded_rate": row.get("evidence_grounded_rate"),
            "requires_review_rate": row.get("requires_review_rate"),
            "contextual_inference_rate": row.get("contextual_inference_rate"),
            "latency_ms": tel.get("latency_ms_total"),
            "input_tokens_est": tel.get("input_tokens_est_total"),
            "output_tokens_est": tel.get("output_tokens_est_total"),
            "cost_usd_est": tel.get("cost_usd_est_total"),
        })
    pd.DataFrame(csv_rows).to_csv(args.out_dir / "journey_evaluation_rows.csv", index=False)

    summary = aggregate_journey_benchmark_rows(evaluation_rows)
    providers = sorted({str(row.get("provider")) for row in prediction_rows})
    models = sorted({str(row.get("model")) for row in prediction_rows})
    manifest = {
        "schema_version": "sh2026-journey-benchmark-manifest-v1",
        "run_mode": "benchmark" if args.benchmark_mode else "development",
        "evaluation_mode": "cached_predictions" if cached is not None else "live_provider",
        "input": str(args.input),
        "benchmark_sha256": benchmark_sha256,
        "frozen_at_commit": args.frozen_at_commit,
        "examples": len(records),
        "providers": providers,
        "models": models,
        "prompt_policy": "spatio_textual.journeys.build_journey_prompt",
        "journey_match_policy": "sh2026-journey-match-v1",
        "journey_field_policy": "sh2026-journey-field-v1",
        "sampling_configuration": (
            "provider_default_in_current_LLMClient; record model/provider and preserve predictions for exact re-scoring"
            if cached is None
            else "not_applicable_cached_predictions"
        ),
        "note": (
            "A formal SH2026 claim should preserve this manifest and journey_predictions.jsonl. "
            "LLM outputs are not treated as ground truth; evidence is grounded locally and contextual inference triggers review."
        ),
    }
    (args.out_dir / "journey_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Wrote {len(prediction_rows)} prediction rows and {len(evaluation_rows)} evaluation rows to {args.out_dir}")
    if not args.benchmark_mode:
        print("DEVELOPMENT MODE: do not report these values as final SH2026 benchmark results.")


if __name__ == "__main__":
    main()
