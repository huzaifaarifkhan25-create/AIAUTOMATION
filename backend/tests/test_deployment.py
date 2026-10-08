import json
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from app.main import create_app
from app.settings import Settings
from collect_leads import collect, run_local


TEST_TOKEN = "synthetic-deployment-access-token-only-0123456789"


class ProductionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Settings(app_env="production", app_api_token=TEST_TOKEN,
            app_allowed_hosts=("workspace.example",), database_path=str(Path(self.temp.name) / "db.sqlite3"))
        self.app = create_app(self.settings)
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="https://workspace.example")
        self.addAsyncCleanup(self.client.aclose)

    def test_invalid_production_configuration_fails_before_creating_database(self):
        for change in ({"app_api_token": ""}, {"app_api_token": "short"}, {"app_api_token": " " * 32},
                       {"app_api_token": "a" * 31 + "\n"}, {"app_allowed_hosts": ()},
                       {"app_allowed_hosts": ("*",)}, {"app_allowed_hosts": ("https://workspace.example",)},
                       {"app_allowed_hosts": ("workspace.example:8000",)}, {"app_allowed_hosts": ("a" * 64 + ".example",)},
                       {"browser_runtime": "invalid"}, {"app_env": "invalid"}):
            with self.subTest(fields=list(change)):
                unused = Path(self.temp.name) / "invalid-config.sqlite3"
                settings = replace(self.settings, database_path=str(unused), **change)
                with self.assertRaises(ValueError) as raised:
                    create_app(settings)
                self.assertNotIn(TEST_TOKEN, str(raised.exception))
                self.assertFalse(unused.exists())

    async def test_shell_and_health_are_public_but_all_data_routes_require_token(self):
        self.assertEqual((await self.client.get("/health")).json(), {"status": "ok"})
        shell = await self.client.get("/app/")
        self.assertEqual(shell.status_code, 200)
        self.assertNotIn(TEST_TOKEN, shell.text)
        self.assertIn("script-src 'self'", shell.headers["content-security-policy"])
        for path in ("/ready", "/capabilities", "/businesses", "/analyses", "/prospects", "/opportunities",
                     "/discovery/jobs", "/calls", "/workflows"):
            with self.subTest(path=path):
                denied = await self.client.get(path)
                self.assertEqual(denied.status_code, 401)
                self.assertEqual(denied.headers["www-authenticate"], "Bearer")
                self.assertEqual(denied.headers["cache-control"], "no-store")
                wrong = await self.client.get(path, headers={"Authorization": "Bearer wrong"})
                self.assertEqual(wrong.status_code, 401)
                allowed = await self.client.get(path, headers={"Authorization": "Bearer " + TEST_TOKEN})
                self.assertEqual(allowed.status_code, 200, allowed.text)
                self.assertNotIn(TEST_TOKEN, allowed.text)

    async def test_production_rejects_other_hosts_and_disables_api_documentation(self):
        for host in ("attacker.example", "workspace.example.attacker.example"):
            response = await self.client.get("/health", headers={"Host": host})
            self.assertEqual(response.status_code, 400)
        for path in ("/docs", "/redoc", "/openapi.json"):
            self.assertEqual((await self.client.get(path)).status_code, 404)
        response = await self.client.get("/health")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")


class LocalCollectorTests(unittest.TestCase):
    def test_local_collection_uses_bundled_browser_without_launching_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def fake_browser(command, environment):
                output = Path(environment["MAPS_OUTPUT_DIR"])
                self.assertEqual(environment["HOME"], str(output / "home"))
                self.assertTrue((output / "queries.txt").exists())
                (output / "results.csv").write_text("title,address,phone\nSynthetic fixture spa,Fixture address,+12025550101\n")
                (output / "manifest.json").write_text(json.dumps({"tls_verification": True}))
                return subprocess.CompletedProcess(command, 0, "fixture browser result", "")
            with patch("collect_leads.httpx.Client") as client, patch("collect_leads.subprocess.run") as trust, \
                 patch("collect_leads.run_local", side_effect=fake_browser) as browser, patch("collect_leads.run_docker") as docker:
                client.return_value.__enter__.return_value.get.return_value.status_code = 200
                path = collect("synthetic fixture only", root, 1, runtime="local")
                self.assertEqual(json.loads(path.with_name("manifest.json").read_text())["browser_runtime"], "local")
                self.assertEqual(browser.call_count, 1)
                docker.assert_not_called()
                self.assertTrue(all(call.args[0][0] == "certutil" for call in trust.call_args_list))

    def test_failed_preflight_creates_no_output_and_never_uses_fixture_fallback(self):
        with tempfile.TemporaryDirectory() as directory, patch("collect_leads.httpx.Client") as client, \
             patch("collect_leads.run_local") as browser:
            client.return_value.__enter__.return_value.get.return_value.status_code = 403
            with self.assertRaisesRegex(RuntimeError, "no scraper job was started"):
                collect("real search cannot run", Path(directory), 1, runtime="local")
            self.assertEqual(list(Path(directory).iterdir()), [])
            browser.assert_not_called()

    def test_local_browser_timeout_terminates_only_its_owned_process(self):
        for needs_kill in (False, True):
            with self.subTest(needs_kill=needs_kill), patch("collect_leads.subprocess.Popen") as popen:
                process = MagicMock()
                popen.return_value.__enter__.return_value = process
                timeout = subprocess.TimeoutExpired(["owned-browser"], 300)
                process.communicate.side_effect = [timeout, timeout, ("", "")] if needs_kill else [timeout, ("", "")]
                with self.assertRaisesRegex(RuntimeError, "5-minute pilot limit"):
                    run_local(["owned-browser"], {})
                process.terminate.assert_called_once()
                self.assertEqual(process.kill.call_count, int(needs_kill))


if __name__ == "__main__":
    unittest.main()
