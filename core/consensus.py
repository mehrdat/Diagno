"""Supervisor-side: draft proposal mid-debate; finalize a full report at the end."""
from __future__ import annotations
import json

from .llm_backends import LLMBackend, extract_json
from .schemas import (
    DebateState,
    FinalReport,
    Hypothesis,
    Medication,
    SpecialistOpinion,
)
from .specialists import SUPERVISOR_SYSTEM


def _serialize_opinions(opinions: list[SpecialistOpinion]) -> str:
    return "\n\n".join(
        f"[Round {o.round}] {o.name} ({o.specialty})\n"
        f"  Monologue: {o.monologue}\n"
        f"  Hypotheses: " + json.dumps(
            [{"name": h.name, "p": h.probability, "for": h.supporting_evidence,
              "against": h.contradicting_evidence} for h in o.hypotheses]
        )
        + (f"\n  Critiques: {o.critiques}" if o.critiques else "")
        for o in opinions
    )


def draft_proposal(
    backend: LLMBackend,
    case_summary: str,
    evidence_text: str,
    opinions: list[SpecialistOpinion],
) -> dict:
    """A lightweight proposal used for the satisfaction vote."""
    user = f"""CASE: {case_summary}

EVIDENCE EXCERPT:
{evidence_text[:5000]}

DEBATE TRANSCRIPT:
{_serialize_opinions(opinions)}

Draft a preliminary primary diagnosis the panel will vote on. JSON:
{{
  "primary_diagnosis": {{"name":"...","icd10":"...","probability":0.0,"reasoning":"..."}},
  "differentials": [{{"name":"...","probability":0.0,"reasoning":"..."}}],
  "key_disagreements": ["..."]
}}"""
    raw = backend.chat(SUPERVISOR_SYSTEM, user, json_mode=True)
    try:
        return extract_json(raw)
    except Exception:
        return {"primary_diagnosis": {"name": "undetermined", "probability": 0.0,
                                      "reasoning": raw[:500]},
                "differentials": [], "key_disagreements": []}


FINAL_REPORT_INSTRUCTIONS = """Output JSON exactly matching:
{
  "primary_diagnosis": {
    "name": "...", "icd10": "...", "probability": 0.0,
    "supporting_evidence": ["..."], "contradicting_evidence": ["..."],
    "reasoning": "..."
  },
  "differential_diagnoses": [
    {"name":"...","icd10":"...","probability":0.0,
     "supporting_evidence":[],"contradicting_evidence":[],"reasoning":"..."}
  ],
  "why_it_happened": "pathophysiology + likely triggers, in plain language",
  "what_user_should_do": ["concrete action 1", "..."],
  "lifestyle_recommendations": ["..."],
  "medications": [
    {
      "name":"Brand or generic","generic_name":"...",
      "indication":"why this drug","dosage":"e.g. 500 mg PO BID",
      "duration":"e.g. 7 days",
      "common_side_effects":["..."],
      "serious_side_effects":["..."],
      "contraindications":["..."],
      "interactions":["..."]
    }
  ],
  "follow_up_tests": ["..."],
  "red_flags": ["symptoms that warrant immediate ER"],
  "specialist_referrals": ["..."],
  "agreement_score": 0.0,
  "dissenting_opinions": ["paraphrase any disagreeing specialist"]
}"""


def finalize_report(backend: LLMBackend, state: DebateState, last_proposal: dict) -> FinalReport:
    last_votes = state.votes[-1] if state.votes else []
    score = 0.0
    if last_votes:
        agree = sum(v.confidence for v in last_votes if v.vote == "agree")
        active = sum(v.confidence for v in last_votes if v.vote != "abstain") or 1.0
        score = agree / active
    dissent = [f"{v.name}: {v.reason}" for v in last_votes if v.vote == "disagree"]

    user = f"""CASE: {state.case_summary}

FULL DEBATE:
{_serialize_opinions(state.opinions)}

LATEST PROPOSAL:
{json.dumps(last_proposal, indent=2)}

LATEST VOTES:
{json.dumps([v.model_dump() for v in last_votes], indent=2)}

Now produce the FINAL patient-facing report. Be thorough. Medications must include dosage AND
side effects (common + serious) AND contraindications AND interactions. Use evidence-based
first-line therapy when possible.

agreement_score MUST equal {score:.3f}.
dissenting_opinions MUST include: {dissent}

{FINAL_REPORT_INSTRUCTIONS}"""

    raw = backend.chat(SUPERVISOR_SYSTEM, user, json_mode=True)
    try:
        d = extract_json(raw)
        # coerce
        primary = Hypothesis(**d["primary_diagnosis"])
        diffs = []
        for h in d.get("differential_diagnoses", []) or []:
            try:
                diffs.append(Hypothesis(**h))
            except Exception:
                continue
        meds = []
        for m in d.get("medications", []) or []:
            try:
                meds.append(Medication(**m))
            except Exception:
                continue
        return FinalReport(
            primary_diagnosis=primary,
            differential_diagnoses=diffs,
            why_it_happened=d.get("why_it_happened", ""),
            what_user_should_do=list(d.get("what_user_should_do", []) or []),
            lifestyle_recommendations=list(d.get("lifestyle_recommendations", []) or []),
            medications=meds,
            follow_up_tests=list(d.get("follow_up_tests", []) or []),
            red_flags=list(d.get("red_flags", []) or []),
            specialist_referrals=list(d.get("specialist_referrals", []) or []),
            agreement_score=float(d.get("agreement_score", score)),
            dissenting_opinions=list(d.get("dissenting_opinions", []) or dissent),
        )
    except Exception as e:
        # Last-ditch fallback so the run never crashes
        return FinalReport(
            primary_diagnosis=Hypothesis(
                name="undetermined", probability=0.0,
                reasoning=f"failed to parse final report: {e}\n\nRaw:\n{raw[:1000]}",
            ),
            why_it_happened="(parsing failed)",
            agreement_score=score,
            dissenting_opinions=dissent,
        )
