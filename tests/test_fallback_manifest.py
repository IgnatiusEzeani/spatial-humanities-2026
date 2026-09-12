import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT
MANIFEST = PROJECT_ROOT / "demo" / "fallback_manifest_v1.json"


def test_fallback_manifest_resolves_and_separates_claim_types():
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "sh2026-demo-fallback-manifest-v1"
    assets = payload["assets"]
    assert {row["id"] for row in assets} == {
        "journey_curated_v1",
        "affect_transformer_teaching_v1",
        "ner_transformer_teaching_v1",
    }

    for row in assets:
        path = REPO_ROOT / row["path"]
        assert path.exists(), row["path"]
        assert row["benchmark_result"] is False

    journey = next(row for row in assets if row["id"] == "journey_curated_v1")
    assert journey["kind"] == "curated_teaching"
    assert journey["machine_output"] is False

    for asset_id in ("affect_transformer_teaching_v1", "ner_transformer_teaching_v1"):
        row = next(item for item in assets if item["id"] == asset_id)
        assert row["kind"] == "precomputed_machine_output"
        assert row["machine_output"] is True
        assert row["generation_commit"]
