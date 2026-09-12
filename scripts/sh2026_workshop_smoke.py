from __future__ import annotations

import json
from pathlib import Path

from spatio_textual.emotion import EmotionAnalyzer
from spatio_textual.journeys import normalise_model_journey, validate_runtime_journey
from spatio_textual.moe import ModelAnnotation, adjudicate_entities
from spatio_textual.provenance import build_run_manifest
from spatio_textual.qa import segment_testimony
from spatio_textual.review import apply_human_review, human_correction_burden
from spatio_textual.rules import RuleGazetteerAnnotator
from spatio_textual.sentiment import SentimentAnalyzer
from spatio_textual.utils import Annotator, load_spacy_model
from spatio_textual.viz import journeys_to_geojson, make_map_geojson, to_geojson


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT
OUT = PROJECT_ROOT / "sh2026_outputs" / "release_smoke"
GAZETTEER = PROJECT_ROOT / "workshop" / "data" / "teaching_gazetteer.csv"


class FixedResolver:
    COORDS = {
        "oxford": (51.7520, -1.2577),
        "reading": (51.4543, -0.9781),
    }

    def resolve(self, name: str, label: str | None = None, context: str | None = None):
        coord = self.COORDS.get(name.lower())
        if coord is None:
            return None
        lat, lon = coord
        return {
            "resolved_name": name,
            "lat": lat,
            "lon": lon,
            "place_type_resolved": "CITY",
            "resolution_status": "resolved",
            "geo_source": "smoke:fixed",
            "geo_confidence": 1.0,
            "ambiguous": False,
            "candidates_count": 1,
            "candidates": [],
        }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    assert GAZETTEER.exists(), GAZETTEER

    qa_text = (
        "Q: Where did you live before the move?\n"
        "A: We lived in Amsterdam near my family. Later we travelled by train to London.\n"
        "Q: What happened next?\n"
        "A: I stayed there for several months."
    )
    turns = segment_testimony(qa_text)
    assert len(turns) == 4
    assert turns[0].is_question is True
    assert turns[1].is_answer is True

    rules = RuleGazetteerAnnotator(gazetteer_path=GAZETTEER, link_places=False)
    rule_result = rules.annotate(qa_text)
    assert rule_result["spans"]

    nlp = load_spacy_model("en_core_web_sm", add_entity_ruler=False)
    spacy_ann = Annotator(nlp, model_name="en_core_web_sm", link_places=False)
    spacy_result = spacy_ann.annotate(qa_text, include_text=True, include_events=True)
    assert spacy_result.get("error") is None

    sentiment = SentimentAnalyzer("rule").predict([turn.text for turn in turns])
    emotion = EmotionAnalyzer("rule").predict([turn.text for turn in turns])
    assert len(sentiment) == len(turns)
    assert len(emotion) == len(turns)
    assert all("distribution" in row for row in sentiment + emotion)

    adjudicated = adjudicate_entities([
        ModelAnnotation("rules", {"entities": rule_result["spans"], "telemetry": rule_result.get("telemetry", [])}),
        ModelAnnotation("spacy", spacy_result),
    ])
    assert isinstance(adjudicated.disagreements, list)

    journey_text = "I had been staying in Oxford for several weeks. From there I travelled to Reading by train."
    raw_journey = {
        "start_location": "Oxford",
        "end_location": "Reading",
        "transport_mode": "train",
        "date": None,
        "journey_reason": None,
        "evidence_quote": journey_text,
        "explicit_or_inferred": {
            "start_location": "contextual_inference",
            "end_location": "explicit",
            "transport_mode": "explicit",
            "date": "missing",
            "journey_reason": "missing",
        },
        "confidence": 0.9,
    }
    journey = normalise_model_journey(
        raw_journey,
        source_text=journey_text,
        file_id="smoke_journey",
        seg_id=1,
        model="fixed-smoke-proposal",
        provider="local",
    )
    assert journey["evidence_grounded"] is True
    assert journey["requires_review"] is True
    assert validate_runtime_journey(journey, journey_text) == []

    reviewed = apply_human_review(journey, action="accept", reason="contextual_inference")
    burden = human_correction_burden([reviewed])
    assert burden["records_reviewed"] == 1
    assert burden["records_corrected"] == 0

    route_geojson = journeys_to_geojson([journey], resolver=FixedResolver())
    assert len(route_geojson["features"]) == 1
    assert route_geojson["audit"][0]["mapped"] is True
    map_path = make_map_geojson(route_geojson, OUT / "route_map.html")
    assert Path(map_path).exists()

    point_records = [{
        "fileId": "smoke_points",
        "segId": 1,
        "entities": [
            {"text": "Oxford", "label": "GPE", "lat": 51.7520, "lon": -1.2577},
            {"text": "Reading", "label": "GPE", "lat": 51.4543, "lon": -0.9781},
        ],
    }]
    point_geojson = to_geojson(point_records)
    assert len(point_geojson["features"]) == 2

    manifest = build_run_manifest(
        input_text=qa_text,
        config={
            "ner_model": "en_core_web_sm",
            "rule_gazetteer": str(GAZETTEER),
            "api_key": "must-not-escape",
        },
    )
    assert manifest["config"]["api_key"] == "<redacted>"

    report = {
        "status": "passed",
        "project_root": str(PROJECT_ROOT),
        "qa_turns": len(turns),
        "rule_spans": len(rule_result["spans"]),
        "spacy_entities": len(spacy_result.get("entities") or []),
        "adjudication_disagreements": len(adjudicated.disagreements),
        "journey_evidence_grounded": journey["evidence_grounded"],
        "journey_requires_review": journey["requires_review"],
        "review_burden": burden,
        "route_features": len(route_geojson["features"]),
        "point_features": len(point_geojson["features"]),
        "manifest": manifest,
    }
    (OUT / "smoke_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
