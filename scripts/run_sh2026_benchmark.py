from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from spatio_textual.benchmark import aggregate_comparison_rows, span_comparison_row
from spatio_textual.evaluation import (
    harmonize_ner_entities,
    reference_spans_for_ner,
    supported_reference_fraction,
)
from spatio_textual.gold import load_gold_jsonl
from spatio_textual.rules import RuleGazetteerAnnotator, filter_supported_gold_labels
from spatio_textual.transformer_ner import HFNERAnnotator
from spatio_textual.utils import Annotator, load_spacy_model

DEFAULT_HF_MODEL = "dslim/bert-base-NER"
# Pinned after the safetensors model was present; later upstream changes are
# mainly model-card edits. Formal SH2026 runs should record this exact revision.
DEFAULT_HF_REVISION = "0b95561fd0c304538b5eb8a0ee532ca24dd009b9"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GAZETTEER = PROJECT_ROOT / "workshop" / "data" / "teaching_gazetteer.csv"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run reproducible SH2026 span-method comparisons. Final keynote claims require a frozen holdout."
    )
    p.add_argument("input", type=Path, help="SH2026 reference JSONL")
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/benchmark"))
    p.add_argument(
        "--methods",
        default="rules",
        help="Comma-separated: rules,spacy,spacy_resources,hf",
    )
    p.add_argument("--gazetteer", type=Path, default=DEFAULT_GAZETTEER)
    p.add_argument("--spacy-model", default="en_core_web_sm")
    p.add_argument(
        "--hf-model",
        default=DEFAULT_HF_MODEL,
        help="Hugging Face token-classification model used by the hf condition.",
    )
    p.add_argument(
        "--hf-revision",
        default=DEFAULT_HF_REVISION,
        help="Pinned Hugging Face model revision. Set explicitly for formal comparisons.",
    )
    p.add_argument(
        "--benchmark-mode",
        action="store_true",
        help="Refuse provisional/development records and require freeze metadata/checksum.",
    )
    p.add_argument("--frozen-at-commit", default=None)
    p.add_argument(
        "--expected-sha256",
        default=None,
        help="Expected SHA-256 of the exact benchmark JSONL. Required in --benchmark-mode.",
    )
    return p.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _assert_benchmark_ready(
    records: list[dict[str, Any]],
    *,
    input_path: Path,
    frozen_at_commit: str | None,
    expected_sha256: str | None,
) -> str:
    if not frozen_at_commit:
        raise SystemExit("--benchmark-mode requires --frozen-at-commit so results remain tied to a frozen data revision.")
    if not expected_sha256:
        raise SystemExit("--benchmark-mode requires --expected-sha256 so the exact benchmark bytes are verified.")

    actual_sha256 = _sha256(input_path)
    if actual_sha256.lower() != expected_sha256.strip().lower():
        raise SystemExit(
            "Benchmark checksum mismatch: "
            f"expected {expected_sha256.strip().lower()}, got {actual_sha256.lower()}. "
            "Refusing to label this run as an SH2026 benchmark."
        )

    bad = []
    for rec in records:
        status = str(rec.get("reference_status") or "").lower()
        distribution = str((rec.get("source") or {}).get("distribution_status") or "").lower()
        if "provisional" in status or "pending" in distribution:
            bad.append(rec.get("example_id"))
    if bad:
        raise SystemExit(
            "Benchmark mode refused provisional/pending records: " + ", ".join(str(x) for x in bad)
        )
    return actual_sha256


def _strict_spacy_model(model_name: str):
    """Load the requested model without the package's tutorial fallback."""
    import spacy

    try:
        return spacy.load(model_name)
    except Exception as exc:
        raise SystemExit(
            f"Could not load spaCy model {model_name!r}. Benchmark mode must not silently fall back to a blank pipeline: {exc}"
        ) from exc


def run_rules(record: dict[str, Any], gazetteer: Path) -> dict[str, Any]:
    ann = RuleGazetteerAnnotator(gazetteer_path=gazetteer, link_places=False)
    result = ann.annotate(record["text"])
    reference = filter_supported_gold_labels(record.get("spans", []))
    reach = supported_reference_fraction(record, {span["label"] for span in reference})
    return span_comparison_row(
        example_id=record["example_id"],
        method="rule_gazetteer",
        backend="rules",
        model="entity_ruler+regex",
        predicted=result.get("spans", []),
        reference=reference,
        task="spatial_annotation_supported_labels",
        match="exact",
        supported_reference_total=reach["ontology_supported"],
        reference_total=reach["reference_total"],
        telemetry=result.get("telemetry", []),
        notes=(
            "Accuracy denominator contains only labels the deterministic baseline is designed to predict; "
            "coverage reports its broader ontology ceiling. The gazetteer is the pre-holdout teaching/development "
            "gazetteer and is not expanded using holdout errors."
        ),
    )


def build_spacy_runner(model_name: str) -> Annotator:
    nlp = _strict_spacy_model(model_name)
    return Annotator(nlp=nlp, model_name=model_name, link_places=False)


def build_spacy_resources_runner(model_name: str) -> Annotator:
    _strict_spacy_model(model_name)
    nlp = load_spacy_model(model_name, add_entity_ruler=True)
    return Annotator(
        nlp=nlp,
        model_name=f"{model_name}+project_resources",
        link_places=False,
    )


def build_hf_runner(model_name: str, revision: str | None) -> HFNERAnnotator:
    """Instantiate a revision-pinned HF token-classification condition."""
    try:
        return HFNERAnnotator(model_name=model_name, revision=revision, link_places=False)
    except Exception as exc:
        identifier = f"{model_name}@{revision}" if revision else model_name
        raise SystemExit(f"Could not initialise Hugging Face model {identifier!r}: {exc}") from exc


def run_spacy(record: dict[str, Any], annotator: Annotator, model_name: str) -> dict[str, Any]:
    result = annotator.annotate(record["text"], include_entities=True, include_verbs=False, include_events=False)
    predicted = harmonize_ner_entities(result.get("entities", []))
    reference = reference_spans_for_ner(record, include_geonouns=False, include_temporal=False)
    reach = supported_reference_fraction(record, {"TOPONYM"})
    return span_comparison_row(
        example_id=record["example_id"],
        method="contextual_ner",
        backend="spacy",
        model=model_name,
        predicted=predicted,
        reference=reference,
        task="toponym_recognition",
        match="exact",
        supported_reference_total=reach["ontology_supported"],
        reference_total=reach["reference_total"],
        telemetry=result.get("telemetry", []),
        notes="Contextual spaCy condition without project EntityRuler. Accuracy is TOPONYM-only; coverage is reported separately.",
    )


def run_spacy_resources(record: dict[str, Any], annotator: Annotator, model_name: str) -> dict[str, Any]:
    result = annotator.annotate(record["text"], include_entities=True, include_verbs=False, include_events=False)
    predicted = harmonize_ner_entities(result.get("entities", []))
    reference = reference_spans_for_ner(record, include_geonouns=True, include_temporal=False)
    reach = supported_reference_fraction(record, {"TOPONYM", "GEONOUN"})
    return span_comparison_row(
        example_id=record["example_id"],
        method="contextual_ner_plus_resources",
        backend="spacy+entity_ruler",
        model=f"{model_name}+project_resources",
        predicted=predicted,
        reference=reference,
        task="toponym_geonoun_recognition",
        match="exact",
        supported_reference_total=reach["ontology_supported"],
        reference_total=reach["reference_total"],
        telemetry=result.get("telemetry", []),
        notes=(
            "Hybrid condition: the same contextual spaCy model plus the project resource lists frozen before holdout inspection. "
            "Accuracy covers TOPONYM+GEONOUN; broader ontology coverage remains separate."
        ),
    )


def run_hf(record: dict[str, Any], annotator: HFNERAnnotator) -> dict[str, Any]:
    result = annotator.annotate(record["text"])
    if result.get("error"):
        raise SystemExit(
            f"Hugging Face benchmark inference failed for {record['example_id']}: {result['error']}"
        )
    predicted = harmonize_ner_entities(result.get("entities", []))
    reference = reference_spans_for_ner(record, include_geonouns=False, include_temporal=False)
    reach = supported_reference_fraction(record, {"TOPONYM"})
    return span_comparison_row(
        example_id=record["example_id"],
        method="hf_transformer_ner",
        backend="huggingface_transformers",
        model=annotator.model_identifier,
        predicted=predicted,
        reference=reference,
        task="toponym_recognition",
        match="exact",
        supported_reference_total=reach["ontology_supported"],
        reference_total=reach["reference_total"],
        telemetry=result.get("telemetry", []),
        notes=(
            "Revision-pinned off-the-shelf Hugging Face token-classification condition. Accuracy is TOPONYM-only, "
            "matching the contextual spaCy recognition denominator; place linking is disabled and representational "
            "reach is reported separately from within-task accuracy."
        ),
    )


def main() -> None:
    args = _parse_args()
    records = load_gold_jsonl(args.input)
    input_sha256 = _sha256(args.input)
    if args.benchmark_mode:
        input_sha256 = _assert_benchmark_ready(
            records,
            input_path=args.input,
            frozen_at_commit=args.frozen_at_commit,
            expected_sha256=args.expected_sha256,
        )

    methods = {item.strip().lower() for item in args.methods.split(",") if item.strip()}
    allowed = {"rules", "spacy", "spacy_resources", "hf"}
    unknown = methods - allowed
    if unknown:
        raise SystemExit(f"Unsupported methods: {sorted(unknown)}")

    spacy_runner = build_spacy_runner(args.spacy_model) if "spacy" in methods else None
    spacy_resources_runner = (
        build_spacy_resources_runner(args.spacy_model)
        if "spacy_resources" in methods
        else None
    )
    hf_runner = build_hf_runner(args.hf_model, args.hf_revision) if "hf" in methods else None

    rows: list[dict[str, Any]] = []
    for record in records:
        if "rules" in methods:
            rows.append(run_rules(record, args.gazetteer))
        if spacy_runner is not None:
            rows.append(run_spacy(record, spacy_runner, args.spacy_model))
        if spacy_resources_runner is not None:
            rows.append(run_spacy_resources(record, spacy_resources_runner, args.spacy_model))
        if hf_runner is not None:
            rows.append(run_hf(record, hf_runner))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    per_example_jsonl = args.out_dir / "comparison_rows.jsonl"
    with per_example_jsonl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    core_columns = [
        "example_id", "method", "backend", "model", "task", "precision", "recall", "f1",
        "coverage", "unsupported_rate", "ambiguous_rate", "human_edits_required", "latency_ms",
        "cost_usd_est", "notes",
    ]
    pd.DataFrame(rows).reindex(columns=core_columns).to_csv(args.out_dir / "comparison_rows.csv", index=False)

    summary = aggregate_comparison_rows(rows)
    hf_identifier = None
    if "hf" in methods:
        hf_identifier = f"{args.hf_model}@{args.hf_revision}" if args.hf_revision else args.hf_model
    (args.out_dir / "comparison_summary.json").write_text(
        json.dumps(
            {
                "run_mode": "benchmark" if args.benchmark_mode else "development",
                "frozen_at_commit": args.frozen_at_commit,
                "input": str(args.input),
                "input_sha256": input_sha256,
                "methods": sorted(methods),
                "models": {
                    "spacy": args.spacy_model if {"spacy", "spacy_resources"} & methods else None,
                    "hf": hf_identifier,
                    "hf_revision": args.hf_revision if "hf" in methods else None,
                },
                "summary": summary,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    pd.DataFrame(summary).to_csv(args.out_dir / "comparison_summary.csv", index=False)

    print(f"Wrote {len(rows)} comparison rows to {args.out_dir}")
    print(f"Input SHA-256: {input_sha256}")
    if not args.benchmark_mode:
        print("DEVELOPMENT MODE: outputs are diagnostic and must not be reported as final SH2026 benchmark results.")


if __name__ == "__main__":
    main()
