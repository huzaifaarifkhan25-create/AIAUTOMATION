from uuid import UUID

from fastapi import APIRouter, Request

from app.errors import AppError
from app.models.n8n import ConnectionRequest, DeployRequest, InquiryRequest
from app.routes.agent import local_connection_allowed
from app.services.n8n_template import inquiry_template

router = APIRouter(prefix="/n8n", tags=["n8n inquiry automation"])


@router.get("/status")
async def status(request: Request):
    return request.app.state.n8n.status(await local_connection_allowed(request))


@router.post("/connection")
async def connection(body: ConnectionRequest, request: Request):
    if not await local_connection_allowed(request):
        raise AppError(403, "n8n_local_setup_only", "Sign in with an operator account on a local development laptop, or configure N8N_BASE_URL and N8N_API_KEY in server environment settings")
    return await request.app.state.n8n.connect(body)


@router.delete("/connection")
async def disconnect(request: Request):
    if not await local_connection_allowed(request):
        raise AppError(403, "n8n_local_setup_only", "Manage hosted n8n credentials through environment settings")
    return await request.app.state.n8n.disconnect()


@router.get("/template")
async def template():
    return inquiry_template("AIAutomation inquiry follow-up", "configure-your-webhook-path")


@router.post("/demo")
async def demo(request: Request):
    return await request.app.state.n8n.demo_workflow()


@router.get("/deployments")
async def deployments(request: Request):
    return await request.app.state.n8n.deployments()


@router.post("/deployments", status_code=201)
async def deploy(body: DeployRequest, request: Request):
    return await request.app.state.n8n.deploy(body)


@router.post("/deployments/{deployment_id}/pause")
async def pause(deployment_id: UUID, request: Request):
    return await request.app.state.n8n.pause(str(deployment_id))


@router.post("/deployments/{deployment_id}/inquiries", status_code=201)
async def inquiry(deployment_id: UUID, body: InquiryRequest, request: Request):
    return await request.app.state.n8n.run(str(deployment_id), body)


@router.get("/runs")
async def runs(request: Request):
    return await request.app.state.n8n.runs()
