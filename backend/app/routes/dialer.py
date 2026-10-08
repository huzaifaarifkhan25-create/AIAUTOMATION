from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

from app.errors import AppError
from app.models.execution import sandbox_confirmation

router = APIRouter(tags=["Dialer outcomes"])
callbacks = APIRouter(tags=["Provider callbacks"])


class ReconcileCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_call_id: Annotated[str, StringConstraints(pattern=r"^CA[0-9a-fA-F]{32}$")]
    confirm_provider_record: Annotated[Literal[True], BeforeValidator(sandbox_confirmation)]


@router.get("/calls/{call_id}")
async def get_call(call_id: str, request: Request):
    return await request.app.state.platform.require("calls", call_id)


@router.post("/calls/{call_id}/reconcile")
async def reconcile_call(call_id: str, body: ReconcileCall, request: Request):
    return await request.app.state.dialer.reconcile(call_id, body.provider_call_id)


@callbacks.post("/webhooks/twilio/calls/{call_id}")
async def call_callback(call_id: UUID, request: Request):
    if request.url.query or request.headers.get("content-type", "").split(";")[0].lower() != "application/x-www-form-urlencoded":
        raise AppError(422, "call_callback_invalid_content", "Use the registered form callback URL without a query")
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 16384:
            raise AppError(413, "call_callback_too_large", "Callback exceeds 16 KB")
    await request.app.state.dialer.callback(str(call_id), bytes(data), request.headers.get("x-twilio-signature", ""))
    return Response(status_code=204)
