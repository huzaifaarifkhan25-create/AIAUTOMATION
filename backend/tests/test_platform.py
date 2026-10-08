import asyncio
import tempfile
import unittest
from pathlib import Path

import httpx

from app.database.store import SQLiteStore
from app.main import create_app
from app.services.scoring import WEIGHTS
from app.settings import Settings


def complete_evidence(assessment="strong"):
    return [
        {"criterion": name, "assessment": assessment,
         "source": "business_confirmation" if component == "N" else "manual_research",
         "detail": f"Synthetic test evidence for {name}."}
        for name, (component, _) in WEIGHTS.items()
    ]


class PlatformTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(database_path=str(Path(self.temp.name) / "db.sqlite3"))
        self.app = create_app(self.settings)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)
        response = await self.client.post("/businesses/import", json={"industry": "med spa", "location": "Demo City"})
        self.assertEqual(response.status_code, 200)
        self.business = response.json()[0]
        self.bid = self.business["id"]

    async def analyze(self, evidence=None):
        response = await self.client.post(f"/businesses/{self.bid}/analyze", json={"evidence": evidence or complete_evidence()})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_full_discover_analyze_rank_contact_build_flow(self):
        analysis = await self.analyze()
        self.assertEqual(analysis["components"], {"N": 40, "C": 20, "V": 20, "D": 20})
        self.assertEqual((analysis["need_score"], analysis["sales_score"], analysis["total_score"]), (100, 100, 100))
        self.assertEqual(analysis["evidence_coverage"], 100)
        self.assertEqual(analysis["priority"], "high")
        self.assertFalse(analysis["provisional"])
        ranking = (await self.client.get("/opportunities?include_demo=true")).json()
        self.assertEqual([a["id"] for a in ranking], [analysis["id"]])
        draft = await self.client.get(f"/businesses/{self.bid}/outreach-draft", params={"analysis_id": analysis["id"]})
        self.assertEqual(draft.status_code, 200)
        self.assertFalse(draft.json()["sent"])
        contact = await self.client.patch(f"/businesses/{self.bid}/contact", json={"stage": "demo_booked", "notes": "Synthetic demo outcome"})
        self.assertEqual(contact.status_code, 200)
        self.assertEqual(contact.json()["stage"], "demo_booked")
        generated = await self.client.post("/workflows", json={"analysis_id": analysis["id"]})
        self.assertEqual(generated.status_code, 201, generated.text)
        workflow = generated.json()
        self.assertEqual(workflow["format"], "medspa-workflow-v1")
        self.assertFalse(workflow["execution_supported"])
        ids = {node["id"] for node in workflow["nodes"]}
        self.assertTrue(all(a in ids and b in ids for a, b in workflow["connections"]))
        self.assertIn("condition", {node["type"] for node in workflow["nodes"]})
        exported = await self.client.get(f'/workflows/{workflow["id"]}/export')
        self.assertEqual(exported.json(), workflow)
        archived = await self.client.post(f'/workflows/{workflow["id"]}/archive')
        self.assertEqual(archived.json()["status"], "archived")

    async def test_business_import_is_idempotent_and_survives_new_app(self):
        response = await self.client.post("/businesses/import", json={"industry": "med spa", "location": "Demo City"})
        self.assertEqual(response.json()[0]["id"], self.bid)
        self.assertEqual(response.json()[0]["created_at"], self.business["created_at"])
        self.assertEqual(len((await self.client.get("/businesses")).json()), 2)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(self.settings)), base_url="http://testserver") as client:
            record = await client.get(f"/businesses/{self.bid}")
            self.assertEqual(record.json()["business"], self.business["business"])
            self.assertEqual(record.json()["source"], "mock")

    async def test_partial_points_formula_and_unknown_coverage(self):
        analysis = await self.analyze(complete_evidence("partial"))
        self.assertEqual(analysis["total_score"], 50)
        self.assertEqual(analysis["need_score"], 50)
        self.assertEqual(analysis["sales_score"], 50)
        self.assertEqual(analysis["evidence_coverage"], 100)
        response = await self.client.post(f"/businesses/{self.bid}/analyze", json={})
        unknown = response.json()
        self.assertEqual(unknown["total_score"], 0)
        self.assertEqual(unknown["evidence_coverage"], 0)
        self.assertEqual(len(unknown["unknown_criteria"]), 12)
        self.assertEqual(unknown["priority"], "research")
        self.assertEqual((await self.client.get("/opportunities")).json(), [])
        self.assertEqual(len((await self.client.get("/opportunities?include_provisional=true&include_demo=true")).json()), 1)
        rejected = await self.client.post("/workflows", json={"analysis_id": unknown["id"]})
        self.assertEqual(rejected.status_code, 409)

    async def test_known_clear_is_assessed_not_unknown(self):
        analysis = await self.analyze(complete_evidence("clear"))
        self.assertEqual(analysis["total_score"], 0)
        self.assertEqual(analysis["evidence_coverage"], 100)
        self.assertEqual(analysis["unknown_criteria"], [])
        self.assertFalse(analysis["provisional"])

    async def test_duplicate_and_unconfirmed_operational_evidence_rejected(self):
        evidence = complete_evidence()
        evidence[0]["source"] = "public_website"
        response = await self.client.post(f"/businesses/{self.bid}/analyze", json={"evidence": evidence})
        self.assertEqual(response.status_code, 422)
        duplicate = complete_evidence()[:1] * 2
        response = await self.client.post(f"/businesses/{self.bid}/analyze", json={"evidence": duplicate})
        self.assertEqual(response.status_code, 422)

    async def test_missing_records_and_mismatched_outreach_analysis(self):
        for path in ("/businesses/missing", "/analyses/missing", "/workflows/missing"):
            with self.subTest(path=path):
                self.assertEqual((await self.client.get(path)).status_code, 404)
        analysis = await self.analyze()
        other_id = (await self.client.get("/businesses")).json()[1]["id"]
        if other_id == self.bid:
            other_id = (await self.client.get("/businesses")).json()[0]["id"]
        response = await self.client.get(f"/businesses/{other_id}/outreach-draft", params={"analysis_id": analysis["id"]})
        self.assertEqual(response.status_code, 409)

    async def test_unconfigured_real_services_fail_explicitly(self):
        discovery = await self.client.post("/businesses/search", json={"industry": "med spa", "location": "Demo City", "source": "google_places"})
        self.assertEqual(discovery.status_code, 503)
        ai = await self.client.post(f"/businesses/{self.bid}/analyze", json={"use_ai": True})
        self.assertEqual(ai.status_code, 503)
        website = await self.client.post(f"/businesses/{self.bid}/analyze", json={"fetch_website": True})
        self.assertEqual(website.status_code, 422)
        self.assertEqual((await self.client.get("/analyses")).json(), [])

    async def test_api_token_protects_data_but_health_is_public(self):
        app = create_app(Settings(database_path=self.settings.database_path, app_api_token="test-only-token"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            self.assertEqual((await client.get("/health")).status_code, 200)
            self.assertEqual((await client.get("/businesses")).status_code, 401)
            self.assertEqual((await client.get("/businesses", headers={"Authorization": "Bearer wrong"})).status_code, 401)
            self.assertEqual((await client.get("/businesses", headers={"Authorization": "Bearer test-only-token"})).status_code, 200)

    async def test_mock_business_calls_never_execute(self):
        response = await self.client.post(f"/businesses/{self.bid}/calls", json={"idempotency_key": "demo-only-key", "confirm_outbound_call": True})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "mock_business")

    async def test_call_reservation_is_atomic(self):
        store = SQLiteStore(self.settings.database_path)
        results = await asyncio.gather(*(store.reserve("calls", "same-key", {"status": "pending"}) for _ in range(5)))
        self.assertEqual(sum(results), 1)

    async def test_ready_pagination_and_limits(self):
        self.assertEqual((await self.client.get("/ready")).status_code, 200)
        self.assertEqual(len((await self.client.get("/businesses?limit=1&offset=1")).json()), 1)
        self.assertEqual((await self.client.get("/businesses?limit=0")).status_code, 422)
        response = await self.client.post("/businesses/search", json={"industry": "med spas", "location": "Demo City", "limit": 1})
        self.assertEqual(len(response.json()), 1)
