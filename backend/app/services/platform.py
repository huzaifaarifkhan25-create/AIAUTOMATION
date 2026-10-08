from uuid import NAMESPACE_URL, uuid4, uuid5
import asyncio

from app.errors import AppError
from app.models.workflow import Analysis, BusinessRecord, Contact, now
from app.services.scoring import automatic_evidence, score
from app.services.workflows import generate_workflow
from app.services.qualification import latest_by_business, qualify
from app.services.csv_import import identity


class Platform:
    def __init__(self, store, gateway):
        self.store = store
        self.gateway = gateway

    async def require(self, kind, record_id):
        record = await self.store.get(kind, record_id)
        if record is None:
            raise AppError(404, "not_found", "Requested record was not found")
        return record

    async def save_business(self, business, source="manual"):
        async with self.store.business_lock:
            key = identity(business)
            record_id = str(uuid5(NAMESPACE_URL, "medspa:" + key))
            existing = await self.store.get("businesses", record_id)
            if not existing:
                existing = next((record for record in await self.store.list("businesses")
                    if identity(BusinessRecord.model_validate(record).business) == key), None)
            if existing:
                return BusinessRecord.model_validate(existing)
            timestamp = now()
            record = BusinessRecord(id=record_id, business=business, source=source, created_at=timestamp, updated_at=timestamp)
            if not await self.store.reserve("businesses", record_id, record.model_dump(mode="json")):
                return BusinessRecord.model_validate(await self.require("businesses", record_id))
            return record

    async def analyze(self, business_id, request):
        record = BusinessRecord.model_validate(await self.require("businesses", business_id))
        website = None
        if request.fetch_website:
            if not record.business.website:
                raise AppError(422, "website_missing", "This business has no website to analyze")
            website = await self.gateway.analyze_website(record.business.website)
        observed_at = record.provenance.collected_at if record.provenance else record.updated_at
        listing_source = "manual_research" if record.source == "manual" else "public_listing"
        evidence = {e.criterion: e for e in automatic_evidence(record.business, website, observed_at, listing_source)}
        evidence.update({e.criterion: e for e in request.evidence if not (request.fetch_website and e.origin == "automatic")})
        evidence = list(evidence.values())
        result = score(evidence)
        summary = "Evidence-based research. Unknown criteria are unassessed, not proof of no need. Confirm internal processes with the business."
        questions = ["How do you currently manage inquiries, reminders, consultation follow-up, and rebooking?"]
        if request.use_ai:
            narrative = await self.gateway.summarize(record.business, evidence, website)
            summary, questions = narrative.summary, narrative.suggested_questions
        analysis = Analysis(
            id=str(uuid4()), business_id=business_id, created_at=now(),
            mode="rules_with_ai_summary" if request.use_ai else "rules",
            evidence=evidence, website=website, summary=summary, suggested_questions=questions,
            **result,
        )
        # Network research happens outside the action guard. Commit the new
        # evidence under it so completed updates cannot race an old message.
        async with self.execution.lock:
            analysis.created_at = now()
            await self.store.put("analyses", analysis.id, analysis.model_dump(mode="json"))
        return analysis

    async def workflow(self, analysis_id):
        analysis = Analysis.model_validate(await self.require("analyses", analysis_id))
        await self.require("businesses", analysis.business_id)
        contact = await self.store.get("contacts", analysis.business_id)
        if contact and contact.get("stage") == "do_not_contact":
            raise AppError(409, "do_not_contact", "This business is marked do not contact")
        await self.require_current_analysis(analysis)
        workflow = generate_workflow(analysis)
        await self.store.put("workflows", workflow.id, workflow.model_dump(mode="json"))
        return workflow

    async def require_current_analysis(self, analysis):
        latest = latest_by_business(await self.store.list("analyses")).get(analysis.business_id)
        if not latest or latest["id"] != analysis.id:
            raise AppError(409, "analysis_outdated", "Use the latest analysis before creating an outreach or workflow draft")

    async def opportunities(self, include_provisional=False, include_demo=False):
        businesses, analyses, contacts = await asyncio.gather(
            self.store.list("businesses"), self.store.list("analyses"), self.store.list("contacts"))
        blocked = {item["business_id"] for item in contacts if item.get("stage") == "do_not_contact"}
        eligible = {record["id"] for record in businesses if record["id"] not in blocked and (include_demo or record["source"] != "mock")}
        records = [record for bid, record in latest_by_business(analyses).items()
                   if bid in eligible and (include_provisional or not record["provisional"])]
        return sorted(records, key=lambda record: (-record["total_score"], record["business_id"]))

    async def update_contact(self, business_id, update):
        if getattr(self, "crm", None) and self.crm.supported:
            async with self.execution.lock, self.dialer.lock:
                return await self.crm.update_contact(business_id, update)
        async with self.dialer.lock:
            await self.require("businesses", business_id)
            contact = Contact(business_id=business_id, stage=update.stage, notes=update.notes, updated_at=now())
            await self.store.put("contacts", business_id, contact.model_dump(mode="json"))
        return contact

    async def archive_workflow(self, workflow_id):
        async with self.execution.lock:
            record = await self.require("workflows", workflow_id)
            record["status"] = "archived"
            await self.store.put("workflows", workflow_id, record)
        self.execution.wake.set()
        return record

    async def qualification(self, business_id):
        record = await self.require("businesses", business_id)
        analyses, contact = await asyncio.gather(self.store.list("analyses"), self.store.get("contacts", business_id))
        return qualify(record, latest_by_business(analyses).get(business_id), contact)

    async def prospects(self, include_demo=False, include_blocked=False):
        businesses, analyses, contacts = await asyncio.gather(
            self.store.list("businesses"), self.store.list("analyses"), self.store.list("contacts"))
        latest = latest_by_business(analyses)
        contact_map = {contact["business_id"]: contact for contact in contacts}
        results = [qualify(record, latest.get(record["id"]), contact_map.get(record["id"]))
                   for record in businesses if include_demo or record["source"] != "mock"]
        if not include_blocked:
            results = [item for item in results if item.prospect_status != "do_not_contact"]
        order = {"ready_for_review": 0, "research": 1, "not_analyzed": 2, "do_not_contact": 3}
        return sorted(results, key=lambda item: (order[item.prospect_status], -item.prospect_score,
                                                 -item.public_evidence_coverage, item.business_id))

    async def outreach_draft(self, business_id, analysis_id):
        record = await self.require("businesses", business_id)
        business = BusinessRecord.model_validate(record).business
        analysis = Analysis.model_validate(await self.require("analyses", analysis_id))
        if analysis.business_id != business_id:
            raise AppError(409, "analysis_mismatch", "Analysis belongs to a different business")
        contact = await self.store.get("contacts", business_id)
        qualification = qualify(record, analysis, contact)
        if qualification.prospect_status == "do_not_contact":
            raise AppError(409, "do_not_contact", "This business is marked do not contact")
        await self.require_current_analysis(analysis)
        confirmed = qualification.need_status == "confirmed_gap"
        if confirmed:
            gaps = " ".join(item.detail for item in analysis.evidence if item.criterion.value in qualification.confirmed_gap_criteria)
            text = f"The recorded discussion described: {gaps}\n\nWould you be open to reviewing whether {analysis.recommended_automation.lower()} would help? We would first confirm the scope together."
        else:
            text = "I'd like to understand how your team currently handles new inquiries, appointment reminders, and client rebooking.\n\nWould you be open to a short conversation about whether automation could be useful? We would first confirm any need and agree on scope."
        return {
            "business_id": business_id, "analysis_id": analysis_id, "status": "draft",
            "kind": "confirmed_need" if confirmed else "discovery",
            "subject": f"Automation discussion for {business.name}",
            "body": f"Hello {business.name} team,\n\n{text}\n\nBest regards",
            "sent": False,
        }

    async def call(self, business_id, request):
        return await self.dialer.start(business_id, request)
