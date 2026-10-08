# Hackathon reminder milestone — v0.6.0

Version 0.7 adds client onboarding, reviewed local activation, managed reminders,
CRM history/tasks, dialer outcomes and monitoring. See [MVP.md](MVP.md).
Current v0.9 browser steps are in [WORKSPACE.md](WORKSPACE.md); the completion
scope and live prerequisites are in [HANDOFF.md](HANDOFF.md).
The reminder contracts below remain supported; verification counts here describe
the historical v0.6 release, while [VERIFICATION.md](VERIFICATION.md) has current results.

The research workspace now includes a working local reminder demo, durable
appointment events, and a guarded Resend email adapter. Scheduling and cancellation
execute against SQLite. Provider submission and signed callbacks have simulated
coverage; no live email has been sent or verified.

## Demonstrate without credentials

1. Start the API using the repository README. Open the browser workspace and
   unlock it with the configured shared token if required.
2. Select **Automation lab**, then **Create fictional reminder demo**. This
   explicitly creates/reuses Demo Reminder Studio (Mock), synthetic evidence,
   and a reminder workflow. It never invents needs for a real lead.
3. Select the demo workflow. Enter a synthetic contact reference and preview
   text. Choose an appointment in the future and an earlier reminder time
   (for a quick demo, a minute from now). Check both confirmations and schedule.
4. Use **Refresh run history** after the due time. Inspect the succeeded run,
   step history, and saved **unsent** preview.
5. Schedule another future reminder and cancel its appointment. Refresh to
   inspect cancellation. Pending work stops; an existing preview is retained.

The browser form offers sandbox mode only. Its timings are editable suggestions;
submission records the operator's choices. Creating an appointment does not reserve
availability or create a Google Calendar booking. Restart the same single-worker
API with the same database to retain appointments, runs, and previews.

## Appointment API

Data routes use the configured bearer token and require SQLite. Lists accept
`limit` 1–500 (default 100) and `offset` >=0.

| Route | Behavior |
|---|---|
| `POST /demo/reminder-workflow` | Explicit fictional scaffold, HTTP 201 |
| `POST /appointments` | Persist event and queue a generated reminder, HTTP 202 |
| `GET /appointments?business_id=...` | List saved events |
| `GET /appointments/{id}` | Read one event |
| `POST /appointments/{id}/cancel` | Persist cancellation and stop pending work |
| `POST /businesses/{id}/automation-contacts/{contact_id}/opt-out` | Persist customer opt-out within this business |

Example body; replace IDs and dates with current values:

```json
{
  "workflow_id": "SAVED_REMINDER_WORKFLOW_ID",
  "starts_at": "2026-10-09T15:00:00+05:00",
  "reminder": {
    "mode": "sandbox",
    "confirm_sandbox": true,
    "idempotency_key": "synthetic-appointment-001",
    "event": {"contact_id": "synthetic-contact-001", "contact_permission": true},
    "message_body": "Synthetic appointment reminder preview only.",
    "scheduled_at": "2026-10-09T14:00:00+05:00"
  }
}
```

Dates require timezones; a new appointment starts in the future and its reminder
precedes it. The workflow must be a supported generated reminder using current
analysis. Repeating identical workflow/key inputs reuses the appointment/run;
changed inputs conflict. Partial enqueue failures recover on startup/worker cycles.
Persisted cancellation, an expired appointment, archived/outdated workflow,
business do-not-contact, or stored customer opt-out prevents pending delivery.
An input `contact_permission=true` is an assertion, not independent verification,
and cannot override stored opt-out. There is no opt-in reset API. To reschedule,
cancel and create a new event with a new key. Submitted messages cannot be recalled.

## Configure the first real email channel

Set these securely on the API host; the app does not automatically load `.env`:

- `APP_API_TOKEN`: strong shared token (production also needs `APP_ENV=production`
  and exact `APP_ALLOWED_HOSTS`).
- `ENABLE_EMAIL_DELIVERY=true`: defaults to false.
- `RESEND_API_KEY`: provider key; allow HTTPS access to `api.resend.com`.
- `RESEND_FROM_EMAIL`: plain sender email address verified with Resend.
- `RESEND_WEBHOOK_SECRET`: actual `whsec_...` signing secret supplied **directly
  to the runtime**. A network proxy placeholder cannot perform local HMAC checks.

Publish the API on an HTTPS host with persistent `/data`, one worker/replica,
and the correct allowed hostname. Register its actual `/webhooks/resend` URL with
Resend for `email.sent`, `email.delivered`, `email.bounced`, `email.complained`,
`email.failed`, and `email.suppressed`. Callbacks use their signature and require
no workspace bearer token. The endpoint checks raw-body signatures, a five-minute
timestamp window, duplicate IDs, and a 64 KB body limit. Preserve signature headers
and exact bytes through ingress. No public callback host has been provisioned here.

For an isolated consented test recipient and a non-mock eligible workflow, use
`POST /workflows/{id}/runs`, or the appointment body above, with this reminder:

```json
{
  "mode": "email",
  "confirm_send": true,
  "idempotency_key": "consented-test-001",
  "event": {"contact_id": "consented-test-contact", "contact_permission": true},
  "recipient_email": "YOUR_TEST_RECIPIENT@example.com",
  "subject": "Appointment reminder test",
  "message_body": "Explicitly approved test message.",
  "scheduled_at": "2026-10-09T14:00:00+05:00"
}
```

Replace the placeholder recipient, IDs, dates, and text before any live submission.
Mock businesses are blocked from email mode. Confirmation fields require literal
JSON `true`; the runner does not invent recipients, permission, timing, or messages.
Check run history and `/workflow-outbox?run_id=...`. `submitted` means provider
acceptance; it does not set `sent=true`. Signed provider events distinguish sent,
delivered, and failure states. Delivery does not establish that a person read it.
Bounces, complaints, and suppression persist customer opt-out. Duplicate/early
callbacks reconcile safely; late sent events cannot overwrite delivered/failure.

## An uncertain submission

A timeout, server error, invalid provider ID, or crash around submission leaves
an uncertain attempt. The runner does **not automatically send it again**. Check
the provider dashboard, then reconcile a known record using the authenticated
`POST /workflow-outbox/{id}/reconcile` route:

```json
{"provider_email_id":"ACTUAL_PROVIDER_UUID","confirm_provider_record":true}
```

This performs a read-only provider lookup and requires the saved sender, recipient,
subject, and ID to match. It never resends. Historical failed run status can remain;
the run's derived delivery status and outbox reflect reconciled provider evidence.
The stable outbox ID is also the provider idempotency key. Never create a fresh
event merely to bypass an uncertain attempt.

## Verified scope and remaining work

Version 0.6.0 passes 131 Python tests, five isolated Automation lab browser checks,
and 19 packaged deployment checks (nine API/container and ten browser). Provider
checks use simulated responses and signed synthetic callbacks; no business was
contacted. Production tests exercise actual SQLite, timing, cancellation, and
container restarts. See [VERIFICATION.md](VERIFICATION.md) for retained evidence.

General external/client execution flags remain false. Supported generated message
graphs now have sandbox mode plus email mode when enabled/configured. This is
not arbitrary workflow execution, native n8n, calendar synchronization, SMS,
AI voice calling, multi-user accounts, or client handoff. Supabase runner routes
return 503; research routes retain their previous behavior. Large-scale queues,
indexed storage, hosting, live provider verification, and business-confirmed needs
remain separate work. Keep credentials and patient information out of research
inputs and development fixtures.

Provider contracts were checked against Resend's official Python SDK/webhook models
and Standard Webhooks/Svix verifier source. This establishes the implementation
contract, not live account authentication or deliverability.
