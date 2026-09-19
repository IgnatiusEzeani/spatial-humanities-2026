#!/usr/bin/env python3
"""
build_passages.py
-----------------
Build the stratified passages.jsonl the panel runs over.

    python3 build_passages.py \
        --cldw-dir /path/to/CLDW/plain_text \
        --testimony data/synthetic_testimony.jsonl \
        --n-cldw 260 --n-testimony 140 \
        --out passages.jsonl

Design decisions worth knowing, because they determine what your numbers mean:

1. NEGATIVE PASSAGES ARE INCLUDED ON PURPOSE (--negative-frac, default 0.15).
   If you sample only passages that obviously contain place names, every method
   looks better than it is and you cannot estimate false positives at all. A
   voter that marks something in a passage containing no spatial expression is
   making an error you can only see if such passages are in the sample. This is
   the difference between a sample and a highlight reel.

2. STRATIFICATION IS BY PERIOD AND GENRE, not by convenience. Allocation is
   proportional to what the corpus actually contains, so coverage figures can be
   read back to the corpus rather than only to the sample.

3. EVERY PASSAGE CARRIES ITS SOURCE OFFSETS. A reviewer, or you in two years,
   must be able to go from a panel decision back to the exact characters in the
   exact file. This is the same recoverable-path-to-source principle the keynote
   argues for; the sampler should not be the place it breaks.

4. `generated_by` RECORDS MODEL PROVENANCE for contamination control. Real CLDW
   text gets null. Anything a model wrote gets that model's name, and
   panel_config.json must then exclude that model from voting on it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# CLDW periodisation, as used in the project's earlier work
PERIODS = [
    ("late_18c", 1700, 1795),
    ("romantic", 1796, 1837),
    ("victorian", 1838, 1900),
]

# Sentence splitter that does not break on the abbreviations 19th-century travel
# writing is full of. spaCy is used when available; this is the fallback.
_ABBREV = r"(?<!\bMr)(?<!\bMrs)(?<!\bDr)(?<!\bSt)(?<!\bRev)(?<!\bCapt)(?<!\bNo)(?<!\bvol)(?<!\bp)(?<!\bfig)"
_SPLIT = re.compile(_ABBREV + r"(?<=[.!?])[\"')\]]?\s+(?=[A-Z\"'(\[])")

# A crude spatial cue test, used ONLY to label a passage positive or negative for
# sampling. It is deliberately not the annotation scheme and never becomes gold.
_CAP = re.compile(r"\b[A-Z][a-z]{2,}\b")
_GEONOUN = re.compile(
    r"\b(road|roads|lake|lakes|hill|hills|fell|fells|river|rivers|valley|vale|"
    r"bridge|mountain|mountains|village|town|church|inn|path|track|shore|coast|"
    r"wood|woods|camp|ghetto|station|border|street|field|fields|stream|beck)\b", re.I)
_DIST = re.compile(r"\b(mile|miles|league|leagues|yards?|hours?\s+(walk|ride|journey))\b", re.I)


DROP_ELEMENTS = ("teiHeader", "note", "figDesc", "fw", "gap", "back")


def clean_with_offsets(raw: str, drop: tuple[str, ...] = DROP_ELEMENTS
                       ) -> tuple[str, list[int]]:
    """Strip XML/TEI markup and collapse whitespace, KEEPING a map back to raw.

    The previous version did re.sub on the text and then recorded offsets into
    the CLEANED string. Those offsets only resolve if a reader re-applies exactly
    the same regexes in exactly the same order. That is not a recoverable path to
    source, it is a recoverable path to my cleaning function. CLDW carries XML
    tags, so on real LD80 files the discrepancy would have been large.

    Returns (clean_text, offmap) where offmap[i] is the index in `raw` of
    clean_text[i], so raw[offmap[a]:offmap[b-1]+1] recovers the original span
    including any markup that sat inside it.
    """
    # Whole elements whose CONTENT is not running text. The probe on TEI-marked
    # fixtures showed the teiHeader title ("The English Lakes") prepended to the
    # first sentence of every file, which would have put a phantom toponym in
    # front of 80 passages.
    for el in drop:
        for m in re.finditer(rf"<\s*{el}\b[^>]*>.*?<\s*/\s*{el}\s*>", raw,
                             re.S | re.I):
            raw = raw[:m.start()] + (" " * (m.end() - m.start())) + raw[m.end():]

    out: list[str] = []
    offmap: list[int] = []
    i, n = 0, len(raw)
    in_tag = False
    last_space = False
    while i < n:
        ch = raw[i]
        if ch == "<":
            in_tag = True
            i += 1
            continue
        if in_tag:
            if ch == ">":
                in_tag = False
                if not last_space:
                    out.append(" "); offmap.append(i); last_space = True
            i += 1
            continue
        if ch.isspace():
            if not last_space:
                out.append(" "); offmap.append(i); last_space = True
        else:
            # a tag sitting between a word and its punctuation leaves "Keswick ,"
            # which shifts every span boundary a voter proposes. Drop the space.
            if last_space and ch in ",.;:!?)]}\u2019\u201d" and out and out[-1] == " ":
                out.pop(); offmap.pop()
            out.append(ch); offmap.append(i); last_space = False
        i += 1
    return "".join(out), offmap


def probe_corpus(cldw_dir: Path, limit: int = 8) -> None:
    """Report what is actually in the corpus directory before sampling it.

    Run this first on LD80. It answers the questions the sampler has to assume:
    which subdirectory, which extension, what markup, whether years are in the
    filenames, and what a sentence looks like after cleaning.
    """
    print(f"probing {cldw_dir}\n")
    exts = Counter(p.suffix.lower() for p in cldw_dir.rglob("*") if p.is_file())
    print("file extensions:", dict(exts))
    subdirs = Counter(str(p.relative_to(cldw_dir).parts[0])
                      for p in cldw_dir.rglob("*") if p.is_file() and
                      len(p.relative_to(cldw_dir).parts) > 1)
    print("subdirectories :", dict(subdirs) or "(flat)")

    files = sorted(p for p in cldw_dir.rglob("*") if p.suffix.lower() in (".txt", ".xml", ".tei"))
    print(f"candidate text files: {len(files)}\n")
    tags: Counter = Counter()
    undated = 0
    for p in files:
        raw = p.read_text(encoding="utf-8", errors="replace")
        tags.update(re.findall(r"<\s*/?\s*([A-Za-z][\w:.-]*)", raw[:200000]))
        if detect_year(p, {}) is None:
            undated += 1
    print("markup tags found:", dict(tags.most_common(12)) or "(none, plain text)")
    print(f"files with no detectable year: {undated}/{len(files)}"
          + ("   -> supply --year-map" if undated else ""))

    for p in files[:limit]:
        raw = p.read_text(encoding="utf-8", errors="replace")
        clean, offmap = clean_with_offsets(raw)
        sents = split_sentences(clean)
        sample = next((clean[a:b].strip() for a, b in sents
                       if 45 <= b - a <= 420), "(none in length range)")
        print(f"\n  {p.name}  year={detect_year(p, {})}  "
              f"raw={len(raw)} clean={len(clean)} sents={len(sents)}")
        print(f"    {sample[:150]}")


def detect_year(path: Path, override: dict[str, int]) -> int | None:
    if path.name in override:
        return override[path.name]
    years = [int(y) for y in re.findall(r"(?<!\d)(1[6-9]\d\d)(?!\d)", path.name)]
    if years:
        return years[0]
    head = path.read_text(encoding="utf-8", errors="replace")[:3000]
    years = [int(y) for y in re.findall(r"(?<!\d)(1[6-9]\d\d)(?!\d)", head)]
    return min(years) if years else None


def period_of(year: int | None) -> str:
    if year is None:
        return "unknown"
    for name, lo, hi in PERIODS:
        if lo <= year <= hi:
            return name
    return "outside_range"


def split_sentences(text: str) -> list[tuple[int, int]]:
    """Return (start, end) offsets. Offsets, not strings: see design note 3."""
    try:
        import spacy
        nlp = split_sentences._nlp                      # type: ignore[attr-defined]
    except (ImportError, AttributeError):
        try:
            import spacy
            nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
            split_sentences._nlp = nlp                  # type: ignore[attr-defined]
        except Exception:                               # noqa: BLE001
            nlp = None
            split_sentences._nlp = None                 # type: ignore[attr-defined]
    if nlp is not None:
        return [(s.start_char, s.end_char) for s in nlp(text).sents]

    out, prev = [], 0
    for m in _SPLIT.finditer(text):
        out.append((prev, m.start() + 1))
        prev = m.end()
    if prev < len(text):
        out.append((prev, len(text)))
    return out


def is_positive(s: str) -> bool:
    """Does this passage plausibly contain a spatial expression?"""
    caps = [c for c in _CAP.findall(s) if c not in ("The", "This", "That", "There",
                                                    "These", "Those", "When", "What")]
    return bool(caps) or bool(_GEONOUN.search(s)) or bool(_DIST.search(s))


def harvest_cldw(cldw_dir: Path, override: dict[str, int], genre: dict[str, str],
                 min_len: int, max_len: int) -> list[dict]:
    rows = []
    files = sorted(p for p in cldw_dir.rglob("*.txt"))
    if not files:
        sys.exit(f"no .txt files under {cldw_dir}")
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="replace")
        text, offmap = clean_with_offsets(raw)
        year = detect_year(path, override)
        per = period_of(year)
        gen = genre.get(path.name, "unknown")
        for start, end in split_sentences(text):
            s = text[start:end].strip()
            if not (min_len <= len(s) <= max_len):
                continue
            if sum(ch.isalpha() for ch in s) / max(len(s), 1) < 0.6:
                continue                                       # tables, page furniture
            # offsets into the ORIGINAL file, so the passage is recoverable
            # without re-running any cleaning step
            lead = len(text[start:end]) - len(text[start:end].lstrip())
            raw_start = offmap[start + lead]
            raw_end = offmap[min(end, len(offmap)) - 1] + 1
            rows.append({
                "text": s, "source": "cldw", "source_file": path.name,
                "source_start": raw_start, "source_end": raw_end,
                "clean_start": start, "clean_end": end,
                "year": year, "period": per, "genre": gen,
                "positive": is_positive(s), "generated_by": None,
            })
    return rows


def load_testimony(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows.append({
            "text": r["text"], "source": "testimony_synthetic",
            "source_file": r.get("source_file", path.name),
            "source_start": r.get("start", 0), "source_end": r.get("end", len(r["text"])),
            "year": None, "period": r.get("phase", "unknown"),
            "genre": r.get("genre", "qa_segment"),
            "positive": is_positive(r["text"]),
            # CRITICAL for contamination control: which model wrote this
            "generated_by": r.get("generated_by"),
        })
    return rows


def dedupe(rows: list[dict]) -> tuple[list[dict], int]:
    """Drop repeated text BEFORE sampling.

    Doing this afterwards silently shrinks the sample below the requested size:
    on a first test it returned 44 passages for a request of 100 and reported
    success. Corpora with boilerplate, running heads or reprinted passages will
    do the same to you on real data.
    """
    seen, out = set(), []
    for r in rows:
        key = re.sub(r"\W+", "", r["text"].lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out, len(rows) - len(out)


def stratified_sample(rows: list[dict], n: int, negative_frac: float,
                      rng: random.Random, label: str = "") -> list[dict]:
    """Proportional allocation over (period, genre), with a negative quota."""
    rows, n_dupes = dedupe(rows)
    if n_dupes:
        print(f"  {label}: dropped {n_dupes} duplicate texts, "
              f"{len(rows)} unique candidates remain")
    if len(rows) < n:
        print(f"  ! {label}: only {len(rows)} unique candidates for a request of "
              f"{n}. Sample will be short. Widen --min-len/--max-len, or add files.")
        n = len(rows)
    n_neg = int(round(n * negative_frac))
    n_pos = n - n_neg
    picked: list[dict] = []

    pos_pool = [r for r in rows if r["positive"]]
    neg_pool = [r for r in rows if not r["positive"]]
    if len(neg_pool) < n_neg:
        print(f"  ! {label}: wanted {n_neg} negative passages, only {len(neg_pool)} "
              f"available. Precision estimates will rest on fewer of them.")
        n_neg = len(neg_pool)
        n_pos = n - n_neg
    for want, pool in ((n_pos, pos_pool), (n_neg, neg_pool)):
        if not pool or want <= 0:
            continue
        strata: dict[tuple, list[dict]] = defaultdict(list)
        for r in pool:
            strata[(r["period"], r["genre"])].append(r)
        total = len(pool)
        alloc = {k: max(1, round(want * len(v) / total)) for k, v in strata.items()}
        # trim or pad to hit `want` exactly
        while sum(alloc.values()) > want:
            k = max(alloc, key=lambda k: alloc[k])
            alloc[k] -= 1
            if alloc[k] == 0:
                del alloc[k]
        while sum(alloc.values()) < want:
            k = max(strata, key=lambda k: len(strata[k]) - alloc.get(k, 0))
            alloc[k] = alloc.get(k, 0) + 1
        for k, take in alloc.items():
            pool_k = strata[k]
            rng.shuffle(pool_k)
            picked.extend(pool_k[:take])
    rng.shuffle(picked)
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cldw-dir", type=Path)
    ap.add_argument("--probe", action="store_true",
                    help="inspect the corpus directory and exit, without sampling")
    ap.add_argument("--testimony", type=Path)
    ap.add_argument("--out", type=Path, default=Path("passages.jsonl"))
    ap.add_argument("--n-cldw", type=int, default=260)
    ap.add_argument("--n-testimony", type=int, default=140)
    ap.add_argument("--negative-frac", type=float, default=0.15)
    ap.add_argument("--min-len", type=int, default=45)
    ap.add_argument("--max-len", type=int, default=420)
    ap.add_argument("--year-map", type=Path, help="CSV: filename,year")
    ap.add_argument("--genre-map", type=Path, help="CSV: filename,genre")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()

    if a.probe:
        if not a.cldw_dir:
            sys.exit("--probe needs --cldw-dir")
        probe_corpus(a.cldw_dir)
        return 0

    rng = random.Random(a.seed)

    def read_map(p: Path | None, cast=str) -> dict:
        if not p:
            return {}
        out = {}
        for line in p.read_text(encoding="utf-8").splitlines()[1:]:
            if "," in line:
                k, v = line.split(",", 1)
                out[k.strip()] = cast(v.strip())
        return out

    picked: list[dict] = []
    if a.cldw_dir:
        rows = harvest_cldw(a.cldw_dir, read_map(a.year_map, int),
                            read_map(a.genre_map), a.min_len, a.max_len)
        print(f"CLDW: {len(rows)} candidate sentences from "
              f"{len({r['source_file'] for r in rows})} files")
        unknown = sum(1 for r in rows if r["period"] in ("unknown", "outside_range"))
        if unknown:
            print(f"  ! {unknown} sentences have no detectable year. "
                  f"Supply --year-map to stratify these properly.")
        picked += stratified_sample(rows, a.n_cldw, a.negative_frac, rng, "CLDW")

    if a.testimony:
        rows = load_testimony(a.testimony)
        print(f"testimony: {len(rows)} candidate segments")
        picked += stratified_sample(rows, a.n_testimony, a.negative_frac, rng, "testimony")

    # stable ids. Deduplication already happened before sampling.
    final = []
    for r in picked:
        # include the text: testimony segments share source_start=0, so hashing
        # only file+offset collides and silently produces duplicate ids
        h = hashlib.sha1(
            f"{r['source_file']}:{r['source_start']}:{r['text']}".encode()
        ).hexdigest()[:10]
        r["passage_id"] = f"{r['source']}_{r['period']}_{h}"
        r["stratum"] = f"{r['period']}/{r['genre']}/{'pos' if r['positive'] else 'neg'}"
        final.append(r)

    with a.out.open("w", encoding="utf-8") as f:
        for r in final:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    target = (a.n_cldw if a.cldw_dir else 0) + (a.n_testimony if a.testimony else 0)
    print(f"\nwrote {len(final)} passages to {a.out}" +
          (f"   ! SHORT OF TARGET {target}" if len(final) < target else ""))
    print(f"  negative (no obvious spatial cue): "
          f"{sum(1 for r in final if not r['positive'])} "
          f"({100*sum(1 for r in final if not r['positive'])/max(len(final),1):.0f}%)")
    print("\nby stratum:")
    for k, v in sorted(Counter(r["stratum"] for r in final).items()):
        print(f"  {k:44s} {v}")

    gen = Counter(r["generated_by"] for r in final if r["generated_by"])
    if gen:
        print("\nMODEL-GENERATED PASSAGES (contamination control):")
        for k, v in gen.items():
            print(f"  {k}: {v} passages")
        print("  -> add these passage_ids to that model's `excluded_passages` "
              "in panel_config.json")
        for model in gen:
            ids = [r["passage_id"] for r in final if r["generated_by"] == model]
            Path(f"excluded_{model}.json").write_text(json.dumps(ids, indent=2))
            print(f"  -> wrote excluded_{model}.json")
    else:
        print("\nno model-generated passages flagged. If that is wrong, set "
              "`generated_by` in the testimony file before running the panel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
