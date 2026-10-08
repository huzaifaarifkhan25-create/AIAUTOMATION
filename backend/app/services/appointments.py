"""Authenticated appointment events; no calendar provider or availability engine."""
import asyncio
import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from pydantic import TypeAdapter

from app.errors import AppError
from app.models.appointments import Appointment
from app.models.execution import EmailRunRequest, RunRequest
from app.models.workflow import Workflow, now
from app.models.business import Business
from app.models.workflow import AnalyzeRequest


class Appointments:
    def __init__(self, store, execution):
        self.store, self.execution = store, execution
        self.lock = asyncio.Lock()

    async def demo_workflow(self):
        self.execution.require_supported()
        async with self.lock:
            platform = self.execution.platform
            business = await platform.save_business(Business(name="Demo Reminder Studio (Mock)", address="Fictional hackathon address",
                website=None, phone=None, rating=None, review_count=None), source="mock")
            if business.source != "mock":
                raise AppError(409, "demo_identity_conflict", "The demo identity conflicts with an existing non-demo record")
            analyses = [item for item in await self.store.list("analyses") if item["business_id"] == business.id]
            latest = max(analyses, key=lambda item: item["created_at"], default=None)
            if latest and latest["automation_type"] == "appointment_reminders":
                workflows = [item for item in await self.store.list("workflows")
                    if item["analysis_id"] == latest["id"] and item["status"] == "draft"]
                if workflows:
                    return {"business": business.model_dump(mode="json"), "workflow": workflows[0], "synthetic": True}
            analysis = await platform.analyze(business.id, AnalyzeRequest.model_validate({"evidence": [
                {"criterion": "appointment_reminders", "assessment": "strong", "source": "business_confirmation", "origin": "operator",
                 "detail": "Fictional demo confirmation only. This is not evidence about any real business."}]}))
            workflow = await platform.workflow(analysis.id)
            return {"business": business.model_dump(mode="json"), "workflow": workflow.model_dump(mode="json"), "synthetic": True}

    async def create(self, request, deployment_id=None):
        self.execution.require_supported()
        scope = f"deployment:{deployment_id}:" if deployment_id else ""
        appointment_id = str(uuid5(NAMESPACE_URL, f"medspa-appointment:{scope}{request.workflow_id}:{request.reminder.idempotency_key}"))
        payload = request.model_dump(mode="json")
        if deployment_id:
            payload["deployment_id"] = deployment_id
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        async with self.lock:
            previous = await self.store.get("appointments", appointment_id)
            if previous:
                if previous["request_hash"] != fingerprint:
                    raise AppError(409, "appointment_key_conflict", "This event key already belongs to different appointment inputs")
                if previous["status"] == "pending":
                    return await self.schedule(previous)
                return previous
            if request.starts_at <= now():
                raise AppError(422, "appointment_in_past", "Appointment starts_at must be in the future")
            workflow = Workflow.model_validate(await self.execution.platform.require("workflows", request.workflow_id))
            if deployment_id:
                if not self.execution.clients:
                    raise AppError(503, "client_service_unavailable", "Client workflow service is unavailable")
                await self.execution.clients.check_execution(deployment_id, workflow.id, request.reminder.mode)
            await self.execution.check_current(workflow)
            if workflow.nodes[0].parameters.get("event") != "appointment_reminders":
                raise AppError(409, "appointment_workflow_required", "Choose a generated appointment reminder workflow")
            if request.reminder.mode == "email":
                self.execution.delivery.require_configured()
                business = await self.execution.platform.require("businesses", workflow.business_id)
                if business["source"] == "mock":
                    raise AppError(409, "mock_business", "Demo businesses cannot send email")
            timestamp = now()
            record = Appointment(id=appointment_id, workflow_id=workflow.id, business_id=workflow.business_id,
                starts_at=request.starts_at, status="pending", created_at=timestamp, updated_at=timestamp,
                request_hash=fingerprint, reminder=request.reminder, deployment_id=deployment_id).model_dump(mode="json")
            await self.store.reserve("appointments", appointment_id, record)
            return await self.schedule(record)

    async def schedule(self, record):
        reminder = TypeAdapter(RunRequest | EmailRunRequest).validate_python(record["reminder"])
        try:
            # Use a private scoped event key; appointment ID is also hashed into the run.
            reminder.idempotency_key = "appointment:" + record["id"]
            run = await self.execution.enqueue(record["workflow_id"], reminder, appointment_id=record["id"], deployment_id=record.get("deployment_id"))
            record.update(status="scheduled", run_id=run["id"], updated_at=now().isoformat())
            await self.store.put("appointments", record["id"], record)
            return record
        except AppError as error:
            if error.code == "storage_unavailable":
                raise
            record.update(status="failed", error_code=error.code, updated_at=now().isoformat())
            await self.store.put("appointments", record["id"], record)
            raise

    async def recover(self):
        if not self.execution.supported:
            return
        async with self.lock:
            for record in await self.store.list("appointments"):
                if record["status"] == "pending":
                    try:
                        await self.schedule(record)
                    except AppError as error:
                        if error.code == "storage_unavailable":
                            raise

    async def cancel(self, appointment_id):
        self.execution.require_supported()
        async with self.lock:
            record = await self.execution.platform.require("appointments", appointment_id)
            record.update(status="cancelled", updated_at=now().isoformat())
            # Persist cancellation first: startup and message guards see it even
            # if the service stops before the associated run is marked cancelled.
            await self.store.put("appointments", record["id"], record)
            if record.get("run_id"):
                try:
                    await self.execution.cancel(record["run_id"])
                except AppError as error:
                    if error.code != "run_finished":
                        raise
            return record
