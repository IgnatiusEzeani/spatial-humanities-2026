"""
panel_voters.py
---------------
Provider-specific `call` functions and the factory that assembles the panel.

IMPORTANT, PLEASE READ: everything in this file that touches a network endpoint
is UNTESTED against live APIs, because it was written offline. The JSON parsing,
label harmonisation, config loading and panel assembly ARE tested (see
test_panel_voters.py). Run `preflight.py` before you spend money: it sends one
passage to every voter and reports exactly what came back.

Provider notes worth knowing before you debug:

  OpenAI    Chat Completions + response_format json_schema with strict=True.
            `gpt-5.6-sol` postdates my knowledge, so CHECK TWO THINGS: whether it
            wants the Responses API rather than Chat Completions, and whether it
            accepts `temperature`. Several recent reasoning-tuned models reject
            temperature outright. preflight.py reports the error verbatim.

  Anthropic Structured output via forced tool use. This is the reliable path:
            define one tool whose input_schema IS the schema, then force it with
            tool_choice. The model cannot emit prose around the JSON.

  Gemini    generation_config with response_mime_type=application/json and
            response_schema. Gemini's schema dialect is a subset of JSON Schema
            and rejects `additionalProperties`, so SCHEMA is stripped for it.

  Open      Anything OpenAI-compatible: Together, Fireworks, Groq, DeepInfra,
  weight    vLLM, Ollama. Many support only {"type": "json_object"}, not full
            json_schema. `openai_compatible_call` degrades automatically and
            records which mode it used.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from panel_adapters import SCHEMA, CallableVoter, GenerativeVoter
from spanpanel import Span

# --------------------------------------------------------------------------
# label harmonisation
# --------------------------------------------------------------------------

# Tier 1: span layers that share one prompt, one pooling pass, one adjudication.
# Adding TIME costs almost nothing because it comes back in the same call.
# Tier 2 (sentiment, emotion) is segment classification, handled separately in
# affect_panel.py. Tier 3 (family relations, event arguments) is deferred: it
# needs relation-level adjudication, which is several times the cost.
PANEL_LABELS = ("TOPONYM", "GEONOUN", "RELATION", "DISTANCE", "TIME")

# Non-generative voters emit their own inventories. Map them ONCE, here, and
# record the mapping: it is a methodological decision, not a detail. Anything
# unmapped is dropped rather than guessed, and the drop is counted.
LABEL_MAP: dict[str, str] = {
    # spaCy / OntoNotes
    "GPE": "TOPONYM", "LOC": "TOPONYM", "FAC": "GEONOUN", "NORP": None,
    # CoNLL-2003 (dslim/bert-base-NER)
    "B-LOC": "TOPONYM", "I-LOC": "TOPONYM", "LOCATION": "TOPONYM",
    # spatio_textual project inventory
    "TOPONYM": "TOPONYM", "GEONOUN": "GEONOUN",
    "RELATION": "RELATION", "DISTANCE": "DISTANCE",
    "PLACE": "TOPONYM", "CAMP": "TOPONYM", "CITY": "TOPONYM",
    "COUNTRY": "TOPONYM", "CONTINENT": "TOPONYM",
    # temporal
    "DATE": "TIME", "TIME": "TIME", "EVENT": None,
    # PyMUSAS / USAS semantic tags, if the hybrid emits them
    "M6": "DISTANCE", "N3.7": "DISTANCE", "T1": "TIME", "T1.3": "TIME",
    "Z2": "TOPONYM", "W3": "GEONOUN",
    # explicitly dropped: these are real categories, but not Tier 1
    "PERSON": None, "ORG": None, "CARDINAL": None, "ORDINAL": None,
    "MONEY": None, "PERCENT": None, "QUANTITY": None, "WORK_OF_ART": None,
    "LANGUAGE": None, "LAW": None, "PRODUCT": None,
}


def harmonise(label: str) -> str | None:
    """Map a voter's native label into the panel inventory, or None to drop."""
    if label in PANEL_LABELS:
        return label
    return LABEL_MAP.get(label, LABEL_MAP.get(label.upper()))


# --------------------------------------------------------------------------
# provider call functions:  (system, user, schema) -> raw JSON string
# --------------------------------------------------------------------------

def openai_call(model: str, temperature: float | None = 0.0,
                seed: int | None = 2026, api_key_env: str = "OPENAI_API_KEY",
                base_url: str | None = None, timeout: float = 90.0,
                max_retries: int = 1) -> Callable[[str, str, dict], str]:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ[api_key_env], base_url=base_url,
                    timeout=timeout, max_retries=max_retries)

    def call(system: str, user: str, schema: dict) -> str:
        kwargs: dict[str, Any] = dict(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            response_format={"type": "json_schema", "json_schema": {
                "name": "spatial_spans", "strict": True, "schema": schema}},
        )
        if temperature is not None:
            kwargs["temperature"] = temperature
        if seed is not None:
            kwargs["seed"] = seed
        r = client.chat.completions.create(**kwargs)
        return r.choices[0].message.content

    return call


def anthropic_call(model: str, temperature: float = 0.0,
                   api_key_env: str = "ANTHROPIC_API_KEY",
                   max_tokens: int = 2048) -> Callable[[str, str, dict], str]:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ[api_key_env], timeout=90.0,
                                 max_retries=1)

    def call(system: str, user: str, schema: dict) -> str:
        r = client.messages.create(
            model=model, max_tokens=max_tokens, temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[{"name": "record_spans",
                    "description": "Record the spatial expressions found.",
                    "input_schema": schema}],
            tool_choice={"type": "tool", "name": "record_spans"},
        )
        for block in r.content:
            if getattr(block, "type", None) == "tool_use":
                return json.dumps(block.input)
        raise RuntimeError("no tool_use block returned")

    return call


def gemini_call(model: str, temperature: float = 0.0,
                api_key_env: str = "GOOGLE_API_KEY") -> Callable[[str, str, dict], str]:
    import google.generativeai as genai
    genai.configure(api_key=os.environ[api_key_env])

    def _strip(node: Any) -> Any:
        """Gemini's schema dialect rejects additionalProperties and strict."""
        if isinstance(node, dict):
            return {k: _strip(v) for k, v in node.items()
                    if k not in ("additionalProperties", "strict")}
        if isinstance(node, list):
            return [_strip(v) for v in node]
        return node

    def call(system: str, user: str, schema: dict) -> str:
        m = genai.GenerativeModel(model_name=model, system_instruction=system)
        r = m.generate_content(user, generation_config={
            "temperature": temperature,
            "response_mime_type": "application/json",
            "response_schema": _strip(schema),
        })
        return r.text

    return call


def openrouter_call(model: str, temperature: float = 0.0, seed: int | None = 2026,
                    api_key_env: str = "OPENROUTER_API_KEY",
                    timeout: float = 60.0, max_retries: int = 0,
                    budget_s: float = 150.0,
                    only: list[str] | None = None,
                    quantizations: list[str] | None = None,
                    allow_fallbacks: bool = False,
                    require_parameters: bool = True,
                    force_json_object: bool = False,
                    app_title: str = "SH2026 annotation panel",
                    ) -> Callable[[str, str, dict], str]:
    """One key for every frontier and open-weight model on the panel.

    PIN THE ROUTING. By default OpenRouter load-balances across providers to
    maximise uptime, and two providers can serve the same open-weight model at
    different quantisation. Unpinned, your 400 passages can be answered by
    several different backends at several different precisions, and "we ran
    Qwen2.5-72B" becomes untrue in a way nobody can detect afterwards.

      only               hard allowlist of provider slugs
      allow_fallbacks    False, so the router cannot silently go elsewhere
      quantizations      e.g. ["fp16", "bf16"] for open-weight models
      require_parameters only route to providers that support temperature,
                         seed and structured outputs, so voters are comparable

    Every call records what actually served it on `call.last_meta`, which
    run_panel writes into the output. That, not the slug, is your provenance.
    """
    from openai import OpenAI
    # WITHOUT AN EXPLICIT TIMEOUT the OpenAI client waits ten minutes per call.
    # Combined with the 15-combination degradation ladder below, one cold or
    # overloaded endpoint can hang the whole probe for over two hours with no
    # output. Fail fast and move on.
    client = OpenAI(api_key=os.environ[api_key_env],
                    base_url="https://openrouter.ai/api/v1",
                    timeout=timeout, max_retries=max_retries,
                    default_headers={"X-Title": app_title})

    provider: dict[str, Any] = {"allow_fallbacks": allow_fallbacks,
                                "require_parameters": require_parameters}
    if only:
        provider["only"] = only
    if quantizations:
        provider["quantizations"] = quantizations

    # The ladder below is 3 structured-output modes x 5 parameter sets = 15
    # combinations. At a 90s timeout with one retry that is 45 MINUTES for a
    # single call against a cold endpoint, and GenerativeVoter's own retries
    # multiply it again. That is how a preflight ran overnight.
    #
    # Two guards: a hard wall-clock budget for the whole ladder, and memory of
    # which combinations have already failed, so the ladder is walked once per
    # voter rather than once per passage.
    state: dict[str, Any] = {"mode": None, "params": None,
                             "dead": False, "failed": set()}
    meta: dict[str, Any] = {}

    # Endpoints differ in which parameters they accept, and with
    # require_parameters=True OpenRouter refuses to route when any requested
    # parameter is unsupported (it fails at the "Filter by Parameters" step of
    # the routing funnel, which is NOT a bad provider slug). Anthropic has no
    # `seed`; several reasoning-tuned models reject `temperature`. So degrade
    # in a fixed order and RECORD which combination was used: a voter that ran
    # without a seed is a different condition and belongs in a footnote.
    PARAM_SETS = [
        ("seed+temperature", True, True, True),
        ("temperature_only", False, True, True),
        ("seed_only", True, False, True),
        ("neither", False, False, True),
        ("neither,unpinned_params", False, False, False),
    ]

    def call(system: str, user: str, schema: dict) -> str:
        if state["dead"]:
            raise RuntimeError(
                f"openrouter: {model} has no working configuration "
                f"(established on an earlier call; not retrying)")
        t_start = time.time()
        modes = [] if force_json_object else [
            ("json_schema", {"type": "json_schema", "json_schema": {
                "name": "spatial_spans", "strict": True, "schema": schema}})]
        modes += [("json_object", {"type": "json_object"}), ("prompt_only", None)]
        attempts = [(m, rf, p) for m, rf in modes for p in PARAM_SETS]
        last = None
        for mode, rf, (pname, use_seed, use_temp, require) in attempts:
            if state["mode"] and state["mode"] != mode:
                continue
            if state["params"] and state["params"] != pname:
                continue
            if (mode, pname) in state["failed"]:
                continue
            if time.time() - t_start > budget_s:
                state["dead"] = True
                raise TimeoutError(
                    f"openrouter: {model} exhausted its {budget_s:.0f}s budget "
                    f"without a working configuration. Tried: "
                    f"{sorted(state['failed'])}. Last error: {last!r}")
            try:
                prov = dict(provider)
                prov["require_parameters"] = require
                kwargs: dict[str, Any] = dict(
                    model=model,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user
                               if mode != "prompt_only"
                               else user + "\n\nSchema:\n" + json.dumps(schema)}],
                    extra_body={"provider": prov},
                )
                if use_temp:
                    kwargs["temperature"] = temperature
                if use_seed and seed is not None:
                    kwargs["seed"] = seed
                if rf:
                    kwargs["response_format"] = rf
                r = client.chat.completions.create(**kwargs)
                meta.clear()
                meta.update({
                    "served_model": getattr(r, "model", None),
                    "served_provider": getattr(r, "provider", None)
                                       or (r.model_extra or {}).get("provider"),
                    "generation_id": getattr(r, "id", None),
                    "structured_mode": mode,
                    "params": pname,
                })
                state["mode"] = mode
                state["params"] = pname
                return r.choices[0].message.content
            except Exception as exc:                       # noqa: BLE001
                last = exc
                state["failed"].add((mode, pname))
                state["mode"] = None
                state["params"] = None
        state["dead"] = True
        raise RuntimeError(
            f"openrouter: no working combination of structured-output mode and "
            f"parameters for {model}. Last error: {last!r}")

    call.mode_state = state          # type: ignore[attr-defined]
    call.last_meta = meta            # type: ignore[attr-defined]
    return call


def openai_compatible_call(model: str, base_url: str, api_key_env: str,
                           temperature: float = 0.0, seed: int | None = 2026,
                           force_json_object: bool = False
                           ) -> Callable[[str, str, dict], str]:
    """Together / Fireworks / Groq / DeepInfra / vLLM / Ollama.

    Tries full json_schema first, falls back to json_object, then to a bare
    request with the schema inlined in the prompt. Records which mode worked on
    the function object so the run log can report it.
    """
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get(api_key_env, "not-needed"),
                    base_url=base_url, timeout=90.0, max_retries=1)

    state = {"mode": None}

    def _create(rf: dict | None, system: str, user: str):
        kwargs: dict[str, Any] = dict(
            model=model, temperature=temperature,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}])
        if seed is not None:
            kwargs["seed"] = seed
        if rf:
            kwargs["response_format"] = rf
        return client.chat.completions.create(**kwargs).choices[0].message.content

    def call(system: str, user: str, schema: dict) -> str:
        attempts = [] if force_json_object else [
            ("json_schema", {"type": "json_schema", "json_schema": {
                "name": "spatial_spans", "strict": True, "schema": schema}})]
        attempts += [("json_object", {"type": "json_object"}), ("prompt_only", None)]
        last = None
        for mode, rf in attempts:
            if state["mode"] and state["mode"] != mode:
                continue                       # stick with what worked first time
            try:
                u = user if mode != "prompt_only" else (
                    user + "\n\nSchema:\n" + json.dumps(schema))
                out = _create(rf, system, u)
                state["mode"] = mode
                return out
            except Exception as exc:           # noqa: BLE001
                last = exc
                state["mode"] = None
        raise RuntimeError(f"all structured-output modes failed: {last!r}")

    call.mode_state = state                    # type: ignore[attr-defined]
    return call


# --------------------------------------------------------------------------
# non-generative voters
# --------------------------------------------------------------------------

def build_hf_ner_voter(name: str = "hf_bert_ner",
                       model_id: str = "dslim/bert-base-NER",
                       revision: str | None = None) -> CallableVoter:
    """Pinned transformer NER. `revision` MUST be a commit sha, not 'main'."""
    from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
    kw = {"revision": revision} if revision else {}
    tok = AutoTokenizer.from_pretrained(model_id, **kw)
    mdl = AutoModelForTokenClassification.from_pretrained(model_id, **kw)
    nlp = pipeline("ner", model=mdl, tokenizer=tok, aggregation_strategy="first")

    def fn(text: str) -> list[dict]:
        out = []
        for e in nlp(text):
            lab = harmonise(e["entity_group"])
            if not lab:
                continue
            start, end = int(e["start"]), int(e["end"])

            # NEVER trust e["word"]: it is tokenizer output and comes back as
            # wordpiece fragments ("##rrowdale", "##lvellyn") whenever subword
            # aggregation does not merge cleanly, which on 19th-century place
            # names is often. Slice the ORIGINAL text at the reported offsets
            # instead, and snap to word boundaries so a span cannot begin or end
            # in the middle of a token. Left unfixed this cost the supervised
            # voter ~93 of 808 spans on exact match.
            while start > 0 and (text[start - 1].isalnum() or text[start - 1] == "\u017f"):
                start -= 1
            while end < len(text) and (text[end].isalnum() or text[end] == "\u017f"):
                end += 1
            surface = text[start:end]
            if not surface.strip():
                continue
            out.append({"text": surface, "label": lab,
                        "start_char": start, "end_char": end})

        # snapping can make two adjacent fragments identical; drop duplicates
        seen, uniq = set(), []
        for d in sorted(out, key=lambda x: (x["start_char"], -x["end_char"])):
            k = (d["start_char"], d["end_char"])
            if k not in seen:
                seen.add(k)
                uniq.append(d)
        return uniq

    return CallableVoter(name, f"{model_id}@{revision or 'UNPINNED'}", fn, kind="supervised")


def build_spacy_voter(name: str = "spacy_sm", model: str = "en_core_web_sm") -> CallableVoter:
    import spacy
    nlp = spacy.load(model)
    rev = f"{model}=={nlp.meta.get('version', '?')}"

    def fn(text: str) -> list[dict]:
        out = []
        for e in nlp(text).ents:
            lab = harmonise(e.label_)
            if lab:
                out.append({"text": e.text, "label": lab,
                            "start_char": e.start_char, "end_char": e.end_char})
        return out

    return CallableVoter(name, rev, fn, kind="supervised")


def build_spacy_hybrid_voter(
    gazetteer: Any = None,
    name: str = "spacy_trf_hybrid",
    model: str = "en_core_web_trf",
    pymusas_pipeline: str | None = None,
) -> CallableVoter:
    """en_core_web_trf + project gazetteers (+ optional PyMUSAS).

    This, not `en_core_web_sm`, is the serious non-generative competitor, and it
    is the project's own best system. Benchmarking frontier LLMs against a small
    CNN pipeline would be strawmanning the baseline, and a reviewer would say so.

    `en_core_web_trf` is roberta-base under the hood. On 400 passages it runs in
    a few minutes on CPU. Pin the model version: it goes in the record.

    `gazetteer` may be any object exposing `.lookup(text) -> list[dict]` with
    text/label/start_char/end_char, or a plain {surface_form: label} mapping.
    Gazetteer hits take precedence over the statistical model on overlap, because
    a curated project resource outranks an OntoNotes guess for this domain. That
    is a methodological choice and it belongs in the write-up.
    """
    import spacy
    nlp = spacy.load(model)
    rev = f"{model}=={nlp.meta.get('version', '?')}"
    if pymusas_pipeline:
        nlp.add_pipe("pymusas_rule_based_tagger", source=spacy.load(pymusas_pipeline))
        rev += f"+{pymusas_pipeline}"

    # Accept EITHER a flat {surface: LABEL} map or the layered form
    # {"case_sensitive": {...}, "case_insensitive": {...}}. The layered form is
    # preferred: one case policy for the whole gazetteer is wrong in both
    # directions. Case-sensitive everywhere misses "Sea and shore" and "the Inn
    # at Grasmere" at sentence start; case-insensitive everywhere turns every
    # sentence beginning "March..." into a toponym.
    buckets: list[tuple[dict[str, str], bool]] = []
    if isinstance(gazetteer, dict) and {"case_sensitive", "case_insensitive"} \
            & set(gazetteer):
        for key, ci in (("case_sensitive", False), ("case_insensitive", True)):
            m = gazetteer.get(key) or {}
            if m:
                buckets.append((m, ci))
        rev += f"+gazetteer[layered:{sum(len(m) for m, _ in buckets)}]"
    elif isinstance(gazetteer, dict):
        buckets.append((gazetteer, False))
        rev += f"+gazetteer[flat:{len(gazetteer)}]"
    elif gazetteer is not None:
        rev += "+gazetteer"

    compiled: list[tuple[re.Pattern, dict[str, str], bool]] = []
    for m, ci in buckets:
        # longest surface form first, so "Pooley Bridge" beats "Pooley"
        surfaces = sorted(m, key=len, reverse=True)
        if not surfaces:
            continue
        pat = re.compile(r"\b(" + "|".join(re.escape(s) for s in surfaces) + r")\b",
                         re.IGNORECASE if ci else 0)
        compiled.append((pat, {k.lower(): v for k, v in m.items()} if ci else m, ci))

    def fn(text: str) -> list[dict]:
        hits: list[dict] = []
        if compiled:
            for pat, lookup, ci in compiled:
                for m in pat.finditer(text):
                    surface = m.group(1)
                    lab = harmonise(lookup.get(surface.lower() if ci else surface, ""))
                    if not lab:
                        continue
                    if any(m.start() < h["end_char"] and m.end() > h["start_char"]
                           for h in hits):
                        continue                  # earlier bucket wins on overlap
                    hits.append({"text": surface, "label": lab,
                                 "start_char": m.start(), "end_char": m.end()})
        elif gazetteer is not None and hasattr(gazetteer, "lookup"):
            for d in gazetteer.lookup(text):
                lab = harmonise(d["label"])
                if lab:
                    hits.append({**d, "label": lab})

        taken = [(h["start_char"], h["end_char"]) for h in hits]
        for e in nlp(text).ents:
            lab = harmonise(e.label_)
            if not lab:
                continue
            if any(e.start_char < b and e.end_char > a for a, b in taken):
                continue                      # gazetteer wins on overlap
            hits.append({"text": e.text, "label": lab,
                         "start_char": e.start_char, "end_char": e.end_char})
        return sorted(hits, key=lambda h: h["start_char"])

    return CallableVoter(name, rev, fn, kind="supervised")


def build_rules_voter(annotator: Any, name: str = "rules_gazetteer",
                      revision: str = "gazetteer_v1") -> CallableVoter:
    """Wraps your existing rule annotator.

    Expects `annotator.annotate(text) -> {"spans": [...]}` as in workshop
    notebook 02. If your API differs, change only this function.
    """
    def fn(text: str) -> list[dict]:
        # Accept the shapes a rule annotator plausibly returns, rather than
        # assuming one: {"spans": [...]}, a bare list, or {"entities": [...]}.
        res = annotator.annotate(text)
        if isinstance(res, dict):
            raw = res.get("spans") or res.get("entities") or []
        else:
            raw = res or []
        out = []
        for s in raw:
            lab = harmonise(s.get("label") or s.get("entity_group") or "")
            if not lab:
                continue
            start = s.get("start_char", s.get("start"))
            end = s.get("end_char", s.get("end"))
            if start is None or end is None:
                continue
            out.append({"text": s.get("text") or text[start:end], "label": lab,
                        "start_char": int(start), "end_char": int(end)})
        return out

    return CallableVoter(name, revision, fn, kind="deterministic")


# --------------------------------------------------------------------------
# config + factory
# --------------------------------------------------------------------------

@dataclass
class VoterSpec:
    name: str
    provider: str                       # openai | anthropic | gemini | openai_compatible
    model: str
    revision: str = ""                  # exact snapshot string; REQUIRED for the record
    base_url: str | None = None
    api_key_env: str = ""
    only: list[str] | None = None            # openrouter: hard provider allowlist
    quantizations: list[str] | None = None   # openrouter: e.g. ["fp16", "bf16"]
    allow_fallbacks: bool = False            # openrouter: keep this False
    timeout: float = 60.0                    # seconds per attempt
    budget_s: float = 150.0                  # whole degradation ladder, per voter
    temperature: float | None = 0.0
    seed: int | None = 2026
    force_json_object: bool = False
    enabled: bool = True
    excluded_passages: list[str] = field(default_factory=list)   # contamination


def build_generative(spec: VoterSpec) -> GenerativeVoter:
    if spec.provider == "openai":
        call = openai_call(spec.model, spec.temperature, spec.seed,
                           spec.api_key_env or "OPENAI_API_KEY", spec.base_url)
    elif spec.provider == "anthropic":
        call = anthropic_call(spec.model, spec.temperature or 0.0,
                              spec.api_key_env or "ANTHROPIC_API_KEY")
    elif spec.provider == "gemini":
        call = gemini_call(spec.model, spec.temperature or 0.0,
                           spec.api_key_env or "GOOGLE_API_KEY")
    elif spec.provider == "openrouter":
        call = openrouter_call(spec.model, spec.temperature or 0.0, spec.seed,
                               spec.api_key_env or "OPENROUTER_API_KEY",
                               timeout=spec.timeout, budget_s=spec.budget_s,
                               only=spec.only, quantizations=spec.quantizations,
                               allow_fallbacks=spec.allow_fallbacks,
                               force_json_object=spec.force_json_object)
    elif spec.provider == "openai_compatible":
        if not spec.base_url:
            raise ValueError(f"{spec.name}: openai_compatible needs base_url")
        call = openai_compatible_call(spec.model, spec.base_url, spec.api_key_env,
                                      spec.temperature or 0.0, spec.seed,
                                      spec.force_json_object)
    else:
        raise ValueError(f"{spec.name}: unknown provider {spec.provider!r}")
    return GenerativeVoter(spec.name, spec.revision or spec.model, call)


def load_specs(path: str) -> list[VoterSpec]:
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    specs = [VoterSpec(**{k: v for k, v in s.items() if not k.startswith("_")})
             for s in cfg["voters"]]

    # An empty revision is obviously bad. A PLACEHOLDER revision is worse,
    # because it passes a truthiness check and then sits in the reproducibility
    # record looking like data. Reject both.
    placeholder = ("fill in", "todo", "tbd", "xxx", "changeme", "?")
    bad = [s.name for s in specs if s.enabled and
           (not s.revision or any(p in s.revision.lower() for p in placeholder))]
    if bad:
        raise ValueError(
            "These voters have no usable `revision`: " + ", ".join(bad) +
            ". A bare family name or a placeholder cannot be reproduced. Put the "
            "exact snapshot string from the provider into panel_config.json, then "
            "re-run. This is the field that goes on the reproducibility slide.")

    dupes = {s.name for s in specs if [x.name for x in specs].count(s.name) > 1}
    if dupes:
        raise ValueError(f"duplicate voter names: {sorted(dupes)}")
    return specs
