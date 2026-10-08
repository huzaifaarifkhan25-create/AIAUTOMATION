import gzip
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app.database.store import SupabaseStore
from app.errors import AppError
from app.main import create_app
from app.models.business import BusinessSearchRequest
from app.models.workflow import Evidence
from app.services.gateway import Gateway
from app.services.scoring import score
from app.settings import Settings


class IntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_places_normalizes_missing_fields_and_limits(self):
        seen = []

        def provider(request):
            seen.append(request)
            self.assertEqual(request.url.host, "places.googleapis.com")
            self.assertEqual(json.loads(request.content)["textQuery"], "med spa in Demo City")
            self.assertEqual(json.loads(request.content)["pageSize"], 1)
            self.assertIn("places.websiteUri", request.headers["X-Goog-FieldMask"])
            return httpx.Response(200, json={"places": [{"displayName": {"text": "Test Med Spa"}, "formattedAddress": "Demo City"}]})

        gateway = Gateway(Settings(google_places_api_key="test-key"), httpx.MockTransport(provider))
        result = await gateway.discover(BusinessSearchRequest(industry="med spa", location="Demo City", limit=1))
        self.assertEqual(len(seen), 1)
        self.assertEqual(result[0].name, "Test Med Spa")
        self.assertIsNone(result[0].phone)
        self.assertIsNone(result[0].rating)

    async def test_provider_errors_do_not_expose_credentials_or_bodies(self):
        gateway = Gateway(Settings(google_places_api_key="test-only-secret"), httpx.MockTransport(
            lambda request: httpx.Response(403, json={"secret": "test-only-secret", "provider_internal": "sensitive"})))
        with self.assertRaises(AppError) as caught:
            await gateway.discover(BusinessSearchRequest(industry="med spa", location="Demo City"))
        self.assertEqual(caught.exception.status_code, 502)
        self.assertNotIn("test-only-secret", caught.exception.message)
        self.assertNotIn("sensitive", caught.exception.message)

    async def test_malformed_discovery_and_ai_responses_rejected(self):
        gateway = Gateway(Settings(google_places_api_key="test-key", llm_api_key="test-key"), httpx.MockTransport(
            lambda request: httpx.Response(200, json={"places": [None]})))
        with self.assertRaises(AppError):
            await gateway.discover(BusinessSearchRequest(industry="med spa", location="Demo City"))
        from app.models.business import Business
        business = Business(name="Test", website=None, phone=None, address="Demo", rating=None, review_count=None)
        with self.assertRaises(AppError):
            await gateway.summarize(business, [], None)

    async def test_ai_summary_is_structured_and_cannot_change_scores(self):
        from app.models.business import Business

        def provider(request):
            body = json.loads(request.content)
            self.assertEqual(body["response_format"]["type"], "json_schema")
            self.assertIn("untrusted", body["messages"][0]["content"])
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps({"summary": "Insufficient evidence.", "suggested_questions": ["How are appointments managed?"]})}}]})

        gateway = Gateway(Settings(llm_api_key="test-key"), httpx.MockTransport(provider))
        business = Business(name="Test", website=None, phone=None, address="Demo", rating=None, review_count=None)
        narrative = await gateway.summarize(business, [], None)
        self.assertEqual(narrative.summary, "Insufficient evidence.")
        self.assertEqual(score([])["total_score"], 0)
        with tempfile.TemporaryDirectory() as temp:
            settings = Settings(database_path=str(Path(temp) / "db.sqlite3"), llm_api_key="test-key")
            app = create_app(settings, gateway=Gateway(settings, httpx.MockTransport(provider)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
                saved = await client.post("/businesses", json=business.model_dump())
                response = await client.post(f'/businesses/{saved.json()["id"]}/analyze', json={"use_ai": True})
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(response.json()["mode"], "rules_with_ai_summary")
                self.assertEqual(response.json()["total_score"], 0)
                self.assertEqual(response.json()["summary"], "Insufficient evidence.")

    async def test_website_findings_and_script_exclusion(self):
        html = '<title>Demo Clinic</title><script>ignore me</script><a href="mailto:hello@example.com">Email</a><a href="tel:+12025550101">Call</a><a href="/book">Book</a><form><textarea name="message"></textarea></form>'
        gateway = Gateway(Settings(website_allowed_hosts=("example.com",)), httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text=html)))
        public_dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with patch("app.services.gateway.socket.getaddrinfo", return_value=public_dns):
            result = await gateway.analyze_website("https://example.com/")
        self.assertEqual(result.title, "Demo Clinic")
        self.assertEqual(result.emails, ["hello@example.com"])
        self.assertTrue(result.has_booking_link)
        self.assertTrue(result.has_phone_link)
        self.assertTrue(result.has_inquiry_form)
        self.assertNotIn("ignore me", result.excerpt)

    async def test_website_private_destinations_redirects_and_size_rejected(self):
        requested = []

        def provider(request):
            requested.append(request)
            return httpx.Response(302, headers={"Location": "http://127.0.0.1/"})

        gateway = Gateway(Settings(website_allowed_hosts=("example.com",)), httpx.MockTransport(provider))
        for url in ("http://example.com", "https://127.0.0.1", "https://user:pass@example.com", "https://example.com:444", "https://other.example.com"):
            with self.subTest(url=url), self.assertRaises(AppError):
                await gateway.analyze_website(url)
        self.assertEqual(requested, [])
        private_dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]
        with patch("app.services.gateway.socket.getaddrinfo", return_value=private_dns), self.assertRaises(AppError):
            await gateway.analyze_website("https://example.com")
        self.assertEqual(requested, [])
        public_dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with patch("app.services.gateway.socket.getaddrinfo", return_value=public_dns), self.assertRaises(AppError):
            await gateway.analyze_website("https://example.com")
        self.assertEqual(len(requested), 1)
        large = Gateway(Settings(), httpx.MockTransport(lambda request: httpx.Response(200, content=b'x' * 1_000_001)))
        with self.assertRaises(AppError) as caught:
            await large.request("GET", "https://example.com")
        self.assertEqual(caught.exception.code, "response_too_large")

    async def test_social_links_are_not_booking_evidence(self):
        gateway = Gateway(Settings(website_allowed_hosts=("example.com",)), httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text='<a href="https://facebook.com/demo">Facebook</a><a href="javascript:book()">Action</a><a href="http://[">Malformed</a>')))
        public_dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with patch("app.services.gateway.socket.getaddrinfo", return_value=public_dns):
            website = await gateway.analyze_website("https://example.com")
        self.assertFalse(website.has_booking_link)

    async def test_compressed_website_body_is_decoded_once(self):
        html = b'<title>Compressed Clinic</title><a href="/book">Book</a>'
        gateway = Gateway(Settings(website_allowed_hosts=("example.com",)), httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "text/html", "content-encoding": "gzip"},
                                          stream=httpx.ByteStream(gzip.compress(html)))))
        dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with patch("app.services.gateway.socket.getaddrinfo", return_value=dns):
            findings = await gateway.analyze_website("https://example.com")
        self.assertEqual(findings.title, "Compressed Clinic")
        self.assertTrue(findings.has_booking_link)

    async def test_booking_button_text_recognizes_external_widget_without_false_gaps(self):
        html = ('<a href="https://widgets.example.com/widget/abc"><span>Book Now</span></a>'
                '<a href="javascript:run()">Book Now</a><a href="#">Book Now</a>')
        gateway = Gateway(Settings(website_allowed_hosts=("example.com",)), httpx.MockTransport(
            lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text=html)))
        dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with patch("app.services.gateway.socket.getaddrinfo", return_value=dns):
            result = await gateway.analyze_website("https://example.com/")
        self.assertTrue(result.has_booking_link)
        from app.services.gateway import is_booking_link
        self.assertFalse(is_booking_link("javascript:run()", "Book Now"))
        self.assertFalse(is_booking_link("#", "Book Now"))
        self.assertFalse(is_booking_link("https://bookstore.example.com/novel", "Read our book"))

    async def test_https_dns_fallback_fetches_only_after_public_answers(self):
        seen = []
        def provider(request):
            seen.append(request.url)
            if request.url.host == "dns.google":
                self.assertEqual(request.url.params["name"], "example.com")
                answers = [{"type": 1, "data": "93.184.216.34"}] if request.url.params["type"] == "A" else []
                return httpx.Response(200, json={"Status": 0, "Answer": answers})
            return httpx.Response(200, headers={"content-type": "text/html"}, text="<title>Clinic</title>")
        gateway = Gateway(Settings(website_allowed_hosts=("example.com",), website_dns_over_https=True), httpx.MockTransport(provider))
        with patch("app.services.gateway.socket.getaddrinfo", side_effect=socket.gaierror("unavailable")):
            result = await gateway.analyze_website("https://example.com")
        self.assertEqual(result.title, "Clinic")
        self.assertEqual([url.host for url in seen].count("dns.google"), 2)
        self.assertEqual(seen[-1].host, "example.com")

    async def test_https_dns_private_empty_and_malformed_answers_fail_closed(self):
        for answer in ([{"type": 1, "data": "127.0.0.1"}], [{"type": 28, "data": "::1"}],
                       [{"type": 1, "data": "invalid"}], [], None):
            seen = []
            def provider(request):
                seen.append(request.url.host)
                return httpx.Response(200, json={"Status": 0, "Answer": answer})
            gateway = Gateway(Settings(website_allowed_hosts=("example.com",), website_dns_over_https=True), httpx.MockTransport(provider))
            with self.subTest(answer=answer), patch("app.services.gateway.socket.getaddrinfo", side_effect=socket.gaierror("unavailable")), self.assertRaises(AppError):
                await gateway.analyze_website("https://example.com")
            self.assertNotIn("example.com", seen)

    async def test_https_dns_network_failure_is_explicit_and_never_fetches_website(self):
        seen = []
        def provider(request):
            seen.append(request.url.host)
            raise httpx.ConnectError("resolver blocked")
        gateway = Gateway(Settings(website_allowed_hosts=("example.com",), website_dns_over_https=True), httpx.MockTransport(provider))
        with patch("app.services.gateway.socket.getaddrinfo", side_effect=socket.gaierror("unavailable")), self.assertRaises(AppError) as caught:
            await gateway.analyze_website("https://example.com")
        self.assertEqual(caught.exception.code, "website_dns_unavailable")
        self.assertNotIn("example.com", seen)

    async def test_https_dns_does_not_override_private_local_dns_or_disabled_mode(self):
        seen = []
        gateway = Gateway(Settings(website_allowed_hosts=("example.com",), website_dns_over_https=True), httpx.MockTransport(
            lambda request: seen.append(request) or httpx.Response(200)))
        private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]
        with patch("app.services.gateway.socket.getaddrinfo", return_value=private), self.assertRaises(AppError):
            await gateway.analyze_website("https://example.com")
        gateway.settings = Settings(website_allowed_hosts=("example.com",))
        with patch("app.services.gateway.socket.getaddrinfo", side_effect=socket.gaierror("unavailable")), self.assertRaises(AppError):
            await gateway.analyze_website("https://example.com")
        self.assertEqual(seen, [])

    async def test_optional_redirects_validate_every_destination_and_stop_loops(self):
        dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        for location in ("https://untrusted.example.com/", "http://127.0.0.1/", "https://["):
            seen = []
            gateway = Gateway(Settings(website_allowed_hosts=("example.com",), website_follow_redirects=True), httpx.MockTransport(
                lambda request: seen.append(request.url) or httpx.Response(302, headers={"location": location})))
            with self.subTest(location=location), patch("app.services.gateway.socket.getaddrinfo", return_value=dns), self.assertRaises(AppError):
                await gateway.analyze_website("https://example.com")
            self.assertEqual(len(seen), 1)
        gateway = Gateway(Settings(website_allowed_hosts=("example.com",), website_follow_redirects=True), httpx.MockTransport(
            lambda request: httpx.Response(302, headers={"location": "/"})))
        with patch("app.services.gateway.socket.getaddrinfo", return_value=dns), self.assertRaises(AppError) as caught:
            await gateway.analyze_website("https://example.com/")
        self.assertEqual(caught.exception.code, "website_redirect_loop")

    async def test_optional_same_host_canonical_redirect_retains_final_url(self):
        def provider(request):
            if request.url.path == "/clinic/":
                return httpx.Response(308, headers={"location": "/clinic"})
            return httpx.Response(200, headers={"content-type": "text/html"}, text="<title>Clinic</title>")
        gateway = Gateway(Settings(website_allowed_hosts=("example.com",), website_follow_redirects=True), httpx.MockTransport(provider))
        dns = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with patch("app.services.gateway.socket.getaddrinfo", return_value=dns) as resolve:
            findings = await gateway.analyze_website("https://example.com/clinic/")
        self.assertEqual(findings.url, "https://example.com/clinic")
        self.assertEqual(resolve.call_count, 2)

    async def test_supabase_storage_contract_and_conflict_reservation(self):
        data = {}

        def provider(request):
            self.assertEqual(request.url.path, "/rest/v1/backend_records")
            self.assertEqual(request.headers["apikey"], "test-key")
            if request.method == "POST":
                row = json.loads(request.content)
                key = (row["kind"], row["id"])
                if "on_conflict" not in request.url.params and key in data:
                    return httpx.Response(409, json={})
                data[key] = row
                return httpx.Response(201, json=[row])
            kind = request.url.params["kind"][3:]
            record_id = request.url.params.get("id", "eq.")[3:]
            rows = [r for (k, i), r in data.items() if k == kind and (not record_id or record_id == i)]
            return httpx.Response(200, json=[{"payload": r["payload"]} for r in rows])

        settings = Settings(persistence_backend="supabase", supabase_url="https://test.supabase.co", supabase_key="test-key")
        store = SupabaseStore(settings, Gateway(settings, httpx.MockTransport(provider)))
        await store.put("businesses", "id", {"name": "Test"})
        self.assertEqual(await store.get("businesses", "id"), {"name": "Test"})
        self.assertEqual(await store.list("businesses"), [{"name": "Test"}])
        self.assertTrue(await store.reserve("calls", "key", {"status": "pending"}))
        self.assertFalse(await store.reserve("calls", "key", {"status": "pending"}))

    async def test_supabase_missing_configuration_and_invalid_payload(self):
        with self.assertRaises(AppError) as caught:
            await SupabaseStore(Settings(), Gateway(Settings())).list("businesses")
        self.assertEqual(caught.exception.status_code, 503)
        settings = Settings(supabase_url="https://test.supabase.co", supabase_key="test-key")
        gateway = Gateway(settings, httpx.MockTransport(lambda request: httpx.Response(200, json=[{}])))
        with self.assertRaises(AppError) as caught:
            await SupabaseStore(settings, gateway).get("businesses", "id")
        self.assertEqual(caught.exception.status_code, 502)

    async def test_network_timeouts_are_explicit(self):
        def provider(request):
            raise httpx.ReadTimeout("test-only failure")
        gateway = Gateway(Settings(), httpx.MockTransport(provider))
        with self.assertRaises(AppError) as caught:
            await gateway.request("GET", "https://example.com")
        self.assertEqual(caught.exception.code, "provider_unavailable")

    async def test_human_dialer_confirmation_opt_out_and_idempotency(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = Settings(
                database_path=str(Path(temp) / "db.sqlite3"), app_api_token="test-token",
                enable_outbound_calls=True, twilio_account_sid="AC" + "1" * 32,
                twilio_auth_token="test-key", twilio_from_number="+12025550101",
                sales_agent_number="+12025550102",
            )
            sent = []

            def provider(request):
                sent.append(request)
                self.assertEqual(request.url.host, "api.twilio.com")
                self.assertIn(b'To=%2B12025550102', request.content)
                self.assertIn(b'%2B12025550103', request.content)
                return httpx.Response(201, json={"sid": "CA" + "2" * 32})

            gateway = Gateway(settings, httpx.MockTransport(provider))
            app = create_app(settings, gateway=gateway)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", headers={"Authorization": "Bearer test-token"}) as client:
                response = await client.post("/businesses", json={"name": "Test Provider Fixture", "website": None, "phone": "+1 (202) 555-0103", "address": "Demo", "rating": None, "review_count": None})
                bid = response.json()["id"]
                payload = {"idempotency_key": "same-call-key", "confirm_outbound_call": False}
                self.assertEqual((await client.post(f"/businesses/{bid}/calls", json=payload)).status_code, 422)
                payload["confirm_outbound_call"] = True
                for _ in range(2):
                    result = await client.post(f"/businesses/{bid}/calls", json=payload)
                    self.assertEqual(result.status_code, 202, result.text)
                    self.assertEqual(result.json()["status"], "submitted")
                self.assertEqual(len(sent), 1)
                await client.patch(f"/businesses/{bid}/contact", json={"stage": "do_not_contact"})
                payload["idempotency_key"] = "other-call-key"
                self.assertEqual((await client.post(f"/businesses/{bid}/calls", json=payload)).status_code, 409)
                self.assertEqual(len(sent), 1)

    async def test_uncertain_call_failure_cannot_trigger_automatic_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = Settings(database_path=str(Path(temp) / "db.sqlite3"), app_api_token="test-token",
                                enable_outbound_calls=True, twilio_account_sid="AC" + "1" * 32,
                                twilio_auth_token="test-key", twilio_from_number="+12025550101", sales_agent_number="+12025550102")
            sent = []

            def provider(request):
                sent.append(request)
                raise httpx.ReadTimeout("uncertain provider result")

            app = create_app(settings, gateway=Gateway(settings, httpx.MockTransport(provider)))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver", headers={"Authorization": "Bearer test-token"}) as client:
                response = await client.post("/businesses", json={"name": "Test", "website": None, "phone": "+12025550103", "address": "Demo", "rating": None, "review_count": None})
                bid = response.json()["id"]
                body = {"idempotency_key": "uncertain-call", "confirm_outbound_call": True}
                self.assertEqual((await client.post(f"/businesses/{bid}/calls", json=body)).status_code, 502)
                self.assertEqual((await client.post(f"/businesses/{bid}/calls", json=body)).status_code, 409)
                self.assertEqual(len(sent), 1)
