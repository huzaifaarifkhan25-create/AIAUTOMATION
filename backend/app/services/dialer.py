"""Human dialing and verified sales-agent leg outcomes; no AI voice or recording."""
import asyncio
import base64
import hashlib
import hmac
import re
from urllib.parse import parse_qs
from uuid import NAMESPACE_URL, uuid5

import httpx

from app.database.store import SQLiteStore
from app.errors import AppError
from app.models.workflow import BusinessRecord, now

SID = re.compile(r"CA[0-9a-fA-F]{32}")
STATUSES = {"queued", "ringing", "in-progress", "completed", "busy", "failed", "no-answer", "canceled"}
TERMINAL = {"completed", "busy", "failed", "no-answer", "canceled"}
RANK = {"queued": 0, "ringing": 1, "in-progress": 2, **{state: 3 for state in TERMINAL}}


def number(value):
    return re.sub(r"[\s().-]", "", value or "")


class Dialer:
    def __init__(self, store, platform):
        self.store, self.platform, self.gateway = store, platform, platform.gateway
        self.lock = asyncio.Lock()

    async def start(self, business_id, request):
        async with self.lock:
            record = BusinessRecord.model_validate(await self.platform.require("businesses", business_id))
            if record.source == "mock":
                raise AppError(409, "mock_business", "Mock businesses cannot receive outbound calls")
            contact = await self.store.get("contacts", business_id)
            if contact and contact["stage"] == "do_not_contact":
                raise AppError(409, "do_not_contact", "This business is marked do not contact")
            if request.confirm_outbound_call is not True:
                raise AppError(422, "call_confirmation_required", "Explicitly confirm the outbound call request")
            s = self.gateway.settings
            if not s.enable_outbound_calls:
                raise AppError(503, "calling_disabled", "Outbound calling is disabled")
            key = str(uuid5(NAMESPACE_URL, business_id + ":call:" + request.idempotency_key))
            previous = await self.store.get("calls", key)
            if previous:
                if previous.get("provider_call_id"):
                    return previous
                raise AppError(409, "call_status_uncertain", "This call was already attempted; reconcile provider evidence before any new attempt")
            # Known local validation failures have made no provider attempt and
            # must not consume the durable external-call reservation.
            self.gateway.prepare_call(record.business.phone)
            pending = {"id": key, "business_id": business_id, "status": "pending", "created_at": now().isoformat(),
                "account_sid": s.twilio_account_sid, "agent_number": number(s.sales_agent_number),
                "from_number": number(s.twilio_from_number), "prospect_number": number(record.business.phone),
                "provider_status": None, "outcome_leg": "sales_agent", "last_sequence": -1}
            if not await self.store.reserve("calls", key, pending):
                previous = await self.platform.require("calls", key)
                if previous.get("provider_call_id"):
                    return previous
                raise AppError(409, "call_status_uncertain", "This call was already attempted; reconcile provider evidence before any new attempt")
            try:
                result = await self.gateway.start_call(record.business.phone, call_id=key)
                if not isinstance(result, dict) or not isinstance(result.get("sid"), str) or not SID.fullmatch(result["sid"]):
                    raise AppError(502, "calling_invalid_response", "Calling provider returned an invalid call identifier")
                pending.update(status="submitted", provider_call_id=result["sid"])
            except AppError:
                pending["status"] = "failed_or_uncertain"
                await self.store.put("calls", key, pending)
                raise
            await self.store.put("calls", key, pending)
            return pending

    def require_callbacks(self):
        s = self.gateway.settings
        if not isinstance(self.store, SQLiteStore):
            raise AppError(503, "dialer_tracking_storage_unsupported", "Verified dialer outcomes currently require SQLite")
        if not s.app_public_url or not s.twilio_auth_token or not s.twilio_account_sid:
            raise AppError(503, "dialer_callback_not_configured", "Configure APP_PUBLIC_URL and actual runtime Twilio credentials for signed callbacks")
        return s

    async def callback(self, call_id, raw, signature):
        s = self.require_callbacks()
        try:
            values = parse_qs(raw.decode("utf-8", errors="strict"), strict_parsing=True, keep_blank_values=True, max_num_fields=64)
            if any(len(value) != 1 for value in values.values()):
                raise ValueError()
            params = {key: values[0] for key, values in values.items()}
        except (ValueError, UnicodeError):
            raise AppError(422, "call_callback_invalid_payload", "Callback must contain single-valued form fields") from None
        url = s.app_public_url.rstrip("/") + "/webhooks/twilio/calls/" + call_id
        signed = url + "".join(key + params[key] for key in sorted(params))
        expected = base64.b64encode(hmac.new(s.twilio_auth_token.encode(), signed.encode(), hashlib.sha1).digest()).decode()
        if not isinstance(signature, str) or len(signature) > 200 or not hmac.compare_digest(signature.encode(), expected.encode()):
            raise AppError(401, "call_callback_invalid_signature", "A valid provider signature is required")
        if (params.get("AccountSid") != s.twilio_account_sid or params.get("CallStatus") not in STATUSES
            or not SID.fullmatch(params.get("CallSid", "")) or not re.fullmatch(r"[0-9]{1,9}", params.get("SequenceNumber", ""))):
            raise AppError(422, "call_callback_invalid_payload", "Callback account, identifier, status or sequence is invalid")
        async with self.lock:
            record = await self.platform.require("calls", call_id)
            self.match(record, params["CallSid"], params.get("To"), params.get("From"), params["AccountSid"])
            sequence = int(params["SequenceNumber"])
            key = str(uuid5(NAMESPACE_URL, f"medspa-call-event:{call_id}:{sequence}"))
            digest = hashlib.sha256(raw).hexdigest()
            previous = await self.store.get("call_events", key)
            if previous:
                if previous["request_hash"] != digest:
                    raise AppError(409, "call_callback_conflict", "This sequence already belongs to different callback data")
                return {"status": "duplicate"}
            status = params["CallStatus"]
            changed = sequence > record.get("last_sequence", -1) and self.advance_allowed(record.get("provider_status"), status)
            event = {"id": key, "call_id": call_id, "business_id": record["business_id"], "provider_status": status,
                "sequence": sequence, "request_hash": digest, "received_at": now().isoformat(), "applied": changed}
            if changed:
                self.outcome(record, params["CallSid"], status)
                record["last_sequence"] = sequence
            await self.store.put_many([("call_events", key, event), ("calls", call_id, record)])
            return {"status": "applied" if changed else "ignored"}

    @staticmethod
    def advance_allowed(current, candidate):
        return current not in TERMINAL and (current is None or RANK[candidate] >= RANK[current])

    @staticmethod
    def match(record, sid, to, sender, account):
        if (record.get("provider_call_id") not in {None, sid} or record.get("account_sid") != account
            or record.get("agent_number") != number(to) or record.get("from_number") != number(sender)):
            raise AppError(409, "call_provider_record_mismatch", "Provider record does not match the saved sales-agent call")

    @staticmethod
    def outcome(record, sid, status):
        record.update(provider_call_id=sid, provider_status=status, outcome_leg="sales_agent",
            status="finished" if status in TERMINAL else "submitted", updated_at=now().isoformat())

    async def reconcile(self, call_id, sid):
        if not SID.fullmatch(sid):
            raise AppError(422, "call_identifier_invalid", "Supply an actual Twilio call SID")
        async with self.lock:
            s = self.gateway.settings
            if not s.app_api_token or not s.twilio_auth_token or not s.twilio_account_sid:
                raise AppError(503, "calling_not_configured", "Configure authenticated provider access before reconciliation")
            record = await self.platform.require("calls", call_id)
            result = await self.gateway.json_request("GET",
                f"https://api.twilio.com/2010-04-01/Accounts/{s.twilio_account_sid}/Calls/{sid}.json",
                auth=httpx.BasicAuth(s.twilio_account_sid, s.twilio_auth_token))
            if not isinstance(result, dict) or result.get("sid") != sid or result.get("status") not in STATUSES:
                raise AppError(502, "call_provider_invalid_response", "Calling provider returned an invalid outcome")
            self.match(record, sid, result.get("to"), result.get("from"), result.get("account_sid"))
            if self.advance_allowed(record.get("provider_status"), result["status"]):
                self.outcome(record, sid, result["status"])
            await self.store.put("calls", call_id, record)
            return record
