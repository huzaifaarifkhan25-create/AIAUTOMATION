# CALLER-EMAIL-INSTRUCTIONS.md

Task for Codex: finish the **cold-call script** and **cold-email/pitch** features end to end, and wire the optional
**real email sending (Resend)** and **click-to-call (Twilio)** safely. Read `CODEX-INSTRUCTIONS.md` and `AGENTS.md` first;
all their ground rules still apply (preserve existing behavior, no secrets in code/logs/browser, no real-business contact in
tests, honest verification notes).

The work is split into levels. **Finish Level 1 and 2 fully before touching Level 3 or 4.** Level 1 alone is enough for the demo.

---

## Level 0: Check what already exists (read-only)

The completion report says these already exist; confirm by reading the code and `/openapi.json`, then list gaps:
- `POST /ai/businesses/{id}/pitch` and `POST /ai/businesses/{id}/call-script` (Gemini, draft only, do-not-contact blocked).
- Existing rule-based `GET /businesses/{id}/outreach-draft?analysis_id=...` (no AI; keep it as the fallback when Gemini is unavailable).
- Email: Resend adapter inside the sandbox/workflow runner (disabled by default, API-only, simulated tests only).
- Calls: Twilio human click-to-call adapter (`POST /businesses/{id}/calls`, `GET /calls`), disabled by default.
- The Next.js proxy currently **blocks the call route**. Keep it blocked unless Level 3 is explicitly implemented.

Write a short gap list (what the UI can and cannot do today) before coding.

---

## Level 1: Scripts and drafts (no provider, no sending) — REQUIRED

### 1.1 Output schemas (validate with Pydantic; retry once on invalid JSON)

**Email pitch**
```json
{
  "language": "en|ur|roman_ur",
  "subject_options": ["...", "...", "..."],
  "body": "plain text, 90-150 words",
  "personalization_used": [{"fact": "...", "source": "...", "observed_on": "YYYY-MM-DD"}],
  "call_to_action": "one low-pressure ask (e.g. 15-minute call)",
  "follow_ups": [{"after_days": 3, "body": "..."}, {"after_days": 7, "body": "..."}],
  "opt_out_line": "...",
  "assumptions_and_unknowns": ["..."]
}
```

**Call script**
```json
{
  "language": "en|ur|roman_ur",
  "opening": "10-15 second intro that states who is calling and why",
  "permission_question": "ask if it is a good time",
  "discovery_questions": ["3-5 open questions about inquiries, reminders, follow-ups, rebooking"],
  "value_statement": "one or two sentences, no invented problems",
  "objections": [{"objection": "...", "response": "..."}],
  "close": "ask for a short follow-up call or meeting",
  "voicemail": "under 20 seconds",
  "if_not_interested": "polite exit and offer to stop contacting",
  "assumptions_and_unknowns": ["..."]
}
```

### 1.2 Content rules (mandatory)
- Use only facts from the lead's saved listing and **latest saved analysis**. Cite each personalization fact with source and date.
  If there is no analysis, say so and produce a generic discovery-style draft; do not invent anything.
- Discovery style: ask about their process. **Never claim a problem exists** ("you miss calls", "no reminders") unless a
  business-confirmed gap is recorded. Public friction may be mentioned neutrally ("I noticed the booking link is on the contact page").
- Do not promise results, savings or revenue. No fake urgency, no fake familiarity, no pretending to be a customer.
- Email must include a clear identification of the sender and a simple opt-out line. Keep it short and plain.
- Language selector: English, Urdu, Roman Urdu. Default English. The script must stay natural for a Pakistani med-spa owner.
- Add a configurable "sender profile" (name, company, offer one-liner) in server-side settings or request input, never hard-coded.
- Block for do-not-contact leads and for archived/mock handling consistent with existing guards. Mark demo leads as DEMO in outputs.
- Treat website/CSV text as untrusted data (prompt-injection safe delimiters), as in `CODEX-INSTRUCTIONS.md`.
- Tone and length limits enforced by validation (e.g. email body max ~170 words, opening max ~40 words).

### 1.3 UI (Next.js lead detail page)
- Two panels: **Email pitch** and **Call script**, with a language selector, Generate / Regenerate, loading and error states.
- Show the personalization facts with their sources/dates, and the unknowns list. Label the output "AI draft, review before use".
- Buttons: **Copy** (subject, body, script), **Download .txt**, and:
  - Email: **Open in email app** using a `mailto:` link with subject/body URL-encoded. The recipient field is empty or taken
    from a recorded public contact the operator selects. This does not send anything from our server.
  - Call: **Call on my phone** using a `tel:` link for a recorded public phone number. The operator's own phone dials; our server does nothing.
  These two links are the **zero-risk way to "send/call"** in the demo.
- After the operator actually emails/calls from their own tools, offer **Log contact** that creates a manual contact-history
  entry (existing activities API) with the outcome. A log entry never claims delivery and never creates operational evidence.
- Save generated drafts as AI insights (existing provenance fields) so they can be shown without calling Gemini again.
- If Gemini is unavailable: fall back to the rule-based outreach draft for email and show a clear "AI unavailable" note for scripts.

### 1.4 Tests (mock Gemini, no live calls)
Valid output; invalid JSON then retry; missing key; do-not-contact blocked; no-analysis path makes no invented claims;
prompt-injection text in a website snippet ignored; each language option; length validation; `mailto:`/`tel:` URL encoding
(special characters, Urdu text); log-contact does not set delivery or evidence fields.

Acceptance: 3-4 real, category-reviewed leads have saved email + call-script drafts; the full suite passes.

---

## Level 2: Real email sending to TEST addresses only — OPTIONAL

Use the existing guarded Resend path. Do not weaken any guard.

Requirements already enforced by the repo (verify, do not rebuild): `ENABLE_EMAIL_DELIVERY=true`, `APP_API_TOKEN` set,
`RESEND_API_KEY`, verified `RESEND_FROM_EMAIL`; mock businesses cannot send; explicit recipient/subject/message/event/timing;
literal `confirm_send=true`; outbox reserved before submission with a provider idempotency key; "submitted" is not "delivered";
no automatic resend after timeouts; opt-outs block sending.

Tasks:
1. Add a **Send test email** action in the Next.js UI, shown only when `GET /capabilities` reports email enabled.
   The recipient must be typed by the operator and must be an address the owner controls. Show a confirmation dialog with the
   full recipient, subject and body, and a checkbox "I own this address and consent to receive this test".
2. Route it through the existing backend send path (through the Next.js proxy with an explicit allowlist entry for only this route).
   Never expose `RESEND_API_KEY` or `APP_API_TOKEN` to the browser.
3. Display the outbox state honestly: reserved / submitted / delivered / bounced / failed, with timestamps. Never show "sent"
   for "submitted".
4. For delivery callbacks, `POST /webhooks/resend` needs a public HTTPS backend URL (`APP_PUBLIC_URL`) and the real
   `RESEND_WEBHOOK_SECRET`. If the backend is not publicly hosted yet, skip callbacks and say delivery status is unverified.
5. Add an **opt-out footer** in the email template and make sure the existing opt-out recording remains effective.
6. Tests: simulated provider only (success, timeout, ambiguous error, duplicate click, opted-out recipient, mock business).
7. One **manual live check** by the owner: send to their own address, record the result honestly in `backend/VERIFICATION.md`.

Human-only steps (ask the owner): create the Resend account and API key; verify a sender domain or address (check Resend's
current rules for which recipients an unverified sender may email); set secrets in the host environment, never in chat or git.

---

## Level 3: Click-to-call via Twilio to the OWNER'S OWN phones only — OPTIONAL, LAST

The existing adapter is a **human** dialer: it calls the sales agent first, then connects to the prospect. No AI calling, no recording.

Requirements already enforced (verify): `ENABLE_OUTBOUND_CALLS=true`, API authentication, explicit per-call confirmation,
persistent idempotency, local validation before reserving a call, no automatic redial after provider uncertainty,
`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `SALES_AGENT_NUMBER`, callbacks at an exact public HTTPS URL.

Tasks:
1. Keep the proxy call route blocked by default. Only if the owner explicitly asks, add one allowlisted route for the
   "Start test call" action, behind the same confirmation pattern as email.
2. UI: confirmation dialog showing both numbers, the script beside it, and a checkbox "Both numbers belong to me/consenting testers".
3. For the demo, the "prospect" number must be a second phone the owner controls. Never dial a real business.
4. Show call state honestly; a completed callback describes the sales-agent leg, not whether the prospect answered.
5. Tests: simulated provider only.
6. Manual live check by the owner only, and note account limits honestly (a trial Twilio account may only call verified numbers;
   check Twilio's current rules and country permissions for Pakistan before promising anything).

Human-only steps: Twilio account, number, verified numbers, secrets in environment, public HTTPS callback URL.

---

## Level 4: Not in scope now (do not build, do not claim)
Bulk or automated cold campaigns, AI voice calling, call recording, SMS/WhatsApp sending, scheduled prospecting sequences that
send without a human click, native n8n execution. Follow-up sequences in Level 1 are **drafts only**.

---

## Compliance and safety notes (apply to everything above)
- Cold email and cold calling to businesses can be regulated (consent, opt-out, do-not-call, anti-spam rules differ by country).
  The owner must check the rules for each target market before any real outreach. This project does not provide legal advice.
- For the hackathon: demonstrate with fictional/test recipients only. Do not message or call real businesses.
- Keep an opt-out/do-not-contact record path and respect it everywhere (existing guards).
- Every UI label must keep: "AI draft", "DEMO", "unsent", "submitted (not confirmed delivered)", "unconfirmed need".

## Deliverables
1. Code + tests for Levels 1 (and 2/3 only if explicitly proceeding).
2. UI changes on the lead detail page and (if Level 2/3) a clearly gated send/call dialog.
3. `.env.example` updated with names only; no values anywhere.
4. `backend/VERIFICATION.md` and `AGENTS.md` updated: exactly what was tested, what was mocked, what remains unverified.
5. Final report: what changed, test results, what the owner must do manually (accounts, keys, live checks), known limits.
