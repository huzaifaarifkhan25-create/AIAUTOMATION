"""Bounded non-clinical inquiry intake and operator-reviewed source settings."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints, model_validator

from app.models.execution import EmailAddress, Reference


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRequest(Input):
    request_id: UUID
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    n8n_deployment_id: UUID
    acknowledgement: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    followup_delay_minutes: int = Field(default=60, ge=5, le=10080, strict=True)
    confirm_activation: StrictBool
    email_mode: Literal["none", "email"] = "none"
    email_subject: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200, pattern=r"^[^\r\n]+$")] | None = None
    confirm_email_delivery: StrictBool = False

    @model_validator(mode="after")
    def email_review(self):
        if self.email_mode == "email" and (not self.email_subject or not self.confirm_email_delivery):
            raise ValueError("Email mode requires a reviewed subject and explicit delivery authorization")
        if self.email_mode == "none" and (self.email_subject is not None or self.confirm_email_delivery):
            raise ValueError("Email settings are only used in email mode")
        return self


class IntakeRequest(Input):
    event_id: Reference
    contact_reference: Reference
    inquiry: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    contact_permission: StrictBool
    recipient_email: EmailAddress | None = None


class PauseRequest(Input):
    confirm_pause: StrictBool


class RotateRequest(Input):
    confirm_rotation: StrictBool


class RetryRequest(Input):
    confirm_retry: StrictBool
