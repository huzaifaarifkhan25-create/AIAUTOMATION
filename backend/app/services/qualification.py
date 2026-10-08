"""Derived stages; no new observations or changes to historical analyses."""
from app.models.qualification import Qualification
from app.models.workflow import Analysis, BusinessRecord
from app.services.scoring import WEIGHTS

FACTORS = {"strong": 1, "partial": 0.5, "clear": 0, "unknown": 0}
PUBLIC_CRITERIA = [name for name, (component, _) in WEIGHTS.items() if component in {"C", "V"}]
NEED_CRITERIA = [name for name, (component, _) in WEIGHTS.items() if component in {"N", "D"}]
LABELS = {"public_email": "Business email", "business_phone": "Business phone", "inquiry_form": "Inquiry form",
          "operational_scale": "Operational scale", "recurring_services": "Recurring-service offering"}


def qualify(record, analysis=None, contact=None):
    record = BusinessRecord.model_validate(record)
    analysis = Analysis.model_validate(analysis) if analysis else None
    evidence = {item.criterion.value: item for item in analysis.evidence} if analysis else {}
    points = sum(WEIGHTS[name][1] * FACTORS[evidence[name].assessment] for name in PUBLIC_CRITERIA if name in evidence)
    assessed = [name for name in PUBLIC_CRITERIA if name in evidence and evidence[name].assessment != "unknown"]
    score = round(100 * points / 40)
    coverage = 100 * sum(WEIGHTS[name][1] for name in assessed) / 40
    # A detected, untested form is not enough by itself to establish contactability.
    contact_route = any(name in evidence and evidence[name].assessment in {"strong", "partial"}
                        for name in ("public_email", "business_phone")) or (
                            "inquiry_form" in evidence and evidence["inquiry_form"].assessment == "strong")
    reasons = [f"{LABELS[name]}: {evidence[name].assessment} evidence recorded; review its source and date."
               for name in assessed if FACTORS[evidence[name].assessment] > 0]
    if not contact_route:
        reasons.append("No supported contact route is recorded. A detected but untested form alone is insufficient.")
    confirmed = [name for name in NEED_CRITERIA if WEIGHTS[name][0] == "N" and name in evidence
                 and evidence[name].assessment in {"strong", "partial"} and evidence[name].source == "business_confirmation"]
    friction = [name for name in NEED_CRITERIA if WEIGHTS[name][0] == "D" and name in evidence
                and evidence[name].assessment in {"strong", "partial"}]
    no_gap = all(name in evidence and evidence[name].assessment == "clear" for name in NEED_CRITERIA)
    need_status = "confirmed_gap" if confirmed else "observed_friction" if friction else "assessed_no_gap" if no_gap else "unconfirmed"
    blocked = bool(contact and contact.get("stage") == "do_not_contact")
    ready = bool(analysis and score >= 40 and coverage >= 40 and contact_route and not blocked)
    status = "do_not_contact" if blocked else "not_analyzed" if not analysis else "ready_for_review" if ready else "research"
    next_step = ("Respect the do-not-contact stage. Do not prepare outreach." if blocked else
                 "Analyze the saved listing and record public contact and business-fit evidence." if not analysis else
                 "Review the recorded gap and confirm the scope before proposing an automation." if confirmed else
                 "Verify the observed customer-facing issue and ask the business about its process." if friction else
                 "Review the source and contact details, then ask how inquiries, reminders, and rebooking are handled. No internal gap is established." if ready else
                 "Research public contact details and business fit. Keep missing facts unknown.")
    return Qualification(
        business_id=record.id, analysis_id=analysis.id if analysis else None, is_demo=record.source == "mock",
        prospect_score=score, public_evidence_coverage=coverage, prospect_status=status,
        prospect_reasons=reasons, public_unknown_criteria=[name for name in PUBLIC_CRITERIA if name not in assessed],
        need_status=need_status, confirmed_gap_criteria=confirmed, observed_friction_criteria=friction,
        need_review_ready=bool(analysis and not analysis.provisional and (confirmed or friction) and not blocked),
        next_step=next_step,
    )


def latest_by_business(records):
    latest = {}
    for record in sorted(records, key=lambda item: item["created_at"], reverse=True):
        latest.setdefault(record["business_id"], record)
    return latest
