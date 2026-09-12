import json
from pathlib import Path

from spatio_textual.journeys import normalise_model_journey, validate_runtime_journey


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP = PROJECT_ROOT / "demo" / "streamlit_app.py"
EXAMPLES = PROJECT_ROOT / "workshop" / "data" / "examples.json"
FALLBACKS = PROJECT_ROOT / "demo" / "fallback_journeys_v1.json"
VALID_STATUSES = {"explicit", "contextual_inference", "missing"}
JOURNEY_FIELDS = {"start_location", "end_location", "transport_mode", "date", "journey_reason"}


def test_demo_exposes_humanities_facing_evidence_views():
    source = APP.read_text(encoding="utf-8")
    for marker in [
        "render_highlighted_source",
        "render_affect",
        "st.bar_chart",
        "render_journey_cards",
        "Source evidence",
        '["accept", "edit", "reject"]',
        "curated_teaching_fallback",
    ]:
        assert marker in source


def test_demo_never_requests_provider_secrets_from_visitors():
    source = APP.read_text(encoding="utf-8")
    forbidden = [
        'text_input("API key',
        'text_input("OpenAI API',
        'text_input("Groq API',
        'password="',
    ]
    for marker in forbidden:
        assert marker not in source


def test_curated_fallbacks_are_public_safe_and_evidence_grounded():
    examples = {row["id"]: row for row in json.loads(EXAMPLES.read_text(encoding="utf-8"))}
    payload = json.loads(FALLBACKS.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "sh2026-demo-fallback-v1"
    assert "not model predictions" in payload["purpose"]

    for example_id, journeys in payload["examples"].items():
        assert example_id in examples
        example = examples[example_id]
        assert example["distribution_status"] == "safe_to_distribute"
        source_text = example["text"]
        for raw in journeys:
            quote = raw["evidence_quote"]
            assert quote
            assert quote in source_text
            assert set(raw["explicit_or_inferred"]) == JOURNEY_FIELDS
            assert set(raw["explicit_or_inferred"].values()) <= VALID_STATUSES
            for field in JOURNEY_FIELDS:
                status = raw["explicit_or_inferred"][field]
                value = raw[field]
                if status == "missing":
                    assert value is None
                else:
                    assert value not in (None, "")

            runtime = normalise_model_journey(
                raw,
                source_text=source_text,
                file_id=f"test:{example_id}",
                seg_id=1,
                model="instructor_curated_v1",
                provider="sh2026",
            )
            assert runtime["evidence_grounded"] is True
            assert runtime["evidence_match_count"] == 1
            assert validate_runtime_journey(runtime, source_text) == []


def test_curated_fallback_does_not_cover_source_derived_cldw_example():
    payload = json.loads(FALLBACKS.read_text(encoding="utf-8"))
    assert "cldw_penrith_pooley_bridge" not in payload["examples"]
