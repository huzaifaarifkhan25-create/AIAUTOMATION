from fastapi import APIRouter, Query, Request

from app.models.business import Business, BusinessSearchRequest
from app.models.workflow import (
    Analysis, AnalyzeRequest, BusinessRecord, CallRequest, Contact,
    ContactUpdate, Workflow, WorkflowRequest, now,
)
from app.services.business_search import search_mock_businesses
from app.models.qualification import Qualification
from collect_leads import collector_configured

router = APIRouter(tags=["Platform"])


@router.get("/ready")
async def ready(request: Request):
    await request.app.state.store.get("businesses", "readiness-probe")
    return {"status": "ready", "persistence": request.app.state.settings.persistence_backend}


@router.get("/capabilities")
async def capabilities(request: Request):
    s = request.app.state.settings
    return {
        "persistence": s.persistence_backend,
        "discovery_configured": bool(s.google_places_api_key),
        "browser_collection_configured": collector_configured(s.browser_runtime),
        "browser_collection_runtime": s.browser_runtime,
        "ai_configured": bool(s.llm_api_key),
        "gemini_configured": bool(s.gemini_api_key),
        "supabase_configured": bool(s.supabase_url and s.supabase_key),
        "website_fetching_configured": bool(s.website_allowed_hosts),
        "calling_enabled": s.enable_outbound_calls,
        "calling_configured": bool(s.app_api_token and s.twilio_account_sid and s.twilio_auth_token and s.twilio_from_number and s.sales_agent_number),
        "workflow_execution_supported": False,
        "workflow_runner_modes": (["sandbox", "email"] if request.app.state.execution.delivery.configured else ["sandbox"]) if request.app.state.execution.supported else [],
        "workflow_runner_storage": "sqlite_single_worker",
        "email_delivery_enabled": s.enable_email_delivery,
        "email_delivery_configured": request.app.state.execution.delivery.configured,
        "email_webhook_configured": bool(s.resend_webhook_secret),
        "crm_history_supported": request.app.state.crm.supported,
        "client_workflow_activation_supported": request.app.state.execution.supported,
        "call_outcomes_storage_supported": request.app.state.crm.supported,
        "call_callbacks_configured": bool(s.app_public_url and s.twilio_auth_token and s.twilio_account_sid),
        "public_origin_configured": bool(s.app_public_url),
    }


@router.post("/businesses", response_model=BusinessRecord, status_code=201)
async def save_business(business: Business, request: Request):
    return await request.app.state.platform.save_business(business)


@router.post("/businesses/import", response_model=list[BusinessRecord])
async def import_businesses(search: BusinessSearchRequest, request: Request):
    businesses = search_mock_businesses(search)[:search.limit] if search.source == "mock" else await request.app.state.gateway.discover(search)
    return [await request.app.state.platform.save_business(business, source=search.source) for business in businesses]


@router.get("/businesses", response_model=list[BusinessRecord])
async def list_businesses(request: Request, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    return (await request.app.state.store.list("businesses"))[offset:offset+limit]


@router.get("/businesses/{business_id}", response_model=BusinessRecord)
async def get_business(business_id: str, request: Request):
    return await request.app.state.platform.require("businesses", business_id)


@router.post("/businesses/{business_id}/analyze", response_model=Analysis, status_code=201)
async def analyze_business(business_id: str, body: AnalyzeRequest, request: Request):
    return await request.app.state.platform.analyze(business_id, body)


@router.get("/analyses", response_model=list[Analysis])
async def list_analyses(request: Request, business_id: str | None = None,
                        limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    records = await request.app.state.store.list("analyses")
    if business_id:
        records = [r for r in records if r["business_id"] == business_id]
    records.sort(key=lambda r: r["created_at"], reverse=True)
    return records[offset:offset+limit]


@router.get("/analyses/{analysis_id}", response_model=Analysis)
async def get_analysis(analysis_id: str, request: Request):
    return await request.app.state.platform.require("analyses", analysis_id)


@router.get("/opportunities", response_model=list[Analysis])
async def rank_opportunities(request: Request, include_provisional: bool = False,
                              include_demo: bool = False,
                              limit: int = Query(100, ge=1, le=500)):
    return (await request.app.state.platform.opportunities(include_provisional, include_demo))[:limit]


@router.get("/prospects", response_model=list[Qualification])
async def rank_prospects(request: Request, include_demo: bool = False, include_blocked: bool = False,
                         limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    return (await request.app.state.platform.prospects(include_demo, include_blocked))[offset:offset+limit]


@router.get("/businesses/{business_id}/qualification", response_model=Qualification)
async def qualify_business(business_id: str, request: Request):
    return await request.app.state.platform.qualification(business_id)


@router.post("/workflows", response_model=Workflow, status_code=201)
async def create_workflow(body: WorkflowRequest, request: Request):
    return await request.app.state.platform.workflow(body.analysis_id)


@router.get("/workflows", response_model=list[Workflow])
async def list_workflows(request: Request, business_id: str | None = None,
                        limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    records = await request.app.state.store.list("workflows")
    if business_id:
        records = [r for r in records if r["business_id"] == business_id]
    return records[offset:offset+limit]


@router.get("/workflows/{workflow_id}", response_model=Workflow)
@router.get("/workflows/{workflow_id}/export", response_model=Workflow)
async def get_workflow(workflow_id: str, request: Request):
    return await request.app.state.platform.require("workflows", workflow_id)


@router.post("/workflows/{workflow_id}/archive", response_model=Workflow)
async def archive_workflow(workflow_id: str, request: Request):
    return await request.app.state.platform.archive_workflow(workflow_id)


@router.get("/businesses/{business_id}/contact", response_model=Contact)
async def get_contact(business_id: str, request: Request):
    await request.app.state.platform.require("businesses", business_id)
    return await request.app.state.store.get("contacts", business_id) or {
        "business_id": business_id, "stage": "new", "notes": "", "updated_at": now(),
    }


@router.patch("/businesses/{business_id}/contact", response_model=Contact)
async def update_contact(business_id: str, body: ContactUpdate, request: Request):
    return await request.app.state.platform.update_contact(business_id, body)


@router.get("/businesses/{business_id}/outreach-draft")
async def outreach_draft(business_id: str, analysis_id: str, request: Request):
    return await request.app.state.platform.outreach_draft(business_id, analysis_id)


@router.post("/businesses/{business_id}/calls", status_code=202)
async def call_business(business_id: str, body: CallRequest, request: Request):
    return await request.app.state.platform.call(business_id, body)


@router.get("/calls")
async def list_calls(request: Request, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    return (await request.app.state.store.list("calls"))[offset:offset+limit]
