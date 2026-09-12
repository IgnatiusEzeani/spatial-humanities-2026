from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from spatio_textual.benchmark import aggregate_comparison_rows, span_comparison_row
from spatio_textual.evaluation import (
    reference_spans_for_ner,
    reference_spatial_reach,
    supported_reference_fraction,
)
from spatio_textual.gold import load_gold_jsonl, score_span_annotations
from spatio_textual.llm import LLMClient
from spatio_textual.llm_spans import (
    FULL_SPATIAL_LABELS,
    LLMSpanExtractor,
    TOPONYM_LABELS,
    span_audit_metrics,
    span_response_schema,
)
from spatio_textual.openai_responses import OpenAIResponsesJSONClient

REMOTE_PROVIDER_KEYS = {
    "openai": "OPENAI_API_KEY",
    "azure_openai": "AZURE_OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google_gemini": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "huggingface_inference": "HF_TOKEN",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run or re-score the SH2026 evidence-first LLM spatial NER experiments."
    )
    p.add_argument("input", type=Path, help="Frozen SH2026 reference JSONL")
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/llm_ner"))
    p.add_argument("--condition", choices=["toponym", "full_spatial"], default="toponym")
    p.add_argument("--predictions", type=Path, default=None, help="Cached prediction JSONL; skips live model calls")
    p.add_argument("--provider", default="openai")
    p.add_argument("--model", default=None)
    p.add_argument("--base-url", default=None)
    p.add_argument(
        "--reasoning-effort",
        choices=["none", "low", "medium", "high", "xhigh", "max"],
        default="none",
        help="OpenAI Responses reasoning effort. TOPONYM-only formal runs use none unless protocol version changes.",
    )
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
    if args.predictions is None and args.provider == "openai" and args.reasoning_effort != "none":
        raise SystemExit("SH2026 TOPONYM/full-spatial v1 formal OpenAI runs require --reasoning-effort none")
    if args.predictions is None and args.provider != "openai":
        raise SystemExit(
            "SH2026 LLM NER v1 formal live runs currently require provider=openai so strict Responses JSON Schema is enforced. "
            "Other providers may be evaluated later from separately frozen cached predictions."
        )
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
        raise SystemExit("Formal LLM NER benchmark refused provisional/pending records: " + ", ".join(map(str, bad)))
    return actual


def load_cached(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            example_id = str(row.get("example_id") or "")
            if not example_id:
                raise SystemExit(f"{path}:{line_no}: missing example_id")
            if example_id in rows:
                raise SystemExit(f"{path}:{line_no}: duplicate example_id {example_id}")
            rows[example_id] = row
    return rows


def validate_cached(
    cached: dict[str, dict[str, Any]],
    records: list[dict[str, Any]],
    *,
    condition: str,
    benchmark_sha256: str,
    formal: bool,
) -> None:
    expected_ids = {str(r["example_id"]) for r in records}
    if formal and set(cached) != expected_ids:
        raise SystemExit(
            f"Cached prediction coverage mismatch. missing={sorted(expected_ids - set(cached))}, "
            f"extra={sorted(set(cached) - expected_ids)}"
        )
    by_id = {str(r["example_id"]): r for r in records}
    for example_id, row in cached.items():
        if example_id not in by_id:
            if formal:
                raise SystemExit(f"Cached prediction {example_id!r} not in frozen benchmark")
            continue
        if row.get("source_sha256") != sha256_text(str(by_id[example_id]["text"])):
            raise SystemExit(f"Cached source hash mismatch for {example_id}")
        if formal and row.get("benchmark_sha256") != benchmark_sha256:
            raise SystemExit(f"Cached benchmark hash mismatch for {example_id}")
        if row.get("condition") != condition:
            raise SystemExit(f"Cached condition mismatch for {example_id}: {row.get('condition')!r}")


def require_live_provider(provider: str, base_url: str | None) -> None:
    if provider == "ollama":
        return
    key_name = REMOTE_PROVIDER_KEYS.get(provider)
    if key_name and not os.getenv(key_name):
        if provider == "huggingface_inference" and os.getenv("HUGGINGFACEHUB_API_TOKEN"):
            return
        raise SystemExit(f"Live provider {provider!r} requires {key_name} in the environment")
    if provider == "azure_openai" and not (base_url or os.getenv("AZURE_OPENAI_ENDPOINT")):
        raise SystemExit("azure_openai requires --base-url or AZURE_OPENAI_ENDPOINT")


def allowed_labels(condition: str) -> tuple[str, ...]:
    return TOPONYM_LABELS if condition == "toponym" else FULL_SPATIAL_LABELS


def reference_spans(record: dict[str, Any], condition: str) -> list[dict[str, Any]]:
    if condition == "toponym":
        return reference_spans_for_ner(record, include_geonouns=False, include_temporal=False)
    return reference_spatial_reach(record)


def live_prediction(
    record: dict[str, Any], *, extractor: LLMSpanExtractor, condition: str, benchmark_sha256: str
) -> dict[str, Any]:
    text = str(record["text"])
    result = extractor.extract(text, file_id=str(record["example_id"]))
    failures = [x for x in result.get("telemetry", []) if isinstance(x, dict) and x.get("success") is False]
    if failures:
        raise SystemExit(
            f"Provider failure for {record['example_id']}: "
            + "; ".join(str(x.get("error")) for x in failures)
        )
    return {
        "schema_version": "sh2026-llm-ner-prediction-v1",
        "example_id": record["example_id"],
        "condition": condition,
        "benchmark_sha256": benchmark_sha256,
        "source_sha256": sha256_text(text),
        "prompt_sha256": result.get("prompt_sha256"),
        "provider": getattr(extractor.client, "provider", None),
        "model": getattr(extractor.client, "model", None),
        "allowed_labels": result.get("allowed_labels"),
        "spans": result.get("spans", []),
        "audit": result.get("audit", {}),
        "telemetry": result.get("telemetry", []),
        "raw_structured_response": result.get("raw_structured_response"),
        "raw_response_text": result.get("raw_response_text"),
        "response_metadata": result.get("response_metadata"),
        "requires_review": result.get("requires_review"),
        "review_notes": result.get("review_notes", []),
    }


def evaluate(record: dict[str, Any], prediction: dict[str, Any], condition: str) -> dict[str, Any]:
    predicted = prediction.get("spans", [])
    reference = reference_spans(record, condition)
    supported = {"TOPONYM"} if condition == "toponym" else set(FULL_SPATIAL_LABELS)
    reach = supported_reference_fraction(record, supported)
    exact = span_comparison_row(
        example_id=str(record["example_id"]),
        method="llm_toponym" if condition == "toponym" else "llm_full_spatial",
        backend="openai_responses" if prediction.get("provider") == "openai" else "llm",
        model=prediction.get("model"),
        predicted=predicted,
        reference=reference,
        task="toponym_recognition" if condition == "toponym" else "spatial_annotation_full_schema",
        match="exact",
        supported_reference_total=reach["ontology_supported"],
        reference_total=reach["reference_total"],
        telemetry=prediction.get("telemetry", []),
        notes=(
            "LLM literal-span condition. Model proposes verbatim source strings; software computes offsets. "
            "TOPONYM-only is accuracy-comparable to spaCy/HF; full_spatial answers a wider representational question."
        ),
    )
    overlap = score_span_annotations(predicted, reference, match="overlap", label_sensitive=True)
    audit = span_audit_metrics(predicted)
    exact.update({
        "overlap_precision": overlap["precision"],
        "overlap_recall": overlap["recall"],
        "overlap_f1": overlap["f1"],
        "unsupported_rate": audit["unsupported_rate"],
        "evidence_grounded_rate": audit["evidence_grounded_rate"],
        "requires_review_rate": audit["requires_review_rate"],
        "contextual_inference_rate": audit["contextual_inference_rate"],
        "ambiguous_rate": audit["ambiguous_rate"],
        "invalid_label_rate": audit["invalid_label_rate"],
    })
    return exact


def build_live_extractor(args: argparse.Namespace) -> LLMSpanExtractor:
    labels = allowed_labels(args.condition)
    if args.provider == "openai":
        if not args.model:
            raise SystemExit("OpenAI live LLM NER requires an explicit --model identifier")
        schema_name = f"sh2026_{args.condition}_v1"
        client = OpenAIResponsesJSONClient(
            model=args.model,
            response_schema=span_response_schema(labels),
            schema_name=schema_name,
            reasoning_effort=args.reasoning_effort,
            base_url=args.base_url,
        )
    else:
        client = LLMClient(provider=args.provider, model=args.model, base_url=args.base_url)
    return LLMSpanExtractor(client, allowed_labels=labels)


def main() -> None:
    args = parse_args()
    records = load_gold_jsonl(args.input)
    benchmark_sha256 = sha256_path(args.input)
    if args.benchmark_mode:
        benchmark_sha256 = assert_benchmark_ready(args, records)
    if args.max_examples is not None:
        if args.max_examples < 1:
            raise SystemExit("--max-examples must be >= 1")
        records = records[: args.max_examples]

    cached = load_cached(args.predictions) if args.predictions else None
    extractor = None
    if cached is not None:
        validate_cached(
            cached,
            records,
            condition=args.condition,
            benchmark_sha256=benchmark_sha256,
            formal=args.benchmark_mode,
        )
    else:
        require_live_provider(args.provider, args.base_url)
        extractor = build_live_extractor(args)

    predictions: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for record in records:
        example_id = str(record["example_id"])
        if cached is not None:
            prediction = cached.get(example_id)
            if prediction is None:
                prediction = {
                    "schema_version": "sh2026-llm-ner-prediction-v1",
                    "example_id": example_id,
                    "condition": args.condition,
                    "benchmark_sha256": benchmark_sha256,
                    "source_sha256": sha256_text(str(record["text"])),
                    "provider": "missing_cached_prediction",
                    "model": None,
                    "spans": [],
                    "telemetry": [],
                }
        else:
            assert extractor is not None
            prediction = live_prediction(
                record,
                extractor=extractor,
                condition=args.condition,
                benchmark_sha256=benchmark_sha256,
            )
        predictions.append(prediction)
        rows.append(evaluate(record, prediction, args.condition))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "llm_ner_predictions.jsonl").open("w", encoding="utf-8") as fh:
        for row in predictions:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (args.out_dir / "llm_ner_evaluation_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    pd.DataFrame(rows).to_csv(args.out_dir / "llm_ner_evaluation_rows.csv", index=False)

    summary = aggregate_comparison_rows(rows)
    live_api = "openai_responses_json_schema" if cached is None and args.provider == "openai" else (
        "provider_specific_generic_json" if cached is None else "not_applicable_cached_predictions"
    )
    manifest = {
        "schema_version": "sh2026-llm-ner-run-v1",
        "run_mode": "benchmark" if args.benchmark_mode else "development",
        "evaluation_mode": "cached_predictions" if cached is not None else "live_provider",
        "condition": args.condition,
        "input": str(args.input),
        "benchmark_sha256": benchmark_sha256,
        "frozen_at_commit": args.frozen_at_commit,
        "examples": len(records),
        "provider": "cached" if cached is not None else args.provider,
        "model": "cached" if cached is not None else args.model,
        "api_mode": live_api,
        "reasoning_effort": None if cached is not None else args.reasoning_effort,
        "prompt_policy": "spatio_textual.llm_spans.build_span_prompt",
        "response_schema_sha256": sha256_text(json.dumps(span_response_schema(allowed_labels(args.condition)), sort_keys=True)),
        "offset_policy": "model_returns_verbatim_text_and_evidence; software_computes_offsets",
        "primary_match": "exact_character_span_and_label",
        "secondary_match": "overlap_character_span_and_label",
        "repetitions": 1,
        "temperature": "not_set; API/model default",
        "note": (
            "Formal SH2026 LLM NER v1 uses strict OpenAI Responses JSON Schema and reasoning_effort=none. "
            "One observed run does not support claims about stochastic stability; preserve predictions for exact re-scoring."
        ),
    }
    (args.out_dir / "llm_ner_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (args.out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    pd.DataFrame(summary).to_csv(args.out_dir / "llm_ner_summary.csv", index=False)

    print(json.dumps(summary, indent=2))
    print(f"Wrote {len(predictions)} predictions and {len(rows)} evaluation rows to {args.out_dir}")
    if not args.benchmark_mode:
        print("DEVELOPMENT MODE: do not report these values as final SH2026 benchmark results.")


if __name__ == "__main__":
    main()
