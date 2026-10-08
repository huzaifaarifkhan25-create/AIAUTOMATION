from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints

from app.models.business import Business

CsvSource = Literal["gosom", "instant_data_scraper", "web_scraper", "csv"]


class ImportProvenance(BaseModel):
    source: CsvSource
    collected_at: AwareDatetime
    file_name: Annotated[str, StringConstraints(max_length=120)]
    place_id: Annotated[str, StringConstraints(max_length=256)] | None = None
    listing_url: Annotated[str, StringConstraints(max_length=2048)] | None = None
    column_map: dict[str, str]
    original_values: dict[str, str]


class ImportRowResult(BaseModel):
    row_number: int
    status: Literal["valid", "imported", "duplicate", "invalid"]
    business: Business | None = None
    business_id: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CsvImportReport(BaseModel):
    dry_run: bool
    source: CsvSource
    total_rows: int
    valid_rows: int
    imported_rows: int
    duplicate_rows: int
    invalid_rows: int
    column_map: dict[str, str]
    ignored_columns: list[str]
    rows: list[ImportRowResult]
