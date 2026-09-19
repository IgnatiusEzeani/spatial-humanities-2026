#!/usr/bin/env python3
"""
affect_panel.py
---------------
Tier 2: segment-level classification (sentiment, emotion).

Different problem from Tier 1. There are no spans to align: the decision item IS
the segment. So there is no pooling step, and crucially NO ADJUDICATION BUDGET is
spent here. What gets reported is inter-model agreement, not accuracy.

That is a deliberate limit, not a shortcut. Assigning an emotion label to a
passage of testimony is an interpretive act with no single correct answer, so
"precision against gold" is the wrong frame. Agreement across seven independent
systems measures something real and reportable: how far the task constrains the
answer at all.

The headline this produces:

    Seven systems agree on 91% of place names and 34% of emotion labels.
    That gap is not a model deficiency. It is the difference between
    recognition and interpretation.

Krippendorff's alpha is the right statistic (Artstein & Poesio 2008; Krippendorff
2004) because it handles multiple coders, missing values, and chance correction.
Percentage agreement alone would flatter a skewed label distribution, which
emotion labels always have.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from itertools import combinations
from typing import Sequence

import numpy as np

from spanpanel import ABSTAIN, Cluster, dawid_skene, voter_reliability

SENTIMENT = ["positive", "negative", "neutral"]
EMOTION = ["fear", "sadness", "anger", "joy", "relief", "gratitude", "neutral"]

AFFECT_INSTRUCTION = """Classify the emotional tone of the passage below.

Choose ONE sentiment: positive, negative, neutral
Choose ONE emotion: fear, sadness, anger, joy, relief, gratitude, neutral

Rules:
  - Judge what the passage conveys, not what you infer the speaker felt.
  - "neutral" means the passage carries no explicit affective content. It does
    NOT mean the experience described was emotionally neutral.
  - Quote the wording that carries the tone, verbatim, or null if there is none.

Return JSON: {"sentiment": "...", "emotion": "...", "evidence": "..." or null}

Passage:
<<<
%s
>>>"""

AFFECT_SCHEMA = {
    "type": "object",
    "properties": {
        "sentiment": {"type": "string", "enum": SENTIMENT},
        "emotion": {"type": "string", "enum": EMOTION},
        "evidence": {"type": ["string", "null"]},
    },
    "required": ["sentiment", "emotion", "evidence"],
    "additionalProperties": False,
}


# --------------------------------------------------------------------------
# agreement
# --------------------------------------------------------------------------

def krippendorff_alpha(votes: dict[str, dict[str, str]], categories: Sequence[str]) -> float:
    """Nominal alpha over {voter: {item: label}}, missing values allowed.

    alpha = 1 - Do/De, computed on the coincidence matrix, which is the
    formulation that tolerates coders who did not label every item.
    """
    items: dict[str, list[str]] = defaultdict(list)
    for voter, per_item in votes.items():
        for item, lab in per_item.items():
            if lab is not None and lab != ABSTAIN:
                items[item].append(lab)
    usable = {k: v for k, v in items.items() if len(v) >= 2}
    if not usable:
        return float("nan")

    cats = list(categories)
    ci = {c: i for i, c in enumerate(cats)}
    k = len(cats)
    coincidence = np.zeros((k, k))
    for labs in usable.values():
        m = len(labs)
        for a, b in combinations(labs, 2):
            if a not in ci or b not in ci:
                continue
            coincidence[ci[a], ci[b]] += 1 / (m - 1)
            coincidence[ci[b], ci[a]] += 1 / (m - 1)
        for lab in labs:
            if lab in ci:
                coincidence[ci[lab], ci[lab]] += 0        # explicit: no self-pair

    n = coincidence.sum()
    if n == 0:
        return float("nan")
    marg = coincidence.sum(axis=1)
    do = 1 - (np.trace(coincidence) / n)
    de = 1 - (np.sum(marg * (marg - 1)) / (n * (n - 1))) if n > 1 else 0.0
    return float(1 - do / de) if de else float("nan")


def pairwise_agreement(votes: dict[str, dict[str, str]]) -> dict[tuple[str, str], float]:
    out = {}
    for a, b in combinations(sorted(votes), 2):
        shared = set(votes[a]) & set(votes[b])
        if not shared:
            continue
        out[(a, b)] = sum(votes[a][i] == votes[b][i] for i in shared) / len(shared)
    return out


def unanimity_rate(votes: dict[str, dict[str, str]]) -> float:
    items = defaultdict(list)
    for voter, per in votes.items():
        for item, lab in per.items():
            items[item].append(lab)
    full = [v for v in items.values() if len(v) == len(votes)]
    return sum(1 for v in full if len(set(v)) == 1) / len(full) if full else float("nan")


def to_clusters(votes: dict[str, dict[str, str]]) -> list[Cluster]:
    """Reuse Dawid-Skene by treating each segment as a one-item cluster.

    No span semantics are involved, so start/end are dummies. The estimator does
    not care: it consumes a vote dictionary per item.
    """
    all_items = sorted({i for per in votes.values() for i in per})
    voters = sorted(votes)
    return [Cluster(i, 0, 0, i, {v: votes[v].get(i, ABSTAIN) for v in voters})
            for i in all_items]


def report(votes: dict[str, dict[str, str]], categories: Sequence[str],
           layer: str) -> dict:
    alpha = krippendorff_alpha(votes, categories)
    pw = pairwise_agreement(votes)
    unan = unanimity_rate(votes)
    clusters = to_clusters(votes)
    post, err, prior, latent = dawid_skene(clusters, list(categories))
    rel = voter_reliability(err, latent)

    dist = Counter(l for per in votes.values() for l in per.values())
    print(f"\n=== {layer} ===")
    print(f"  Krippendorff alpha : {alpha:.3f}")
    print(f"  unanimity rate     : {unan:.3f}")
    print(f"  label distribution : {dict(dist.most_common())}")
    if pw:
        lo = min(pw, key=pw.get)
        hi = max(pw, key=pw.get)
        print(f"  most agreement     : {hi[0]} / {hi[1]}  {pw[hi]:.3f}")
        print(f"  least agreement    : {lo[0]} / {lo[1]}  {pw[lo]:.3f}")
    print("  estimated voter accuracy (no gold):")
    for v, d in sorted(rel.items(), key=lambda x: -x[1]["accuracy"]):
        print(f"    {v:18s} {d['accuracy']:.3f}")

    return {"layer": layer, "alpha": alpha, "unanimity": unan,
            "pairwise": {f"{a}|{b}": round(v, 4) for (a, b), v in pw.items()},
            "label_distribution": dict(dist),
            "voter_accuracy": {k: round(v["accuracy"], 4) for k, v in rel.items()},
            "consensus": {clusters[i].passage_id: latent[int(post[i].argmax())]
                          for i in range(len(clusters))}}


def main(path: str) -> int:
    """Input: jsonl of {"voter","passage_id","sentiment","emotion"}."""
    sent: dict[str, dict[str, str]] = defaultdict(dict)
    emo: dict[str, dict[str, str]] = defaultdict(dict)
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("sentiment"):
            sent[r["voter"]][r["passage_id"]] = r["sentiment"]
        if r.get("emotion"):
            emo[r["voter"]][r["passage_id"]] = r["emotion"]

    out = [report(dict(sent), SENTIMENT, "sentiment"),
           report(dict(emo), EMOTION, "emotion")]
    json.dump(out, open("affect_summary.json", "w"), indent=2)
    print("\nwritten: affect_summary.json")
    print("\nReport these as agreement, never as accuracy. No gold was used and "
          "none should be implied.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "affect_votes.jsonl"))
