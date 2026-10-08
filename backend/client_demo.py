"""Explicit fictional client handoff demo against a local SQLite API; never sends."""
import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from uuid import uuid4

import httpx


def run(base_url):
    parsed = urlsplit(base_url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.scheme != "http":
        raise ValueError("The fictional demo requires a local HTTP server")
    headers = {}
    if os.getenv("APP_API_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["APP_API_TOKEN"]
    with httpx.Client(base_url=base_url, headers=headers, timeout=15, trust_env=False) as client:
        def request(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            if response.status_code >= 400:
                raise RuntimeError(f"Demo request failed: {method} {path}, HTTP {response.status_code}")
            return response.json()
        ready = request("GET", "/ready")
        if ready != {"status": "ready", "persistence": "sqlite"}:
            raise ValueError("The fictional demo requires ready local SQLite storage")
        scaffold = request("POST", "/demo/reminder-workflow")
        business, workflow = scaffold["business"], scaffold["workflow"]
        assert business["source"] == "mock" and scaffold["synthetic"]
        bid = business["id"]
        draft = request("GET", f"/businesses/{bid}/outreach-draft", params={"analysis_id": workflow["analysis_id"]})
        assert draft["sent"] is False
        request("PATCH", f"/businesses/{bid}/contact", json={"stage": "won", "notes": "Fictional demo approval only; no business was contacted."})
        key = uuid4().hex
        stamp = datetime.now(timezone.utc)
        task = request("POST", f"/businesses/{bid}/tasks", json={"idempotency_key": "demo-task:" + key,
            "title": "Review fictional client handoff", "due_at": (stamp + timedelta(hours=1)).isoformat()})
        profiles = request("GET", "/clients", params={"limit":500})
        profile = next((r for r in profiles if r["business_id"] == bid and r["status"] != "archived"), None)
        if not profile:
            profile = request("POST", "/clients", json={"business_id":bid, "idempotency_key":"demo-client:"+key,
                "contact_name":"Fictional demo operator", "timezone":"Asia/Karachi", "contact_email":None,
                "approval_reference":"Synthetic hackathon approval only, not actual business authorization.",
                "confirm_business_authorization":True})
        request("POST", "/clients/"+profile["id"]+"/activate", json={"confirm_authorization":True})
        # Reuse a successful proof. A new attempt has its own explicit event key.
        proofs = request("GET", "/workflow-runs", params={"workflow_id":workflow["id"], "limit":500})
        proof = next((r for r in proofs if r["mode"]=="sandbox" and r["status"]=="succeeded"), None)
        def wait_succeeded(run_id):
            deadline = time.monotonic()+20
            while time.monotonic() < deadline:
                saved = request("GET", "/workflow-runs/"+run_id)
                if saved["status"] == "succeeded":
                    return saved
                if saved["status"] in {"failed", "skipped", "cancelled"}:
                    raise RuntimeError("Fictional run did not succeed: " + saved["status"])
                time.sleep(.25)
            raise RuntimeError("Fictional run did not finish within 20 seconds")
        reminder = {"mode":"sandbox", "confirm_sandbox":True, "idempotency_key":"demo-proof:"+key,
            "event":{"contact_id":"synthetic-demo-contact", "contact_permission":True},
            "message_body":"Fictional reminder preview. No message is sent.", "scheduled_at":stamp.isoformat()}
        if not proof:
            proof = wait_succeeded(request("POST", "/workflows/"+workflow["id"]+"/runs", json=reminder)["id"])
        deployments = request("GET", "/deployments", params={"client_id":profile["id"],"limit":500})
        deployment = next((r for r in deployments if r["workflow_id"]==workflow["id"] and r["channel"]=="sandbox" and r["status"]!="archived"), None)
        if not deployment:
            deployment = request("POST", "/clients/"+profile["id"]+"/deployments", json={
                "idempotency_key":"demo-deployment:"+key,"workflow_id":workflow["id"],"channel":"sandbox"})
        if deployment["status"] == "active":
            request("POST", "/deployments/"+deployment["id"]+"/pause")
        validated = request("POST", "/deployments/"+deployment["id"]+"/validate")
        assert validated["validation"]["ready"] and validated["status"]=="validated"
        request("POST", "/deployments/"+deployment["id"]+"/activate", json={"confirm_activation":True})
        due = datetime.now(timezone.utc)+timedelta(seconds=3)
        appointment = request("POST", "/deployments/"+deployment["id"]+"/appointments", json={
            "workflow_id":workflow["id"],"starts_at":(due+timedelta(hours=1)).isoformat(),
            "reminder":{**reminder,"idempotency_key":"demo-appointment:"+key,"scheduled_at":due.isoformat()}})
        finished = wait_succeeded(appointment["run_id"])
        outbox = request("GET", "/workflow-outbox", params={"run_id":finished["id"]})
        assert len(outbox)==1 and outbox[0]["sent"] is False and outbox[0]["mode"]=="sandbox"
        request("PATCH", "/tasks/"+task["id"], json={"status":"completed"})
        handoff = request("GET", "/clients/"+profile["id"]+"/handoff")
        assert handoff["client"]["is_demo"] and handoff["credentials_included"] is False
        timeline = request("GET", f"/businesses/{bid}/activities")
        operations = request("GET", "/operations/summary", params={"include_demo":"true"})
        return {"synthetic":True,"businesses_contacted":False,"sent":False,"business_id":bid,
            "client_id":profile["id"],"deployment_id":deployment["id"],"appointment_id":appointment["id"],
            "run_id":finished["id"],"run_status":finished["status"],"handoff_format":handoff["format"],
            "timeline_entries":len(timeline),"scheduler_running":operations["scheduler_running"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url",default="http://127.0.0.1:8000")
    print(json.dumps(run(parser.parse_args().base_url),indent=2))
