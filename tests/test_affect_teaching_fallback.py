import json
from pathlib import Path

from spatio_textual.affect_transformer import (
    EMOTION_MODEL,
    EMOTION_REVISION,
    SENTIMENT_MODEL,
    SENTIMENT_REVISION,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FALLBACK = PROJECT_ROOT / "demo" / "affect_transformer_teaching_fallback_v1.json"

EXPECTED_TEXTS = [
    "We reached the village at sunset and felt relieved to find shelter.",
    "The road was quiet and we waited beside the river.",
    "I was afraid as we crossed the dark forest, but later I felt safe.",
    "We left the village and walked to the station before returning home.",
    "The children returned happily from summer camp.",
]


def test_affect_teaching_fallback_is_pinned_and_not_a_benchmark_claim():
    payload = json.loads(FALLBACK.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "sh2026-affect-teaching-fallback-v1"
    assert "not a benchmark result" in payload["purpose"]
    assert payload["source_status"] == "instructor_created_public_safe"
    assert payload["generation_commit"]
    assert payload["sentiment_model"] == SENTIMENT_MODEL
    assert payload["sentiment_revision"] == SENTIMENT_REVISION
    assert payload["emotion_model"] == EMOTION_MODEL
    assert payload["emotion_revision"] == EMOTION_REVISION
    assert [row["text"] for row in payload["records"]] == EXPECTED_TEXTS


def test_affect_teaching_fallback_records_preserve_model_provenance():
    payload = json.loads(FALLBACK.read_text(encoding="utf-8"))

    assert len(payload["records"]) == 5
    for index, row in enumerate(payload["records"]):
        assert row["segment_id"] == index
        assert row["sentiment_label"] in {"positive", "negative", "neutral", "mixed"}
        assert isinstance(row["emotion_labels"], list)
        assert row["evidence_quote"] is None
        assert row["explicit_or_inferred"] == "not_available"
        assert row["telemetry"]["success"] is True
        assert row["telemetry"]["provider"] == "huggingface_transformers"
        model = row["telemetry"]["model"]
        assert model["sentiment"] == SENTIMENT_MODEL
        assert model["sentiment_revision"] == SENTIMENT_REVISION
        assert model["emotion"] == EMOTION_MODEL
        assert model["emotion_revision"] == EMOTION_REVISION
