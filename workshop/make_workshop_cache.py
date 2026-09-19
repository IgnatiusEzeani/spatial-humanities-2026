#!/usr/bin/env python3
"""
make_workshop_cache.py
----------------------
Build the cached panel results the merged workshop notebook reads.

    python3 make_workshop_cache.py \
        --panel  ../experiments/panel_panel_v1_openrouter.jsonl \
        --results ../experiments/results_snapshot_v2.json \
        --passages workshop_passages.json \
        --out    ../workshop/data/panel_cache.json

Why cache rather than call live
-------------------------------
Thirty people each calling four APIs during a 35-minute block is a bad idea for
three reasons: it needs keys nobody has, it costs money, and it fails on
conference Wi-Fi. But showing SIMULATED output would undercut the whole argument
of the workshop, which is that you should be able to trace any claim to evidence.

So: the notebook shows the REAL outputs from the real 399-passage run, for six
specific passages, extracted here. Participants see what the models actually did.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

# Display names, and the order rows appear in the comparison
NICE = [
    ("rules", "rules + gazetteer"),
    ("hf_bert_ner", "BERT NER (2019, pinned)"),
    ("spacy_trf_hybrid", "spaCy trf + gazetteers"),
    ("qwen_large", "Qwen 3.5 27B (open weight)"),
    ("gpt_5_6_sol", "GPT-5.6-sol"),
    ("claude", "Claude Opus 5"),
    ("gemini_2_5", "Gemini 2.5 Pro"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", type=Path, required=True)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--passages", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--layer", default="TOPONYM",
                    help="which layer to show in the comparison; the gold "
                         "standard covers TOPONYM only")
    a = ap.parse_args()

    wanted = {p["passage_id"] for p in
              json.load(open(a.passages, encoding="utf-8"))}
    res = json.load(open(a.results, encoding="utf-8"))

    per: dict[str, dict[str, list]] = defaultdict(dict)
    elapsed: dict[str, list[float]] = defaultdict(list)
    layers: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for line in open(a.panel, encoding="utf-8"):
        r = json.loads(line)
        if r.get("elapsed_s") is not None:
            elapsed[r["voter"]].append(float(r["elapsed_s"]))
        for sp in r["spans"]:
            layers[r["voter"]][sp["label"]] += 1
        if r["passage_id"] not in wanted:
            continue
        per[r["passage_id"]][r["voter"]] = [
            {"start_char": s["start"], "end_char": s["end"],
             "label": s["label"], "text": s["text"]}
            for s in r["spans"] if s["label"] == a.layer
        ]

    missing = wanted - set(per)
    if missing:
        print(f"  ! no panel output for: {', '.join(sorted(missing))}")

    out: dict = {}
    for pid, by_voter in per.items():
        out[pid] = {nice: by_voter[v] for v, nice in NICE if v in by_voter}

    all_labels = sorted({k for d in layers.values() for k in d})
    out["_layer_counts"] = [
        dict({"voter": nice},
             **{l: layers[v].get(l, 0) for l in all_labels},
             **{"total": sum(layers[v].values())})
        for v, nice in NICE if v in layers
    ]

    ex = {v: d.get("exact", {}) for v, d in res.get("voters", {}).items()}
    ov = {v: d.get("overlap", {}) for v, d in res.get("voters", {}).items()}
    out["_results"] = [
        {"system": nice,
         "P": ex[v].get("precision"), "R": ex[v].get("recall"),
         "F1": ex[v].get("f1"),
         "95% CI": f"[{ex[v]['f1_ci95'][0]:.3f}, {ex[v]['f1_ci95'][1]:.3f}]"
                   if ex[v].get("f1_ci95") else "",
         "F1 (overlap)": ov[v].get("f1"),
         # Computed from the run's own timings rather than pasted in by hand.
         # The latency spread is the single most useful number in Block 3 for an
         # audience deciding what they could actually run over a whole corpus,
         # and it should not depend on someone remembering to fill it in.
         "ms/passage": round(1000 * sum(elapsed[v]) / len(elapsed[v]), 1)
                       if elapsed.get(v) else None}
        for v, nice in NICE if v in ex
    ]
    out["_meta"] = {
        "n_passages": res.get("n_passages"),
        "n_gold_spans": res.get("n_gold_spans"),
        "n_negative_passages": res.get("n_negative_passages"),
        "layer_shown": a.layer,
        "note": "Real outputs from the LD80 panel run. Scored against the "
                "<cdplace> human gold standard, binary span detection.",
    }

    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"wrote {a.out}")
    print(f"  {len(per)} passages x {len(out['_layer_counts'])} systems")
    print(f"  scored on {res.get('n_gold_spans')} gold spans in "
          f"{res.get('n_passages')} passages")
    timed = [r for r in out["_results"] if r["ms/passage"] is not None]
    if timed:
        fast = min(timed, key=lambda r: r["ms/passage"])
        slow = max(timed, key=lambda r: r["ms/passage"])
        ratio = slow["ms/passage"] / fast["ms/passage"]
        print(f"\n  latency spread: {fast['system']} {fast['ms/passage']:,.0f} ms "
              f"vs {slow['system']} {slow['ms/passage']:,.0f} ms  ({ratio:,.0f}x)")
    else:
        print("\n  ! no elapsed_s in the panel file; ms/passage left null.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
