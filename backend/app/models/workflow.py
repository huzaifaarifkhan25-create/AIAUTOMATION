from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StrictBool, StringConstraints, model_validator

from app.models.business import Business
from app.models.csv_import import ImportProvenance

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


def now() -> datetime:
    return datetime.now(timezone.utc)


class Criterion(str, Enum):
    inquiry_followup = "inquiry_followup"
    appointment_reminders = "appointment_reminders"
    consultation_followup = "consultation_followup"
    rebooking = "rebooking"
    public_email = "public_email"
    business_phone = "business_phone"
    inquiry_form = "inquiry_form"
    operational_scale = "operational_scale"
    recurring_services = "recurring_services"
    booking_friction = "booking_friction"
    inquiry_friction = "inquiry_friction"
    intake_friction = "intake_friction"


class Evidence(BaseModel):
    criterion: Criterion
    assessment: Literal["strong", "partial", "clear", "unknown"]
    source: Literal["business_confirmation", "public_website", "public_listing", "manual_research"]
    origin: Literal["operator", "automatic", "unspecified"] = "unspecified"
    detail: Text
    observed_at: AwareDatetime = Field(default_factory=now)

    @model_validator(mode="after")
    def validate_confirmation(self):
        operational = {"inquiry_followup", "appointment_reminders", "consultation_followup", "rebooking"}
        if self.criterion.value in operational and self.assessment != "unknown":
            if self.source != "business_confirmation":
                raise ValueError("Operational criteria require business confirmation")
        if self.observed_at > now():
            raise ValueError("Evidence cannot have a future observation date")
        return self


class AnalyzeRequest(BaseModel):
    fetch_website: bool = False
    use_ai: bool = False
    evidence: list[Evidence] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def unique_criteria(self):
        criteria = [item.criterion for item in self.evidence]
        if len(criteria) != len(set(criteria)):
            raise ValueError("Supply at most one assessment for each criterion")
        return self


class BusinessRecord(BaseModel):
    id: str
    business: Business
    source: Literal["manual", "mock", "google_places", "gosom", "instant_data_scraper", "web_scraper", "csv"] = "manual"
    provenance: ImportProvenance | None = None
    created_at: AwareDatetime
    updated_at: AwareDatetime


class WebsiteFindings(BaseModel):
    url: str
    title: str
    emails: list[str]
    has_phone_link: bool
    has_booking_link: bool
    has_inquiry_form: bool
    excerpt: str
    observed_at: AwareDatetime = Field(default_factory=now)
    limitations: str = "Static public HTML only; absence does not establish an internal operational gap."


class Narrative(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    suggested_questions: list[str]


class Analysis(BaseModel):
    id: str
    business_id: str
    created_at: AwareDatetime
    mode: Literal["rules", "rules_with_ai_summary"]
    need_score: int = Field(ge=0, le=100)
    sales_score: int = Field(ge=0, le=100)
    total_score: float = Field(ge=0, le=100)
    components: dict[str, float]
    evidence_coverage: float = Field(ge=0, le=100)
    provisional: bool
    priority: Literal["research", "high", "medium", "low", "insufficient_evidence"]
    evidence: list[Evidence]
    unknown_criteria: list[str]
    pain_points: list[str]
    recommended_automation: str
    automation_type: Literal["booking_assistant", "inquiry_followup", "appointment_reminders", "consultation_followup", "rebooking", "research_required"]
    summary: str
    suggested_questions: list[str]
    website: WebsiteFindings | None


class WorkflowRequest(BaseModel):
    analysis_id: str


class WorkflowNode(BaseModel):
    id: str
    type: Literal["webhook", "condition", "delay", "message", "calendar", "database"]
    parameters: dict = Field(default_factory=dict)


class Workflow(BaseModel):
    id: str
    business_id: str
    analysis_id: str
    name: str
    created_at: AwareDatetime
    status: Literal["draft", "archived"] = "draft"
    format: Literal["medspa-workflow-v1"] = "medspa-workflow-v1"
    nodes: list[WorkflowNode]
    connections: list[tuple[str, str]]
    required_configuration: list[str]
    execution_supported: bool = False


class ContactUpdate(BaseModel):
    stage: Literal["new", "contacted", "interested", "demo_booked", "won", "lost", "do_not_contact"]
    notes: Annotated[str, StringConstraints(max_length=4000)] = ""


class Contact(BaseModel):
    business_id: str
    stage: str
    notes: str
    updated_at: AwareDatetime


class CallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=8, max_length=100)]
    confirm_outbound_call: StrictBool = False
