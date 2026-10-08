# Shared-workspace backend MVP — v0.10.0

The backend now supports the seven-stage pilot: discover, analyze, rank, record
contact activity, generate supported workflows, execute reminders, and prepare
client handoff. This is a single-operator workspace with SQLite and one API
worker/replica. The browser connects research, reminders, client onboarding,
manual follow-up tasks and operations. See [WORKSPACE.md](WORKSPACE.md) for the
new browser walkthrough; the endpoint contracts below remain current.
Version 0.10 adopts a [HubSpot-inspired CRM interface](CRM_DESIGN.md); saved-record
search, lead views and sorting use existing data without changing API contracts.

Code completion and live integration verification are separate. Email and human
dialing have simulated provider coverage. Actual provider credentials, a verified
sender/caller, public HTTPS callback hosting and live verification are outstanding.
No real business was contacted during development or testing.

Version 0.9 closes reproduced reliability gaps: known recipient opt-outs survive
contact-ID changes and restarts, local dialer validation leaves retry keys unused,
contact/evidence/archive changes share action guards, and Operations flags active
setups whose validation no longer permits execution. Endpoint contracts remain
compatible. See [HANDOFF.md](HANDOFF.md) for completion scope and live requirements.

## Run the complete fictional client demo

Start the API as described in the repository README, then explicitly run:

```bash
.venv/bin/python backend/client_demo.py
```

The script requires a local HTTP server and SQLite. Supply the server's shared
`APP_API_TOKEN` in the script's runtime when configured; never pass it on the command
line. The script writes clearly labeled fictional demo records. Use a separate
database when verifying existing real leads. It creates/reuses a fictional
workflow, records contact/task history, onboards a demo client, executes a sandbox
proof, validates and activates a local sandbox deployment, schedules a managed
appointment reminder, completes its task, and reads handoff/operations data.
It creates unsent previews only. Repeating the script reuses the client/deployment
and creates separate explicitly keyed demo events.

## Contact activity and manual tasks

| Route | Contract |
|---|---|
| `PATCH /businesses/{id}/contact` | Existing stage/notes contract; SQLite now atomically records history; identical updates reuse current state |
| `POST /businesses/{id}/activities` | `idempotency_key`, kind=`note/call/email/meeting`, direction=`incoming/outgoing/internal`, notes, timezone-aware `occurred_at` |
| `GET /businesses/{id}/activities` | Chronological operator/stage/task history plus current call/run summaries |
| `POST /businesses/{id}/tasks` | `idempotency_key`, title, optional notes and timezone-aware `due_at` |
| `GET /tasks` | Filter by business_id, status, overdue; paginate |
| `GET /tasks/{id}` | Saved task |
| `PATCH /tasks/{id}` | Finish a pending task with status=`completed/cancelled`; repeated same status is safe |

Activity dates cannot be in the future. A recorded phone/email/meeting activity is
an operator assertion about contact, not provider delivery evidence or confirmation
of operational need. It never creates analysis evidence. New tasks are blocked for
do-not-contact businesses; existing history remains readable. Tasks are manual
follow-up records, not an automatic prospect outreach sender. Task dates may be
past to represent overdue work. Mutation keys conflict if reused with changed inputs.

## Human dialer outcomes

Existing `POST /businesses/{id}/calls` retains explicit confirmation, disabled
defaults, mock/opt-out blocking and durable reservation. Confirmation now rejects
string/integer coercion. Calls first ring the sales agent, then bridge to the
prospect. `GET /calls/{id}` reads one attempt.

Optional `APP_PUBLIC_URL` is the exact public HTTPS app origin, with no path,
query, credentials or nonstandard port. In production its hostname must appear
in `APP_ALLOWED_HOSTS`. When configured, submission registers a completed-event
callback at `/webhooks/twilio/calls/{local_call_id}`. The endpoint verifies the
Twilio HMAC-SHA1 signature against the configured public URL and form fields,
checks account/SID/from/to against the reserved attempt, and persists bounded
events. It uses provider signatures, not the workspace token. Exact duplicate
events are safe; stale sequences cannot roll back a terminal outcome.

These are **sales-agent leg** outcomes. A completed agent call does not prove that
the prospect answered. There is no AI voice or recording feature. Submissions remain
`submitted` until provider evidence; terminal attempts have status=`finished` with
the separate `provider_status` (`completed`, `busy`, `failed`, `no-answer`, or
`canceled`). Returning a previously submitted/finished key never makes another call.

For an uncertain attempt, authenticated `POST /calls/{id}/reconcile` accepts:

```json
{"provider_call_id":"CA_ACTUAL_32_HEX_CHARACTERS","confirm_provider_record":true}
```

Use an actual provider SID. Reconciliation performs a provider **GET only**, matches
account/from/to/known ID, and updates outcomes without dialing. Old pre-v0.7
attempts without reserved number/account metadata remain readable but cannot be
automatically matched. There is no automatic retry of uncertain calls.

Twilio signature verification needs the actual `TWILIO_AUTH_TOKEN` at runtime;
a network-proxy placeholder cannot compute the provider's HMAC locally. Twilio REST
also needs supported Basic Auth propagation. Set the token securely on the hosting
service, never in the browser, chat, docs or repository. Live proof remains absent.
The signature implementation was checked against Twilio's official Python validator.

## Client onboarding and managed workflow activation

`POST /clients` accepts:

```json
{
  "business_id":"SAVED_BUSINESS_ID",
  "idempotency_key":"client-001",
  "contact_name":"APPROVED_CLIENT_CONTACT",
  "contact_email":null,
  "timezone":"Asia/Karachi",
  "approval_reference":"REFERENCE_TO_ACTUAL_BUSINESS_AUTHORIZATION",
  "confirm_business_authorization":true
}
```

Replace placeholders with actual approved values; use synthetic values only for
labeled demo businesses. Authorization is an explicit operator record, not an
independently verified signature. IANA timezones are validated. One non-archived
client is allowed per business. Profile status starts `onboarding`; `GET /clients`
and `GET /clients/{id}` read it. `POST /clients/{id}/activate` requires
`{"confirm_authorization":true}`. Pause/archive use `POST /clients/{id}/pause`
or `/archive`. Archives are final; previous data remains available.

`POST /clients/{id}/deployments` accepts `idempotency_key`, `workflow_id`, and
channel=`sandbox/email`. This creates a local `draft` and verifies ownership.
It does not provision another server. Read/list with `GET /deployments` (optional
client_id filter) and `GET /deployments/{id}`.

1. Execute a successful sandbox run of the exact generated workflow. See
   [EXECUTION.md](EXECUTION.md). Demo evidence belongs only to mocked businesses.
2. Read `GET /deployments/{id}/preflight`; then explicitly
   `POST /deployments/{id}/validate` to persist its checks and audit event.
3. Activate a validated deployment with `POST /deployments/{id}/activate`
   and `{"confirm_activation":true}`. Failed/stale validation returns a conflict.
4. Submit explicit event inputs through `POST /deployments/{id}/runs`. Its body
   is the existing sandbox/email run request. Channel/workflow must match.
5. For reminders, `POST /deployments/{id}/appointments` accepts the existing
   appointment body in [HACKATHON.md](HACKATHON.md). Read/cancel through the normal
   appointment/run routes.

Checks require an active authorized client, current/unarchived workflow,
matching business, no do-not-contact state, supported generated message graph,
and a successful sandbox proof. Email additionally requires a non-mock business,
business confirmation of the workflow's operational scope, enabled/configured
sender/provider access, and a valid signing secret plus public callback origin.
Configuration presence does not prove live delivery. Customer event permission
and stored opt-outs are still checked by the runner.

Validation fingerprints bind the current workflow/client/sender and stable sandbox
proof. Changed evidence, client state or sender requires renewed validation. Pause
with `POST /deployments/{id}/pause`; validate again before reactivation. Archive
with `/archive`. Paused/archived clients or deployments prevent new managed events
and stop pending managed runs, including during waits. Already submitted messages
cannot be recalled. Stopped runs do not silently resume or resend.

Managed runs/events include a deployment ID and use separate idempotency scopes
from low-level operator runs. Existing low-level research/sandbox API contracts
remain available. Use the managed endpoints for client activation controls.

## Handoff and monitoring

`GET /clients/{id}/handoff` returns an authenticated `medspa-client-handoff-v1`
package containing the client, business/source, qualification/unknowns, workflow
definitions, current preflight checks and operating instructions. Provider keys
and the shared token are excluded. The package is an operator handoff artifact;
it neither provisions public hosting nor creates client login accounts.
`GET /clients/{id}/history` returns timestamped onboarding/activation audit events.

`GET /operations/summary` reports counts by status, active runs, scheduler state
and actionable alerts: failed/retrying runs, uncertain/negative message outcomes,
overdue tasks, uncertain calls, pending/failed appointments and interrupted/failed
discovery. It includes no message bodies, recipients or secrets. Demos are excluded
by default; `include_demo=true` explicitly includes them. `alert_limit` is 1–500,
default 100, with a truncation indicator. This is API monitoring; no external
alerting service or log exporter has been configured.

All new data routes require the configured shared bearer token. Lists use
`limit` 1–500 and `offset` >=0. These new execution/client/CRM features require
SQLite; unsupported Supabase routes return 503 while existing research routes
remain usable. Atomic local writes retain related state/audit entries together.
Consistent backup/restore includes all new records automatically.

## Completion boundary

The supported shared-workspace backend MVP is implemented. Public publication,
real provider credentials and successful live email/call checks remain required
before claiming live operation. Individual accounts/roles, AI voice, native
calendar/availability, arbitrary workflows/native n8n, SMS, automatic prospect
email campaigns, billing and distributed queues are outside this pilot's implemented
scope. The five real leads retain unconfirmed internal needs. See
[STATUS.md](STATUS.md) and [VERIFICATION.md](VERIFICATION.md) for current evidence.
