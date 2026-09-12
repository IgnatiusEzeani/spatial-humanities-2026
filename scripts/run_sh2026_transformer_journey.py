from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from spatio_textual.gold import load_gold_jsonl
from spatio_textual.journey_benchmark import aggregate_journey_benchmark_rows, journey_benchmark_row
from spatio_textual.journey_transformer import TransformerJourneyExtractor


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Score a frozen SH2026 transformer journey event model")
    p.add_argument("input", type=Path)
    p.add_argument("--model-dir", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/journey_transformer_formal"))
    p.add_argument("--max-length", type=int, default=256)
    p.add_argument("--benchmark-mode", action="store_true")
    p.add_argument("--expected-sha256", default=None)
    p.add_argument("--frozen-at-commit", default=None)
    p.add_argument("--model-metadata", type=Path, default=None, help="Optional training manifest copied into provenance")
    return p.parse_args()


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_dir(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(str(file_path.relative_to(path)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def assert_formal(args: argparse.Namespace, records: list[dict[str, Any]]) -> str:
    if not args.expected_sha256 or not args.frozen_at_commit:
        raise SystemExit("--benchmark-mode requires --expected-sha256 and --frozen-at-commit")
    actual = sha256_path(args.input)
    if actual.lower() != args.expected_sha256.strip().lower():
        raise SystemExit(f"Transformer journey benchmark checksum mismatch: expected {args.expected_sha256}, got {actual}")
    bad = []
    for record in records:
        status = str(record.get("reference_status") or "").lower()
        distribution = str((record.get("source") or {}).get("distribution_status") or "").lower()
        if "provisional" in status or "pending" in distribution:
            bad.append(record.get("example_id"))
    if bad:
        raise SystemExit("Formal transformer journey run refused provisional/pending records: " + ", ".join(map(str, bad)))
    return actual


def main() -> None:
    args = parse_args()
    if not args.model_dir.exists():
        raise SystemExit(f"Model directory does not exist: {args.model_dir}")
    records = load_gold_jsonl(args.input)
    dataset_sha = sha256_path(args.input)
    if args.benchmark_mode:
        dataset_sha = assert_formal(args, records)

    model_sha = sha256_dir(args.model_dir)
    extractor = TransformerJourneyExtractor(str(args.model_dir), max_length=args.max_length)
    predictions: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for record in records:
        example_id = str(record["example_id"])
        result = extractor.extract(str(record["text"]), file_id=example_id)
        predictions.append({
            "schema_version": "sh2026-journey-prediction-v1",
            "example_id": example_id,
            "benchmark_sha256": dataset_sha,
            "model_sha256": model_sha,
            "provider": "local",
            "model": "transformer_token_event_v1",
            "journeys": result.get("journeys", []),
            "telemetry": result.get("telemetry", []),
        })
        rows.append(journey_benchmark_row(
            example_id=example_id,
            predicted=result.get("journeys", []),
            reference=record.get("journeys", []),
            telemetry=result.get("telemetry", []),
            provider="local",
            model=f"transformer_token_event_v1:{model_sha[:12]}",
        ))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "journey_predictions.jsonl").open("w", encoding="utf-8") as fh:
        for row in predictions:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (args.out_dir / "journey_evaluation_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_rows = []
    for row in rows:
        fields = (row.get("field_scoring") or {}).get("totals") or {}
        tel = row.get("telemetry_summary") or {}
        csv_rows.append({
            "example_id": row["example_id"],
            "predicted_journeys": row.get("predicted_journeys"),
            "reference_journeys": row.get("reference_journeys"),
            "tp": row.get("tp"), "fp": row.get("fp"), "fn": row.get("fn"),
            "precision": row.get("precision"), "recall": row.get("recall"), "f1": row.get("f1"),
            "field_precision": fields.get("precision"),
            "field_recall": fields.get("recall"),
            "unsupported_field_rate": fields.get("unsupported_field_rate"),
            "evidence_grounded_rate": row.get("evidence_grounded_rate"),
            "requires_review_rate": row.get("requires_review_rate"),
            "contextual_inference_rate": row.get("contextual_inference_rate"),
            "latency_ms": tel.get("latency_ms_total"),
        })
    pd.DataFrame(csv_rows).to_csv(args.out_dir / "journey_evaluation_rows.csv", index=False)

    summary = aggregate_journey_benchmark_rows(rows)
    training_metadata = None
    if args.model_metadata and args.model_metadata.exists():
        training_metadata = json.loads(args.model_metadata.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "sh2026-transformer-journey-run-v1",
        "run_mode": "benchmark" if args.benchmark_mode else "development",
        "input": str(args.input),
        "input_sha256": dataset_sha,
        "frozen_at_commit": args.frozen_at_commit,
        "model_dir": str(args.model_dir),
        "model_sha256": model_sha,
        "training_metadata": training_metadata,
        "journey_match_policy": "sh2026-journey-match-v1",
        "journey_field_policy": "sh2026-journey-field-v1",
    }
    (args.out_dir / "journey_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
