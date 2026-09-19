"""
spanpanel.py
------------
Multi-voter span annotation: pooling, aggregation, calibration.

The three operations that have to be right:

1. cluster_spans   pool overlapping proposals from N voters into decision items
2. dawid_skene     estimate per-voter reliability and a posterior label per item
3. calibrate       turn agreement level into an empirical precision/coverage curve

Everything here is pure Python plus numpy. No model calls, no network.
Model adapters live in panel_adapters.py so this file stays testable offline.

Grounding:
  Pooled evaluation ......... Zobel, SIGIR 1998; TREC pooling methodology
  Aggregation ............... Dawid & Skene, JRSS-C 1979
  Self-preference bias ...... Panickssery, Bowman & Feng, NeurIPS 2024
  Validation requirement .... Pangakis, Wolken & Fasching, 2023
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Iterable, Sequence

import numpy as np

ABSTAIN = "NONE"   # voter proposed nothing overlapping this cluster


# --------------------------------------------------------------------------
# data model
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Span:
    passage_id: str
    start: int
    end: int
    label: str
    text: str = ""
    voter: str = ""

    def overlap(self, other: "Span") -> int:
        return max(0, min(self.end, other.end) - max(self.start, other.start))

    def iou(self, other: "Span") -> float:
        if self.passage_id != other.passage_id:
            return 0.0
        inter = self.overlap(other)
        if inter == 0:
            return 0.0
        union = (self.end - self.start) + (other.end - other.start) - inter
        return inter / union if union else 0.0


@dataclass
class Cluster:
    """One decision item: a region of text that at least one voter marked."""
    passage_id: str
    start: int
    end: int
    text: str
    votes: dict[str, str] = field(default_factory=dict)      # voter -> label or ABSTAIN
    members: list[Span] = field(default_factory=list)
    gold: str | None = None                                   # set during adjudication

    # ---- agreement summaries -------------------------------------------------
    def n_proposing(self) -> int:
        return sum(1 for v in self.votes.values() if v != ABSTAIN)

    def modal_label(self) -> str:
        counts = Counter(v for v in self.votes.values() if v != ABSTAIN)
        return counts.most_common(1)[0][0] if counts else ABSTAIN

    def agreement(self) -> int:
        """How many voters back the modal label."""
        return sum(1 for v in self.votes.values() if v == self.modal_label())

    def unanimous(self) -> bool:
        return self.agreement() == len(self.votes)

    def extent_disagreement(self) -> bool:
        """True when proposing voters chose different character boundaries."""
        spans = {(m.start, m.end) for m in self.members}
        return len(spans) > 1

    def stratum(self) -> str:
        """Which adjudication stratum this item falls into."""
        if self.unanimous() and not self.extent_disagreement():
            return "A_unanimous"
        return "B_contested"


# --------------------------------------------------------------------------
# 1. pooling
# --------------------------------------------------------------------------

def same_annotation(a: Span, b: Span, iou_threshold: float = 0.5,
                    containment_threshold: float = 0.8) -> bool:
    """Do two proposals refer to the same underlying annotation?

    IoU ALONE IS NOT ENOUGH, and this cost me a test. "Pooley" inside "Pooley
    Bridge" has IoU 6/13 = 0.46, just under a 0.5 threshold, so pure IoU splits
    a boundary dispute into two decision items: the adjudicator sees it twice and
    the agreement counts are wrong (5/7 rather than 6/7 proposing something).
    The same applies to the case the keynote is built on, "coast" inside "the
    Adriatic coast" (IoU 0.29).

    So also merge on the overlap coefficient, overlap / len(shorter). Nesting
    gives 1.0 and always merges, which is what a boundary dispute should do.
    Disjoint spans overlap by 0 and never merge. This mirrors partial-match
    conventions in NER evaluation (MUC, SemEval-2013).
    """
    inter = a.overlap(b)
    if inter == 0 or a.passage_id != b.passage_id:
        return False
    if a.iou(b) >= iou_threshold:
        return True
    shorter = min(a.end - a.start, b.end - b.start)
    return shorter > 0 and inter / shorter >= containment_threshold


def cluster_spans(
    by_voter: dict[str, Sequence[Span]],
    iou_threshold: float = 0.5,
    containment_threshold: float = 0.8,
) -> list[Cluster]:
    """Pool proposals from all voters into decision items.

    Single-link clustering within a passage, using same_annotation(). A boundary
    dispute becomes ONE contested item rather than two: the panel should surface
    the disagreement, not double-count it.

    Voters absent from a cluster are recorded as ABSTAIN, which is informative
    (they read the text and declined) rather than missing.
    """
    voters = list(by_voter.keys())
    all_spans: list[Span] = []
    for voter, spans in by_voter.items():
        for s in spans:
            all_spans.append(Span(s.passage_id, s.start, s.end, s.label, s.text, voter))

    by_passage: dict[str, list[Span]] = defaultdict(list)
    for s in all_spans:
        by_passage[s.passage_id].append(s)

    clusters: list[Cluster] = []
    for pid, spans in sorted(by_passage.items()):
        spans = sorted(spans, key=lambda s: (s.start, s.end))
        groups: list[list[Span]] = []
        for s in spans:
            placed = False
            for g in groups:
                if any(same_annotation(s, m, iou_threshold, containment_threshold)
                       for m in g):
                    g.append(s)
                    placed = True
                    break
            if not placed:
                groups.append([s])

        for g in groups:
            start = min(m.start for m in g)
            end = max(m.end for m in g)
            longest = max(g, key=lambda m: m.end - m.start)
            votes = {v: ABSTAIN for v in voters}
            for m in g:
                # a voter proposing twice in one cluster keeps its widest proposal
                if votes[m.voter] == ABSTAIN:
                    votes[m.voter] = m.label
            clusters.append(Cluster(pid, start, end, longest.text, votes, list(g)))

    clusters.sort(key=lambda c: (c.passage_id, c.start, c.end))
    return clusters


# --------------------------------------------------------------------------
# 2. Dawid-Skene
# --------------------------------------------------------------------------

REJECT = "REJECT"   # latent: there is genuinely no annotation here


def dawid_skene(
    clusters: Sequence[Cluster],
    labels: Sequence[str] | None = None,
    max_iter: int = 200,
    tol: float = 1e-7,
    seed: int = 2026,
    reject_kappa: float = 50.0,
) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray, list[str]]:
    """EM estimation of latent labels and per-voter confusion matrices.

    Why not majority vote: majority vote weights a 7B open-weight model exactly
    as heavily as a frontier model, and weights a deterministic rule system with
    1.00 precision the same as a model that over-proposes. Dawid-Skene learns
    each voter's error profile from the disagreement structure itself, with no
    gold labels required.

    The latent space and the observed space are DIFFERENT, and this matters.
    A voter can emit ABSTAIN (it proposed nothing here), but ABSTAIN is not a
    thing a span can truly BE. The latent counterpart is REJECT: the cluster is
    spurious, nobody should have marked it. Treating ABSTAIN as a candidate true
    label puts probability mass on a class that cannot occur, and the aggregate
    then loses to plain majority vote.

      latent   : real labels + REJECT
      observed : real labels + ABSTAIN
      error[v] : (n_latent, n_observed), rows sum to 1

    REJECT needs an identifying constraint or it is unidentifiable: nothing in
    the vote pattern alone distinguishes "spurious cluster" from "real label,
    several abstentions", and unconstrained EM happily parks 12% of the mass
    there, turning 5-of-7 agreements into rejections. The constraint is the
    definition of REJECT itself: if there is truly nothing here, a voter should
    ABSTAIN. `reject_kappa` is the Dirichlet strength of that belief. Raise it
    if the panel is over-rejecting; drop it toward 0 to recover unconstrained EM.

    Returns
      posterior : (n_items, n_latent) probability of each latent label
      error     : voter -> (n_latent, n_observed) confusion
      prior     : (n_latent,) class prevalence
      latent    : latent label ordering used by the arrays
    """
    voters = list(clusters[0].votes.keys()) if clusters else []
    if labels is None:
        seen = {v for c in clusters for v in c.votes.values()}
        labels = sorted(seen - {ABSTAIN})
    real = [l for l in labels if l not in (ABSTAIN, REJECT)]

    latent = real + [REJECT]
    observed = real + [ABSTAIN]
    Lt, Lo = len(latent), len(observed)
    oidx = {lab: i for i, lab in enumerate(observed)}
    n = len(clusters)

    obs = np.full((n, len(voters)), oidx[ABSTAIN], dtype=int)
    for i, c in enumerate(clusters):
        for j, v in enumerate(voters):
            obs[i, j] = oidx.get(c.votes.get(v, ABSTAIN), oidx[ABSTAIN])

    # initialise from the observed vote distribution; REJECT seeded from the
    # abstention rate, so single-voter clusters start out looking spurious
    rng = np.random.default_rng(seed)
    post = np.zeros((n, Lt))
    for i in range(n):
        counts = np.bincount(obs[i], minlength=Lo).astype(float)
        real_counts = counts[:len(real)]
        post[i, :len(real)] = real_counts
        post[i, -1] = counts[oidx[ABSTAIN]] * 0.5
        post[i] += rng.random(Lt) * 1e-6
        post[i] /= post[i].sum()

    prior = np.full(Lt, 1.0 / Lt)
    error = {v: np.full((Lt, Lo), 1.0 / Lo) for v in voters}
    prev_ll = -np.inf

    for _ in range(max_iter):
        # M step
        prior = post.sum(axis=0) + 1e-9
        prior /= prior.sum()
        for j, v in enumerate(voters):
            m = np.zeros((Lt, Lo))
            for i in range(n):
                m[:, obs[i, j]] += post[i]
            # identifying prior on the REJECT row: truly-absent spans draw
            # abstentions, not labels
            m[-1, oidx[ABSTAIN]] += reject_kappa
            m[-1, :len(real)] += reject_kappa * 0.02
            m += 1e-9
            error[v] = m / m.sum(axis=1, keepdims=True)

        # E step
        logp = np.log(prior)[None, :].repeat(n, axis=0)
        for j, v in enumerate(voters):
            logp += np.log(error[v][:, obs[:, j]]).T
        mx = logp.max(axis=1, keepdims=True)
        p = np.exp(logp - mx)
        post = p / p.sum(axis=1, keepdims=True)

        ll = float((mx.ravel() + np.log(p.sum(axis=1))).sum())
        if abs(ll - prev_ll) < tol:
            break
        prev_ll = ll

    return post, error, prior, latent


def voter_reliability(error: dict[str, np.ndarray], latent: Sequence[str]) -> dict[str, dict[str, float]]:
    """Per-voter accuracy and coverage, reported SEPARATELY.

    An earlier version of this took the raw confusion diagonal, which scored a
    rule system with perfect precision and 25% recall as the worst voter on the
    panel. That conflates two different things, and the distinction is exactly
    the rules-versus-LLM story the keynote is about:

      accuracy : given this voter proposed a label, how often is it right?
                 (confusion row renormalised with the ABSTAIN column removed)
      coverage : how often does this voter propose anything at all?
                 (1 - P(ABSTAIN | true label is a real label))

    A deterministic gazetteer should come out near accuracy 1.0, coverage 0.2.
    A frontier model should come out high on both. Reporting one number would
    hide the trade.
    """
    real = [l for l in latent if l != REJECT]
    out: dict[str, dict[str, float]] = {}
    for v, m in error.items():
        accs, covs = [], []
        for i, _lab in enumerate(real):          # rows: latent real labels
            row = m[i]
            spoke = float(row[:len(real)].sum())  # observed real labels only
            covs.append(spoke)
            accs.append(float(row[i] / spoke) if spoke > 1e-12 else float("nan"))
        out[v] = {
            "accuracy": float(np.nanmean(accs)),
            "coverage": float(np.mean(covs)),
        }
    return out


# --------------------------------------------------------------------------
# 3. calibration
# --------------------------------------------------------------------------

def calibration_curve(clusters: Sequence[Cluster]) -> list[dict]:
    """Agreement threshold -> precision and coverage, measured against gold.

    Only clusters with .gold set contribute. Precision is measured on the
    adjudicated sample; coverage is the share of ALL clusters the threshold
    would auto-accept. That combination is what lets you choose an operating
    point honestly: precision from the judged subset, coverage from everything.
    """
    n_voters = len(clusters[0].votes) if clusters else 0
    judged = [c for c in clusters if c.gold is not None]
    rows = []
    for k in range(1, n_voters + 1):
        at_k = [c for c in judged if c.agreement() >= k]
        correct = sum(1 for c in at_k if c.modal_label() == c.gold)
        auto = [c for c in clusters if c.agreement() >= k]
        rows.append({
            "threshold": k,
            "judged_at_threshold": len(at_k),
            "precision": correct / len(at_k) if at_k else None,
            "coverage": len(auto) / len(clusters) if clusters else 0.0,
            "n_auto_accepted": len(auto),
            "review_burden": 1 - (len(auto) / len(clusters)) if clusters else 1.0,
        })
    return rows


def bootstrap_ci(values: Sequence[float], n_boot: int = 10000, seed: int = 2026,
                 alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap interval. Use this instead of reporting bare F1."""
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return (float("nan"), float("nan"))
    means = rng.choice(arr, size=(n_boot, arr.size), replace=True).mean(axis=1)
    return (float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)))


# --------------------------------------------------------------------------
# adjudication queue
# --------------------------------------------------------------------------

def build_adjudication_queue(clusters: Sequence[Cluster], sample_unanimous: int = 40,
                             seed: int = 2026) -> dict[str, list[Cluster]]:
    """Split clusters into the two strata a human actually has to look at.

    Stratum C (spans NO voter proposed) cannot be produced from this data by
    definition. It requires reading raw passages blind. See PANEL_PLAN.md.
    """
    rng = np.random.default_rng(seed)
    unan = [c for c in clusters if c.stratum() == "A_unanimous"]
    cont = [c for c in clusters if c.stratum() == "B_contested"]
    if len(unan) > sample_unanimous:
        pick = rng.choice(len(unan), size=sample_unanimous, replace=False)
        unan_sample = [unan[i] for i in sorted(pick)]
    else:
        unan_sample = unan
    return {"A_unanimous_sample": unan_sample, "B_contested": cont,
            "A_unanimous_all": unan}


def queue_to_jsonl(queue: Sequence[Cluster], path: str, passages: dict[str, str] | None = None) -> None:
    """Write an adjudication queue a human can work through quickly."""
    with open(path, "w", encoding="utf-8") as f:
        for c in queue:
            rec = {
                "passage_id": c.passage_id,
                "start": c.start,
                "end": c.end,
                "text": c.text,
                "votes": c.votes,
                "modal_label": c.modal_label(),
                "agreement": c.agreement(),
                "extent_disagreement": c.extent_disagreement(),
                "gold": None,          # <- the human fills this
                "note": "",
            }
            if passages and c.passage_id in passages:
                src = passages[c.passage_id]
                lo, hi = max(0, c.start - 60), min(len(src), c.end + 60)
                rec["context"] = src[lo:hi]
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
