"""Simulated n8n contract checks. Real-engine evidence is recorded separately."""
import json
import copy
import asyncio
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import httpx

from app.errors import AppError
from app.main import create_app
from app.models.n8n import ConnectionRequest, DeployRequest, InquiryRequest
from app.models.workflow import AnalyzeRequest, ContactUpdate, now
from app.services.n8n_template import inquiry_template
from app.settings import Settings

TOKEN = "fixture-n8n-app-access-token"
KEY = "fixture-n8n-provider-api-key"


class N8NTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.app = create_app(Settings(database_path=str(Path(temp.name) / "test.sqlite3"), app_api_token=TOKEN))
        self.n8n = self.app.state.n8n
        self.requests, self.payload, self.webhook_calls = [], None, 0
        self.unregistered, self.mismatch, self.fail_execution = False, False, False
        self.remote_graph = None
        self.execution_graph = None
        self.n8n.transport = httpx.MockTransport(self.provider)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app, client=("127.0.0.1", 1234)), base_url="http://testserver", headers={"Authorization": "Bearer " + TOKEN})
        self.addAsyncCleanup(self.client.aclose)
        await self.n8n.connect(ConnectionRequest(base_url="http://127.0.0.1:5678", api_key=KEY))
        self.demo = await self.n8n.demo_workflow()

    def provider(self, request):
        self.requests.append(request)
        path = request.url.path
        if path == "/api/v1/workflows" and request.method == "GET":
            return httpx.Response(200, json={"data": []})
        if path == "/api/v1/credentials":
            return httpx.Response(200, json={"id": "credential-fixture"})
        if path == "/api/v1/workflows":
            self.remote_graph = json.loads(request.content)
            self.remote_graph.update(id="workflow-fixture", active=True)
            return httpx.Response(200, json={"id": "workflow-fixture"})
        if path == "/api/v1/workflows/workflow-fixture":
            return httpx.Response(200, json=self.remote_graph)
        if path.endswith("/activate"):
            return httpx.Response(200, json={"active": True})
        if path.endswith("/deactivate"):
            return httpx.Response(200, json={"active": False})
        if path.startswith("/webhook/"):
            self.webhook_calls += 1
            if self.unregistered and self.webhook_calls == 1:
                return httpx.Response(404, json={"code": 404, "message": "The requested webhook is not registered."})
            self.payload = json.loads(request.content)
            output = {k: v for k, v in self.payload.items() if k != "contact_permission"}
            output.update(execution_id="execution-fixture", delivery_status="unsent_draft")
            if self.mismatch:
                output["business_id"] = "wrong-business"
            return httpx.Response(200, json=output)
        if path.startswith("/api/v1/executions/"):
            output = {k: v for k, v in self.payload.items() if k != "contact_permission"}
            output.update(execution_id="execution-fixture", delivery_status="unsent_draft")
            return httpx.Response(200, json={"id": "execution-fixture", "workflowId": "workflow-fixture", "status": "error" if self.fail_execution else "success",
                "workflowData": self.execution_graph or self.remote_graph,
                "data": {"resultData": {"runData": {"Prepare follow-up": [{"data": {"main": [[{"json": output}]]}}]}}}})
        raise AssertionError("Unexpected n8n endpoint")

    async def deploy(self):
        return await self.n8n.deploy(DeployRequest(request_id=uuid4(), workflow_id=self.demo["workflow"]["id"], confirm_deployment=True))

    def inquiry(self, **changes):
        return InquiryRequest.model_validate({"request_id": str(uuid4()), "contact_reference": "Fictional customer", "inquiry": "Consultation question", "acknowledgement": "Thank you; our team will follow up.", "followup_at": (now() + timedelta(hours=1)).isoformat(), "contact_permission": True, "confirm_run": True, **changes})

    async def test_authenticated_routes_and_local_setup_boundary(self):
        for path in ("/n8n/status", "/n8n/template", "/n8n/runs", "/n8n/deployments"):
            response = await self.client.get(path, headers={"Authorization": "Bearer wrong-token"})
            self.assertEqual(response.status_code, 401)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app, client=("203.0.113.2", 1234)), base_url="http://testserver", headers=self.client.headers) as remote:
            response = await remote.post("/n8n/connection", json={"base_url": "http://127.0.0.1:5678", "api_key": KEY})
            self.assertEqual(response.status_code, 403)

    async def test_local_key_form_requires_real_session_and_csrf_even_with_bearer(self):
        body = {"base_url": "http://127.0.0.1:5678", "api_key": KEY}
        self.assertEqual((await self.client.post("/n8n/connection", json=body)).status_code, 403)
        signup = await self.client.post("/auth/register", json={"name": "Fictional Local Operator", "email": "n8n-operator@example.test",
            "password": "Fictional-long-account-password", "access_code": TOKEN, "confirm_shared_workspace": True})
        self.assertEqual(signup.status_code, 201, signup.text)
        self.assertTrue((await self.client.get("/n8n/status")).json()["local_connection_allowed"])
        self.assertEqual((await self.client.post("/n8n/connection", json=body)).status_code, 403)
        headers = {"X-Workspace-CSRF": signup.json()["csrf_token"]}
        self.assertEqual((await self.client.post("/n8n/connection", json=body, headers={**headers, "Origin": "https://other.example.test"})).status_code, 403)
        connected = await self.client.post("/n8n/connection", json=body, headers=headers)
        self.assertEqual(connected.status_code, 200, connected.text)
        self.assertTrue(connected.json()["configured"])
        self.assertNotIn(KEY, connected.text)

    async def test_native_export_contains_only_fixed_nodes_and_no_secrets(self):
        data = (await self.client.get("/n8n/template")).json()
        self.assertEqual([n["type"] for n in data["nodes"]], ["n8n-nodes-base.webhook", "n8n-nodes-base.set", "n8n-nodes-base.respondToWebhook"])
        self.assertNotIn(KEY, json.dumps(data)); self.assertEqual(data["nodes"][0]["parameters"]["authentication"], "headerAuth")

    async def test_real_task_requires_matching_successful_execution_and_repeats_safely(self):
        deployment = await self.deploy(); body = self.inquiry()
        result = await self.n8n.run(deployment["id"], body)
        repeated = await self.n8n.run(deployment["id"], body)
        self.assertEqual(result["status"], "succeeded"); self.assertEqual(result["delivery_status"], "unsent_draft")
        self.assertEqual(result["task_id"], repeated["task_id"])
        self.assertEqual(len(await self.app.state.store.list("tasks")), 1); self.assertEqual(self.webhook_calls, 1)
        self.assertTrue(any(r.url.path.startswith("/api/v1/executions/") for r in self.requests))
        hook = next(r for r in self.requests if r.url.path.startswith("/webhook/"))
        self.assertNotIn("X-N8N-API-KEY", hook.headers); self.assertIn("X-AIAutomation-Token", hook.headers)

    async def test_activation_registration_race_is_bounded_and_does_not_duplicate_task(self):
        self.unregistered = True
        result = await self.n8n.run((await self.deploy())["id"], self.inquiry())
        self.assertEqual(result["status"], "succeeded"); self.assertEqual(self.webhook_calls, 2)
        self.assertEqual(len(await self.app.state.store.list("tasks")), 1)

    async def test_paused_deployment_blocks_retry_of_verified_execution_before_task_commit(self):
        deployment = await self.deploy(); body = self.inquiry()
        original_task = self.app.state.crm.task
        async def fail_task(*args, **kwargs):
            raise AppError(503, "fixture_task_write_blocked", "Fixture transient task failure")
        self.app.state.crm.task = fail_task
        with self.assertRaises(AppError) as first:
            await self.n8n.run(deployment["id"], body)
        self.assertEqual(first.exception.code, "fixture_task_write_blocked")
        self.assertEqual((await self.n8n.runs())[0]["status"], "processed")
        self.app.state.crm.task = original_task
        await self.n8n.pause(deployment["id"])
        with self.assertRaises(AppError) as repeated:
            await self.n8n.run(deployment["id"], body)
        self.assertEqual(repeated.exception.code, "n8n_deployment_not_active")
        self.assertEqual(await self.app.state.store.list("tasks"), [])
        self.assertEqual(self.webhook_calls, 1)

    async def test_mismatched_output_and_failed_engine_never_create_task(self):
        for mismatch in (True, False):
            self.mismatch, self.fail_execution = mismatch, not mismatch
            with self.assertRaises(AppError):
                await self.n8n.run((await self.deploy())["id"], self.inquiry())
        self.assertEqual(await self.app.state.store.list("tasks"), [])
        self.assertTrue(all(r["status"] == "uncertain" for r in await self.n8n.runs()))

    async def test_missing_permission_confirmation_and_expired_time_stop_before_webhook(self):
        deployment = await self.deploy()
        for change in ({"contact_permission": False}, {"confirm_run": False}, {"followup_at": (now()-timedelta(minutes=1)).isoformat()}):
            with self.assertRaises(AppError):
                await self.n8n.run(deployment["id"], self.inquiry(**change))
        self.assertEqual(self.webhook_calls, 0)

    async def test_blocked_business_stops_runs_but_can_still_pause(self):
        deployment = await self.deploy()
        await self.app.state.crm.update_contact(deployment["business_id"], ContactUpdate(stage="do_not_contact", notes="Fixture opt-out"))
        with self.assertRaises(AppError):
            await self.n8n.run(deployment["id"], self.inquiry())
        paused = await self.n8n.pause(deployment["id"])
        self.assertEqual(paused["status"], "paused"); self.assertEqual(self.webhook_calls, 0)

    async def test_new_analysis_blocks_old_workflow_runs(self):
        deployment = await self.deploy()
        await self.app.state.platform.analyze(deployment["business_id"], AnalyzeRequest())
        with self.assertRaises(AppError):
            await self.n8n.run(deployment["id"], self.inquiry())
        self.assertEqual(self.webhook_calls, 0)
        self.assertEqual((await self.n8n.pause(deployment["id"]))["status"], "paused")

    async def test_public_friction_alone_cannot_authorize_native_inquiry_automation(self):
        analysis = await self.app.state.platform.analyze(self.demo["business"]["id"], AnalyzeRequest.model_validate({"evidence": [
            {"criterion": "inquiry_friction", "assessment": "strong", "source": "public_website", "detail": "Fictional observed public friction only"}]}))
        self.assertEqual(analysis.automation_type, "inquiry_followup")
        workflow = await self.app.state.platform.workflow(analysis.id)
        with self.assertRaises(AppError) as caught:
            await self.n8n.deploy(DeployRequest(request_id=uuid4(), workflow_id=workflow.id, confirm_deployment=True))
        self.assertEqual(caught.exception.code, "n8n_template_unsupported")
        self.assertFalse(any(r.method == "POST" for r in self.requests))

    async def test_analysis_changed_during_external_execution_blocks_task_commit(self):
        deployment = await self.deploy()
        async def change_after_webhook(request):
            response = self.provider(request)
            if request.url.path.startswith("/webhook/"):
                await self.app.state.platform.analyze(deployment["business_id"], AnalyzeRequest())
            return response
        self.n8n.transport = httpx.MockTransport(change_after_webhook)
        with self.assertRaises(AppError) as caught:
            await self.n8n.run(deployment["id"], self.inquiry())
        self.assertEqual(caught.exception.code, "analysis_outdated")
        self.assertEqual(await self.app.state.store.list("tasks"), [])
        run = (await self.n8n.runs())[0]
        self.assertEqual(run["status"], "processed"); self.assertIn("latest analysis", run["error"])

    async def test_customer_opt_out_before_and_during_webhook_prevents_followup_task(self):
        deployment = await self.deploy()
        await self.app.state.execution.delivery.opt_out(deployment["business_id"], "Already opted out")
        with self.assertRaises(AppError) as caught:
            await self.n8n.run(deployment["id"], self.inquiry(contact_reference="Already opted out"))
        self.assertEqual(caught.exception.code, "contact_opted_out")
        self.assertEqual(self.webhook_calls, 0)
        async def opt_out_after_webhook(request):
            response = self.provider(request)
            if request.url.path.startswith("/webhook/"):
                await self.app.state.execution.delivery.opt_out(deployment["business_id"], "Fictional customer")
            return response
        self.n8n.transport = httpx.MockTransport(opt_out_after_webhook)
        with self.assertRaises(AppError) as caught:
            await self.n8n.run(deployment["id"], self.inquiry())
        self.assertEqual(caught.exception.code, "contact_opted_out")
        self.assertEqual(self.webhook_calls, 1)
        self.assertEqual(await self.app.state.store.list("tasks"), [])
        self.assertEqual((await self.n8n.runs())[0]["status"], "processed")

    async def test_changed_connection_and_changed_request_inputs_are_rejected(self):
        deployment = await self.deploy(); body = self.inquiry()
        await self.n8n.run(deployment["id"], body)
        with self.assertRaises(AppError):
            await self.n8n.run(deployment["id"], body.model_copy(update={"inquiry": "Different inquiry"}))
        self.n8n._key = "different-fixture-provider-key"
        with self.assertRaises(AppError):
            await self.n8n.run(deployment["id"], self.inquiry())
        self.assertEqual(self.webhook_calls, 1)

    async def test_validation_does_not_echo_keys_and_origin_guards_apply(self):
        response = await self.client.post("/n8n/connection", json={"base_url": "http://127.0.0.1:5678", "api_key": KEY, "extra_secret": KEY})
        self.assertEqual(response.status_code, 422); self.assertNotIn(KEY, response.text)
        for origin in ("http://10.0.0.1", "https://user:password@example.test", "http://127.0.0.1:5678/path", "http://127.0.0.1:5678?key=test"):
            with self.assertRaises(AppError): await self.n8n.validate_origin(origin)

    async def test_recovery_marks_interrupted_external_work_uncertain_without_replay(self):
        await self.app.state.store.put("n8n_runs", "interrupted", {"id": "interrupted", "status": "processing"})
        await self.n8n.recover()
        self.assertEqual((await self.app.state.store.get("n8n_runs", "interrupted"))["status"], "uncertain")
        self.assertEqual(self.webhook_calls, 0)

    async def test_status_and_deployment_views_do_not_expose_credentials(self):
        deployment = await self.deploy()
        self.assertNotIn(KEY, json.dumps(self.n8n.status()))
        self.assertNotIn("webhook_path", deployment); self.assertNotIn("credential_id", deployment)
        self.assertNotIn("connection_id", deployment)

    async def test_edited_remote_graph_never_triggers_webhook_or_task(self):
        deployment = await self.deploy()
        original = copy.deepcopy(self.remote_graph)
        for mutation in ("extra_node", "expression", "disabled", "credential", "connection", "error_workflow", "malformed_node"):
            self.remote_graph = copy.deepcopy(original)
            if mutation == "extra_node":
                self.remote_graph["nodes"].append({"name": "Send email", "type": "n8n-nodes-base.emailSend"})
            elif mutation == "expression":
                self.remote_graph["nodes"][1]["parameters"]["assignments"]["assignments"][0]["value"] = "={{ $env.PRIVATE_VALUE }}"
            elif mutation == "disabled":
                self.remote_graph["nodes"][1]["disabled"] = True
            elif mutation == "credential":
                self.remote_graph["nodes"][0]["credentials"]["httpHeaderAuth"] = None
            elif mutation == "connection":
                self.remote_graph["connections"] = {}
            elif mutation == "error_workflow":
                self.remote_graph["settings"]["errorWorkflow"] = "unreviewed-extra-workflow"
            else:
                self.remote_graph["nodes"][1] = None
            with self.assertRaises(AppError) as caught:
                await self.n8n.run(deployment["id"], self.inquiry())
            self.assertEqual(caught.exception.code, "n8n_template_changed")
        self.assertEqual(self.webhook_calls, 0)
        self.assertEqual(await self.app.state.store.list("tasks"), [])
        self.assertEqual(await self.n8n.runs(), [])

    async def test_execution_snapshot_edit_blocks_task_and_stays_uncertain(self):
        deployment = await self.deploy()
        self.execution_graph = copy.deepcopy(self.remote_graph)
        self.execution_graph["nodes"].append({"name": "Send email", "type": "n8n-nodes-base.emailSend"})
        with self.assertRaises(AppError) as caught:
            await self.n8n.run(deployment["id"], self.inquiry())
        self.assertEqual(caught.exception.code, "n8n_run_uncertain")
        self.assertEqual(self.webhook_calls, 1)
        self.assertEqual(await self.app.state.store.list("tasks"), [])
        self.assertEqual((await self.n8n.runs())[0]["status"], "uncertain")
        self.assertNotIn("No customer message was sent", caught.exception.message)

    async def test_n8n_materialized_defaults_are_accepted_but_behavior_changes_are_not(self):
        deployment = await self.deploy()
        self.execution_graph = copy.deepcopy(self.remote_graph)
        defaults = [{"multipleMethods": False, "webhookNotice": ""},
                    {"mode": "manual", "duplicateItem": False, "includeOtherFields": False},
                    {"enableResponseOutput": False, "generalNotice": "", "webhookNotice": ""}]
        for node, values in zip(self.execution_graph["nodes"], defaults):
            node["parameters"].update(values)
        self.assertEqual((await self.n8n.run(deployment["id"], self.inquiry()))["status"], "succeeded")
        self.remote_graph = copy.deepcopy(self.execution_graph)
        self.remote_graph["nodes"][1]["parameters"]["duplicateItem"] = True
        with self.assertRaises(AppError) as caught:
            await self.n8n.run(deployment["id"], self.inquiry())
        self.assertEqual(caught.exception.code, "n8n_template_changed")
        self.assertEqual(self.webhook_calls, 1)

    async def test_remote_pause_blocks_inquiry_before_webhook(self):
        deployment = await self.deploy()
        self.remote_graph["active"] = False
        with self.assertRaises(AppError) as caught:
            await self.n8n.run(deployment["id"], self.inquiry())
        self.assertEqual(caught.exception.code, "n8n_remote_not_active")
        self.assertEqual(self.webhook_calls, 0)

    async def test_pause_completion_is_ordered_with_an_inflight_guarded_action(self):
        deployment = await self.deploy()
        deactivated = asyncio.Event()
        async def notify_deactivation(request):
            response = self.provider(request)
            if request.url.path.endswith("/deactivate"):
                deactivated.set()
            return response
        self.n8n.transport = httpx.MockTransport(notify_deactivation)
        async with self.app.state.execution.lock:
            pause = asyncio.create_task(self.n8n.pause(deployment["id"]))
            await asyncio.wait_for(deactivated.wait(), 2)
            self.assertFalse(pause.done())
        self.assertEqual((await asyncio.wait_for(pause, 2))["status"], "paused")


if __name__ == "__main__": unittest.main()
