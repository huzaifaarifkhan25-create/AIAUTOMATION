from fastapi import APIRouter, Request

from app.models.ai import ChatRequest, ChatResponse, DraftRequest

router = APIRouter(prefix="/ai", tags=["AI drafts"])


@router.post("/businesses/{business_id}/analysis", status_code=201)
async def ai_analysis(business_id: str, request: Request):
    return await request.app.state.ai.analysis(business_id)


@router.get("/businesses/{business_id}/insights")
async def ai_insights(business_id: str, request: Request):
    return await request.app.state.ai.insights(business_id)


@router.post("/businesses/{business_id}/pitch")
async def ai_pitch(business_id: str, request: Request, body: DraftRequest | None = None):
    return await request.app.state.ai.pitch(business_id, body)


@router.post("/businesses/{business_id}/call-script")
async def ai_call_script(business_id: str, request: Request, body: DraftRequest | None = None):
    return await request.app.state.ai.call_script(business_id, body)


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(body: ChatRequest, request: Request):
    return await request.app.state.ai.chat(body)
