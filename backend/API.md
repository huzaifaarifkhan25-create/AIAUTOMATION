# Backend API guide

Development request/response schemas are in `/docs` and `/openapi.json`.
Production disables these public schema pages; the endpoint contracts remain supported.

For free scraper exports, use `POST /businesses/import-csv` with a raw UTF-8 CSV
body and Content-Type: text/csv. Query parameters: source, dry_run (default true),
collected_at, file_name, column_map (JSON object of target field to exact header).
Name and address are required. Preview saves no records; committing skips duplicates
and existing data, saves valid rows, and reports invalid rows. Limits: 2 MB, 2,000 rows.
Saved records retain source/provider provenance without changing the six business fields.
See [SCRAPING.md](SCRAPING.md) for complete rules, examples, and the free tool setup.
The local browser pilot exports CSV for this endpoint with source=csv. Supply the
manifest's collection timestamp as collected_at; extra CSV category/date columns
are ignored by the importer and remain in the raw evidence. Browser collection
uses either the CLI or the authenticated `/discovery/jobs` pilot. It is not launched
by `/businesses/search`, which still defaults to mock.

## Discover and persist

`POST /businesses/search` accepts industry, location, optional source (`mock` or
`google_places`), and limit (1–20). `POST /businesses/import` accepts the same input
and saves results. Search alone does not save. `POST /businesses` saves a manual
normalized business. Saved records include id, source, business, and timestamps.
`GET /businesses` supports limit (1–500) and offset.

Repeated saves reuse an existing normalized name/address match, including CSV
Place-ID records, without replacing fields, provenance, or timestamps. Import/save
identity checks share a process-local lock: run one worker/replica.

Google discovery requires `GOOGLE_PLACES_API_KEY`, Places API (New) access, and
egress to `places.googleapis.com`. It requests phone and website fields, which can
require a higher pricing tier. A search returns at most 20 listings, not every
business in a city. Missing credentials return 503, never mock results labeled real.

## Analyze evidence

`POST /businesses/{id}/analyze` accepts:

```json
{
  "fetch_website": false,
  "use_ai": false,
  "evidence": [
    {
      "criterion": "inquiry_followup",
      "assessment": "strong",
      "source": "business_confirmation",
      "detail": "The owner confirmed inquiries are tracked manually without follow-up."
    }
  ]
}
```

Evidence is an operator's assertion: supply real observations, not invented
business confirmation. Assessment is strong (full points), partial (half), clear
(assessed, zero), or unknown (unassessed, zero). Sources: business_confirmation,
public_website, public_listing, manual_research. Maximum 12 distinct criteria.
Explicit evidence overrides automatic observations for the same criterion.
Observation timestamps default to current UTC; supplied dates require a timezone
and cannot be in the future. Internal operational gaps require business confirmation.

Evidence includes `origin`: `operator`, `automatic`, or `unspecified` (default).
New automatic observations are tagged. The workspace tags operator edits; legacy
records keep unspecified origin. With `fetch_website=true`, supplied automatic
entries are discarded and recomputed; operator/unspecified evidence retains its
date and must be reviewed. Without a fetch, supplied automatic evidence is retained.
Listing phone observations use the original collection/update date. Plausible
number syntax supports contact scoring, not proof of reachability.

| Criterion | Component | Maximum |
|---|---|---:|
| inquiry_followup | N | 10 |
| appointment_reminders | N | 10 |
| consultation_followup | N | 10 |
| rebooking | N | 10 |
| public_email | C | 8 |
| business_phone | C | 6 |
| inquiry_form | C | 6 |
| operational_scale | V | 10 |
| recurring_services | V | 10 |
| booking_friction | D | 10 |
| inquiry_friction | D | 5 |
| intake_friction | D | 5 |

For scale, assess one practitioner as clear; two or three as partial; four or more
or multiple locations as strong. For recurrence, no documented repeat offering
is clear; one repeat treatment/package is partial; multiple repeat treatments,
memberships, or packages are strong. Include supporting counts/details. The server
does not independently verify manual assessments.

```text
need_score = round(100 * (N + D) / 60)
sales_score = round(100 * (C + V) / 40)
total_score = N + C + V + D
```

Need/sales scores use Python's round-to-even for exact half ties. Total can include
half points. Coverage is the sum of maximum points for assessed criteria, not a
statistical confidence estimate. Below 70% coverage, priority is research and
analysis is provisional. Otherwise priority is high (80+), medium (60+), low (40+),
or insufficient_evidence. Unknown criteria remain visible; zero is not proof of no need.

`fetch_website=true` reads the saved website's static public HTML. Configure its
exact trusted hostname in `WEBSITE_ALLOWED_HOSTS` and the network allowlist.
HTTPS and public DNS are required. Redirects are rejected by default and response
size is bounded at 1 MB of decoded content. Set WEBSITE_FOLLOW_REDIRECTS=true to
allow at most three redirects; every destination must independently pass the same
HTTPS, hostname allowlist, and public-address checks. The final URL is retained.
If local DNS is unavailable, WEBSITE_DNS_OVER_HTTPS=true enables a fixed Google
HTTPS DNS resolver at dns.google. Allow that domain in network settings. Both A
and AAAA answers are checked, private/invalid/empty results fail closed, and private
local answers never trigger this fallback. Both settings default to false.
Only allow trusted hostnames; egress policy is an additional boundary.
This is not a JavaScript browser. A booking link's presence or absence leaves
booking friction unknown, with zero points and no assessed coverage. Assess the
actual customer journey before recording friction. Static forms are not assumed to submit successfully.
Booking detection examines both link destinations and visible button text, so a
Book Now button targeting an external widget is recognized. A detected booking
link does not verify that booking can be completed.

On 2026-10-06, five official pilot sites were retrieved through the cloud HTTPS
proxy and operator-reviewed analyses were saved with retained HTML, source URLs,
timestamps, and checksums. Two listings had phone discrepancies with their websites.
All five remain provisional research records; no internal operational gaps were
confirmed. After dns.google access became available, all five sites also passed
live API analysis with fetch_website=true and use_ai=false (HTTP 201). Previously
reviewed evidence was supplied explicitly so scale/membership facts and phone
discrepancies remained in the new snapshots. Each new analysis was read back
through the API. HTTPS DNS fallback and Trifecta's canonical redirect now work
live for the five-site pilot. Other websites require their own access checks.

`use_ai=true` adds a structured summary/questions using `LLM_API_KEY`, `LLM_MODEL`,
and `api.openai.com`. AI cannot assign or change scores. Public business data,
provided evidence, and fetched text are sent to the provider; keep patient data
out of these inputs. Missing credentials return 503; provider failures return 502.

Analyses are saved snapshots. `GET /analyses` supports business_id, limit, offset;
`GET /analyses/{id}` retrieves one. Failed analyses are not partially persisted.

## Rank, contact, and generate workflows

`GET /opportunities` ranks the latest analysis per business. Provisional analyses
are excluded unless include_provisional=true. Limit is 1–500, default 100.
Demo records are excluded unless include_demo=true; do-not-contact records are
always excluded. Original need/sales/total formulas remain unchanged.

## Two-stage qualification

`GET /prospects` ranks businesses by the latest saved contact/business-fit evidence.
`GET /businesses/{id}/qualification` returns one business's current stages.
These authenticated routes derive results at read time, preserving historical
analysis JSON. No migration, website fetch, inference of internal operations, or
new analysis snapshot is performed. An unanalyzed business stays not_analyzed.

- `prospect_score = round(100 * (C + V) / 40)`, equivalent to the existing sales_score.
- `public_evidence_coverage = 100 * assessed C+V maximum weight / 40`.
  Clear is assessed but earns zero points; unknown is unassessed.
- `prospect_status=ready_for_review` needs score >=40, public coverage >=40%, and
  a supported contact route. Phone/email strong or partial can support a route;
  an inquiry form must be strong (a detected untested form alone is insufficient).
  Other states are research, not_analyzed, and do_not_contact.
- These thresholds are initial screening heuristics, not calibrated probabilities,
  guaranteed reachability, confirmed internal need, or evidence of willingness to buy.
- `need_status` is confirmed_gap only with strong/partial N evidence sourced to
  business_confirmation; observed_friction means strong/partial D evidence; it
  does not establish an internal gap. assessed_no_gap requires all N+D criteria
  explicitly clear; otherwise the status is unconfirmed.
- `need_review_ready` requires a recorded gap (confirmed N or observed D), the
  existing >=70% overall coverage gate, and no do-not-contact stage. This means
  ready for human need review, not workflow execution.

Default prospect ranking excludes mock and do-not-contact records. Set
include_demo=true and/or include_blocked=true to inspect them; is_demo remains
explicit. Supported limit is 1–500 (default 100), with offset >=0. Review-ready
records rank first, then research, unanalyzed, and blocked; within a stage, score
and public coverage descend, followed by stable business ID. Stage/contact notes
cannot establish business-confirmed need. All original need/sales/total formulas
remain unchanged; `/opportunities` now defaults to excluding demos and opt-outs.

The five recorded live leads now rank as prospect-review ready, while their
internal needs remain unconfirmed: ZZ 85, Trifecta 65, Perfect 48, Dolce 40,
Tribeca 40. These figures use the previously retained observations, not new scraping.
Their original phone discrepancies and need-provisional analyses remain intact.

`GET /businesses/{id}/outreach-draft?analysis_id=...` creates a draft; it sends
nothing. The analysis must belong to that business and be its latest saved analysis;
an older analysis returns 409 `analysis_outdated`.
Drafts return kind=discovery unless strong/partial operational evidence is sourced
to business_confirmation; discovery wording asks about processes without asserting
an internal problem. kind=confirmed_need references the recorded discussion and
still requires human review. A do_not_contact stage blocks draft generation with 409.
`PATCH /businesses/{id}/contact`
accepts stage and notes. Stages: new, contacted, interested, demo_booked, won, lost,
do_not_contact. On SQLite this atomically stores status plus contact history; identical updates
reuse the current state. Manual activity and task routes are described in
[MVP.md](MVP.md). Contact entries do not themselves establish operational need.

`POST /workflows` accepts `{"analysis_id":"saved-analysis-id"}`. It
requires the latest saved analysis; an older one returns 409 `analysis_outdated`.
Do-not-contact records cannot generate new workflow drafts. Historical workflow
readback/export remains available for review.
The template uses confirmed operational gaps first, then tentative booking/inquiry friction.
Without a supported opportunity it returns 409. A provisional analysis can create
a draft, not deployment approval. Graphs include a trigger, permission check,
optional timing/calendar step, message action, and result record. Required
configuration is listed. `execution_supported=false` remains the general external/client flag. Saving/exporting
does not run a graph. Supported generated message graphs can be explicitly queued
through the sandbox runner or configured email channel described below.

`GET /workflows` supports business_id, limit, offset. Retrieve/export via
`GET /workflows/{id}` and `GET /workflows/{id}/export`. Archive without deleting via
`POST /workflows/{id}/archive`. The internal JSON format is not native n8n JSON.

## Sandbox execution

`POST /workflows/{id}/runs` accepts explicit sandbox mode, confirmation, an
idempotency key, a typed event, an operator message, and configured timing.
`GET /workflow-runs` lists runs; `GET /workflow-runs/{id}` reads progress/history;
`POST /workflow-runs/{id}/cancel` cancels active work. `GET /workflow-outbox`
lists saved local previews. All routes use data authentication and require SQLite.
The runner resumes unfinished local work on startup with one API worker/replica.
Outbox previews remain sent=false. Full contracts, examples, scheduling, retry,
recovery behavior, and limits are in [EXECUTION.md](EXECUTION.md).
The existing external execution flags remain false; `/capabilities` separately
reports sandbox mode for this local channel, adding email only when enabled and
configured.

## Appointment events and opt-in reminder email

Version 0.6.0 adds `POST`/`GET /appointments`, `GET /appointments/{id}`, and
`POST /appointments/{id}/cancel`. Appointment input includes a generated reminder
workflow, future timezone-aware start, and explicit reminder request/time.
`POST /demo/reminder-workflow` explicitly scaffolds a fictional sandbox demo.
The browser Automation lab offers sandbox controls, history, previews, and cancellation.

`POST /workflows/{id}/runs` also accepts mode=email with literal confirm_send=true,
recipient_email, subject, message_body, event permission, and required timing.
Email defaults disabled and requires shared-token access, RESEND_API_KEY, verified
RESEND_FROM_EMAIL, and ENABLE_EMAIL_DELIVERY=true. `POST /webhooks/resend` uses
Resend signatures with a direct-runtime RESEND_WEBHOOK_SECRET, not bearer auth.
API acceptance is submitted, not sent/delivered. Signed events update the outbox.
Uncertain submissions cannot automatically resend; authenticated
`POST /workflow-outbox/{id}/reconcile` performs only a provider read/match.
`POST /businesses/{id}/automation-contacts/{contact_id}/opt-out` stores an opt-out
that later event permission cannot override. All execution storage remains SQLite.
See [HACKATHON.md](HACKATHON.md) for full bodies, guards, recovery, configuration,
and the distinction between simulated tests and unverified live email.
Appointment events do not provide booking availability or calendar integration.

## Human click-to-call

Twilio first calls SALES_AGENT_NUMBER, then connects the human agent to the prospect.
Required settings: APP_API_TOKEN, ENABLE_OUTBOUND_CALLS=true, TWILIO_ACCOUNT_SID,
TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER, SALES_AGENT_NUMBER; allow api.twilio.com.
Use international E.164 numbers and a provider-authorized caller ID. Ordinary
formatting spaces/dashes are normalized. Twilio requires HTTP Basic authentication:
the token must be available at runtime or the environment proxy must support that
encoding. An untested proxy placeholder does not prove authentication works.

`POST /businesses/{id}/calls` accepts:

```json
{"idempotency_key":"unique-request-key","confirm_outbound_call":true}
```

The endpoint requires API authentication and explicit confirmation. Mock businesses
and do_not_contact businesses cannot be called. Responses mean submitted, not
answered/completed. No recording or AI voice calling is enabled.

The key is atomically reserved before contacting Twilio. Repeating a submitted key
returns its existing record. A failed/uncertain attempt cannot automatically retry:
the same key returns 409. Check the provider dashboard before creating another
key. `GET /calls` and `GET /calls/{id}` read local attempts. Version 0.7 adds signed
Twilio callbacks at `/webhooks/twilio/calls/{id}` when APP_PUBLIC_URL is configured,
and authenticated read-only `POST /calls/{id}/reconcile`. Outcomes refer to the
sales-agent leg; they do not establish that the prospect answered. See
[MVP.md](MVP.md) for direct-runtime signing credentials and uncertain outcomes.
Malformed provider call IDs also leave the attempt failed/uncertain; submissions
are accepted only with a `CA` prefix followed by 32 hexadecimal characters.

## Client onboarding, local activation and operations

Version 0.7 implements authenticated client profiles, approval references,
sandbox-tested workflow validation/activation, managed runs/appointments,
pause/archive guards, audit history and secret-free client handoff.
Version 0.8 connects client onboarding, reviewed sandbox activation, managed
reminders, handoff downloads, manual tasks and operations in the browser.
See [WORKSPACE.md](WORKSPACE.md) for its walkthrough. Live email/calling remains
API-only and unverified with real providers.
Version 0.9 adds `deployment_readiness` operations alerts for active setups whose
current checks fail or whose saved validation fingerprint is stale. Missing saved
references produce `deployment_reference_missing`; storage failures remain errors.
These checks do not mutate activation or establish provider connectivity.
`GET /operations/summary` reports current counts, scheduler state and bounded
alerts for failed/pending/overdue work, excluding demos by default.
These features require SQLite and one API worker/replica. They do not provision
public hosting or individual login accounts. Full endpoint tables and request
bodies are in [MVP.md](MVP.md).

## Persistence, readiness, and errors

For Supabase, run supabase.sql in the project's SQL editor, configure SUPABASE_URL
and the backend service-role SUPABASE_KEY securely, allow the exact project host,
select PERSISTENCE_BACKEND=supabase, restart, then check `/ready`. RLS denies public
table access. Do not put service-role credentials in frontend code. SQLite data
is not automatically migrated. List operations support API pagination but the
MVP storage adapter loads records before filtering; large datasets need indexed
server-side queries.
Supabase listing halves its batch size on oversized decoded responses, down to
one record, while preserving pagination. This has simulated regression coverage;
it does not establish live Supabase access.

For SQLite, `backend/backup.py` creates consistent database-plus-scraper backups,
verifies hashes/integrity, and restores to a new directory. See
[recovery instructions](../deploy/README.md#backup-and-recovery).

Health is liveness only. `/ready` checks selected storage. `/capabilities` reports
configuration presence, not verified access. Data, readiness, and capability
routes require bearer authentication when APP_API_TOKEN is configured. Health is
public. Documentation is public in development and disabled in production.
Production startup requires a token of at least 32 printable non-space characters
and explicit APP_ALLOWED_HOSTS. The shared token is MVP access control, not a
multi-user authorization system. Keep default loopback binding until deployed securely.

Validation errors use HTTP 422 with FastAPI's detail format. Application errors use
`{"error":{"code":"...","message":"..."}}`: 404 missing record, 409 conflict,
503 missing/unavailable configuration, 502 upstream failure. Provider bodies and
credentials are not returned. The browser workspace and single-worker pilot jobs
are implemented. Portable production packaging is documented in
[deploy/README.md](../deploy/README.md). Public hosting, distributed jobs, general external/client workflow execution,
automatic prospect outreach, user accounts, and AI calling remain future work.
The configured reminder email adapter is implemented but unverified live.
