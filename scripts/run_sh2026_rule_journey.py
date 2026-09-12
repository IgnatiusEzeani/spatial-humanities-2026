from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from spatio_textual.gold import load_gold_jsonl
from spatio_textual.journey_benchmark import aggregate_journey_benchmark_rows, journey_benchmark_row
from spatio_textual.journey_rules import RuleDependencyJourneyExtractor


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the transparent SH2026 rule/dependency journey baseline")
    p.add_argument("input", type=Path)
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/journey_rules"))
    p.add_argument("--spacy-model", default="en_core_web_sm")
    p.add_argument("--benchmark-mode", action="store_true")
    p.add_argument("--expected-sha256", default=None)
    p.add_argument("--frozen-at-commit", default=None)
    return p.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _assert_formal(args: argparse.Namespace, records: list[dict[str, Any]]) -> str:
    if not args.expected_sha256:
        raise SystemExit("--benchmark-mode requires --expected-sha256")
    if not args.frozen_at_commit:
        raise SystemExit("--benchmark-mode requires --frozen-at-commit")
    actual = _sha256(args.input)
    if actual.lower() != args.expected_sha256.strip().lower():
        raise SystemExit(f"Journey benchmark checksum mismatch: expected {args.expected_sha256}, got {actual}")
    bad = []
    for record in records:
        status = str(record.get("reference_status") or "").lower()
        distribution = str((record.get("source") or {}).get("distribution_status") or "").lower()
        if "provisional" in status or "pending" in distribution:
            bad.append(record.get("example_id"))
    if bad:
        raise SystemExit("Formal rule journey benchmark refused provisional/pending records: " + ", ".join(map(str, bad)))
    return actual


def main() -> None:
    args = _args()
    records = load_gold_jsonl(args.input)
    dataset_sha = _sha256(args.input)
    if args.benchmark_mode:
        dataset_sha = _assert_formal(args, records)

    extractor = RuleDependencyJourneyExtractor(model_name=args.spacy_model)
    predictions: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for record in records:
        example_id = str(record["example_id"])
        text = str(record["text"])
        result = extractor.extract(text, file_id=example_id)
        prediction = {
            "schema_version": "sh2026-journey-prediction-v1",
            "example_id": example_id,
            "benchmark_sha256": dataset_sha,
            "source_sha256": _source_sha(text),
            "provider": "local",
            "model": f"rule_dependency_v1+{args.spacy_model}",
            "journeys": result.get("journeys", []),
            "telemetry": result.get("telemetry", []),
            "requires_review": result.get("requires_review"),
            "review_notes": result.get("review_notes", []),
        }
        predictions.append(prediction)
        rows.append(journey_benchmark_row(
            example_id=example_id,
            predicted=prediction["journeys"],
            reference=record.get("journeys", []),
            telemetry=prediction["telemetry"],
            provider="local",
            model=prediction["model"],
        ))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "journey_predictions.jsonl").open("w", encoding="utf-8") as fh:
        for row in predictions:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (args.out_dir / "journey_evaluation_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_rows: list[dict[str, Any]] = []
    for row in rows:
        fields = (row.get("field_scoring") or {}).get("totals") or {}
        tel = row.get("telemetry_summary") or {}
        csv_rows.append({
            "example_id": row["example_id"],
            "predicted_journeys": row.get("predicted_journeys"),
            "reference_journeys": row.get("reference_journeys"),
            "tp": row.get("tp"),
            "fp": row.get("fp"),
            "fn": row.get("fn"),
            "precision": row.get("precision"),
            "recall": row.get("recall"),
            "f1": row.get("f1"),
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
    manifest = {
        "schema_version": "sh2026-rule-journey-manifest-v1",
        "run_mode": "benchmark" if args.benchmark_mode else "development",
        "input": str(args.input),
        "input_sha256": dataset_sha,
        "frozen_at_commit": args.frozen_at_commit,
        "examples": len(records),
        "method": "rule_dependency_v1",
        "spacy_model": args.spacy_model,
        "journey_match_policy": "sh2026-journey-match-v1",
        "journey_field_policy": "sh2026-journey-field-v1",
        "note": "Deterministic non-generative baseline. No geocoder, LLM or frozen-holdout tuning is used by the extractor.",
    }
    (args.out_dir / "journey_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
