import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import httpx

from app.main import create_app
from app.settings import Settings

GOSOM = (
    'title,address,website,phone,review_rating,review_count,place_id,link\n'
    'Demo Med Spa,"10 Example Street, Demo City",demo.example.com,+12025550101,4.8,"1,234",demo-place-id,https://www.google.com/maps/place/demo\n'
    'Other Demo Spa,20 Example Street,,,,,,\n'
)


class CsvImportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(database_path=str(Path(self.temp.name) / "csv.sqlite3"))
        self.app = create_app(self.settings)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)

    async def upload(self, data=GOSOM, **params):
        return await self.client.post("/businesses/import-csv", content=data,
                                      headers={"Content-Type": "text/csv"}, params=params)

    async def test_preview_maps_gosom_headers_without_saving(self):
        response = await self.upload(source="gosom")
        self.assertEqual(response.status_code, 200, response.text)
        report = response.json()
        self.assertTrue(report["dry_run"])
        self.assertEqual(report["valid_rows"], 2)
        self.assertEqual(report["imported_rows"], 0)
        self.assertEqual(report["column_map"]["name"], "title")
        self.assertEqual(report["column_map"]["rating"], "review_rating")
        first = report["rows"][0]["business"]
        self.assertEqual(first["website"], "https://demo.example.com")
        self.assertEqual(first["review_count"], 1234)
        self.assertEqual(first["rating"], 4.8)
        self.assertEqual(first["address"], "10 Example Street, Demo City")
        self.assertIsNone(report["rows"][1]["business"]["phone"])
        self.assertEqual((await self.client.get("/businesses")).json(), [])

    async def test_import_persists_provenance_and_reimport_skips(self):
        timestamp = "2026-01-01T00:00:00Z"
        response = await self.upload(source="gosom", dry_run="false", collected_at=timestamp, file_name="folder/medspas.csv")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["imported_rows"], 2)
        record_id = response.json()["rows"][0]["business_id"]
        record = (await self.client.get(f"/businesses/{record_id}")).json()
        self.assertEqual(record["source"], "gosom")
        provenance = record["provenance"]
        self.assertEqual(provenance["file_name"], "medspas.csv")
        self.assertEqual(provenance["place_id"], "demo-place-id")
        self.assertEqual(provenance["collected_at"], timestamp)
        self.assertEqual(provenance["original_values"]["website"], "demo.example.com")
        self.assertEqual(provenance["original_values"]["review_count"], "1,234")
        retry = (await self.upload(source="gosom", dry_run="false")).json()
        self.assertEqual(retry["imported_rows"], 0)
        self.assertEqual(retry["duplicate_rows"], 2)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(self.settings)), base_url="http://testserver") as client:
            self.assertEqual((await client.get(f"/businesses/{record_id}")).json()["provenance"], provenance)

    async def test_stable_place_id_deduplicates_changed_name_address(self):
        first = await self.upload(dry_run="false")
        changed = GOSOM.replace("Demo Med Spa", "Renamed Demo Spa").replace("10 Example Street, Demo City", "Changed Address")
        response = await self.upload(changed, dry_run="false")
        self.assertEqual(response.json()["duplicate_rows"], 2)
        self.assertEqual(response.json()["rows"][0]["business_id"], first.json()["rows"][0]["business_id"])

    async def test_duplicate_rows_and_existing_manual_data_are_preserved(self):
        data = 'name,address,phone\nDemo Spa,Demo Address,+12025550101\n demo spa , demo address ,+12025550102\n'
        preview = await self.upload(data)
        self.assertEqual(preview.json()["valid_rows"], 1)
        self.assertEqual(preview.json()["duplicate_rows"], 1)
        manual = await self.client.post("/businesses", json={"name": "Demo Spa", "address": "Demo Address", "website": None, "phone": "+12025550103", "rating": None, "review_count": None})
        response = await self.upload(data, dry_run="false")
        self.assertEqual(response.json()["duplicate_rows"], 2)
        saved = await self.client.get(f'/businesses/{manual.json()["id"]}')
        self.assertEqual(saved.json()["business"]["phone"], "+12025550103")
        self.assertEqual(saved.json()["source"], "manual")

    async def test_custom_mapping_for_generated_extension_headers(self):
        data = 'qBF1Pd,W4Efsd,extra\nDemo Spa,Demo Address,ignored\n'
        self.assertEqual((await self.upload(data)).status_code, 422)
        import json
        mapping = json.dumps({"name": "qBF1Pd", "address": "W4Efsd"})
        response = await self.upload(data, source="instant_data_scraper", column_map=mapping)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["valid_rows"], 1)
        self.assertEqual(response.json()["ignored_columns"], ["extra"])
        self.assertIsNone(response.json()["rows"][0]["business"]["rating"])

    async def test_invalid_rows_reported_and_valid_rows_imported(self):
        data = 'name,address,rating,review_count,website\nGood Demo,Demo Address,4.5,10,https://example.com\nBad Rating,Demo Address,8,10,\n,Demo Address,4.5,10,\nBad Count,Demo Address,4.5,-1,\nBad URL,Demo Address,4.5,10,javascript:alert(1)\nExtra,Demo Address,4.5,10,,unexpected\n'
        response = await self.upload(data, dry_run="false")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["imported_rows"], 1)
        self.assertEqual(response.json()["invalid_rows"], 5)
        self.assertEqual(len((await self.client.get("/businesses")).json()), 1)

    async def test_bom_semicolon_csv_and_decimal_comma(self):
        data = '\ufeffBusiness Name;Full Address;Rating;Reviews\r\nDemo Spa;Demo Address;4,8;120 reviews\r\n'
        response = await self.upload(data)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["rows"][0]["business"]["rating"], 4.8)
        self.assertEqual(response.json()["rows"][0]["business"]["review_count"], 120)

    async def test_abbreviated_counts_remain_unknown_with_warning(self):
        response = await self.upload('name,address,review_count\nDemo Spa,Demo Address,1.2K\n')
        self.assertEqual(response.status_code, 200)
        row = response.json()["rows"][0]
        self.assertIsNone(row["business"]["review_count"])
        self.assertTrue(row["warnings"])

    async def test_malformed_files_and_ambiguous_headers_do_not_save(self):
        for data in ('', 'name,address\n', 'name,address\n"unterminated,Demo', 'name,name,address\nDemo,Demo,Address\n', 'name,title,address\nDemo,Demo,Address\n', 'name,address\nDemo,\x00\n'):
            with self.subTest(data=data):
                response = await self.upload(data, dry_run="false")
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual((await self.client.get("/businesses")).json(), [])
        self.assertEqual((await self.upload(b'\xff\xfe')).status_code, 422)

    async def test_unsupported_mapping_and_google_maps_website_rejected(self):
        for mapping in ('[]', '{"name":4}', '{"unknown":"title"}', '{"name":"absent"}', '{not-json}'):
            with self.subTest(mapping=mapping):
                self.assertEqual((await self.upload(column_map=mapping)).status_code, 422)
        response = await self.upload('name,address,website\nDemo,Demo Address,https://www.google.com/maps/place/demo\n')
        self.assertEqual(response.json()["invalid_rows"], 1)

    async def test_byte_and_row_limits_enforced_before_writes(self):
        response = await self.upload(b'x' * 2_000_001, dry_run="false")
        self.assertEqual(response.status_code, 413)
        data = 'name,address\n' + ''.join(f'Demo {i},Address {i}\n' for i in range(2001))
        self.assertEqual((await self.upload(data, dry_run="false")).status_code, 413)
        self.assertEqual((await self.client.get("/businesses")).json(), [])

    async def test_type_authentication_and_future_date(self):
        response = await self.client.post("/businesses/import-csv", json={"data": GOSOM})
        self.assertEqual(response.status_code, 415)
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        self.assertEqual((await self.upload(collected_at=future)).status_code, 422)
        app = create_app(Settings(database_path=self.settings.database_path, app_api_token="test-token"))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post("/businesses/import-csv", content=GOSOM, headers={"Content-Type": "text/csv"})
            self.assertEqual(response.status_code, 401)

    async def test_imported_business_enters_existing_analysis_pipeline(self):
        report = (await self.upload(dry_run="false")).json()
        bid = report["rows"][0]["business_id"]
        analysis = await self.client.post(f"/businesses/{bid}/analyze", json={})
        self.assertEqual(analysis.status_code, 201, analysis.text)
        self.assertEqual(analysis.json()["sales_score"], 15)
        self.assertTrue(analysis.json()["provisional"])

    async def test_chunked_upload_limit_and_partial_storage_failure(self):
        async def chunks():
            yield b'x' * 1_000_000
            yield b'x' * 1_000_001
        response = await self.client.post("/businesses/import-csv", content=chunks(), headers={"Content-Type": "text/csv"})
        self.assertEqual(response.status_code, 413)
        from app.errors import AppError
        original = self.app.state.store.reserve
        count = 0
        async def fail_second(*args):
            nonlocal count
            count += 1
            if count == 2:
                raise AppError(503, "storage_unavailable", "test failure")
            return await original(*args)
        with patch.object(self.app.state.store, "reserve", side_effect=fail_second):
            response = await self.upload(dry_run="false")
        self.assertEqual(response.status_code, 503)
        self.assertIn("after 1 rows saved", response.json()["error"]["message"])
        retry = await self.upload(dry_run="false")
        self.assertEqual(retry.json()["imported_rows"], 1)
        self.assertEqual(retry.json()["duplicate_rows"], 1)


class ScraperNetworkTests(unittest.TestCase):
    def test_blocked_managed_network_prevents_container_start(self):
        from collect_leads import collect
        with tempfile.TemporaryDirectory() as temp:
            with patch("collect_leads.httpx.Client", side_effect=httpx.ConnectError("blocked")), patch("collect_leads.subprocess.run") as run:
                with self.assertRaisesRegex(RuntimeError, "no scraper job was started"):
                    collect("med spas in Demo City", Path(temp))
                run.assert_not_called()
            self.assertEqual(list(Path(temp).iterdir()), [])
