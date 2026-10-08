from app.models.workflow import Criterion, Evidence, now
from app.models.business import plausible_phone

WEIGHTS = {
    "inquiry_followup": ("N", 10), "appointment_reminders": ("N", 10),
    "consultation_followup": ("N", 10), "rebooking": ("N", 10),
    "public_email": ("C", 8), "business_phone": ("C", 6), "inquiry_form": ("C", 6),
    "operational_scale": ("V", 10), "recurring_services": ("V", 10),
    "booking_friction": ("D", 10), "inquiry_friction": ("D", 5), "intake_friction": ("D", 5),
}
AUTOMATIONS = {
    "inquiry_followup": "Inquiry follow-up assistant",
    "appointment_reminders": "Appointment reminder workflow",
    "consultation_followup": "Consultation follow-up assistant",
    "rebooking": "Client rebooking workflow",
    "booking_assistant": "Consultation booking assistant",
    "research_required": "Confirm business needs before proposing an automation",
}


def automatic_evidence(business, website, listing_observed_at=None, listing_source="public_listing"):
    evidence = []
    if plausible_phone(business.phone):
        evidence.append(Evidence(criterion=Criterion.business_phone, assessment="strong", source=listing_source, origin="automatic",
            observed_at=listing_observed_at or now(), detail="The saved business record includes a plausible phone number; reachability is unverified."))
    if website:
        if not plausible_phone(business.phone) and website.has_phone_link:
            evidence.append(Evidence(criterion=Criterion.business_phone, assessment="strong", source="public_website", origin="automatic", detail="The public website includes a plausible phone contact link; reachability is unverified.", observed_at=website.observed_at))
        if website.emails:
            evidence.append(Evidence(criterion=Criterion.public_email, assessment="strong", source="public_website", origin="automatic", detail="The public website includes an email contact link.", observed_at=website.observed_at))
        if website.has_inquiry_form:
            evidence.append(Evidence(criterion=Criterion.inquiry_form, assessment="partial", source="public_website", origin="automatic", detail="Static HTML contains a form with a text area; its submission behavior is unverified.", observed_at=website.observed_at))
        evidence.append(Evidence(
            criterion=Criterion.booking_friction,
            assessment="unknown",
            source="public_website", origin="automatic", observed_at=website.observed_at,
            detail="A booking-related link is visible; booking usability is unverified." if website.has_booking_link else "No booking-related link was observed in static HTML; the complete customer journey remains unassessed.",
        ))
    return evidence


def score(evidence):
    components = {"N": 0.0, "C": 0.0, "V": 0.0, "D": 0.0}
    coverage = 0
    assessed = set()
    gaps = []
    factors = {"strong": 1, "partial": 0.5, "clear": 0, "unknown": 0}
    for item in evidence:
        criterion = item.criterion.value
        component, maximum = WEIGHTS[criterion]
        components[component] += maximum * factors[item.assessment]
        if item.assessment != "unknown":
            coverage += maximum
            assessed.add(criterion)
        if component in {"N", "D"} and item.assessment in {"strong", "partial"}:
            gaps.append(item)
    total = sum(components.values())
    priority = "high" if total >= 80 else "medium" if total >= 60 else "low" if total >= 40 else "insufficient_evidence"
    recommendation = "research_required"
    operational = [item for item in gaps if WEIGHTS[item.criterion.value][0] == "N"]
    if operational:
        selected = max(operational, key=lambda e: factors[e.assessment])
        recommendation = selected.criterion.value
    elif any(item.criterion == Criterion.booking_friction for item in gaps):
        recommendation = "booking_assistant"
    elif any(item.criterion == Criterion.inquiry_friction for item in gaps):
        recommendation = "inquiry_followup"
    return {
        "need_score": round(100 * (components["N"] + components["D"]) / 60),
        "sales_score": round(100 * (components["C"] + components["V"]) / 40),
        "total_score": total, "components": components,
        "evidence_coverage": coverage, "provisional": coverage < 70,
        "priority": "research" if coverage < 70 else priority,
        "unknown_criteria": [name for name in WEIGHTS if name not in assessed],
        "pain_points": [item.detail for item in gaps],
        "automation_type": recommendation,
        "recommended_automation": AUTOMATIONS[recommendation],
    }
