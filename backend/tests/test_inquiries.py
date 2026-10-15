"""Real local intake/CRM orchestration with simulated external n8n and email."""
import base64
import asyncio
import copy
from dataclasses import replace
import hashlib
import hmac
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx

from app.main import create_app
from app.errors import AppError
from app.models.n8n import ConnectionRequest, DeployRequest
from app.settings import Settings

TOKEN = "synthetic-inquiry-owner-token"
PROVIDER_ID = "00000000-0000-4000-8000-000000000abc"
WEBHOOK_KEY = b"inquiry-fixture-signing-secret-only"


class InquiryFixture:
    async def asyncSetUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.settings = Settings(database_path=str(Path(temp.name) / "fixture.sqlite3"), app_api_token=TOKEN,
            app_public_url="https://automation.example.com", enable_email_delivery=True,
            resend_api_key="synthetic-resend-key", resend_from_email="sender@example.com",
            resend_webhook_secret="whsec_" + base64.b64encode(WEBHOOK_KEY).decode())
        self.remote = None
        self.webhook_calls = self.email_calls = 0
        self.fail_native = self.fail_email = False
        from app.services.gateway import Gateway
        gateway = Gateway(self.settings, httpx.MockTransport(self.email_provider))
        self.app = create_app(self.settings, gateway=gateway)
        self.store, self.service = self.app.state.store, self.app.state.inquiries
        self.app.state.n8n.transport = httpx.MockTransport(self.n8n_provider)
        self.owner = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app, client=("127.0.0.1", 1234)),
            base_url="http://testserver", headers={"Authorization": "Bearer " + TOKEN})
        self.sender = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app, client=("198.51.100.5", 1234)), base_url="http://testserver")
        self.addAsyncCleanup(self.owner.aclose); self.addAsyncCleanup(self.sender.aclose)
        saved = await self.owner.post("/businesses", json={"name": "Synthetic Inquiry Fixture", "address": "Fictional only",
            "website": None, "phone": None, "rating": None, "review_count": None})
        self.assertEqual(saved.status_code, 201, saved.text)
        business = saved.json()
        self.bid = business["id"]
        analysis = (await self.owner.post(f"/businesses/{self.bid}/analyze", json={"evidence": [
            {"criterion": "inquiry_followup", "assessment": "strong", "source": "business_confirmation", "detail": "Synthetic fixture business authorization."}]})).json()
        self.workflow = (await self.owner.post("/workflows", json={"analysis_id": analysis["id"]})).json()
        await self.app.state.n8n.connect(ConnectionRequest(base_url="http://127.0.0.1:5678", api_key="synthetic-n8n-api-key"))
        self.deployment = await self.app.state.n8n.deploy(DeployRequest(request_id=uuid4(), workflow_id=self.workflow["id"], confirm_deployment=True))

    def n8n_provider(self, request):
        path = request.url.path
        if path == "/api/v1/workflows" and request.method == "GET":
            return httpx.Response(200, json={"data": []})
        if path == "/api/v1/credentials":
            return httpx.Response(200, json={"id": "credential-fixture"})
        if path == "/api/v1/workflows":
            self.remote = json.loads(request.content); self.remote.update(id="workflow-fixture", active=True)
            return httpx.Response(200, json={"id": "workflow-fixture"})
        if path.endswith("/activate"):
            return httpx.Response(200, json={"active": True})
        if path.endswith("/deactivate"):
            self.remote["active"] = False
            return httpx.Response(200, json={"active": False})
        if path == "/api/v1/workflows/workflow-fixture":
            return httpx.Response(200, json=self.remote)
        if path.startswith("/webhook/"):
            self.webhook_calls += 1
            self.payload = json.loads(request.content)
            self.output = {k: v for k, v in self.payload.items() if k != "contact_permission"}
            self.output.update(execution_id="fixture-execution", delivery_status="unsent_draft")
            return httpx.Response(200, json=self.output)
        if path.startswith("/api/v1/executions/"):
            return httpx.Response(200, json={"id": "fixture-execution", "workflowId": "workflow-fixture",
                "workflowData": copy.deepcopy(self.remote), "status": "error" if self.fail_native else "success",
                "data": {"resultData": {"runData": {"Prepare follow-up": [{"data": {"main": [[{"json": self.output}]]}}]}}}})
        raise AssertionError("Unexpected native provider endpoint")

    def email_provider(self, request):
        self.email_calls += 1
        if self.fail_email:
            raise httpx.ReadTimeout("Synthetic timeout")
        return httpx.Response(200, json={"id": PROVIDER_ID})

    async def create_source(self, email=False, **changes):
        body = {"request_id": str(uuid4()), "name": "Synthetic web form", "n8n_deployment_id": self.deployment["id"],
                "acknowledgement": "Thank you. Our team will follow up.", "followup_delay_minutes": 60,
                "confirm_activation": True, "email_mode": "email" if email else "none", **changes}
        if email:
            body.update(email_subject="Your inquiry was received", confirm_email_delivery=True)
        response = await self.owner.post("/inquiry-sources", json=body)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json(), body

    def event(self, **changes):
        return {"event_id": "fixture-event-1", "contact_reference": "fixture-contact-1", "inquiry": "General consultation availability question.",
                "contact_permission": True, **changes}

    async def intake(self, source, body=None, key=None):
        return await self.sender.post(source["intake_path"], json=body or self.event(),
            headers={"X-Inquiry-Key": source["webhook_key"] if key is None else key})

    async def settle(self):
        for _ in range(8):
            await self.app.state.execution.tick()

    def signed_event(self, kind="email.delivered", event_id="synthetic-svix-inquiry"):
        from app.models.workflow import now
        stamp = now()
        raw = json.dumps({"type": kind, "created_at": stamp.isoformat(), "data": {"email_id": PROVIDER_ID}}, separators=(",", ":")).encode()
        timestamp = str(int(stamp.timestamp()))
        signature = base64.b64encode(hmac.new(WEBHOOK_KEY, event_id.encode() + b"." + timestamp.encode() + b"." + raw, hashlib.sha256).digest()).decode()
        return raw, {"svix-id": event_id, "svix-timestamp": timestamp, "svix-signature": "v1," + signature}


class InquiryTests(InquiryFixture, unittest.IsolatedAsyncioTestCase):
    async def test_source_owner_auth_and_machine_key_are_separate(self):
        source, _ = await self.create_source()
        for path in ("/inquiry-sources", "/inquiries", "/outcomes/summary"):
            response = await self.sender.get(path)
            self.assertEqual(response.status_code, 401)
        response = await self.intake(source, key=TOKEN)
        self.assertEqual(response.status_code, 401)
        response = await self.intake(source)
        self.assertEqual(response.status_code, 202, response.text)
        self.assertEqual(response.json()["status"], "processed")
        self.assertNotIn("recipient_email", response.text)
        self.assertEqual(self.webhook_calls, 1)

    async def test_key_is_only_returned_on_create_and_rotation(self):
        source, body = await self.create_source()
        key = source["webhook_key"]
        raw = await self.store.get("inquiry_sources", source["source"]["id"])
        self.assertNotIn(key, json.dumps(raw))
        self.assertEqual(len(raw["key_hash"]), 64)
        listed = (await self.owner.get("/inquiry-sources")).text
        self.assertNotIn(key, listed); self.assertNotIn("key_hash", listed)
        replay = (await self.owner.post("/inquiry-sources", json=body)).json()
        self.assertIsNone(replay["webhook_key"])
        rotated = (await self.owner.post("/inquiry-sources/" + source["source"]["id"] + "/rotate-key", json={"confirm_rotation": True})).json()
        self.assertNotEqual(rotated["webhook_key"], key)
        self.assertEqual((await self.intake(source)).status_code, 401)
        self.assertEqual((await self.intake(rotated)).status_code, 202)

    async def test_duplicate_and_changed_event_ids_do_not_reexecute(self):
        source, _ = await self.create_source()
        first = await self.intake(source)
        repeated = await self.intake(source)
        self.assertEqual(first.json(), repeated.json())
        conflict = await self.intake(source, self.event(inquiry="Different question"))
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(self.webhook_calls, 1)
        self.assertEqual(len(await self.store.list("inquiries")), 1)
        self.assertEqual(len(await self.store.list("tasks")), 1)

    async def test_permission_optout_and_stale_analysis_stop_before_native(self):
        source, _ = await self.create_source()
        for value in (False, "true", 1):
            self.assertEqual((await self.intake(source, self.event(contact_permission=value))).status_code, 422)
        async with self.app.state.execution.lock:
            await self.app.state.execution.delivery.opt_out(self.bid, "fixture-contact-1")
        self.assertEqual((await self.intake(source)).status_code, 409)
        await self.owner.post(f"/businesses/{self.bid}/analyze", json={})
        self.assertEqual((await self.intake(source, self.event(contact_reference="different-contact"))).status_code, 409)
        self.assertEqual(self.webhook_calls, 0)
        self.assertEqual(await self.store.list("inquiries"), [])

    async def test_no_task_or_email_without_saved_native_proof(self):
        source, _ = await self.create_source(email=True)
        self.fail_native = True
        response = await self.intake(source, self.event(recipient_email="customer@example.com"))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json()["status"], "uncertain")
        self.assertEqual(await self.store.list("tasks"), [])
        self.assertEqual(await self.store.list("workflow_runs"), [])
        retry = await self.owner.post("/inquiries/" + response.json()["inquiry_id"] + "/retry", json={"confirm_retry": True})
        self.assertEqual(retry.status_code, 409); self.assertEqual(self.webhook_calls, 1)

    async def test_pause_blocks_intake_and_cancels_queued_email(self):
        source, _ = await self.create_source(email=True)
        response = await self.intake(source, self.event(recipient_email="customer@example.com"))
        self.assertEqual(response.json()["status"], "processed")
        pause = await self.owner.post("/inquiry-sources/" + source["source"]["id"] + "/pause", json={"confirm_pause": True})
        self.assertEqual(pause.status_code, 200)
        self.assertEqual((await self.intake(source, self.event(event_id="another-event"))).status_code, 409)
        await self.settle()
        self.assertEqual(self.email_calls, 0)
        self.assertEqual((await self.service.get(response.json()["inquiry_id"]))["email_status"], "cancelled")

    async def test_native_pause_after_enqueue_blocks_email_runner(self):
        source, _ = await self.create_source(email=True)
        await self.intake(source, self.event(recipient_email="customer@example.com"))
        await self.app.state.n8n.pause(self.deployment["id"])
        await self.settle()
        self.assertEqual(self.email_calls, 0)
        self.assertEqual((await self.service.list())[0]["email_status"], "skipped")

    async def test_bounded_payload_strict_fields_and_auth_attempts(self):
        source, _ = await self.create_source()
        big = await self.sender.post(source["intake_path"], content=b" " * 8193,
            headers={"X-Inquiry-Key": source["webhook_key"], "Content-Type": "application/json"})
        self.assertEqual(big.status_code, 413)
        self.assertEqual((await self.intake(source, self.event(business_id=self.bid))).status_code, 422)
        for _ in range(28):
            self.assertEqual((await self.intake(source, key="bad")).status_code, 401)
        self.assertEqual((await self.intake(source, key="bad")).status_code, 429)
        self.assertEqual(self.webhook_calls, 0)

    async def test_email_source_configuration_and_mock_guards(self):
        demo = await self.app.state.n8n.demo_workflow()
        deployment = await self.app.state.n8n.deploy(DeployRequest(request_id=uuid4(), workflow_id=demo["workflow"]["id"], confirm_deployment=True))
        body = {"request_id": str(uuid4()), "name": "Fictional source", "n8n_deployment_id": deployment["id"],
                "acknowledgement": "Fictional acknowledgement", "confirm_activation": True, "email_mode": "email",
                "email_subject": "Fictional subject", "confirm_email_delivery": True}
        self.assertEqual((await self.owner.post("/inquiry-sources", json=body)).status_code, 409)
        body["email_mode"] = "none"; body.pop("email_subject"); body["confirm_email_delivery"] = False
        self.assertEqual((await self.owner.post("/inquiry-sources", json=body)).status_code, 201)
        self.assertEqual((await self.owner.get("/inquiry-sources")).json(), [])
        self.assertEqual(len((await self.owner.get("/inquiry-sources?include_demo=true")).json()), 1)

    async def test_restart_preserves_native_uncertainty_without_replay(self):
        source, _ = await self.create_source()
        self.fail_native = True
        response = await self.intake(source)
        inquiry = await self.store.get("inquiries", response.json()["inquiry_id"])
        inquiry["status"] = "processing"
        await self.store.put("inquiries", inquiry["id"], inquiry)
        native_id = str(uuid5(NAMESPACE_URL, "n8n-run:" + inquiry["id"]))
        native = await self.store.get("n8n_runs", native_id)
        native["status"] = "processing"
        await self.store.put("n8n_runs", native_id, native)
        await self.app.state.n8n.recover(); await self.service.recover()
        self.assertEqual((await self.service.get(inquiry["id"]))["status"], "uncertain")
        self.assertEqual(self.webhook_calls, 1)

    async def test_email_timeout_retry_and_restart_never_resubmit(self):
        source, _ = await self.create_source(email=True)
        self.fail_email = True
        response = await self.intake(source, self.event(recipient_email="customer@example.com"))
        await self.settle()
        inquiry_id = response.json()["inquiry_id"]
        self.assertEqual((await self.service.get(inquiry_id))["email_status"], "submission_uncertain")
        await self.owner.post("/inquiries/" + inquiry_id + "/retry", json={"confirm_retry": True})
        await self.service.recover(); await self.settle()
        self.assertEqual(self.email_calls, 1)

    async def test_recovery_after_native_task_commit_keeps_original_task_and_execution(self):
        source, _ = await self.create_source()
        response = await self.intake(source)
        inquiry = await self.store.get("inquiries", response.json()["inquiry_id"])
        original_task = inquiry["task_id"]
        inquiry.update(status="processing", task_id=None, processed_at=None, execution_id=None)
        await self.store.put("inquiries", inquiry["id"], inquiry)
        await self.service.recover()
        restored = await self.service.get(inquiry["id"])
        self.assertEqual(restored["status"], "processed")
        self.assertEqual(restored["task_id"], original_task)
        self.assertEqual(self.webhook_calls, 1)
        self.assertEqual(len(await self.store.list("tasks")), 1)

    async def test_recovery_after_native_proof_before_email_reservation_uses_stable_keys(self):
        source, _ = await self.create_source(email=True)
        with patch.object(self.app.state.execution, "enqueue", side_effect=AppError(503, "storage_unavailable", "Synthetic storage failure")):
            response = await self.intake(source, self.event(recipient_email="customer@example.com"))
        inquiry = await self.service.get(response.json()["inquiry_id"])
        self.assertEqual(inquiry["status"], "processed")
        self.assertEqual(inquiry["email_status"], "not_enqueued")
        await self.service.recover()
        await self.settle()
        recovered = await self.service.get(inquiry["id"])
        self.assertEqual(recovered["email_run_id"], inquiry["email_run_id"])
        self.assertEqual(recovered["email_status"], "submitted")
        self.assertEqual(self.webhook_calls, 1); self.assertEqual(self.email_calls, 1)

    async def test_recipient_optout_during_native_network_blocks_task_and_email(self):
        source, _ = await self.create_source(email=True)
        async def optout_during_network(request):
            response = self.n8n_provider(request)
            if request.url.path.startswith("/webhook/"):
                async with self.app.state.execution.lock:
                    await self.app.state.execution.delivery.opt_out(self.bid, "older-contact-ref", recipient="CUSTOMER@example.com")
            return response
        self.app.state.n8n.transport = httpx.MockTransport(optout_during_network)
        response = await self.intake(source, self.event(recipient_email="customer@example.com"))
        self.assertEqual(response.json()["status"], "blocked")
        self.assertEqual(await self.store.list("tasks"), [])
        self.assertEqual(await self.store.list("workflow_runs"), [])
        self.assertEqual(self.email_calls, 0)

    async def test_changed_sender_after_enqueue_needs_source_review_and_sends_nothing(self):
        source, _ = await self.create_source(email=True)
        await self.intake(source, self.event(recipient_email="customer@example.com"))
        self.app.state.gateway.settings = replace(self.settings, resend_from_email="changed@example.com")
        await self.settle()
        self.assertEqual(self.email_calls, 0)
        self.assertEqual((await self.service.list())[0]["email_status"], "skipped")

    async def test_missing_callback_key_rejects_source_before_reserving_it(self):
        self.app.state.gateway.settings = replace(self.settings, resend_webhook_secret="")
        body = {"request_id": str(uuid4()), "name": "Missing email callback", "n8n_deployment_id": self.deployment["id"],
                "acknowledgement": "Thank you.", "confirm_activation": True, "email_mode": "email",
                "email_subject": "Received", "confirm_email_delivery": True}
        response = await self.owner.post("/inquiry-sources", json=body)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(await self.store.list("inquiry_sources"), [])
        self.assertEqual(self.email_calls, 0)

    async def test_source_confirmation_and_idempotency_conflicts_preserve_reviewed_settings(self):
        source, body = await self.create_source()
        for value in (False, 1, "true"):
            response = await self.owner.post("/inquiry-sources", json={**body, "request_id": str(uuid4()), "confirm_activation": value})
            self.assertEqual(response.status_code, 422)
        conflict = await self.owner.post("/inquiry-sources", json={**body, "acknowledgement": "Different response"})
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(len(await self.store.list("inquiry_sources")), 1)
        injected = await self.intake(source, self.event(acknowledgement="Unreviewed customer message"))
        self.assertEqual(injected.status_code, 422)
        self.assertEqual(self.webhook_calls, 0)

    async def test_pause_during_native_http_persists_before_task_or_email_commit(self):
        source, _ = await self.create_source(email=True)
        entered, release = asyncio.Event(), asyncio.Event()
        async def delayed_native(request):
            response = self.n8n_provider(request)
            if request.url.path.startswith("/webhook/"):
                entered.set()
                await release.wait()
            return response
        self.app.state.n8n.transport = httpx.MockTransport(delayed_native)
        pending = asyncio.create_task(self.intake(source, self.event(recipient_email="customer@example.com")))
        try:
            await asyncio.wait_for(entered.wait(), 2)
            pause = await asyncio.wait_for(self.owner.post("/inquiry-sources/" + source["source"]["id"] + "/pause",
                json={"confirm_pause": True}), 2)
            self.assertEqual(pause.status_code, 200)
            self.assertFalse(pending.done())
        finally:
            release.set()
        response = await pending
        self.assertEqual(response.json()["status"], "blocked")
        self.assertEqual(await self.store.list("tasks"), [])
        self.assertEqual(await self.store.list("workflow_runs"), [])
        self.assertEqual(self.email_calls, 0)

    async def test_rotation_while_request_body_streams_rejects_old_authenticated_key(self):
        source, _ = await self.create_source()
        streaming, resume = asyncio.Event(), asyncio.Event()
        raw = json.dumps(self.event()).encode()
        async def body_stream():
            yield raw[:1]
            streaming.set()
            await resume.wait()
            yield raw[1:]
        pending = asyncio.create_task(self.sender.post(source["intake_path"], content=body_stream(),
            headers={"X-Inquiry-Key": source["webhook_key"], "Content-Type": "application/json"}))
        try:
            await asyncio.wait_for(streaming.wait(), 2)
            rotation = await self.owner.post("/inquiry-sources/" + source["source"]["id"] + "/rotate-key",
                json={"confirm_rotation": True})
            self.assertEqual(rotation.status_code, 200)
        finally:
            resume.set()
        response = await pending
        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(await self.store.list("inquiries"), [])
        self.assertEqual(self.webhook_calls, 0)
