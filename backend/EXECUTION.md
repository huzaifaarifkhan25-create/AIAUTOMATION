# Durable sandbox workflow runner

Version 0.6.0 adds browser sandbox controls, appointment events, and opt-in email.
This document describes the sandbox channel; see [HACKATHON.md](HACKATHON.md)
for appointment/email contracts, setup, delivery evidence, and remaining limits.
Version 0.9 serializes evidence commits and workflow archiving with runner actions.
Known email recipient opt-outs are retained across contact-ID changes; see the
[backend handoff](HANDOFF.md) for the current reliability guarantees.

The first execution milestone runs generated message workflows inside the API
process. It receives an authenticated event, checks permission and current
workflow/evidence, waits for configured timing, creates a local outbox preview,
and records its result. SQLite retains runs, progress, retries, and previews.
There are no network actions or delivery-provider calls in sandbox mode.

This is a working local action engine with a **sandbox channel**. A succeeded
run means `sandbox_recorded`, never sent, delivered, or booked. The saved workflow
contract still reports `execution_supported=false` for external/client execution.
`/capabilities` exposes sandbox mode on SQLite, adding email only when enabled
and configured. The browser Automation lab has sandbox reminder controls.

## Start and inspect a run

Create a workflow from the latest saved supported analysis, then:

```http
POST /workflows/WORKFLOW_ID/runs
Content-Type: application/json
Authorization: Bearer YOUR_CONFIGURED_TOKEN
```

```json
{
  "mode": "sandbox",
  "confirm_sandbox": true,
  "idempotency_key": "synthetic-reminder-001",
  "event": {
    "contact_id": "synthetic-contact-001",
    "contact_permission": true,
    "appointment_cancelled": false
  },
  "message_body": "Synthetic reminder preview only.",
  "scheduled_at": "2026-10-08T12:00:00+05:00"
}
```

Use synthetic events/text in development. No recipient phone/email, patient
name, or medical information is required. Contact references are opaque strings
of 1–100 letters/digits/underscore/dot/colon/hyphen. Permission/cancellation
must be JSON booleans. Unrecognized fields are rejected. Email mode has its own explicit request contract. Only sandbox mode is described here.
message_body is explicit operator configuration, limited to 1,000 characters;
the runner does not invent a customer message from an analysis recommendation.

`scheduled_at` needs a timezone and is required for reminder, consultation
follow-up, and rebooking delay nodes. Past times catch up on the next worker
cycle. Inquiry follow-up has no delay; omit scheduled_at. No timing is silently
chosen. The supplied event is an assertion, not independent consent verification.

| Route | Purpose |
|---|---|
| `POST /workflows/{id}/runs` | Persist a run; HTTP 202 returns its current status |
| `GET /workflow-runs?workflow_id=...` | Run history list, newest first |
| `GET /workflow-runs/{id}` | Status, snapshot, step progress, attempts, timestamps, history |
| `POST /workflow-runs/{id}/cancel` | Cancel active work; repeating cancellation is safe |
| `GET /workflow-outbox?run_id=...` | Saved previews, each explicitly `sent=false` |

List routes accept limit 1–500 (default 100) and offset >=0. All routes use the
existing data authentication. Run status is queued, running, waiting, retry_wait,
succeeded, skipped, cancelled, or failed. Each run retains up to 200 most recent
history entries. Terminal runs do not restart when the same event is submitted.
Cancel after completion returns 409; any existing preview remains historical.

## Persistence and failure behavior

- The key is scoped to workflow ID. Identical inputs reuse one record; different
  inputs with the same key return 409 `run_key_conflict`. Repeated completed or
  cancelled events cannot re-create previews.
- Outbox IDs are deterministic for run + message step. Atomic SQLite reservation
  prevents duplicates when the service stops after saving an effect but before
  saving progress. This guarantee covers local actions; it makes no promise about
  future external provider delivery.
- Transient storage errors schedule retries after one and two seconds, with at
  most three attempts per step. Other action failures stop. If storage cannot
  even save failure state, the worker retries its storage cycle until storage
  recovers; no outbound network action can occur.
- App startup resumes unfinished local steps and saved waits. Running steps are
  marked queued with a recovery history entry. Scheduled times remain durable.
- Guards reject archived, changed, superseded, missing, or do-not-contact workflows.
  Permission=false or appointment_cancelled=true skips the run. Active waits also
  check workflow/business guards; retry backoff is honored before checking again.
  Operator cancellation provides the current manual revocation path. There is no
  live client consent/calendar connection yet.
- SQLite backup/recovery includes these records automatically. Never overwrite
  primary data during a recovery test.

Run exactly one worker and one replica. The scheduler polls about twice a second
and currently loads records into memory; large queues need indexed due-time
queries and a worker-claim/lease design. There is no distributed lease. Do not
point multiple API processes at the same database. Supabase runner routes return
503 `runner_storage_unsupported`; existing Supabase research routes are unchanged.
Only the exact generated message graphs are supported. Arbitrary graphs and
calendar nodes return 409 `workflow_unsupported`, before a run is queued.

## Validation and next integration

Run the normal Python suite from backend/; tests/test_execution.py covers real
local persistence, scheduling, idempotency, permissions, cancellation, bounded
retries, restart replay, backup/recovery, authentication, and unsupported inputs.
`deploy/verify.py` additionally stops/restarts an actual production container
while a synthetic run is waiting and verifies one preview after its due time.
Neither test path sends messages or contacts a real business.

Before adding live delivery, implement a provider adapter, securely bind its
credentials, map approved templates/recipient permissions, persist provider IDs,
and handle delivery callbacks and uncertain submissions. External operations
need their own idempotency and reconciliation; do not enable blind retries.
