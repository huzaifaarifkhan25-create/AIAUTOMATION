"""Durable authenticated inquiry orchestration; acceptance is never delivery proof."""
import asyncio
import hashlib
import hmac
import json
import secrets
import time
from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from app.database.store import SQLiteStore
from app.errors import AppError
from app.models.execution import EmailRunRequest
from app.models.n8n import InquiryRequest
from app.models.workflow import now
from app.services.execution import ACTIVE


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Inquiries:
    def __init__(self, state):
        self.state, self.store = state, state.store
        self.supported = isinstance(self.store, SQLiteStore)
        self.lock = asyncio.Lock()
        self._attempts = {}

    def require_supported(self):
        if not self.supported:
            raise AppError(503, "inquiry_storage_unsupported", "Inquiry intake requires SQLite and one API worker")

    @staticmethod
    def source_view(record):
        return {k: v for k, v in record.items() if k not in {"key_hash", "request_hash"}}

    async def source(self, identifier):
        self.require_supported()
        return self.source_view(await self.state.platform.require("inquiry_sources", identifier))

    async def sources(self, include_demo=False):
        self.require_supported()
        records = await self.store.list("inquiry_sources")
        return [self.source_view(r) for r in sorted(records, key=lambda r: r["created_at"], reverse=True)
                if include_demo or not r["synthetic"]]

    async def ready_source(self, source):
        if source["status"] != "active":
            raise AppError(409, "inquiry_source_paused", "This inquiry source is paused")
        deployment = await self.state.n8n.managed(source["n8n_deployment_id"])
        if deployment["status"] != "active" or deployment["workflow_id"] != source["workflow_id"] or deployment["business_id"] != source["business_id"]:
            raise AppError(409, "inquiry_deployment_inactive", "The source's reviewed n8n deployment is no longer active")
        return deployment

    def require_email(self, source=None):
        delivery = self.state.execution.delivery
        delivery.require_configured()
        delivery.signing_key()
        if not self.state.settings.app_public_url:
            raise AppError(503, "inquiry_callback_required", "Email sources need APP_PUBLIC_URL and the signed Resend callback configured")
        if source and source.get("email_sender") != delivery.gateway.settings.resend_from_email:
            raise AppError(409, "inquiry_sender_changed", "The email sender changed; review and create a new source before sending acknowledgements")

    async def create_source(self, body):
        self.require_supported()
        if not body.confirm_activation:
            raise AppError(422, "inquiry_source_confirmation", "Review the source, fixed response and workflow before activation")
        identifier = str(uuid5(NAMESPACE_URL, "inquiry-source:" + str(body.request_id)))
        digest = fingerprint(body.model_dump(mode="json"))
        async with self.lock:
            previous = await self.store.get("inquiry_sources", identifier)
            if previous:
                if previous["request_hash"] != digest:
                    raise AppError(409, "inquiry_source_conflict", "This request ID belongs to different source settings")
                return {"source": self.source_view(previous), "webhook_key": None,
                        "intake_path": "/intake/" + identifier, "key_returned_once": True}
            deployment = await self.state.n8n.managed(str(body.n8n_deployment_id))
            if deployment["status"] != "active":
                raise AppError(409, "inquiry_deployment_inactive", "Choose an active reviewed n8n deployment")
            if body.email_mode == "email":
                if deployment["synthetic"]:
                    raise AppError(409, "mock_business", "Fictional sources cannot send email")
                self.require_email()
            key = secrets.token_urlsafe(48)
            stamp = now().isoformat()
            record = {"id": identifier, "name": body.name, "n8n_deployment_id": deployment["id"],
                      "workflow_id": deployment["workflow_id"], "business_id": deployment["business_id"],
                      "synthetic": deployment["synthetic"], "acknowledgement": body.acknowledgement,
                      "followup_delay_minutes": body.followup_delay_minutes, "email_mode": body.email_mode,
                      "email_subject": body.email_subject, "status": "active", "created_at": stamp,
                      "email_sender": self.state.execution.delivery.gateway.settings.resend_from_email if body.email_mode == "email" else None,
                      "updated_at": stamp, "key_rotated_at": stamp, "key_hash": hashlib.sha256(key.encode()).hexdigest(),
                      "request_hash": digest, "intake_path": "/intake/" + identifier,
                      "intake_url": self.state.settings.app_public_url.rstrip("/") + "/intake/" + identifier if self.state.settings.app_public_url else None,
                      "email_delivery_authorized": body.confirm_email_delivery}
            await self.store.put("inquiry_sources", identifier, record)
            return {"source": self.source_view(record), "webhook_key": key, "intake_path": record["intake_path"], "key_returned_once": True}

    async def authenticate_source(self, identifier, key, client):
        self.require_supported()
        # Bound unauthenticated attempts before lookup. Never log a supplied key.
        stamp = time.monotonic()
        bucket = (identifier, client)
        recent = [t for t in self._attempts.get(bucket, []) if stamp - t < 60]
        if len(recent) >= 30:
            raise AppError(429, "inquiry_rate_limited", "Too many intake attempts; wait one minute")
        if len(self._attempts) >= 1024 and bucket not in self._attempts:
            oldest = min(self._attempts, key=lambda k: self._attempts[k][-1])
            self._attempts.pop(oldest)
        self._attempts[bucket] = recent + [stamp]
        source = await self.store.get("inquiry_sources", identifier)
        supplied = hashlib.sha256(key.encode()).hexdigest() if 32 <= len(key) <= 200 else ""
        if not source or not hmac.compare_digest(source["key_hash"], supplied):
            raise AppError(401, "inquiry_key_invalid", "A valid X-Inquiry-Key is required")
        return source

    async def pause(self, identifier, confirmed):
        self.require_supported()
        if not confirmed:
            raise AppError(422, "inquiry_pause_confirmation", "Confirm pausing intake and pending acknowledgement work")
        async with self.state.execution.lock:
            source = await self.state.platform.require("inquiry_sources", identifier)
            source.update(status="paused", updated_at=now().isoformat())
            await self.store.put("inquiry_sources", identifier, source)
        for inquiry in await self.store.list("inquiries"):
            if inquiry["source_id"] == identifier and inquiry.get("email_run_id"):
                run = await self.store.get("workflow_runs", inquiry["email_run_id"])
                if run and run["status"] in ACTIVE:
                    try:
                        await self.state.execution.cancel(run["id"])
                    except AppError as error:
                        if error.code != "run_finished":
                            raise
        return self.source_view(source)

    async def rotate(self, identifier, confirmed):
        self.require_supported()
        if not confirmed:
            raise AppError(422, "inquiry_rotation_confirmation", "Confirm replacing the source key and invalidating the old key")
        async with self.state.execution.lock:
            source = await self.state.platform.require("inquiry_sources", identifier)
            key, stamp = secrets.token_urlsafe(48), now().isoformat()
            source.update(key_hash=hashlib.sha256(key.encode()).hexdigest(), key_rotated_at=stamp, updated_at=stamp)
            await self.store.put("inquiry_sources", identifier, source)
            return {"source": self.source_view(source), "webhook_key": key, "intake_path": source["intake_path"], "key_returned_once": True}

    async def receive(self, source_id, body, *, authenticated_hash):
        self.require_supported()
        if not body.contact_permission:
            raise AppError(422, "inquiry_permission_required", "Record contact permission before submitting a follow-up inquiry")
        identifier = str(uuid5(NAMESPACE_URL, "inquiry-event:" + source_id + ":" + body.event_id))
        digest = fingerprint(body.model_dump(mode="json"))
        async with self.lock:
            async with self.state.execution.lock:
                source = await self.state.platform.require("inquiry_sources", source_id)
                if not hmac.compare_digest(source["key_hash"], authenticated_hash):
                    raise AppError(401, "inquiry_key_rotated", "The source key changed while this request was being received")
                previous = await self.store.get("inquiries", identifier)
                if previous:
                    if previous["request_hash"] != digest:
                        raise AppError(409, "inquiry_event_conflict", "This source event ID belongs to different inquiry data")
                    return await self.view(previous)
                await self.ready_source(source)
                if source["email_mode"] == "email" and not body.recipient_email:
                    raise AppError(422, "inquiry_recipient_required", "This source requires the customer's permitted email address")
                if await self.state.execution.delivery.is_opted_out(source["business_id"], body.contact_reference, body.recipient_email):
                    raise AppError(409, "inquiry_contact_opted_out", "This contact is blocked from follow-up")
                stamp = now()
                record = {"id": identifier, "source_id": source_id, "business_id": source["business_id"],
                          "workflow_id": source["workflow_id"], "n8n_deployment_id": source["n8n_deployment_id"],
                          "synthetic": source["synthetic"], **body.model_dump(mode="json"), "request_hash": digest,
                          "status": "received", "received_at": stamp.isoformat(), "updated_at": stamp.isoformat(),
                          "followup_at": (stamp + timedelta(minutes=source["followup_delay_minutes"])).isoformat(),
                          "acknowledgement": source["acknowledgement"], "email_subject": source["email_subject"],
                          "email_mode": source["email_mode"], "processed_at": None, "n8n_run_id": None,
                          "execution_id": None, "task_id": None, "email_run_id": None, "error": None}
                # Pause/rotation share this guard with the durable reservation.
                if not await self.store.reserve("inquiries", identifier, record):
                    previous = await self.state.platform.require("inquiries", identifier)
                    if previous["request_hash"] != digest:
                        raise AppError(409, "inquiry_event_conflict", "This event ID belongs to different inquiry data")
                    return await self.view(previous)
            return await self._process(record)

    async def _process(self, record):
        native_started = False
        try:
            source = await self.state.platform.require("inquiry_sources", record["source_id"])
            await self.ready_source(source)
            if await self.state.execution.delivery.is_opted_out(record["business_id"], record["contact_reference"], record["recipient_email"]):
                raise AppError(409, "inquiry_contact_opted_out", "This contact is blocked from follow-up")
            if not record.get("task_id"):
                record.update(status="processing", error=None, updated_at=now().isoformat(),
                              n8n_run_id=str(uuid5(NAMESPACE_URL, "n8n-run:" + record["id"])))
                await self.store.put("inquiries", record["id"], record)
                native_started = True
                result = await self.state.n8n.run(record["n8n_deployment_id"], InquiryRequest(
                    request_id=record["id"], contact_reference=record["contact_reference"], inquiry=record["inquiry"],
                    acknowledgement=record["acknowledgement"], followup_at=record["followup_at"],
                    contact_permission=record["contact_permission"], confirm_run=True))
                task = await self.store.get("tasks", result.get("task_id", ""))
                if result.get("status") != "succeeded" or not result.get("execution_id") or not task or task["business_id"] != record["business_id"]:
                    raise AppError(502, "inquiry_execution_unverified", "The native execution did not establish a matching saved follow-up task")
                record.update(status="processed", processed_at=task["created_at"], n8n_run_id=result["id"],
                              execution_id=result["execution_id"], task_id=task["id"], updated_at=now().isoformat(), error=None)
                await self.store.put("inquiries", record["id"], record)
            if record["email_mode"] == "email":
                source = await self.state.platform.require("inquiry_sources", record["source_id"])
                self.require_email(source)
                await self.ready_source(source)
                # Save the deterministic linkage before waking the email runner.
                key = "inquiry:" + record["id"]
                record["email_run_id"] = str(uuid5(NAMESPACE_URL, f"medspa-run:{record['workflow_id']}:{key}"))
                await self.store.put("inquiries", record["id"], record)
                await self.state.execution.enqueue(record["workflow_id"], EmailRunRequest(
                    mode="email", confirm_send=True, idempotency_key=key,
                    event={"contact_id": record["contact_reference"], "contact_permission": record["contact_permission"]},
                    recipient_email=record["recipient_email"], subject=record["email_subject"], message_body=record["acknowledgement"]))
            record.update(error=None, updated_at=now().isoformat())
            await self.store.put("inquiries", record["id"], record)
            return await self.view(record)
        except AppError as error:
            if not record.get("task_id"):
                native_id = str(uuid5(NAMESPACE_URL, "n8n-run:" + record["id"]))
                native = await self.store.get("n8n_runs", native_id) if native_started else None
                record["n8n_run_id"] = native_id if native else record.get("n8n_run_id")
                record["status"] = "uncertain" if (native and native["status"] in {"processing", "uncertain"}) or error.code == "inquiry_execution_unverified" else "blocked"
            record.update(error=error.code, updated_at=now().isoformat())
            await self.store.put("inquiries", record["id"], record)
            return await self.view(record)

    async def check_native_task(self, native):
        """Called under the execution guard before committing a native task."""
        inquiry = next((r for r in await self.store.list("inquiries") if r.get("n8n_run_id") == native["id"]), None)
        if not inquiry:
            return
        source = await self.state.platform.require("inquiry_sources", inquiry["source_id"])
        await self.ready_source(source)
        if await self.state.execution.delivery.is_opted_out(inquiry["business_id"], inquiry["contact_reference"], inquiry["recipient_email"]):
            raise AppError(409, "inquiry_contact_opted_out", "This contact is blocked from follow-up")

    async def check_email_run(self, run):
        if run["mode"] != "email":
            return
        inquiry = next((r for r in await self.store.list("inquiries") if r.get("email_run_id") == run["id"]), None)
        if not inquiry:
            return
        source = await self.state.platform.require("inquiry_sources", inquiry["source_id"])
        await self.ready_source(source)
        self.require_email(source)
        if not inquiry.get("task_id") or inquiry["status"] != "processed" or not source["email_delivery_authorized"]:
            raise AppError(409, "inquiry_email_not_authorized", "A reviewed source and verified follow-up task are required before acknowledgement delivery")

    async def retry(self, identifier, confirmed):
        self.require_supported()
        if not confirmed:
            raise AppError(422, "inquiry_retry_confirmation", "Review the saved inquiry and confirm a safe retry")
        async with self.lock:
            record = await self.state.platform.require("inquiries", identifier)
            if record["status"] == "uncertain":
                raise AppError(409, "inquiry_reconciliation_required", "Inspect the existing n8n execution; an uncertain submission cannot be replayed")
            # enqueue uses the original ID; terminal/uncertain email attempts
            # are returned by the runner and never replaced or resent.
            return await self._process(record)

    async def recover(self):
        if not self.supported:
            return
        async with self.lock:
            for record in await self.store.list("inquiries"):
                if record["status"] == "processing":
                    native = await self.store.get("n8n_runs", str(uuid5(NAMESPACE_URL, "n8n-run:" + record["id"])))
                    if native and native["status"] in {"processing", "uncertain"}:
                        record.update(status="uncertain", error="inquiry_interrupted", updated_at=now().isoformat())
                        await self.store.put("inquiries", record["id"], record)
                        continue
                if record["status"] in {"received", "processing"} or (record["status"] == "processed" and record["email_mode"] == "email" and not await self.store.get("workflow_runs", record.get("email_run_id") or "")):
                    await self._process(record)

    async def view(self, record):
        result = {k: v for k, v in record.items() if k != "request_hash"}
        result.update(email_status="disabled" if record["email_mode"] == "none" else "not_enqueued",
                      outbox_id=None, email_submission_started_at=None, email_last_event_at=None,
                      email_submission_recorded=False, email_sent=False, delivered=False)
        if record.get("email_run_id"):
            run = await self.store.get("workflow_runs", record["email_run_id"])
            if run:
                result.update(email_status=run["status"], outbox_id=run.get("outbox_id"))
                if run.get("outbox_id"):
                    outbox = await self.store.get("workflow_outbox", run["outbox_id"])
                    if outbox:
                        result.update(email_status=outbox["status"], email_submission_started_at=outbox.get("submission_started_at"),
                                      email_submission_recorded=bool(outbox.get("provider_email_id")), email_sent=outbox.get("sent", False),
                                      email_last_event_at=outbox.get("last_event_at"), delivered=outbox.get("delivered", False))
        return result

    async def list(self, include_demo=False):
        self.require_supported()
        records = [r for r in await self.store.list("inquiries") if include_demo or not r["synthetic"]]
        return [await self.view(r) for r in sorted(records, key=lambda r: (r["received_at"], r["id"]), reverse=True)]

    async def get(self, identifier):
        self.require_supported()
        return await self.view(await self.state.platform.require("inquiries", identifier))

    async def summary(self, include_demo=False):
        records = await self.list(include_demo=include_demo)
        task_ids = {r["task_id"] for r in records if r.get("task_id")}
        tasks = [r for r in await self.store.list("tasks") if r["id"] in task_ids]
        times = [(datetime.fromisoformat(r["processed_at"]) - datetime.fromisoformat(r["received_at"])).total_seconds()
                 for r in records if r.get("processed_at")]
        return {"scope": "recorded_inquiry_sources", "include_demo": include_demo, "generated_at": now().isoformat(),
                "inquiries": {"received": len(records), "processed": sum(bool(r.get("task_id")) for r in records),
                    "pending": sum(r["status"] in {"received", "processing"} for r in records),
                    "uncertain": sum(r["status"] == "uncertain" for r in records),
                    "blocked": sum(r["status"] == "blocked" for r in records)},
                "tasks": {"created": len(tasks), "pending": sum(t["status"] == "pending" for t in tasks),
                    "completed": sum(t["status"] == "completed" for t in tasks),
                    "cancelled": sum(t["status"] == "cancelled" for t in tasks),
                    "overdue": sum(t["status"] == "pending" and datetime.fromisoformat(t["due_at"]) < now() for t in tasks)},
                "email": {"enabled": sum(r["email_mode"] == "email" for r in records),
                    "submitted": sum(r["email_submission_recorded"] for r in records),
                    "sent": sum(r["email_sent"] for r in records),
                    "delivered": sum(r["delivered"] for r in records),
                    "uncertain": sum(r["email_status"] in {"submission_started", "submission_uncertain"} for r in records),
                    "failed": sum(r["email_status"] in {"failed", "bounced", "complained", "suppressed"} for r in records),
                    "stopped": sum(r["email_status"] in {"skipped", "cancelled"} for r in records)},
                "mean_task_creation_seconds": round(sum(times) / len(times), 3) if times else None,
                "delivery_evidence": "Delivered requires a signed provider callback or matched provider reconciliation. Submission is not delivery.",
                "limitations": "Task creation time is not customer response time. No inferred bookings, revenue or time saved."}
