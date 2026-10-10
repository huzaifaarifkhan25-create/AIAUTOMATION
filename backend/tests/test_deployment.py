import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from app.main import create_app
from app.settings import Settings
from collect_leads import CollectorUnavailable, collect, collector_status, run_docker, run_local


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

    def test_container_entrypoint_rejects_development_mode(self):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / "serve.py")],
                                env={**os.environ, "APP_ENV": "development"},
                                capture_output=True, text=True, timeout=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires APP_ENV=production", result.stderr)

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
    def test_local_browser_status_does_not_need_docker(self):
        with patch("collect_leads.local_browser_paths", return_value=("node", "package", "edge")), \
             patch("collect_leads.shutil.which", return_value="certutil") as which:
            status = collector_status("local")
        self.assertTrue(status["ready"])
        self.assertEqual(status["code"], "ready")
        self.assertFalse(any(call.args[0] == "docker" for call in which.call_args_list))

    def test_collector_status_reports_missing_image_without_pulling(self):
        with patch("collect_leads.shutil.which", return_value="docker"), \
             patch("collect_leads.subprocess.run", side_effect=[
                 subprocess.CompletedProcess([], 0, "29.6.1", ""),
                 subprocess.CompletedProcess([], 1, "", "image missing")]) as run:
            status = collector_status("docker")
        self.assertEqual(status["code"], "image_missing")
        self.assertFalse(status["ready"])
        self.assertEqual([call.args[0][1:3] for call in run.call_args_list],
                         [["info", "--format"], ["image", "inspect"]])

    def test_collector_status_bounds_unresponsive_docker(self):
        with patch("collect_leads.shutil.which", return_value="docker"), \
             patch("collect_leads.subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 3)) as run:
            status = collector_status("docker")
        self.assertEqual(status["code"], "docker_unavailable")
        self.assertFalse(status["ready"])
        self.assertEqual(run.call_count, 1)

    @unittest.skipUnless(os.name == "nt", "Windows Docker host behavior")
    def test_windows_docker_collection_uses_container_trust_without_host_nss(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def fake_browser(output, run_id, script, limit):
                self.assertTrue((output / "home").is_dir())
                (output / "results.csv").write_text("title,address,phone\nSynthetic fixture spa,Fixture address,+12025550101\n")
                (output / "manifest.json").write_text(json.dumps({"tls_verification": True}))
                return subprocess.CompletedProcess([], 0, "", "")
            with patch("collect_leads.collector_status", return_value={"ready": True}), \
                 patch("collect_leads.httpx.Client") as client, patch("collect_leads.subprocess.run") as trust, \
                 patch("collect_leads.run_docker", side_effect=fake_browser) as browser:
                client.return_value.__enter__.return_value.get.return_value.status_code = 200
                path = collect("synthetic fixture only", root, 1, runtime="docker")
                self.assertTrue(path.exists())
                self.assertEqual(browser.call_count, 1)
                trust.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows Docker host behavior")
    def test_windows_docker_command_does_not_require_unix_uid(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"HTTPS_PROXY": "", "HTTP_PROXY": "", "ALL_PROXY": ""}), \
             patch("collect_leads.collector_status", return_value={"ready": True}), \
             patch("collect_leads.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")) as run:
            run_docker(Path(directory), "synthetic-run", Path(directory) / "collector.cjs", 1)
            command = run.call_args_list[0].args[0]
            self.assertEqual(command[:2], ["docker", "run"])
            self.assertNotIn("--user", command)
            self.assertIn("--entrypoint", command)

    def test_local_collection_uses_bundled_browser_without_launching_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def fake_browser(command, environment):
                output = Path(environment["MAPS_OUTPUT_DIR"])
                self.assertEqual(environment["HOME"], str(output / "home"))
                self.assertEqual(environment["MAPS_PLAYWRIGHT_PACKAGE"], "fixture-package")
                self.assertEqual(environment["HTTPS_PROXY"], "http://proxy.example:1234")
                self.assertNotIn("APP_API_TOKEN", environment)
                self.assertNotIn("RESEND_API_KEY", environment)
                if os.name == "nt":
                    self.assertEqual(environment["MAPS_BROWSER_EXECUTABLE"], "fixture-edge")
                    self.assertEqual(environment["MAPS_BROWSER_VISIBLE"], "1")
                    self.assertEqual(environment["SystemRoot"], os.environ["SystemRoot"])
                self.assertTrue((output / "queries.txt").exists())
                (output / "results.csv").write_text("title,address,phone\nSynthetic fixture spa,Fixture address,+12025550101\n")
                (output / "manifest.json").write_text(json.dumps({"tls_verification": True}))
                return subprocess.CompletedProcess(command, 0, "fixture browser result", "")
            with patch.dict(os.environ, {"HTTPS_PROXY": "http://proxy.example:1234",
                                      "APP_API_TOKEN": "synthetic-secret", "RESEND_API_KEY": "synthetic-secret"}), \
                 patch("collect_leads.collector_status", return_value={"ready": True}), \
                 patch("collect_leads.local_browser_paths", return_value=("fixture-node", "fixture-package", "fixture-edge" if os.name == "nt" else "")), \
                 patch("collect_leads.httpx.Client") as client, patch("collect_leads.subprocess.run") as trust, \
                 patch("collect_leads.run_local", side_effect=fake_browser) as browser, patch("collect_leads.run_docker") as docker:
                client.return_value.__enter__.return_value.get.return_value.status_code = 200
                path = collect("synthetic fixture only", root, 1, runtime="local")
                self.assertEqual(json.loads(path.with_name("manifest.json").read_text())["browser_runtime"], "local")
                self.assertEqual(browser.call_count, 1)
                docker.assert_not_called()
                self.assertTrue(all(call.args[0][0] == "certutil" for call in trust.call_args_list))

    def test_failed_preflight_creates_no_output_and_never_uses_fixture_fallback(self):
        with tempfile.TemporaryDirectory() as directory, patch("collect_leads.collector_status", return_value={"ready": True}), \
             patch("collect_leads.httpx.Client") as client, \
             patch("collect_leads.run_local") as browser:
            client.return_value.__enter__.return_value.get.return_value.status_code = 403
            with self.assertRaisesRegex(RuntimeError, "no scraper job was started"):
                collect("real search cannot run", Path(directory), 1, runtime="local")
            self.assertEqual(list(Path(directory).iterdir()), [])
            browser.assert_not_called()

    def test_known_local_browser_failures_have_safe_actionable_messages(self):
        cases = (("maps_results_unavailable", "readable listing cards"),
                 ("browser_closed", "page closed unexpectedly"),
                 ("maps_navigation_failed", "could not open the Maps search page"),
                 ("maps_place_page", "place or city page"))
        for code, expected in cases:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory, \
                 patch("collect_leads.collector_status", return_value={"ready": True}), \
                 patch("collect_leads.local_browser_paths", return_value=("fixture-node", "fixture-package", "fixture-edge")), \
                 patch("collect_leads.httpx.Client") as client, \
                 patch("collect_leads.run_local", return_value=subprocess.CompletedProcess([], 1, "", f"COLLECTOR_ERROR_CODE={code}\n")):
                client.return_value.__enter__.return_value.get.return_value.status_code = 200
                with self.assertRaises(CollectorUnavailable) as raised:
                    collect("synthetic fixture only", Path(directory), 1, runtime="local")
                self.assertIn(expected, str(raised.exception))
                self.assertIn("No leads were imported", str(raised.exception))
                self.assertFalse(any(Path(directory).rglob("results.csv")))

    def test_missing_browser_prevents_network_and_output(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch("collect_leads.collector_status", return_value={"ready": False, "message": "Browser unavailable."}), \
             patch("collect_leads.httpx.Client") as client:
            with self.assertRaisesRegex(RuntimeError, "Browser unavailable"):
                collect("synthetic fixture only", Path(directory), runtime="docker")
            client.assert_not_called()
            self.assertEqual(list(Path(directory).iterdir()), [])

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
