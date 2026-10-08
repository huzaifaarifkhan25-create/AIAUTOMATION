from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, BeforeValidator, ConfigDict

from app.models.execution import EmailRunRequest, OutboxPreview, Reference, RunRequest, WorkflowRun, sandbox_confirmation

router = APIRouter(tags=["Workflow execution"])


@router.post("/workflows/{workflow_id}/runs", response_model=WorkflowRun, status_code=202)
async def enqueue_run(workflow_id: str, body: RunRequest | EmailRunRequest, request: Request):
    return await request.app.state.execution.view(await request.app.state.execution.enqueue(workflow_id, body))


@router.get("/workflow-runs", response_model=list[WorkflowRun])
async def list_runs(request: Request, workflow_id: str | None = None,
                    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    request.app.state.execution.require_supported()
    records = await request.app.state.store.list("workflow_runs")
    if workflow_id:
        records = [record for record in records if record["workflow_id"] == workflow_id]
    records.sort(key=lambda record: (record["created_at"], record["id"]), reverse=True)
    return [await request.app.state.execution.view(record) for record in records[offset:offset+limit]]


@router.get("/workflow-runs/{run_id}", response_model=WorkflowRun)
async def get_run(run_id: str, request: Request):
    request.app.state.execution.require_supported()
    return await request.app.state.execution.view(await request.app.state.platform.require("workflow_runs", run_id))


@router.post("/workflow-runs/{run_id}/cancel", response_model=WorkflowRun)
async def cancel_run(run_id: str, request: Request):
    return await request.app.state.execution.view(await request.app.state.execution.cancel(run_id))


@router.get("/workflow-outbox", response_model=list[OutboxPreview])
async def list_outbox(request: Request, run_id: str | None = None,
                      limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    request.app.state.execution.require_supported()
    records = await request.app.state.store.list("workflow_outbox")
    if run_id:
        records = [record for record in records if record["run_id"] == run_id]
    records.sort(key=lambda record: (record["created_at"], record["id"]), reverse=True)
    return records[offset:offset+limit]


class ReconcileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_email_id: UUID
    confirm_provider_record: Annotated[Literal[True], BeforeValidator(sandbox_confirmation)]


@router.post("/workflow-outbox/{outbox_id}/reconcile", response_model=OutboxPreview)
async def reconcile_email(outbox_id: str, body: ReconcileRequest, request: Request):
    runner = request.app.state.execution
    runner.require_supported()
    async with runner.lock:
        outbox = await request.app.state.platform.require("workflow_outbox", outbox_id)
        return await runner.delivery.reconcile_provider(outbox, str(body.provider_email_id))


@router.post("/businesses/{business_id}/automation-contacts/{contact_id}/opt-out")
async def opt_out_contact(business_id: str, contact_id: Reference, request: Request):
    runner = request.app.state.execution
    runner.require_supported()
    await request.app.state.platform.require("businesses", business_id)
    async with runner.lock:
        return await runner.delivery.opt_out(business_id, contact_id)
