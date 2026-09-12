import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FALLBACK = PROJECT_ROOT / "demo" / "ner_transformer_teaching_fallback_v1.json"
EXAMPLES = PROJECT_ROOT / "workshop" / "data" / "examples.json"
MODEL = "dslim/bert-base-NER"
REVISION = "0b95561fd0c304538b5eb8a0ee532ca24dd009b9"
PUBLIC_STATUSES = {"safe_to_distribute", "public_domain_source_verified"}


def test_ner_teaching_fallback_is_pinned_public_safe_and_not_benchmark_claim():
    payload = json.loads(FALLBACK.read_text(encoding="utf-8"))
    examples = {row["id"]: row for row in json.loads(EXAMPLES.read_text(encoding="utf-8"))}

    assert payload["schema_version"] == "sh2026-ner-teaching-fallback-v1"
    assert "not the frozen holdout benchmark" in payload["purpose"]
    assert payload["generation_commit"]
    assert payload["model"] == MODEL
    assert payload["revision"] == REVISION
    assert payload["target_ontology"] == "TOPONYM"
    assert payload["match"] == "exact"

    fallback_ids = [row["example_id"] for row in payload["records"]]
    assert fallback_ids == list(examples)
    for row in payload["records"]:
        example = examples[row["example_id"]]
        assert example["distribution_status"] in PUBLIC_STATUSES
        assert row["text"] == example["text"]


def test_ner_teaching_fallback_preserves_spans_scores_and_model_provenance():
    payload = json.loads(FALLBACK.read_text(encoding="utf-8"))

    for row in payload["records"]:
        score = row["exact_score"]
        for key in ("precision", "recall", "f1"):
            assert 0.0 <= score[key] <= 1.0
        for entity in row["entities"]:
            assert row["text"][entity["start_char"]:entity["end_char"]] == entity["text"]
            assert entity["model_revision"] == REVISION
        for entity in row["harmonized_spatial_entities"]:
            assert entity["label"] == "TOPONYM"
            assert row["text"][entity["start_char"]:entity["end_char"]] == entity["text"]
            assert entity["model_revision"] == REVISION
        telemetry = row["telemetry"]
        assert telemetry["success"] is True
        assert telemetry["provider"] == "huggingface_transformers"
        assert telemetry["model_revision"] == REVISION
        assert telemetry["model"] == f"{MODEL}@{REVISION}"
