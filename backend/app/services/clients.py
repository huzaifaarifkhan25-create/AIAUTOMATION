"""Client onboarding, reviewed local workflow activation and authenticated handoff."""
import asyncio
import hashlib
import json
from copy import deepcopy
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.errors import AppError
from app.models.workflow import Analysis, Workflow, now
from app.services.crm import fingerprint
from app.services.workflows import generate_workflow


class Clients:
    def __init__(self, store, execution):
        self.store, self.execution, self.platform = store, execution, execution.platform
        self.lock = asyncio.Lock()

    def audit(self, client_id, outcome, deployment_id=None):
        return {"id": str(uuid4()), "client_id": client_id, "deployment_id": deployment_id,
                "outcome": outcome, "at": now().isoformat(), "actor": "shared_workspace_operator"}

    async def save_with_audit(self, kind, record, outcome):
        event = self.audit(record["id"] if kind == "clients" else record["client_id"], outcome,
                           record["id"] if kind == "deployments" else None)
        await self.store.put_many([(kind, record["id"], record), ("deployment_events", event["id"], event)])

    async def create(self, body):
        self.execution.require_supported()
        async with self.lock:
            business = await self.platform.require("businesses", body.business_id)
            key = str(uuid5(NAMESPACE_URL, f"medspa-client:{body.business_id}:{body.idempotency_key}"))
            digest = fingerprint(body)
            previous = await self.store.get("clients", key)
            if previous:
                if previous["request_hash"] != digest:
                    raise AppError(409, "client_key_conflict", "This key already belongs to different client inputs")
                return previous
            for client in await self.store.list("clients"):
                if client["business_id"] == body.business_id and client["status"] != "archived":
                    raise AppError(409, "client_exists", "Use the existing client for this business")
            stamp = now().isoformat()
            record = {"id": key, "business_id": body.business_id, "contact_name": body.contact_name,
                "contact_email": body.contact_email, "timezone": body.timezone,
                "approval_reference": body.approval_reference, "authorization_recorded": True,
                "is_demo": business["source"] == "mock", "status": "onboarding", "created_at": stamp,
                "updated_at": stamp, "request_hash": digest}
            await self.save_with_audit("clients", record, "client_created")
            return record

    async def state(self, client_id, status):
        self.execution.require_supported()
        async with self.lock, self.execution.lock:
            client = await self.platform.require("clients", client_id)
            if client["status"] == status:
                return client
            if client["status"] == "archived":
                raise AppError(409, "client_archived", "An archived client cannot be reactivated")
            if status == "active":
                contact = await self.store.get("contacts", client["business_id"])
                if contact and contact["stage"] == "do_not_contact":
                    raise AppError(409, "do_not_contact", "This business is marked do not contact")
            client.update(status=status, updated_at=now().isoformat())
            await self.save_with_audit("clients", client, "client_" + status)
        self.execution.wake.set()
        return client

    async def deployment(self, client_id, body):
        self.execution.require_supported()
        async with self.lock:
            client = await self.platform.require("clients", client_id)
            if client["status"] == "archived":
                raise AppError(409, "client_archived", "An archived client cannot create deployments")
            key = str(uuid5(NAMESPACE_URL, f"medspa-deployment:{client_id}:{body.idempotency_key}"))
            digest = fingerprint(body)
            previous = await self.store.get("deployments", key)
            if previous:
                if previous["request_hash"] != digest:
                    raise AppError(409, "deployment_key_conflict", "This key already belongs to different deployment inputs")
                return previous
            workflow = await self.platform.require("workflows", body.workflow_id)
            if workflow["business_id"] != client["business_id"]:
                raise AppError(409, "client_workflow_mismatch", "The workflow belongs to a different client's business")
            stamp = now().isoformat()
            record = {"id": key, "client_id": client_id, "business_id": client["business_id"],
                "workflow_id": body.workflow_id, "channel": body.channel, "status": "draft", "is_demo": client["is_demo"],
                "created_at": stamp, "updated_at": stamp, "request_hash": digest,
                "validation": None, "activation_at": None, "execution_location": "this_application"}
            await self.save_with_audit("deployments", record, "deployment_created")
            return record

    async def preflight(self, deployment):
        self.execution.require_supported()
        client = await self.platform.require("clients", deployment["client_id"])
        workflow = Workflow.model_validate(await self.platform.require("workflows", deployment["workflow_id"]))
        analysis = Analysis.model_validate(await self.platform.require("analyses", workflow.analysis_id))
        checks = []
        def check(code, passed, message):
            checks.append({"code": code, "passed": bool(passed), "message": message})
        check("client_active", client["status"] == "active", "Client must be active and authorization recorded")
        check("business_authorization", client["authorization_recorded"] and bool(client["approval_reference"]),
              "An operator must record the business authorization reference")
        check("workflow_ownership", workflow.business_id == client["business_id"] == deployment["business_id"],
              "Workflow and client must refer to the same business")
        try:
            await self.execution.check_current(workflow)
            check("current_workflow", True, "Workflow is current, unarchived and business is not blocked")
        except AppError as error:
            check("current_workflow", False, error.message)
        try:
            expected = generate_workflow(analysis)
            supported = workflow.nodes == expected.nodes and workflow.connections == expected.connections and not any(n.type == "calendar" for n in workflow.nodes)
        except AppError:
            supported = False
        check("supported_graph", supported, "Only supported generated message workflows can activate")
        proofs = [r for r in await self.store.list("workflow_runs") if r["workflow_id"] == workflow.id
            and r["mode"] == "sandbox" and r["status"] == "succeeded"]
        previous_proof = (deployment.get("validation") or {}).get("sandbox_proof_run_id")
        proof = next((r for r in proofs if r["id"] == previous_proof), None)
        if not proof:
            proof = min(proofs, key=lambda r: (r["created_at"], r["id"]), default=None)
        check("sandbox_test", proof is not None, "A successful sandbox run of this exact workflow is required")
        sender = None
        if deployment["channel"] == "email":
            check("real_client", not client["is_demo"], "Mock clients cannot activate live email")
            criterion = workflow.nodes[0].parameters.get("event") if workflow.nodes else None
            confirmed = any(e.criterion.value == criterion and e.assessment in {"strong", "partial"}
                and e.source == "business_confirmation" for e in analysis.evidence)
            check("confirmed_scope", confirmed, "The workflow's operational need must be business-confirmed")
            try:
                self.execution.delivery.require_configured()
                check("email_configured", True, "Email is enabled with configured sender and provider access")
            except AppError as error:
                check("email_configured", False, error.message)
            s = self.platform.gateway.settings
            try:
                self.execution.delivery.signing_key()
                valid_secret = True
            except AppError:
                valid_secret = False
            check("callback_configured", valid_secret and bool(s.app_public_url),
                  "Signed email callbacks need a valid runtime secret and public HTTPS app origin")
            sender = s.resend_from_email
        snapshot = {"client_id": client["id"], "client_updated_at": client["updated_at"],
            "workflow": workflow.model_dump(mode="json"), "analysis_id": analysis.id,
            "channel": deployment["channel"], "sender": sender,
            "proof_run_id": proof["id"] if proof else None, "checks": checks}
        digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
        return {"ready": all(c["passed"] for c in checks), "checks": checks, "fingerprint": digest,
            "checked_at": now().isoformat(), "provider_live_verified": False,
            "sandbox_proof_run_id": proof["id"] if proof else None}

    async def validate(self, deployment_id):
        self.execution.require_supported()
        async with self.lock:
            record = await self.platform.require("deployments", deployment_id)
            if record["status"] not in {"draft", "validated", "paused"}:
                raise AppError(409, "deployment_state_conflict", "Validate a draft or paused deployment")
            report = await self.preflight(record)
            record.update(validation=report, status="validated" if report["ready"] else "draft", updated_at=now().isoformat())
            await self.save_with_audit("deployments", record, "deployment_validated" if report["ready"] else "deployment_validation_failed")
            return record

    async def state_deployment(self, deployment_id, status):
        self.execution.require_supported()
        async with self.lock, self.execution.lock:
            record = await self.platform.require("deployments", deployment_id)
            if record["status"] == status:
                return record
            if record["status"] == "archived":
                raise AppError(409, "deployment_archived", "An archived deployment cannot reactivate")
            if status == "active":
                if record["status"] != "validated":
                    raise AppError(409, "deployment_not_validated", "Validate the deployment before activation")
                report = await self.preflight(record)
                if not report["ready"] or report["fingerprint"] != record["validation"]["fingerprint"]:
                    raise AppError(409, "deployment_validation_stale", "Configuration or evidence changed; validate again")
                record["activation_at"] = now().isoformat()
            record.update(status=status, updated_at=now().isoformat())
            await self.save_with_audit("deployments", record, "deployment_" + status)
        self.execution.wake.set()
        return record

    async def check_execution(self, deployment_id, workflow_id, mode):
        record = await self.platform.require("deployments", deployment_id)
        if record["status"] != "active":
            raise AppError(409, "deployment_inactive", "This deployment is not active")
        if record["workflow_id"] != workflow_id or record["channel"] != mode:
            raise AppError(409, "deployment_run_mismatch", "Run channel/workflow must match its deployment")
        report = await self.preflight(record)
        if not report["ready"] or report["fingerprint"] != record["validation"]["fingerprint"]:
            raise AppError(409, "deployment_validation_stale", "Client, workflow or provider configuration needs renewed validation")

    async def enqueue(self, deployment_id, body):
        self.execution.require_supported()
        record = await self.platform.require("deployments", deployment_id)
        # Execution checks again under its lock and includes deployment in the key.
        return await self.execution.enqueue(record["workflow_id"], body, deployment_id=deployment_id)

    async def handoff(self, client_id):
        self.execution.require_supported()
        client = await self.platform.require("clients", client_id)
        business = await self.platform.require("businesses", client["business_id"])
        deployments = [d for d in await self.store.list("deployments") if d["client_id"] == client_id]
        details = []
        for record in deployments:
            item = deepcopy(record)
            item["current_preflight"] = await self.preflight(record)
            item["workflow"] = await self.platform.require("workflows", record["workflow_id"])
            details.append(item)
        return {"format": "medspa-client-handoff-v1", "exported_at": now().isoformat(), "client": client,
            "business": business, "qualification": (await self.platform.qualification(client["business_id"])).model_dump(mode="json"),
            "deployments": details, "access_model": "shared_operator_token", "credentials_included": False,
            "publicly_deployed": False, "instructions": [
                "Review the business authorization, scope, timezone and message configuration with the client.",
                "Use authenticated deployment run endpoints with explicit recipient permission and timing.",
                "Pause the deployment or client to stop pending managed work; submitted messages cannot be recalled.",
                "Check delivery outbox evidence; provider acceptance alone is not delivery.",
                "This handoff does not provision hosting, individual accounts or a native calendar integration."]}
