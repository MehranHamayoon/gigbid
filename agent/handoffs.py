from typing import Literal

from pydantic import BaseModel, Field


class JobSpec(BaseModel):
    job_id: str
    title: str
    deliverables: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    budget_min: float | None = None
    budget_max: float | None = None
    duration_days: int = 0
    screening_questions: list[str] = Field(default_factory=list)
    hidden_needs: list[str] = Field(default_factory=list)


class RiskReport(BaseModel):
    score: float = Field(ge=0, le=1)
    flags: list[str] = Field(default_factory=list)
    explanation: str


class FitReport(BaseModel):
    score: float = Field(ge=0, le=1)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    matrix: dict[str, list[str]] = Field(default_factory=dict)


class BidDecision(BaseModel):
    action: Literal["bid", "watch", "skip"]
    reason: str


class PriceQuote(BaseModel):
    amount: int = Field(ge=0)
    low: int
    high: int
    connects: int
    rationale: str


class ProposalDraft(BaseModel):
    job_id: str
    cover_letter: str
    screening_answers: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    status: str = "pending_review"


class Critique(BaseModel):
    accepted: bool
    feedback: list[str] = Field(default_factory=list)
    revision: int


class ComplianceVerdict(BaseModel):
    allowed: bool
    reasons: list[str] = Field(default_factory=list)


class Approval(BaseModel):
    action: Literal["approve", "edit", "reject"]
    text: str | None = Field(default=None, max_length=5000)
    reason: str = Field(default="", max_length=500)
