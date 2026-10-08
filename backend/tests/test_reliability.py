"""Final pilot regressions with fictional data and simulated provider transports."""
import asyncio
import base64
import hashlib
import hmac
import json
from dataclasses import replace
from datetime import timedelta

import httpx

from app.main import create_app
from app.models.workflow import now
from app.services.delivery import permission_id
from test_completion import CompletionFixture, EMAIL_SID


class ReliabilityTests(CompletionFixture):
    def email(self, key, contact='original-contact', recipient='recipient@example.com'):
        return {**{k:v for k,v in self.run.items() if k not in {'mode','confirm_sandbox'}},
            'mode':'email','confirm_send':True,'idempotency_key':key,
            'event':{'contact_id':contact,'contact_permission':True},
            'recipient_email':recipient,'subject':'Fictional test reminder'}

    async def enqueue_email(self, body, client=None):
        response=await (client or self.client).post('/workflows/'+self.workflow['id']+'/runs',json=body)
        self.assertEqual(response.status_code,202,response.text)
        return response.json()

    async def test_manual_optout_blocks_known_email_after_contact_id_and_case_change(self):
        self.provider_response={'id':EMAIL_SID}
        original=await self.enqueue_email(self.email('original-email',recipient='Recipient@Example.com'))
        await self.client.post(f'/businesses/{self.bid}/automation-contacts/original-contact/opt-out')
        alias=await self.enqueue_email(self.email('alias-email',contact='new-import-id'))
        await self.settle()
        for run in (original,alias):
            saved=(await self.client.get('/workflow-runs/'+run['id'])).json()
            self.assertEqual(saved['stop_reason'],'contact_opted_out')
        self.assertEqual(self.requests,[])

    async def test_address_optout_survives_restart_without_blocking_another_address(self):
        self.provider_response={'id':EMAIL_SID}
        await self.enqueue_email(self.email('before-restart'))
        await self.client.post(f'/businesses/{self.bid}/automation-contacts/original-contact/opt-out')
        restarted=create_app(self.settings,gateway=self.gateway)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=restarted),base_url='http://testserver',headers=self.client.headers) as client:
            blocked=await self.enqueue_email(self.email('after-restart','alias-id'),client)
            allowed=await self.enqueue_email(self.email('different-address','other-id','different@example.com'),client)
            await self.settle(restarted)
            self.assertEqual((await client.get('/workflow-runs/'+blocked['id'])).json()['stop_reason'],'contact_opted_out')
            self.assertEqual((await client.get('/workflow-runs/'+allowed['id'])).json()['status'],'succeeded')
        self.assertEqual(len(self.requests),1)
        self.assertEqual(json.loads(self.requests[0].content)['to'],['different@example.com'])

    async def test_legacy_contact_only_optout_also_blocks_known_recipient_alias(self):
        self.provider_response={'id':EMAIL_SID}
        await self.enqueue_email(self.email('legacy-email'))
        await self.app.state.store.put('workflow_permissions',permission_id(self.bid,'original-contact'),
            {'business_id':self.bid,'contact_id':'original-contact','contact_permission':False,
             'reason':'legacy_opt_out','updated_at':now().isoformat()})
        alias=await self.enqueue_email(self.email('legacy-alias','alias-id'))
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-runs/'+alias['id'])).json()['stop_reason'],'contact_opted_out')
        self.assertEqual(self.requests,[])

    async def test_signed_bounce_blocks_recipient_with_another_contact_id(self):
        self.provider_response={'id':EMAIL_SID}
        await self.enqueue_email(self.email('first-submission'))
        await self.settle()
        payload={'type':'email.bounced','created_at':now().isoformat(),'data':{'email_id':EMAIL_SID}}
        raw=json.dumps(payload).encode(); stamp=str(int(now().timestamp())); event='fictional-bounce'
        signature=base64.b64encode(hmac.new(b'synthetic-hook-secret',event.encode()+b'.'+stamp.encode()+b'.'+raw,hashlib.sha256).digest()).decode()
        response=await self.client.post('/webhooks/resend',content=raw,headers={
            'svix-id':event,'svix-timestamp':stamp,'svix-signature':'v1,'+signature})
        self.assertEqual(response.status_code,200,response.text)
        alias=await self.enqueue_email(self.email('after-bounce','new-contact-id'))
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-runs/'+alias['id'])).json()['stop_reason'],'contact_opted_out')
        self.assertEqual(len(self.requests),1)

    async def test_missing_dialer_configuration_does_not_consume_key(self):
        self.gateway.settings=replace(self.settings,twilio_auth_token='')
        response=await self.client.post(f'/businesses/{self.bid}/calls',json={
            'idempotency_key':'config-correction','confirm_outbound_call':True})
        self.assertEqual(response.status_code,503)
        self.assertEqual(await self.app.state.store.list('calls'),[])
        self.assertEqual(self.requests,[])
        self.gateway.settings=self.settings
        await self.call('config-correction')
        self.assertEqual(len(self.requests),1)

    async def test_invalid_dialer_number_does_not_consume_key(self):
        self.gateway.settings=replace(self.settings,sales_agent_number='invalid')
        response=await self.client.post(f'/businesses/{self.bid}/calls',json={
            'idempotency_key':'number-correction','confirm_outbound_call':True})
        self.assertEqual(response.status_code,422)
        self.assertEqual(await self.app.state.store.list('calls'),[])
        self.assertEqual(self.requests,[])
        self.gateway.settings=self.settings
        await self.call('number-correction')
        self.assertEqual(len(self.requests),1)

    async def test_business_optout_serializes_with_in_progress_call_submission(self):
        entered,release=asyncio.Event(),asyncio.Event()
        async def provider(request):
            self.requests.append(request); entered.set(); await release.wait()
            return httpx.Response(201,json=self.provider_response)
        self.gateway.transport=httpx.MockTransport(provider)
        calling=asyncio.create_task(self.call('in-progress-call'))
        await asyncio.wait_for(entered.wait(),2)
        opting_out=asyncio.create_task(self.client.patch(f'/businesses/{self.bid}/contact',json={'stage':'do_not_contact'}))
        try:
            done,_=await asyncio.wait({opting_out},timeout=.03)
        finally:
            release.set()
            await calling
            response=await opting_out
        self.assertFalse(done,'Opt-out must not finish while call submission owns its guard')
        self.assertEqual(response.status_code,200)
        response=await self.client.post(f'/businesses/{self.bid}/calls',json={
            'idempotency_key':'after-optout','confirm_outbound_call':True})
        self.assertEqual(response.status_code,409)
        self.assertEqual(len(self.requests),1)

    async def guarded_mutation(self,path,body=None):
        async with self.app.state.execution.lock:
            operation=asyncio.create_task(self.client.post(path,json=body) if body is not None else self.client.post(path))
            done,_=await asyncio.wait({operation},timeout=.03)
        response=await operation
        self.assertFalse(done,'State mutation must wait for the runner action guard')
        self.assertIn(response.status_code,{200,201},response.text)

    async def test_archiving_waits_for_action_guard_and_stops_waiting_run(self):
        response=await self.client.post('/workflows/'+self.workflow['id']+'/runs',json={
            **self.run,'scheduled_at':(now()+timedelta(hours=1)).isoformat()})
        run=response.json(); await self.settle()
        await self.guarded_mutation('/workflows/'+self.workflow['id']+'/archive')
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-runs/'+run['id'])).json()['stop_reason'],'workflow_archived')
        self.assertEqual(await self.app.state.store.list('workflow_outbox'),[])

    async def test_new_evidence_waits_for_action_guard_and_stops_outdated_run(self):
        response=await self.client.post('/workflows/'+self.workflow['id']+'/runs',json={
            **self.run,'scheduled_at':(now()+timedelta(hours=1)).isoformat()})
        run=response.json(); await self.settle()
        await self.guarded_mutation(f'/businesses/{self.bid}/analyze',{'evidence':[]})
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-runs/'+run['id'])).json()['stop_reason'],'analysis_outdated')
        self.assertEqual(await self.app.state.store.list('workflow_outbox'),[])

    async def test_operations_flags_active_deployment_after_evidence_changes(self):
        _,deployment=await self.profile_and_deployment(); await self.activate(deployment)
        await self.client.post(f'/businesses/{self.bid}/analyze',json={'evidence':[]})
        response=await self.client.get('/operations/summary')
        alerts=response.json()['alerts']
        alert=next(a for a in alerts if a['id']==deployment['id'])
        self.assertEqual(alert['type'],'deployment_readiness')
        self.assertEqual(alert['reason'],'deployment_validation_stale')
        self.assertIn('current_workflow',alert['failed_checks'])
        self.assertEqual(self.requests,[])

    async def test_operations_flags_paused_client_and_preserves_demo_filter(self):
        record=await self.app.state.store.get('businesses',self.bid); record['source']='mock'
        await self.app.state.store.put('businesses',self.bid,record)
        client,deployment=await self.profile_and_deployment(); await self.activate(deployment)
        await self.client.post('/clients/'+client['id']+'/pause')
        self.assertEqual((await self.client.get('/operations/summary')).json()['alert_count'],0)
        alerts=(await self.client.get('/operations/summary?include_demo=true')).json()['alerts']
        alert=next(a for a in alerts if a['id']==deployment['id'])
        self.assertIn('client_active',alert['failed_checks'])
        await self.client.post('/deployments/'+deployment['id']+'/pause')
        self.assertEqual((await self.client.get('/operations/summary?include_demo=true')).json()['alert_count'],0)

    async def test_operations_flags_missing_deployment_reference_without_secrets(self):
        _,deployment=await self.profile_and_deployment(); await self.activate(deployment)
        deployment=await self.app.state.store.get('deployments',deployment['id'])
        deployment['workflow_id']='missing-fixture-workflow'
        await self.app.state.store.put('deployments',deployment['id'],deployment)
        response=await self.client.get('/operations/summary')
        self.assertEqual(response.status_code,200,response.text)
        alert=next(a for a in response.json()['alerts'] if a['id']==deployment['id'])
        self.assertEqual(alert['reason'],'deployment_reference_missing')
        self.assertNotIn(self.settings.twilio_auth_token,response.text)


if __name__=='__main__':
    import unittest
    unittest.main()
