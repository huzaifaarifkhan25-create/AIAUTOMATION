"""Sandbox inputs deliberately contain no recipient address or patient details."""
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, StrictBool, StringConstraints

from app.models.workflow import Workflow

Reference = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9_.:-]{1,100}$")]
EmailAddress = Annotated[str, StringConstraints(strip_whitespace=True, max_length=254,
    pattern=r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}$")]


def sandbox_confirmation(value):
    if value is not True:
        raise ValueError("Explicit JSON true confirmation is required")
    return value


class RunEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contact_id: Reference
    contact_permission: StrictBool
    appointment_cancelled: StrictBool = False


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["sandbox"]
    confirm_sandbox: Annotated[Literal[True], BeforeValidator(sandbox_confirmation)]
    idempotency_key: Reference
    event: RunEvent
    message_body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    scheduled_at: AwareDatetime | None = None


class EmailRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["email"]
    confirm_send: Annotated[Literal[True], BeforeValidator(sandbox_confirmation)]
    idempotency_key: Reference
    event: RunEvent
    recipient_email: EmailAddress
    subject: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200, pattern=r"^[^\r\n]+$")]
    message_body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    scheduled_at: AwareDatetime | None = None


class RunHistory(BaseModel):
    at: AwareDatetime
    step: str | None = None
    outcome: str


class WorkflowRun(BaseModel):
    id: str
    workflow_id: str
    business_id: str
    analysis_id: str
    mode: Literal["sandbox", "email"]
    status: Literal["queued", "running", "waiting", "retry_wait", "succeeded", "skipped", "cancelled", "failed"]
    created_at: AwareDatetime
    updated_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    next_at: AwareDatetime | None = None
    scheduled_at: AwareDatetime | None = None
    next_step: int = 0
    step_attempts: dict[str, int] = Field(default_factory=dict)
    request_hash: str
    event: RunEvent
    message_body: str
    recipient_email: str | None = None
    subject: str | None = None
    appointment_id: str | None = None
    deployment_id: str | None = None
    delivery_status: str | None = None
    workflow_snapshot: Workflow
    history: list[RunHistory] = Field(default_factory=list)
    outbox_id: str | None = None
    stop_reason: str | None = None
    result: Literal["sandbox_recorded", "email_submission_recorded"] | None = None
    sent: bool = False


class OutboxPreview(BaseModel):
    id: str
    run_id: str
    workflow_id: str
    business_id: str
    contact_id: str
    mode: Literal["sandbox", "email"]
    status: Literal["preview_created", "submission_started", "submission_uncertain", "submitted", "sent", "delivered", "bounced", "complained", "failed", "suppressed"]
    message_body: str
    created_at: AwareDatetime
    sent: bool = False
    recipient_email: str | None = None
    subject: str | None = None
    from_email: str | None = None
    provider_email_id: str | None = None
    submission_started_at: AwareDatetime | None = None
    last_event_at: AwareDatetime | None = None
    delivered: bool = False
