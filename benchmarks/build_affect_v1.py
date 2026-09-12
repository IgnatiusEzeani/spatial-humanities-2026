from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "affect_spec_v1.py"


def _load_spec_module():
    spec = importlib.util.spec_from_file_location("sh2026_affect_spec_v1", SPEC_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic SH2026 affect development and holdout corpora."
    )
    parser.add_argument("--out-dir", type=Path, default=HERE)
    args = parser.parse_args()

    module = _load_spec_module()
    dev_path = args.out_dir / "affect_dev_v1.jsonl"
    holdout_path = args.out_dir / "affect_holdout_v1.jsonl"
    dev_sha = module._write_jsonl(dev_path, module.build_dev())
    holdout_sha = module._write_jsonl(holdout_path, module.build_holdout())
    print(f"Wrote 80 development records to {dev_path}")
    print(f"DEV_SHA256 {dev_sha}")
    print(f"Wrote 48 holdout records to {holdout_path}")
    print(f"HOLDOUT_SHA256 {holdout_sha}")


if __name__ == "__main__":
    main()
