import asyncio
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import httpx

from app.errors import AppError
from app.main import create_app
from app.models.workflow import now
from app.services.appointments import Appointments
from app.services.execution import Execution
from app.settings import Settings


class AppointmentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.time=now()
        self.settings=Settings(database_path=str(Path(self.temp.name)/'fixture.sqlite3'))
        self.app=create_app(self.settings)
        self.runner=Execution(self.app.state.store,self.app.state.platform,clock=lambda:self.time)
        self.service=Appointments(self.app.state.store,self.runner)
        self.app.state.execution=self.runner
        self.app.state.appointments=self.service
        self.runner.appointments=self.service
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app),base_url='http://testserver')
        self.addAsyncCleanup(self.client.aclose)
        business={'name':'Synthetic appointment fixture','address':'Fixture address','website':None,'phone':None,'rating':None,'review_count':None}
        self.bid=(await self.client.post('/businesses',json=business)).json()['id']
        analysis=(await self.client.post(f'/businesses/{self.bid}/analyze',json={'evidence':[
            {'criterion':'appointment_reminders','assessment':'strong','source':'business_confirmation','detail':'Synthetic fixture only.'}]})).json()
        self.workflow=(await self.client.post('/workflows',json={'analysis_id':analysis['id']})).json()
        self.body={'workflow_id':self.workflow['id'],'starts_at':(self.time+timedelta(hours=1)).isoformat(),
            'reminder':{'mode':'sandbox','confirm_sandbox':True,'idempotency_key':'synthetic-appointment',
                'event':{'contact_id':'synthetic-contact','contact_permission':True},'message_body':'Synthetic appointment reminder.',
                'scheduled_at':(self.time+timedelta(seconds=10)).isoformat()}}

    async def create(self,body=None):
        response=await self.client.post('/appointments',json=body or self.body)
        self.assertEqual(response.status_code,202,response.text)
        return response.json()

    async def settle(self):
        for _ in range(8):await self.runner.tick()

    async def test_appointment_event_schedules_real_local_reminder_at_requested_time(self):
        appointment=await self.create()
        await self.settle()
        run=(await self.client.get('/workflow-runs/'+appointment['run_id'])).json()
        self.assertEqual(run['status'],'waiting')
        self.assertEqual(run['appointment_id'],appointment['id'])
        self.assertEqual((await self.client.get('/workflow-outbox')).json(),[])
        self.time+=timedelta(seconds=10)
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-runs/'+appointment['run_id'])).json()['status'],'succeeded')
        self.assertEqual(len((await self.client.get('/workflow-outbox')).json()),1)

    async def test_duplicate_events_create_one_appointment_one_run_and_changed_inputs_conflict(self):
        responses=await asyncio.gather(*(self.client.post('/appointments',json=self.body) for _ in range(10)))
        self.assertTrue(all(r.status_code==202 for r in responses))
        self.assertEqual(len({r.json()['id'] for r in responses}),1)
        self.assertEqual(len((await self.client.get('/appointments')).json()),1)
        self.assertEqual(len((await self.client.get('/workflow-runs')).json()),1)
        changed={**self.body,'starts_at':(self.time+timedelta(hours=2)).isoformat()}
        self.assertEqual((await self.client.post('/appointments',json=changed)).status_code,409)

    async def test_cancel_is_persistent_idempotent_and_suppresses_waiting_reminder(self):
        appointment=await self.create()
        await self.settle()
        for _ in range(2):
            response=await self.client.post('/appointments/'+appointment['id']+'/cancel')
            self.assertEqual(response.json()['status'],'cancelled')
        self.time+=timedelta(minutes=2)
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-outbox')).json(),[])
        self.assertEqual((await self.create())['status'],'cancelled')
        self.assertEqual((await self.client.get('/workflow-runs/'+appointment['run_id'])).json()['status'],'cancelled')

    async def test_cancellation_saved_before_run_cancel_still_blocks_action_after_failure(self):
        appointment=await self.create()
        with patch.object(self.runner,'cancel',side_effect=AppError(503,'storage_unavailable','Synthetic outage')):
            self.assertEqual((await self.client.post('/appointments/'+appointment['id']+'/cancel')).status_code,503)
        self.time+=timedelta(minutes=2)
        await self.settle()
        run=(await self.client.get('/workflow-runs/'+appointment['run_id'])).json()
        self.assertEqual(run['stop_reason'],'appointment_cancelled')
        self.assertEqual((await self.client.get('/workflow-outbox')).json(),[])

    async def test_pending_event_recovers_without_creating_a_second_run(self):
        original=self.app.state.store.put
        failures=0
        async def flaky(kind,record_id,payload):
            nonlocal failures
            if kind=='appointments' and payload['status']=='scheduled' and not failures:
                failures+=1
                raise AppError(503,'storage_unavailable','Synthetic outage')
            return await original(kind,record_id,payload)
        with patch.object(self.app.state.store,'put',side_effect=flaky):
            self.assertEqual((await self.client.post('/appointments',json=self.body)).status_code,503)
        self.assertEqual((await self.client.get('/appointments')).json()[0]['status'],'pending')
        await self.service.recover()
        self.assertEqual((await self.client.get('/appointments')).json()[0]['status'],'scheduled')
        self.assertEqual(len((await self.client.get('/workflow-runs')).json()),1)

    async def test_expired_appointment_does_not_send_a_late_reminder_after_downtime(self):
        appointment=await self.create()
        self.time+=timedelta(hours=2)
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-runs/'+appointment['run_id'])).json()['stop_reason'],'appointment_expired')
        self.assertEqual((await self.client.get('/workflow-outbox')).json(),[])

    async def test_invalid_dates_unknown_workflows_and_pagination_fail_explicitly(self):
        for starts in (self.time.isoformat(),(self.time-timedelta(hours=1)).isoformat(),self.time.replace(tzinfo=None).isoformat()):
            self.assertEqual((await self.client.post('/appointments',json={**self.body,'starts_at':starts})).status_code,422)
        missing={**self.body,'reminder':{k:v for k,v in self.body['reminder'].items() if k!='scheduled_at'}}
        self.assertEqual((await self.client.post('/appointments',json=missing)).status_code,422)
        self.assertEqual((await self.client.post('/appointments',json={**self.body,'workflow_id':'missing'})).status_code,404)
        self.assertEqual((await self.client.get('/appointments?limit=0')).status_code,422)
        self.assertEqual((await self.client.get('/appointments')).json(),[])

    async def test_customer_opt_out_blocks_appointment_without_overriding_recorded_permission(self):
        await self.client.post(f'/businesses/{self.bid}/automation-contacts/synthetic-contact/opt-out')
        appointment=await self.create()
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-runs/'+appointment['run_id'])).json()['stop_reason'],'contact_opted_out')
        self.assertEqual((await self.client.get('/workflow-outbox')).json(),[])

    async def test_demo_scaffold_is_explicitly_fictional_and_repeated_requests_reuse_workflow(self):
        first = await self.client.post('/demo/reminder-workflow')
        self.assertEqual(first.status_code, 201)
        second = await self.client.post('/demo/reminder-workflow')
        self.assertTrue(first.json()['synthetic'])
        self.assertEqual(first.json()['business']['source'], 'mock')
        self.assertEqual(first.json()['workflow']['id'], second.json()['workflow']['id'])


if __name__=='__main__':unittest.main()
