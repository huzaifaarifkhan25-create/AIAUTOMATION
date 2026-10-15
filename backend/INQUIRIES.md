# Real inquiry intake and measured outcomes

This feature connects a server-side website form or webhook sender to one
operator-reviewed, active native n8n inquiry workflow. It stores real incoming
events and verifies n8n execution before creating a CRM task. A separate,
explicitly enabled email mode submits the reviewed acknowledgement through Resend.

The integration is implemented. Tests use fictional records and simulated
providers. Live email delivery requires your own provider configuration and a
consented test address; implementation and test fixtures are not live proof.

## Set up one source

1. Import or create the business and confirm its inquiry follow-up need with
   business-confirmed evidence. Public website friction alone is insufficient.
2. Generate its current inquiry follow-up workflow, connect n8n, review and deploy
   the fixed template. A deployment must be active and current.
3. Open Inquiries in the new UI. Create a source with a name, deployment, fixed
   acknowledgement and follow-up delay (5 minutes to 7 days). Confirm activation.
4. Save the source's **one-time webhook key** in the sending server's private
   environment. Source history contains a hash, never the raw key. A repeated
   creation request cannot recover the key; use Rotate key if it is lost.
5. Configure the form's backend or webhook service to POST JSON to the displayed
   intake URL with `Content-Type: application/json` and `X-Inquiry-Key`.
   Never put the key in public website JavaScript. Browser visitors submit to
   your own form backend, which authenticates requests to this application.

```json
{
  "event_id": "your-stable-form-event-123",
  "contact_reference": "your-opaque-contact-456",
  "inquiry": "General consultation availability question.",
  "contact_permission": true,
  "recipient_email": "your-consented-test-address@example.com"
}
```

Use a unique stable event ID per actual submission. Reposting the identical event
returns its saved attempt. Reusing the ID with changed data returns 409. Email is
optional in task-only mode and required in email mode. Business/workflow selection
comes from the reviewed source, never the incoming body. Unknown fields are
rejected. References are opaque identifiers using letters, digits, `_ . : -`.

This endpoint is for general operational inquiries, not patient or clinical
records. Do not include diagnoses, treatments, medical histories, payment details,
or confidential documents. Customer text is data, not an instruction to the AI.

## Enable actual acknowledgement email

Task-only sources send nothing. To create an email source, configure privately:

```dotenv
ENABLE_EMAIL_DELIVERY=true
APP_API_TOKEN=<strong private service access token>
RESEND_API_KEY=<private Resend API key>
RESEND_FROM_EMAIL=<plain address on your verified sending domain>
RESEND_WEBHOOK_SECRET=<actual direct-runtime webhook signing secret>
APP_PUBLIC_URL=https://your-app.example.com
```

Create a Resend account at https://resend.com, verify a sending domain in Domains,
create a sending API key in API Keys, and create the webhook
`https://your-app.example.com/webhooks/resend` in Webhooks. Subscribe to sent,
delivered, bounced, complained, failed and suppressed email events. Save its
signing secret privately. DNS/domain verification and public HTTPS hosting are
external prerequisites. The sender must be a plain address, not `Name <address>`.

Choose email mode, review the exact subject and acknowledgement, and explicitly
authorize delivery for incoming contacts with permission. This is source-scoped
preauthorization; it does not authorize campaigns or sending arbitrary messages.
Fictional/mock businesses cannot send. Each incoming event must contain literal
JSON `true` contact permission and a permitted recipient. Known opt-outs block
intake; later opt-outs, stale analysis, paused sources/native deployments or a
changed sender block waiting email work. Pausing cannot recall already-submitted
messages. A changed sender requires reviewing and creating a new source.

First live check: use only an address you own and explicitly consent to contact,
a real authorized business configuration, a new test event ID, and non-clinical
text. Observe the n8n execution ID and CRM task, then the provider email ID in the
saved outbox. Wait for a signed delivery callback or matched read-only provider
reconciliation before describing the email as delivered. Never contact prospects
to test configuration.

## Reliability and review

Inquiry reservation precedes network calls. The n8n run request and email-run key
are stable per source event. n8n verifies the fixed remote graph and successful
saved execution output before the task is committed. Email is enqueued only after
that task exists. It uses the existing durable outbox and provider idempotency key.
Ambiguous n8n or email submissions are retained and never blindly replayed.

Identical webhook retries acknowledge the saved attempt; they do not retry its
side effects. The owner's Retry action uses original IDs and inputs. An uncertain
n8n submission is blocked pending inspection. A failed/uncertain email attempt
must use the existing outbox's read-only reconciliation endpoint; Retry never
creates a fresh send ID. Restart recovery resumes only safely identifiable work.

Sources can pause and rotate their key. Rotation immediately invalidates the old
key. Paused sources cannot accept new events; existing accepted events remain
readable. Rotate does not resume a paused source; create a newly reviewed source
when work should resume. Source creation itself is idempotent by request UUID.

Intake uses its own source key, never the workspace cookie or bearer token.
Payloads are bounded to 8 KB, general inquiry text to 2,000 characters, and intake
attempts to 30 per source/client per minute per process. Run one SQLite API
worker/replica. This is a bounded pilot limit, not distributed abuse prevention.
Public deployment should retain HTTPS and upstream request limits.

## API contracts

Owner authentication protects:

| Endpoint | Purpose |
|---|---|
| `GET/POST /inquiry-sources` | List safe settings / create reviewed source |
| `GET /inquiry-sources/{id}` | Safe settings without key/hash |
| `POST /inquiry-sources/{id}/pause` | `{"confirm_pause":true}` |
| `POST /inquiry-sources/{id}/rotate-key` | `{"confirm_rotation":true}`, key once |
| `GET /inquiries` | Durable inquiries, tasks and current email evidence |
| `GET /inquiries/{id}` | One inquiry's saved state |
| `POST /inquiries/{id}/retry` | `{"confirm_retry":true}`, original keys |
| `GET /outcomes/summary` | Counts from actual inquiry/task/outbox records |

Machine ingress: `POST /intake/{source_uuid}` with `X-Inquiry-Key`.
Successful acceptance returns 202 and only accepted/id/status, not private
customer/CRM/provider details. A saved blocked or uncertain attempt is still
accepted for review; acceptance does not mean successful processing or delivery.

Lists and metrics exclude mock sources by default. `include_demo=true` explicitly
includes fictional records. Outcomes measure inquiries received, verified task
creation, pending/blocked/uncertain work, overdue/completed tasks, submitted/sent/
delivered/failed email, safely stopped email (skipped/cancelled), and mean time to
task creation. Failed counts provider failures, bounces, complaints and
suppression; stopping before submission is recorded separately. Task creation time is not
customer response time. There are no inferred revenue, booking or time-saved
claims. Provider acceptance is submitted; delivered needs verified provider
evidence. Later bounce/complaint/suppression can replace delivered state and
persist an opt-out.

## Local owned-recipient email check without public hosting

Automatic **email sources** require a public HTTPS callback origin so outcomes can
arrive independently. Task-only sources and n8n checks work locally without it.
For an operator-consented, one-off local email check before hosting is available,
the existing low-level runner supports `POST /workflows/{workflow_id}/runs` with
`mode:"email"`, literal `confirm_send:true`, a new stable idempotency key, an
explicit permitted contact, your owned recipient, reviewed subject and message.
It still requires `ENABLE_EMAIL_DELIVERY`, `APP_API_TOKEN`, `RESEND_API_KEY` and
the verified `RESEND_FROM_EMAIL`; mock businesses remain blocked. The source's
automatic email guard is not relaxed by this separate check.

After submission, inspect the saved `/workflow-outbox` record. If there is no
public callback, use the Resend dashboard's exact provider email ID with
`POST /workflow-outbox/{outbox_id}/reconcile` and
`{"provider_email_id":"<provider UUID>","confirm_provider_record":true}`.
The API key must allow reading that provider record. Reconciliation is a read-only
GET and matches recipient, sender and subject before accepting its outcome.
An uncertain attempt must be reconciled, never retried with a fresh send key.
This proves only that consented test message's outcome; it does not establish
automatic inquiry email operation or continuous public callback delivery.

Retained live inquiry evidence: `.local/complete-automation/n8n/intake-live-proof.json`
records an authenticated ASGI intake route against real local n8n 2.42.6,
the saved execution ID, one fictional CRM task, safe identical retry/conflict,
source pause and demo exclusion. That check sent no customer messages and does
not establish a public HTTPS deployment or live Resend operation.
