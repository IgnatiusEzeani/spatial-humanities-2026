#!/usr/bin/env python3
"""
discover_revisions.py
---------------------
Fill in the `revision` field for every voter, by asking.

    python3 discover_revisions.py panel_config_openrouter.json          # report only
    python3 discover_revisions.py panel_config_openrouter.json --write  # patch the file

Costs a few cents: one two-token call per generative voter, plus one HuggingFace
API lookup for the pinned NER model. No passages are annotated.

Why not just write the model name by hand
-----------------------------------------
"claude-opus-5" or "gpt-5.6-sol" is what you ASKED for. What you GOT may be a
dated snapshot, and through an aggregator it may also be a particular upstream
provider at a particular quantisation. The reproducibility slide needs the
second thing. This script reads it off the response.

It also catches, before you spend money on 400 passages:
  * a provider slug in `only` that does not serve that model (with
    allow_fallbacks false this fails loudly, which is what you want)
  * a model that rejects `temperature` or `seed`
  * a voter whose structured-output mode falls back to json_object
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import date

import panel_voters as PV


def hf_revision(model_id: str) -> str | None:
    """Resolve a HuggingFace model id to its current commit sha."""
    try:
        import urllib.request
        with urllib.request.urlopen(
                f"https://huggingface.co/api/models/{model_id}", timeout=20) as r:
            return json.load(r).get("sha")
    except Exception as exc:                                  # noqa: BLE001
        print(f"    could not reach the HuggingFace API: {exc!r}")
        print(f"    fallback:  python3 -c \"from huggingface_hub import HfApi; "
              f"print(HfApi().model_info('{model_id}').sha)\"")
        return None


def list_models(term: str) -> int:
    """Search OpenRouter's live model catalogue. Slugs change; guessing them
    from memory does not work, as the qwen 400s demonstrated."""
    import urllib.request
    with urllib.request.urlopen("https://openrouter.ai/api/v1/models",
                                timeout=30) as r:
        models = json.load(r)["data"]
    hits = [m for m in models if term.lower() in m["id"].lower()
            or term.lower() in (m.get("name") or "").lower()]
    print(f"{len(hits)} of {len(models)} models match {term!r}:\n")
    for m in sorted(hits, key=lambda x: x["id"]):
        ctx = m.get("context_length", "?")
        print(f"  {m['id']:52s} ctx={ctx}")
    if not hits:
        print("  nothing matched. Try a shorter term.")
    return 0


def probe(spec: PV.VoterSpec) -> dict:
    """One minimal call. Returns whatever the provider tells us about itself."""
    out: dict = {"name": spec.name, "model": spec.model, "ok": False}
    try:
        voter = PV.build_generative(spec)
    except Exception as exc:                                  # noqa: BLE001
        out["error"] = f"build failed: {exc!r}"
        return out

    tiny_schema = {
        "type": "object",
        "properties": {"spans": {"type": "array", "items": {
            "type": "object",
            "properties": {"quote": {"type": "string"},
                           "label": {"type": "string", "enum": ["TOPONYM"]}},
            "required": ["quote", "label"], "additionalProperties": False}}},
        "required": ["spans"], "additionalProperties": False,
    }
    try:
        raw = voter.call("You return only JSON.",
                         'Return {"spans":[{"quote":"Penrith","label":"TOPONYM"}]}',
                         tiny_schema)
        out["ok"] = True
        out["sample"] = (raw or "")[:80]
    except Exception as exc:                                  # noqa: BLE001
        out["error"] = repr(exc)
        out["traceback"] = traceback.format_exc(limit=2)

    meta = dict(getattr(voter.call, "last_meta", {}) or {})
    mode = getattr(getattr(voter.call, "mode_state", None), "get", lambda _: None)("mode")
    out["served"] = meta
    out["structured_mode"] = meta.get("structured_mode") or mode
    return out


def compose_revision(spec: PV.VoterSpec, served: dict) -> str:
    """The string that goes on the reproducibility slide."""
    parts = [served.get("served_model") or spec.model]
    if served.get("served_provider"):
        parts.append(f"provider={served['served_provider']}")
    if served.get("params"):
        parts.append(f"params={served['params']}")
    if spec.quantizations:
        parts.append("quant=" + "|".join(spec.quantizations))
    if spec.provider == "openrouter":
        parts.append("via=openrouter")
    parts.append(f"probed={date.today().isoformat()}")
    return "; ".join(parts)


def main(cfg_path: str, write: bool) -> int:
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    # bypass the placeholder guard: filling placeholders in is the whole job here
    specs = [PV.VoterSpec(**{k: v for k, v in s.items() if not k.startswith("_")})
             for s in cfg["voters"]]

    keys = {s.api_key_env or "OPENROUTER_API_KEY" for s in specs if s.enabled}
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        print("MISSING: " + ", ".join(f"${k}" for k in missing))
        return 1

    resolved: dict[str, str] = {}
    failures = 0

    def flush() -> None:
        """Persist whatever has resolved so far.

        The first version only wrote at the very end, so a single hanging
        endpoint threw away every voter that had already succeeded. Write after
        each one instead: probes cost real money and real minutes.
        """
        if not write or not resolved:
            return
        cur = json.load(open(cfg_path, encoding="utf-8"))
        for v in cur["voters"]:
            if v["name"] in resolved:
                v["revision"] = resolved[v["name"]]
        cur.setdefault("non_generative", {}).update(cfg.get("non_generative", {}))
        json.dump(cur, open(cfg_path, "w", encoding="utf-8"), indent=2)

    for spec in specs:
        if not spec.enabled:
            print(f"{spec.name:16s} skipped (disabled)")
            continue
        print(f"{spec.name:16s} probing {spec.model} ...", flush=True)
        try:
            r = probe(spec)
        except KeyboardInterrupt:
            print(f"\n{'':16s} interrupted. {len(resolved)} voter(s) already "
                  f"saved to {cfg_path}. Re-run to continue: resolved voters are "
                  f"skipped only if you remove them, so just let it re-probe.")
            flush()
            return 1
        if not r["ok"]:
            failures += 1
            print(f"{'':16s} FAILED  {r.get('error')}")
            err = str(r.get("error", ""))
            low = err.lower()
            # Read the routing funnel rather than guessing. "Filter by
            # Parameters" means the slug was FINE and a parameter was not.
            if "filter by parameters" in low:
                print(f"{'':16s} -> the provider slug is fine: the funnel reached "
                      f"'Filter by Allowed Providers' with endpoints left, then "
                      f"failed on parameters. This voter's endpoint rejects seed "
                      f"and/or temperature. The adaptive probe should have "
                      f"handled it; if it still fails, set require_parameters "
                      f"false for this voter.")
            elif "allowed providers" in low and "endpoint_count': 0" in low:
                print(f"{'':16s} -> no endpoint survived your `only` allowlist. "
                      f"Fix the provider slug on the model's OpenRouter page.")
            elif "not a valid model id" in low:
                print(f"{'':16s} -> the MODEL SLUG does not exist. Run: "
                      f"python3 discover_revisions.py --list-models qwen")
            elif "404" in low or "not found" in low:
                print(f"{'':16s} -> check both the model slug and the `only` "
                      f"provider slug on the model's OpenRouter page.")
            continue

        if r["served"].get("params") and r["served"]["params"] != "seed+temperature":
            print(f"{'':16s} !   ran with params={r['served']['params']}: this "
                  f"endpoint would not take the full set. Record it.")
        rev = compose_revision(spec, r["served"])
        resolved[spec.name] = rev
        flush()
        print(f"{'':16s} OK  {rev}")
        if r["structured_mode"] and r["structured_mode"] != "json_schema":
            print(f"{'':16s} !   structured output fell back to "
                  f"{r['structured_mode']}: a weaker condition than the others. "
                  f"Footnote it.")

    ng = cfg.setdefault("non_generative", {})
    if "hf_ner" in ng:
        mid = ng["hf_ner"].get("model_id", "dslim/bert-base-NER")
        print(f"{'hf_ner':16s} resolving {mid} ...")
        sha = hf_revision(mid)
        if sha:
            ng["hf_ner"]["revision"] = sha
            print(f"{'':16s} OK  {mid}@{sha}")
        else:
            failures += 1

    if write:
        flush()
        print(f"\nwrote {len(resolved)} revisions into {cfg_path}")
    else:
        print("\n--write not given, nothing changed. Re-run with --write to patch "
              "the config.")

    if failures:
        print(f"\n{failures} voter(s) unresolved. Fix those before preflight.")
        return 1
    print("\nAll voters resolved. Next: python3 preflight.py " + cfg_path)
    return 0


if __name__ == "__main__":
    if "--list-models" in sys.argv:
        i = sys.argv.index("--list-models")
        sys.exit(list_models(sys.argv[i + 1] if len(sys.argv) > i + 1 else ""))
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    sys.exit(main(args[0] if args else "panel_config.json", "--write" in sys.argv))
