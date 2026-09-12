from __future__ import annotations

import hashlib
import subprocess
import sys
from collections import Counter
from pathlib import Path

from spatio_textual.gold import load_gold_jsonl, validate_gold_records


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILDER = PROJECT_ROOT / "benchmarks" / "build_holdout_v1.py"
EXPECTED_SHA256 = "fcd985d1727bb924d1b01a91166a1f792f7e15cf2ebf6f126d85eff1ac195453"
PRE_MIGRATION_SHA256 = "be9c526af68230f22cb92507af69d8aacea8cbb5bd7ad5dfcf3d7c16767fdb9b"
TEACHING_REFERENCE = PROJECT_ROOT / "workshop" / "data" / "gold_reference_v0.1.jsonl"


def _build(tmp_path: Path) -> Path:
    path = tmp_path / "holdout_v1.jsonl"
    subprocess.run(
        [sys.executable, str(BUILDER), "--output", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert path.exists()
    return path


def test_frozen_holdout_build_is_byte_stable_and_schema_valid(tmp_path):
    path = _build(tmp_path)
    payload = path.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_SHA256

    records = load_gold_jsonl(path)
    assert len(records) == 30
    assert validate_gold_records(records) == []
    assert len({row["example_id"] for row in records}) == 30
    assert all(row["reference_status"] == "adjudicated_reference" for row in records)
    assert all(row["source"]["distribution_status"] == "safe_to_distribute" for row in records)
    assert all(row["source"]["genre"] == "synthetic benchmark narrative" for row in records)


def test_holdout_is_disjoint_from_teaching_development_examples(tmp_path):
    holdout = load_gold_jsonl(_build(tmp_path))
    teaching = load_gold_jsonl(TEACHING_REFERENCE)
    holdout_ids = {row["example_id"] for row in holdout}
    teaching_ids = {row["example_id"] for row in teaching}
    assert holdout_ids.isdisjoint(teaching_ids)


def test_live_workflows_use_the_post_migration_holdout_checksum():
    workflows = PROJECT_ROOT / ".github" / "workflows"
    text = "\n".join(path.read_text(encoding="utf-8") for path in workflows.glob("*.yml"))
    assert PRE_MIGRATION_SHA256 not in text
    assert EXPECTED_SHA256 in text


def test_holdout_has_expected_methodological_coverage(tmp_path):
    records = load_gold_jsonl(_build(tmp_path))
    labels = Counter(span["label"] for row in records for span in row.get("spans", []))
    journeys = [journey for row in records for journey in row.get("journeys", [])]
    contextual = [
        journey
        for journey in journeys
        if "contextual_inference" in (journey.get("explicit_or_inferred") or {}).values()
    ]

    assert sum(labels.values()) == 145
    assert labels["TOPONYM"] == 41
    assert labels["GEONOUN"] == 27
    assert labels["SPATIAL_RELATION"] == 16
    assert labels["MOVEMENT_CUE"] == 18
    assert labels["TIME"] == 20
    assert len(journeys) == 18
    assert len(contextual) == 12

    for required in {
        "DISTANCE",
        "DIRECTION",
        "TRANSPORT_CUE",
        "SUBJECTIVE_DESCRIPTOR",
        "SENSORY_DESCRIPTOR",
        "DEICTIC_REFERENCE",
    }:
        assert labels[required] > 0
