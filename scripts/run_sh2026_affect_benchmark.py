from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from spatio_textual.affect_benchmark import EMOTION_LABELS, evaluate_affect_predictions


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    p = argparse.ArgumentParser(description="Score cached SH2026 affect predictions.")
    p.add_argument("reference", type=Path)
    p.add_argument("--predictions", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/affect_evaluation"))
    p.add_argument("--benchmark-mode", action="store_true")
    p.add_argument("--expected-sha256", default=None)
    p.add_argument("--frozen-at-commit", default=None)
    p.add_argument(
        "--representable-emotions",
        default=",".join(EMOTION_LABELS),
        help="Comma-separated SH2026 emotion labels the method can natively represent.",
    )
    args = p.parse_args()

    reference_sha = _sha256(args.reference)
    if args.benchmark_mode:
        if not args.expected_sha256 or not args.frozen_at_commit:
            raise SystemExit("--benchmark-mode requires --expected-sha256 and --frozen-at-commit")
        if reference_sha.lower() != args.expected_sha256.strip().lower():
            raise SystemExit(f"Affect benchmark checksum mismatch: expected {args.expected_sha256}, got {reference_sha}")

    refs = _load_jsonl(args.reference)
    preds = _load_jsonl(args.predictions)
    representable = [x.strip() for x in args.representable_emotions.split(",") if x.strip()]
    summary = evaluate_affect_predictions(refs, preds, representable_emotion_labels=representable)
    summary.update(
        {
            "reference_sha256": reference_sha,
            "predictions_sha256": _sha256(args.predictions),
            "run_mode": "benchmark" if args.benchmark_mode else "development",
            "frozen_at_commit": args.frozen_at_commit,
        }
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "affect_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
