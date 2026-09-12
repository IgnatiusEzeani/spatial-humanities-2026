from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from spatio_textual.benchmark import aggregate_comparison_rows, span_comparison_row
from spatio_textual.evaluation import reference_spans_for_ner, supported_reference_fraction
from spatio_textual.gold import load_gold_jsonl
from spatio_textual.rules import RuleGazetteerAnnotator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAZETTEER = PROJECT_ROOT / "workshop" / "data" / "teaching_gazetteer.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Run the SH2026 deterministic rule/gazetteer condition on the same "
            "TOPONYM-only denominator used by spaCy, Hugging Face and LLM NER."
        )
    )
    p.add_argument("input", type=Path, help="Frozen SH2026 reference JSONL")
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/rules_toponym"))
    p.add_argument(
        "--gazetteer",
        type=Path,
        default=DEFAULT_GAZETTEER,
    )
    p.add_argument("--benchmark-mode", action="store_true")
    p.add_argument("--frozen-at-commit", default=None)
    p.add_argument("--expected-sha256", default=None)
    return p.parse_args()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_benchmark_ready(args: argparse.Namespace, records: list[dict[str, Any]]) -> str:
    if not args.frozen_at_commit:
        raise SystemExit("--benchmark-mode requires --frozen-at-commit")
    if not args.expected_sha256:
        raise SystemExit("--benchmark-mode requires --expected-sha256")
    actual = sha256_path(args.input)
    if actual.lower() != args.expected_sha256.strip().lower():
        raise SystemExit(f"Benchmark checksum mismatch: expected {args.expected_sha256}, got {actual}")
    bad = []
    for record in records:
        status = str(record.get("reference_status") or "").lower()
        distribution = str((record.get("source") or {}).get("distribution_status") or "").lower()
        if "provisional" in status or "pending" in distribution:
            bad.append(record.get("example_id"))
    if bad:
        raise SystemExit(
            "Formal rule TOPONYM benchmark refused provisional/pending records: "
            + ", ".join(map(str, bad))
        )
    return actual


def evaluate_record(
    record: dict[str, Any],
    annotator: RuleGazetteerAnnotator,
) -> dict[str, Any]:
    result = annotator.annotate(str(record["text"]))
    predicted = [
        dict(span)
        for span in result.get("spans", [])
        if span.get("label") == "TOPONYM"
    ]
    reference = reference_spans_for_ner(
        record,
        include_geonouns=False,
        include_temporal=False,
    )
    reach = supported_reference_fraction(record, {"TOPONYM"})
    return span_comparison_row(
        example_id=str(record["example_id"]),
        method="rule_gazetteer_toponym",
        backend="rules",
        model="entity_ruler+teaching_gazetteer",
        predicted=predicted,
        reference=reference,
        task="toponym_recognition",
        match="exact",
        supported_reference_total=reach["ontology_supported"],
        reference_total=reach["reference_total"],
        telemetry=result.get("telemetry", []),
        notes=(
            "TOPONYM-only deterministic condition. Uses the teaching/development gazetteer "
            "frozen before holdout inspection and filters rule output to TOPONYM so the "
            "accuracy denominator matches spaCy, HF and constrained LLM NER."
        ),
    )


def main() -> None:
    args = parse_args()
    records = load_gold_jsonl(args.input)
    input_sha256 = sha256_path(args.input)
    if args.benchmark_mode:
        input_sha256 = assert_benchmark_ready(args, records)

    annotator = RuleGazetteerAnnotator(
        gazetteer_path=args.gazetteer,
        link_places=False,
    )
    rows = [evaluate_record(record, annotator) for record in records]
    summary = aggregate_comparison_rows(rows)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "comparison_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    pd.DataFrame(rows).to_csv(args.out_dir / "comparison_rows.csv", index=False)
    (args.out_dir / "comparison_summary.json").write_text(
        json.dumps(
            {
                "schema_version": "sh2026-rules-toponym-v1",
                "run_mode": "benchmark" if args.benchmark_mode else "development",
                "input": str(args.input),
                "input_sha256": input_sha256,
                "frozen_at_commit": args.frozen_at_commit,
                "gazetteer": str(args.gazetteer),
                "task": "toponym_recognition",
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    pd.DataFrame(summary).to_csv(args.out_dir / "comparison_summary.csv", index=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Wrote {len(rows)} TOPONYM-only rule comparison rows to {args.out_dir}")
    if not args.benchmark_mode:
        print("DEVELOPMENT MODE: do not report these values as final SH2026 benchmark results.")


if __name__ == "__main__":
    main()
