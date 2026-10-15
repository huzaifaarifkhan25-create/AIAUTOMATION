"""Owner routes and a separate token-authenticated machine intake route."""
import json
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import ValidationError

from app.errors import AppError
from app.models.inquiries import IntakeRequest, PauseRequest, RetryRequest, RotateRequest, SourceRequest

router = APIRouter(tags=["Inquiry sources and outcomes"])
public = APIRouter(tags=["Authenticated machine inquiry intake"])


@router.get("/inquiry-sources")
async def sources(request: Request, include_demo: bool = False):
    return await request.app.state.inquiries.sources(include_demo=include_demo)


@router.post("/inquiry-sources", status_code=201)
async def create_source(body: SourceRequest, request: Request):
    return await request.app.state.inquiries.create_source(body)


@router.get("/inquiry-sources/{source_id}")
async def source(source_id: UUID, request: Request):
    return await request.app.state.inquiries.source(str(source_id))


@router.post("/inquiry-sources/{source_id}/pause")
async def pause_source(source_id: UUID, body: PauseRequest, request: Request):
    return await request.app.state.inquiries.pause(str(source_id), body.confirm_pause)


@router.post("/inquiry-sources/{source_id}/rotate-key")
async def rotate_key(source_id: UUID, body: RotateRequest, request: Request):
    return await request.app.state.inquiries.rotate(str(source_id), body.confirm_rotation)


@router.get("/inquiries")
async def inquiries(request: Request, include_demo: bool = False,
                    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    return (await request.app.state.inquiries.list(include_demo=include_demo))[offset:offset + limit]


@router.get("/inquiries/{inquiry_id}")
async def inquiry(inquiry_id: UUID, request: Request):
    return await request.app.state.inquiries.get(str(inquiry_id))


@router.post("/inquiries/{inquiry_id}/retry")
async def retry(inquiry_id: UUID, body: RetryRequest, request: Request):
    return await request.app.state.inquiries.retry(str(inquiry_id), body.confirm_retry)


@router.get("/outcomes/summary")
async def outcomes(request: Request, include_demo: bool = False):
    return await request.app.state.inquiries.summary(include_demo=include_demo)


@public.post("/intake/{source_id}", status_code=202)
async def intake(source_id: UUID, request: Request):
    service = request.app.state.inquiries
    source = await service.authenticate_source(str(source_id), request.headers.get("X-Inquiry-Key", ""),
                                               request.client.host if request.client else "unknown")
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise AppError(415, "inquiry_json_required", "Submit an application/json inquiry")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 8192:
            raise AppError(413, "inquiry_too_large", "Inquiry payload exceeds 8 KB")
    try:
        body = IntakeRequest.model_validate(json.loads(data))
    except (ValueError, ValidationError, UnicodeError):
        # Do not reflect arbitrary customer data or credential-like input.
        raise AppError(422, "inquiry_invalid", "Use a unique event ID, contact reference, general inquiry and literal contact permission") from None
    record = await service.receive(source["id"], body, authenticated_hash=source["key_hash"])
    # The sender needs acknowledgement, not private CRM/provider references.
    return {"accepted": True, "inquiry_id": record["id"], "status": record["status"]}
