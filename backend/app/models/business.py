from typing import Annotated, Literal
import re

from pydantic import BaseModel, Field, StringConstraints


def plausible_phone(value):
    """Syntax screening only; never establishes that a number is reachable."""
    value = (value or "").strip()
    if not re.fullmatch(r"\+?[0-9\s().-]+(?:\s*(?:ext\.?|x)\s*[0-9]{1,6})?", value, re.I):
        return False
    main = re.split(r"(?:ext\.?|x)", value, flags=re.I)[0]
    return 7 <= len(re.sub(r"[^0-9]", "", main)) <= 15


class BusinessSearchRequest(BaseModel):
    industry: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]
    location: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    source: Literal["mock", "google_places"] = "mock"
    limit: int = Field(default=10, ge=1, le=20)


class Business(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    website: Annotated[str, StringConstraints(max_length=2048)] | None
    phone: Annotated[str, StringConstraints(max_length=64)] | None
    address: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=600)]
    rating: float | None = Field(ge=0, le=5)
    review_count: int | None = Field(ge=0)
