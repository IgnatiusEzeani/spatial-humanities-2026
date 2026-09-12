from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "holdout_spec_v1.py"
DEFAULT_OUTPUT = HERE / "holdout_v1.jsonl"


def _load_spec_module():
    spec = importlib.util.spec_from_file_location("sh2026_holdout_spec_v1", SPEC_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_records() -> list[dict]:
    module = _load_spec_module()
    return [module._record(item) for item in module.SPECS]


def serialize(records: list[dict]) -> bytes:
    return "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in records
    ).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the frozen SH2026 holdout benchmark.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    records = build_records()
    payload = serialize(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    print(f"Wrote {len(records)} records to {args.output}")
    print(f"SHA256 {digest}")


if __name__ == "__main__":
    main()
