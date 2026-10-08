from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints, field_validator


class DiscoveryRequest(BaseModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    limit: int = Field(default=5, ge=1, le=10, strict=True)

    @field_validator("query")
    @classmethod
    def one_line(cls, value):
        if "\n" in value or "\r" in value:
            raise ValueError("Use one business and location query")
        return value


class DiscoveryJob(BaseModel):
    id: str
    query: str
    limit: int
    status: Literal["queued", "running", "succeeded", "failed", "interrupted"]
    created_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    error: str | None = None
    collected_count: int | None = None
    collected_at: AwareDatetime | None = None
    sha256: str | None = None
    complete_directory: bool = False
