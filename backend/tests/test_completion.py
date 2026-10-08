"""Isolated shared-workspace MVP checks. Never contacts a provider or real business."""
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
from urllib.parse import parse_qs, urlencode
from unittest.mock import patch

import httpx

from app.database.store import SQLiteStore, SupabaseStore
from app.errors import AppError
from app.main import create_app
from app.models.workflow import now
from app.services.gateway import Gateway
from app.settings import Settings

TOKEN = 'synthetic-completion-token-not-a-real-secret'
ACCOUNT = 'AC' + '1' * 32
CALL_SID = 'CA' + '2' * 32
EMAIL_SID = '8eac3d2f-66bb-4f02-820a-2c77c82c789c'


class CompletionFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.requests = []
        self.response_code = 200
        self.provider_response = {'sid': CALL_SID}
        self.settings = Settings(database_path=str(Path(self.temp.name) / 'fixture.sqlite3'),
            app_api_token=TOKEN, app_public_url='https://app.example.com', enable_outbound_calls=True,
            twilio_account_sid=ACCOUNT, twilio_auth_token='synthetic-signature-key',
            twilio_from_number='+12025550101', sales_agent_number='+12025550102',
            enable_email_delivery=True, resend_api_key='synthetic-resend-key', resend_from_email='sender@example.com',
            resend_webhook_secret='whsec_' + base64.b64encode(b'synthetic-hook-secret').decode())
        def provider(request):
            self.requests.append(request)
            return httpx.Response(self.response_code, json=self.provider_response)
        self.gateway = Gateway(self.settings, httpx.MockTransport(provider))
        self.app = create_app(self.settings, gateway=self.gateway)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url='http://testserver',
            headers={'Authorization': 'Bearer ' + TOKEN})
        self.addAsyncCleanup(self.client.aclose)
        self.business = (await self.client.post('/businesses', json={
            'name': 'Synthetic completion fixture', 'address': 'Fictional test address',
            'phone': '+12025550103', 'website': None, 'rating': None, 'review_count': None})).json()
        self.bid = self.business['id']
        self.analysis = (await self.client.post(f'/businesses/{self.bid}/analyze', json={'evidence':[
            {'criterion':'appointment_reminders','assessment':'strong','source':'business_confirmation',
             'detail':'Synthetic fixture only; no real business was consulted.'}]})).json()
        self.workflow = (await self.client.post('/workflows', json={'analysis_id':self.analysis['id']})).json()
        self.profile = {'business_id':self.bid, 'idempotency_key':'synthetic-client', 'contact_name':'Synthetic operator',
            'contact_email':'operator@example.com', 'timezone':'Asia/Karachi',
            'approval_reference':'Fictional test authorization only.', 'confirm_business_authorization':True}
        self.run = {'mode':'sandbox','confirm_sandbox':True,'idempotency_key':'synthetic-proof',
            'event':{'contact_id':'synthetic-contact','contact_permission':True},
            'message_body':'Synthetic reminder preview only.', 'scheduled_at':(now()-timedelta(seconds=1)).isoformat()}

    async def settle(self, app=None):
        for _ in range(8):
            await (app or self.app).state.execution.tick()

    async def profile_and_deployment(self, channel='sandbox', proof=True):
        response = await self.client.post('/clients', json=self.profile)
        self.assertEqual(response.status_code,201,response.text)
        client = response.json()
        response = await self.client.post('/clients/'+client['id']+'/activate',json={'confirm_authorization':True})
        self.assertEqual(response.status_code,200,response.text)
        deployment = (await self.client.post('/clients/'+client['id']+'/deployments',json={
            'idempotency_key':'synthetic-deployment','workflow_id':self.workflow['id'],'channel':channel})).json()
        if proof:
            response = await self.client.post('/workflows/'+self.workflow['id']+'/runs',json=self.run)
            self.assertEqual(response.status_code,202,response.text)
            await self.settle()
        return client, deployment

    async def activate(self, deployment):
        response = await self.client.post('/deployments/'+deployment['id']+'/validate')
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['status'],'validated',response.text)
        response = await self.client.post('/deployments/'+deployment['id']+'/activate',json={'confirm_activation':True})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def call(self, key='synthetic-call'):
        response=await self.client.post(f'/businesses/{self.bid}/calls',json={
            'idempotency_key':key,'confirm_outbound_call':True})
        self.assertEqual(response.status_code,202,response.text)
        return response.json()

    def callback(self, call, status='completed', sequence='0', **changes):
        fields={'AccountSid':ACCOUNT,'CallSid':CALL_SID,'CallStatus':status,'SequenceNumber':sequence,
                'To':self.settings.sales_agent_number,'From':self.settings.twilio_from_number,**changes}
        url=self.settings.app_public_url+'/webhooks/twilio/calls/'+call['id']
        signed=url+''.join(key+fields[key] for key in sorted(fields))
        signature=base64.b64encode(hmac.new(self.settings.twilio_auth_token.encode(),signed.encode(),hashlib.sha1).digest()).decode()
        return urlencode(fields),{'Content-Type':'application/x-www-form-urlencoded','X-Twilio-Signature':signature}


class CRMTests(CompletionFixture):
    async def test_stage_history_is_durable_and_identical_patch_is_noop(self):
        body={'stage':'interested','notes':'Synthetic conversation.'}
        await self.client.patch(f'/businesses/{self.bid}/contact',json=body)
        await self.client.patch(f'/businesses/{self.bid}/contact',json=body)
        body={'stage':'won','notes':'Synthetic approval.'}
        await self.client.patch(f'/businesses/{self.bid}/contact',json=body)
        timeline=(await self.client.get(f'/businesses/{self.bid}/activities')).json()
        self.assertEqual(len(timeline),2)
        self.assertEqual(timeline[0]['previous_stage'],'interested')
        restarted=create_app(self.settings,gateway=self.gateway)
        self.assertEqual(len(await restarted.state.crm.timeline(self.bid)),2)
        self.assertEqual((await self.client.get(f'/businesses/{self.bid}/qualification')).json()['need_status'],'confirmed_gap')

    async def test_manual_activity_dedupes_and_does_not_create_need_evidence(self):
        analysis_before=await self.app.state.store.list('analyses')
        body={'idempotency_key':'synthetic-note','kind':'meeting','direction':'outgoing',
              'notes':'Synthetic activity only.','occurred_at':now().isoformat()}
        responses=await asyncio.gather(*(self.client.post(f'/businesses/{self.bid}/activities',json=body) for _ in range(6)))
        self.assertEqual({r.status_code for r in responses},{201})
        self.assertEqual(len({r.json()['id'] for r in responses}),1)
        changed={**body,'notes':'Changed content.'}
        self.assertEqual((await self.client.post(f'/businesses/{self.bid}/activities',json=changed)).status_code,409)
        future={**body,'idempotency_key':'synthetic-future','occurred_at':(now()+timedelta(days=1)).isoformat()}
        self.assertEqual((await self.client.post(f'/businesses/{self.bid}/activities',json=future)).status_code,422)
        self.assertEqual(await self.app.state.store.list('analyses'),analysis_before)

    async def test_tasks_dedupe_filter_overdue_and_finish_once(self):
        body={'idempotency_key':'synthetic-task','title':'Review fictional lead','due_at':(now()-timedelta(hours=1)).isoformat()}
        responses=await asyncio.gather(*(self.client.post(f'/businesses/{self.bid}/tasks',json=body) for _ in range(6)))
        self.assertEqual({r.status_code for r in responses},{201})
        task=responses[0].json()
        self.assertEqual(len({r.json()['id'] for r in responses}),1)
        self.assertEqual(len((await self.client.get('/tasks?overdue=true')).json()),1)
        self.assertEqual((await self.client.post(f'/businesses/{self.bid}/tasks',json={**body,'title':'Other title'})).status_code,409)
        for _ in range(2):
            self.assertEqual((await self.client.patch('/tasks/'+task['id'],json={'status':'completed'})).status_code,200)
        self.assertEqual((await self.client.patch('/tasks/'+task['id'],json={'status':'cancelled'})).status_code,409)
        self.assertEqual((await self.client.get('/tasks?overdue=true')).json(),[])
        timeline=(await self.client.get(f'/businesses/{self.bid}/activities')).json()
        self.assertEqual(len(timeline),2)

    async def test_optout_blocks_new_tasks_but_preserves_history(self):
        await self.client.patch(f'/businesses/{self.bid}/contact',json={'stage':'do_not_contact','notes':'Synthetic opt-out.'})
        response=await self.client.post(f'/businesses/{self.bid}/tasks',json={
            'idempotency_key':'blocked','title':'Follow up','due_at':now().isoformat()})
        self.assertEqual(response.status_code,409)
        self.assertEqual(len((await self.client.get(f'/businesses/{self.bid}/activities')).json()),1)

    async def test_contact_and_audit_write_rolls_back_together(self):
        store=self.app.state.store
        initial={'business_id':self.bid,'stage':'new','notes':'','updated_at':now().isoformat()}
        await store.put('contacts',self.bid,initial)
        with self.assertRaises(AppError):
            await store.put_many([('contacts',self.bid,{**initial,'stage':'won'}),('activities',None,{'invalid':'second write'})])
        self.assertEqual(await store.get('contacts',self.bid),initial)
        self.assertEqual(await store.list('activities'),[])


class DialerOutcomeTests(CompletionFixture):
    async def test_call_submission_registers_callback_and_terminal_replay_does_not_dial(self):
        call=await self.call()
        data=parse_qs(self.requests[0].content.decode())
        self.assertEqual(data['StatusCallback'],[self.settings.app_public_url+'/webhooks/twilio/calls/'+call['id']])
        raw,headers=self.callback(call)
        headers['Authorization']='Bearer intentionally-wrong'
        response=await self.client.post('/webhooks/twilio/calls/'+call['id'],content=raw,headers=headers)
        self.assertEqual(response.status_code,204,response.text)
        self.assertEqual((await self.call())['status'],'finished')
        self.assertEqual((await self.call())['outcome_leg'],'sales_agent')
        self.assertEqual(len(self.requests),1)

    async def test_signature_exact_url_fields_and_account_are_required(self):
        call=await self.call()
        raw,headers=self.callback(call)
        for candidate,modified in ((raw,{**headers,'X-Twilio-Signature':'invalid'}),(raw+'&To=other',headers)):
            response=await self.client.post('/webhooks/twilio/calls/'+call['id'],content=candidate,headers=modified)
            self.assertIn(response.status_code,{401,422})
        for changes in ({'AccountSid':'AC'+'9'*32},{'To':'+12025550999'},{'CallSid':'CA'+'8'*32}):
            raw,headers=self.callback(call,**changes)
            response=await self.client.post('/webhooks/twilio/calls/'+call['id'],content=raw,headers=headers)
            self.assertIn(response.status_code,{409,422})
        self.assertEqual(await self.app.state.store.list('call_events'),[])
        self.assertEqual((await self.client.get('/calls/'+call['id'])).json()['status'],'submitted')

    async def test_duplicate_and_out_of_order_callbacks_do_not_roll_back_terminal_status(self):
        call=await self.call()
        raw,headers=self.callback(call,sequence='3')
        for _ in range(2):
            self.assertEqual((await self.client.post('/webhooks/twilio/calls/'+call['id'],content=raw,headers=headers)).status_code,204)
        raw,headers=self.callback(call,status='ringing',sequence='1')
        self.assertEqual((await self.client.post('/webhooks/twilio/calls/'+call['id'],content=raw,headers=headers)).status_code,204)
        self.assertEqual((await self.client.get('/calls/'+call['id'])).json()['provider_status'],'completed')
        self.assertEqual(len(await self.app.state.store.list('call_events')),2)
        raw,headers=self.callback(call,status='failed',sequence='3')
        self.assertEqual((await self.client.post('/webhooks/twilio/calls/'+call['id'],content=raw,headers=headers)).status_code,409)

    async def test_uncertain_submission_can_reconcile_by_read_only_provider_match(self):
        self.response_code=500
        response=await self.client.post(f'/businesses/{self.bid}/calls',json={'idempotency_key':'synthetic-call','confirm_outbound_call':True})
        self.assertEqual(response.status_code,502)
        call=(await self.client.get('/calls')).json()[0]
        self.response_code=200
        self.provider_response={'sid':CALL_SID,'status':'completed','account_sid':ACCOUNT,
                                'to':self.settings.sales_agent_number,'from':self.settings.twilio_from_number}
        response=await self.client.post('/calls/'+call['id']+'/reconcile',json={
            'provider_call_id':CALL_SID,'confirm_provider_record':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['provider_status'],'completed')
        self.assertEqual(self.requests[-1].method,'GET')
        await self.call()
        self.assertEqual(len([r for r in self.requests if r.method=='POST']),1)

    async def test_provider_mismatch_cannot_reconcile_or_leak_response_diagnostics(self):
        call=await self.call()
        self.provider_response={'sid':CALL_SID,'status':'completed','account_sid':ACCOUNT,
            'to':'+12025550999','from':self.settings.twilio_from_number,'secret_diagnostic':'Never disclose this.'}
        response=await self.client.post('/calls/'+call['id']+'/reconcile',json={'provider_call_id':CALL_SID,'confirm_provider_record':True})
        self.assertEqual(response.status_code,409)
        self.assertNotIn('Never disclose',response.text)
        self.assertEqual((await self.client.get('/calls/'+call['id'])).json()['provider_status'],None)

    async def test_callback_and_confirmation_limits(self):
        call=await self.call()
        route='/webhooks/twilio/calls/'+call['id']
        self.assertEqual((await self.client.post(route,content=b'x'*16385,headers={'Content-Type':'application/x-www-form-urlencoded'})).status_code,413)
        self.assertEqual((await self.client.post(route,json={})).status_code,422)
        raw,headers=self.callback(call)
        self.assertEqual((await self.client.post(route+'?spoof=1',content=raw,headers=headers)).status_code,422)
        for value in (1,'true',False):
            response=await self.client.post(f'/businesses/{self.bid}/calls',json={'idempotency_key':'synthetic-other','confirm_outbound_call':value})
            self.assertEqual(response.status_code,422)
        self.gateway.settings=replace(self.settings,app_public_url='')
        self.assertEqual((await self.client.post(route,content=raw,headers=headers)).status_code,503)


class ClientDeliveryTests(CompletionFixture):
    async def test_onboarding_deduplication_timezone_and_explicit_authorization(self):
        responses=await asyncio.gather(*(self.client.post('/clients',json=self.profile) for _ in range(6)))
        self.assertEqual({r.status_code for r in responses},{201})
        client=responses[0].json()
        self.assertEqual(len({r.json()['id'] for r in responses}),1)
        self.assertEqual(client['status'],'onboarding')
        self.assertEqual((await self.client.post('/clients',json={**self.profile,'contact_name':'Different'})).status_code,409)
        self.assertEqual((await self.client.post('/clients',json={**self.profile,'idempotency_key':'other-key'})).status_code,409)
        for changes in ({'timezone':'Not/AZone'},{'confirm_business_authorization':1},{'confirm_business_authorization':False}):
            self.assertEqual((await self.client.post('/clients',json={**self.profile,**changes})).status_code,422)
        self.assertEqual((await self.client.post('/clients/'+client['id']+'/activate',json={'confirm_authorization':'true'})).status_code,422)

    async def test_preflight_and_activation_require_actual_sandbox_proof(self):
        client,deployment=await self.profile_and_deployment(proof=False)
        response=await self.client.post('/deployments/'+deployment['id']+'/validate')
        self.assertEqual(response.json()['status'],'draft')
        self.assertFalse(response.json()['validation']['ready'])
        self.assertEqual((await self.client.post('/deployments/'+deployment['id']+'/activate',json={'confirm_activation':True})).status_code,409)
        await self.client.post('/workflows/'+self.workflow['id']+'/runs',json=self.run)
        await self.settle()
        await self.activate(deployment)
        handoff=(await self.client.get('/clients/'+client['id']+'/handoff')).json()
        self.assertEqual(handoff['format'],'medspa-client-handoff-v1')
        self.assertFalse(handoff['credentials_included'])
        self.assertFalse(handoff['publicly_deployed'])
        self.assertNotIn(TOKEN,json.dumps(handoff))
        self.assertNotIn(self.settings.resend_api_key,json.dumps(handoff))

    async def test_activated_deployment_executes_and_keeps_keys_separate_from_direct_runs(self):
        client,deployment=await self.profile_and_deployment()
        await self.activate(deployment)
        responses=await asyncio.gather(*(self.client.post('/deployments/'+deployment['id']+'/runs',json=self.run) for _ in range(6)))
        self.assertEqual({r.status_code for r in responses},{202})
        run=responses[0].json()
        self.assertEqual(run['deployment_id'],deployment['id'])
        self.assertEqual(len({r.json()['id'] for r in responses}),1)
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-runs/'+run['id'])).json()['status'],'succeeded')
        self.assertEqual(len(await self.app.state.store.list('workflow_outbox')),2)
        self.assertEqual((await self.client.get('/deployments/'+deployment['id']+'/preflight')).json()['ready'],True)
        self.assertGreaterEqual(len((await self.client.get('/clients/'+client['id']+'/history')).json()),5)

    async def test_client_pause_stops_waiting_managed_run_before_message(self):
        client,deployment=await self.profile_and_deployment()
        await self.activate(deployment)
        waiting={**self.run,'idempotency_key':'future-managed','scheduled_at':(now()+timedelta(hours=1)).isoformat()}
        run=(await self.client.post('/deployments/'+deployment['id']+'/runs',json=waiting)).json()
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-runs/'+run['id'])).json()['status'],'waiting')
        await self.client.post('/clients/'+client['id']+'/pause')
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-runs/'+run['id'])).json()['status'],'skipped')
        self.assertEqual(len(await self.app.state.store.list('workflow_outbox')),1)
        self.assertEqual((await self.client.post('/deployments/'+deployment['id']+'/runs',json={**waiting,'idempotency_key':'new-after-pause'})).status_code,409)

    async def test_deployment_pause_archive_and_scope_guard(self):
        client,deployment=await self.profile_and_deployment()
        await self.activate(deployment)
        self.assertEqual((await self.client.post('/deployments/'+deployment['id']+'/runs',json={**self.run,'mode':'email','confirm_send':True,'recipient_email':'contact@example.com','subject':'Test'})).status_code,422)
        await self.client.post('/deployments/'+deployment['id']+'/pause')
        self.assertEqual((await self.client.post('/deployments/'+deployment['id']+'/runs',json=self.run)).status_code,409)
        await self.client.post('/deployments/'+deployment['id']+'/archive')
        self.assertEqual((await self.client.post('/deployments/'+deployment['id']+'/validate')).status_code,409)
        await self.client.post('/clients/'+client['id']+'/archive')
        self.assertEqual((await self.client.post('/clients/'+client['id']+'/activate',json={'confirm_authorization':True})).status_code,409)

    async def test_stale_analysis_and_changed_config_require_validation_again(self):
        client,deployment=await self.profile_and_deployment()
        response=await self.client.post('/deployments/'+deployment['id']+'/validate')
        self.assertEqual(response.json()['status'],'validated')
        await self.client.post(f'/businesses/{self.bid}/analyze',json={'evidence':self.analysis['evidence']})
        self.assertEqual((await self.client.post('/deployments/'+deployment['id']+'/activate',json={'confirm_activation':True})).status_code,409)
        self.assertFalse((await self.client.get('/deployments/'+deployment['id']+'/preflight')).json()['ready'])

    async def test_sender_change_after_validation_blocks_activation_and_pending_email(self):
        client,deployment=await self.profile_and_deployment(channel='email')
        await self.activate(deployment)
        body={key:value for key,value in self.run.items() if key not in {'mode','confirm_sandbox'}}
        body.update(mode='email',confirm_send=True,recipient_email='synthetic-recipient@example.com',
            subject='Synthetic reminder',idempotency_key='pending-email',scheduled_at=(now()+timedelta(hours=1)).isoformat())
        run=(await self.client.post('/deployments/'+deployment['id']+'/runs',json=body)).json()
        await self.settle()
        self.gateway.settings=replace(self.settings,resend_from_email='changed@example.com')
        await self.settle()
        saved=(await self.client.get('/workflow-runs/'+run['id'])).json()
        self.assertEqual(saved['status'],'skipped')
        self.assertEqual(saved['stop_reason'],'deployment_validation_stale')
        self.assertEqual(self.requests,[])
        await self.client.post('/deployments/'+deployment['id']+'/pause')
        self.assertEqual((await self.client.post('/deployments/'+deployment['id']+'/activate',json={'confirm_activation':True})).status_code,409)

    async def test_deployment_ids_and_modes_are_checked_before_any_provider_action(self):
        client,deployment=await self.profile_and_deployment()
        await self.activate(deployment)
        body={key:value for key,value in self.run.items() if key not in {'mode','confirm_sandbox'}}
        body.update(mode='email',confirm_send=True,recipient_email='synthetic-recipient@example.com',subject='Synthetic test')
        self.assertEqual((await self.client.post('/deployments/'+deployment['id']+'/runs',json=body)).status_code,409)
        self.assertEqual(self.requests,[])
        self.assertEqual((await self.client.get('/deployments?client_id='+client['id'])).json()[0]['id'],deployment['id'])

    async def test_managed_appointments_cancel_and_survive_restart(self):
        client,deployment=await self.profile_and_deployment()
        await self.activate(deployment)
        body={'workflow_id':self.workflow['id'],'starts_at':(now()+timedelta(hours=2)).isoformat(),
              'reminder':{**self.run,'idempotency_key':'managed-appointment','scheduled_at':(now()+timedelta(hours=1)).isoformat()}}
        response=await self.client.post('/deployments/'+deployment['id']+'/appointments',json=body)
        self.assertEqual(response.status_code,202,response.text)
        appointment=response.json()
        self.assertEqual(appointment['deployment_id'],deployment['id'])
        restarted=create_app(self.settings,gateway=self.gateway)
        await self.settle(restarted)
        run=await restarted.state.store.get('workflow_runs',appointment['run_id'])
        self.assertEqual(run['status'],'waiting')
        await restarted.state.appointments.cancel(appointment['id'])
        await self.settle(restarted)
        self.assertEqual((await self.client.get('/workflow-runs/'+run['id'])).json()['status'],'cancelled')
        self.assertEqual(len(await self.app.state.store.list('workflow_outbox')),1)

    async def test_email_activation_requires_callback_config_and_matching_business(self):
        client,deployment=await self.profile_and_deployment(channel='email')
        self.gateway.settings=replace(self.settings,resend_webhook_secret='',app_public_url='')
        response=await self.client.post('/deployments/'+deployment['id']+'/validate')
        self.assertFalse(response.json()['validation']['ready'])
        self.assertFalse(next(c['passed'] for c in response.json()['validation']['checks'] if c['code']=='callback_configured'))
        self.gateway.settings=self.settings
        await self.activate(deployment)
        other=(await self.client.post('/businesses',json={'name':'Other synthetic fixture','address':'Other fictional address',
            'website':None,'phone':None,'rating':None,'review_count':None})).json()
        other_profile={**self.profile,'business_id':other['id'],'idempotency_key':'other-client'}
        other_client=(await self.client.post('/clients',json=other_profile)).json()
        response=await self.client.post('/clients/'+other_client['id']+'/deployments',json={
            'workflow_id':self.workflow['id'],'channel':'sandbox','idempotency_key':'mismatch'})
        self.assertEqual(response.status_code,409)

    async def test_mock_client_email_is_blocked_and_demo_export_labeled(self):
        demo=(await self.client.post('/demo/reminder-workflow')).json()
        self.bid=demo['business']['id'];self.workflow=demo['workflow']
        self.profile={**self.profile,'business_id':self.bid}
        client,deployment=await self.profile_and_deployment(channel='email')
        response=await self.client.post('/deployments/'+deployment['id']+'/validate')
        self.assertEqual(response.json()['status'],'draft')
        self.assertFalse(next(c['passed'] for c in response.json()['validation']['checks'] if c['code']=='real_client'))
        self.assertTrue((await self.client.get('/clients/'+client['id']+'/handoff')).json()['client']['is_demo'])
        self.assertEqual(self.requests,[])

    async def test_email_managed_run_tracks_acceptance_without_claiming_delivery(self):
        client,deployment=await self.profile_and_deployment(channel='email')
        await self.activate(deployment)
        self.provider_response={'id':EMAIL_SID}
        body={key:value for key,value in self.run.items() if key not in {'mode','confirm_sandbox'}}
        body.update(mode='email',confirm_send=True,recipient_email='synthetic-recipient@example.com',subject='Synthetic reminder',idempotency_key='email-managed')
        response=await self.client.post('/deployments/'+deployment['id']+'/runs',json=body)
        self.assertEqual(response.status_code,202,response.text)
        await self.settle()
        run=(await self.client.get('/workflow-runs/'+response.json()['id'])).json()
        self.assertEqual(run['status'],'succeeded')
        self.assertEqual(run['delivery_status'],'submitted')
        self.assertFalse(run['sent'])
        self.assertEqual(len(self.requests),1)


class OperationsTests(CompletionFixture):
    async def test_new_sqlite_only_routes_fail_explicitly_without_breaking_supabase_research(self):
        settings=replace(self.settings,persistence_backend='supabase',supabase_url='https://fixture.supabase.co',supabase_key='synthetic-key')
        gateway=Gateway(settings,httpx.MockTransport(lambda request:httpx.Response(200,json=[])))
        app=create_app(settings,store=SupabaseStore(settings,gateway),gateway=gateway)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver',headers={'Authorization':'Bearer '+TOKEN}) as client:
            for route in ('/clients','/deployments','/tasks','/operations/summary'):
                self.assertEqual((await client.get(route)).status_code,503,route)
            self.assertEqual((await client.get('/businesses')).status_code,200)
            capabilities=(await client.get('/capabilities')).json()
            self.assertFalse(capabilities['crm_history_supported'])
            self.assertFalse(capabilities['client_workflow_activation_supported'])

    async def test_summary_reports_overdue_and_uncertain_work_without_secrets(self):
        await self.client.post(f'/businesses/{self.bid}/tasks',json={
            'idempotency_key':'overdue','title':'Synthetic follow-up','due_at':(now()-timedelta(hours=1)).isoformat()})
        self.response_code=500
        await self.client.post(f'/businesses/{self.bid}/calls',json={'idempotency_key':'uncertain-call','confirm_outbound_call':True})
        response=await self.client.get('/operations/summary?alert_limit=1')
        self.assertEqual(response.status_code,200,response.text)
        summary=response.json()
        self.assertEqual(summary['businesses'],1)
        self.assertEqual(summary['counts']['tasks'],{'pending':1})
        self.assertEqual(summary['alert_count'],2)
        self.assertTrue(summary['alerts_truncated'])
        self.assertEqual(len(summary['alerts']),1)
        for secret in (TOKEN,self.settings.twilio_auth_token,self.settings.resend_api_key):
            self.assertNotIn(secret,response.text)

    async def test_data_routes_require_shared_token_and_mock_counts_are_explicit(self):
        demo=(await self.client.post('/demo/reminder-workflow')).json()
        self.assertEqual((await self.client.get('/operations/summary')).json()['businesses'],1)
        self.assertEqual((await self.client.get('/operations/summary?include_demo=true')).json()['businesses'],2)
        for route in ('/operations/summary','/clients','/deployments','/tasks',f'/businesses/{self.bid}/activities','/calls/missing'):
            self.assertEqual((await self.client.get(route,headers={'Authorization':'Bearer wrong'})).status_code,401,route)
        self.assertEqual((await self.client.get('/clients?limit=0')).status_code,422)

    async def test_invalid_public_callback_origins_fail_before_serving(self):
        for url in ('http://app.example.com','https://localhost','https://127.0.0.1','https://app.example.com/path','https://user:pass@app.example.com','https://app.example.com?query=1'):
            with self.subTest(url=url),self.assertRaises(ValueError):
                create_app(replace(self.settings,app_public_url=url))


if __name__=='__main__':
    unittest.main()
