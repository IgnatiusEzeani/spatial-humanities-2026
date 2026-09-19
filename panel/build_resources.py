#!/usr/bin/env python3
"""
build_resources.py
------------------
Sanitize the loose .txt resource lists into one versioned, documented bundle.

    python3 build_resources.py --src resources/ --out-dir resources_v1/

Produces:
    resources_v1/resources.json          every layer, with provenance and licence
    resources_v1/gazetteer_hybrid.json   flat {surface: LABEL} for the panel voter
    resources_v1/RESOURCES.md            human-readable manifest
    resources_v1/CITATION.md             third-party attribution

Why not just load the .txt files
--------------------------------
Three reasons, all of which bite later rather than now.

1. ATTRIBUTION IS IN A COMMENT. positive-words.txt and negative-words.txt are
   the Hu & Liu Opinion Lexicon. Their only licence statement is a ';' header
   that every naive loader discards, so the obligation silently disappears the
   first time someone writes `[l.strip() for l in open(f)]`. Here it becomes
   structured metadata that travels with the data.

2. A BARE WORD LIST HAS NO LAYER. "Amsterdam" in ambiguous_cities and
   "Auschwitz" in cleaned_holocaust_camps are both TOPONYM but mean different
   things to the pipeline: one is a disambiguation warning, the other a
   domain entity. Flattening them loses that.

3. MATCHING RULES DIFFER PER LAYER. Geonouns must match case-insensitively and
   need inflected forms ("road" must also catch "roads", the failure the
   workshop is built around). Place names must match case-sensitively, or
   every sentence beginning "March..." becomes a toponym. Encoding that per
   layer stops it being re-derived, differently, in each script.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

# Layer definitions. `panel_label` is None for layers that are not span
# annotations in the panel's inventory: they feed other stages.
LAYERS: dict[str, dict] = {
    "ambiguous_cities": {
        "file": ["ambiguous_cities.txt"],
        "panel_label": "TOPONYM",
        "role": "disambiguation_warning",
        "match": "case_sensitive",
        "inflect": False,
        "description": "Place names with more than one well-known referent. A "
                       "hit is a signal to withhold a coordinate, not to assign "
                       "one. See the Cambridge slide.",
        "provenance": "project-curated",
        "licence": "project",
    },
    "holocaust_camps": {
        "file": ["cleaned_holocaust_camps.txt"],
        "panel_label": "TOPONYM",
        "role": "domain_entity",
        "match": "case_sensitive",
        "inflect": False,
        "description": "Camp and killing-site names appearing in testimony.",
        "provenance": "project-curated",
        "licence": "project",
        "handling": "Names only. No victim, survivor or location-of-death data. "
                    "Safe to publish.",
    },
    "geonouns": {
        "file": ["combined_geonouns.txt"],
        "panel_label": "GEONOUN",
        "role": "feature_type",
        "match": "case_insensitive",
        "inflect": True,
        "description": "Common nouns denoting geographical or built features. "
                       "Unnamed geography: the layer a toponym list cannot hold.",
        "provenance": "project-curated",
        "licence": "project",
    },
    "family_terms": {
        "file": ["family_relationships.txt", "family_terms.txt"],
        "panel_label": None,
        "role": "relation_cue",
        "match": "case_insensitive",
        "inflect": True,
        "description": "Kinship terms. Tier 3 (family relations), deferred: "
                       "relation-level adjudication is out of scope for now.",
        "provenance": "project-curated",
        "licence": "project",
    },
    "non_verbals": {
        "file": ["ht_non_verbals.txt", "non_verbals.txt"],
        "also": ["non-english-expressions.txt"],
        "panel_label": None,
        "role": "transcription_artefact",
        "match": "case_sensitive",
        "inflect": False,
        "description": "Interview transcription markers. Used at SEGMENTATION, "
                       "not annotation: these must not be inside an evidence "
                       "quote, and a span that contains one is suspect.",
        "provenance": "project-curated",
        "licence": "project",
    },
    "sentiment_positive": {
        "file": ["positive-words.txt"],
        "panel_label": None,
        "role": "affect_lexicon",
        "match": "case_insensitive",
        "inflect": False,
        "description": "Positive opinion words. Tier 2 (affect), reported as "
                       "inter-model agreement, never as accuracy.",
        "provenance": "Hu & Liu Opinion Lexicon",
        "licence": "third_party_cite_required",
        "citation": "Minqing Hu and Bing Liu. Mining and Summarizing Customer "
                    "Reviews. KDD 2004. Lexicon: "
                    "https://www.cs.uic.edu/~liub/FBS/sentiment-analysis.html",
    },
    "sentiment_negative": {
        "file": ["negative-words.txt"],
        "panel_label": None,
        "role": "affect_lexicon",
        "match": "case_insensitive",
        "inflect": False,
        "description": "Negative opinion words. Tier 2 (affect).",
        "provenance": "Hu & Liu Opinion Lexicon",
        "licence": "third_party_cite_required",
        "citation": "Minqing Hu and Bing Liu. Mining and Summarizing Customer "
                    "Reviews. KDD 2004. Lexicon: "
                    "https://www.cs.uic.edu/~liub/FBS/sentiment-analysis.html",
    },
}


COUNTED = re.compile(r"^(?P<term>.+?)\s*:\s*(?P<count>[\d,]+)\s*,?\s*$")


def read_list(path: Path) -> tuple[list[str], dict]:
    """Strip ';' comments, BOMs, CRLF, blanks; dedupe case-insensitively.

    Also parses the "TAG: 44884" frequency format used by
    non-english-expressions.txt, keeping the counts as metadata. Corpus
    frequency is useful: a marker seen 44,884 times deserves different handling
    from one seen once, and one seen once is often a transcription one-off
    rather than a convention.
    """
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    raw = text.split("\n")
    seen: dict[str, str] = {}
    notes = {"raw_lines": len(raw), "comment_lines": 0, "blank": 0,
             "duplicates": 0, "repaired": 0, "suspicious": [], "counts": {}}
    for line in raw:
        if line.lstrip().startswith(";"):
            notes["comment_lines"] += 1
            continue
        s = line.strip()
        if not s:
            notes["blank"] += 1
            continue
        cleaned = re.sub(r"\s+", " ", s)
        m = COUNTED.match(cleaned)
        if m:
            cleaned = m.group("term").strip()
            try:
                notes["counts"][cleaned] = int(m.group("count").replace(",", ""))
            except ValueError:
                pass
        if cleaned != s:
            notes["repaired"] += 1
        # flag rather than silently drop: a single character or a digit-only
        # entry in a gazetteer matches everywhere and ruins precision
        if len(cleaned) < 2 or cleaned.isdigit():
            notes["suspicious"].append(cleaned)
            continue
        key = cleaned.lower()
        if key in seen:
            notes["duplicates"] += 1
            continue
        seen[key] = cleaned
    return list(seen.values()), notes


def inflect(term: str) -> list[str]:
    """Minimal English plurals for common nouns.

    This exists because of the road/roads failure in workshop notebook 02: one
    inflected form absent from one list and the geography of the sentence
    disappears. Generated forms are marked so they can be excluded if a
    reviewer objects to them.
    """
    t = term.lower()
    out = {t}
    if t.endswith("y") and len(t) > 2 and t[-2] not in "aeiou":
        out.add(t[:-1] + "ies")
    elif t.endswith(("s", "x", "z", "ch", "sh")):
        out.add(t + "es")
    else:
        out.add(t + "s")
    return sorted(out - {t})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("resources_v1"))
    ap.add_argument("--version", default="v1.0")
    a = ap.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)

    bundle: dict = {"version": a.version, "built": date.today().isoformat(),
                    "layers": {}}
    gazetteer: dict[str, str] = {}
    generated: dict[str, str] = {}
    # Per-layer matching rules must survive into the artefact. A single flat map
    # forces one case policy for everything, which silently loses "Sea" and
    # "the Inn" at sentence start while a case-insensitive toponym list would
    # turn every sentence beginning "March..." into a place.
    layered: dict[str, dict[str, str]] = {"case_sensitive": {},
                                          "case_insensitive": {}}
    problems: list[str] = []

    print(f"{'layer':22s} {'entries':>8s} {'+inflect':>9s} {'dropped':>8s}  notes")
    for name, spec in LAYERS.items():
        candidates = [a.src / f for f in spec["file"]] + \
                     [a.src / f for f in spec.get("also", [])]
        found = [p for p in candidates if p.exists()]
        if not found:
            problems.append(f"absent from this upload: {' / '.join(spec['file'])}")
            print(f"{name:22s} {'ABSENT':>8s}")
            continue
        terms, notes = [], {"raw_lines": 0, "comment_lines": 0, "blank": 0,
                            "duplicates": 0, "repaired": 0, "suspicious": [],
                            "counts": {}, "files": [p.name for p in found]}
        seen_l: set[str] = set()
        for p in found:
            t, n = read_list(p)
            for k in ("raw_lines", "comment_lines", "blank", "duplicates",
                      "repaired"):
                notes[k] += n[k]
            notes["suspicious"] += n["suspicious"]
            notes["counts"].update(n["counts"])
            for x in t:
                if x.lower() in seen_l:
                    notes["duplicates"] += 1
                    continue
                seen_l.add(x.lower())
                terms.append(x)
        extra: list[str] = []
        if spec["inflect"]:
            for t in terms:
                extra.extend(x for x in inflect(t) if x not in {y.lower() for y in terms})
            extra = sorted(set(extra))

        # A gazetteer term that is not actually a geographical feature fires on
        # every occurrence and costs precision everywhere. 2,234 entries is large
        # enough that hand-checking is impractical, so flag the classes most
        # likely to be wrong and let a human confirm rather than silently trust.
        risky: list[str] = []
        if spec["panel_label"] == "GEONOUN":
            # A bare -er/-or suffix rule flagged amphitheater, aquifer, chamber,
            # corridor and cloister, all of which are legitimate features. Use
            # reliably person-forming suffixes only, plus an explicit denylist,
            # so the review file stays short enough that someone reads it.
            PERSON = re.compile(r"(keeper|wright|smith|monger|maker|ist|man|men)$",
                                re.I)
            DENY = {"roofer", "broom", "cathouse", "second-floor", "plumber",
                    "glazier", "joiner", "mason", "carpenter", "tiler"}
            for t in terms:
                low = t.lower()
                if len(t) <= 3:
                    # NOT a substring problem: the voter matches on word
                    # boundaries, so "bay" cannot fire inside "Bombay". The risk
                    # is POLYSEMY, which no matching rule fixes: "a bar of soap",
                    # "the tip of the iceberg", "a gap in the record".
                    risky.append(f"{t} (short and polysemous: has common "
                                 f"non-geographic senses)")
                elif low in DENY:
                    risky.append(f"{t} (not a geographical feature)")
                elif PERSON.search(low) and " " not in t:
                    risky.append(f"{t} (person-forming suffix: check)")
            if risky:
                (a.out_dir / f"REVIEW_{name}.txt").write_text(
                    "Terms in this layer that may cost precision.\n\n"
                    "Matching is on WORD BOUNDARIES, so these do not fire inside\n"
                    "longer words: 'bay' will not match 'Bombay'. The risk is\n"
                    "polysemy, which no matching rule fixes: 'a bar of soap',\n"
                    "'the tip of the iceberg', 'a gap in the record'.\n\n"
                    "Delete the wrong ones from the source list and rebuild.\n\n"
                    + "\n".join(sorted(risky)) + "\n")

        bundle["layers"][name] = {k: v for k, v in spec.items() if k != "file"}
        bundle["layers"][name].update({
            "source_files": notes.get("files", spec["file"]),
            "needs_review": len(risky) if spec["panel_label"] == "GEONOUN" else 0,
            "n_terms": len(terms),
            "n_generated": len(extra),
            "terms": sorted(terms),
            "generated_forms": extra,
            "sanitisation": notes,
        })

        if spec["panel_label"]:
            mode = spec["match"]
            for t in terms:
                gazetteer[t] = spec["panel_label"]
                layered[mode][t] = spec["panel_label"]
            for t in extra:
                generated[t] = spec["panel_label"]
                layered[mode][t] = spec["panel_label"]

        drop = len(notes["suspicious"]) + notes["duplicates"]
        note = []
        if risky:
            note.append(f"{len(risky)} need review -> REVIEW_{name}.txt")
        if notes["counts"]:
            note.append(f"{len(notes['counts'])} with corpus frequencies")
        if notes["comment_lines"]:
            note.append(f"{notes['comment_lines']} comment lines stripped")
        if notes["suspicious"]:
            note.append(f"suspicious: {notes['suspicious'][:3]}")
        if spec["licence"] == "third_party_cite_required":
            note.append("THIRD PARTY, citation required")
        print(f"{name:22s} {len(terms):8d} {len(extra):9d} {drop:8d}  "
              + "; ".join(note))

    # the hybrid voter consumes one flat map; generated forms kept separate so
    # the effect of inflection can be measured rather than assumed
    (a.out_dir / "gazetteer_hybrid.json").write_text(
        json.dumps({**gazetteer, **generated}, indent=2, ensure_ascii=False))
    (a.out_dir / "gazetteer_hybrid_curated_only.json").write_text(
        json.dumps(gazetteer, indent=2, ensure_ascii=False))
    (a.out_dir / "gazetteer_layered.json").write_text(
        json.dumps(layered, indent=2, ensure_ascii=False))
    (a.out_dir / "resources.json").write_text(
        json.dumps(bundle, indent=2, ensure_ascii=False))

    cites = {n: s for n, s in LAYERS.items()
             if s.get("licence") == "third_party_cite_required"}
    (a.out_dir / "CITATION.md").write_text(
        "# Third-party resources\n\n"
        "These layers are not project-created. Cite them wherever the pipeline "
        "that uses them is described, including slides.\n\n"
        + "\n\n".join(f"## {n}\n\n{s['citation']}" for n, s in cites.items())
        + "\n")

    lines = [f"# Project resources {a.version}", "",
             f"Built {date.today().isoformat()} by `build_resources.py` from "
             f"`{a.src}`.", "",
             "| layer | panel label | role | match | entries | generated | licence |",
             "|---|---|---|---|---|---|---|"]
    for n, d in bundle["layers"].items():
        lines.append(f"| {n} | {d['panel_label'] or '-'} | {d['role']} | "
                     f"{d['match']} | {d['n_terms']} | {d['n_generated']} | "
                     f"{d['licence']} |")
    lines += ["", "## Notes", "",
              "* `gazetteer_hybrid.json` is the flat map the panel's hybrid "
              "voter consumes. It contains ONLY layers with a panel label.",
              "* `gazetteer_hybrid_curated_only.json` excludes machine-generated "
              "inflected forms, so their contribution can be measured.",
              "* Inflected forms exist because of the road/roads failure: one "
              "missing form removes the geography of a sentence.",
              "* `gazetteer_layered.json` preserves per-layer case rules. Prefer "
              "it over the flat map: toponyms must match case-sensitively, "
              "geonouns must not.",
              "* Ambiguous cities are a warning layer. A hit should withhold a "
              "coordinate, not assign one.",
              "* No victim, survivor or personal data appears in any layer."]
    (a.out_dir / "RESOURCES.md").write_text("\n".join(lines) + "\n")

    print(f"\n{len(gazetteer)} curated + {len(generated)} generated terms "
          f"-> {a.out_dir}/gazetteer_hybrid.json")
    print(f"wrote resources.json, RESOURCES.md, CITATION.md")
    for p in problems:
        print(f"  ! {p}")

    covered = {t.lower() for t in gazetteer}
    if not any(t in covered for t in
               ("keswick", "helvellyn", "borrowdale", "windermere", "grasmere")):
        print("\n  ! NO LAKE DISTRICT PLACE NAMES in this gazetteer. It is a "
              "testimony-side\n    resource. Attached to the hybrid voter for "
              "the LD80 run it will contribute\n    the geonoun layer and four "
              "city names, and nothing else. See the note in\n    RESOURCES.md "
              "about building a held-out Lake District gazetteer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
