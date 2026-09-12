from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from spatio_textual.affect_benchmark import EMOTION_LABELS, evaluate_affect_predictions
from spatio_textual.affect_rules import classify_affect_rule


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
    p = argparse.ArgumentParser(description="Run the transparent SH2026 affect rule baseline.")
    p.add_argument("input", type=Path)
    p.add_argument("--out-dir", type=Path, default=Path("sh2026_outputs/affect_rule"))
    p.add_argument("--benchmark-mode", action="store_true")
    p.add_argument("--expected-sha256", default=None)
    p.add_argument("--frozen-at-commit", default=None)
    args = p.parse_args()

    actual_sha = _sha256(args.input)
    if args.benchmark_mode:
        if not args.expected_sha256 or not args.frozen_at_commit:
            raise SystemExit("--benchmark-mode requires --expected-sha256 and --frozen-at-commit")
        if actual_sha.lower() != args.expected_sha256.strip().lower():
            raise SystemExit(f"Affect benchmark checksum mismatch: expected {args.expected_sha256}, got {actual_sha}")

    refs = _load_jsonl(args.input)
    predictions: list[dict[str, Any]] = []
    for ref in refs:
        pred = classify_affect_rule(str(ref["text"]))
        predictions.append({"example_id": ref["example_id"], **pred})

    summary = evaluate_affect_predictions(
        refs,
        predictions,
        representable_emotion_labels=EMOTION_LABELS,
    )
    summary.update(
        {
            "method": "sh2026-affect-lexicon-v1",
            "input_sha256": actual_sha,
            "run_mode": "benchmark" if args.benchmark_mode else "development",
            "frozen_at_commit": args.frozen_at_commit,
            "claim_boundary": (
                "Transparent lexical baseline on public-safe synthetic SH2026 affect references. "
                "It encodes explicit lexical cues and limited negation, not psychological truth or implicit affect understanding."
            ),
        }
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "affect_predictions.jsonl").open("w", encoding="utf-8") as fh:
        for row in predictions:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    (args.out_dir / "affect_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
