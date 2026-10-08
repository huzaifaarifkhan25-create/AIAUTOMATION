import asyncio
import base64
import hashlib
import hmac
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import httpx

from app.main import create_app
from app.models.workflow import now
from app.services.execution import Execution
from app.services.gateway import Gateway
from app.settings import Settings

PROVIDER_ID = "00000000-0000-4000-8000-000000000123"  # Synthetic provider fixture.
WEBHOOK_KEY = b"synthetic-webhook-test-key-only!!"


class DeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.time = now()
        self.requests = []
        self.provider_response = {"id": PROVIDER_ID}
        self.provider_status = 200
        self.settings = Settings(database_path=str(Path(self.temp.name) / "fixture.sqlite3"),
            app_api_token="synthetic-delivery-access-only", enable_email_delivery=True,
            resend_api_key="synthetic-resend-token-only", resend_from_email="sender@example.com",
            resend_webhook_secret="whsec_" + base64.b64encode(WEBHOOK_KEY).decode())
        def provider(request):
            self.requests.append(request)
            return httpx.Response(self.provider_status, json=self.provider_response)
        self.gateway = Gateway(self.settings, httpx.MockTransport(provider))
        self.app = create_app(self.settings, gateway=self.gateway)
        self.runner = Execution(self.app.state.store, self.app.state.platform, clock=lambda: self.time)
        self.app.state.execution = self.runner
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver",
            headers={"Authorization": "Bearer synthetic-delivery-access-only"})
        self.addAsyncCleanup(self.client.aclose)
        business = {"name": "Synthetic email fixture", "address": "Fixture address", "website": None,
                    "phone": None, "rating": None, "review_count": None}
        self.bid = (await self.client.post('/businesses', json=business)).json()["id"]
        analysis = (await self.client.post(f'/businesses/{self.bid}/analyze', json={"evidence": [
            {"criterion": "inquiry_followup", "assessment": "strong", "source": "business_confirmation", "detail": "Synthetic fixture only."}]})).json()
        self.workflow = (await self.client.post('/workflows', json={"analysis_id": analysis["id"]})).json()
        self.body = {"mode": "email", "confirm_send": True, "idempotency_key": "synthetic-email-event",
            "event": {"contact_id": "synthetic-contact", "contact_permission": True}, "recipient_email": "recipient@example.com",
            "subject": "Synthetic reminder", "message_body": "Synthetic reminder body only."}

    async def enqueue(self, body=None):
        response = await self.client.post(f'/workflows/{self.workflow["id"]}/runs', json=body or self.body)
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    async def settle(self, count=8):
        for _ in range(count):
            await self.runner.tick()

    async def read(self, run):
        return (await self.client.get('/workflow-runs/' + run['id'])).json()

    def signed(self, payload, event_id="synthetic-svix-event", timestamp=None, version="v1"):
        raw = json.dumps(payload, separators=(",", ":")).encode()
        timestamp = str(timestamp if timestamp is not None else int(self.time.timestamp()))
        signature = base64.b64encode(hmac.new(WEBHOOK_KEY, event_id.encode()+b'.'+timestamp.encode()+b'.'+raw, hashlib.sha256).digest()).decode()
        return raw, {"svix-id": event_id, "svix-timestamp": timestamp, "svix-signature": version+","+signature}

    def event(self, kind="email.delivered", provider_id=PROVIDER_ID):
        return {"type": kind, "created_at": self.time.isoformat(), "data": {"email_id": provider_id}}

    async def callback(self, kind="email.delivered", event_id="synthetic-svix-event"):
        raw, headers = self.signed(self.event(kind), event_id)
        response = await self.client.post('/webhooks/resend', content=raw, headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response

    async def test_email_request_is_guarded_and_submission_is_not_delivery(self):
        run = await self.enqueue()
        await self.settle()
        saved = await self.read(run)
        self.assertEqual(saved["result"], "email_submission_recorded")
        self.assertEqual(saved["delivery_status"], "submitted")
        self.assertFalse(saved["sent"])
        self.assertEqual(len(self.requests), 1)
        request = self.requests[0]
        self.assertEqual(str(request.url), "https://api.resend.com/emails")
        self.assertEqual(request.headers["Authorization"], "Bearer synthetic-resend-token-only")
        self.assertEqual(request.headers["Idempotency-Key"], saved["outbox_id"])
        self.assertEqual(json.loads(request.content), {"from": "sender@example.com", "to": ["recipient@example.com"],
            "subject": self.body["subject"], "text": self.body["message_body"]})
        await self.callback()
        self.assertEqual((await self.read(run))["delivery_status"], "delivered")
        self.assertTrue((await self.read(run))["sent"])
        self.assertTrue((await self.client.get('/workflow-outbox')).json()[0]["delivered"])

    async def test_disabled_missing_auth_and_bad_sender_fail_before_any_request(self):
        for overrides in ({"enable_email_delivery": False}, {"app_api_token": ""}, {"resend_api_key": ""}, {"resend_from_email": "invalid"}):
            self.gateway.settings = replace(self.settings, **overrides)
            response = await self.client.post(f'/workflows/{self.workflow["id"]}/runs', json=self.body)
            self.assertEqual(response.status_code, 503)
        self.assertEqual(self.requests, [])
        self.assertEqual(await self.app.state.store.list('workflow_runs'), [])

    async def test_mock_business_cannot_send_and_confirmation_is_literal_true(self):
        record = await self.app.state.store.get('businesses', self.bid)
        record['source'] = 'mock'
        await self.app.state.store.put('businesses', self.bid, record)
        response = await self.client.post(f'/workflows/{self.workflow["id"]}/runs', json=self.body)
        self.assertEqual(response.status_code, 409)
        for value in (False, 1, "true"):
            response = await self.client.post(f'/workflows/{self.workflow["id"]}/runs', json={**self.body, 'confirm_send': value})
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.requests, [])

    async def test_timeout_server_error_and_invalid_ids_stop_without_automatic_retry(self):
        for status, result in ((500, {"diagnostic": "Never expose provider details"}), (200, {"id": "invalid"}), (200, {})):
            self.provider_status, self.provider_response = status, result
            run = await self.enqueue({**self.body, 'idempotency_key': f'synthetic-{status}-{len(self.requests)}'})
            before = len(self.requests)
            await self.settle()
            self.assertEqual((await self.read(run))["status"], "failed")
            self.assertEqual((await self.read(run))["delivery_status"], "submission_uncertain")
            self.time += timedelta(hours=25)
            await self.settle()
            self.assertEqual(len(self.requests), before+1)
            self.assertNotIn("Never expose", str(await self.read(run)))

    async def test_explicit_provider_rejection_is_saved_without_resubmission(self):
        self.provider_status = 422
        self.provider_response = {"diagnostic": "Synthetic rejection details"}
        run = await self.enqueue()
        await self.settle()
        self.assertEqual((await self.read(run))["stop_reason"], "email_rejected")
        self.assertEqual((await self.read(run))["delivery_status"], "failed")
        self.assertEqual(len(self.requests), 1)
        self.assertEqual((await self.enqueue())["status"], "failed")
        self.assertEqual(len(self.requests), 1)

    async def test_network_timeout_is_uncertain_without_a_second_submission(self):
        attempts = 0
        def timeout(request):
            nonlocal attempts
            attempts += 1
            raise httpx.ReadTimeout('Synthetic response timeout', request=request)
        self.gateway.transport = httpx.MockTransport(timeout)
        run = await self.enqueue()
        await self.settle()
        self.assertEqual((await self.read(run))['delivery_status'], 'submission_uncertain')
        await self.enqueue()
        await self.settle()
        self.assertEqual(attempts, 1)

    async def test_crash_after_reservation_is_uncertain_and_never_replays_network_action(self):
        run = await self.enqueue()
        await self.settle(2)
        with patch.object(self.runner.delivery, 'submit', side_effect=asyncio.CancelledError()):
            with self.assertRaises(asyncio.CancelledError):
                await self.runner.tick()
        self.assertEqual((await self.client.get('/workflow-outbox')).json()[0]['status'], 'submission_started')
        recovered = Execution(self.app.state.store, self.app.state.platform, clock=lambda: self.time)
        self.runner = recovered
        self.app.state.execution = recovered
        await self.settle()
        self.assertEqual((await self.read(run))["delivery_status"], "submission_uncertain")
        self.assertEqual(self.requests, [])

    async def test_crash_after_provider_acceptance_can_be_reconciled_read_only(self):
        run = await self.enqueue()
        await self.settle(2)
        original = self.app.state.store.put
        async def crash(kind, record_id, payload):
            if kind == 'workflow_outbox' and payload['status'] == 'submitted':
                raise asyncio.CancelledError()
            return await original(kind, record_id, payload)
        with patch.object(self.app.state.store, 'put', side_effect=crash):
            with self.assertRaises(asyncio.CancelledError):
                await self.runner.tick()
        await self.settle()
        self.assertEqual(len(self.requests), 1)
        saved = await self.read(run)
        self.assertEqual(saved['delivery_status'], 'submission_uncertain')
        self.provider_response = {'id': PROVIDER_ID, 'to': [self.body['recipient_email']], 'from': self.settings.resend_from_email,
            'subject': self.body['subject'], 'last_event': 'delivered'}
        response = await self.client.post('/workflow-outbox/'+saved['outbox_id']+'/reconcile',
            json={'provider_email_id': PROVIDER_ID,'confirm_provider_record':True})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()['delivered'])
        self.assertEqual(self.requests[-1].method, 'GET')
        self.assertEqual(len([r for r in self.requests if r.method=='POST']),1)

    async def test_reconciliation_rejects_another_recipient(self):
        run = await self.enqueue()
        await self.settle()
        self.provider_response = {'id':PROVIDER_ID,'to':['different@example.com'],'from':self.settings.resend_from_email,
            'subject':self.body['subject'],'last_event':'delivered'}
        saved = await self.read(run)
        response = await self.client.post('/workflow-outbox/'+saved['outbox_id']+'/reconcile',
            json={'provider_email_id':PROVIDER_ID,'confirm_provider_record':True})
        self.assertEqual(response.status_code,409)
        self.assertEqual((await self.read(run))['delivery_status'],'submitted')

    async def test_callback_requires_signature_recent_timestamp_and_exact_raw_body(self):
        raw, headers = self.signed(self.event())
        for body, candidate in ((raw, {}),(raw+b' ',headers),(raw,{**headers,'svix-signature':'v2,'+headers['svix-signature'].split(',')[1]})):
            self.assertEqual((await self.client.post('/webhooks/resend',content=body,headers=candidate)).status_code,401)
        for difference in (-301,301):
            raw,headers=self.signed(self.event(),timestamp=int(self.time.timestamp())+difference)
            self.assertEqual((await self.client.post('/webhooks/resend',content=raw,headers=headers)).status_code,401)
        self.assertEqual(await self.app.state.store.list('delivery_events'),[])

    async def test_duplicate_callbacks_and_late_sent_events_cannot_roll_back_delivery(self):
        run=await self.enqueue()
        await self.settle()
        await self.callback()
        await self.callback()
        await self.callback('email.sent','synthetic-late-sent')
        self.assertEqual((await self.read(run))['delivery_status'],'delivered')
        self.assertEqual(len(await self.app.state.store.list('delivery_events')),2)
        raw, headers=self.signed(self.event('email.bounced'))
        self.assertEqual((await self.client.post('/webhooks/resend',content=raw,headers=headers)).status_code,409)

    async def test_early_callback_is_retained_until_the_provider_id_is_saved(self):
        await self.callback()
        self.assertEqual((await self.app.state.store.list('delivery_events'))[0]['status'],'received')
        run=await self.enqueue()
        await self.settle()
        self.assertEqual((await self.read(run))['delivery_status'],'delivered')
        self.assertEqual((await self.app.state.store.list('delivery_events'))[0]['status'],'applied')

    async def test_bounce_suppresses_future_events_despite_asserted_permission(self):
        run=await self.enqueue()
        await self.settle()
        await self.callback('email.bounced')
        await self.callback('email.delivered','synthetic-late-delivered')
        self.assertEqual((await self.read(run))['delivery_status'],'bounced')
        future=await self.enqueue({**self.body,'idempotency_key':'synthetic-after-bounce'})
        await self.settle()
        self.assertEqual((await self.read(future))['stop_reason'],'contact_opted_out')
        self.assertEqual(len(self.requests),1)

    async def test_manual_opt_out_and_false_permission_block_network_action(self):
        run=await self.enqueue({**self.body,'event':{**self.body['event'],'contact_permission':False}})
        await self.settle()
        self.assertEqual((await self.read(run))['status'],'skipped')
        await self.client.post(f'/businesses/{self.bid}/automation-contacts/synthetic-contact/opt-out')
        second=await self.enqueue({**self.body,'idempotency_key':'synthetic-opted-out'})
        await self.settle()
        self.assertEqual((await self.read(second))['stop_reason'],'contact_opted_out')
        self.assertEqual(self.requests,[])

    async def test_callback_body_limits_unknown_events_and_missing_config(self):
        self.assertEqual((await self.client.post('/webhooks/resend',content=b'x'*65537)).status_code,413)
        raw,headers=self.signed({'type':'email.opened','created_at':self.time.isoformat(),'data':{}})
        self.assertEqual((await self.client.post('/webhooks/resend',content=raw,headers=headers)).status_code,200)
        self.assertEqual((await self.app.state.store.list('delivery_events'))[0]['status'],'ignored')
        self.gateway.settings=replace(self.settings,resend_webhook_secret='')
        self.assertEqual((await self.client.post('/webhooks/resend',content=raw,headers=headers)).status_code,503)


if __name__=='__main__':
    unittest.main()
