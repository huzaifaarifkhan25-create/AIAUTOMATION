from fastapi import APIRouter, Query, Request

from app.models.clients import ClientRequest, ConfirmActivation, ConfirmClient, DeploymentRequest
from app.models.execution import EmailRunRequest, RunRequest
from app.models.appointments import AppointmentRequest

router = APIRouter(tags=["Clients and workflow activation"])


@router.post("/clients", status_code=201)
async def create_client(body: ClientRequest, request: Request):
    return await request.app.state.clients.create(body)


@router.get("/clients")
async def list_clients(request: Request, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    request.app.state.execution.require_supported()
    return (await request.app.state.store.list("clients"))[offset:offset+limit]


@router.get("/clients/{client_id}")
async def get_client(client_id: str, request: Request):
    request.app.state.execution.require_supported()
    return await request.app.state.platform.require("clients", client_id)


@router.post("/clients/{client_id}/activate")
async def activate_client(client_id: str, body: ConfirmClient, request: Request):
    return await request.app.state.clients.state(client_id, "active")


@router.post("/clients/{client_id}/pause")
async def pause_client(client_id: str, request: Request):
    return await request.app.state.clients.state(client_id, "paused")


@router.post("/clients/{client_id}/archive")
async def archive_client(client_id: str, request: Request):
    return await request.app.state.clients.state(client_id, "archived")


@router.get("/clients/{client_id}/handoff")
async def export_handoff(client_id: str, request: Request):
    return await request.app.state.clients.handoff(client_id)


@router.post("/clients/{client_id}/deployments", status_code=201)
async def create_deployment(client_id: str, body: DeploymentRequest, request: Request):
    return await request.app.state.clients.deployment(client_id, body)


@router.get("/deployments")
async def list_deployments(request: Request, client_id: str | None = None,
                           limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    request.app.state.execution.require_supported()
    records = await request.app.state.store.list("deployments")
    if client_id:
        records = [r for r in records if r["client_id"] == client_id]
    return records[offset:offset+limit]


@router.get("/deployments/{deployment_id}")
async def get_deployment(deployment_id: str, request: Request):
    request.app.state.execution.require_supported()
    return await request.app.state.platform.require("deployments", deployment_id)


@router.get("/deployments/{deployment_id}/preflight")
async def preflight(deployment_id: str, request: Request):
    request.app.state.execution.require_supported()
    record = await request.app.state.platform.require("deployments", deployment_id)
    return await request.app.state.clients.preflight(record)


@router.post("/deployments/{deployment_id}/validate")
async def validate_deployment(deployment_id: str, request: Request):
    return await request.app.state.clients.validate(deployment_id)


@router.post("/deployments/{deployment_id}/activate")
async def activate_deployment(deployment_id: str, body: ConfirmActivation, request: Request):
    return await request.app.state.clients.state_deployment(deployment_id, "active")


@router.post("/deployments/{deployment_id}/pause")
async def pause_deployment(deployment_id: str, request: Request):
    return await request.app.state.clients.state_deployment(deployment_id, "paused")


@router.post("/deployments/{deployment_id}/archive")
async def archive_deployment(deployment_id: str, request: Request):
    return await request.app.state.clients.state_deployment(deployment_id, "archived")


@router.post("/deployments/{deployment_id}/runs", status_code=202)
async def deployment_run(deployment_id: str, body: RunRequest | EmailRunRequest, request: Request):
    return await request.app.state.execution.view(await request.app.state.clients.enqueue(deployment_id, body))


@router.get("/clients/{client_id}/history")
async def client_history(client_id: str, request: Request,
                         limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    request.app.state.execution.require_supported()
    await request.app.state.platform.require("clients", client_id)
    records = [r for r in await request.app.state.store.list("deployment_events") if r["client_id"] == client_id]
    records.sort(key=lambda r: (r["at"], r["id"]), reverse=True)
    return records[offset:offset+limit]


@router.post("/deployments/{deployment_id}/appointments", status_code=202)
async def deployment_appointment(deployment_id: str, body: AppointmentRequest, request: Request):
    return await request.app.state.appointments.create(body, deployment_id=deployment_id)
