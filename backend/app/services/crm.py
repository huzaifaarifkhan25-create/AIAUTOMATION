"""Single-workspace contact history and manual follow-up tasks; no auto outreach."""
import asyncio
import hashlib
import json
from datetime import datetime
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.database.store import SQLiteStore
from app.errors import AppError
from app.models.workflow import Contact, now


def fingerprint(model):
    return hashlib.sha256(json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class CRM:
    def __init__(self, store, platform):
        self.store, self.platform = store, platform
        self.supported = isinstance(store, SQLiteStore)
        self.lock = asyncio.Lock()

    def require_supported(self):
        if not self.supported:
            raise AppError(503, "crm_storage_unsupported", "Contact history and tasks currently require SQLite")

    def entry(self, business_id, kind, notes, **fields):
        stamp = now().isoformat()
        return {"id": str(uuid4()), "business_id": business_id, "kind": kind,
                "notes": notes, "occurred_at": stamp, "created_at": stamp,
                "origin": "system", "direction": "internal", **fields}

    async def update_contact(self, business_id, update):
        self.require_supported()
        async with self.lock:
            await self.platform.require("businesses", business_id)
            previous = await self.store.get("contacts", business_id)
            if previous and previous["stage"] == update.stage and previous["notes"] == update.notes:
                return Contact.model_validate(previous)
            contact = Contact(business_id=business_id, stage=update.stage, notes=update.notes, updated_at=now())
            activity = self.entry(business_id, "stage_changed", update.notes,
                previous_stage=previous["stage"] if previous else "new", stage=update.stage)
            await self.store.put_many([("contacts", business_id, contact.model_dump(mode="json")),
                                       ("activities", activity["id"], activity)])
            return contact

    async def activity(self, business_id, body):
        self.require_supported()
        async with self.lock:
            await self.platform.require("businesses", business_id)
            key = str(uuid5(NAMESPACE_URL, f"medspa-activity:{business_id}:{body.idempotency_key}"))
            digest = fingerprint(body)
            previous = await self.store.get("activities", key)
            if previous:
                if previous["request_hash"] != digest:
                    raise AppError(409, "activity_key_conflict", "This key already belongs to different activity inputs")
                return previous
            if body.occurred_at > now():
                raise AppError(422, "activity_in_future", "Record an actual past or current activity")
            record = self.entry(business_id, body.kind, body.notes, id=key, origin="operator",
                occurred_at=body.occurred_at.isoformat(), direction=body.direction, request_hash=digest)
            await self.store.put("activities", key, record)
            return record

    async def task(self, business_id, body):
        self.require_supported()
        async with self.lock:
            await self.platform.require("businesses", business_id)
            key = str(uuid5(NAMESPACE_URL, f"medspa-task:{business_id}:{body.idempotency_key}"))
            digest = fingerprint(body)
            previous = await self.store.get("tasks", key)
            if previous:
                if previous["request_hash"] != digest:
                    raise AppError(409, "task_key_conflict", "This key already belongs to different task inputs")
                return previous
            contact = await self.store.get("contacts", business_id)
            if contact and contact["stage"] == "do_not_contact":
                raise AppError(409, "do_not_contact", "Do not schedule follow-up for a blocked business")
            stamp = now().isoformat()
            record = {"id": key, "business_id": business_id, "title": body.title, "notes": body.notes,
                      "due_at": body.due_at.isoformat(), "status": "pending", "created_at": stamp,
                      "updated_at": stamp, "request_hash": digest}
            activity = self.entry(business_id, "task_created", body.title, task_id=key)
            await self.store.put_many([("tasks", key, record), ("activities", activity["id"], activity)])
            return record

    async def update_task(self, task_id, status):
        self.require_supported()
        async with self.lock:
            task = await self.platform.require("tasks", task_id)
            if task["status"] == status:
                return task
            if task["status"] != "pending":
                raise AppError(409, "task_finished", "This task is already finished")
            task.update(status=status, updated_at=now().isoformat())
            activity = self.entry(task["business_id"], "task_" + status, task["title"], task_id=task_id)
            await self.store.put_many([("tasks", task_id, task), ("activities", activity["id"], activity)])
            return task

    async def timeline(self, business_id):
        self.require_supported()
        await self.platform.require("businesses", business_id)
        activities, calls, runs = await asyncio.gather(*(self.store.list(kind) for kind in ("activities", "calls", "workflow_runs")))
        records = [r for r in activities if r["business_id"] == business_id]
        for call in calls:
            if call["business_id"] == business_id:
                records.append({"id": "call:" + call["id"], "business_id": business_id, "kind": "dialer_attempt",
                    "origin": "provider_adapter", "occurred_at": call["created_at"], "status": call["status"],
                    "provider_status": call.get("provider_status"), "leg": "sales_agent", "call_id": call["id"]})
        for run in runs:
            if run["business_id"] == business_id:
                records.append({"id": "run:" + run["id"], "business_id": business_id, "kind": "workflow_run",
                    "origin": "runner", "occurred_at": run["created_at"], "status": run["status"],
                    "mode": run["mode"], "run_id": run["id"]})
        return sorted(records, key=lambda r: (datetime.fromisoformat(r["occurred_at"]), r["id"]), reverse=True)
