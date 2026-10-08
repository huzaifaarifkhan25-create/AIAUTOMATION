import json
from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import AwareDatetime

from app.errors import AppError
from app.models.csv_import import CsvImportReport, CsvSource
from app.models.workflow import now
from app.services.csv_import import MAX_BYTES, import_csv

router = APIRouter(tags=["CSV import"])


@router.post(
    "/businesses/import-csv",
    response_model=CsvImportReport,
    summary="Preview or import a scraper CSV file",
    openapi_extra={"requestBody": {"required": True, "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}}}},
)
async def import_scraper_csv(
    request: Request,
    source: CsvSource = "csv",
    dry_run: bool = True,
    collected_at: AwareDatetime | None = None,
    file_name: Annotated[str, Query(min_length=1, max_length=120)] = "upload.csv",
    column_map: Annotated[str | None, Query(max_length=4096)] = None,
):
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() not in {"text/csv", "application/csv", "application/octet-stream"}:
        raise AppError(415, "csv_content_type", "Send the CSV file as the raw request body with Content-Type: text/csv")
    explicit = {}
    if column_map:
        try:
            explicit = json.loads(column_map)
            if not isinstance(explicit, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in explicit.items()):
                raise ValueError()
        except ValueError:
            raise AppError(422, "invalid_column_map", "column_map must be a JSON object mapping supported fields to CSV header names") from None
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BYTES:
            raise AppError(413, "csv_too_large", "CSV must be at most 2 MB")
        chunks.append(chunk)
    return await import_csv(
        request.app.state.store, b"".join(chunks), source, dry_run,
        collected_at or now(), file_name, explicit,
    )
