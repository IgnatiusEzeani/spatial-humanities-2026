from __future__ import annotations

import hashlib
import importlib.util
from collections import Counter
from pathlib import Path

from spatio_textual.gold import assert_valid_gold


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "benchmarks" / "build_journey_dev_v1.py"
spec = importlib.util.spec_from_file_location("build_journey_dev_v1", SCRIPT)
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_journey_dev_v1_is_deterministic_and_valid():
    records = builder.build_records()
    assert len(records) == 180
    assert sum(len(record.get("journeys", [])) for record in records) == 135
    assert_valid_gold(records)

    digest = hashlib.sha256(builder.serialize(records)).hexdigest()
    assert digest == builder.EXPECTED_SHA256

    categories = Counter(record["source"]["development_category"] for record in records)
    assert len(categories) == 12
    assert set(categories.values()) == {15}


def test_journey_dev_v1_keeps_holdout_separate():
    records = builder.build_records()
    assert all(record["source"]["distribution_status"] == "public_safe_synthetic_development" for record in records)
    assert all(record["example_id"].startswith("journey_dev_") for record in records)
