"""Outcome counters follow recorded CRM and signed provider evidence."""
import unittest
from dataclasses import replace
from datetime import timedelta

from app.models.workflow import now
from app.models.n8n import DeployRequest
from uuid import uuid4
from test_inquiries import InquiryFixture


class OutcomeTests(InquiryFixture, unittest.IsolatedAsyncioTestCase):
    async def test_empty_metrics_have_no_invented_results(self):
        result = await self.service.summary()
        self.assertEqual(result["inquiries"]["received"], 0)
        self.assertEqual(result["email"]["delivered"], 0)
        self.assertIsNone(result["mean_task_creation_seconds"])
        self.assertNotIn("revenue", result)

    async def test_email_acceptance_does_not_count_as_delivery_then_signed_callback_does(self):
        source, _ = await self.create_source(email=True)
        await self.intake(source, self.event(recipient_email="customer@example.com"))
        await self.settle()
        result = await self.service.summary()
        self.assertEqual(result["inquiries"]["received"], 1)
        self.assertEqual(result["inquiries"]["processed"], 1)
        self.assertEqual(result["tasks"]["created"], 1)
        self.assertEqual(result["email"]["submitted"], 1)
        self.assertEqual(result["email"]["sent"], 0)
        self.assertEqual(result["email"]["delivered"], 0)
        raw, headers = self.signed_event()
        invalid = await self.sender.post("/webhooks/resend", content=raw, headers={**headers, "svix-signature": "v1,invalid"})
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual((await self.service.summary())["email"]["delivered"], 0)
        callback = await self.sender.post("/webhooks/resend", content=raw, headers=headers)
        self.assertEqual(callback.status_code, 200, callback.text)
        await self.sender.post("/webhooks/resend", content=raw, headers=headers)
        result = await self.service.summary()
        self.assertEqual(result["email"]["sent"], 1); self.assertEqual(result["email"]["delivered"], 1)
        self.assertEqual(len(await self.store.list("delivery_events")), 1)

    async def test_task_completion_and_overdue_use_saved_records(self):
        source, _ = await self.create_source()
        response = await self.intake(source)
        inquiry = await self.service.get(response.json()["inquiry_id"])
        task = await self.store.get("tasks", inquiry["task_id"])
        task["due_at"] = (now() - timedelta(minutes=1)).isoformat()
        await self.store.put("tasks", task["id"], task)
        self.assertEqual((await self.service.summary())["tasks"]["overdue"], 1)
        await self.app.state.crm.update_task(task["id"], "completed")
        summary = await self.service.summary()
        self.assertEqual(summary["tasks"]["completed"], 1)
        self.assertEqual(summary["tasks"]["overdue"], 0)

    async def test_rejected_and_uncertain_email_are_not_delivered(self):
        source, _ = await self.create_source(email=True)
        self.fail_email = True
        await self.intake(source, self.event(recipient_email="customer@example.com"))
        await self.settle()
        summary = await self.service.summary()
        self.assertEqual(summary["email"]["uncertain"], 1)
        self.assertEqual(summary["email"]["submitted"], 0)
        self.assertEqual(summary["email"]["delivered"], 0)

    async def test_bounce_after_delivered_revokes_delivered_and_suppresses_next_event(self):
        source, _ = await self.create_source(email=True)
        await self.intake(source, self.event(recipient_email="customer@example.com"))
        await self.settle()
        for kind in ("email.delivered", "email.bounced"):
            raw, headers = self.signed_event(kind, event_id="fixture-" + kind)
            self.assertEqual((await self.sender.post("/webhooks/resend", content=raw, headers=headers)).status_code, 200)
        summary = await self.service.summary()
        self.assertEqual(summary["email"]["submitted"], 1)
        self.assertEqual(summary["email"]["failed"], 1)
        self.assertEqual(summary["email"]["stopped"], 0)
        self.assertEqual(summary["email"]["delivered"], 0)
        response = await self.intake(source, self.event(event_id="second-event", contact_reference="changed-ref", recipient_email="CUSTOMER@example.com"))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.webhook_calls, 1); self.assertEqual(self.email_calls, 1)

    async def test_paused_and_safely_skipped_email_are_stopped_not_provider_failures(self):
        source, _ = await self.create_source(email=True)
        await self.intake(source, self.event(recipient_email="customer@example.com"))
        pause = await self.owner.post("/inquiry-sources/" + source["source"]["id"] + "/pause",
                                      json={"confirm_pause": True})
        self.assertEqual(pause.status_code, 200)
        await self.settle()
        summary = await self.service.summary()
        self.assertEqual(summary["email"]["stopped"], 1)
        self.assertEqual(summary["email"]["failed"], 0)

        second, _ = await self.create_source(email=True)
        await self.intake(second, self.event(event_id="second-inquiry", recipient_email="customer@example.com"))
        self.app.state.gateway.settings = replace(self.settings, resend_from_email="changed@example.com")
        await self.settle()
        summary = await self.service.summary()
        self.assertEqual(summary["email"]["stopped"], 2)
        self.assertEqual(summary["email"]["failed"], 0)
        self.assertEqual(summary["email"]["submitted"], 0)
        self.assertEqual(self.email_calls, 0)

    async def test_fictional_inquiry_results_are_excluded_by_default(self):
        demo = await self.app.state.n8n.demo_workflow()
        self.deployment = await self.app.state.n8n.deploy(DeployRequest(request_id=uuid4(), workflow_id=demo["workflow"]["id"], confirm_deployment=True))
        source, _ = await self.create_source()
        await self.intake(source)
        self.assertEqual((await self.service.summary())["inquiries"]["received"], 0)
        included = await self.service.summary(include_demo=True)
        self.assertEqual(included["inquiries"]["received"], 1)
        self.assertEqual(included["tasks"]["created"], 1)
        self.assertEqual(included["email"]["delivered"], 0)
