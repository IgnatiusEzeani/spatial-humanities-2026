from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from spatio_textual.affect_transformer import (
    EMOTION_MODEL,
    EMOTION_REVISION,
    REPRESENTABLE_EMOTIONS,
    SENTIMENT_MODEL,
    SENTIMENT_REVISION,
    UNSUPPORTED_EMOTIONS,
    classify_affect_transformer,
)

TEACHING_SEGMENTS = [
    "We reached the village at sunset and felt relieved to find shelter.",
    "The road was quiet and we waited beside the river.",
    "I was afraid as we crossed the dark forest, but later I felt safe.",
    "We left the village and walked to the station before returning home.",
    "The children returned happily from summer camp.",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate the pinned SH2026 Notebook 05 transformer-affect teaching fallback."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sh2026_outputs/affect_teaching_fallback_v1.json"),
    )
    args = parser.parse_args()

    records = []
    for index, text in enumerate(TEACHING_SEGMENTS):
        records.append(
            {
                "segment_id": index,
                "text": text,
                **classify_affect_transformer(text),
            }
        )

    payload = {
        "schema_version": "sh2026-affect-teaching-fallback-v1",
        "purpose": (
            "Precomputed machine output for the public-safe Notebook 05 teaching passages. "
            "This is a reliability fallback for demonstrating a pinned transformer condition; "
            "it is not a benchmark result and must not be presented as one."
        ),
        "source": "workshop/05_affect_and_events.ipynb",
        "source_status": "instructor_created_public_safe",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generation_commit": os.getenv("SH2026_HEAD_SHA") or os.getenv("GITHUB_SHA"),
        "sentiment_model": SENTIMENT_MODEL,
        "sentiment_revision": SENTIMENT_REVISION,
        "emotion_model": EMOTION_MODEL,
        "emotion_revision": EMOTION_REVISION,
        "representable_emotion_labels": list(REPRESENTABLE_EMOTIONS),
        "unsupported_emotion_labels": list(UNSUPPORTED_EMOTIONS),
        "records": records,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
