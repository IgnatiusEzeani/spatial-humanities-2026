from pathlib import Path

from spatio_textual.gold import (
    assert_valid_gold,
    load_gold_jsonl,
    score_relation_annotations,
    score_span_annotations,
    select_spans,
    find_span,
    validate_gold_record,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOLD_PATH = PROJECT_ROOT / "workshop" / "data" / "gold_reference_v0.1.jsonl"


def _records():
    return load_gold_jsonl(GOLD_PATH)


def test_gold_file_loads_and_validates():
    records = _records()
    assert len(records) == 5
    assert_valid_gold(records)


def test_every_reference_span_points_to_exact_source_text():
    for record in _records():
        text = record["text"]
        for span in record.get("spans", []):
            assert text[span["start_char"]:span["end_char"]] == span["text"]


def test_every_relation_evidence_points_to_exact_source_text():
    for record in _records():
        text = record["text"]
        for rel in record.get("relations", []):
            assert text[rel["evidence_start_char"]:rel["evidence_end_char"]] == rel["evidence_quote"]


def test_every_journey_evidence_points_to_exact_source_text():
    for record in _records():
        text = record["text"]
        for journey in record.get("journeys", []):
            assert text[journey["evidence_start_char"]:journey["evidence_end_char"]] == journey["evidence_quote"]


def test_contextual_journey_inference_requires_review():
    for record in _records():
        for journey in record.get("journeys", []):
            statuses = journey["explicit_or_inferred"]
            if "contextual_inference" in statuses.values():
                assert journey["requires_review"] is True


def test_historical_polity_source_form_is_preserved():
    record = next(r for r in _records() if r["example_id"] == "synthetic_historical_polity")
    top = next(s for s in record["spans"] if s["text"] == "Czechoslovakia")
    assert top["label"] == "TOPONYM"
    assert top["attributes"]["normalization_policy"] == "preserve_source_form"
    assert record["text"][top["start_char"]:top["end_char"]] == "Czechoslovakia"


def test_cambridge_is_textually_explicit_but_resolution_flagged_ambiguous():
    record = next(r for r in _records() if r["example_id"] == "synthetic_ambiguous_cambridge")
    cambridge = next(s for s in record["spans"] if s["text"] == "Cambridge")
    assert cambridge["certainty"] == "explicit"
    assert cambridge["attributes"]["resolution_expected"] == "ambiguous"
    assert record["journeys"][0]["requires_review"] is True


def test_exact_reference_score_is_perfect():
    record = next(r for r in _records() if r["example_id"] == "cldw_penrith_pooley_bridge")
    spans = record["spans"]
    score = score_span_annotations(spans, spans, match="exact")
    assert score["precision"] == 1.0
    assert score["recall"] == 1.0
    assert score["f1"] == 1.0


def test_overlap_scoring_exposes_boundary_difference_without_calling_it_total_failure():
    record = next(r for r in _records() if r["example_id"] == "cldw_penrith_pooley_bridge")
    reference = select_spans(record, ["DISTANCE"])
    predicted = [find_span(record["text"], "six miles", "DISTANCE", layer="spatial_cue")]
    exact = score_span_annotations(predicted, reference, match="exact")
    overlap = score_span_annotations(predicted, reference, match="overlap")
    assert exact["f1"] == 0.0
    assert overlap["f1"] == 1.0
    assert overlap["matches"][0]["overlap_iou"] < 1.0


def test_relation_score_is_perfect_for_reference_against_itself():
    record = next(r for r in _records() if r["example_id"] == "cldw_penrith_pooley_bridge")
    score = score_relation_annotations(record["relations"], record["relations"])
    assert score["f1"] == 1.0


def test_validator_detects_corrupt_offsets():
    record = next(r for r in _records() if r["example_id"] == "synthetic_historical_polity")
    corrupted = dict(record)
    corrupted["spans"] = [dict(s) for s in record["spans"]]
    corrupted["spans"][0]["start_char"] = 0
    errors = validate_gold_record(corrupted)
    assert any("text/offset mismatch" in error for error in errors)
