from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SENTIMENT_LABELS = ("positive", "negative", "neutral", "mixed")
EMOTION_LABELS = (
    "fear",
    "sadness",
    "anger",
    "joy",
    "anxiety",
    "despair",
    "gratitude",
    "surprise",
)

DEV_CUES = {
    "fear": ("afraid", "frightened", "fearful", "scared"),
    "sadness": ("sad", "sorrowful", "downhearted", "mournful"),
    "anger": ("angry", "furious", "resentful", "irritated"),
    "joy": ("joyful", "delighted", "glad", "cheerful"),
    "anxiety": ("anxious", "uneasy", "worried", "nervous"),
    "despair": ("despondent", "discouraged", "without hope", "in despair"),
    "gratitude": ("grateful", "thankful", "appreciative", "full of thanks"),
    "surprise": ("surprised", "astonished", "startled", "amazed"),
}

HOLDOUT_CUES = {
    "fear": ("alarmed", "terrified", "filled with fear"),
    "sadness": ("melancholy", "grief-stricken", "deeply saddened"),
    "anger": ("indignant", "enraged", "incensed"),
    "joy": ("elated", "overjoyed", "pleased"),
    "anxiety": ("apprehensive", "restless with worry", "on edge"),
    "despair": ("dejected", "demoralised", "despairing"),
    "gratitude": ("indebted", "deeply thankful", "filled with gratitude"),
    "surprise": ("taken aback", "unexpectedly amazed", "caught by surprise"),
}

NEGATIVE_EMOTIONS = {"fear", "sadness", "anger", "anxiety", "despair"}
POSITIVE_EMOTIONS = {"joy", "gratitude"}


def _sentiment_for(emotion: str) -> str:
    if emotion in NEGATIVE_EMOTIONS:
        return "negative"
    if emotion in POSITIVE_EMOTIONS:
        return "positive"
    return "neutral"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _record(
    example_id: str,
    text: str,
    sentiment: str,
    emotions: list[str],
    *,
    evidence_quote: str | None = None,
    explicit_or_inferred: str = "explicit",
    category: str,
    split: str,
    notes: str = "",
) -> dict[str, Any]:
    if sentiment not in SENTIMENT_LABELS:
        raise ValueError(f"invalid sentiment {sentiment!r}")
    invalid = sorted(set(emotions) - set(EMOTION_LABELS))
    if invalid:
        raise ValueError(f"invalid emotion labels: {invalid}")
    if explicit_or_inferred not in {"explicit", "contextual_inference", "none"}:
        raise ValueError(f"invalid explicit_or_inferred {explicit_or_inferred!r}")

    quote = text if evidence_quote is None and emotions else evidence_quote
    evidence_spans: list[dict[str, Any]] = []
    if quote:
        start = text.find(quote)
        if start < 0:
            raise ValueError(f"evidence quote not found for {example_id}: {quote!r}")
        evidence_spans.append(
            {
                "text": quote,
                "start_char": start,
                "end_char": start + len(quote),
                "emotion_labels": list(emotions),
            }
        )

    return {
        "schema_version": "sh2026-affect-reference-v1",
        "example_id": example_id,
        "text": text,
        "sentiment_label": sentiment,
        "emotion_labels": list(emotions),
        "evidence_spans": evidence_spans,
        "explicit_or_inferred": explicit_or_inferred,
        "annotation_notes": notes,
        "reference_status": "adjudicated_synthetic_reference",
        "source": {
            "source_type": "instructor_authored_synthetic",
            "public_safe": True,
            "distribution_status": "frozen" if split == "holdout" else "development",
            "category": category,
            "split": split,
        },
    }


def _explicit_records(split: str, cues: dict[str, tuple[str, ...]], start_index: int) -> list[dict[str, Any]]:
    settings = (
        "at the station before the morning train",
        "while reading the archive catalogue",
        "on the path beside the lake",
        "during the meeting in the town hall",
    )
    rows: list[dict[str, Any]] = []
    idx = start_index
    for emotion in EMOTION_LABELS:
        for cue_index, cue in enumerate(cues[emotion]):
            setting = settings[cue_index % len(settings)]
            text = f"Mira felt {cue} {setting}."
            rows.append(
                _record(
                    f"affect_{split}_{idx:03d}",
                    text,
                    _sentiment_for(emotion),
                    [emotion],
                    evidence_quote=f"felt {cue}",
                    explicit_or_inferred="explicit",
                    category="explicit_single_emotion",
                    split=split,
                )
            )
            idx += 1
    return rows


def _dev_specials(start_index: int) -> list[dict[str, Any]]:
    cases = [
        # Multi-label / mixed-affect cases.
        ("I was frightened about the delay but grateful when the guide returned.", "mixed", ["fear", "gratitude"], "explicit", "multi_emotion"),
        ("The unexpected letter left me surprised and joyful.", "positive", ["surprise", "joy"], "explicit", "multi_emotion"),
        ("I felt anxious and afraid while waiting for the announcement.", "negative", ["anxiety", "fear"], "explicit", "multi_emotion"),
        ("The cancellation made me sad and despondent for the rest of the afternoon.", "negative", ["sadness", "despair"], "explicit", "multi_emotion"),
        ("I was angry at the mistake yet thankful that it was corrected quickly.", "mixed", ["anger", "gratitude"], "explicit", "multi_emotion"),
        ("The sudden change startled me, then I became uneasy about the new route.", "negative", ["surprise", "anxiety"], "explicit", "multi_emotion"),
        ("I was delighted to arrive, though sorrowful that the visit was ending.", "mixed", ["joy", "sadness"], "explicit", "multi_emotion"),
        ("I felt furious about the closure and discouraged about finding another entrance.", "negative", ["anger", "despair"], "explicit", "multi_emotion"),
        ("I was glad to see the old bridge and amazed that it was still standing.", "positive", ["joy", "surprise"], "explicit", "multi_emotion"),
        ("I felt thankful for the directions but nervous about missing the final bus.", "mixed", ["gratitude", "anxiety"], "explicit", "multi_emotion"),
        ("The empty platform made me fearful and downhearted.", "negative", ["fear", "sadness"], "explicit", "multi_emotion"),
        ("I was appreciative of the welcome and cheerful during the walk home.", "positive", ["gratitude", "joy"], "explicit", "multi_emotion"),
        ("The abrupt announcement astonished me and irritated everyone nearby.", "negative", ["surprise", "anger"], "explicit", "multi_emotion"),
        ("I felt worried by the silence and discouraged by the lack of news.", "negative", ["anxiety", "despair"], "explicit", "multi_emotion"),
        ("I was sad about leaving but grateful for the week we had spent there.", "mixed", ["sadness", "gratitude"], "explicit", "multi_emotion"),
        ("The good news surprised me and left me delighted.", "positive", ["surprise", "joy"], "explicit", "multi_emotion"),
        # Neutral and negated lexical cues. Domain words must not create affect by themselves.
        ("The train reached York at twelve minutes past noon.", "neutral", [], "none", "neutral"),
        ("The catalogue lists three villages beside the river.", "neutral", [], "none", "neutral"),
        ("We measured the path from the station to the library.", "neutral", [], "none", "neutral"),
        ("The old camp site appears on the map north of the road.", "neutral", [], "none", "neutral_domain_term"),
        ("The guide described a former ghetto district as part of the historical itinerary.", "neutral", [], "none", "neutral_domain_term"),
        ("Mira was not afraid of the short tunnel.", "neutral", [], "none", "negated_emotion"),
        ("I was not angry when the timetable changed.", "neutral", [], "none", "negated_emotion"),
        ("The unexpected turn did not surprise me.", "neutral", [], "none", "negated_emotion"),
        ("I felt no sadness about taking the later train.", "neutral", [], "none", "negated_emotion"),
        ("The word 'fear' appeared in the exhibition title, not as a description of my feelings.", "neutral", [], "none", "metalinguistic"),
        ("She quoted the phrase 'full of gratitude' from an old letter without describing her own reaction.", "neutral", ["gratitude"], "explicit", "reported_affect"),
        ("The archivist said he was anxious about the missing box.", "negative", ["anxiety"], "explicit", "reported_affect"),
        ("The diary records that its author felt joyful on returning home.", "positive", ["joy"], "explicit", "reported_affect"),
        ("The interview question asked whether she had been angry, but she did not answer it.", "neutral", [], "none", "question_not_evidence"),
        ("The note says the traveller was surprised by the new station building.", "neutral", ["surprise"], "explicit", "reported_affect"),
        ("The plaque mentions a period of despair in the writer's correspondence.", "negative", ["despair"], "explicit", "reported_affect"),
        # Implicit/contextual cases: no canonical emotion word is required.
        ("My hands trembled while I waited alone for the late train.", "negative", ["fear", "anxiety"], "contextual_inference", "implicit_affect"),
        ("I kept checking the clock and could not settle while the announcement was delayed.", "negative", ["anxiety"], "contextual_inference", "implicit_affect"),
        ("When the familiar hills came into view, I smiled all the way to the village.", "positive", ["joy"], "contextual_inference", "implicit_affect"),
        ("I had to stop speaking for a moment when I saw the empty family house.", "negative", ["sadness"], "contextual_inference", "implicit_affect"),
        ("I could hardly believe the quiet lane had become a busy square overnight.", "neutral", ["surprise"], "contextual_inference", "implicit_affect"),
        ("After three wrong directions, I spoke sharply to the driver about the route.", "negative", ["anger"], "contextual_inference", "implicit_affect"),
        ("The volunteer stayed after closing to help, and I wrote to thank her the next morning.", "positive", ["gratitude"], "contextual_inference", "implicit_affect"),
        ("After the final rejection, I stopped expecting the archive visit to happen that week.", "negative", ["despair"], "contextual_inference", "implicit_affect"),
        ("The room erupted in applause when the lost notebook was finally found.", "positive", ["joy"], "contextual_inference", "implicit_affect"),
        ("I avoided the narrow bridge after hearing the warning about high winds.", "negative", ["fear"], "contextual_inference", "implicit_affect"),
        ("I reread the message several times because the result was nothing like what I expected.", "neutral", ["surprise"], "contextual_inference", "implicit_affect"),
        ("The delay left me pacing beside the ticket office until the doors opened.", "negative", ["anxiety"], "contextual_inference", "implicit_affect"),
        ("I kept the guide's small note because her help had mattered so much that day.", "positive", ["gratitude"], "contextual_inference", "implicit_affect"),
        ("I spoke more loudly with every explanation because the decision still seemed unfair.", "negative", ["anger"], "contextual_inference", "implicit_affect"),
        ("For the rest of the journey I said very little after learning that the old house was gone.", "negative", ["sadness"], "contextual_inference", "implicit_affect"),
        ("By evening I no longer believed any of the alternative routes would work.", "negative", ["despair"], "contextual_inference", "implicit_affect"),
    ]
    rows: list[dict[str, Any]] = []
    for offset, (text, sentiment, emotions, status, category) in enumerate(cases):
        rows.append(
            _record(
                f"affect_dev_{start_index + offset:03d}",
                text,
                sentiment,
                emotions,
                explicit_or_inferred=status,
                category=category,
                split="dev",
            )
        )
    return rows


def _holdout_specials(start_index: int) -> list[dict[str, Any]]:
    cases = [
        ("The missed connection alarmed me, but I was deeply thankful when a neighbour offered a lift.", "mixed", ["fear", "gratitude"], "explicit", "multi_emotion"),
        ("I was on edge before the talk and overjoyed when it finished well.", "mixed", ["anxiety", "joy"], "explicit", "multi_emotion"),
        ("The closure left me deeply saddened and demoralised.", "negative", ["sadness", "despair"], "explicit", "multi_emotion"),
        ("I was incensed by the error and caught by surprise when it was repeated.", "negative", ["anger", "surprise"], "explicit", "multi_emotion"),
        ("The unexpected invitation left me pleased and filled with gratitude.", "positive", ["joy", "gratitude"], "explicit", "multi_emotion"),
        ("I felt terrified by the storm warning and restless with worry about the journey.", "negative", ["fear", "anxiety"], "explicit", "multi_emotion"),
        ("I was melancholy about leaving but unexpectedly amazed by the farewell gathering.", "mixed", ["sadness", "surprise"], "explicit", "multi_emotion"),
        ("I felt indebted to the guide even though I remained indignant about the cancellation.", "mixed", ["gratitude", "anger"], "explicit", "multi_emotion"),
        ("The road crosses the river two kilometres east of the village.", "neutral", [], "none", "neutral"),
        ("The timetable records one service each hour.", "neutral", [], "none", "neutral"),
        ("The former camp boundary is marked by a line of trees on the survey map.", "neutral", [], "none", "neutral_domain_term"),
        ("The museum guide uses the word 'despair' as the title of a gallery section.", "neutral", [], "none", "metalinguistic"),
        ("I was never frightened by the open hillside.", "neutral", [], "none", "negated_emotion"),
        ("I did not feel grateful for the automatic reminder; it was simply informative.", "neutral", [], "none", "negated_emotion"),
        ("The interviewer asked if he had been surprised, and he replied only with a date.", "neutral", [], "none", "question_not_evidence"),
        ("The letter says its writer felt apprehensive before the crossing.", "negative", ["anxiety"], "explicit", "reported_affect"),
        ("I gripped the rail until the swaying bridge was behind us.", "negative", ["fear"], "contextual_inference", "implicit_affect"),
        ("I arrived an hour early and checked the platform board again and again.", "negative", ["anxiety"], "contextual_inference", "implicit_affect"),
        ("I laughed when the familiar station clock finally came into view.", "positive", ["joy"], "contextual_inference", "implicit_affect"),
        ("I folded the old photograph away and could not continue the description for several moments.", "negative", ["sadness"], "contextual_inference", "implicit_affect"),
        ("I read the address twice because I had expected the building to be somewhere else entirely.", "neutral", ["surprise"], "contextual_inference", "implicit_affect"),
        ("My reply became increasingly sharp as the clerk repeated the same incorrect directions.", "negative", ["anger"], "contextual_inference", "implicit_affect"),
        ("I sent a note the next day to acknowledge how much the stranger's directions had helped.", "positive", ["gratitude"], "contextual_inference", "implicit_affect"),
        ("After the third cancellation, I stopped making plans for the visit at all.", "negative", ["despair"], "contextual_inference", "implicit_affect"),
    ]
    rows: list[dict[str, Any]] = []
    for offset, (text, sentiment, emotions, status, category) in enumerate(cases):
        rows.append(
            _record(
                f"affect_holdout_{start_index + offset:03d}",
                text,
                sentiment,
                emotions,
                explicit_or_inferred=status,
                category=category,
                split="holdout",
            )
        )
    return rows


def build_dev() -> list[dict[str, Any]]:
    rows = _explicit_records("dev", DEV_CUES, 1)
    rows.extend(_dev_specials(len(rows) + 1))
    if len(rows) != 80:
        raise AssertionError(f"expected 80 development records, got {len(rows)}")
    return rows


def build_holdout() -> list[dict[str, Any]]:
    rows = _explicit_records("holdout", HOLDOUT_CUES, 1)
    rows.extend(_holdout_specials(len(rows) + 1))
    if len(rows) != 48:
        raise AssertionError(f"expected 48 holdout records, got {len(rows)}")
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    ).encode("utf-8")
    path.write_bytes(payload)
    return _sha256(payload)


def main() -> None:
    p = argparse.ArgumentParser(description="Build deterministic SH2026 affect development and holdout corpora.")
    p.add_argument("--out-dir", type=Path, default=Path("benchmarks/sh2026"))
    args = p.parse_args()

    dev_path = args.out_dir / "affect_dev_v1.jsonl"
    holdout_path = args.out_dir / "affect_holdout_v1.jsonl"
    dev_sha = _write_jsonl(dev_path, build_dev())
    holdout_sha = _write_jsonl(holdout_path, build_holdout())
    print(f"Wrote 80 development records to {dev_path}")
    print(f"DEV_SHA256 {dev_sha}")
    print(f"Wrote 48 holdout records to {holdout_path}")
    print(f"HOLDOUT_SHA256 {holdout_sha}")


if __name__ == "__main__":
    main()
