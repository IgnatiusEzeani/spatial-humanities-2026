"""Offline tests: everything except the network calls themselves."""
import json, tempfile, os, sys
import panel_voters as PV
from panel_adapters import GenerativeVoter, SCHEMA, ground, run_panel, load_panel_output
from spanpanel import cluster_spans, dawid_skene, voter_reliability, calibration_curve

P = "From Penrith two roads lead to Pooley Bridge, about six miles distant, which spans the Eamont just at its issue from Ulleswater."

# --- label harmonisation ---------------------------------------------------
assert PV.harmonise("GPE") == "TOPONYM"
assert PV.harmonise("LOC") == "TOPONYM"
assert PV.harmonise("FAC") == "GEONOUN"
assert PV.harmonise("TOPONYM") == "TOPONYM"
assert PV.harmonise("NORP") is None, "nationalities must be DROPPED, not guessed"
assert PV.harmonise("PERSON") is None, "unmapped labels must be dropped"
assert PV.harmonise("gpe") == "TOPONYM", "case-insensitive fallback"
print("label harmonisation OK (unmapped -> dropped, never guessed)")

# --- config: refuses unpinned revisions ------------------------------------
p = tempfile.mktemp(suffix=".json")
for label, rev in [("empty",""), ("placeholder","FILL IN exact snapshot"),
                   ("todo","TODO"), ("tbd","tbd")]:
    json.dump({"voters":[{"name":"x","provider":"openai","model":"m","revision":rev}]}, open(p,"w"))
    try:
        PV.load_specs(p); raise SystemExit(f"FAIL: accepted a {label} revision")
    except ValueError as e:
        assert "no usable `revision`" in str(e), str(e)
print("config refuses empty AND placeholder revisions OK")

json.dump({"voters":[{"name":"d","provider":"openai","model":"m","revision":"r1"},
                     {"name":"d","provider":"openai","model":"m","revision":"r2"}]}, open(p,"w"))
try:
    PV.load_specs(p); raise SystemExit("FAIL: accepted duplicate voter names")
except ValueError as e:
    assert "duplicate" in str(e)
print("config refuses duplicate voter names OK")

good = {"voters":[{"name":"x","provider":"openai","model":"m","revision":"m-2026-01-01"},
                  {"name":"y","provider":"openai_compatible","model":"q","revision":"sha",
                   "base_url":"http://h/v1","api_key_env":"K"}]}
json.dump(good, open(p,"w"))
specs = PV.load_specs(p)
assert len(specs)==2 and specs[1].base_url=="http://h/v1"
try:
    PV.build_generative(PV.VoterSpec(name="z",provider="openai_compatible",model="q",revision="r"))
    raise SystemExit("FAIL: accepted openai_compatible with no base_url")
except ValueError as e:
    assert "base_url" in str(e)
print("config validation OK")
os.unlink(p)

# --- the real config file parses and is fully marked -----------------------
cfg = json.load(open(__import__("pathlib").Path(__file__).parent / "panel_config.json"))
names = [v["name"] for v in cfg["voters"]]
assert len(names)==len(set(names)), "duplicate voter names"
unfilled = [v["name"] for v in cfg["voters"] if v["revision"].startswith("FILL IN")]
print(f"panel_config.json: {len(cfg['voters'])} generative + 2 non-generative = 7 voters")
print(f"  revisions still to fill in: {unfilled}")

# --- generative voter with a MOCKED call, incl. the failure modes -----------
def mock(payload, fail_times=0):
    st={"n":0}
    def call(system,user,schema):
        st["n"]+=1
        if st["n"]<=fail_times: raise RuntimeError("transient 429")
        return payload
    return call

good_json = json.dumps({"spans":[{"quote":"Penrith","label":"TOPONYM"},
                                 {"quote":"about six miles distant","label":"DISTANCE"}]})
v = GenerativeVoter("mockA","rev-1",mock(good_json))
spans,fails = v.annotate(P,"p1")
assert len(spans)==2 and not fails
print("generative voter OK:", [(s.text,s.label) for s in spans])

# fenced output must still parse
v2 = GenerativeVoter("mockB","rev-1",mock("```json\n"+good_json+"\n```"))
assert len(v2.annotate(P,"p1")[0])==2
print("markdown fences stripped OK")

# retry then succeed
v3 = GenerativeVoter("mockC","rev-1",mock(good_json,fail_times=2),max_retries=3)
import time; t0=time.time(); s3,f3=v3.annotate(P,"p1")
assert len(s3)==2 and not f3
print(f"retry/backoff OK ({time.time()-t0:.1f}s for 2 failures)")

# unrecoverable -> recorded, not raised
v4 = GenerativeVoter("mockD","rev-1",mock(good_json,fail_times=99),max_retries=2)
s4,f4 = v4.annotate(P,"p1")
assert s4==[] and f4[0]["reason"]=="unrecoverable"
print("unrecoverable failure recorded, run continues OK")

# hallucinated quote caught by grounding
hall = json.dumps({"spans":[{"quote":"Ullswater","label":"TOPONYM"}]})
s5,f5 = GenerativeVoter("mockE","rev-1",mock(hall)).annotate(P,"p1")
assert s5==[] and f5[0]["reason"]=="not_in_passage"
print("silent spelling normalisation caught by grounding OK")

# malformed JSON -> unrecoverable, not a crash
s6,f6 = GenerativeVoter("mockF","rev-1",mock("{not json"),max_retries=1).annotate(P,"p1")
assert s6==[] and f6[0]["reason"]=="unrecoverable"
print("malformed JSON handled OK")

# --- full 7-voter panel, end to end, with mocks ----------------------------
def gv(name, pairs, fail=0):
    return GenerativeVoter(name,"rev", mock(json.dumps(
        {"spans":[{"quote":q,"label":l} for q,l in pairs]}), fail))
def cv(name, pairs):
    from panel_adapters import CallableVoter
    return CallableVoter(name,"rev", lambda t,pp=pairs: [
        {"text":q,"label":l,"start_char":t.index(q),"end_char":t.index(q)+len(q)} for q,l in pp])

panel = [
  gv("gpt_5_6_sol",[("Penrith","TOPONYM"),("Pooley Bridge","TOPONYM"),("Ulleswater","TOPONYM"),("about six miles distant","DISTANCE")]),
  gv("claude",     [("Penrith","TOPONYM"),("Pooley Bridge","TOPONYM"),("Ulleswater","TOPONYM"),("roads","GEONOUN")]),
  gv("gemini_2_5", [("Penrith","TOPONYM"),("Pooley Bridge","TOPONYM"),("Eamont","TOPONYM")]),
  gv("qwen_large", [("Penrith","TOPONYM"),("Pooley Bridge","TOPONYM"),("Ullswater","TOPONYM")]),  # hallucinates
  gv("small_open", [("Penrith","TOPONYM"),("Pooley","TOPONYM")]),                                  # boundary error
  cv("hf_ner",     [("Penrith","TOPONYM"),("Pooley Bridge","TOPONYM"),("Eamont","TOPONYM")]),
  cv("rules",      [("Penrith","TOPONYM")]),
]
out = tempfile.mktemp(suffix=".jsonl")
rep = run_panel(panel, {"p1": P}, out)
cl = cluster_spans(load_panel_output(out))
print(f"\n7-voter panel over 1 passage -> {len(cl)} decision items, {rep['n_failures']} quote failures")
for c in sorted(cl, key=lambda c:-c.agreement()):
    print(f"  {c.text!r:28s} agree={c.agreement()}/7  {c.stratum()}"
          + ("  [extent dispute]" if c.extent_disagreement() else ""))
assert any(c.text=="Penrith" and c.unanimous() for c in cl)
pb=[c for c in cl if "Pooley" in c.text]
assert len(pb)==1 and pb[0].extent_disagreement(), "boundary dispute must merge into ONE item"
assert rep["n_failures"]==1, rep   # the Ullswater hallucination
os.unlink(out)
print("\nALL TESTS PASSED")
