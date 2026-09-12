from pathlib import Path

from spatio_textual.rules import RuleGazetteerAnnotator, load_teaching_gazetteer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GAZETTEER = PROJECT_ROOT / "workshop" / "data" / "teaching_gazetteer.csv"


def test_teaching_gazetteer_loads():
    rows = load_teaching_gazetteer(GAZETTEER)
    assert any(row["text"] == "Penrith" and row["label"] == "TOPONYM" for row in rows)
    assert any(row["text"] == "Czechoslovakia" for row in rows)


def test_rule_baseline_recognises_bounded_toponyms_and_distance():
    text = (
        "From Penrith two roads lead to Pooley Bridge, about six miles distant, "
        "which spans the Eamont just at its issue from Ulleswater."
    )
    ann = RuleGazetteerAnnotator(gazetteer_path=GAZETTEER, link_places=False)
    result = ann.annotate(text)
    found = {(row["text"], row["label"]) for row in result["spans"]}
    assert ("Penrith", "TOPONYM") in found
    assert ("Pooley Bridge", "TOPONYM") in found
    assert ("Eamont", "TOPONYM") in found
    assert ("Ulleswater", "TOPONYM") in found
    assert ("about six miles distant", "DISTANCE") in found


def test_resource_list_exposes_plural_brittleness_for_roads():
    ann = RuleGazetteerAnnotator(gazetteer_path=GAZETTEER, link_places=False)
    result = ann.annotate("Two roads crossed a road near the village.")
    spans = {(row["text"], row["label"]) for row in result["spans"]}
    assert ("road", "GEONOUN") in spans
    assert ("village", "GEONOUN") in spans
    assert ("near", "SPATIAL_RELATION") in spans
    assert ("roads", "GEONOUN") not in spans


def test_rule_baseline_is_case_insensitive_by_default():
    ann = RuleGazetteerAnnotator(gazetteer_path=GAZETTEER, link_places=False)
    result = ann.annotate("We left PENRITH for LONDON.")
    found = {(row["text"], row["label"]) for row in result["spans"]}
    assert ("PENRITH", "TOPONYM") in found
    assert ("LONDON", "TOPONYM") in found


def test_historical_place_linking_surfaces_review():
    ann = RuleGazetteerAnnotator(gazetteer_path=GAZETTEER, link_places=True)
    result = ann.annotate("In 1938 our family lived in Czechoslovakia.")
    row = next(item for item in result["spans"] if item["text"] == "Czechoslovakia")
    assert row["resolution_status"] == "unresolved"
    assert row["resolved_name"] == "Czechoslovakia"
    assert row["historical_name"] is True
    assert result["requires_review"] is True


def test_rule_telemetry_is_local_zero_cost_estimate():
    ann = RuleGazetteerAnnotator(gazetteer_path=GAZETTEER, link_places=False)
    telemetry = ann.annotate("From Penrith to London.")["telemetry"][0]
    assert telemetry["backend"] == "rules"
    assert telemetry["provider"] == "local"
    assert telemetry["cost_usd_est"] == 0.0
    assert telemetry["success"] is True
