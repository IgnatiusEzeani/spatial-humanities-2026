#!/usr/bin/env python3
"""
preflight.py
------------
Send ONE passage to every voter and report exactly what came back.

Run this before the paid run. It costs pennies and it is the only thing standing
between you and discovering at passage 240 of 400 that one provider rejects
`temperature`, or that an open-weight endpoint does not support json_schema.

    python3 preflight.py panel_config.json

Exit code 0 means every enabled voter returned usable spans.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback

import panel_voters as PV
from panel_adapters import prompt_fingerprint

PASSAGE = (
    "From Penrith two roads lead to Pooley Bridge, about six miles distant, "
    "which spans the Eamont just at its issue from Ulleswater."
)
# What a competent voter should find. Not a score, just a sanity floor.
EXPECT_AT_LEAST = {"Penrith", "Pooley Bridge"}


def check_env(specs) -> list[str]:
    missing = []
    for s in specs:
        if not s.enabled:
            continue
        env = s.api_key_env or {
            "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GOOGLE_API_KEY"}.get(s.provider, "")
        if env and not os.environ.get(env):
            missing.append(f"{s.name}: ${env} not set")
    return missing


def main(cfg_path: str) -> int:
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    try:
        specs = PV.load_specs(cfg_path)
    except ValueError as exc:
        print("CONFIG NOT READY\n")
        print(" ", exc)
        return 1

    print(f"prompt fingerprint : {prompt_fingerprint()}")
    print(f"prompt version     : {cfg.get('prompt_version')}")
    print(f"run id             : {cfg.get('run_id')}\n")

    missing = check_env(specs)
    if missing:
        print("MISSING CREDENTIALS")
        for m in missing:
            print("  -", m)
        print()

    rows, failures = [], 0

    for spec in specs:
        if not spec.enabled:
            print(f"{spec.name:16s} SKIPPED (disabled)")
            continue
        try:
            voter = PV.build_generative(spec)
        except Exception as exc:                          # noqa: BLE001
            print(f"{spec.name:16s} BUILD FAILED  {exc!r}")
            failures += 1
            continue

        t0 = time.time()
        try:
            spans, fails = voter.annotate(PASSAGE, "preflight")
        except Exception:                                 # noqa: BLE001
            print(f"{spec.name:16s} CALL RAISED")
            traceback.print_exc()
            failures += 1
            continue
        dt = time.time() - t0

        found = {s.text for s in spans}
        mode = getattr(getattr(voter.call, "mode_state", None), "get", lambda _: None)("mode")
        status = "ok"
        notes = []
        if fails:
            notes.append(f"{len(fails)} ungrounded quote(s): "
                         + ", ".join(f"{f.get('quote')!r}({f['reason']})" for f in fails[:3]))
            if any(f["reason"] == "unrecoverable" for f in fails):
                status = "FAIL"
                failures += 1
        if not EXPECT_AT_LEAST <= found:
            status = "WARN" if status == "ok" else status
            notes.append("missed " + ", ".join(sorted(EXPECT_AT_LEAST - found)))
        if mode and mode != "json_schema":
            notes.append(f"structured-output fallback: {mode}")

        print(f"{spec.name:16s} {status:4s} {dt:6.2f}s  {len(spans):2d} spans  "
              + ", ".join(sorted(found))[:70])
        for n in notes:
            print(f"{'':16s}      ! {n}")
        rows.append({"voter": spec.name, "revision": spec.revision,
                     "status": status, "elapsed_s": round(dt, 3),
                     "spans": [{"text": s.text, "label": s.label} for s in spans],
                     "ungrounded": fails, "structured_mode": mode})

    # non-generative voters
    ng = cfg.get("non_generative", {})
    if "hf_ner" in ng:
        try:
            v = PV.build_hf_ner_voter(revision=ng["hf_ner"].get("revision"))
            spans, _ = v.annotate(PASSAGE, "preflight")
            print(f"{'hf_ner':16s} ok         {len(spans):2d} spans  "
                  + ", ".join(s.text for s in spans)[:70])
            rows.append({"voter": "hf_ner", "revision": v.revision, "status": "ok",
                         "spans": [{"text": s.text, "label": s.label} for s in spans]})
        except Exception as exc:                          # noqa: BLE001
            print(f"{'hf_ner':16s} FAILED  {exc!r}")
            failures += 1
    print(f"\n{'rules':16s} wire up build_rules_voter() with your annotator instance")

    out = f"preflight_{cfg.get('run_id', 'run')}.json"
    json.dump({"fingerprint": prompt_fingerprint(), "rows": rows},
              open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"\nwritten: {out}")

    if failures:
        print(f"\n{failures} voter(s) failed. DO NOT start the paid run.")
        return 1
    print("\nAll enabled voters returned usable spans. Safe to run the panel.")
    print("Copy each voter's true revision string into panel_config.json now, "
          "if the API reported one different from what you recorded.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "panel_config.json"))
