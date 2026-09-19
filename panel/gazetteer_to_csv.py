#!/usr/bin/env python3
"""
gazetteer_to_csv.py
-------------------
Emit the sanitized gazetteer in the CSV form RuleGazetteerAnnotator reads.

    python3 gazetteer_to_csv.py --resources resources_v2/resources.json \
        --out gazetteer_rules.csv

Schema matches data/teaching_gazetteer.csv exactly:

    text, label, conceptual_level, note

`conceptual_level` comes from the label, following the workshop's own three-layer
vocabulary: TOPONYM is a `location` (may carry a coordinate), GEONOUN is a
`locale` (a setting, usually a common noun).

`note` carries the provenance the flat JSON drops: which source layer the term
came from, its matching rule, and whether it is curated or a generated inflection.
That matters because a reviewer asking "why is `bar` in your gazetteer?" should be
able to answer it from the artefact rather than from memory.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

LEVEL = {"TOPONYM": "location", "GEONOUN": "locale",
         "RELATION": "relation", "DISTANCE": "distance", "TIME": "time"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resources", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=Path("gazetteer_rules.csv"))
    ap.add_argument("--no-generated", action="store_true",
                    help="curated terms only; excludes machine-made inflections "
                         "so their contribution can be measured separately")
    a = ap.parse_args()

    bundle = json.load(open(a.resources, encoding="utf-8"))
    rows: list[dict] = []
    seen: set[str] = set()

    for layer, spec in bundle["layers"].items():
        label = spec.get("panel_label")
        if not label:
            continue                      # affect lexicons, transcription markers
        match = spec.get("match", "case_sensitive")
        for term in spec.get("terms", []):
            if term.lower() in seen:
                continue
            seen.add(term.lower())
            rows.append({"text": term, "label": label,
                         "conceptual_level": LEVEL.get(label, "location"),
                         "note": f"{layer}; {match}; curated"})
        if a.no_generated:
            continue
        for term in spec.get("generated_forms", []):
            if term.lower() in seen:
                continue
            seen.add(term.lower())
            rows.append({"text": term, "label": label,
                         "conceptual_level": LEVEL.get(label, "location"),
                         "note": f"{layer}; {match}; generated inflection"})

    rows.sort(key=lambda r: (r["label"], r["text"].lower()))
    with a.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "label", "conceptual_level", "note"])
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    print(f"wrote {a.out}: {len(rows)} rows")
    for k, v in sorted(Counter(r["label"] for r in rows).items()):
        print(f"  {k:10s} {v}")
    gen = sum(1 for r in rows if "generated" in r["note"])
    print(f"  of which generated inflections: {gen}")
    print("\nNOTE: this CSV is flat, so per-layer case rules are recorded in the "
          "`note`\ncolumn but NOT enforced by it. If RuleGazetteerAnnotator "
          "matches case-sensitively\nthroughout, geonouns will miss 'Sea' and "
          "'the Inn' at sentence start. Check with:\n"
          "  python3 -c \"from spatio_textual.rules import RuleGazetteerAnnotator; "
          "import inspect; print(inspect.signature(RuleGazetteerAnnotator.__init__))\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
