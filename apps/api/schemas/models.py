from typing import Any, Literal

from pydantic import BaseModel, Field


class Credentials(BaseModel):
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=254)
    password: str = Field(min_length=10, max_length=128)


class Signup(Credentials):
    name: str = Field(min_length=2, max_length=60)


class Preferences(BaseModel):
    persona: Literal["ai", "web", "data", "agency"] = "ai"
    floor: int = Field(default=180, ge=0, le=100000)
    weekly_limit: int = Field(default=30, ge=0, le=100)
    filters: str = Field(default="", max_length=120)
    autonomy: Literal["review", "auto_skip"] = "review"
    scout_hours: int = Field(default=4, ge=2, le=48)
    onboarded: bool = True


class User(BaseModel):
    id: str
    name: str
    email: str
    settings: Preferences


class Job(BaseModel):
    id: str
    title: str
    description: str
    client: str
    client_id: str
    category: str
    skills: list[str]
    budget_min: int
    budget_max: int
    connects: int
    duration_days: int
    country: str
    source: str


class Run(BaseModel):
    id: str
    kind: Literal["bid", "conversation"]
    job_id: str
    status: str
    result: dict[str, Any] | None
    error: str | None
    created: str
    updated: str


class RunStart(BaseModel):
    job_id: str = Field(min_length=1, max_length=100)
    strategy: Literal["evidence_first", "plan_first"] = "evidence_first"


class Message(BaseModel):
    id: str
    job_id: str
    direction: str
    body: str
    created: str


class PipelineCard(BaseModel):
    job_id: str
    title: str
    stage: str
    amount: int
    connects: int
    updated: str
    run_id: str | None = None


class Health(BaseModel):
    status: str
    marketplace: str
    mode: str
    demo_access: bool


class Balance(BaseModel):
    remaining: int
    spent: int
    week_spent: int
