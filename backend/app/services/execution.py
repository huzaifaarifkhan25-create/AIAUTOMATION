"""One-worker durable execution with sandbox previews and guarded email actions."""
import asyncio
import hashlib
import json
import logging
from copy import deepcopy
from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from app.database.store import SQLiteStore
from app.errors import AppError
from app.models.execution import OutboxPreview, WorkflowRun
from app.models.workflow import Analysis, Workflow, now
from app.services.workflows import generate_workflow
from app.services.delivery import Delivery

ACTIVE = {"queued", "running", "waiting", "retry_wait"}
logger = logging.getLogger(__name__)


class Execution:
    def __init__(self, store, platform, clock=now, poll_seconds=.5):
        self.store, self.platform = store, platform
        self.clock, self.poll_seconds = clock, poll_seconds
        self.supported = isinstance(store, SQLiteStore)
        self.delivery = Delivery(store, platform.gateway, clock=clock)
        self.lock = asyncio.Lock()
        self.wake = asyncio.Event()
        self.task = None
        self.appointments = None
        self.clients = None

    def require_supported(self):
        if not self.supported:
            raise AppError(503, "runner_storage_unsupported", "The sandbox runner currently requires SQLite and one API worker")

    def history(self, run, outcome, step=None):
        run["updated_at"] = self.clock().isoformat()
        run["history"].append({"at": run["updated_at"], "step": step, "outcome": outcome})
        run["history"] = run["history"][-200:]

    async def save(self, run):
        await self.store.put("workflow_runs", run["id"], run)

    async def start(self):
        if not self.supported or self.task:
            return
        async with self.lock:
            for run in await self.store.list("workflow_runs"):
                if run["status"] == "running":
                    run["status"] = "queued"
                    self.history(run, "recovered_after_restart")
                    await self.save(run)
        self.task = asyncio.create_task(self.worker())

    async def close(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None

    async def worker(self):
        while True:
            self.wake.clear()
            try:
                if self.appointments:
                    await self.appointments.recover()
                await self.tick()
            except Exception:
                # Do not expose storage/provider messages or credentials in logs.
                logger.warning("Sandbox runner storage cycle failed; will retry")
            try:
                await asyncio.wait_for(self.wake.wait(), timeout=self.poll_seconds)
            except TimeoutError:
                pass

    async def enqueue(self, workflow_id, request, appointment_id=None, deployment_id=None):
        self.require_supported()
        scope = f"deployment:{deployment_id}:" if deployment_id else ""
        run_id = str(uuid5(NAMESPACE_URL, f"medspa-run:{scope}{workflow_id}:{request.idempotency_key}"))
        payload = request.model_dump(mode="json")
        if appointment_id:
            payload["appointment_id"] = appointment_id
        if deployment_id:
            payload["deployment_id"] = deployment_id
        request_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        async with self.lock:
            previous = await self.store.get("workflow_runs", run_id)
            if previous:
                if previous["request_hash"] != request_hash:
                    raise AppError(409, "run_key_conflict", "This key already belongs to different run inputs")
                return previous
            if deployment_id:
                if not self.clients:
                    raise AppError(503, "client_service_unavailable", "Client workflow service is unavailable")
                await self.clients.check_execution(deployment_id, workflow_id, request.mode)
            workflow = Workflow.model_validate(await self.platform.require("workflows", workflow_id))
            await self.check_current(workflow)
            if request.mode == "email":
                self.delivery.require_configured()
                business = await self.platform.require("businesses", workflow.business_id)
                if business["source"] == "mock":
                    raise AppError(409, "mock_business", "Demo businesses cannot send email")
            analysis = Analysis.model_validate(await self.platform.require("analyses", workflow.analysis_id))
            expected = generate_workflow(analysis)
            if (workflow.nodes != expected.nodes or workflow.connections != expected.connections
                    or any(node.type == "calendar" for node in workflow.nodes)):
                raise AppError(409, "workflow_unsupported", "The sandbox runner supports only the generated message workflows; calendar actions need an integration")
            if any(node.type == "delay" for node in workflow.nodes) and request.scheduled_at is None:
                raise AppError(422, "run_timing_required", "Supply scheduled_at for a workflow containing a delay")
            if request.scheduled_at is not None and not any(node.type == "delay" for node in workflow.nodes):
                raise AppError(422, "run_timing_unused", "This workflow has no delay node; scheduled_at would not be used")
            timestamp = self.clock()
            run = WorkflowRun(id=run_id, workflow_id=workflow_id, business_id=workflow.business_id,
                analysis_id=workflow.analysis_id, mode=request.mode, status="queued", created_at=timestamp,
                updated_at=timestamp, request_hash=request_hash, event=request.event,
                message_body=request.message_body, scheduled_at=request.scheduled_at,
                workflow_snapshot=workflow, appointment_id=appointment_id, deployment_id=deployment_id,
                recipient_email=getattr(request, "recipient_email", None), subject=getattr(request, "subject", None)).model_dump(mode="json")
            self.history(run, "queued")
            if not await self.store.reserve("workflow_runs", run_id, run):
                previous = await self.platform.require("workflow_runs", run_id)
                if previous["request_hash"] != request_hash:
                    raise AppError(409, "run_key_conflict", "This key already belongs to different run inputs")
                return previous
        self.wake.set()
        return run

    async def view(self, run):
        result = deepcopy(run)
        if run["mode"] == "email" and run.get("outbox_id"):
            outbox = await self.store.get("workflow_outbox", run["outbox_id"])
            if outbox:
                result.update(sent=outbox["sent"], delivery_status=outbox["status"])
        return result

    async def check_current(self, workflow):
        current = Workflow.model_validate(await self.platform.require("workflows", workflow.id))
        if current.status == "archived":
            raise AppError(409, "workflow_archived", "An archived workflow cannot run")
        if current.business_id != workflow.business_id or current.analysis_id != workflow.analysis_id or current.nodes != workflow.nodes or current.connections != workflow.connections:
            raise AppError(409, "workflow_changed", "The workflow definition changed; create a new run")
        await self.platform.require("businesses", workflow.business_id)
        contact = await self.store.get("contacts", workflow.business_id)
        if contact and contact.get("stage") == "do_not_contact":
            raise AppError(409, "do_not_contact", "This business is marked do not contact")
        analysis = Analysis.model_validate(await self.platform.require("analyses", workflow.analysis_id))
        await self.platform.require_current_analysis(analysis)

    async def finish(self, run, status, reason):
        run.update(status=status, stop_reason=reason, next_at=None, finished_at=self.clock().isoformat())
        self.history(run, reason)
        await self.save(run)

    async def cancel(self, run_id):
        self.require_supported()
        async with self.lock:
            run = await self.platform.require("workflow_runs", run_id)
            if run["status"] == "cancelled":
                return run
            if run["status"] not in ACTIVE:
                raise AppError(409, "run_finished", "This run already finished; history remains available")
            await self.finish(run, "cancelled", "cancelled_by_operator")
            return run

    async def tick(self):
        self.require_supported()
        async with self.lock:
            for run in await self.store.list("workflow_runs"):
                if run["status"] not in ACTIVE:
                    continue
                if run["status"] == "retry_wait" and run["next_at"] and datetime.fromisoformat(run["next_at"]) > self.clock():
                    continue
                checkpoint = deepcopy(run)
                try:
                    # Guards are checked even during waits and immediately before actions.
                    await self.check_current(Workflow.model_validate(run["workflow_snapshot"]))
                    if run.get("deployment_id"):
                        if not self.clients:
                            raise AppError(503, "client_service_unavailable", "Client workflow service is unavailable")
                        await self.clients.check_execution(run["deployment_id"], run["workflow_id"], run["mode"])
                    if await self.delivery.is_opted_out(run["business_id"], run["event"]["contact_id"],
                            run.get("recipient_email") if run["mode"] == "email" else None):
                        await self.finish(run, "skipped", "contact_opted_out")
                        continue
                    if run.get("appointment_id"):
                        appointment = await self.platform.require("appointments", run["appointment_id"])
                        if appointment["status"] == "cancelled" or datetime.fromisoformat(appointment["starts_at"]) <= self.clock():
                            await self.finish(run, "skipped", "appointment_cancelled" if appointment["status"] == "cancelled" else "appointment_expired")
                            continue
                    if not run["event"]["contact_permission"] or run["event"]["appointment_cancelled"]:
                        await self.finish(run, "skipped", "contact_permission_missing" if not run["event"]["contact_permission"] else "appointment_cancelled")
                        continue
                    if run["next_at"] and datetime.fromisoformat(run["next_at"]) > self.clock():
                        continue
                    await self.advance(run)
                except AppError as error:
                    if error.status_code == 503 and error.code == "storage_unavailable":
                        checkpoint["outbox_id"] = run.get("outbox_id")
                        step = checkpoint["workflow_snapshot"]["nodes"][checkpoint["next_step"]]["id"]
                        checkpoint["step_attempts"][step] = max(checkpoint["step_attempts"].get(step, 0) + 1,
                            run["step_attempts"].get(step, 0))
                        await self.retry(checkpoint)
                    else:
                        checkpoint["outbox_id"] = run.get("outbox_id")
                        await self.finish(checkpoint, "failed" if error.status_code >= 500 else "skipped", error.code)
                except Exception:
                    await self.finish(checkpoint, "failed", "execution_failed")
            await self.delivery.reconcile_events()

    async def retry(self, run):
        nodes = run["workflow_snapshot"]["nodes"]
        step = nodes[min(run["next_step"], len(nodes)-1)]["id"]
        attempts = max(1, run["step_attempts"].get(step, 0))
        run["step_attempts"][step] = attempts
        if attempts >= 3:
            await self.finish(run, "failed", "retry_limit_reached")
        else:
            run.update(status="retry_wait", next_at=(self.clock() + timedelta(seconds=2 ** (attempts-1))).isoformat())
            self.history(run, "storage_retry_scheduled", step)
            await self.save(run)

    async def advance(self, run):
        nodes = run["workflow_snapshot"]["nodes"]
        node = nodes[run["next_step"]]
        step = node["id"]
        if node["type"] == "delay" and datetime.fromisoformat(run["scheduled_at"]) > self.clock():
            run.update(status="waiting", next_at=run["scheduled_at"])
            self.history(run, "waiting_until_scheduled_time", step)
            await self.save(run)
            return
        run.update(status="running", next_at=None)
        run["step_attempts"][step] = run["step_attempts"].get(step, 0) + 1
        self.history(run, "step_started", step)
        await self.save(run)
        if node["type"] == "message":
            outbox_id = str(uuid5(NAMESPACE_URL, f"medspa-outbox:{run['id']}:{step}"))
            run["outbox_id"] = outbox_id
            await self.save(run)
            if run["mode"] == "email":
                self.delivery.require_configured()
            preview = OutboxPreview(id=outbox_id, run_id=run["id"], workflow_id=run["workflow_id"],
                business_id=run["business_id"], contact_id=run["event"]["contact_id"], mode=run["mode"],
                status="preview_created" if run["mode"] == "sandbox" else "submission_started", message_body=run["message_body"], created_at=self.clock(),
                recipient_email=run.get("recipient_email"), subject=run.get("subject"),
                from_email=self.delivery.gateway.settings.resend_from_email if run["mode"] == "email" else None,
                submission_started_at=self.clock() if run["mode"] == "email" else None)
            # Atomic reserve makes replay after a crash safe even if progress was not saved.
            created = await self.store.reserve("workflow_outbox", outbox_id, preview.model_dump(mode="json"))
            if run["mode"] == "email":
                if created:
                    await self.delivery.submit(preview.model_dump(mode="json"))
                else:
                    previous = await self.store.get("workflow_outbox", outbox_id)
                    if not previous.get("provider_email_id"):
                        if previous["status"] == "submission_started":
                            previous["status"] = "submission_uncertain"
                            await self.store.put("workflow_outbox", outbox_id, previous)
                        raise AppError(502, "email_submission_uncertain", "A previous email attempt needs provider reconciliation; it cannot be automatically repeated")
        elif node["type"] == "database":
            run["result"] = "sandbox_recorded" if run["mode"] == "sandbox" else "email_submission_recorded"
        elif node["type"] not in {"webhook", "condition", "delay"}:
            raise AppError(409, "workflow_unsupported", "This action is not implemented in the sandbox runner")
        self.history(run, "step_completed", step)
        run["next_step"] += 1
        if run["next_step"] == len(nodes):
            await self.finish(run, "succeeded", "sandbox_completed" if run["mode"] == "sandbox" else "email_submission_recorded")
        else:
            run["status"] = "queued"
            await self.save(run)
