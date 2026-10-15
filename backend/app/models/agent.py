"""Operator chat inputs; provider credentials never belong in stored conversations."""
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, SecretStr, StrictBool, StringConstraints, field_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class AgentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationRequest(AgentInput):
    idempotency_key: UUID


class ChatRequest(AgentInput):
    request_id: UUID
    message: Text
    include_demo: StrictBool = False
    business_id: str | None = None
    timezone: Annotated[str, StringConstraints(max_length=80)] = "Asia/Karachi"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ValueError, ZoneInfoNotFoundError):
            raise ValueError("Choose a valid IANA timezone") from None
        return value


class ConnectionRequest(AgentInput):
    provider: Literal["gemini", "openai"]
    api_key: SecretStr
    model: str | None = None


class ReviewRequest(AgentInput):
    conversation_id: UUID
    decision: Literal["approve", "reject"]
    confirm_action: StrictBool = False
