"""Debate orchestrator — router, rounds, satisfaction-driven consensus."""
from __future__ import annotations
import json
import os
from typing import Callable, Iterable

from .llm_backends import LLMBackend, extract_json
from .schemas import (
    DebateState,
    Hypothesis,
    SatisfactionVote,
    SpecialistOpinion,
)
from .specialists import (
    ROUTER_SYSTEM,
    SPECIALISTS,
    specialist_system_prompt,
)


# ─── tunables ──────────────────────────────────────────────────────────────
MIN_SPECIALISTS = int(os.getenv("MIN_SPECIALISTS", "5"))
MAX_SPECIALISTS = int(os.getenv("MAX_SPECIALISTS", "8"))
MAX_DEBATE_ROUNDS = int(os.getenv("MAX_DEBATE_ROUNDS", "4"))
SATISFACTION_THRESHOLD = float(os.getenv("SATISFACTION_THRESHOLD", "0.8"))


EventCb = Callable[[dict], None]  # for streaming UI updates


# ─── router ────────────────────────────────────────────────────────────────
def route_specialists(backend: LLMBackend, case_summary: str, evidence_text: str) -> list[str]:
    user = f"""Case summary:
{case_summary}

Evidence:
{evidence_text[:6000]}

Available specialists (id → specialty):
{json.dumps({k: v["specialty"] for k, v in SPECIALISTS.items()}, indent=2)}

Select between {MIN_SPECIALISTS} and {MAX_SPECIALISTS} specialist IDs whose expertise is most relevant.
Always include "internal".
Return ONLY a JSON array of IDs, e.g. ["internal","cardio","neuro"]."""
    raw = backend.chat(ROUTER_SYSTEM, user, json_mode=True)
    try:
        ids = extract_json(raw)
        if isinstance(ids, dict):
            for k in ("specialists", "ids", "selected"):
                if k in ids:
                    ids = ids[k]
                    break
        ids = [i for i in ids if i in SPECIALISTS]
    except Exception:
        ids = []
    if "internal" not in ids:
        ids = ["internal"] + ids
    if len(ids) < MIN_SPECIALISTS:
        # backfill with broad set
        for fallback in ["cardio", "neuro", "endo", "infect", "hema", "gastro", "rheum"]:
            if fallback not in ids:
                ids.append(fallback)
            if len(ids) >= MIN_SPECIALISTS:
                break
    return ids[:MAX_SPECIALISTS]


# ─── one specialist's turn ─────────────────────────────────────────────────
SPECIALIST_OUTPUT_INSTRUCTIONS = """Output JSON exactly matching this schema:
{
  "monologue": "string — your full talkative reasoning, 4-10 sentences",
  "hypotheses": [
    {
      "name": "string",
      "icd10": "string or null",
      "probability": 0.0,
      "supporting_evidence": ["..."],
      "contradicting_evidence": ["..."],
      "reasoning": "string"
    }
  ],
  "recommended_tests": ["..."],
  "critiques": ["specific critiques of named colleagues, or [] in round 1"]
}"""


def _format_prior(opinions: list[SpecialistOpinion]) -> str:
    if not opinions:
        return ""
    lines = ["\n\n=== PRIOR OPINIONS FROM COLLEAGUES ==="]
    for o in opinions:
        lines.append(f"\n[Round {o.round}] {o.name} — {o.specialty}")
        lines.append(f"  Monologue: {o.monologue}")
        if o.hypotheses:
            lines.append("  Hypotheses:")
            for h in o.hypotheses:
                lines.append(f"    • {h.name} (p={h.probability:.2f}) — {h.reasoning[:200]}")
        if o.critiques:
            lines.append("  Critiques: " + " | ".join(o.critiques))
    lines.append("\nYou MUST critique or explicitly support at least one colleague.")
    return "\n".join(lines)


def specialist_turn(
    backend: LLMBackend,
    spec_id: str,
    round_num: int,
    case_summary: str,
    evidence_text: str,
    prior: list[SpecialistOpinion],
) -> SpecialistOpinion:
    spec = SPECIALISTS[spec_id]
    sys = specialist_system_prompt(spec_id)
    user = f"""ROUND {round_num} of debate.

CASE SUMMARY:
{case_summary}

EVIDENCE:
{evidence_text}
{_format_prior(prior)}

{SPECIALIST_OUTPUT_INSTRUCTIONS}"""

    raw = backend.chat(sys, user, json_mode=True)
    try:
        data = extract_json(raw)
    except Exception:
        data = {"monologue": raw, "hypotheses": [], "recommended_tests": [], "critiques": []}

    hyps = []
    for h in data.get("hypotheses", []) or []:
        try:
            hyps.append(Hypothesis(**h))
        except Exception:
            continue

    return SpecialistOpinion(
        specialist_id=spec_id,
        name=spec["name"],
        specialty=spec["specialty"],
        round=round_num,
        monologue=str(data.get("monologue", "")),
        hypotheses=hyps,
        recommended_tests=list(data.get("recommended_tests", []) or []),
        critiques=list(data.get("critiques", []) or []),
    )


# ─── satisfaction vote ─────────────────────────────────────────────────────
def collect_votes(
    backend: LLMBackend,
    proposal: dict,
    specialists: Iterable[str],
    case_summary: str,
    evidence_text: str,
    _all_opinions: list[SpecialistOpinion] | None = None,
) -> list[SatisfactionVote]:
    votes: list[SatisfactionVote] = []
    proposal_text = json.dumps(proposal, indent=2)
    for spec_id in specialists:
        spec = SPECIALISTS[spec_id]
        sys = specialist_system_prompt(spec_id) + (
            "\nNow you are voting on a proposed primary diagnosis. Be honest. "
            "If you disagree, say so."
        )
        user = f"""The Chief Medical Officer proposes:
{proposal_text}

Case:
{case_summary}

Evidence (excerpt):
{evidence_text[:5000]}

Considering all the debate so far, do you AGREE, DISAGREE, or ABSTAIN?
Output JSON: {{"vote":"agree|disagree|abstain","confidence":0.0,"reason":"..."}}"""
        raw = backend.chat(sys, user, json_mode=True)
        try:
            d = extract_json(raw)
            v = SatisfactionVote(
                specialist_id=spec_id,
                name=spec["name"],
                vote=d.get("vote", "abstain"),
                confidence=float(d.get("confidence", 0.5)),
                reason=str(d.get("reason", "")),
            )
        except Exception:
            v = SatisfactionVote(
                specialist_id=spec_id, name=spec["name"],
                vote="abstain", confidence=0.0, reason="parse error",
            )
        votes.append(v)
    return votes


def agreement_score(votes: list[SatisfactionVote]) -> float:
    if not votes:
        return 0.0
    weighted = sum(v.confidence for v in votes if v.vote == "agree")
    total = sum(v.confidence for v in votes if v.vote != "abstain") or 1.0
    return weighted / total


# ─── full run ──────────────────────────────────────────────────────────────
def run_debate(
    backend: LLMBackend,
    case_summary: str,
    evidence: dict,
    evidence_text: str,
    on_event: EventCb | None = None,
) -> DebateState:
    def emit(kind: str, **kw):
        if on_event:
            on_event({"kind": kind, **kw})

    state = DebateState(case_summary=case_summary, evidence=evidence)

    emit("status", message="Routing to specialists…")
    state.selected_specialists = route_specialists(backend, case_summary, evidence_text)
    emit("specialists_selected", ids=state.selected_specialists,
         names=[SPECIALISTS[i]["name"] for i in state.selected_specialists])

    proposal: dict = {}

    for round_num in range(1, MAX_DEBATE_ROUNDS + 1):
        emit("round_start", round=round_num)
        prior = list(state.opinions)
        for spec_id in state.selected_specialists:
            emit("speaker_start", round=round_num, specialist_id=spec_id,
                 name=SPECIALISTS[spec_id]["name"])
            op = specialist_turn(backend, spec_id, round_num, case_summary, evidence_text, prior)
            state.opinions.append(op)
            emit("opinion", opinion=op.model_dump())
        state.rounds_completed = round_num

        # Build supervisor proposal from current opinions
        from .consensus import draft_proposal
        emit("status", message=f"Supervisor drafting proposal after round {round_num}…")
        proposal = draft_proposal(backend, case_summary, evidence_text, state.opinions) or {}
        emit("proposal", proposal=proposal)

        # Vote
        emit("status", message="Specialists voting on satisfaction…")
        votes = collect_votes(backend, proposal, state.selected_specialists,
                              case_summary, evidence_text, state.opinions)
        state.votes.append(votes)
        score = agreement_score(votes)
        emit("vote_result", round=round_num, score=score,
             votes=[v.model_dump() for v in votes])

        if score >= SATISFACTION_THRESHOLD:
            state.converged = True
            emit("converged", round=round_num, score=score)
            break

    # Final report
    from .consensus import finalize_report
    emit("status", message="Finalizing report…")
    state.final_report = finalize_report(backend, state, proposal or {})
    emit("done", report=state.final_report.model_dump() if state.final_report else None)
    return state
