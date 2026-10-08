from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints, field_validator

from app.models.execution import EmailAddress, Reference, sandbox_confirmation

Confirmed = Annotated[Literal[True], BeforeValidator(sandbox_confirmation)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class ClientRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: Reference
    business_id: str
    contact_name: ShortText
    contact_email: EmailAddress | None = None
    timezone: ShortText
    approval_reference: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    confirm_business_authorization: Confirmed

    @field_validator("timezone")
    @classmethod
    def timezone_exists(cls, value):
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError):
            raise ValueError("Supply a valid IANA timezone") from None
        return value


class ConfirmClient(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_authorization: Confirmed


class DeploymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: Reference
    workflow_id: str
    channel: Literal["sandbox", "email"]


class ConfirmActivation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_activation: Confirmed
