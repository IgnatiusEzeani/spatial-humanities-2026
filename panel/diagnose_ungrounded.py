#!/usr/bin/env python3
"""
diagnose_ungrounded.py
----------------------
Why did a voter's quotes fail to ground?

    python3 diagnose_ungrounded.py panel_panel_v1_openrouter.jsonl ld80_keep.jsonl

A quote that cannot be found in the source is discarded by `ground()`. The rate
at which that happens is a property of the voter, and the REASON is a finding.

This script tests one hypothesis in particular: that some models silently
normalise historical orthography when asked to quote verbatim. The long s (U+017F)
appears in 125 of the 399 LD80 passages, concentrated in five 18th-century texts.
A model that writes "Ullswater" where the source has "Ulleswater", or "ſide" as
"side", produces a quote that is semantically right and textually absent.

That failure mode is INVISIBLE to any evaluation that asks a model for character
offsets instead of quotes, because the offsets would simply point at the original
spelling and the substitution would never surface.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict

LONG_S = "\u017f"


def normalise(s: str) -> str:
    """Fold the transformations a model might silently apply."""
    s = s.replace(LONG_S, "s")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = re.sub(r"[\u2010-\u2015]", "-", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def classify(quote: str, passage: str) -> str:
    """Why is this quote not in this passage?"""
    if not quote:
        return "empty"
    if quote in passage:
        return "present_but_exhausted"
    if LONG_S in passage and normalise(quote) in normalise(passage):
        nq, np_ = quote.replace(LONG_S, "s"), passage.replace(LONG_S, "s")
        if nq in np_:
            return "long_s_normalised"
        return "other_normalisation"
    if normalise(quote) in normalise(passage):
        return "other_normalisation"
    if quote.strip(" .,;:'\"") and quote.strip(" .,;:'\"") in passage:
        return "whitespace_or_punctuation"
    words = quote.split()
    if words and all(w in passage for w in words):
        return "words_present_reordered_or_gapped"
    return "not_in_passage_at_all"


def main(panel_path: str, passages_path: str) -> int:
    passages: dict[str, str] = {}
    for line in open(passages_path, encoding="utf-8"):
        r = json.loads(line)
        passages[r["passage_id"]] = r["text"]

    n_longs = sum(1 for t in passages.values() if LONG_S in t)
    print(f"{len(passages)} passages, {n_longs} containing the long s (U+017F)\n")

    fails: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    on_longs: dict[str, set] = defaultdict(set)
    examples: dict[str, list] = defaultdict(list)

    # run records only carry the COUNT of failed quotes, so re-derive the reason
    # by re-grounding every returned span against its passage
    for line in open(panel_path, encoding="utf-8"):
        r = json.loads(line)
        v, pid = r["voter"], r["passage_id"]
        p = passages.get(pid)
        if p is None:
            continue
        totals[v] += r.get("n_failed_quotes", 0)
        if r.get("n_failed_quotes") and LONG_S in p:
            on_longs[v].add(pid)
        for sp in r["spans"]:
            if sp["text"] and sp["text"] not in p:
                why = classify(sp["text"], p)
                fails[v][why] += 1
                if len(examples[v]) < 4:
                    examples[v].append((sp["text"], why))

    print("=== ungrounded quotes: which passages were they in? ===")
    print(f"  {'voter':20s} {'failures':>9s} {'in long-s passages':>20s} "
          f"{'share':>7s}")
    for v in sorted(totals):
        n = totals[v]
        ls = len(on_longs[v])
        share = ls / n if n else 0
        print(f"  {v:20s} {n:9d} {ls:20d} {share:7.1%}")

    print("\n  If a voter's failures cluster in the long-s passages, it is "
          "silently\n  modernising the orthography it was asked to quote verbatim.")

    if any(fails.values()):
        print("\n=== reason, where spans survived into the record ===")
        reasons = sorted({k for c in fails.values() for k in c})
        print(f"  {'voter':20s} " + " ".join(f"{r[:16]:>18s}" for r in reasons))
        for v in sorted(fails):
            print(f"  {v:20s} " + " ".join(f"{fails[v].get(r,0):18d}" for r in reasons))

    for v in sorted(examples):
        if examples[v]:
            print(f"\n  {v}:")
            for q, why in examples[v]:
                print(f"     {why:28s} {q[:60]!r}")

    print("\nNote: quotes rejected by ground() are NOT in the run record, only "
          "their count.\nTo capture the rejected strings themselves, have "
          "run_panel persist the\n`failures` list from ground(). Worth doing "
          "before any re-run.")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
