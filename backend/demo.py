"""Run the fictional backend workflow against an already running local server."""
import argparse
import os
from urllib.parse import urlsplit

import httpx


def run(base_url):
    # This script writes demo records; require a local endpoint to avoid polluting a live deployment.
    if urlsplit(base_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("The demo requires a local server")
    token = os.getenv("APP_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with httpx.Client(base_url=base_url, headers=headers, timeout=15) as client:
        def request(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

        assert request("GET", "/health") == {"status": "ok"}
        readiness = request("GET", "/ready")
        if readiness.get("status") != "ready" or readiness.get("persistence") != "sqlite":
            raise RuntimeError("The fictional demo requires ready local SQLite storage")
        businesses = request("POST", "/businesses/import", json={"industry": "med spa", "location": "Demo City"})
        business = businesses[0]
        assert business["source"] == "mock"
        criteria = {
            "inquiry_followup": "business_confirmation",
            "appointment_reminders": "business_confirmation",
            "consultation_followup": "business_confirmation",
            "rebooking": "business_confirmation",
            "public_email": "manual_research",
            "business_phone": "manual_research",
            "inquiry_form": "manual_research",
            "operational_scale": "manual_research",
            "recurring_services": "manual_research",
            "booking_friction": "manual_research",
            "inquiry_friction": "manual_research",
            "intake_friction": "manual_research",
        }
        evidence = [{"criterion": name, "assessment": "partial", "source": source,
                     "detail": f"Fictional demo evidence only: {name}."} for name, source in criteria.items()]
        bid = business["id"]
        analysis = request("POST", f"/businesses/{bid}/analyze", json={"evidence": evidence})
        assert analysis["total_score"] == 50 and analysis["evidence_coverage"] == 100
        ranking = request("GET", "/opportunities", params={"include_demo": "true"})
        assert any(item["id"] == analysis["id"] for item in ranking)
        draft = request("GET", f"/businesses/{bid}/outreach-draft", params={"analysis_id": analysis["id"]})
        assert draft["sent"] is False
        contact = request("PATCH", f"/businesses/{bid}/contact", json={"stage": "demo_booked", "notes": "Fictional demo only; no contact made."})
        assert contact["stage"] == "demo_booked"
        workflow = request("POST", "/workflows", json={"analysis_id": analysis["id"]})
        exported = request("GET", f'/workflows/{workflow["id"]}/export')
        assert exported == workflow and workflow["execution_supported"] is False
        print("Demo passed: import → analyze → rank → outreach draft → contact record → workflow export.")
        print("Data and evidence are fictional. No messages, calls, or automation executions occurred.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    run(parser.parse_args().base_url)
