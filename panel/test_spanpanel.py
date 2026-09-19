"""Tests with a scenario where the right answer is known by construction."""
import numpy as np
from spanpanel import (Span, cluster_spans, dawid_skene, voter_reliability,
                       calibration_curve, build_adjudication_queue, bootstrap_ci, ABSTAIN)

P = "From Penrith two roads lead to Pooley Bridge, about six miles distant, which spans the Eamont just at its issue from Ulleswater."
def sp(t, lab, voter="", pid="p1"):
    i = P.index(t); return Span(pid, i, i+len(t), lab, t, voter)

# --- 1. clustering: boundary dispute must become ONE contested item ----------
by_voter = {
  "gpt":    [sp("Penrith","TOPONYM"), sp("Pooley Bridge","TOPONYM"), sp("Ulleswater","TOPONYM")],
  "claude": [sp("Penrith","TOPONYM"), sp("Pooley Bridge","TOPONYM"), sp("Ulleswater","TOPONYM")],
  "gemini": [sp("Penrith","TOPONYM"), sp("Pooley Bridge","TOPONYM")],
  "qwen":   [sp("Penrith","TOPONYM"), sp("Pooley Bridge","GEONOUN")],
  "small":  [sp("Penrith","TOPONYM")],
  "hf":     [sp("Penrith","TOPONYM"), sp("Pooley Bridge","TOPONYM"), sp("Eamont","TOPONYM")],
  "rules":  [sp("Penrith","TOPONYM")],
}
cl = cluster_spans(by_voter)
assert len(cl) == 4, [(c.text, c.n_proposing()) for c in cl]
by_text = {c.text: c for c in cl}
assert by_text["Penrith"].unanimous(), by_text["Penrith"].votes
assert by_text["Penrith"].stratum() == "A_unanimous"
assert by_text["Pooley Bridge"].stratum() == "B_contested"      # qwen says GEONOUN
assert by_text["Pooley Bridge"].agreement() == 4                # 4 of 7 back TOPONYM
assert by_text["Ulleswater"].n_proposing() == 2
assert by_text["Ulleswater"].votes["rules"] == ABSTAIN
print("clustering OK:", [(c.text, c.agreement(), c.stratum()) for c in cl])

# boundary dispute merges rather than duplicating
bd = cluster_spans({"a":[sp("Pooley Bridge","TOPONYM")], "b":[sp("Pooley","TOPONYM")]}, iou_threshold=0.4)
assert len(bd) == 1 and bd[0].extent_disagreement(), bd
print("boundary dispute merged into one contested item: OK")

# --- 2. Dawid-Skene: must down-weight a known-bad voter ---------------------
rng = np.random.default_rng(7)
LABELS = ["TOPONYM","GEONOUN",ABSTAIN]
truth = rng.choice(["TOPONYM","GEONOUN"], size=600, p=[0.7,0.3])
acc = {"gpt":.95,"claude":.94,"gemini":.90,"qwen":.85,"small":.55,"hf":.88,"rules":.99}
prop = {"gpt":.95,"claude":.95,"gemini":.92,"qwen":.90,"small":.80,"hf":.85,"rules":.25}  # rules: high acc, low recall
clusters=[]
from spanpanel import Cluster
for i,t in enumerate(truth):
    votes={}
    for v in acc:
        if rng.random() > prop[v]: votes[v]=ABSTAIN
        elif rng.random() < acc[v]: votes[v]=t
        else: votes[v]="GEONOUN" if t=="TOPONYM" else "TOPONYM"
    c=Cluster("p%d"%i,0,5,"x",votes); c.gold=t; clusters.append(c)

post, err, prior, labs = dawid_skene(clusters, ["TOPONYM","GEONOUN"])
rel = voter_reliability(err, labs)
print("estimated voter profiles (no gold used):")
for k,v in sorted(rel.items(), key=lambda x:-x[1]["accuracy"]):
    print("   %-8s accuracy %.3f  coverage %.3f   (true: acc %.2f cov %.2f)"%(k,v["accuracy"],v["coverage"],acc[k],prop[k]))
# accuracy must track the TRUE accuracy, not the propensity to speak
order_est=[k for k,_ in sorted(rel.items(), key=lambda x:-x[1]["accuracy"])]
order_true=[k for k,_ in sorted(acc.items(), key=lambda x:-x[1])]
assert order_est[0] in order_true[:2], (order_est, order_true)
assert rel["small"]["accuracy"] == min(v["accuracy"] for v in rel.values()), rel
assert rel["rules"]["accuracy"] > rel["small"]["accuracy"] + 0.2, rel   # the earlier bug
assert rel["rules"]["coverage"] == min(v["coverage"] for v in rel.values()), rel
assert abs(rel["rules"]["coverage"] - prop["rules"]) < 0.12, rel["rules"]

pred=[labs[i] for i in post.argmax(1)]
ds_acc=np.mean([p==t for p,t in zip(pred,truth)])
mv_acc=np.mean([c.modal_label()==c.gold for c in clusters])
print(f"Dawid-Skene {ds_acc:.4f} vs majority vote {mv_acc:.4f}")
assert ds_acc >= mv_acc, (ds_acc, mv_acc)

# --- 3. calibration: precision must fall as threshold falls -----------------
rows = calibration_curve(clusters)
precs=[r["precision"] for r in rows if r["precision"] is not None]
print("calibration:"); [print("  k=%d prec=%.3f cov=%.3f burden=%.3f"%(r["threshold"],r["precision"],r["coverage"],r["review_burden"])) for r in rows if r["precision"]]
assert rows[-1]["precision"] >= rows[0]["precision"] - 1e-9
assert rows[0]["coverage"] == 1.0
cov=[r["coverage"] for r in rows]; assert cov == sorted(cov, reverse=True)

# --- 4. queue + bootstrap ---------------------------------------------------
q = build_adjudication_queue(clusters, sample_unanimous=40)
assert len(q["A_unanimous_sample"]) <= 40
assert len(q["A_unanimous_all"]) + len(q["B_contested"]) == len(clusters)
print("adjudication: %d unanimous (sample 40), %d contested -> human sees %d of %d (%.0f%%)"
      % (len(q["A_unanimous_all"]), len(q["B_contested"]),
         len(q["A_unanimous_sample"])+len(q["B_contested"]), len(clusters),
         100*(len(q["A_unanimous_sample"])+len(q["B_contested"]))/len(clusters)))
lo,hi = bootstrap_ci([1.0]*35+[0.0]*8)
print("bootstrap 95%% CI on 43 items at .814: [%.3f, %.3f]"%(lo,hi))
lo2,hi2 = bootstrap_ci(([1.0]*35+[0.0]*8)*8)
print("bootstrap 95%% CI on 344 items:        [%.3f, %.3f]"%(lo2,hi2))
assert (hi-lo) > (hi2-lo2)
print("\nALL TESTS PASSED")
