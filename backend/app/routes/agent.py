import ipaddress
from uuid import UUID

from fastapi import APIRouter, Request

from app.errors import AppError
from app.models.agent import ChatRequest, ConnectionRequest, ConversationRequest, ReviewRequest

router = APIRouter(prefix="/agent", tags=["AI Agent"])


async def local_connection_allowed(request):
    try:
        local = request.app.state.settings.app_env == "development" and ipaddress.ip_address(request.client.host).is_loopback
        if not local:
            return False
        accounts = getattr(request.app.state, "accounts", None)
        if not accounts or not await accounts.session(request, required=False):
            return False
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            # A supplied bearer must not bypass the account's CSRF/origin guard
            # on the local credential form.
            from app.routes.auth import same_origin
            same_origin(request)
            await accounts.authorize_cookie(request)
        return True
    except (ValueError, AttributeError):
        return False


@router.get("/status")
async def status(request: Request):
    return request.app.state.agent.status(await local_connection_allowed(request))


@router.post("/connection")
async def connect(body: ConnectionRequest, request: Request):
    if not await local_connection_allowed(request):
        raise AppError(403, "agent_local_setup_only", "Sign in with an operator account on a local development laptop, or configure provider credentials in server environment settings")
    return await request.app.state.agent.connect(body)


@router.post("/verify")
async def verify(request: Request):
    return await request.app.state.agent.verify()


@router.delete("/connection")
async def disconnect(request: Request):
    if not await local_connection_allowed(request):
        raise AppError(403, "agent_local_setup_only", "Manage the hosted provider connection through server environment settings")
    return await request.app.state.agent.disconnect()


@router.post("/conversations", status_code=201)
async def create_conversation(body: ConversationRequest, request: Request):
    return await request.app.state.agent.create_conversation(body)


@router.get("/conversations")
async def conversations(request: Request):
    return await request.app.state.agent.conversations()


@router.get("/conversations/{conversation_id}")
async def conversation(conversation_id: UUID, request: Request):
    return await request.app.state.agent.conversation(str(conversation_id))


@router.post("/conversations/{conversation_id}/messages")
async def chat(conversation_id: UUID, body: ChatRequest, request: Request):
    return await request.app.state.agent.chat(str(conversation_id), body)


@router.post("/actions/{action_id}/review")
async def review(action_id: UUID, body: ReviewRequest, request: Request):
    return await request.app.state.agent.review(str(action_id), body)
