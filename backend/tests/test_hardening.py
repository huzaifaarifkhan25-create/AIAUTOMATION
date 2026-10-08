import asyncio
import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import httpx

from app.database.store import SQLiteStore, SupabaseStore
from app.main import create_app
from app.services.gateway import Gateway
from app.services.scoring import WEIGHTS
from app.settings import Settings


class HardeningTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings(database_path=str(self.root / "fixture.sqlite3"), website_allowed_hosts=("example.com",))
        self.app = create_app(self.settings)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)
        self.business = {"name": "Synthetic audit fixture", "address": "Fixture address", "phone": "+12025550101",
                         "website": "https://example.com", "rating": None, "review_count": None}

    async def save(self):
        response = await self.client.post("/businesses", json=self.business)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def analyze(self, bid, **body):
        response = await self.client.post(f"/businesses/{bid}/analyze", json=body)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_repeat_manual_save_preserves_csv_identity_source_and_provenance(self):
        for place in ("", "synthetic-place-id"):
            with self.subTest(place=place):
                business = {**self.business, "name": "Synthetic audit fixture " + place}
                csv = f'name,address,phone,place_id\n{business["name"]},Fixture address,+12025550101,{place}\n'
                imported = await self.client.post("/businesses/import-csv?dry_run=false&collected_at=2026-01-01T00:00:00Z",
                    content=csv, headers={"Content-Type": "text/csv"})
                bid = imported.json()["rows"][0]["business_id"]
                before = (await self.client.get(f"/businesses/{bid}")).json()
                response = await self.client.post("/businesses", json={**business, "phone": "+12025550102"})
                self.assertEqual(response.json(), before)
                self.assertEqual((await self.client.get(f"/businesses/{bid}")).json(), before)
        self.assertEqual(len((await self.client.get("/businesses")).json()), 2)

    async def test_listing_analysis_keeps_original_observation_date(self):
        imported = await self.client.post("/businesses/import-csv?dry_run=false&collected_at=2026-01-01T00:00:00Z",
            content="name,address,phone\nSynthetic dated fixture,Fixture address,+12025550101\n", headers={"Content-Type": "text/csv"})
        bid = imported.json()["rows"][0]["business_id"]
        for _ in range(2):
            analysis = await self.analyze(bid)
            phone = next(e for e in analysis["evidence"] if e["criterion"] == "business_phone")
            self.assertEqual(phone["observed_at"], "2026-01-01T00:00:00Z")

    async def test_concurrent_csv_and_manual_saves_share_one_identity(self):
        csv = 'name,address,phone,place_id\nSynthetic audit fixture,Fixture address,+12025550101,synthetic-concurrent-place\n'
        requests = [self.client.post("/businesses/import-csv?dry_run=false", content=csv, headers={"Content-Type": "text/csv"})
                    if index % 2 else self.client.post("/businesses", json=self.business) for index in range(20)]
        responses = await asyncio.gather(*requests)
        self.assertTrue(all(response.status_code in (200, 201) for response in responses))
        self.assertEqual(len((await self.client.get("/businesses")).json()), 1)

    async def test_legacy_evidence_origin_is_unspecified_and_stored_snapshots_are_not_rewritten(self):
        bid = (await self.save())["id"]
        analysis = await self.analyze(bid)
        self.assertEqual(analysis["evidence"][0]["source"], "manual_research")
        record = await self.app.state.store.get("analyses", analysis["id"])
        for item in record["evidence"]:
            item.pop("origin")
        await self.app.state.store.put("analyses", analysis["id"], record)
        response = await self.client.get('/analyses/' + analysis['id'])
        self.assertEqual(response.json()["evidence"][0]["origin"], "unspecified")
        self.assertEqual(await self.app.state.store.get("analyses", analysis["id"]), record)

    async def test_website_refresh_replaces_automatic_observations_but_preserves_operator_confirmation(self):
        bid = (await self.save())["id"]
        pages = iter(["<title>Fixture</title><a href='mailto:test@example.com'>Email</a>", "<title>Fixture changed</title>"])
        self.app.state.gateway = Gateway(self.settings, httpx.MockTransport(lambda request: httpx.Response(200,
            headers={"Content-Type": "text/html"}, text=next(pages))))
        self.app.state.platform.gateway = self.app.state.gateway
        confirmation = {"criterion": "inquiry_followup", "assessment": "strong", "source": "business_confirmation",
            "detail": "Synthetic business confirmation only.", "observed_at": "2026-01-01T00:00:00Z"}
        with patch("app.services.gateway.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("8.8.8.8", 443))]):
            first = await self.analyze(bid, fetch_website=True, evidence=[confirmation])
            self.assertEqual(first["components"]["C"], 14)
            second = await self.analyze(bid, fetch_website=True, evidence=first["evidence"])
        self.assertFalse(second["website"]["emails"])
        self.assertEqual(second["components"]["C"], 6)
        self.assertEqual(second["components"]["N"], 10)
        preserved = next(e for e in second["evidence"] if e["criterion"] == "inquiry_followup")
        self.assertEqual(preserved["observed_at"], confirmation["observed_at"])
        self.assertEqual((await self.client.get('/analyses/' + first['id'])).json(), first)

    async def test_old_analysis_cannot_drive_new_outreach_or_workflow_after_need_is_withdrawn(self):
        bid = (await self.save())["id"]
        evidence = [{"criterion": "rebooking", "assessment": "strong", "source": "business_confirmation", "detail": "Synthetic prior confirmation."}]
        old = await self.analyze(bid, evidence=evidence)
        self.assertEqual((await self.client.post("/workflows", json={"analysis_id": old["id"]})).status_code, 201)
        new = await self.analyze(bid, evidence=[{**evidence[0], "assessment": "clear", "detail": "Synthetic reassessment: no gap."}])
        draft = await self.client.get(f"/businesses/{bid}/outreach-draft", params={"analysis_id": old["id"]})
        self.assertEqual(draft.status_code, 409)
        self.assertEqual((await self.client.post("/workflows", json={"analysis_id": old["id"]})).status_code, 409)
        current = (await self.client.get(f"/businesses/{bid}/outreach-draft", params={"analysis_id": new["id"]})).json()
        self.assertEqual(current["kind"], "discovery")
        self.assertEqual((await self.client.get('/analyses/' + old['id'])).json(), old)

    async def test_blocked_lead_cannot_generate_workflow_and_is_removed_from_opportunity_ranking(self):
        bid = (await self.save())["id"]
        evidence = [{"criterion": name, "assessment": "strong", "source": "business_confirmation" if component == "N" else "manual_research",
                     "detail": "Synthetic audit evidence only."} for name, (component, _) in WEIGHTS.items()]
        analysis = await self.analyze(bid, evidence=evidence)
        self.assertEqual(len((await self.client.get("/opportunities")).json()), 1)
        await self.client.patch(f"/businesses/{bid}/contact", json={"stage": "do_not_contact"})
        self.assertEqual((await self.client.get("/opportunities")).json(), [])
        self.assertEqual((await self.client.post("/workflows", json={"analysis_id": analysis["id"]})).status_code, 409)
        self.assertEqual((await self.client.get("/workflows")).json(), [])

    async def test_opportunity_ranking_excludes_demos_unless_explicitly_requested(self):
        mock = (await self.client.post("/businesses/import", json={"industry": "med spa", "location": "Synthetic city"})).json()[0]
        await self.analyze(mock["id"])
        self.assertEqual((await self.client.get("/opportunities?include_provisional=true")).json(), [])
        self.assertEqual(len((await self.client.get("/opportunities?include_provisional=true&include_demo=true")).json()), 1)

    async def test_text_or_short_values_do_not_become_automatic_phone_evidence(self):
        for phone in ("not available", "   ", "1234", "Reference 1234567890", "9" * 20):
            self.business = {**self.business, "name": "Synthetic phone " + phone, "phone": phone}
            analysis = await self.analyze((await self.save())["id"])
            self.assertEqual(analysis["components"]["C"], 0)
            self.assertIn("business_phone", analysis["unknown_criteria"])

    async def test_sqlite_operations_close_connections_even_after_errors(self):
        connect, connections = sqlite3.connect, []
        def tracked(*args, **kwargs):
            kwargs["check_same_thread"] = False
            connection = connect(*args, **kwargs)
            connections.append(connection)
            return connection
        store = self.app.state.store
        with patch("app.database.store.sqlite3.connect", side_effect=tracked):
            await store.put("contacts", "fixture", {"business_id": "fixture"})
            await store.get("contacts", "fixture")
            await store.list("contacts")
            await store.reserve("contacts", "fixture", {})
            with self.assertRaises(TypeError):
                await store.put("contacts", "invalid", {"bad": object()})
        try:
            for connection in connections:
                with self.assertRaises(sqlite3.ProgrammingError):
                    connection.execute("SELECT 1")
        finally:
            for connection in connections:
                connection.close()

    async def test_supabase_pagination_handles_large_analysis_batches_without_truncation(self):
        rows = [{"payload": {"id": str(index), "detail": "x" * 24000}} for index in range(120)]
        limits = []
        def provider(request):
            offset, limit = int(request.url.params.get("offset", "0")), int(request.url.params["limit"])
            limits.append(limit)
            return httpx.Response(200, json=rows[offset:offset + limit])
        settings = Settings(supabase_url="https://fixture.supabase.co", supabase_key="synthetic-key")
        store = SupabaseStore(settings, Gateway(settings, httpx.MockTransport(provider)))
        self.assertEqual(await store.list("analyses"), [row["payload"] for row in rows])
        self.assertGreater(len(limits), 1)

    async def test_invalid_provider_call_identifier_is_not_reported_as_submitted_or_retried(self):
        settings = replace(self.settings, app_api_token="synthetic-audit-token", enable_outbound_calls=True,
            twilio_account_sid="AC" + "1" * 32, twilio_auth_token="synthetic-twilio-secret",
            twilio_from_number="+12025550102", sales_agent_number="+12025550103")
        attempts = []
        def provider(request):
            attempts.append(request)
            return httpx.Response(201, json={"sid": ""})
        app = create_app(settings, gateway=Gateway(settings, httpx.MockTransport(provider)))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver",
                                    headers={"Authorization": "Bearer synthetic-audit-token"}) as client:
            bid = (await client.post("/businesses", json=self.business)).json()["id"]
            request = {"confirm_outbound_call": True, "idempotency_key": "synthetic-invalid-sid"}
            self.assertEqual((await client.post(f"/businesses/{bid}/calls", json=request)).status_code, 502)
            self.assertEqual((await client.post(f"/businesses/{bid}/calls", json=request)).status_code, 409)
            self.assertEqual((await client.get("/calls")).json()[0]["status"], "failed_or_uncertain")
            self.assertEqual(len(attempts), 1)


if __name__ == "__main__":
    unittest.main()
