from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

from app.models.execution import EmailRunRequest, RunRequest


class AppointmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_id: str
    starts_at: AwareDatetime
    reminder: RunRequest | EmailRunRequest

    @model_validator(mode="after")
    def timing(self):
        if self.reminder.scheduled_at is None or self.reminder.scheduled_at >= self.starts_at:
            raise ValueError("Reminder scheduled_at must be supplied and be before starts_at")
        if self.reminder.event.appointment_cancelled:
            raise ValueError("Create an active appointment, then use the cancellation endpoint when needed")
        return self


class Appointment(BaseModel):
    id: str
    business_id: str
    workflow_id: str
    starts_at: AwareDatetime
    status: Literal["pending", "scheduled", "cancelled", "failed"]
    created_at: AwareDatetime
    updated_at: AwareDatetime
    request_hash: str
    reminder: RunRequest | EmailRunRequest
    run_id: str | None = None
    deployment_id: str | None = None
    error_code: str | None = None
