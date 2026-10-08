from typing import Literal

from pydantic import BaseModel, Field


class Qualification(BaseModel):
    business_id: str
    analysis_id: str | None
    is_demo: bool
    prospect_score: int = Field(ge=0, le=100)
    public_evidence_coverage: float = Field(ge=0, le=100)
    prospect_status: Literal["not_analyzed", "research", "ready_for_review", "do_not_contact"]
    prospect_reasons: list[str]
    public_unknown_criteria: list[str]
    need_status: Literal["unconfirmed", "confirmed_gap", "observed_friction", "assessed_no_gap"]
    confirmed_gap_criteria: list[str]
    observed_friction_criteria: list[str]
    need_review_ready: bool
    next_step: str
