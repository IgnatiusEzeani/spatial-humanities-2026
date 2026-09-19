#!/usr/bin/env python3
"""
run_panel_sh2026.py
-------------------
The actual run. Assumes preflight.py exited 0.

    python3 run_panel_sh2026.py panel_config.json passages.jsonl

passages.jsonl: one {"passage_id": "...", "text": "...", "source": "cldw|vha_synthetic",
"stratum": "..."} per line.

Writes:
    panel_<run_id>.jsonl          raw per-voter output, resumable
    queue_A_unanimous.jsonl       40 sampled unanimous items to verify
    queue_B_contested.jsonl       every contested item, adjudicate all
    stratum_C_passages.txt        25 passages to read blind
    panel_summary.json            counts, agreement distribution, failure rates
"""
from __future__ import annotations
import json, sys, random
from pathlib import Path
import panel_voters as PV
from panel_adapters import run_panel, load_panel_output, prompt_fingerprint
from spanpanel import (cluster_spans, build_adjudication_queue, queue_to_jsonl,
                       dawid_skene, voter_reliability)

def main(cfg_path: str, passages_path: str) -> int:
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    specs = PV.load_specs(cfg_path)
    run_id = cfg.get("run_id", "panel_v1")

    passages, meta = {}, {}
    for line in open(passages_path, encoding="utf-8"):
        r = json.loads(line)
        passages[r["passage_id"]] = r["text"]
        meta[r["passage_id"]] = r
    print(f"{len(passages)} passages · fingerprint {prompt_fingerprint()}")

    voters = [PV.build_generative(s) for s in specs if s.enabled]

    # Non-generative voters depend on optional packages. A missing one must NOT
    # abort the run: the generative voters are the expensive part and they are
    # already built. Warn, skip, record the skip, carry on.
    ng = cfg.get("non_generative", {})
    skipped: list[str] = []

    def try_add(name: str, build) -> None:
        try:
            voters.append(build())
        except ImportError as exc:
            skipped.append(f"{name} (missing package: {exc.name})")
        except Exception as exc:                                  # noqa: BLE001
            skipped.append(f"{name} ({exc!r})")

    if "hf_ner" in ng:
        try_add("hf_ner", lambda: PV.build_hf_ner_voter(
            model_id=ng["hf_ner"].get("model_id", "dslim/bert-base-NER"),
            revision=ng["hf_ner"].get("revision")))

    # ANY key beginning "spacy" becomes a voter, so an ablation is one config
    # entry rather than a code change:
    #   "spacy_hybrid": {"model": "en_core_web_trf", "gazetteer_json": "..."}
    #   "spacy_bare":   {"model": "en_core_web_trf"}
    # The pair isolates exactly what the curated gazetteer contributes.
    for key in sorted(k for k in ng if k.startswith("spacy")):
        cfg_s = ng[key]
        gaz = None
        gp = cfg_s.get("gazetteer_json")
        if gp:
            if not Path(gp).exists():
                skipped.append(f"{key} (gazetteer not found: {gp})")
                continue
            gaz = json.load(open(gp, encoding="utf-8"))
        name = cfg_s.get("name") or (
            "spacy_trf_hybrid" if gaz else "spacy_trf_bare")
        try_add(name, lambda c=cfg_s, g=gaz, n=name: PV.build_spacy_hybrid_voter(
            gazetteer=g, name=n, model=c.get("model", "en_core_web_trf"),
            pymusas_pipeline=c.get("pymusas")))

    # The rules voter needs YOUR annotator. Give it an import path in the config
    # rather than editing this file:
    #   "rules": {"import": "spatio_textual:RuleAnnotator",
    #             "kwargs": {"gazetteer_path": "..."},
    #             "revision": "gazetteer_v1"}
    if "rules" in ng and ng["rules"].get("import"):
        spec_r = ng["rules"]

        def make_rules():
            mod_name, _, attr = spec_r["import"].partition(":")
            import importlib
            obj = getattr(importlib.import_module(mod_name), attr)
            inst = obj(**spec_r.get("kwargs", {})) if callable(obj) else obj
            return PV.build_rules_voter(inst,
                                        revision=spec_r.get("revision", "rules"))

        try_add("rules", make_rules)
    elif "rules" in ng:
        skipped.append("rules (no `import` key in config: see the comment above)")

    print(f"{len(voters)} voters: " + ", ".join(v.name for v in voters))
    for s_ in skipped:
        print(f"  ! SKIPPED {s_}")
    if skipped:
        print("  These are recorded as absent. Fix and re-run to add them: "
              "run_panel resumes, so already-completed voters are not repeated.")
    if not voters:
        print("no voters could be built. Nothing to do.")
        return 1

    # contamination: a model must not vote on passages it generated
    excl = {s.name: set(s.excluded_passages) for s in specs}
    for v in voters:
        if excl.get(v.name):
            print(f"  ! {v.name} excluded from {len(excl[v.name])} passage(s)")

    raw = f"panel_{run_id}.jsonl"
    rep = run_panel(voters, passages, raw)
    print(f"\nrun complete · {rep['n_failures']} ungrounded quotes")

    by_voter = load_panel_output(raw)
    for name, banned in excl.items():
        if banned and name in by_voter:
            by_voter[name] = [s for s in by_voter[name] if s.passage_id not in banned]

    clusters = cluster_spans(by_voter)
    n = len(clusters)
    if n == 0:
        print("\nNo spans were returned by any voter. Check panel_*.jsonl: every "
              "record will have an empty `spans` list and a `n_failed_quotes` "
              "count. Nothing to adjudicate.")
        return 1
    q = build_adjudication_queue(clusters, sample_unanimous=40)
    queue_to_jsonl(q["A_unanimous_sample"], "queue_A_unanimous.jsonl", passages)
    queue_to_jsonl(q["B_contested"], "queue_B_contested.jsonl", passages)

    rng = random.Random(2026)
    cpick = rng.sample(sorted(passages), min(25, len(passages)))
    with open("stratum_C_passages.txt", "w", encoding="utf-8") as f:
        for pid in cpick:
            f.write(f"### {pid}\n{passages[pid]}\n\n")

    try:
        post, err, prior, latent = dawid_skene(clusters)
        rel = voter_reliability(err, latent)
    except Exception as exc:                                   # noqa: BLE001
        print(f"\n  aggregation skipped: {exc!r}")
        rel = {}

    agree = {}
    for c in clusters:
        agree[c.agreement()] = agree.get(c.agreement(), 0) + 1

    n_unan = len(q["A_unanimous_all"])
    burden = len(q["B_contested"]) / n if n else 0
    summary = {
        "run_id": run_id, "fingerprint": prompt_fingerprint(),
        "n_passages": len(passages), "n_clusters": n,
        "n_unanimous": n_unan, "n_contested": len(q["B_contested"]),
        "adjudication_burden": round(burden, 4),
        "agreement_distribution": dict(sorted(agree.items())),
        "voter_profiles": {k: {kk: round(vv, 4) for kk, vv in v.items()}
                           for k, v in rel.items()},
        "ungrounded_quotes": rep["n_failures"],
    }
    json.dump(summary, open("panel_summary.json", "w"), indent=2)

    print(f"\n{n} decision items · {n_unan} unanimous ({100*n_unan/n:.0f}%) "
          f"· {len(q['B_contested'])} contested ({100*burden:.0f}%)")
    print("\nvoter profiles (estimated WITHOUT gold):")
    for k, v in sorted(rel.items(), key=lambda x: -x[1]["accuracy"]):
        print(f"  {k:16s} accuracy {v['accuracy']:.3f}  coverage {v['coverage']:.3f}")
    print(f"\nYou now adjudicate {len(q['A_unanimous_sample'])} + "
          f"{len(q['B_contested'])} items, and read 25 passages for stratum C.")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
