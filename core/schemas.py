"""Pydantic models — every agent output must conform to these."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class Hypothesis(BaseModel):
    """One candidate diagnosis from a specialist."""
    name: str = Field(..., description="Diagnosis name")
    icd10: Optional[str] = Field(None, description="ICD-10 code if known")
    probability: float = Field(..., ge=0.0, le=1.0)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    reasoning: str = ""

    @field_validator("probability")
    @classmethod
    def _round(cls, v: float) -> float:
        return round(float(v), 4)


class SpecialistOpinion(BaseModel):
    """One specialist's contribution in one round."""
    specialist_id: str
    name: str
    specialty: str
    round: int
    monologue: str = Field(..., description="Full talkative reasoning — let them speak")
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    recommended_tests: list[str] = Field(default_factory=list)
    critiques: list[str] = Field(default_factory=list, description="Critiques of colleagues")


class SatisfactionVote(BaseModel):
    specialist_id: str
    name: str
    vote: Literal["agree", "disagree", "abstain"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str


class Medication(BaseModel):
    name: str
    generic_name: Optional[str] = None
    indication: str
    dosage: str
    duration: str
    common_side_effects: list[str] = Field(default_factory=list)
    serious_side_effects: list[str] = Field(default_factory=list)
    contraindications: list[str] = Field(default_factory=list)
    interactions: list[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    primary_diagnosis: Hypothesis
    differential_diagnoses: list[Hypothesis] = Field(default_factory=list)
    why_it_happened: str
    what_user_should_do: list[str] = Field(default_factory=list)
    lifestyle_recommendations: list[str] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    follow_up_tests: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list, description="Symptoms requiring ER")
    specialist_referrals: list[str] = Field(default_factory=list)
    agreement_score: float = Field(..., ge=0.0, le=1.0)
    dissenting_opinions: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "⚠️ This is an AI multi-agent simulation for educational purposes. "
        "It is NOT medical advice. Consult a licensed physician for any health concern."
    )


class DebateState(BaseModel):
    """Full state for a single debate run."""
    case_summary: str
    evidence: dict = Field(default_factory=dict)  # parsed data files
    selected_specialists: list[str] = Field(default_factory=list)
    opinions: list[SpecialistOpinion] = Field(default_factory=list)
    votes: list[list[SatisfactionVote]] = Field(default_factory=list)  # per round
    rounds_completed: int = 0
    converged: bool = False
    final_report: Optional[FinalReport] = None
