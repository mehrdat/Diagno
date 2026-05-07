"""Metrics for assessing the multi-agent run.

These are *intrinsic* metrics (no ground-truth label needed). For ground-truth
calibration you'd run on a labeled set (e.g. NEJM case challenges) and call
`calibration_against_truth`.
"""
from __future__ import annotations
from collections import defaultdict

from .schemas import DebateState, SatisfactionVote, SpecialistOpinion


def _normalize_name(s: str) -> str:
    return " ".join(s.lower().strip().split())


def hypotheses_per_round(opinions: list[SpecialistOpinion]) -> dict[int, dict[str, float]]:
    """Average probability per (normalized) diagnosis name in each round."""
    by_round: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for o in opinions:
        for h in o.hypotheses:
            by_round[o.round][_normalize_name(h.name)].append(h.probability)
    return {r: {name: sum(ps) / len(ps) for name, ps in d.items()}
            for r, d in by_round.items()}


def hypothesis_stability(opinions: list[SpecialistOpinion]) -> float:
    """Jaccard similarity of top-3 hypothesis sets between consecutive rounds.
    1.0 == perfectly stable. Useful as a 'has the panel converged?' signal."""
    per_round = hypotheses_per_round(opinions)
    rounds = sorted(per_round.keys())
    if len(rounds) < 2:
        return 1.0
    sims = []
    for a, b in zip(rounds, rounds[1:]):
        top_a = set(sorted(per_round[a], key=lambda k: per_round[a][k], reverse=True)[:3])
        top_b = set(sorted(per_round[b], key=lambda k: per_round[b][k], reverse=True)[:3])
        if not top_a and not top_b:
            sims.append(1.0)
            continue
        sims.append(len(top_a & top_b) / max(1, len(top_a | top_b)))
    return sum(sims) / len(sims)


def agreement_per_round(votes: list[list[SatisfactionVote]]) -> list[float]:
    out = []
    for round_votes in votes:
        agree = sum(v.confidence for v in round_votes if v.vote == "agree")
        active = sum(v.confidence for v in round_votes if v.vote != "abstain") or 1.0
        out.append(agree / active)
    return out


def specialist_engagement(opinions: list[SpecialistOpinion]) -> dict[str, dict]:
    """How much each specialist contributed: words spoken, # critiques, # hypotheses."""
    out: dict[str, dict] = defaultdict(lambda: {"words": 0, "critiques": 0, "hypotheses": 0, "rounds": 0})
    for o in opinions:
        out[o.name]["words"] += len(o.monologue.split())
        out[o.name]["critiques"] += len(o.critiques)
        out[o.name]["hypotheses"] += len(o.hypotheses)
        out[o.name]["rounds"] += 1
    return dict(out)


def evidence_citation_rate(opinions: list[SpecialistOpinion]) -> float:
    """Fraction of hypotheses that cite at least one piece of supporting evidence."""
    total = sum(len(o.hypotheses) for o in opinions) or 1
    cited = sum(1 for o in opinions for h in o.hypotheses if h.supporting_evidence)
    return cited / total


def calibration_against_truth(state: DebateState, true_diagnosis: str) -> dict:
    """If you have a known correct diagnosis, score top-1 / top-3 / Brier."""
    if not state.final_report:
        return {"top1": 0, "top3": 0, "brier": 1.0}
    truth = _normalize_name(true_diagnosis)
    primary = _normalize_name(state.final_report.primary_diagnosis.name)
    diffs = [_normalize_name(h.name) for h in state.final_report.differential_diagnoses]
    top1 = int(primary == truth)
    top3 = int(truth in [primary] + diffs[:2])
    p_truth = state.final_report.primary_diagnosis.probability if primary == truth else 0.0
    brier = (1.0 - p_truth) ** 2
    return {"top1": top1, "top3": top3, "brier": round(brier, 4)}


def summarize(state: DebateState, true_diagnosis: str | None = None) -> dict:
    s = {
        "rounds_completed": state.rounds_completed,
        "converged": state.converged,
        "agreement_per_round": agreement_per_round(state.votes),
        "hypothesis_stability_jaccard": round(hypothesis_stability(state.opinions), 3),
        "evidence_citation_rate": round(evidence_citation_rate(state.opinions), 3),
        "specialist_engagement": specialist_engagement(state.opinions),
        "n_specialists": len(state.selected_specialists),
        "n_opinions": len(state.opinions),
    }
    if true_diagnosis:
        s["calibration_vs_truth"] = calibration_against_truth(state, true_diagnosis)
    return s
