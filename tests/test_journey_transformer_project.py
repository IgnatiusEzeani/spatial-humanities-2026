from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

from spatio_textual.journey_transformer import development_record_splits, journey_training_instances


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILDER = PROJECT_ROOT / "benchmarks" / "build_journey_dev_v1.py"
spec = importlib.util.spec_from_file_location("build_journey_dev_v1", BUILDER)
assert spec and spec.loader
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_transformer_journey_split_is_record_level_and_stratified():
    records = builder.build_records()
    splits = development_record_splits(records)
    assert Counter(splits.values()) == {"train": 144, "dev": 36}

    by_category = {}
    for record in records:
        category = record["source"]["development_category"]
        by_category.setdefault(category, Counter())[splits[record["example_id"]]] += 1
    assert all(counts == {"train": 12, "dev": 3} for counts in by_category.values())


def test_transformer_training_instances_are_separate_from_formal_holdout():
    records = builder.build_records()
    rows = journey_training_instances(records)
    assert len(rows) == 195
    assert Counter(row["split"] for row in rows) == {"train": 156, "dev": 39}
    assert all(row["record_id"].startswith("journey_dev_") for row in rows)

    positives = [row for row in rows if row["roles"]]
    assert len(positives) == 135
    assert all(any(role["role"] == "TRIGGER" for role in row["roles"]) for row in positives)
