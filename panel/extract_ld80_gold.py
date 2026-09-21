#!/usr/bin/env python3
"""
extract_ld80_gold.py
--------------------
Turn the LD80 gold standard into panel-ready passages WITH gold annotations.

    python3 extract_ld80_gold.py --gold-dir "LD80 gold_standard" \
        --out ld80_passages.jsonl --n 300

Why this changes the plan
-------------------------
The gold standard carries 7,712 human-annotated <cdplace> spans across 28 Lake
District texts, 1724 to 1904. The previous CLDW evidence base was 43 spans in 10
purposively chosen passages. This is roughly 180x more gold, it is human, and it
was made independently of any model on the panel.

So for the TOPONYM layer on historical prose there is NO ADJUDICATION TO DO. You
score straight against gold, with bootstrap intervals that will be narrow enough
to support a ranking claim. Your adjudication time goes entirely to the layers
the gold standard does not cover.

What the gold standard does and does not cover
----------------------------------------------
  covered      <cdplace>    place names            -> TOPONYM
               <cdperson>   personal names         -> (not a panel layer)
               <cdpubplace> place of publication   -> EXCLUDED, it is bibliographic
               <cdtitle>    work titles            -> EXCLUDED
  NOT covered  GEONOUN, RELATION, DISTANCE, TIME

This asymmetry is a finding, not an inconvenience, and it belongs on a slide: the
existing gold standard encodes exactly the layer that a place-name list can hold,
which is the argument the keynote opens with.

Offsets
-------
Every span carries offsets into BOTH the cleaned passage text and the original
file, so any annotation is recoverable to the exact characters on disk without
re-running this script's cleaning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import html as _html
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Elements whose CONTENT is not running prose. Removed wholesale.
DROP = ("note", "ed_comment", "gap", "ptr", "cdpubplace", "cdtitle", "cdpbt")
# Elements that are pure formatting: tags removed, text kept.
TRANSPARENT = ("i", "b", "sub", "sup", "hi", "line", "lb", "pb", "p", "head",
               "chap", "poem", "stanza", "table", "tr", "td", "text",
               "sub_section", "person", "cdperson", "inn", "day", "date",
               "start_place", "end_place", "title", "format")
# The gold layer.
GOLD = "cdplace"

# ---------------------------------------------------------------------------
# Periodisation comes from the corpus manifest, NOT from <text id>.
#
# <text id> is a corpus identifier that usually looks like a year and sometimes
# is not one. Deriving periods from it is wrong in ways that are invisible until
# you check:
#
#   Ruskin_cqp_55      id=1969_a   Year_Comp 1830, Romantic Era
#                                  (1969 is a Frank Graham reprint. I guessed
#                                  1869 from the id and was 39 years out.)
#   Lt.Hammond._cqp_2  id=1904_a   Year_Comp 1634, Early-Modern Era
#                                  (id-derived periodisation is 270 years out)
#   Wilberforce        id=1983_a   Long Eighteenth Century
#   Gell               id=1968_a   Long Eighteenth Century
#
# The join key is the Filename column, which matches the XML stem exactly for
# all 28 gold files. Pass --manifest and this whole class of error disappears.
# ---------------------------------------------------------------------------

PERIOD_SLUG = {
    "Early-Modern Era": "early_modern",
    "Long Eighteenth Century": "long_18c",
    "Romantic Era": "romantic",
    "Regency and Romantic Era": "regency_romantic",
    "Victorian Era": "victorian",
}


def load_manifest(path: Path) -> dict[str, dict]:
    """Manifest_-_updated.csv keyed by Filename (the XML stem)."""
    import csv as _csv
    out: dict[str, dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        for row in _csv.DictReader(f):
            key = (row.get("Filename") or "").strip()
            if not key:
                continue
            out[key] = {
                "id": (row.get("ID") or "").strip(),
                "author": (row.get("Author") or "").strip(),
                "title": (row.get("Title") or "").strip(),
                "period_raw": (row.get("Period") or "").strip(),
                "period": PERIOD_SLUG.get((row.get("Period") or "").strip(), "unknown"),
                "genre": (row.get("Genre") or "").strip(),
                "year_pub": (row.get("Pub_date") or "").strip(),
                "gender": (row.get("Gender") or "").strip(),
                "nationality": (row.get("Nationality") or "").strip(),
            }
    return out


def load_year_comp(path: Path) -> dict[str, str]:
    """Year_Comp from Full_LD_metadata.xlsx, keyed by ID. Optional."""
    try:
        import pandas as pd
    except ImportError:
        print("  (pandas not installed: skipping Year_Comp from the spreadsheet)")
        return {}
    df = pd.read_excel(path, "Full metadata")
    return {str(r["ID"]).strip(): str(r["Year_Comp"]).strip()
            for _, r in df.iterrows()
            if str(r.get("ID", "")).strip() and str(r.get("Year_Comp", "")).strip()
            not in ("", "nan", "No Data")}

_TAG = re.compile(r"<\s*(/?)\s*([A-Za-z][\w:.-]*)([^>]*?)(/?)\s*>", re.S)
_ENTITY = re.compile(r"&(#\d+|#[xX][0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]*);")

# The corpus encodes the long s THREE ways, and two of them are the integral
# sign standing in for it (a transcription convention, not a real character).
# Fold them onto U+017F so the text is at least internally consistent.
LONG_S_ARTEFACTS = {"\u222b": "\u017f", "\u2320": "\u017f", "\u2321": "\u017f"}


def decode_entity(token: str) -> str:
    """&#383; -> 'ſ'.  Undecoded entities reach the models as literal
    '&#383;' strings, which corrupts both the input and every gold span."""
    out = _html.unescape(token)
    return LONG_S_ARTEFACTS.get(out, out)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_SPLIT = re.compile(
    r"(?<!\bMr)(?<!\bMrs)(?<!\bDr)(?<!\bSt)(?<!\bRev)(?<!\bCapt)(?<!\bNo)"
    r"(?<!\bvol)(?<!\bp)(?<!\bfig)(?<=[.!?])[\"')\]]?\s+(?=[A-Z\"'(\[])")


def parse_file(path: Path, long_s: str = "keep"
               ) -> tuple[str, list[int], list[dict], str | None, dict]:
    """Return (clean_text, offmap, gold_spans, year).

    Single pass. Comments and DROP elements are blanked in place so raw offsets
    stay valid; TRANSPARENT tags vanish but their text is kept; cdplace open and
    close positions are recorded against the CLEANED text as it is built.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")

    m = re.search(r'<text\s+id="([^"]+)"', raw)
    text_id = m.group(1) if m else None

    # blank comments, preserving length
    work = _COMMENT.sub(lambda m: " " * (m.end() - m.start()), raw)
    # blank DROP elements, preserving length
    for el in DROP:
        work = re.sub(rf"<\s*{el}\b[^>]*?/\s*>", lambda m: " " * len(m.group(0)), work, flags=re.I)
        work = re.sub(rf"<\s*{el}\b[^>]*>.*?<\s*/\s*{el}\s*>",
                      lambda m: " " * len(m.group(0)), work, flags=re.S | re.I)

    out: list[str] = []
    offmap: list[int] = []
    spans: list[dict] = []
    stats = {"entities": 0}
    open_stack: list[tuple[int, str]] = []
    last_space = False
    pos = 0

    def emit(ch: str, raw_i: int) -> None:
        nonlocal last_space
        if long_s == "normalise" and ch == "\u017f":
            ch = "s"
        if ch.isspace():
            if not last_space:
                out.append(" "); offmap.append(raw_i); last_space = True
        else:
            # a tag between a word and its punctuation leaves "Keswick ,"
            if last_space and ch in ",.;:!?)]}’”" and out and out[-1] == " ":
                out.pop(); offmap.pop()
            out.append(ch); offmap.append(raw_i); last_space = False

    def emit_region(lo: int, hi: int) -> None:
        """Emit raw[lo:hi], decoding entities. Every character produced by an
        entity maps back to the entity's START offset, so raw offsets stay
        valid even though lengths change."""
        i = lo
        while i < hi:
            if work[i] == "&":
                m2 = _ENTITY.match(work, i)
                if m2 and m2.end() <= hi:
                    for c in decode_entity(m2.group(0)):
                        emit(c, i)
                    stats["entities"] += 1
                    i = m2.end()
                    continue
            emit(work[i], i)
            i += 1

    for m in _TAG.finditer(work):
        emit_region(pos, m.start())
        closing, name, attrs, selfclose = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if name == GOLD and not selfclose:
            if closing:
                if open_stack and open_stack[-1][0] is not None:
                    start, at = open_stack.pop()
                    end = len(out)
                    text = "".join(out[start:end]).strip()
                    if text and text not in ("??", "?"):
                        lead = len("".join(out[start:end])) - len("".join(out[start:end]).lstrip())
                        spans.append({
                            "clean_start": start + lead,
                            "clean_end": start + lead + len(text),
                            "text": text, "label": "TOPONYM",
                            "attrs": dict(re.findall(r'([a-zA-Z_]+)\s*=\s*"([^"]*)"', at)),
                        })
            else:
                open_stack.append((len(out), attrs))
        pos = m.end()
    emit_region(pos, len(work))

    clean = "".join(out)
    for s in spans:                      # attach raw offsets
        a, b = s["clean_start"], s["clean_end"]
        if a < len(offmap) and b - 1 < len(offmap):
            s["raw_start"], s["raw_end"] = offmap[a], offmap[b - 1] + 1
    return clean, offmap, spans, text_id, stats


def sentences(text: str) -> list[tuple[int, int]]:
    out, prev = [], 0
    for m in _SPLIT.finditer(text):
        out.append((prev, m.start() + 1))
        prev = m.end()
    if prev < len(text):
        out.append((prev, len(text)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-dir", type=Path, required=True)
    ap.add_argument("--manifest", type=Path,
                    help="Manifest_-_updated.csv. Strongly recommended: without it "
                         "periodisation falls back to <text id>, which is wrong for "
                         "every reprint in the corpus.")
    ap.add_argument("--metadata", type=Path,
                    help="Full_LD_metadata.xlsx, for Year_Comp (optional)")
    ap.add_argument("--out", type=Path, default=Path("ld80_passages.jsonl"))
    ap.add_argument("--n", type=int, default=0, help="0 = keep all passages")
    ap.add_argument("--min-len", type=int, default=45)
    ap.add_argument("--max-len", type=int, default=420)
    ap.add_argument("--negative-frac", type=float, default=0.15)
    ap.add_argument("--long-s", choices=("keep", "normalise"), default="keep",
                    help="keep: leave ſ as ſ (tests historical orthography, which "
                         "is the point). normalise: fold ſ to s (easier for every "
                         "model). Run BOTH and report the gap; it isolates the "
                         "orthography effect for free.")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()

    rng = random.Random(a.seed)
    manifest = load_manifest(a.manifest) if a.manifest else {}
    year_comp = load_year_comp(a.metadata) if a.metadata else {}
    if not manifest:
        print("  ! no --manifest supplied. Periodisation will be 'unknown' for "
              "every file. Supply it.")
    rows: list[dict] = []
    per_file: list[tuple[str, int, int, int]] = []
    dropped_unrecoverable = 0

    unmatched: list[str] = []
    n_entities = 0
    for path in sorted(a.gold_dir.glob("*.xml")):
        clean, offmap, gold, text_id, st = parse_file(path, a.long_s)
        n_entities += st["entities"]
        meta = manifest.get(path.stem)
        if meta is None:
            unmatched.append(path.stem)
            meta = {"id": text_id or "", "author": "", "title": "",
                    "period": "unknown", "period_raw": "", "genre": "unknown",
                    "year_pub": "", "gender": "", "nationality": ""}
        yc = year_comp.get(meta["id"], "")
        kept = 0
        for start, end in sentences(clean):
            s = clean[start:end].strip()
            if not (a.min_len <= len(s) <= a.max_len):
                continue
            if sum(c.isalpha() for c in s) / max(len(s), 1) < 0.6:
                continue
            lead = len(clean[start:end]) - len(clean[start:end].lstrip())
            lo, hi = start + lead, start + lead + len(s)
            inside = [g for g in gold if g["clean_start"] >= lo and g["clean_end"] <= hi]
            local = []
            ok = True
            for g in inside:
                ls, le = g["clean_start"] - lo, g["clean_end"] - lo
                if s[ls:le] != g["text"]:
                    ok = False
                    break
                local.append({"start": ls, "end": le, "text": g["text"],
                              "label": "TOPONYM", "attrs": g["attrs"]})
            if not ok:
                dropped_unrecoverable += 1
                continue
            rows.append({
                "text": s, "source": "ld80_gold", "source_file": path.name,
                "source_start": offmap[lo] if lo < len(offmap) else None,
                "source_end": offmap[hi - 1] + 1 if hi - 1 < len(offmap) else None,
                "text_id": meta["id"], "author": meta["author"],
                "title": meta["title"], "period": meta["period"],
                "period_raw": meta["period_raw"], "genre": meta["genre"],
                "year_pub": meta["year_pub"], "year_comp": yc,
                "gender": meta["gender"].strip(),
                "nationality": meta["nationality"],
                "gold_spans": local, "gold_layers": ["TOPONYM"],
                "positive": bool(local), "generated_by": None,
            })
            kept += 1
        per_file.append((path.name, meta["period"], len(gold), kept))

    print(f"{len(per_file)} files · {sum(p[2] for p in per_file)} gold cdplace spans "
          f"· {n_entities} character entities decoded (long-s: {a.long_s})")
    if unmatched:
        print(f"  ! not found in the manifest: {', '.join(unmatched)}")
    unk = [p[0] for p in per_file if p[1] == "unknown"]
    if unk:
        print(f"  ! period unresolved: {', '.join(unk)}")
    if dropped_unrecoverable:
        print(f"  {dropped_unrecoverable} passages dropped: gold offsets did not "
              f"resolve after cleaning (tags inside the span)")

    pos = [r for r in rows if r["positive"]]
    neg = [r for r in rows if not r["positive"]]
    print(f"{len(rows)} candidate passages · {len(pos)} with gold spans · {len(neg)} without")

    if a.n:
        n_neg = min(len(neg), int(round(a.n * a.negative_frac)))
        n_pos = a.n - n_neg
        by_period: dict[tuple, list[dict]] = defaultdict(list)
        for r in pos:
            by_period[(r["period"], r["genre"])].append(r)
        picked: list[dict] = []
        total = len(pos)
        for per, pool in by_period.items():
            take = max(1, round(n_pos * len(pool) / total))
            rng.shuffle(pool)
            picked += pool[:take]
        rng.shuffle(picked)
        picked = picked[:n_pos]
        rng.shuffle(neg)
        picked += neg[:n_neg]
        rng.shuffle(picked)
        rows = picked

    with a.out.open("w", encoding="utf-8") as f:
        for r in rows:
            h = hashlib.sha1(f"{r['source_file']}:{r['source_start']}:{r['text']}"
                             .encode()).hexdigest()[:10]
            r["passage_id"] = f"ld80_{r['period']}_{h}"
            r["stratum"] = (f"{r['period']}/{r['genre']}/"
                            f"{'pos' if r['positive'] else 'neg'}")
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_gold = sum(len(r["gold_spans"]) for r in rows)
    print(f"\nwrote {len(rows)} passages to {a.out} · {n_gold} gold TOPONYM spans")
    print("\nby period:")
    for k, v in sorted(Counter(r["stratum"] for r in rows).items()):
        g = sum(len(r["gold_spans"]) for r in rows if r["stratum"] == k)
        print(f"  {k:26s} {v:4d} passages  {g:5d} gold spans")
    g = Counter(r["gender"] for r in rows)
    print(f"\nauthor gender across sampled passages: {dict(g)}")
    if g.get("F", 0) / max(sum(g.values()), 1) < 0.15:
        print("  ! The gold subset is overwhelmingly male-authored (1 of 28 texts). "
              "Any claim about 'Lake District writing' from this sample is a claim "
              "about male-authored Lake District writing. Say so on the slide.")
    print("\nThe gold standard covers TOPONYM only. GEONOUN, RELATION, DISTANCE "
          "and TIME still need adjudication via the panel queues.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
