#!/usr/bin/env python3
"""
score_against_gold.py
---------------------
Turn a panel run into the numbers that go on the slides.

    python3 score_against_gold.py panel_panel_v1_openrouter.jsonl ld80_keep.jsonl

Produces, in results_snapshot_v2.json and on stdout:

  1. Per-voter precision / recall / F1 against the LD80 gold standard, with
     BOOTSTRAP CONFIDENCE INTERVALS, under two matching regimes.
  2. The same, broken down by period and by genre.
  3. The panel calibration curve: agreement threshold -> precision, coverage,
     and the human review burden that remains.
  4. Dawid-Skene consensus scored against gold, versus majority vote and versus
     the best single voter.

Scoring decisions, which are methodological and belong in the write-up
----------------------------------------------------------------------
BINARY, NOT LABELLED. <cdplace> is one flat layer: "Great Britain", "Skiddaw"
and "Low-wood Inn" are all just "place". The panel emits five labels. Marking a
voter wrong for saying GEONOUN where the gold says only "place" would measure
the gold scheme, not the model. So detection is scored as a binary span task and
the finer labels are reported as panel agreement only.

TWO MATCHING REGIMES, BOTH REPORTED. `exact` requires identical character
offsets. `overlap` accepts any overlap with a gold span, one-to-one. The gap
between them is the boundary-convention effect, which is the "Adriatic coast"
problem measured rather than asserted. Reporting only exact match understates
every voter; reporting only overlap flatters them.

NEGATIVE PASSAGES COUNT. Passages with no gold span are included, so false
positives are measurable. Precision computed only on passages known to contain
places is not precision.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict

import numpy as np

from spanpanel import (ABSTAIN, Span, bootstrap_ci, calibration_curve,
                       cluster_spans, dawid_skene, voter_reliability)


# ---------------------------------------------------------------- matching

def match(pred: list[dict], gold: list[dict], regime: str) -> tuple[int, int, int]:
    """Greedy one-to-one matching. Returns (tp, fp, fn)."""
    used = set()
    tp = 0
    order = sorted(range(len(pred)), key=lambda i: pred[i]["start"])
    for i in order:
        p = pred[i]
        best, best_ov = None, 0
        for j, g in enumerate(gold):
            if j in used:
                continue
            if regime == "exact":
                if p["start"] == g["start"] and p["end"] == g["end"]:
                    best, best_ov = j, 1
                    break
            else:
                ov = max(0, min(p["end"], g["end"]) - max(p["start"], g["start"]))
                if ov > best_ov:
                    best, best_ov = j, ov
        if best is not None:
            used.add(best)
            tp += 1
    return tp, len(pred) - tp, len(gold) - len(used)


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4),
            "tp": tp, "fp": fp, "fn": fn}


def bootstrap_f1(per_passage: list[tuple[int, int, int]], n_boot: int = 5000,
                 seed: int = 2026) -> tuple[float, float]:
    """Resample PASSAGES, not spans.

    Spans within a passage are not independent: a voter that fails on an
    18th-century sentence usually fails on every name in it. Resampling spans
    would give intervals that are far too narrow.
    """
    rng = np.random.default_rng(seed)
    arr = np.array(per_passage, dtype=float)
    if not len(arr):
        return (float("nan"), float("nan"))
    idx = rng.integers(0, len(arr), size=(n_boot, len(arr)))
    s = arr[idx].sum(axis=1)
    tp, fp, fn = s[:, 0], s[:, 1], s[:, 2]
    f1 = np.divide(2 * tp, 2 * tp + fp + fn,
                   out=np.zeros_like(tp), where=(2 * tp + fp + fn) > 0)
    return (float(np.quantile(f1, 0.025)), float(np.quantile(f1, 0.975)))


# ---------------------------------------------------------------- reporting

def score_voter(by_passage: dict[str, list[dict]], gold: dict[str, dict],
                regime: str) -> dict:
    per, tot = [], [0, 0, 0]
    for pid, g in gold.items():
        tp, fp, fn = match(by_passage.get(pid, []), g["gold_spans"], regime)
        per.append((tp, fp, fn))
        tot[0] += tp; tot[1] += fp; tot[2] += fn
    out = prf(*tot)
    lo, hi = bootstrap_f1(per)
    out["f1_ci95"] = [round(lo, 4), round(hi, 4)]
    out["n_passages"] = len(per)
    return out


def by_facet(by_passage: dict[str, list[dict]], gold: dict[str, dict],
             facet: str, regime: str) -> dict:
    groups: dict[str, list[str]] = defaultdict(list)
    for pid, g in gold.items():
        groups[g.get(facet) or "unknown"].append(pid)
    out = {}
    for k, pids in sorted(groups.items()):
        sub = {p: gold[p] for p in pids}
        if sum(len(v["gold_spans"]) for v in sub.values()) < 15:
            continue                       # too few gold spans to report
        out[k] = score_voter(by_passage, sub, regime)
    return out


def main(panel_path: str, passages_path: str,
         out_path: str = "results_snapshot_v2.json",
         score_labels: tuple[str, ...] = ("TOPONYM",)) -> int:
    gold: dict[str, dict] = {}
    for line in open(passages_path, encoding="utf-8"):
        r = json.loads(line)
        gold[r["passage_id"]] = r

    preds: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    spans_for_cluster: dict[str, list[Span]] = defaultdict(list)
    served: dict[str, set] = defaultdict(set)
    ungrounded: dict[str, int] = defaultdict(int)
    emitted: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    elapsed: dict[str, list[float]] = defaultdict(list)

    for line in open(panel_path, encoding="utf-8"):
        r = json.loads(line)
        v, pid = r["voter"], r["passage_id"]
        if pid not in gold:
            continue
        ungrounded[v] += r.get("n_failed_quotes", 0)
        elapsed[v].append(r.get("elapsed_s", 0.0))
        s = r.get("served") or {}
        if s.get("served_provider"):
            served[v].add(f"{s.get('served_model')}@{s['served_provider']}"
                          f"/{s.get('structured_mode')}/{s.get('params')}")
        for sp in r["spans"]:
            emitted[v][sp["label"]] += 1
            # ONLY SCORE THE LAYER THE GOLD ACTUALLY COVERS.
            #
            # <cdplace> annotates place names and nothing else. The panel emits
            # TOPONYM, GEONOUN, RELATION, DISTANCE and TIME. Scoring all five
            # against a place-only gold counts every correct "roads", "about six
            # miles distant" and "in 1843" as a false positive, which punishes
            # exactly the models doing the richer annotation and flatters a
            # place-only NER model into first place. That is measuring the gold
            # scheme, not the models.
            if sp["label"] not in score_labels:
                continue
            preds[v][pid].append({"start": sp["start"], "end": sp["end"],
                                  "label": sp["label"], "text": sp["text"]})
            # BINARY: collapse to one class before pooling. Only the scored
            # layer is pooled, for the same reason it is the only one scored.
            # The gold layer has no types, so keeping TOPONYM/GEONOUN/... here
            # would make the aggregate compare a five-way vote against a one-way
            # gold and score everything zero. The finer labels are still on
            # `preds` and are reported as panel agreement, not as accuracy.
            spans_for_cluster[v].append(
                Span(pid, sp["start"], sp["end"], "PLACE", sp["text"], v))

    voters = sorted(emitted)
    n_gold = sum(len(g["gold_spans"]) for g in gold.values())
    n_neg = sum(1 for g in gold.values() if not g["gold_spans"])
    print(f"{len(gold)} passages ({n_neg} with no gold span) · {n_gold} gold spans "
          f"· {len(voters)} voters")
    print(f"scoring layer(s): {', '.join(score_labels)} "
          f"(<cdplace> annotates place names only)\n")

    all_labels = sorted({k for d in emitted.values() for k in d})
    print("=== what each voter emitted, by layer ===")
    print(f"  {'voter':20s} " + " ".join(f"{l[:9]:>10s}" for l in all_labels)
          + f" {'scored':>8s} {'dropped':>8s}")
    for v in voters:
        tot = sum(emitted[v].values())
        kept = sum(emitted[v].get(l, 0) for l in score_labels)
        print(f"  {v:20s} " + " ".join(f"{emitted[v].get(l,0):10d}" for l in all_labels)
              + f" {kept:8d} {tot-kept:8d}")
    print("  Dropped spans are annotations of layers the gold standard does not "
          "cover. They are not errors.\n")

    # provenance drift check
    for v in voters:
        if len(served[v]) > 1:
            print(f"  ! {v}: served by MORE THAN ONE configuration during the run:")
            for s in sorted(served[v]):
                print(f"      {s}")
            print(f"      This voter's results are a mixture. Pin `only` and re-run.")

    results: dict = {"n_passages": len(gold), "n_gold_spans": n_gold,
                     "n_negative_passages": n_neg, "voters": {}}

    for regime in ("exact", "overlap"):
        print(f"=== {regime} match, binary span detection vs <cdplace> ===")
        print(f"  {'voter':20s} {'P':>6s} {'R':>6s} {'F1':>6s}   {'95% CI':>16s}  "
              f"{'ungrnd':>7s} {'ms/psg':>8s}")
        for v in voters:
            s = score_voter(preds[v], gold, regime)
            results["voters"].setdefault(v, {})[regime] = s
            ms = 1000 * float(np.mean(elapsed[v])) if elapsed[v] else 0.0
            print(f"  {v:20s} {s['precision']:6.3f} {s['recall']:6.3f} "
                  f"{s['f1']:6.3f}   [{s['f1_ci95'][0]:.3f}, {s['f1_ci95'][1]:.3f}]  "
                  f"{ungrounded[v]:7d} {ms:8.1f}")
        print()

    # overlapping intervals = no defensible ranking
    ex = {v: results["voters"][v]["exact"] for v in voters}
    ranked = sorted(voters, key=lambda v: -ex[v]["f1"])
    if len(ranked) >= 2:
        a, b = ranked[0], ranked[1]
        if ex[a]["f1_ci95"][0] <= ex[b]["f1_ci95"][1]:
            print(f"  NOTE: {a} and {b} have OVERLAPPING confidence intervals. "
                  f"Do not present this as a ranking.\n")
        else:
            print(f"  {a} beats {b} with non-overlapping intervals. "
                  f"This difference is reportable.\n")

    for facet in ("period", "genre"):
        print(f"=== exact match by {facet} ===")
        rows = {v: by_facet(preds[v], gold, facet, "exact") for v in voters}
        keys = sorted({k for r in rows.values() for k in r})
        print(f"  {'voter':20s} " + " ".join(f"{k[:14]:>15s}" for k in keys))
        for v in voters:
            print(f"  {v:20s} " + " ".join(
                f"{rows[v][k]['f1']:15.3f}" if k in rows[v] else f"{'-':>15s}"
                for k in keys))
        results.setdefault("by_" + facet, {})
        for v in voters:
            results["by_" + facet][v] = rows[v]
        print()

    # ---------------- panel aggregation
    clusters = cluster_spans({v: spans_for_cluster[v] for v in voters})
    for c in clusters:
        g = gold.get(c.passage_id)
        c.gold = "PLACE" if g and any(
            not (c.end <= x["start"] or c.start >= x["end"]) for x in g["gold_spans"]
        ) else "REJECT"

    n = len(clusters)
    contested = [c for c in clusters if c.stratum() == "B_contested"]
    print(f"=== panel: {n} pooled decision items ===")
    print(f"  unanimous : {n - len(contested):5d} ({100*(n-len(contested))/n:.1f}%)")
    print(f"  contested : {len(contested):5d} ({100*len(contested)/n:.1f}%)  "
          f"<- the human adjudication surface\n")

    assert all(m.label == "PLACE" for c in clusters for m in c.members), \
        "votes must be collapsed to the binary class before aggregation"
    print("  agreement  precision  coverage  review burden")
    for row in calibration_curve(clusters):
        p = f"{row['precision']:.3f}" if row["precision"] is not None else "   -  "
        print(f"  >={row['threshold']:<9d} {p:>9s}  {row['coverage']:8.3f}  "
              f"{row['review_burden']:13.3f}")
    results["calibration"] = calibration_curve(clusters)

    post, err, prior, latent = dawid_skene(clusters, ["PLACE"])
    pred = [latent[int(i)] for i in post.argmax(1)]
    truth = [c.gold for c in clusters]
    ds = float(np.mean([a == b for a, b in zip(pred, truth)]))
    mv = float(np.mean([(c.modal_label() if c.agreement() > len(c.votes) / 2
                         else "REJECT") == c.gold for c in clusters]))
    best = max(ex[v]["f1"] for v in voters)
    print(f"\n  Dawid-Skene consensus accuracy : {ds:.4f}")
    print(f"  majority vote accuracy         : {mv:.4f}")
    print(f"  best single voter, exact F1    : {best:.4f}")

    rel = voter_reliability(err, latent)
    print("\n  voter profiles estimated WITHOUT gold:")
    for v, d in sorted(rel.items(), key=lambda x: -x[1]["accuracy"]):
        print(f"    {v:20s} accuracy {d['accuracy']:.3f}  coverage {d['coverage']:.3f}")
    results["panel"] = {
        "n_items": n, "n_contested": len(contested),
        "adjudication_burden": round(len(contested) / n, 4),
        "dawid_skene_accuracy": round(ds, 4),
        "majority_vote_accuracy": round(mv, 4),
        "voter_profiles": {k: {kk: round(vv, 4) for kk, vv in d.items()}
                           for k, d in rel.items()},
        "served_configurations": {k: sorted(v) for k, v in served.items()},
    }

    json.dump(results, open(out_path, "w"), indent=2)
    print(f"\nwritten: {out_path}")
    print("\nReport F1 with its interval, never bare. Report binary detection, "
          "not labelled, against <cdplace>.")
    return 0


if __name__ == "__main__":
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    labels = ("TOPONYM",)
    for a in sys.argv[1:]:
        if a.startswith("--labels="):
            labels = tuple(a.split("=", 1)[1].split(","))
    sys.exit(main(argv[0], argv[1],
                  argv[2] if len(argv) > 2 else "results_snapshot_v2.json",
                  labels))
