from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spatio_textual.evaluation import harmonize_ner_entities, reference_spans_for_ner
from spatio_textual.gold import assert_valid_gold, load_gold_jsonl, score_span_annotations
from spatio_textual.transformer_ner import HFNERAnnotator

MODEL = "dslim/bert-base-NER"
REVISION = "0b95561fd0c304538b5eb8a0ee532ca24dd009b9"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the pinned SH2026 Notebook 03 Hugging Face NER teaching fallback."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("workshop/data/gold_reference_v0.1.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sh2026_outputs/ner_teaching_fallback_v1.json"),
    )
    args = parser.parse_args()

    records = load_gold_jsonl(args.input)
    assert_valid_gold(records)
    annotator = HFNERAnnotator(MODEL, revision=REVISION, link_places=False)

    outputs: list[dict[str, Any]] = []
    for ref in records:
        out = annotator.annotate(str(ref["text"]))
        if out.get("error"):
            raise RuntimeError(f"HF NER failed for {ref['example_id']}: {out['error']}")
        harmonized = harmonize_ner_entities(out.get("entities") or [])
        reference = reference_spans_for_ner(ref)
        score = score_span_annotations(harmonized, reference, match="exact", label_sensitive=True)
        outputs.append(
            {
                "example_id": ref["example_id"],
                "title": ref.get("title"),
                "text": ref["text"],
                "source_status": ref.get("distribution_status") or ref.get("reference_status"),
                "entities": out.get("entities") or [],
                "harmonized_spatial_entities": harmonized,
                "reference_toponyms": reference,
                "exact_score": {
                    key: score[key]
                    for key in ("tp", "fp", "fn", "precision", "recall", "f1")
                },
                "telemetry": (out.get("telemetry") or [None])[0],
            }
        )

    payload = {
        "schema_version": "sh2026-ner-teaching-fallback-v1",
        "purpose": (
            "Precomputed machine output for the public-safe Notebook 03 teaching references. "
            "This is a reliability fallback for demonstrating a revision-pinned Hugging Face NER condition; "
            "it is not the frozen holdout benchmark and must not be presented as one."
        ),
        "source": str(args.input),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation_commit": os.getenv("SH2026_HEAD_SHA") or os.getenv("GITHUB_SHA"),
        "model": MODEL,
        "revision": REVISION,
        "target_ontology": "TOPONYM",
        "match": "exact",
        "records": outputs,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
