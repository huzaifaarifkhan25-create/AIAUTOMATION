"""Exercise an isolated production container; --live adds one real Maps listing.

Never imports collected listings or contacts businesses. Uses an ephemeral token,
its own named volume, and loopback-only published port. Keeps a redacted report
and optional live source artifacts in .local/deployment; removes owned containers
and the isolated volume on exit. Does not publish the app.
"""
import argparse
import hashlib
import json
import os
import re
import secrets
import socket
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "aiautomation:local"
REDACT_VALUES = [os.environ[key] for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY") if os.environ.get(key)]


def redacted(value):
    for secret in REDACT_VALUES:
        value = value.replace(secret, "[redacted]")
    return re.sub(r"(?i)(https?|socks5h?)://[^/\s@]+@", r"\1://[redacted]@", value)


def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, check=False)
    if result.returncode:
        # Avoid copying Docker metadata, environment values, or logs into errors.
        raise RuntimeError("Docker operation failed: " + args[0] + "\n" + redacted(result.stderr[-4000:]))
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Collect one live New York med-spa listing, without importing it")
    args = parser.parse_args()
    run_id = "deployment-" + secrets.token_hex(6)
    name, volume = "aiautomation-" + run_id, "aiautomation-data-" + run_id
    out = ROOT / ".local/deployment" / run_id
    out.mkdir(parents=True)
    checks = []
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "image_id": docker("image", "inspect", IMAGE, "--format", "{{.Id}}"),
        "checks": checks, "publicly_deployed": False, "businesses_contacted": False, "live_requested": args.live}
    def checked(message):
        checks.append(message)
        print("PASS " + message, flush=True)
    token = secrets.token_urlsafe(48)
    REDACT_VALUES.append(token)
    try:
        # Startup guard is evaluated before any persistence service is created.
        missing = subprocess.run(["docker", "run", "--rm", "--network", "none", "--env", "APP_ALLOWED_HOSTS=workspace.example", IMAGE],
            capture_output=True, text=True, timeout=30)
        assert missing.returncode != 0 and "Production requires APP_API_TOKEN" in missing.stderr
        checked("Production startup fails without an access token")
        config = json.loads(docker("image", "inspect", IMAGE))[0]["Config"]
        assert config["User"] == "10001:10001"
        assert not any(item.split("=", 1)[0] in {"APP_API_TOKEN", "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"} for item in config["Env"])
        assert docker("run", "--rm", "--network", "none", "--entrypoint", "python3", IMAGE, "-c",
            "from pathlib import Path; import shutil; assert not shutil.which('docker'); assert not any(Path('/app').rglob('*.sqlite3')); assert not Path('/app/.env').exists(); assert not Path('/app/.local').exists(); assert not Path('/app/.git').exists(); print('clean')") == "clean"
        checked("Release image runs as a non-root user and contains no access token, local database, or Docker CLI")
        docker("volume", "create", volume)
        with tempfile.TemporaryDirectory(prefix="runtime-", dir=out) as folder:
            envfile = Path(folder) / "access.env"
            envfile.write_text("APP_API_TOKEN=" + token + "\nAPP_ALLOWED_HOSTS=workspace.example,127.0.0.1,localhost\n")
            envfile.chmod(0o600)
            browserfile = Path(folder) / "browser-test.cjs"
            browserfile.write_bytes((ROOT / "backend/tests/browser_deployment.cjs").read_bytes())
            browserfile.chmod(0o644)
            automationfile = Path(folder) / "automation-test.cjs"
            automationfile.write_bytes((ROOT / "backend/tests/browser_automation.cjs").read_bytes())
            automationfile.chmod(0o644)
            clientsfile = Path(folder) / "clients-test.cjs"
            clientsfile.write_bytes((ROOT / "backend/tests/browser_clients.cjs").read_bytes())
            clientsfile.chmod(0o644)
            command = ["run", "--detach", "--name", name, "--init", "--cpus=2", "--memory=2g", "--shm-size=512m",
                "--cap-drop=ALL", "--security-opt=no-new-privileges", "--read-only", "--tmpfs", "/tmp:rw,nosuid,size=256m",
                "--publish", "127.0.0.1:8002:8000", "--mount", f"type=volume,source={volume},target=/data",
                "--mount", f"type=bind,source={browserfile},target=/tmp/browser-test.cjs,readonly",
                "--mount", f"type=bind,source={automationfile},target=/tmp/automation-test.cjs,readonly",
                "--mount", f"type=bind,source={clientsfile},target=/tmp/clients-test.cjs,readonly",
                "--env-file", str(envfile)]
            if args.live:
                for variable in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
                    if os.environ.get(variable):
                        command.extend(["--env", variable])
                hosts = {urlsplit(os.environ[key]).hostname for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY") if os.environ.get(key)} - {None}
                for host in sorted(hosts):
                    command.extend(["--add-host", f"{host}:{socket.gethostbyname(host)}"])
                ca = Path(os.environ.get("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt"))
                command.extend(["--mount", f"type=bind,source={ca},target=/run/runtime-ca.pem,readonly", "--env", "SSL_CERT_FILE=/run/runtime-ca.pem",
                    "--mount", "type=bind,source=/usr/local/share/ca-certificates,target=/usr/local/share/ca-certificates,readonly"])
            command.append(IMAGE)
            docker(*command)
            with httpx.Client(base_url="http://127.0.0.1:8002", timeout=20, trust_env=False) as client:
                def wait_ready():
                    for _ in range(60):
                        try:
                            if client.get("/health").status_code == 200:
                                return
                        except httpx.HTTPError:
                            pass
                        time.sleep(0.25)
                    raise RuntimeError("Production container did not become healthy")
                wait_ready()
                assert client.get("/businesses").status_code == 401
                assert client.get("/businesses", headers={"Authorization": "Bearer wrong"}).status_code == 401
                assert client.get("/health", headers={"Host": "attacker.example"}).status_code == 400
                assert client.get("/docs").status_code == 404
                assert "script-src 'self'" in client.get("/app/").headers["content-security-policy"]
                client.headers["Authorization"] = "Bearer " + token
                assert client.get("/ready").json()["status"] == "ready"
                capability = client.get("/capabilities").json()
                assert capability["browser_collection_configured"] and capability["browser_collection_runtime"] == "local"
                checked("Running container enforces token, hostname, and production browser restrictions")
                csv = "title,address,phone,place_id\nSynthetic deployment fixture,Fixture address,+12025550101,synthetic-deployment-fixture\n"
                preview = client.post("/businesses/import-csv", content=csv, headers={"Content-Type": "text/csv"})
                assert preview.status_code == 200 and preview.json()["valid_rows"] == 1
                assert client.get("/businesses").json() == []
                imported = client.post("/businesses/import-csv?dry_run=false", content=csv, headers={"Content-Type": "text/csv"})
                assert imported.status_code == 200 and imported.json()["imported_rows"] == 1
                bid = client.get("/businesses").json()[0]["id"]
                evidence = [{"criterion": key, "assessment": "strong", "source": "manual_research", "detail": "Synthetic deployment fixture evidence only."}
                    for key in ("business_phone", "operational_scale")]
                analysis = client.post(f"/businesses/{bid}/analyze", json={"evidence": evidence})
                assert analysis.status_code == 201 and analysis.json()["need_score"] == 0
                contact = {"stage": "interested", "notes": "Synthetic restart verification; no business contacted."}
                assert client.patch(f"/businesses/{bid}/contact", json=contact).status_code == 200
                checked("CSV preview requires explicit import; saved public evidence leaves internal need unknown")
                docker("restart", "--time", "30", name)
                wait_ready()
                assert client.get("/businesses").json()[0]["id"] == bid
                assert client.get(f"/businesses/{bid}/contact").json()["notes"] == contact["notes"]
                assert client.get("/analyses").json()[0]["id"] == analysis.json()["id"]
                assert client.get(f"/businesses/{bid}/qualification").json()["need_status"] == "unconfirmed"
                checked("Businesses, evidence, and contact notes survive container restart on the named volume")
                print(docker("exec", name, "/opt/ms-playwright-go/node", "/tmp/browser-test.cjs"), flush=True)
                docker("cp", name + ":/data/verification", str(out / "browser"))
                report["browser"] = json.loads((out / "browser/browser-report.json").read_text())
                assert capability["workflow_runner_modes"] == ["sandbox"]
                synthetic = client.post("/businesses", json={"name": "Synthetic execution fixture", "address": "Fixture execution address",
                    "website": None, "phone": None, "rating": None, "review_count": None})
                assert synthetic.status_code == 201
                execution_bid = synthetic.json()["id"]
                confirmed = client.post(f"/businesses/{execution_bid}/analyze", json={"evidence": [
                    {"criterion": "appointment_reminders", "assessment": "strong", "source": "business_confirmation",
                     "detail": "Synthetic test confirmation only; no real business contacted."}]})
                assert confirmed.status_code == 201
                generated = client.post("/workflows", json={"analysis_id": confirmed.json()["id"]})
                assert generated.status_code == 201
                workflow_id = generated.json()["id"]
                run_body = {"mode": "sandbox", "confirm_sandbox": True, "idempotency_key": "synthetic-container-restart",
                    "event": {"contact_id": "synthetic-contact", "contact_permission": True},
                    "message_body": "Synthetic appointment reminder preview only.",
                    "scheduled_at": (datetime.now(timezone.utc) + timedelta(seconds=20)).isoformat()}
                started_run = client.post(f"/workflows/{workflow_id}/runs", json=run_body)
                assert started_run.status_code == 202
                run_id = started_run.json()["id"]
                duplicate = client.post(f"/workflows/{workflow_id}/runs", json=run_body)
                assert duplicate.status_code == 202 and duplicate.json()["id"] == run_id
                changed = client.post(f"/workflows/{workflow_id}/runs", json={**run_body, "message_body": "Changed synthetic text"})
                assert changed.status_code == 409
                for _ in range(40):
                    saved_run = client.get(f"/workflow-runs/{run_id}").json()
                    if saved_run["status"] == "waiting":
                        break
                    time.sleep(.1)
                assert saved_run["status"] == "waiting"
                assert client.get("/workflow-outbox").json() == []
                checked("Sandbox runner durably waits; duplicate events reuse one run and conflicting inputs are rejected")
                docker("restart", "--time", "30", name)
                wait_ready()
                while datetime.now(timezone.utc) < datetime.fromisoformat(run_body["scheduled_at"]):
                    assert client.get("/workflow-outbox").json() == []
                    time.sleep(.2)
                for _ in range(100):
                    saved_run = client.get(f"/workflow-runs/{run_id}").json()
                    if saved_run["status"] == "succeeded":
                        break
                    time.sleep(.1)
                assert saved_run["status"] == "succeeded" and saved_run["result"] == "sandbox_recorded"
                previews = client.get("/workflow-outbox", params={"run_id": run_id}).json()
                assert len(previews) == 1 and previews[0]["sent"] is False
                assert previews[0]["message_body"] == run_body["message_body"]
                assert len(client.get("/workflow-runs").json()) == 1
                assert client.post(f"/workflows/{workflow_id}/runs", json=run_body).json()["status"] == "succeeded"
                report["sandbox_execution"] = {"run_id": run_id, "status": saved_run["status"], "outbox_id": previews[0]["id"],
                    "preview_count": len(previews), "sent": False, "restart_recovery": True}
                checked("Scheduled sandbox run survives container restart and creates exactly one unsent preview at the due time")
                print(docker("exec", "--env", "AUTOMATION_TEST_URL=http://127.0.0.1:8000",
                    "--env", "AUTOMATION_TEST_OUT=/data/automation-verification", name,
                    "/opt/ms-playwright-go/node", "/tmp/automation-test.cjs"), flush=True)
                docker("cp", name + ":/data/automation-verification", str(out / "automation-browser"))
                report["automation_browser"] = json.loads((out / "automation-browser/automation-report.json").read_text())
                appointments_before = client.get("/appointments").json()
                outbox_before = client.get("/workflow-outbox").json()
                assert len(appointments_before) == 2 and all(item["sent"] is False for item in outbox_before)
                docker("restart", "--time", "30", name)
                wait_ready()
                assert client.get("/appointments").json() == appointments_before
                assert client.get("/workflow-outbox").json() == outbox_before
                checked("Appointment events, cancellations and unsent previews survive production container restart")
                print(docker("exec", "--env", "CLIENT_TEST_URL=http://127.0.0.1:8000",
                    "--env", "CLIENT_TEST_OUT=/data/client-browser-verification", name,
                    "/opt/ms-playwright-go/node", "/tmp/clients-test.cjs"), flush=True)
                docker("cp", name + ":/data/client-browser-verification", str(out / "client-browser"))
                report["client_browser"] = json.loads((out / "client-browser/client-browser-report.json").read_text())
                client_demo = json.loads(docker("exec", name, "python3", "/app/backend/client_demo.py"))
                assert client_demo["synthetic"] and client_demo["sent"] is False and client_demo["scheduler_running"]
                assert client_demo["run_status"] == "succeeded" and client_demo["handoff_format"] == "medspa-client-handoff-v1"
                report["client_demo"] = client_demo
                checked("Fictional client onboarding, CRM task history, reviewed activation and managed reminder handoff work end to end")
                # Running the same explicit demo again reuses its client and deployment.
                repeated = json.loads(docker("exec", name, "python3", "/app/backend/client_demo.py"))
                assert repeated["client_id"] == client_demo["client_id"] and repeated["deployment_id"] == client_demo["deployment_id"]
                persisted = {path:client.get(path).json() for path in ("/clients", "/deployments", "/tasks", "/appointments", "/workflow-outbox")}
                docker("restart", "--time", "30", name)
                wait_ready()
                assert all(client.get(path).json() == before for path,before in persisted.items())
                assert client.get("/operations/summary").json()["scheduler_running"] is True
                assert client.get(f"/clients/{client_demo['client_id']}/handoff").json()["client"]["is_demo"] is True
                checked("Repeated client demo reuses onboarding/deployment; clients, CRM, appointments and unsent previews survive production restart")
                if args.live:
                    businesses_before_live = len(client.get("/businesses").json())
                    started = client.post("/discovery/jobs", json={"query": "med spas in New York NY", "limit": 1})
                    assert started.status_code == 202
                    job_id = started.json()["id"]
                    deadline = time.monotonic() + 330
                    while time.monotonic() < deadline:
                        job = client.get("/discovery/jobs/" + job_id).json()
                        if job["status"] not in {"queued", "running"}:
                            break
                        time.sleep(1)
                    assert job["status"] == "succeeded", "Live collection failed: " + str(job.get("error", job["status"]))
                    preview = client.post(f"/discovery/jobs/{job_id}/preview")
                    assert preview.status_code == 200 and preview.json()["valid_rows"] == 1
                    csv_response = client.get(f"/discovery/jobs/{job_id}/csv")
                    assert csv_response.status_code == 200 and hashlib.sha256(csv_response.content).hexdigest() == job["sha256"]
                    assert len(client.get("/businesses").json()) == businesses_before_live
                    docker("cp", name + ":/data/scrapes", str(out / "scrapes"))
                    manifests = list((out / "scrapes").glob("*/manifest.json"))
                    assert len(manifests) == 1
                    manifest = json.loads(manifests[0].read_text())
                    assert manifest["tls_verification"] is True and manifest["browser_runtime"] == "local"
                    assert manifest["collected_count"] == 1 and manifest["records"][0]["link"].startswith("https://www.google.com/maps/place/")
                    report["live_job"] = job
                    checked("Real Google Maps listing collected inside the app container; checksum verified and no automatic import")
                    docker("restart", "--time", "30", name)
                    wait_ready()
                    assert client.get(f"/discovery/jobs/{job_id}/csv").content == csv_response.content
                    checked("Live job status and verified source CSV survive container restart")
                # Execute the actual image health check, including its configured Host header.
                health = config["Healthcheck"]["Test"]
                assert health[0] == "CMD"
                docker("exec", "--env", "HTTP_PROXY=http://127.0.0.1:1", "--env", "HTTPS_PROXY=http://127.0.0.1:1", "--env", "NO_PROXY=", name, *health[1:])
                checked("Image health check succeeds with an explicit deployment hostname")
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error).replace(token, "[redacted]")
        raise
    finally:
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        subprocess.run(["docker", "rm", "--force", "--volumes", name], capture_output=True)
        subprocess.run(["docker", "volume", "rm", volume], capture_output=True)
        print("Verification report: " + str(out / "report.json"), flush=True)


if __name__ == "__main__":
    main()
