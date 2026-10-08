"""Resend adapter: submission is distinct from delivery; uncertain sends never retry."""
import base64
import hashlib
import hmac
import json
from datetime import datetime
from uuid import UUID, NAMESPACE_URL, uuid5

from pydantic import TypeAdapter

from app.errors import AppError
from app.models.execution import EmailAddress
from app.models.workflow import now

EVENTS = {"email.sent": "sent", "email.delivered": "delivered", "email.bounced": "bounced",
          "email.complained": "complained", "email.failed": "failed", "email.suppressed": "suppressed"}
RANK = {"submission_started": 0, "submission_uncertain": 0, "submitted": 0, "sent": 1,
        "delivered": 2, "bounced": 3, "failed": 3, "suppressed": 3, "complained": 4}


def permission_id(business_id, contact_id):
    return str(uuid5(NAMESPACE_URL, f"medspa-permission:{business_id}:{contact_id}"))


def recipient_permission_id(business_id, recipient):
    # Conservatively treat case variants as the same recipient within a business.
    return str(uuid5(NAMESPACE_URL, f"medspa-recipient-permission:{business_id}:{recipient.strip().casefold()}"))


def email_id(value):
    try:
        if not isinstance(value, str):
            raise ValueError()
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise AppError(502, "email_invalid_response", "Email provider returned an invalid identifier") from None


class Delivery:
    def __init__(self, store, gateway, clock=now):
        self.store, self.gateway, self.clock = store, gateway, clock

    @property
    def configured(self):
        s = self.gateway.settings
        return bool(s.enable_email_delivery and s.app_api_token and s.resend_api_key and s.resend_from_email)

    def require_configured(self):
        s = self.gateway.settings
        if not s.enable_email_delivery:
            raise AppError(503, "email_disabled", "Email delivery is disabled; sandbox execution remains available")
        if not self.configured:
            raise AppError(503, "email_not_configured", "Configure authenticated access, RESEND_API_KEY and a verified RESEND_FROM_EMAIL before email execution")
        try:
            TypeAdapter(EmailAddress).validate_python(s.resend_from_email)
        except ValueError:
            raise AppError(503, "email_sender_invalid", "Configure a plain verified sender email address") from None

    async def submit(self, outbox):
        if outbox.get("provider_email_id"):
            return outbox
        if outbox["status"] != "submission_started":
            raise AppError(502, "email_submission_uncertain", "This email attempt cannot be automatically repeated; reconcile its provider record")
        self.require_configured()
        # Caller reserves the started record before this method. A replay must
        # never reach this method again, even though the provider also gets a key.
        try:
            response = await self.gateway.request("POST", "https://api.resend.com/emails",
                accepted_statuses=(400, 401, 403, 404, 409, 422),
                headers={"Authorization": f"Bearer {self.gateway.settings.resend_api_key}", "Idempotency-Key": outbox["id"]},
                json={"from": outbox["from_email"], "to": [outbox["recipient_email"]], "subject": outbox["subject"], "text": outbox["message_body"]})
            if response.status_code >= 400:
                outbox["status"] = "failed"
                await self.store.put("workflow_outbox", outbox["id"], outbox)
                raise AppError(502, "email_rejected", "Email provider rejected this submission; review configuration and the saved attempt")
            outbox["provider_email_id"] = email_id(response.json()["id"])
        except AppError as error:
            if error.code == "email_rejected":
                raise
            outbox["status"] = "submission_uncertain"
            await self.store.put("workflow_outbox", outbox["id"], outbox)
            raise AppError(502, "email_submission_uncertain", "Email submission is uncertain; check the provider before attempting a new event") from None
        except (ValueError, KeyError, TypeError):
            outbox["status"] = "submission_uncertain"
            await self.store.put("workflow_outbox", outbox["id"], outbox)
            raise AppError(502, "email_submission_uncertain", "Email provider returned an invalid submission result; reconcile the saved attempt") from None
        outbox["status"] = "submitted"
        await self.store.put("workflow_outbox", outbox["id"], outbox)
        await self.reconcile_events()
        return await self.store.get("workflow_outbox", outbox["id"])

    def signing_key(self):
        secret = self.gateway.settings.resend_webhook_secret
        if not secret:
            raise AppError(503, "email_webhook_not_configured", "Configure RESEND_WEBHOOK_SECRET as a direct runtime secret")
        try:
            encoded = secret.removeprefix("whsec_")
            key = base64.b64decode(encoded + "=" * (-len(encoded) % 4), validate=True)
            if not key:
                raise ValueError()
        except (ValueError, TypeError):
            raise AppError(503, "email_webhook_invalid_config", "The webhook signing secret is not valid") from None
        return key

    def verify(self, raw, headers):
        key = self.signing_key()
        msg_id, timestamp, signatures = (headers.get(name, "") for name in ("svix-id", "svix-timestamp", "svix-signature"))
        try:
            if not msg_id or len(msg_id) > 200 or len(timestamp) > 20 or len(signatures) > 2048:
                raise ValueError()
            if abs(int(self.clock().timestamp()) - int(timestamp)) > 300:
                raise ValueError()
            expected = base64.b64encode(hmac.new(key, msg_id.encode() + b"." + timestamp.encode() + b"." + raw, hashlib.sha256).digest()).decode()
            if not any(version == "v1" and hmac.compare_digest(signature.encode(), expected.encode())
                for token in signatures.split() if "," in token for version, signature in [token.split(",", 1)]):
                raise ValueError()
        except (ValueError, TypeError, UnicodeError):
            raise AppError(401, "email_webhook_invalid_signature", "A valid, recent provider signature is required") from None
        return msg_id

    async def accept_event(self, raw, headers):
        msg_id = self.verify(raw, headers)
        try:
            payload = json.loads(raw)
            kind = payload["type"]
            if not isinstance(kind, str) or len(kind) > 100:
                raise ValueError()
            at = datetime.fromisoformat(payload["created_at"].replace("Z", "+00:00"))
            if at.tzinfo is None:
                raise ValueError()
            provider_id = email_id(payload["data"]["email_id"]) if kind in EVENTS else None
        except (ValueError, KeyError, TypeError, AttributeError, AppError):
            raise AppError(422, "email_webhook_invalid_payload", "Signed callback payload is invalid") from None
        event_id = str(uuid5(NAMESPACE_URL, "resend-event:" + msg_id))
        fingerprint = hashlib.sha256(raw).hexdigest()
        event = {"id": event_id, "request_hash": fingerprint, "type": kind, "provider_email_id": provider_id,
                 "created_at": at.isoformat(), "status": "received" if kind in EVENTS else "ignored"}
        if not await self.store.reserve("delivery_events", event_id, event):
            previous = await self.store.get("delivery_events", event_id)
            if previous["request_hash"] != fingerprint:
                raise AppError(409, "email_webhook_conflict", "This event ID already belongs to different callback data")
        await self.reconcile_events()
        return {"received": True}

    async def reconcile_events(self):
        events = await self.store.list("delivery_events")
        outbox = {item.get("provider_email_id"): item for item in await self.store.list("workflow_outbox")
                  if item["mode"] == "email" and item.get("provider_email_id")}
        for event in sorted(events, key=lambda item: (item["created_at"], item["id"])):
            item = outbox.get(event.get("provider_email_id"))
            if event["status"] != "received" or not item:
                continue
            status = EVENTS[event["type"]]
            previous_rank = RANK.get(item["status"], 0)
            at = datetime.fromisoformat(event["created_at"])
            previous_at = datetime.fromisoformat(item["last_event_at"]) if item.get("last_event_at") else None
            if RANK[status] > previous_rank or (RANK[status] == previous_rank and (previous_at is None or at >= previous_at)):
                item.update(status=status, last_event_at=event["created_at"],
                    sent=item.get("sent", False) or status in {"sent", "delivered", "bounced", "complained"},
                    delivered=status == "delivered")
                await self.store.put("workflow_outbox", item["id"], item)
            if status in {"bounced", "complained", "suppressed"}:
                await self.opt_out(item["business_id"], item["contact_id"], status, item["recipient_email"])
            event["status"] = "applied"
            await self.store.put("delivery_events", event["id"], event)

    async def is_opted_out(self, business_id, contact_id, recipient=None):
        permission = await self.store.get("workflow_permissions", permission_id(business_id, contact_id))
        if permission and not permission["contact_permission"]:
            return True
        if not recipient:
            return False
        permission = await self.store.get("workflow_permissions", recipient_permission_id(business_id, recipient))
        if permission and not permission["contact_permission"]:
            return True
        # Older records suppressed only a contact ID. Resolve known addresses
        # without rewriting existing data or requiring a destructive migration.
        blocked = {r["contact_id"] for r in await self.store.list("workflow_permissions")
            if r["business_id"] == business_id and not r["contact_permission"] and r.get("contact_id")}
        if not blocked:
            return False
        for kind in ("workflow_runs", "workflow_outbox"):
            for record in await self.store.list(kind):
                recorded_contact = record.get("contact_id") or record.get("event", {}).get("contact_id")
                if (record["business_id"] == business_id and recorded_contact in blocked
                    and (record.get("recipient_email") or "").strip().casefold() == recipient.strip().casefold()):
                    return True
        return False

    async def opt_out(self, business_id, contact_id, reason="operator_opt_out", recipient=None):
        record = {"business_id": business_id, "contact_id": contact_id, "contact_permission": False,
                  "reason": reason, "updated_at": self.clock().isoformat()}
        recipients = {recipient.strip().casefold()} if recipient else set()
        for kind in ("workflow_runs", "workflow_outbox"):
            for item in await self.store.list(kind):
                recorded_contact = item.get("contact_id") or item.get("event", {}).get("contact_id")
                if item["business_id"] == business_id and recorded_contact == contact_id and item.get("recipient_email"):
                    recipients.add(item["recipient_email"].strip().casefold())
        records = [("workflow_permissions", permission_id(business_id, contact_id), record)]
        records.extend(("workflow_permissions", recipient_permission_id(business_id, address),
            {"business_id": business_id, "recipient_email": address, "contact_permission": False,
             "reason": reason, "updated_at": record["updated_at"]}) for address in recipients)
        await self.store.put_many(records)
        return record

    async def reconcile_provider(self, outbox, provider_email_id):
        self.require_configured()
        if outbox["mode"] != "email":
            raise AppError(409, "email_outbox_required", "Only an email attempt can be reconciled")
        if outbox.get("provider_email_id") and outbox["provider_email_id"] != provider_email_id:
            raise AppError(409, "email_provider_id_conflict", "This attempt already has another provider identifier")
        response = await self.gateway.json_request("GET", f"https://api.resend.com/emails/{provider_email_id}",
            headers={"Authorization": f"Bearer {self.gateway.settings.resend_api_key}"})
        try:
            if (email_id(response["id"]) != provider_email_id or response["to"] != [outbox["recipient_email"]]
                    or response["from"] != outbox["from_email"] or response["subject"] != outbox["subject"]):
                raise ValueError()
        except (ValueError, TypeError, KeyError, AppError):
            raise AppError(409, "email_provider_record_mismatch", "Provider record does not match the saved recipient, sender and subject") from None
        last = response.get("last_event")
        status = EVENTS.get("email." + last, "submitted") if isinstance(last, str) else "submitted"
        if RANK[status] >= RANK.get(outbox["status"], 0):
            outbox.update(provider_email_id=provider_email_id, status=status,
                sent=outbox.get("sent", False) or status in {"sent", "delivered", "bounced", "complained"}, delivered=status == "delivered")
        else:
            outbox["provider_email_id"] = provider_email_id
        await self.store.put("workflow_outbox", outbox["id"], outbox)
        if status in {"bounced", "complained", "suppressed"}:
            await self.opt_out(outbox["business_id"], outbox["contact_id"], status, outbox["recipient_email"])
        await self.reconcile_events()
        return await self.store.get("workflow_outbox", outbox["id"])
