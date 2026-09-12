from __future__ import annotations

import hashlib
import json
from pathlib import Path

OUT = Path("benchmarks/sh2026/holdout_v1.jsonl")

SPECS = [
    ("holdout_001", "Named places and distance", "We walked from Keswick to Grasmere, a little over twelve miles by road.", [("Keswick", "TOPONYM", "entity"), ("Grasmere", "TOPONYM", "entity"), ("twelve miles", "DISTANCE", "spatial_cue"), ("road", "GEONOUN", "entity"), ("walked", "MOVEMENT_CUE", "event_cue")], {"start_location":"Keswick","end_location":"Grasmere","transport_mode":"walking","date":None,"journey_reason":None,"evidence":"We walked from Keswick to Grasmere, a little over twelve miles by road.","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"contextual_inference","date":"missing","journey_reason":"missing"}}),
    ("holdout_002", "Named places with direction", "From York we travelled north to Durham before sunset.", [("York", "TOPONYM", "entity"), ("Durham", "TOPONYM", "entity"), ("north", "DIRECTION", "spatial_cue"), ("before sunset", "TIME", "temporal_cue"), ("travelled", "MOVEMENT_CUE", "event_cue")], {"start_location":"York","end_location":"Durham","transport_mode":None,"date":"before sunset","journey_reason":None,"evidence":"From York we travelled north to Durham before sunset.","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"missing","date":"explicit","journey_reason":"missing"}}),
    ("holdout_003", "Place and river relation", "The cottage stood beside the River Wye, two miles from Hereford.", [("cottage", "GEONOUN", "entity"), ("beside", "SPATIAL_RELATION", "spatial_cue"), ("River Wye", "TOPONYM", "entity"), ("two miles", "DISTANCE", "spatial_cue"), ("Hereford", "TOPONYM", "entity")], None),
    ("holdout_004", "Island and mainland", "The ferry left Oban for Mull at half past eight.", [("ferry", "GEONOUN", "entity"), ("Oban", "TOPONYM", "entity"), ("Mull", "TOPONYM", "entity"), ("half past eight", "TIME", "temporal_cue"), ("left", "MOVEMENT_CUE", "event_cue")], {"start_location":"Oban","end_location":"Mull","transport_mode":"ferry","date":"half past eight","journey_reason":None,"evidence":"The ferry left Oban for Mull at half past eight.","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"contextual_inference","date":"explicit","journey_reason":"missing"}}),
    ("holdout_005", "Simple place sequence", "After lunch I cycled from Lancaster to Morecambe and returned before dark.", [("After lunch", "TIME", "temporal_cue"), ("cycled", "MOVEMENT_CUE", "event_cue"), ("Lancaster", "TOPONYM", "entity"), ("Morecambe", "TOPONYM", "entity"), ("before dark", "TIME", "temporal_cue")], {"start_location":"Lancaster","end_location":"Morecambe","transport_mode":"bicycle","date":"After lunch","journey_reason":None,"evidence":"After lunch I cycled from Lancaster to Morecambe","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"contextual_inference","date":"explicit","journey_reason":"missing"}}),
    ("holdout_006", "Ambiguous settlement", "I moved from Richmond to London after finishing school.", [("moved", "MOVEMENT_CUE", "event_cue"), ("Richmond", "TOPONYM", "entity"), ("London", "TOPONYM", "entity"), ("after finishing school", "TIME", "temporal_cue")], {"start_location":"Richmond","end_location":"London","transport_mode":None,"date":"after finishing school","journey_reason":None,"evidence":"I moved from Richmond to London after finishing school.","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"missing","date":"explicit","journey_reason":"missing"}}),
    ("holdout_007", "Historical polity", "In 1988 she was living in Yugoslavia near the Adriatic coast.", [("1988", "TIME", "temporal_cue"), ("Yugoslavia", "TOPONYM", "entity"), ("near", "SPATIAL_RELATION", "spatial_cue"), ("coast", "GEONOUN", "entity")], None),
    ("holdout_008", "Historical city name", "His letter says he arrived in Bombay in 1952 and stayed near the harbour.", [("Bombay", "TOPONYM", "entity"), ("1952", "TIME", "temporal_cue"), ("near", "SPATIAL_RELATION", "spatial_cue"), ("harbour", "GEONOUN", "entity"), ("arrived", "MOVEMENT_CUE", "event_cue")], {"start_location":None,"end_location":"Bombay","transport_mode":None,"date":"1952","journey_reason":None,"evidence":"he arrived in Bombay in 1952","statuses":{"start_location":"missing","end_location":"explicit","transport_mode":"missing","date":"explicit","journey_reason":"missing"}}),
    ("holdout_009", "Variant spelling", "The diary records a stop at Ulleswater before the party continued towards Penrith.", [("Ulleswater", "TOPONYM", "entity"), ("continued", "MOVEMENT_CUE", "event_cue"), ("towards", "SPATIAL_RELATION", "spatial_cue"), ("Penrith", "TOPONYM", "entity")], {"start_location":"Ulleswater","end_location":"Penrith","transport_mode":None,"date":None,"journey_reason":None,"evidence":"a stop at Ulleswater before the party continued towards Penrith","statuses":{"start_location":"contextual_inference","end_location":"explicit","transport_mode":"missing","date":"missing","journey_reason":"missing"}}),
    ("holdout_010", "Country alias", "We flew from the UK to France and then took a train south.", [("UK", "TOPONYM", "entity"), ("France", "TOPONYM", "entity"), ("flew", "MOVEMENT_CUE", "event_cue"), ("train", "TRANSPORT_CUE", "journey_cue"), ("south", "DIRECTION", "spatial_cue")], {"start_location":"UK","end_location":"France","transport_mode":"air","date":None,"journey_reason":None,"evidence":"We flew from the UK to France","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"contextual_inference","date":"missing","journey_reason":"missing"}}),
    ("holdout_011", "Relational woodland", "The shelter was hidden behind the ridge and below the old quarry.", [("shelter", "GEONOUN", "entity"), ("behind the ridge", "SPATIAL_RELATION", "spatial_cue"), ("ridge", "GEONOUN", "entity"), ("below the old quarry", "SPATIAL_RELATION", "spatial_cue"), ("quarry", "GEONOUN", "entity")], None),
    ("holdout_012", "Deictic route", "The footpath curved to our right, then disappeared beyond the trees.", [("footpath", "GEONOUN", "entity"), ("to our right", "DIRECTION", "spatial_cue"), ("beyond the trees", "SPATIAL_RELATION", "spatial_cue"), ("trees", "GEONOUN", "entity")], None),
    ("holdout_013", "Qualitative nearness", "A small bridge lay nearby, but the nearest road was across the field.", [("bridge", "GEONOUN", "entity"), ("nearby", "DISTANCE", "spatial_cue"), ("nearest", "DISTANCE", "spatial_cue"), ("road", "GEONOUN", "entity"), ("across the field", "SPATIAL_RELATION", "spatial_cue"), ("field", "GEONOUN", "entity")], None),
    ("holdout_014", "Vertical relation", "The village sits high above the lake, with farms scattered along the slope.", [("village", "GEONOUN", "entity"), ("above the lake", "SPATIAL_RELATION", "spatial_cue"), ("lake", "GEONOUN", "entity"), ("farms", "GEONOUN", "entity"), ("slope", "GEONOUN", "entity")], None),
    ("holdout_015", "Vague destination", "We followed the stream upstream until we reached a clearing somewhere beyond the hill.", [("stream", "GEONOUN", "entity"), ("upstream", "DIRECTION", "spatial_cue"), ("reached", "MOVEMENT_CUE", "event_cue"), ("clearing", "GEONOUN", "entity"), ("beyond the hill", "SPATIAL_RELATION", "spatial_cue"), ("hill", "GEONOUN", "entity")], None),
    ("holdout_016", "Explicit train journey", "On Monday I took the train from Leeds to Manchester for a meeting.", [("On Monday", "TIME", "temporal_cue"), ("train", "TRANSPORT_CUE", "journey_cue"), ("Leeds", "TOPONYM", "entity"), ("Manchester", "TOPONYM", "entity")], {"start_location":"Leeds","end_location":"Manchester","transport_mode":"train","date":"On Monday","journey_reason":"for a meeting","evidence":"On Monday I took the train from Leeds to Manchester for a meeting.","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"explicit","date":"explicit","journey_reason":"explicit"}}),
    ("holdout_017", "Explicit bus journey", "We travelled by bus from Bristol to Bath to visit friends.", [("travelled", "MOVEMENT_CUE", "event_cue"), ("by bus", "TRANSPORT_CUE", "journey_cue"), ("Bristol", "TOPONYM", "entity"), ("Bath", "TOPONYM", "entity")], {"start_location":"Bristol","end_location":"Bath","transport_mode":"bus","date":None,"journey_reason":"to visit friends","evidence":"We travelled by bus from Bristol to Bath to visit friends.","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"explicit","date":"missing","journey_reason":"explicit"}}),
    ("holdout_018", "Explicit walking journey", "At dawn she walked from Ambleside to Rydal to deliver a letter.", [("At dawn", "TIME", "temporal_cue"), ("walked", "MOVEMENT_CUE", "event_cue"), ("Ambleside", "TOPONYM", "entity"), ("Rydal", "TOPONYM", "entity")], {"start_location":"Ambleside","end_location":"Rydal","transport_mode":"walking","date":"At dawn","journey_reason":"to deliver a letter","evidence":"At dawn she walked from Ambleside to Rydal to deliver a letter.","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"contextual_inference","date":"explicit","journey_reason":"explicit"}}),
    ("holdout_019", "Explicit sea journey", "In June they sailed from Liverpool to Belfast for work.", [("In June", "TIME", "temporal_cue"), ("sailed", "MOVEMENT_CUE", "event_cue"), ("Liverpool", "TOPONYM", "entity"), ("Belfast", "TOPONYM", "entity")], {"start_location":"Liverpool","end_location":"Belfast","transport_mode":"ship","date":"In June","journey_reason":"for work","evidence":"In June they sailed from Liverpool to Belfast for work.","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"contextual_inference","date":"explicit","journey_reason":"explicit"}}),
    ("holdout_020", "Explicit flight", "The next morning we flew from Nairobi to Kigali for the conference.", [("next morning", "TIME", "temporal_cue"), ("flew", "MOVEMENT_CUE", "event_cue"), ("Nairobi", "TOPONYM", "entity"), ("Kigali", "TOPONYM", "entity")], {"start_location":"Nairobi","end_location":"Kigali","transport_mode":"air","date":"The next morning","journey_reason":"for the conference","evidence":"The next morning we flew from Nairobi to Kigali for the conference.","statuses":{"start_location":"explicit","end_location":"explicit","transport_mode":"contextual_inference","date":"explicit","journey_reason":"explicit"}}),
    ("holdout_021", "Context-inherited origin", "I had been staying in Oxford for several weeks. From there I travelled to Reading by train.", [("Oxford", "TOPONYM", "entity"), ("several weeks", "TIME", "temporal_cue"), ("there", "DEICTIC_REFERENCE", "spatial_cue"), ("travelled", "MOVEMENT_CUE", "event_cue"), ("Reading", "TOPONYM", "entity"), ("by train", "TRANSPORT_CUE", "journey_cue")], {"start_location":"Oxford","end_location":"Reading","transport_mode":"train","date":None,"journey_reason":None,"evidence":"I had been staying in Oxford for several weeks. From there I travelled to Reading by train.","statuses":{"start_location":"contextual_inference","end_location":"explicit","transport_mode":"explicit","date":"missing","journey_reason":"missing"}}),
    ("holdout_022", "Question supplies time", "Q: Where did you go after graduation?\nA: I moved to Edinburgh and found a room near the university.", [("after graduation", "TIME", "temporal_cue"), ("moved", "MOVEMENT_CUE", "event_cue"), ("Edinburgh", "TOPONYM", "entity"), ("near", "SPATIAL_RELATION", "spatial_cue")], {"start_location":None,"end_location":"Edinburgh","transport_mode":None,"date":"after graduation","journey_reason":None,"evidence":"Q: Where did you go after graduation?\nA: I moved to Edinburgh","statuses":{"start_location":"missing","end_location":"explicit","transport_mode":"missing","date":"contextual_inference","journey_reason":"missing"}}),
    ("holdout_023", "Pronoun destination continuation", "We reached Dover late in the evening. The next day we crossed to Calais by ferry.", [("Dover", "TOPONYM", "entity"), ("late in the evening", "TIME", "temporal_cue"), ("next day", "TIME", "temporal_cue"), ("crossed", "MOVEMENT_CUE", "event_cue"), ("Calais", "TOPONYM", "entity"), ("by ferry", "TRANSPORT_CUE", "journey_cue")], {"start_location":"Dover","end_location":"Calais","transport_mode":"ferry","date":"The next day","journey_reason":None,"evidence":"We reached Dover late in the evening. The next day we crossed to Calais by ferry.","statuses":{"start_location":"contextual_inference","end_location":"explicit","transport_mode":"explicit","date":"explicit","journey_reason":"missing"}}),
    ("holdout_024", "Implied relocation", "My parents lived in Cardiff. When the new job began, we settled in Swansea.", [("Cardiff", "TOPONYM", "entity"), ("When the new job began", "TIME", "temporal_cue"), ("settled", "MOVEMENT_CUE", "event_cue"), ("Swansea", "TOPONYM", "entity")], {"start_location":"Cardiff","end_location":"Swansea","transport_mode":None,"date":"When the new job began","journey_reason":"new job","evidence":"My parents lived in Cardiff. When the new job began, we settled in Swansea.","statuses":{"start_location":"contextual_inference","end_location":"explicit","transport_mode":"missing","date":"explicit","journey_reason":"contextual_inference"}}),
    ("holdout_025", "Destination explicit origin missing", "By winter I had arrived in Glasgow, though I never wrote down where the journey began.", [("By winter", "TIME", "temporal_cue"), ("arrived", "MOVEMENT_CUE", "event_cue"), ("Glasgow", "TOPONYM", "entity")], {"start_location":None,"end_location":"Glasgow","transport_mode":None,"date":"By winter","journey_reason":None,"evidence":"By winter I had arrived in Glasgow","statuses":{"start_location":"missing","end_location":"explicit","transport_mode":"missing","date":"explicit","journey_reason":"missing"}}),
    ("holdout_026", "Sensory lakeside", "Windermere felt unusually quiet that morning, and the wet stone path smelled of rain.", [("Windermere", "TOPONYM", "entity"), ("quiet", "SUBJECTIVE_DESCRIPTOR", "sense_of_place"), ("that morning", "TIME", "temporal_cue"), ("path", "GEONOUN", "entity"), ("smelled of rain", "SENSORY_DESCRIPTOR", "sense_of_place")], None),
    ("holdout_027", "Subjective city edge", "At the edge of Sheffield the streets seemed narrower and the hills suddenly closer.", [("edge of Sheffield", "SPATIAL_RELATION", "spatial_cue"), ("Sheffield", "TOPONYM", "entity"), ("streets", "GEONOUN", "entity"), ("narrower", "SUBJECTIVE_DESCRIPTOR", "sense_of_place"), ("hills", "GEONOUN", "entity"), ("closer", "DISTANCE", "spatial_cue")], None),
    ("holdout_028", "Memory and coast", "I remember the coast near Brighton as bright, windy and open.", [("coast", "GEONOUN", "entity"), ("near", "SPATIAL_RELATION", "spatial_cue"), ("Brighton", "TOPONYM", "entity"), ("bright", "SUBJECTIVE_DESCRIPTOR", "sense_of_place"), ("windy", "SENSORY_DESCRIPTOR", "sense_of_place"), ("open", "SUBJECTIVE_DESCRIPTOR", "sense_of_place")], None),
    ("holdout_029", "Temporal-spatial sequence", "Before sunrise we waited beside the station; an hour later we were already outside Cambridge.", [("Before sunrise", "TIME", "temporal_cue"), ("beside", "SPATIAL_RELATION", "spatial_cue"), ("station", "GEONOUN", "entity"), ("an hour later", "TIME", "temporal_cue"), ("outside Cambridge", "SPATIAL_RELATION", "spatial_cue"), ("Cambridge", "TOPONYM", "entity")], None),
    ("holdout_030", "Mixed explicit and vague spatial evidence", "The road from Keswick climbed east for three miles, then narrowed somewhere below the pass.", [("road", "GEONOUN", "entity"), ("Keswick", "TOPONYM", "entity"), ("east", "DIRECTION", "spatial_cue"), ("three miles", "DISTANCE", "spatial_cue"), ("below the pass", "SPATIAL_RELATION", "spatial_cue"), ("pass", "GEONOUN", "entity")], None),
]


def _span(text, phrase, label, layer, sid):
    start = text.find(phrase)
    if start < 0:
        raise ValueError(f"Could not locate {phrase!r}")
    return {
        "span_id": sid,
        "layer": layer,
        "label": label,
        "text": phrase,
        "start_char": start,
        "end_char": start + len(phrase),
        "conceptual_level": "location" if label == "TOPONYM" else "locale" if label == "GEONOUN" else "sense_of_place" if label in {"SUBJECTIVE_DESCRIPTOR", "SENSORY_DESCRIPTOR"} else None,
        "certainty": "contextual_inference" if label == "DEICTIC_REFERENCE" else "explicit",
        "attributes": {},
        "notes": None,
    }


def _record(spec):
    eid, title, text, span_specs, journey = spec
    spans = [_span(text, phrase, label, layer, f"s{i:03d}") for i, (phrase, label, layer) in enumerate(span_specs, 1)]
    journeys = []
    if journey:
        quote = journey["evidence"]
        start = text.find(quote)
        if start < 0:
            raise ValueError(f"{eid}: evidence quote not found")
        statuses = journey["statuses"]
        review = any(v == "contextual_inference" for v in statuses.values()) or eid in {"holdout_006", "holdout_007", "holdout_008", "holdout_009"}
        journeys.append({
            "journeyId": f"{eid}-j0001",
            "fileId": eid,
            "segId": 1,
            "start_location": journey["start_location"],
            "end_location": journey["end_location"],
            "transport_mode": journey["transport_mode"],
            "date": journey["date"],
            "journey_reason": journey["journey_reason"],
            "evidence_quote": quote,
            "evidence_start_char": start,
            "evidence_end_char": start + len(quote),
            "explicit_or_inferred": statuses,
            "confidence": None,
            "model": "human_reference",
            "provider": "human",
            "requires_review": review,
            "review_notes": ["At least one structured field depends on contextual inference or resolution ambiguity."] if review else [],
            "human_status": "accepted",
            "human_edits": [],
        })
    return {
        "schema_version": "spatio-textual-gold-0.1",
        "example_id": eid,
        "title": title,
        "text": text,
        "source": {
            "genre": "synthetic benchmark narrative",
            "source_note": "Instructor-authored synthetic SH2026 held-out benchmark example; created for evaluation and safe to distribute.",
            "distribution_status": "safe_to_distribute",
        },
        "annotation_policy": "docs/GOLD_ANNOTATION_GUIDE.md",
        "reference_status": "adjudicated_reference",
        "spans": spans,
        "relations": [],
        "journeys": journeys,
        "adjudication_notes": ["Frozen before formal benchmark execution; do not use this record for prompt/rule tuning after freeze."],
    }


def main():
    records = [_record(spec) for spec in SPECS]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    content = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in records)
    OUT.write_text(content, encoding="utf-8")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    print(f"Wrote {len(records)} records to {OUT}")
    print(f"SHA256 {digest}")


if __name__ == "__main__":
    main()
