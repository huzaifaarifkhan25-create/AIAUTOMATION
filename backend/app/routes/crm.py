from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query, Request

from app.models.crm import ActivityRequest, TaskRequest, TaskUpdate
from app.models.workflow import now

router = APIRouter(tags=["Contact activity and tasks"])


@router.post("/businesses/{business_id}/activities", status_code=201)
async def record_activity(business_id: str, body: ActivityRequest, request: Request):
    return await request.app.state.crm.activity(business_id, body)


@router.get("/businesses/{business_id}/activities")
async def list_activity(business_id: str, request: Request,
                        limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    return (await request.app.state.crm.timeline(business_id))[offset:offset+limit]


@router.post("/businesses/{business_id}/tasks", status_code=201)
async def create_task(business_id: str, body: TaskRequest, request: Request):
    return await request.app.state.crm.task(business_id, body)


@router.get("/tasks")
async def list_tasks(request: Request, business_id: str | None = None,
                     status: Literal["pending", "completed", "cancelled"] | None = None,
                     overdue: bool = False, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    request.app.state.crm.require_supported()
    records = await request.app.state.store.list("tasks")
    if business_id:
        records = [r for r in records if r["business_id"] == business_id]
    if status:
        records = [r for r in records if r["status"] == status]
    if overdue:
        records = [r for r in records if r["status"] == "pending" and datetime.fromisoformat(r["due_at"]) < now()]
    records.sort(key=lambda r: (datetime.fromisoformat(r["due_at"]), r["id"]))
    return records[offset:offset+limit]


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    request.app.state.crm.require_supported()
    return await request.app.state.platform.require("tasks", task_id)


@router.patch("/tasks/{task_id}")
async def update_task(task_id: str, body: TaskUpdate, request: Request):
    return await request.app.state.crm.update_task(task_id, body.status)
