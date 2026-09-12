from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from spatio_textual.benchmark import summarize_telemetry
from spatio_textual.evaluation import harmonize_ner_entities, reference_spans_for_ner
from spatio_textual.gold import load_gold_jsonl, score_span_annotations
from spatio_textual.rules import RuleGazetteerAnnotator
from spatio_textual.transformer_ner import HFNERAnnotator
from spatio_textual.utils import Annotator, load_spacy_model

DEFAULT_HF_MODEL = "dslim/bert-base-NER"
DEFAULT_HF_REVISION = "0b95561fd0c304538b5eb8a0ee532ca24dd009b9"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAZETTEER = PROJECT_ROOT / "workshop" / "data" / "teaching_gazetteer.csv"


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run the frozen-source CLDW TOPONYM external-validation check")
    p.add_argument("input", type=Path)
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/cldw_external_v1"))
    p.add_argument("--methods", default="rules,spacy,spacy_resources,hf")
    p.add_argument("--gazetteer", type=Path, default=DEFAULT_GAZETTEER)
    p.add_argument("--spacy-model", default="en_core_web_sm")
    p.add_argument("--hf-model", default=DEFAULT_HF_MODEL)
    p.add_argument("--hf-revision", default=DEFAULT_HF_REVISION)
    p.add_argument("--expected-sha256", default=None)
    p.add_argument("--frozen-at-commit", default=None)
    return p.parse_args()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strict_spacy(name: str):
    import spacy

    try:
        return spacy.load(name)
    except Exception as exc:
        raise SystemExit(f"Could not load required spaCy model {name!r}: {exc}") from exc


def _toponym_reference(record: dict[str, Any]) -> list[dict[str, Any]]:
    return reference_spans_for_ner(record, include_geonouns=False, include_temporal=False)


def _toponym_predictions_from_rules(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [span for span in result.get("spans", []) if span.get("label") == "TOPONYM"]


def _row(
    *,
    record: dict[str, Any],
    method: str,
    backend: str,
    model: str,
    predicted: list[dict[str, Any]],
    telemetry: list[dict[str, Any]],
) -> dict[str, Any]:
    reference = _toponym_reference(record)
    score = score_span_annotations(predicted, reference, match="exact", label_sensitive=True)
    tel = summarize_telemetry(telemetry)
    return {
        "example_id": record["example_id"],
        "method": method,
        "backend": backend,
        "model": model,
        "task": "cldw_toponym_recognition_external_validation",
        "match_policy": "exact_character_span_and_harmonized_TOPONYM_label",
        "reference_count": len(reference),
        "prediction_count": len(predicted),
        "tp": score["tp"],
        "fp": score["fp"],
        "fn": score["fn"],
        "precision": score["precision"],
        "recall": score["recall"],
        "f1": score["f1"],
        "latency_ms": tel.get("latency_ms_total"),
        "cost_usd_est": tel.get("cost_usd_est_total"),
        "source_path": (record.get("source") or {}).get("path"),
        "paragraph_ordinal": (record.get("source") or {}).get("paragraph_ordinal"),
        "reference_spans": reference,
        "predicted_spans": predicted,
    }


def _aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["method"], row["backend"], row["model"]), []).append(row)

    out: list[dict[str, Any]] = []
    for (method, backend, model), items in sorted(groups.items()):
        tp = sum(int(x["tp"]) for x in items)
        fp = sum(int(x["fp"]) for x in items)
        fn = sum(int(x["fn"]) for x in items)
        p = tp / (tp + fp) if tp + fp else 1.0
        r = tp / (tp + fn) if tp + fn else 1.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        latencies = [float(x["latency_ms"]) for x in items if x.get("latency_ms") is not None]
        costs = [float(x["cost_usd_est"]) for x in items if x.get("cost_usd_est") is not None]
        out.append({
            "method": method,
            "backend": backend,
            "model": model,
            "task": "cldw_toponym_recognition_external_validation",
            "match_policy": "exact_character_span_and_harmonized_TOPONYM_label",
            "examples": len(items),
            "reference_mentions": sum(int(x["reference_count"]) for x in items),
            "prediction_mentions": sum(int(x["prediction_count"]) for x in items),
            "tp_total": tp,
            "fp_total": fp,
            "fn_total": fn,
            "precision_micro": round(p, 6),
            "recall_micro": round(r, 6),
            "f1_micro": round(f1, 6),
            "precision_macro": round(sum(float(x["precision"]) for x in items) / len(items), 6),
            "recall_macro": round(sum(float(x["recall"]) for x in items) / len(items), 6),
            "f1_macro": round(sum(float(x["f1"]) for x in items) / len(items), 6),
            "latency_ms_mean_per_example": round(sum(latencies) / len(latencies), 3) if latencies else None,
            "latency_ms_total": round(sum(latencies), 3) if latencies else None,
            "cost_usd_est_total": round(sum(costs), 8) if costs else None,
        })
    return out


def main() -> None:
    args = _args()
    dataset_sha = _sha256(args.input)
    if args.expected_sha256 and dataset_sha.lower() != args.expected_sha256.strip().lower():
        raise SystemExit(f"External-validation checksum mismatch: expected {args.expected_sha256}, got {dataset_sha}")

    records = load_gold_jsonl(args.input)
    if not records:
        raise SystemExit("External-validation dataset is empty")
    for record in records:
        labels = {span.get("label") for span in record.get("spans", [])}
        if labels - {"TOPONYM"}:
            raise SystemExit(f"External validation must contain TOPONYM spans only: {record['example_id']} has {sorted(labels)}")

    methods = {x.strip().lower() for x in args.methods.split(",") if x.strip()}
    allowed = {"rules", "spacy", "spacy_resources", "hf"}
    if methods - allowed:
        raise SystemExit(f"Unsupported methods: {sorted(methods - allowed)}")

    rules = RuleGazetteerAnnotator(gazetteer_path=args.gazetteer, link_places=False) if "rules" in methods else None
    spacy_plain = Annotator(nlp=_strict_spacy(args.spacy_model), model_name=args.spacy_model, link_places=False) if "spacy" in methods else None
    spacy_resources = None
    if "spacy_resources" in methods:
        _strict_spacy(args.spacy_model)
        spacy_resources = Annotator(
            nlp=load_spacy_model(args.spacy_model, add_entity_ruler=True),
            model_name=f"{args.spacy_model}+project_resources",
            link_places=False,
        )
    hf = HFNERAnnotator(args.hf_model, revision=args.hf_revision, link_places=False) if "hf" in methods else None

    rows: list[dict[str, Any]] = []
    for record in records:
        text = record["text"]
        if rules is not None:
            result = rules.annotate(text)
            rows.append(_row(
                record=record,
                method="rule_gazetteer",
                backend="rules",
                model="entity_ruler+regex",
                predicted=_toponym_predictions_from_rules(result),
                telemetry=result.get("telemetry", []),
            ))
        if spacy_plain is not None:
            result = spacy_plain.annotate(text, include_entities=True, include_verbs=False, include_events=False)
            rows.append(_row(
                record=record,
                method="contextual_ner",
                backend="spacy",
                model=args.spacy_model,
                predicted=harmonize_ner_entities(result.get("entities", [])),
                telemetry=result.get("telemetry", []),
            ))
        if spacy_resources is not None:
            result = spacy_resources.annotate(text, include_entities=True, include_verbs=False, include_events=False)
            rows.append(_row(
                record=record,
                method="contextual_ner_plus_resources",
                backend="spacy+entity_ruler",
                model=f"{args.spacy_model}+project_resources",
                predicted=harmonize_ner_entities(result.get("entities", [])),
                telemetry=result.get("telemetry", []),
            ))
        if hf is not None:
            result = hf.annotate(text)
            if result.get("error"):
                raise SystemExit(f"HF inference failed on {record['example_id']}: {result['error']}")
            rows.append(_row(
                record=record,
                method="hf_transformer_ner",
                backend="huggingface_transformers",
                model=hf.model_identifier,
                predicted=harmonize_ner_entities(result.get("entities", [])),
                telemetry=result.get("telemetry", []),
            ))

    summary = _aggregate(rows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "comparison_rows.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    csv_rows = [
        {k: v for k, v in row.items() if k not in {"reference_spans", "predicted_spans"}}
        for row in rows
    ]
    pd.DataFrame(csv_rows).to_csv(args.out_dir / "comparison_rows.csv", index=False)
    pd.DataFrame(summary).to_csv(args.out_dir / "comparison_summary.csv", index=False)
    (args.out_dir / "comparison_summary.json").write_text(
        json.dumps({
            "evaluation": "source-derived CLDW external validation",
            "scope": "TOPONYM recognition only",
            "match_policy": "exact_character_span_and_harmonized_TOPONYM_label",
            "input": str(args.input),
            "input_sha256": dataset_sha,
            "frozen_at_commit": args.frozen_at_commit,
            "methods": sorted(methods),
            "models": {
                "spacy": args.spacy_model,
                "hf": hf.model_identifier if hf is not None else None,
            },
            "summary": summary,
            "reporting_caution": (
                "This ten-passage purposive CLDW check tests named-place recognition on source-derived historical writing only. "
                "It is not external validation of the richer SH2026 ontology, journeys, affect or interpretation. "
                "The primary score uses exact character-span matching, so boundary conventions in the CLDW <cdplace> markup remain visible rather than being silently relaxed."
            ),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
