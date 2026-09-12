from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = REPO_ROOT
SNAPSHOT_PATH = PROJECT_ROOT / "benchmarks" / "results_snapshot_v1.json"
DEMO_PATH = PROJECT_ROOT / "demo" / "streamlit_app.py"


def load_snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_reportable_snapshot_rows_have_metrics_and_provenance() -> None:
    snapshot = load_snapshot()
    rows = snapshot["rows"]
    assert rows

    keys: set[tuple[str, str, str]] = set()
    for row in rows:
        assert row["status"] == "reportable"
        key = (row["dataset"], row["task"], row["method"])
        assert key not in keys
        keys.add(key)

        for metric in ("precision", "recall", "f1"):
            assert 0.0 <= float(row[metric]) <= 1.0

        source = REPO_ROOT / row["source_document"]
        assert source.is_file(), f"Missing provenance document: {source}"


def test_unscored_formal_llm_journey_is_not_presented_as_result() -> None:
    snapshot = load_snapshot()
    scored_llm_journeys = [
        row
        for row in snapshot["rows"]
        if row["task"] == "Journey" and "gpt-5.6-sol" in row["method"].lower()
    ]
    assert scored_llm_journeys == []

    omissions = [
        row
        for row in snapshot["omissions"]
        if row["task"] == "Journey" and "gpt-5.6-sol" in row["method"].lower()
    ]
    assert len(omissions) == 1
    assert omissions[0]["status"] == "not_reportable"
    assert "34578230359" in omissions[0]["reason"]
    assert (REPO_ROOT / omissions[0]["source_document"]).is_file()


def test_demo_reads_snapshot_instead_of_hardcoding_benchmark_rows() -> None:
    source = DEMO_PATH.read_text(encoding="utf-8")
    assert "results_snapshot_v1.json" in source
    assert "load_benchmark_snapshot" in source
    assert '"Precision": 0.750' not in source
