from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator
from typing import Annotated

Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1200)]


class PainPoint(BaseModel):
    point: Short
    evidence: Short
    source: Short
    confidence: Literal["low", "medium", "high"]


class Estimate(BaseModel):
    score: int = Field(ge=0, le=100)
    label: Literal["ai_estimate"]
    rationale: Short


class AutomationIdea(BaseModel):
    type: Literal["appointment_reminders", "inquiry_followup", "consultation_followup", "rebooking"]
    why: Short


class AIInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: Short
    pain_points: list[PainPoint] = Field(max_length=6)
    opportunity_estimate: Estimate
    recommended_automations: list[AutomationIdea] = Field(max_length=4)
    unknowns: list[Short] = Field(max_length=12)
    disclaimer: Literal["AI inference from public information; internal gaps unconfirmed"]


Language = Literal["en", "ur", "roman_ur"]
Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class SenderProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    company: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    offer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]

    @model_validator(mode="after")
    def concise_profile(self):
        weighted_words = 2 * len(self.name.split()) + 2 * len(self.company.split()) + len(self.offer.split())
        if weighted_words > 30:
            raise ValueError("Keep sender name, company and offer concise (about one sentence total)")
        return self


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Language = "en"
    sender: SenderProfile


class PersonalizationFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fact: Line
    source: Line
    observed_on: date


class FollowUp(BaseModel):
    model_config = ConfigDict(extra="forbid")
    after_days: Literal[3, 7]
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class PitchDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Language
    subject_options: list[Line] = Field(min_length=3, max_length=3)
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2500)]
    personalization_used: list[PersonalizationFact] = Field(max_length=5)
    call_to_action: Line
    follow_ups: list[FollowUp] = Field(min_length=2, max_length=2)
    opt_out_line: Line
    assumptions_and_unknowns: list[Line] = Field(max_length=10)

    @field_validator("body")
    @classmethod
    def body_words(cls, value):
        if not 90 <= len(value.split()) <= 150:
            raise ValueError("Email body must contain 90–150 words")
        return value

    @model_validator(mode="after")
    def follow_up_days(self):
        if [item.after_days for item in self.follow_ups] != [3, 7]:
            raise ValueError("Follow-up drafts must be for days 3 and 7")
        return self


class Objection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objection: Line
    response: Line


class CallScript(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Language
    opening: Line
    permission_question: Line
    discovery_questions: list[Line] = Field(min_length=3, max_length=5)
    value_statement: Line
    objections: list[Objection] = Field(min_length=1, max_length=4)
    close: Line
    voicemail: Line
    if_not_interested: Line
    assumptions_and_unknowns: list[Line] = Field(max_length=10)

    @field_validator("opening")
    @classmethod
    def opening_words(cls, value):
        if len(value.split()) > 40:
            raise ValueError("Opening must be at most 40 words")
        return value

    @field_validator("voicemail")
    @classmethod
    def voicemail_words(cls, value):
        if len(value.split()) > 45:
            raise ValueError("Voicemail must be under about 20 seconds")
        return value


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    history: list[ChatMessage] = Field(default_factory=list, max_length=8)


class ProposedAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["create_task", "run_ai_analysis", "generate_pitch"]
    business_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ChatResponse(BaseModel):
    answer: Short
    tool_used: str | None = None
    proposed_action: ProposedAction | None = None
