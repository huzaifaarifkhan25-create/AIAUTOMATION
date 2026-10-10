import asyncio
import csv
import hashlib
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path

import httpx

from app.errors import AppError
from app.main import create_app
from app.models.business import Business
from app.models.discovery import DiscoveryRequest
from app.models.workflow import WebsiteFindings, now
from app.services.discovery import Discovery, spreadsheet_csv
from app.services.scoring import automatic_evidence, score
from app.settings import Settings
from collect_leads import CollectorUnavailable


class WorkspaceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = Settings(database_path=str(self.root / "db.sqlite3"), app_api_token="fixture-access-token")
        self.app = create_app(self.settings)
        self.service = Discovery(self.app.state.store, self.root / "scrapes", self.collector)
        self.app.state.discovery = self.service
        self.addAsyncCleanup(self.service.close)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver",
                                       headers={"Authorization": "Bearer fixture-access-token"})
        self.addAsyncCleanup(self.client.aclose)

    def collector(self, query, root, limit):
        output = root / "fixture-run"
        output.mkdir(parents=True, exist_ok=True)
        data = b'title,address,website,phone,place_id\nSynthetic Test Spa,Fixture Address,https://example.com,+12025550101,test-place\n'
        path = output / "results.csv"
        path.write_bytes(data)
        path.with_name("manifest.json").write_text(json.dumps({"sha256": hashlib.sha256(data).hexdigest(),
            "started_at": now().isoformat(), "collected_count": 1, "query": query, "tls_verification": True}))
        return path

    async def start_job(self):
        response = await self.client.post("/discovery/jobs", json={"query": "synthetic fixture only", "limit": 1})
        self.assertEqual(response.status_code, 202, response.text)
        await self.service.close()
        job = (await self.client.get(f'/discovery/jobs/{response.json()["id"]}')).json()
        return job

    async def test_public_shell_and_assets_keep_api_private(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver") as client:
            self.assertEqual((await client.get("/")).headers["location"], "/app/")
            shell = await client.get("/app/")
            self.assertEqual(shell.status_code, 200)
            self.assertIn('/app/workspace.js', shell.text)
            self.assertNotIn("fixture-access-token", shell.text)
            for path in ("/app/styles.css", "/app/workspace.js"):
                self.assertEqual((await client.get(path)).status_code, 200)
            for path in ("/businesses", "/discovery/jobs", "/discovery/collector-status", "/analyses"):
                self.assertEqual((await client.get(path)).status_code, 401)
            self.assertEqual((await client.post("/discovery/jobs", json={"query": "test"})).status_code, 401)

    async def test_collection_preview_explicit_import_and_duplicate_retry(self):
        job = await self.start_job()
        self.assertEqual(job["status"], "succeeded")
        self.assertNotIn("result_path", job)
        self.assertFalse(job["complete_directory"])
        self.assertEqual((await self.client.get("/businesses")).json(), [])
        prefix = f'/discovery/jobs/{job["id"]}'
        preview = await self.client.post(prefix + "/preview")
        self.assertEqual(preview.json()["valid_rows"], 1)
        self.assertTrue(preview.json()["dry_run"])
        self.assertEqual((await self.client.get("/businesses")).json(), [])
        download = await self.client.get(prefix + "/csv")
        self.assertEqual(hashlib.sha256(download.content).hexdigest(), job["sha256"])
        sheet = await self.client.get(prefix + "/spreadsheet.csv")
        self.assertEqual(sheet.status_code, 200)
        self.assertEqual(list(csv.reader(io.StringIO(sheet.content.decode("utf-8-sig"))))[1][3],
                         "\t+12025550101")
        imported = (await self.client.post(prefix + "/import")).json()
        self.assertEqual(imported["imported_rows"], 1)
        duplicate = (await self.client.post(prefix + "/import")).json()
        self.assertEqual(duplicate["duplicate_rows"], 1)
        record = (await self.client.get("/businesses")).json()[0]
        self.assertEqual(record["provenance"]["collected_at"], job["collected_at"])
        self.assertEqual(record["source"], "csv")

    async def test_spreadsheet_copy_neutralizes_formula_cells_without_changing_raw_data(self):
        raw = b'title,address\n"=1+2"," @SUM(1,2)"\n'
        safe = spreadsheet_csv(raw)
        self.assertEqual(raw, b'title,address\n"=1+2"," @SUM(1,2)"\n')
        self.assertEqual(list(csv.reader(io.StringIO(safe.decode("utf-8-sig"))))[1],
                         ["\t=1+2", "\t @SUM(1,2)"])

    async def test_failures_do_not_leak_secrets_or_fabricate_leads(self):
        def broken(*args):
            raise RuntimeError("sensitive-fixture-token-provider-failure")
        self.service.collector = broken
        job = await self.start_job()
        self.assertEqual(job["status"], "failed")
        self.assertNotIn("sensitive-fixture-token", json.dumps(job))
        self.assertEqual((await self.client.get("/businesses")).json(), [])
        self.assertEqual((await self.client.post(f'/discovery/jobs/{job["id"]}/import')).status_code, 409)

    async def test_known_collector_prerequisite_failure_is_actionable(self):
        def missing(*args):
            raise CollectorUnavailable("The pinned browser image is not installed. Use CSV import.")
        self.service.collector = missing
        job = await self.start_job()
        self.assertEqual(job["status"], "failed")
        self.assertEqual(job["error"], "The pinned browser image is not installed. Use CSV import.")
        self.assertEqual((await self.client.get("/businesses")).json(), [])

    async def test_missing_or_modified_output_cannot_be_imported(self):
        job = await self.start_job()
        path = self.root / "scrapes/fixture-run/results.csv"
        path.write_bytes(path.read_bytes() + b"tampered")
        prefix = f'/discovery/jobs/{job["id"]}'
        for suffix in ("/preview", "/import"):
            self.assertEqual((await self.client.post(prefix + suffix)).status_code, 409)
        self.assertEqual((await self.client.get(prefix + "/csv")).status_code, 409)
        self.assertEqual((await self.client.get(prefix + "/spreadsheet.csv")).status_code, 409)
        path.unlink()
        self.assertEqual((await self.client.post(prefix + "/preview")).status_code, 409)
        self.assertEqual((await self.client.get("/businesses")).json(), [])

    async def test_unowned_result_path_is_rejected(self):
        job = await self.start_job()
        saved = await self.service.require(job["id"])
        saved["result_path"] = str(self.root / "outside/results.csv")
        await self.service.store.put("discovery_jobs", job["id"], saved)
        self.assertEqual((await self.client.post(f'/discovery/jobs/{job["id"]}/import')).status_code, 409)

    async def test_single_active_pilot_and_restart_recovery(self):
        gate = threading.Event()
        def slow(*args):
            gate.wait(5)
            return self.collector(*args)
        self.service.collector = slow
        first = await self.service.start(DiscoveryRequest(query="synthetic fixture only", limit=1))
        try:
            with self.assertRaises(AppError) as error:
                await self.service.start(DiscoveryRequest(query="another"))
            self.assertEqual(error.exception.code, "discovery_busy")
            self.assertEqual((await self.client.post(f'/discovery/jobs/{first["id"]}/preview')).status_code, 409)
        finally:
            gate.set()
            await self.service.close()
        await self.service.store.put("discovery_jobs", "stale", {"id": "stale", "status": "running", "query": "old", "limit": 1, "created_at": now().isoformat()})
        restarted = Discovery(self.service.store, self.root / "scrapes", self.collector)
        await restarted.recover()
        self.assertEqual((await restarted.require("stale"))["status"], "interrupted")
        self.assertEqual((await restarted.require(first["id"]))["status"], "succeeded")

    async def test_invalid_query_and_limit_do_not_create_jobs(self):
        for body in ({"query": " "}, {"query": "a\nb"}, {"query": "q", "limit": 0}, {"query": "q", "limit": 11}, {"query": "q", "limit": 1.5}):
            self.assertEqual((await self.client.post("/discovery/jobs", json=body)).status_code, 422)
        self.assertEqual((await self.client.get("/discovery/jobs")).json(), [])

    def test_static_booking_link_presence_or_absence_stays_unassessed(self):
        business = Business(name="Synthetic Test Spa", address="Fixture Address", website=None, phone=None, rating=None, review_count=None)
        for link in (True, False):
            website = WebsiteFindings(url="https://example.com", title="Fixture", emails=[], has_phone_link=False,
                                      has_booking_link=link, has_inquiry_form=False, excerpt="Fixture only")
            evidence = automatic_evidence(business, website)
            self.assertEqual(evidence[0].assessment, "unknown")
            result = score(evidence)
            self.assertEqual(result["evidence_coverage"], 0)
            self.assertEqual(result["components"]["D"], 0)
            self.assertEqual(result["automation_type"], "research_required")


if __name__ == "__main__":
    unittest.main()
