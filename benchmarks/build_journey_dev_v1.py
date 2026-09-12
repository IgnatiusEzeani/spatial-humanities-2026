from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "journey_dev_v1.jsonl"
EXPECTED_SHA256 = "34ce7c9d30739d0c051697ab7860d4fa5cf78c09e8d9efe02a9ce766860d95ec"

LOCATIONS = [
    "Aberdeen", "Inverness", "Perth", "Stirling", "Dundee", "Carlisle", "Chester", "Exeter", "Plymouth", "Norwich",
    "Cambridge", "Canterbury", "Brighton", "Portsmouth", "Southampton", "Leicester", "Nottingham", "Derby", "Coventry", "Worcester",
    "Paris", "Lyon", "Brussels", "Ghent", "Antwerp", "Rotterdam", "Utrecht", "Hamburg", "Bremen", "Cologne",
    "Vienna", "Graz", "Prague", "Brno", "Krakow", "Gdansk", "Warsaw", "Budapest", "Szeged", "Zagreb",
    "Accra", "Kumasi", "Lagos", "Ibadan", "Nairobi", "Mombasa", "Kampala", "Kigali", "Dar es Salaam", "Arusha",
]
NAMES = ["Mira", "Jonah", "Amina", "Leo", "Nadia", "Peter", "Ruth", "Daniel", "Sofia", "Samuel", "Grace", "Tariq", "Elena", "Noah", "Ada"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "3 March", "18 April", "7 May", "12 June", "21 July", "9 August", "14 September", "2 October"]
JOURNEY_FIELDS = ("start_location", "end_location", "transport_mode", "date", "journey_reason")


def _journey(
    example_id: str,
    index: int,
    text: str,
    evidence_quote: str,
    *,
    start_location: str | None = None,
    end_location: str | None = None,
    transport_mode: str | None = None,
    date: str | None = None,
    journey_reason: str | None = None,
    statuses: dict[str, str] | None = None,
) -> dict[str, Any]:
    start = text.index(evidence_quote)
    end = start + len(evidence_quote)
    values = {
        "start_location": start_location,
        "end_location": end_location,
        "transport_mode": transport_mode,
        "date": date,
        "journey_reason": journey_reason,
    }
    field_status: dict[str, str] = {}
    for field, value in values.items():
        if statuses and field in statuses:
            field_status[field] = statuses[field]
        else:
            field_status[field] = "explicit" if value not in (None, "") else "missing"
    requires_review = any(value == "contextual_inference" for value in field_status.values())
    return {
        "journeyId": f"{example_id}_j{index}",
        "fileId": example_id,
        **values,
        "evidence_quote": evidence_quote,
        "evidence_start_char": start,
        "evidence_end_char": end,
        "explicit_or_inferred": field_status,
        "requires_review": requires_review,
        "review_notes": ["Contains contextual inference."] if requires_review else [],
    }


def _record(example_id: str, category: str, text: str, journeys: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "spatio-textual-gold-0.1",
        "example_id": example_id,
        "reference_status": "adjudicated_reference",
        "source": {
            "distribution_status": "public_safe_synthetic_development",
            "source_note": "Instructor-authored synthetic journey-development example; not part of the frozen SH2026 holdout.",
            "development_category": category,
        },
        "text": text,
        "spans": [],
        "relations": [],
        "journeys": journeys,
    }


def build_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def next_id() -> str:
        return f"journey_dev_{len(records) + 1:03d}"

    for i in range(15):
        a = LOCATIONS[(3 * i) % len(LOCATIONS)]
        b = LOCATIONS[(3 * i + 1) % len(LOCATIONS)]
        c = LOCATIONS[(3 * i + 2) % len(LOCATIONS)]
        name = NAMES[i]
        day = DAYS[i]

        example_id = next_id()
        text = f"On {day}, {name} travelled from {a} to {b} by train for an archive visit."
        records.append(_record(example_id, "explicit_two_endpoint_train", text, [
            _journey(example_id, 1, text, text, start_location=a, end_location=b, transport_mode="train", date=f"On {day}", journey_reason="for an archive visit")
        ]))

        example_id = next_id()
        text = f"{name} walked from {a} toward {b} before noon."
        records.append(_record(example_id, "movement_verb_implied_transport", text, [
            _journey(example_id, 1, text, text, start_location=a, end_location=b, transport_mode="foot", date="before noon", statuses={"transport_mode": "contextual_inference"})
        ]))

        example_id = next_id()
        text = f"Late that evening, {name} arrived in {b} and checked into a hostel."
        records.append(_record(example_id, "destination_only_arrival", text, [
            _journey(example_id, 1, text, text, end_location=b, date="Late that evening")
        ]))

        example_id = next_id()
        text = f"At sunrise, {name} left {a} without recording the destination."
        records.append(_record(example_id, "origin_only_departure", text, [
            _journey(example_id, 1, text, text, start_location=a, date="At sunrise")
        ]))

        example_id = next_id()
        text = f"{name} stayed in {a} for several days. The following morning, from there, {name} travelled to {b} by coach."
        records.append(_record(example_id, "context_inherited_origin", text, [
            _journey(example_id, 1, text, text, start_location=a, end_location=b, transport_mode="bus", date="The following morning", statuses={"start_location": "contextual_inference"})
        ]))

        example_id = next_id()
        year = 2001 + i
        text = f"{name} had lived in {a}. When a new contract began in {year}, the family relocated to {b}."
        records.append(_record(example_id, "relocation_context_reason", text, [
            _journey(
                example_id,
                1,
                text,
                text,
                start_location=a,
                end_location=b,
                date=str(year),
                journey_reason="new contract",
                statuses={"start_location": "contextual_inference", "journey_reason": "contextual_inference"},
            )
        ]))

        example_id = next_id()
        text = f"For a conference, {name} flew from {a} to {b} on {day}."
        records.append(_record(example_id, "flight_reason", text, [
            _journey(example_id, 1, text, text, start_location=a, end_location=b, transport_mode="air", date=day, journey_reason="For a conference", statuses={"transport_mode": "contextual_inference"})
        ]))

        example_id = next_id()
        text = f"In May, {name} went from {a} to {b} by rail. Two days later, {name} continued from {b} to {c} by bus."
        first = f"In May, {name} went from {a} to {b} by rail."
        second = f"Two days later, {name} continued from {b} to {c} by bus."
        records.append(_record(example_id, "two_journeys_same_passage", text, [
            _journey(example_id, 1, text, first, start_location=a, end_location=b, transport_mode="train", date="In May"),
            _journey(example_id, 2, text, second, start_location=b, end_location=c, transport_mode="bus", date="Two days later"),
        ]))

    for i in range(15):
        a = LOCATIONS[(5 * i) % len(LOCATIONS)]
        b = LOCATIONS[(5 * i + 1) % len(LOCATIONS)]
        name = NAMES[i]

        example_id = next_id()
        records.append(_record(example_id, "negative_static_location", f"{name} lived in {a} near the old market for six years.", []))

        example_id = next_id()
        records.append(_record(example_id, "negative_cancelled_plan", f"{name} planned to travel from {a} to {b}, but the trip was cancelled.", []))

        example_id = next_id()
        records.append(_record(example_id, "negative_negated_journey", f"{name} never went from {a} to {b}; the route appears only in a letter.", []))

        example_id = next_id()
        records.append(_record(example_id, "negative_place_comparison", f"The exhibition compares maps of {a} and {b} without describing any journey between them.", []))

    assert len(records) == 180
    assert sum(len(record["journeys"]) for record in records) == 135
    return records


def serialize(records: list[dict[str, Any]]) -> bytes:
    return "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for record in records
    ).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the deterministic SH2026 journey development corpus v1")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    data = serialize(build_records())
    digest = hashlib.sha256(data).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"Journey development corpus checksum drifted: expected {EXPECTED_SHA256}, got {digest}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    checksum_path = args.output.with_suffix(args.output.suffix + ".sha256")
    checksum_path.write_text(f"{digest}  {args.output.name}\n", encoding="utf-8")
    print(f"Wrote 180 synthetic development passages to {args.output}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
