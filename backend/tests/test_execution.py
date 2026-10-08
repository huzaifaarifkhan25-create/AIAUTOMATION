import asyncio
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import httpx

from app.database.store import SQLiteStore, SupabaseStore
from app.errors import AppError
from app.main import create_app
from app.models.workflow import now
from app.services.execution import Execution
from app.settings import Settings
from backup import backup, restore


class ExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings(database_path=str(self.root / "fixture.sqlite3"), scrape_output_path=str(self.root / "scrapes"))
        self.app = create_app(self.settings)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)
        self.time = now()
        self.runner = Execution(self.app.state.store, self.app.state.platform, clock=lambda: self.time, poll_seconds=.01)
        self.app.state.execution = self.runner
        self.addAsyncCleanup(self.runner.close)
        self.bid = (await self.client.post("/businesses/import", json={"industry": "med spa", "location": "Synthetic execution fixture"})).json()[0]["id"]
        self.body = {"mode": "sandbox", "confirm_sandbox": True, "idempotency_key": "synthetic-event-1",
            "event": {"contact_id": "synthetic-contact-1", "contact_permission": True}, "message_body": "Synthetic reminder preview only."}
        self.workflow = await self.make_workflow()

    async def make_workflow(self, criterion="inquiry_followup", source="business_confirmation"):
        analysis = (await self.client.post(f"/businesses/{self.bid}/analyze", json={"evidence": [
            {"criterion": criterion, "assessment": "strong", "source": source, "detail": "Synthetic execution evidence only."}]})).json()
        response = await self.client.post("/workflows", json={"analysis_id": analysis["id"]})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def enqueue(self, body=None, workflow=None):
        response = await self.client.post(f'/workflows/{(workflow or self.workflow)["id"]}/runs', json=body or self.body)
        self.assertEqual(response.status_code, 202, response.text)
        return response.json()

    async def settle(self, count=10):
        for _ in range(count):
            await self.runner.tick()

    async def get(self, run):
        return (await self.client.get('/workflow-runs/' + run['id'])).json()

    async def test_local_workflow_really_executes_and_records_unsent_preview(self):
        run = await self.enqueue()
        with patch.object(self.app.state.gateway, "request", side_effect=AssertionError("No network action permitted")):
            await self.settle()
        saved = await self.get(run)
        self.assertEqual(saved["status"], "succeeded")
        self.assertEqual(saved["result"], "sandbox_recorded")
        self.assertEqual(saved["next_step"], 4)
        self.assertFalse(saved["sent"])
        self.assertEqual([h["step"] for h in saved["history"] if h["outcome"] == "step_completed"], ["event", "permission", "message", "record"])
        outbox = (await self.client.get('/workflow-outbox', params={"run_id": run["id"]})).json()
        self.assertEqual(len(outbox), 1)
        self.assertEqual(outbox[0]["message_body"], self.body["message_body"])
        self.assertFalse(outbox[0]["sent"])

    async def test_concurrent_duplicate_requests_are_one_run_and_different_inputs_conflict(self):
        responses = await asyncio.gather(*(self.client.post(f'/workflows/{self.workflow["id"]}/runs', json=self.body) for _ in range(12)))
        self.assertTrue(all(r.status_code == 202 for r in responses))
        self.assertEqual(len({r.json()["id"] for r in responses}), 1)
        await self.settle()
        self.assertEqual(len((await self.client.get('/workflow-runs')).json()), 1)
        self.assertEqual(len((await self.client.get('/workflow-outbox')).json()), 1)
        self.assertEqual((await self.enqueue())["status"], "succeeded")
        changed = await self.client.post(f'/workflows/{self.workflow["id"]}/runs', json={**self.body, "message_body": "Changed synthetic text"})
        self.assertEqual(changed.status_code, 409)
        self.assertEqual(changed.json()["error"]["code"], "run_key_conflict")

    async def test_scheduled_wait_survives_new_runner_and_never_runs_early(self):
        self.workflow = await self.make_workflow("appointment_reminders")
        run = await self.enqueue({**self.body, "scheduled_at": (self.time + timedelta(days=1)).isoformat()})
        await self.settle()
        self.assertEqual((await self.get(run))["status"], "waiting")
        self.assertEqual((await self.client.get('/workflow-outbox')).json(), [])
        self.runner = Execution(SQLiteStore(self.settings.database_path), self.app.state.platform, clock=lambda: self.time)
        self.app.state.execution = self.runner
        await self.settle()
        self.assertEqual((await self.get(run))["status"], "waiting")
        self.time += timedelta(days=1)
        await self.settle()
        self.assertEqual((await self.get(run))["status"], "succeeded")
        self.assertEqual(len((await self.client.get('/workflow-outbox')).json()), 1)

    async def test_archived_opted_out_and_superseded_workflows_stop_waiting_runs(self):
        for reason in ("workflow_archived", "do_not_contact", "analysis_outdated"):
            with self.subTest(reason=reason):
                await self.client.patch(f"/businesses/{self.bid}/contact", json={"stage": "new"})
                self.workflow = await self.make_workflow("rebooking")
                run = await self.enqueue({**self.body, "idempotency_key": reason, "scheduled_at": (self.time + timedelta(days=1)).isoformat()})
                await self.settle()
                if reason == "workflow_archived":
                    await self.client.post(f'/workflows/{self.workflow["id"]}/archive')
                elif reason == "do_not_contact":
                    await self.client.patch(f"/businesses/{self.bid}/contact", json={"stage": "do_not_contact"})
                else:
                    await self.client.post(f"/businesses/{self.bid}/analyze", json={})
                await self.runner.tick()
                saved = await self.get(run)
                self.assertEqual(saved["status"], "skipped")
                self.assertEqual(saved["stop_reason"], reason)
        self.assertEqual((await self.client.get('/workflow-outbox')).json(), [])

    async def test_permission_cancellation_and_operator_cancel_produce_no_preview(self):
        for event, reason in (({"contact_permission": False}, "contact_permission_missing"), ({"appointment_cancelled": True}, "appointment_cancelled")):
            run = await self.enqueue({**self.body, "idempotency_key": reason, "event": {**self.body["event"], **event}})
            await self.settle()
            self.assertEqual((await self.get(run))["stop_reason"], reason)
            self.assertEqual((await self.get(run))["status"], "skipped")
        run = await self.enqueue()
        cancelled = await self.client.post('/workflow-runs/' + run['id'] + '/cancel')
        self.assertEqual(cancelled.json()["status"], "cancelled")
        self.assertEqual((await self.client.post('/workflow-runs/' + run['id'] + '/cancel')).status_code, 200)
        await self.settle()
        self.assertEqual((await self.client.get('/workflow-outbox')).json(), [])
        self.assertEqual((await self.enqueue())["status"], "cancelled")

    async def test_transient_outbox_failure_retries_at_backoff_and_exhaustion_is_terminal(self):
        for fail_count in (1, 3):
            run = await self.enqueue({**self.body, "idempotency_key": f"failure-{fail_count}"})
            await self.settle(2)
            original = self.app.state.store.reserve
            failures = 0
            async def flaky(kind, *args):
                nonlocal failures
                if kind == "workflow_outbox" and failures < fail_count:
                    failures += 1
                    raise AppError(503, "storage_unavailable", "Secret-looking diagnostic must not be stored")
                return await original(kind, *args)
            with patch.object(self.app.state.store, "reserve", side_effect=flaky):
                await self.runner.tick()
                waiting = await self.get(run)
                self.assertEqual(waiting["status"], "retry_wait")
                await self.settle()
                self.assertEqual(failures, 1)
                for _ in range(3):
                    self.time += timedelta(seconds=4)
                    await self.settle()
            saved = await self.get(run)
            self.assertEqual(saved["status"], "succeeded" if fail_count == 1 else "failed")
            self.assertEqual(saved["step_attempts"]["message"], 2 if fail_count == 1 else 3)
            self.assertNotIn("Secret-looking", str(saved))
        self.assertEqual(len((await self.client.get('/workflow-outbox')).json()), 1)

    async def test_recovery_after_local_effect_before_progress_save_cannot_duplicate_preview(self):
        run = await self.enqueue()
        await self.settle(2)
        original = self.app.state.store.put
        async def crash(kind, record_id, payload):
            if kind == "workflow_runs" and payload["next_step"] == 3:
                raise asyncio.CancelledError()
            return await original(kind, record_id, payload)
        with patch.object(self.app.state.store, "put", side_effect=crash):
            with self.assertRaises(asyncio.CancelledError):
                await self.runner.tick()
        self.assertEqual((await self.get(run))["status"], "running")
        self.assertEqual(len((await self.client.get('/workflow-outbox')).json()), 1)
        restored_app = create_app(self.settings)
        async with restored_app.router.lifespan_context(restored_app):
            for _ in range(100):
                if (await restored_app.state.store.get("workflow_runs", run["id"]))["status"] == "succeeded":
                    break
                await asyncio.sleep(.03)
            else:
                self.fail("Recovered runner did not finish")
        self.assertEqual(len(await restored_app.state.store.list("workflow_outbox")), 1)
        self.assertIn("recovered_after_restart", str(await restored_app.state.store.get("workflow_runs", run["id"])))

    async def test_failure_saving_progress_replays_same_step_with_one_outbox_record(self):
        run = await self.enqueue()
        await self.settle(2)
        original = self.app.state.store.put
        failures = 0
        async def flaky(kind, record_id, payload):
            nonlocal failures
            if kind == "workflow_runs" and payload["next_step"] == 3 and not failures:
                failures += 1
                raise AppError(503, "storage_unavailable", "Synthetic transient write failure")
            return await original(kind, record_id, payload)
        with patch.object(self.app.state.store, "put", side_effect=flaky):
            await self.runner.tick()
        saved = await self.get(run)
        self.assertEqual(saved["next_step"], 2)
        self.assertEqual(saved["status"], "retry_wait")
        self.time += timedelta(seconds=2)
        await self.settle()
        self.assertEqual((await self.get(run))["status"], "succeeded")
        self.assertEqual(len((await self.client.get('/workflow-outbox')).json()), 1)

    async def test_guard_read_failure_has_bounded_retries_without_actions(self):
        run = await self.enqueue()
        with patch.object(self.runner, "check_current", side_effect=AppError(503, "storage_unavailable", "Synthetic outage")):
            for _ in range(4):
                await self.runner.tick()
                await self.runner.tick()
                self.assertEqual((await self.get(run))["step_attempts"]["event"], _ + 1 if _ < 3 else 3)
                self.time += timedelta(seconds=4)
        saved = await self.get(run)
        self.assertEqual(saved["status"], "failed")
        self.assertEqual(saved["step_attempts"]["event"], 3)
        self.assertEqual((await self.client.get('/workflow-outbox')).json(), [])

    async def test_strict_inputs_missing_timing_and_unsupported_calendar_fail_before_enqueuing(self):
        path = f'/workflows/{self.workflow["id"]}/runs'
        bodies = [{**self.body, "mode": "live"}, {**self.body, "confirm_sandbox": False},
            {**self.body, "confirm_sandbox": 1}, {**self.body, "confirm_sandbox": "true"},
            {**self.body, "event": {**self.body["event"], "contact_permission": "false"}},
            {**self.body, "event": {**self.body["event"], "email": "synthetic@example.com"}},
            {**self.body, "scheduled_at": self.time.isoformat()}, {**self.body, "message_body": " "}]
        for body in bodies:
            self.assertEqual((await self.client.post(path, json=body)).status_code, 422)
        self.workflow = await self.make_workflow("appointment_reminders")
        response = await self.client.post(f'/workflows/{self.workflow["id"]}/runs', json=self.body)
        self.assertEqual(response.status_code, 422)
        self.workflow = await self.make_workflow("booking_friction", "manual_research")
        response = await self.client.post(f'/workflows/{self.workflow["id"]}/runs', json=self.body)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "workflow_unsupported")
        self.assertEqual((await self.client.get('/workflow-runs')).json(), [])

    async def test_execution_routes_are_protected_and_supabase_fails_explicitly(self):
        protected = create_app(Settings(database_path=self.settings.database_path, app_api_token="synthetic-runner-token"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=protected), base_url="http://testserver") as client:
            for method, path in (("GET", "/workflow-runs"), ("GET", "/workflow-outbox"),
                                 ("POST", f'/workflows/{self.workflow["id"]}/runs'), ("POST", "/workflow-runs/missing/cancel")):
                self.assertEqual((await client.request(method, path, json=self.body if path.endswith('/runs') else None)).status_code, 401)
            self.assertEqual((await client.get('/workflow-runs', headers={"Authorization": "Bearer synthetic-runner-token"})).status_code, 200)
        remote = SupabaseStore(self.settings, self.app.state.gateway)
        unsupported = Execution(remote, self.app.state.platform)
        self.app.state.execution = unsupported
        self.assertEqual((await self.client.get('/workflow-runs')).status_code, 503)
        self.assertEqual((await self.client.get('/capabilities')).json()["workflow_runner_modes"], [])

    async def test_run_and_preview_survive_sqlite_backup_restore(self):
        run = await self.enqueue()
        await self.settle()
        folder = backup(Path(self.settings.database_path), Path(self.settings.scrape_output_path), self.root / "backups")
        recovered = restore(folder, self.root / "recovered")
        store = SQLiteStore(str(recovered / "backend.sqlite3"))
        self.assertEqual((await store.get("workflow_runs", run["id"]))["status"], "succeeded")
        self.assertEqual(len(await store.list("workflow_outbox")), 1)

    async def test_background_lifecycle_processes_pending_runs_and_stops_cleanly(self):
        run = await self.enqueue()
        await self.runner.start()
        for _ in range(100):
            if (await self.get(run))["status"] == "succeeded":
                break
            await asyncio.sleep(.02)
        else:
            self.fail("Background runner did not finish")
        await self.runner.close()
        self.assertIsNone(self.runner.task)
        self.assertEqual(len((await self.client.get('/workflow-outbox')).json()), 1)


if __name__ == "__main__":
    unittest.main()
