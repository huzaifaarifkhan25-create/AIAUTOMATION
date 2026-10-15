"""Bounded n8n inquiry integration with execution readback and durable CRM tasks."""
import asyncio
import hashlib
import hmac
import ipaddress
import json
import re
import socket
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

import httpx

from app.database.store import SQLiteStore
from app.errors import AppError
from app.models.business import Business
from app.models.crm import TaskRequest
from app.models.workflow import AnalyzeRequest, now
from app.services.n8n_template import inquiry_template
from types import SimpleNamespace


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class N8N:
    def __init__(self, state, transport=None):
        self.state, self.store = state, state.store
        self.supported = isinstance(self.store, SQLiteStore)
        self.base_url, self._key = state.settings.n8n_base_url.rstrip("/"), state.settings.n8n_api_key
        self.source = "environment" if self._key and self.base_url else "none"
        self.checked_at = None
        self.lock = asyncio.Lock()
        self.transport = transport

    def status(self, local_setup=False):
        return {"supported": self.supported, "configured": bool(self.base_url and self._key),
                "base_url": self.base_url, "connection_source": self.source,
                "connection_verified": self.checked_at is not None, "checked_at": self.checked_at,
                "local_connection_allowed": self.supported and local_setup,
                "template": "inquiry_followup", "customer_messages_sent": False}

    def require_supported(self):
        if not self.supported:
            raise AppError(503, "n8n_storage_unsupported", "This n8n pilot requires SQLite")

    async def validate_origin(self, base):
        try:
            p = urlsplit(base)
            port = p.port
            if not p.hostname or p.username or p.password or p.query or p.fragment or p.path not in {"", "/"}:
                raise ValueError()
            local = p.hostname in {"localhost", "127.0.0.1", "::1"}
            if p.scheme == "http" and local and self.state.settings.app_env == "development":
                return
            if p.scheme != "https" or local:
                raise ValueError()
            # Credentials may be sent only to an explicit public HTTPS origin.
            addresses = await asyncio.to_thread(socket.getaddrinfo, p.hostname, port or 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                raise ValueError()
        except (ValueError, OSError):
            raise AppError(422, "n8n_origin_invalid", "Use your public HTTPS n8n origin, or http://127.0.0.1:5678 for local development") from None

    async def request(self, method, path, *, body=None, webhook_secret=None, base=None, key=None):
        base, key = base or self.base_url, key or self._key
        if not base or not key:
            raise AppError(503, "n8n_not_configured", "Connect n8n in Automations before deploying or running this template")
        await self.validate_origin(base)
        local = urlsplit(base).hostname in {"localhost", "127.0.0.1", "::1"}
        headers = {"X-AIAutomation-Token": webhook_secret} if webhook_secret else {"X-N8N-API-KEY": key}
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=not local, transport=self.transport) as client:
                async with client.stream(method, base + path, headers=headers, json=body) as response:
                    if response.status_code >= 300:
                        if webhook_secret and response.status_code == 404:
                            await response.aread()
                            try:
                                missing = response.json().get("message", "")
                            except (ValueError, AttributeError):
                                missing = ""
                            if "not registered" in missing:
                                raise AppError(503, "n8n_webhook_starting", "n8n is still registering this workflow's webhook")
                        code = "n8n_access_rejected" if response.status_code in {401, 403} else "n8n_request_failed"
                        message = "n8n rejected access. Check the API key and its workflow, credential and execution permissions" if code == "n8n_access_rejected" else f"n8n returned HTTP {response.status_code}. Check the connection and workflow in n8n"
                        raise AppError(502, code, message)
                    data = bytearray()
                    async for part in response.aiter_bytes():
                        data.extend(part)
                        if len(data) > 2_000_000:
                            raise AppError(502, "n8n_response_large", "n8n returned too much execution data")
                    result = json.loads(data)
                    if not isinstance(result, dict):
                        raise ValueError()
                    return result
        except (httpx.HTTPError, ValueError):
            raise AppError(502, "n8n_unreachable", "Could not obtain a valid response from n8n. Check that the server is running and reachable") from None

    async def connect(self, body):
        self.require_supported()
        base, key = body.base_url.rstrip("/"), body.api_key.get_secret_value().strip()
        if not 12 <= len(key) <= 4096 or any(c.isspace() for c in key):
            raise AppError(422, "n8n_key_invalid", "Supply a valid n8n API key")
        async with self.lock:
            result = await self.request("GET", "/api/v1/workflows?limit=1", base=base, key=key)
            if not isinstance(result.get("data"), list):
                raise AppError(502, "n8n_invalid_response", "The server did not return the n8n workflow API response")
            self.base_url, self._key, self.source, self.checked_at = base, key, "session", now().isoformat()
        return self.status(True)

    async def disconnect(self):
        async with self.lock:
            self.base_url, self._key, self.source, self.checked_at = "", "", "none", None
        return self.status(True)

    def connection_id(self):
        return digest([self.base_url, self._key])

    def webhook_secret(self, identifier):
        return hmac.new(self._key.encode(), ("aiautomation:" + identifier).encode(), hashlib.sha256).hexdigest()

    async def current_workflow(self, identifier):
        self.require_supported()
        workflow = await self.state.platform.require("workflows", identifier)
        business = await self.state.platform.require("businesses", workflow["business_id"])
        analysis = await self.state.platform.require("analyses", workflow["analysis_id"])
        await self.state.platform.require_current_analysis(SimpleNamespace(**analysis))
        contact = await self.store.get("contacts", business["id"])
        confirmed = any(item.get("criterion") == "inquiry_followup" and item.get("source") == "business_confirmation"
                        and item.get("assessment") in {"strong", "partial"} for item in analysis.get("evidence", []))
        if workflow["status"] != "draft" or analysis["automation_type"] != "inquiry_followup" or not confirmed or analysis["business_id"] != business["id"]:
            raise AppError(409, "n8n_template_unsupported", "Only a current inquiry follow-up draft with a recorded business-confirmed need can use this n8n template")
        if contact and contact["stage"] == "do_not_contact":
            raise AppError(409, "do_not_contact", "This business is blocked from follow-up")
        return workflow, business

    async def demo_workflow(self):
        self.require_supported()
        async with self.lock:
            business = await self.state.platform.save_business(Business(name="Demo Inquiry Studio (Mock)", address="Fictional hackathon address", website=None, phone=None, rating=None, review_count=None), source="mock")
            if business.source != "mock":
                raise AppError(409, "demo_identity_conflict", "The demo conflicts with a non-demo business")
            analyses = [r for r in await self.store.list("analyses") if r["business_id"] == business.id]
            latest = max(analyses, key=lambda r: r["created_at"], default=None)
            if latest and latest["automation_type"] == "inquiry_followup":
                for workflow in await self.store.list("workflows"):
                    if workflow["analysis_id"] == latest["id"] and workflow["status"] == "draft":
                        return {"business": business.model_dump(mode="json"), "workflow": workflow, "synthetic": True}
            analysis = await self.state.platform.analyze(business.id, AnalyzeRequest.model_validate({"evidence": [
                {"criterion": "inquiry_followup", "assessment": "strong", "source": "business_confirmation", "origin": "operator",
                 "detail": "Fictional demo: inquiries need a follow-up task. This is not evidence about a real business."}]}))
            workflow = await self.state.platform.workflow(analysis.id)
            return {"business": business.model_dump(mode="json"), "workflow": workflow.model_dump(mode="json"), "synthetic": True}

    @staticmethod
    def deployment_view(record):
        return {k: v for k, v in record.items() if k not in {"connection_id", "request_hash", "webhook_path", "credential_id"}}

    async def deployments(self):
        self.require_supported()
        return [self.deployment_view(r) for r in await self.store.list("n8n_deployments")]

    async def runs(self):
        self.require_supported()
        return [{k: v for k, v in r.items() if k not in {"request_hash", "payload", "response"}} for r in await self.store.list("n8n_runs")]

    async def deploy(self, body):
        self.require_supported()
        if not body.confirm_deployment:
            raise AppError(422, "n8n_confirmation_required", "Review and confirm creating and activating this n8n workflow")
        async with self.lock:
            workflow, business = await self.current_workflow(body.workflow_id)
            if not self._key:
                raise AppError(503, "n8n_not_configured", "Connect n8n first")
            identifier = str(uuid5(NAMESPACE_URL, "n8n-deploy:" + str(body.request_id)))
            fingerprint = digest(body.model_dump(mode="json"))
            existing = await self.store.get("n8n_deployments", identifier)
            if existing:
                if existing["request_hash"] != fingerprint or existing["connection_id"] != self.connection_id():
                    raise AppError(409, "n8n_deployment_conflict", "This deployment request belongs to different inputs or a different connection")
                if existing["status"] == "active":
                    return self.deployment_view(existing)
                raise AppError(409, "n8n_deployment_finished", "Inspect this deployment in n8n before requesting another deployment")
            # One active managed copy per local workflow and connection.
            for item in await self.store.list("n8n_deployments"):
                if item["workflow_id"] == workflow["id"] and item["connection_id"] == self.connection_id() and item["status"] == "active":
                    return self.deployment_view(item)
            stamp = now().isoformat()
            record = {"id": identifier, "workflow_id": workflow["id"], "business_id": business["id"],
                      "business_name": business["business"]["name"], "synthetic": business["source"] == "mock",
                      "connection_id": self.connection_id(), "request_hash": fingerprint,
                      "webhook_path": "aiautomation-inquiry-" + identifier, "status": "deploying",
                      "remote_workflow_id": None, "credential_id": None, "created_at": stamp, "updated_at": stamp, "error": None}
            await self.store.put("n8n_deployments", identifier, record)
            try:
                credential = await self.request("POST", "/api/v1/credentials", body={"name": "AIAutomation inquiry authentication", "type": "httpHeaderAuth",
                    "data": {"name": "X-AIAutomation-Token", "value": self.webhook_secret(identifier)}})
                record["credential_id"] = str(credential["id"])
                await self.store.put("n8n_deployments", identifier, record)
                remote = await self.request("POST", "/api/v1/workflows", body=inquiry_template("AIAutomation · " + record["business_name"], record["webhook_path"], record["credential_id"]))
                record["remote_workflow_id"] = str(remote["id"])
                await self.store.put("n8n_deployments", identifier, record)
                active = await self.request("POST", f"/api/v1/workflows/{record['remote_workflow_id']}/activate", body={})
                if active.get("active") is not True:
                    raise AppError(502, "n8n_activation_unverified", "n8n did not confirm activation; inspect the remote workflow")
                record.update(status="active", updated_at=now().isoformat())
                self.checked_at = now().isoformat()
            except (AppError, KeyError, TypeError) as error:
                record.update(status="uncertain", error=error.message if isinstance(error, AppError) else "n8n returned an incomplete deployment response", updated_at=now().isoformat())
                await self.store.put("n8n_deployments", identifier, record)
                raise AppError(502, "n8n_deployment_uncertain", record["error"] + ". No automatic redeployment was attempted") from None
            await self.store.put("n8n_deployments", identifier, record)
            return self.deployment_view(record)

    async def managed(self, identifier, require_current=True):
        record = await self.state.platform.require("n8n_deployments", identifier)
        if record["connection_id"] != self.connection_id():
            raise AppError(409, "n8n_connection_changed", "Reconnect the original n8n origin and key to manage this deployment")
        if require_current:
            await self.current_workflow(record["workflow_id"])
        return record

    @staticmethod
    def verify_template(remote, deployment):
        """Reject externally edited graphs, including extra or disabled nodes.

        n8n adds presentation/version fields to stored workflows. Only the
        graph's behavior is compared; credentials are compared by their IDs,
        never by their private values or editable display names.
        """
        expected = inquiry_template("", deployment["webhook_path"], deployment["credential_id"])
        nodes = remote.get("nodes") if isinstance(remote, dict) else None
        valid = isinstance(nodes, list) and len(nodes) == len(expected["nodes"])
        valid = valid and all(isinstance(node, dict) and isinstance(node.get("name"), str) for node in (nodes or []))
        if valid:
            by_name = {node.get("name"): node for node in nodes if isinstance(node, dict)}
            valid = len(by_name) == len(expected["nodes"])
            # n8n materializes these documented node defaults in execution
            # snapshots, even when the saved graph omitted them. Only these
            # exact harmless defaults may differ from the submitted template.
            defaults = {
                "Receive inquiry": {"multipleMethods": False, "webhookNotice": ""},
                "Prepare follow-up": {"mode": "manual", "duplicateItem": False, "includeOtherFields": False},
                "Return task instruction": {"enableResponseOutput": False, "generalNotice": "", "webhookNotice": ""},
            }
            for target in expected["nodes"]:
                actual = by_name.get(target["name"], {})
                parameters = dict(actual["parameters"]) if isinstance(actual.get("parameters"), dict) else None
                if parameters is not None:
                    for field, default in defaults[target["name"]].items():
                        if field in parameters and parameters[field] == default:
                            parameters.pop(field)
                if any(actual.get(field) != target.get(field) for field in ("type", "typeVersion")) or parameters != target["parameters"]:
                    valid = False
                if any(actual.get(field, False) for field in ("disabled", "executeOnce", "alwaysOutputData", "retryOnFail", "continueOnFail")):
                    valid = False
                if actual.get("onError", "stopWorkflow") != "stopWorkflow":
                    valid = False
                credentials = actual.get("credentials", {})
                if target.get("credentials"):
                    if not isinstance(credentials, dict) or set(credentials) != {"httpHeaderAuth"} or not isinstance(credentials["httpHeaderAuth"], dict) or str(credentials["httpHeaderAuth"].get("id")) != deployment["credential_id"]:
                        valid = False
                elif credentials:
                    valid = False
            valid = valid and remote.get("connections") == expected["connections"]
            settings = remote.get("settings", {})
            valid = valid and isinstance(settings, dict) and settings.get("executionOrder", "v1") == "v1" and not settings.get("errorWorkflow")
        if not valid:
            raise AppError(409, "n8n_template_changed", "The remote n8n workflow differs from the supported inquiry template. Review it in n8n before processing")

    async def pause(self, identifier):
        async with self.lock:
            record = await self.managed(identifier, require_current=False)
            if record["status"] == "paused":
                return self.deployment_view(record)
            if record["status"] != "active":
                raise AppError(409, "n8n_deployment_not_active", "Only an active managed deployment can be paused")
            result = await self.request("POST", f"/api/v1/workflows/{record['remote_workflow_id']}/deactivate", body={})
            if result.get("active") is not False:
                raise AppError(502, "n8n_pause_unverified", "n8n did not confirm that the workflow was paused")
            # Email-run guards read this state under the same action lock.
            # A completed pause must be ordered with any in-flight submission.
            async with self.state.execution.lock:
                record.update(status="paused", updated_at=now().isoformat())
                await self.store.put("n8n_deployments", identifier, record)
            return self.deployment_view(record)

    async def finalize(self, record):
        payload = record["payload"]
        try:
            # Research commits/archive use this same guard. A confirmed need
            # must still be current when the task is committed, after network I/O.
            async with self.state.execution.lock:
                deployment = await self.state.platform.require("n8n_deployments", record["deployment_id"])
                if deployment["status"] != "active":
                    raise AppError(409, "n8n_deployment_not_active", "This deployment is paused; no follow-up task can be committed")
                await self.current_workflow(deployment["workflow_id"])
                if not payload.get("contact_permission") or await self.state.execution.delivery.is_opted_out(record["business_id"], payload["contact_reference"]):
                    raise AppError(409, "contact_opted_out", "This customer has opted out; no follow-up task can be committed")
                inquiries = getattr(self.state, "inquiries", None)
                if inquiries is not None:
                    await inquiries.check_native_task(record)
                task = await self.state.crm.task(record["business_id"], TaskRequest(idempotency_key="n8n:" + record["id"],
                    title="Follow up on inquiry: " + payload["contact_reference"],
                    notes="Inquiry: " + payload["inquiry"] + "\nUnsent acknowledgement draft: " + payload["acknowledgement"] + "\nn8n execution: " + record["execution_id"],
                    due_at=payload["followup_at"]))
        except AppError as error:
            record.update(error=error.message, updated_at=now().isoformat())
            await self.store.put("n8n_runs", record["id"], record)
            raise
        record.update(status="succeeded", task_id=task["id"], acknowledgement=payload["acknowledgement"],
                      delivery_status="unsent_draft", updated_at=now().isoformat(), error=None)
        await self.store.put("n8n_runs", record["id"], record)
        return {k: v for k, v in record.items() if k not in {"request_hash", "payload", "response"}}

    async def run(self, identifier, body):
        self.require_supported()
        if not body.confirm_run or not body.contact_permission:
            raise AppError(422, "n8n_run_confirmation_required", "Confirm processing this inquiry and permission to create its follow-up task")
        async with self.lock:
            deployment = await self.managed(identifier)
            key = str(uuid5(NAMESPACE_URL, "n8n-run:" + str(body.request_id)))
            fingerprint = digest([identifier, body.model_dump(mode="json")])
            previous = await self.store.get("n8n_runs", key)
            if previous:
                if previous["request_hash"] != fingerprint:
                    raise AppError(409, "n8n_run_conflict", "This run request belongs to different inputs")
                if previous["status"] == "processed":
                    return await self.finalize(previous)
                if previous["status"] == "succeeded":
                    return {k: v for k, v in previous.items() if k not in {"request_hash", "payload", "response"}}
                raise AppError(409, "n8n_run_finished", "Inspect the recorded n8n execution before submitting another inquiry")
            if deployment["status"] != "active" or body.followup_at <= now():
                raise AppError(409, "n8n_run_not_ready", "Use an active deployment and a future follow-up time")
            if await self.state.execution.delivery.is_opted_out(deployment["business_id"], body.contact_reference):
                raise AppError(409, "contact_opted_out", "This customer has opted out; do not process a follow-up inquiry")
            # Check before invoking the webhook so an edited workflow cannot
            # silently add email, code or network actions to this bounded flow.
            remote = await self.request("GET", f"/api/v1/workflows/{deployment['remote_workflow_id']}")
            if remote.get("active") is not True or str(remote.get("id")) != deployment["remote_workflow_id"]:
                raise AppError(409, "n8n_remote_not_active", "n8n does not confirm the expected workflow is active")
            self.verify_template(remote, deployment)
            payload = {"run_id": key, "business_id": deployment["business_id"], **{k: v for k, v in body.model_dump(mode="json").items()
                       if k not in {"request_id", "confirm_run"}}}
            record = {"id": key, "deployment_id": identifier, "business_id": deployment["business_id"], "synthetic": deployment["synthetic"],
                      "request_hash": fingerprint, "payload": payload, "status": "processing", "execution_id": None,
                      "task_id": None, "created_at": now().isoformat(), "updated_at": now().isoformat(), "error": None}
            await self.store.put("n8n_runs", key, record)
            try:
                # Activation can return before n8n registers its webhook. Retry
                # only n8n's explicit 'not registered' response (no execution).
                for attempt in range(12):
                    try:
                        result = await self.request("POST", "/webhook/" + deployment["webhook_path"], body=payload, webhook_secret=self.webhook_secret(identifier))
                        break
                    except AppError as error:
                        if error.code != "n8n_webhook_starting" or attempt == 11:
                            raise
                        await asyncio.sleep(0.2)
                execution_id = str(result.get("execution_id", ""))
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", execution_id) or result.get("delivery_status") != "unsent_draft" or any(result.get(k) != payload[k] for k in ("run_id", "business_id", "contact_reference", "inquiry", "acknowledgement", "followup_at")):
                    raise AppError(502, "n8n_output_mismatch", "n8n returned output that did not match this inquiry")
                record.update(execution_id=execution_id, response=result)
                await self.store.put("n8n_runs", key, record)
                for attempt in range(12):
                    proof = await self.request("GET", f"/api/v1/executions/{execution_id}?includeData=true")
                    if proof.get("status") == "success":
                        break
                    if proof.get("status") not in {"new", "running"}:
                        raise AppError(502, "n8n_execution_failed", "n8n did not finish this execution successfully")
                    await asyncio.sleep(0.2)
                output = proof.get("data", {}).get("resultData", {}).get("runData", {}).get("Prepare follow-up", [])
                actual = output[0]["data"]["main"][0][0]["json"] if output else None
                if str(proof.get("id")) != execution_id or str(proof.get("workflowId")) != deployment["remote_workflow_id"] or proof.get("status") != "success" or actual != result:
                    raise AppError(502, "n8n_execution_unverified", "Could not verify matching output in the successful n8n execution")
                # The saved execution contains the graph actually used. Check
                # it as well in case an owner edited the graph after preflight.
                self.verify_template(proof.get("workflowData") or proof.get("data", {}).get("workflowData"), deployment)
                record.update(status="processed", updated_at=now().isoformat())
                await self.store.put("n8n_runs", key, record)
            except (AppError, KeyError, TypeError, IndexError) as error:
                record.update(status="uncertain", updated_at=now().isoformat(), error=error.message if isinstance(error, AppError) else "n8n execution proof was incomplete")
                await self.store.put("n8n_runs", key, record)
                raise AppError(502, "n8n_run_uncertain", record["error"] + ". No automatic replay was attempted; inspect the recorded n8n execution") from None
            return await self.finalize(record)

    async def recover(self):
        if not self.supported:
            return
        for kind, running in (("n8n_runs", "processing"), ("n8n_deployments", "deploying")):
            for record in await self.store.list(kind):
                if record["status"] == running:
                    record.update(status="uncertain", error="Server restarted during the n8n operation. Inspect n8n before retrying", updated_at=now().isoformat())
                    await self.store.put(kind, record["id"], record)
