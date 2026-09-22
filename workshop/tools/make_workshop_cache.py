#!/usr/bin/env python3
"""Build the cached panel results used by the main workshop notebook."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


NICE = [
    ("rules", "rules + gazetteer"),
    ("hf_bert_ner", "BERT NER (2019, pinned)"),
    ("spacy_trf_hybrid", "spaCy trf + gazetteers"),
    ("qwen_large", "Qwen 3.5 27B (open weight)"),
    ("gpt_5_6_sol", "GPT-5.6-sol"),
    ("claude", "Claude Opus 5"),
    ("gemini_2_5", "Gemini 2.5 Pro"),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build cached, model-free panel output for the workshop."
    )
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--passages", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--layer",
        default="TOPONYM",
        help="Layer shown in the comparison; the gold standard covers TOPONYM only.",
    )
    args = parser.parse_args()

    wanted = {
        passage["passage_id"]
        for passage in json.loads(args.passages.read_text(encoding="utf-8"))
    }
    results = json.loads(args.results.read_text(encoding="utf-8"))

    per_passage: dict[str, dict[str, list]] = defaultdict(dict)
    elapsed: dict[str, list[float]] = defaultdict(list)
    layers: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    with args.panel.open(encoding="utf-8") as panel_file:
        for line in panel_file:
            row = json.loads(line)
            voter = row["voter"]
            if row.get("elapsed_s") is not None:
                elapsed[voter].append(float(row["elapsed_s"]))
            for span in row["spans"]:
                layers[voter][span["label"]] += 1
            if row["passage_id"] not in wanted:
                continue
            per_passage[row["passage_id"]][voter] = [
                {
                    "start_char": span["start"],
                    "end_char": span["end"],
                    "label": span["label"],
                    "text": span["text"],
                }
                for span in row["spans"]
                if span["label"] == args.layer
            ]

    missing = wanted - set(per_passage)
    if missing:
        print(f"Warning: no panel output for {', '.join(sorted(missing))}")

    output: dict = {
        passage_id: {
            display_name: by_voter[voter]
            for voter, display_name in NICE
            if voter in by_voter
        }
        for passage_id, by_voter in per_passage.items()
    }

    all_labels = sorted({label for counts in layers.values() for label in counts})
    output["_layer_counts"] = [
        {
            "voter": display_name,
            **{label: layers[voter].get(label, 0) for label in all_labels},
            "total": sum(layers[voter].values()),
        }
        for voter, display_name in NICE
        if voter in layers
    ]

    exact = {
        voter: values.get("exact", {})
        for voter, values in results.get("voters", {}).items()
    }
    overlap = {
        voter: values.get("overlap", {})
        for voter, values in results.get("voters", {}).items()
    }
    output["_results"] = [
        {
            "system": display_name,
            "P": exact[voter].get("precision"),
            "R": exact[voter].get("recall"),
            "F1": exact[voter].get("f1"),
            "95% CI": (
                f"[{exact[voter]['f1_ci95'][0]:.3f}, "
                f"{exact[voter]['f1_ci95'][1]:.3f}]"
                if exact[voter].get("f1_ci95")
                else ""
            ),
            "F1 (overlap)": overlap[voter].get("f1"),
            "ms/passage": (
                round(1000 * sum(elapsed[voter]) / len(elapsed[voter]), 1)
                if elapsed.get(voter)
                else None
            ),
        }
        for voter, display_name in NICE
        if voter in exact
    ]
    output["_meta"] = {
        "n_passages": results.get("n_passages"),
        "n_gold_spans": results.get("n_gold_spans"),
        "n_negative_passages": results.get("n_negative_passages"),
        "layer_shown": args.layer,
        "note": (
            "Real outputs from the LD80 panel run. Scored against the <cdplace> "
            "human gold standard, binary span detection."
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {args.out}")
    print(f"  {len(per_passage)} passages x {len(output['_layer_counts'])} systems")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
