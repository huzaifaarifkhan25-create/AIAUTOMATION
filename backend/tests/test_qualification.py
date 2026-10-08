import tempfile
import unittest
from pathlib import Path

import httpx

from app.main import create_app
from app.services.scoring import WEIGHTS
from app.settings import Settings


def item(criterion, assessment="strong", source="public_website"):
    return {"criterion": criterion, "assessment": assessment, "source": source,
            "detail": f"Synthetic fixture observation: {criterion}, {assessment}."}


class QualificationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(database_path=str(Path(self.temp.name) / "fixture.sqlite3"))
        self.app = create_app(self.settings)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)
        self.business = await self.save("Synthetic First Spa")
        self.bid = self.business["id"]

    async def save(self, name):
        response = await self.client.post("/businesses", json={"name": name, "address": name + " Fixture Address",
            "phone": "+12025550101", "website": "https://example.com", "rating": None, "review_count": None})
        self.assertEqual(response.status_code, 201)
        return response.json()

    async def analyze(self, evidence, business_id=None):
        response = await self.client.post(f'/businesses/{business_id or self.bid}/analyze', json={"evidence": evidence})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def qualification(self, business_id=None):
        response = await self.client.get(f'/businesses/{business_id or self.bid}/qualification')
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_public_ready_does_not_establish_internal_need_or_workflow(self):
        analysis = await self.analyze([item("operational_scale")])
        q = await self.qualification()
        self.assertEqual((q["prospect_score"], q["public_evidence_coverage"]), (40, 40))
        self.assertEqual(q["prospect_status"], "ready_for_review")
        self.assertEqual(q["need_status"], "unconfirmed")
        self.assertFalse(q["need_review_ready"])
        self.assertEqual(q["confirmed_gap_criteria"], [])
        self.assertEqual((analysis["need_score"], analysis["evidence_coverage"]), (0, 16))
        self.assertTrue(analysis["provisional"])
        self.assertEqual((await self.client.get("/opportunities")).json(), [])
        self.assertEqual((await self.client.post("/workflows", json={"analysis_id": analysis["id"]})).status_code, 409)
        draft = (await self.client.get(f'/businesses/{self.bid}/outreach-draft', params={"analysis_id": analysis["id"]})).json()
        self.assertEqual(draft["kind"], "discovery")
        self.assertFalse(draft["sent"])
        self.assertIn("I'd like to understand", draft["body"])
        self.assertNotIn("Synthetic fixture observation", draft["body"])
        self.assertNotIn("whether confirm business needs", draft["body"].lower())

    async def test_public_coverage_uses_40_weight_without_lowering_need_gate(self):
        public = [item(name) for name, (component, _) in WEIGHTS.items() if component in {"C", "V"}]
        analysis = await self.analyze(public)
        q = await self.qualification()
        self.assertEqual((q["prospect_score"], q["public_evidence_coverage"]), (100, 100))
        self.assertEqual(analysis["evidence_coverage"], 40)
        self.assertEqual(q["need_status"], "unconfirmed")
        friction = [item(name) for name, (component, _) in WEIGHTS.items() if component == "D"]
        analysis = await self.analyze(public + friction)
        q = await self.qualification()
        self.assertEqual(analysis["evidence_coverage"], 60)
        self.assertTrue(analysis["provisional"])
        self.assertEqual(q["need_status"], "observed_friction")
        self.assertFalse(q["need_review_ready"])
        self.assertEqual(q["confirmed_gap_criteria"], [])
        self.assertEqual(q["public_evidence_coverage"], 100)

    async def test_confirmed_gap_and_scope_readiness_are_distinct(self):
        analysis = await self.analyze([item("operational_scale"), item("inquiry_followup", source="business_confirmation")])
        q = await self.qualification()
        self.assertEqual(q["need_status"], "confirmed_gap")
        self.assertEqual(q["confirmed_gap_criteria"], ["inquiry_followup"])
        self.assertFalse(q["need_review_ready"])
        self.assertEqual(q["prospect_score"], 40)
        draft = (await self.client.get(f'/businesses/{self.bid}/outreach-draft', params={"analysis_id": analysis["id"]})).json()
        self.assertEqual(draft["kind"], "confirmed_need")
        self.assertIn("recorded discussion", draft["body"])
        evidence = [item(name, source="business_confirmation" if component == "N" else "public_website")
                    for name, (component, _) in WEIGHTS.items()]
        await self.analyze(evidence)
        self.assertTrue((await self.qualification())["need_review_ready"])

    async def test_clear_and_unknown_are_not_interchangeable(self):
        await self.analyze([item(name, "clear") for name, (component, _) in WEIGHTS.items() if component in {"C", "V"}])
        q = await self.qualification()
        self.assertEqual(q["public_evidence_coverage"], 100)
        self.assertEqual(q["public_unknown_criteria"], [])
        self.assertEqual(q["prospect_score"], 0)
        self.assertEqual(q["prospect_status"], "research")
        self.assertEqual(q["need_status"], "unconfirmed")
        await self.analyze([item(name, "clear", "business_confirmation" if component == "N" else "manual_research")
                            for name, (component, _) in WEIGHTS.items()])
        q = await self.qualification()
        self.assertEqual(q["need_status"], "assessed_no_gap")
        self.assertFalse(q["need_review_ready"])

    async def test_missing_contact_or_untested_form_does_not_qualify(self):
        evidence = [item("business_phone", "clear"), item("operational_scale"), item("recurring_services"), item("inquiry_form", "partial")]
        await self.analyze(evidence)
        q = await self.qualification()
        self.assertGreaterEqual(q["prospect_score"], 40)
        self.assertEqual(q["prospect_status"], "research")
        self.assertTrue(any("untested form" in reason for reason in q["prospect_reasons"]))
        await self.analyze(evidence[:-1] + [item("inquiry_form", "strong")])
        self.assertEqual((await self.qualification())["prospect_status"], "ready_for_review")

    async def test_phone_only_or_partial_fit_requires_more_research(self):
        await self.analyze([])
        q = await self.qualification()
        self.assertEqual((q["prospect_score"], q["public_evidence_coverage"]), (15, 15))
        self.assertEqual(q["prospect_status"], "research")
        await self.analyze([item("operational_scale", "partial")])
        q = await self.qualification()
        self.assertEqual(q["public_evidence_coverage"], 40)
        self.assertEqual(q["prospect_score"], 28)
        self.assertEqual(q["prospect_status"], "research")

    async def test_contact_stage_cannot_confirm_need_and_opt_out_blocks_drafts(self):
        analysis = await self.analyze([item("operational_scale")])
        await self.client.patch(f'/businesses/{self.bid}/contact', json={"stage": "interested", "notes": "Synthetic fixture"})
        self.assertEqual((await self.qualification())["need_status"], "unconfirmed")
        await self.client.patch(f'/businesses/{self.bid}/contact', json={"stage": "do_not_contact", "notes": "Synthetic opt-out"})
        q = await self.qualification()
        self.assertEqual(q["prospect_status"], "do_not_contact")
        self.assertFalse(q["need_review_ready"])
        self.assertEqual((await self.client.get("/prospects")).json(), [])
        self.assertEqual(len((await self.client.get("/prospects?include_blocked=true")).json()), 1)
        response = await self.client.get(f'/businesses/{self.bid}/outreach-draft', params={"analysis_id": analysis["id"]})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "do_not_contact")

    async def test_latest_snapshot_ranking_and_read_only_legacy_compatibility(self):
        old = await self.analyze([item("operational_scale"), item("rebooking", source="business_confirmation")])
        second = await self.save("Synthetic Second Spa")
        high = await self.analyze([item("public_email"), item("operational_scale"), item("recurring_services")], second["id"])
        snapshots = await self.app.state.store.list("analyses")
        ranked = (await self.client.get("/prospects")).json()
        self.assertEqual([q["business_id"] for q in ranked], [second["id"], self.bid])
        self.assertEqual(ranked[0]["prospect_score"], 85)
        self.assertEqual(ranked[0]["analysis_id"], high["id"])
        self.assertEqual((await self.client.get(f'/analyses/{old["id"]}')).json(), old)
        self.assertEqual(await self.app.state.store.list("analyses"), snapshots)
        new = await self.analyze([], second["id"])
        ranked = (await self.client.get("/prospects")).json()
        self.assertEqual(ranked[0]["business_id"], self.bid)
        self.assertEqual(ranked[1]["analysis_id"], new["id"])
        self.assertEqual((await self.client.get("/prospects?limit=1&offset=1")).json(), ranked[1:2])

    async def test_unanalyzed_demo_exclusion_validation_and_authentication(self):
        q = await self.qualification()
        self.assertIsNone(q["analysis_id"])
        self.assertEqual(q["prospect_status"], "not_analyzed")
        self.assertEqual((q["prospect_score"], q["public_evidence_coverage"]), (0, 0))
        await self.client.post("/businesses/import", json={"industry": "med spa", "location": "Fixture only"})
        self.assertEqual(len((await self.client.get("/prospects")).json()), 1)
        included = (await self.client.get("/prospects?include_demo=true")).json()
        self.assertEqual(len(included), 3)
        self.assertEqual(sum(q["is_demo"] for q in included), 2)
        self.assertEqual((await self.client.get("/prospects?limit=0")).status_code, 422)
        self.assertEqual((await self.client.get("/businesses/missing/qualification")).status_code, 404)
        app = create_app(Settings(database_path=self.settings.database_path, app_api_token="fixture-only-token"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            for path in ("/prospects", f'/businesses/{self.bid}/qualification'):
                self.assertEqual((await client.get(path)).status_code, 401)
                self.assertEqual((await client.get(path, headers={"Authorization": "Bearer fixture-only-token"})).status_code, 200)
