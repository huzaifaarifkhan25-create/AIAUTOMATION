from fastapi import APIRouter, Request

from app.errors import AppError

router = APIRouter(tags=["Provider callbacks"])


@router.post("/webhooks/resend")
async def resend_callback(request: Request):
    runner = request.app.state.execution
    runner.require_supported()
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > 65536:
            raise AppError(413, "email_webhook_too_large", "Callback exceeds 64 KB")
    # Provider callbacks use their signature, never the shared workspace token.
    async with runner.lock:
        return await runner.delivery.accept_event(bytes(data), request.headers)
