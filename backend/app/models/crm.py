from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints

from app.models.execution import Reference

Notes = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class ActivityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: Reference
    kind: Literal["note", "call", "email", "meeting"]
    direction: Literal["incoming", "outgoing", "internal"] = "internal"
    notes: Notes
    occurred_at: AwareDatetime


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    idempotency_key: Reference
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    notes: Annotated[str, StringConstraints(max_length=4000)] = ""
    due_at: AwareDatetime


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed", "cancelled"]
