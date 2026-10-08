import asyncio
from collections import Counter
from datetime import datetime

from fastapi import APIRouter, Query, Request

from app.errors import AppError
from app.models.workflow import now
from app.services.execution import ACTIVE

router = APIRouter(tags=["Operations monitoring"])


@router.get("/operations/summary")
async def operations(request: Request, include_demo: bool = False,
                     alert_limit: int = Query(100, ge=1, le=500)):
    request.app.state.execution.require_supported()
    kinds = ("businesses", "clients", "deployments", "workflow_runs", "workflow_outbox", "appointments", "tasks", "calls", "discovery_jobs")
    data = dict(zip(kinds, await asyncio.gather(*(request.app.state.store.list(kind) for kind in kinds))))
    allowed = {r["id"] for r in data["businesses"] if include_demo or r["source"] != "mock"}
    for kind in kinds:
        if kind not in {"businesses", "discovery_jobs"}:
            data[kind] = [r for r in data[kind] if r["business_id"] in allowed]
    checked_at = now()
    alerts = []
    for deployment in data["deployments"]:
        if deployment["status"] != "active":
            continue
        failed_checks = []
        try:
            readiness = await request.app.state.clients.preflight(deployment)
            stale = readiness["fingerprint"] != (deployment.get("validation") or {}).get("fingerprint")
            if readiness["ready"] and not stale:
                continue
            failed_checks = [c["code"] for c in readiness["checks"] if not c["passed"]]
            reason = "deployment_validation_stale"
        except AppError as error:
            if error.status_code != 404:
                raise
            reason = "deployment_reference_missing"
        alerts.append({"type": "deployment_readiness", "id": deployment["id"],
            "business_id": deployment["business_id"], "client_id": deployment["client_id"],
            "status": "blocked", "reason": reason, "failed_checks": failed_checks, "at": checked_at.isoformat()})
    for run in data["workflow_runs"]:
        if run["status"] in {"failed", "retry_wait"}:
            alerts.append({"type": "workflow_run", "id": run["id"], "business_id": run["business_id"],
                "status": run["status"], "reason": run.get("stop_reason"), "at": run["updated_at"]})
    for outbox in data["workflow_outbox"]:
        if outbox["status"] in {"submission_started", "submission_uncertain", "bounced", "complained", "failed", "suppressed"}:
            alerts.append({"type": "message_outcome", "id": outbox["id"], "business_id": outbox["business_id"],
                "status": outbox["status"], "at": outbox["created_at"]})
    for task in data["tasks"]:
        if task["status"] == "pending" and datetime.fromisoformat(task["due_at"]) < checked_at:
            alerts.append({"type": "overdue_task", "id": task["id"], "business_id": task["business_id"],
                "status": "overdue", "at": task["due_at"]})
    for call in data["calls"]:
        if call["status"] in {"pending", "failed_or_uncertain"} or call.get("provider_status") in {"busy", "failed", "no-answer"}:
            alerts.append({"type": "call_outcome", "id": call["id"], "business_id": call["business_id"],
                "status": call.get("provider_status") or call["status"], "at": call["created_at"], "leg": "sales_agent"})
    for appointment in data["appointments"]:
        if appointment["status"] in {"pending", "failed"}:
            alerts.append({"type": "appointment", "id": appointment["id"], "business_id": appointment["business_id"],
                "status": appointment["status"], "reason": appointment.get("error_code"), "at": appointment["updated_at"]})
    for job in data["discovery_jobs"]:
        if job["status"] in {"failed", "interrupted"}:
            alerts.append({"type": "discovery_job", "id": job["id"], "status": job["status"], "at": job["created_at"]})
    alerts.sort(key=lambda r: (datetime.fromisoformat(r["at"]), r["id"]), reverse=True)
    return {"checked_at": checked_at.isoformat(), "include_demo": include_demo, "businesses": len(allowed),
        "counts": {kind: dict(Counter(r["status"] for r in data[kind])) for kind in kinds if kind != "businesses"},
        "active_runs": sum(r["status"] in ACTIVE for r in data["workflow_runs"]),
        "scheduler_running": bool(request.app.state.execution.task and not request.app.state.execution.task.done()),
        "alert_count": len(alerts), "alerts": alerts[:alert_limit], "alerts_truncated": len(alerts) > alert_limit,
        "live_provider_verification": "not_recorded", "storage": "sqlite_single_worker"}
