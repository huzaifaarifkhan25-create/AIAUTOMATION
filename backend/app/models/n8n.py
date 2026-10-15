"""Inputs for the single supported inquiry-to-task n8n template."""
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, SecretStr, StrictBool, StringConstraints


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConnectionRequest(Input):
    base_url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
    api_key: SecretStr


class DeployRequest(Input):
    request_id: UUID
    workflow_id: Annotated[str, StringConstraints(min_length=1, max_length=100)]
    confirm_deployment: StrictBool


class InquiryRequest(Input):
    request_id: UUID
    contact_reference: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    inquiry: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    acknowledgement: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]
    followup_at: AwareDatetime
    contact_permission: StrictBool
    confirm_run: StrictBool
