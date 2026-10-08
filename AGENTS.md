# Med Spa Automation Platform

## Product direction

Target industry: med spas.
Long-term workflow: Discover → Analyze → Rank → Contact → Build → Automate → Deliver.
Build the backend first with Python, FastAPI, and Pydantic. Add httpx and
python-dotenv to runtime dependencies only when a feature needs them.
Supabase/PostgreSQL is intended for later persistence and must not block the first endpoints.

## Current scope

The user has authorized completing the backend MVP autonomously through discovery,
website analysis, optional AI summaries, evidence scoring, opportunity ranking,
outreach drafts, contact tracking, workflow JSON generation, and persistence.
Prefer free collection: the local browser pilot in collect_leads.py/maps_browser.cjs
and CSV imports from browser extensions or gosom/google-maps-scraper (MIT).
The pilot uses the pinned image's browser, not the gosom CLI scraping engine:
that engine rejected the cloud's unauthenticated proxy. Keep managed proxy routing
and TLS verification enabled. Five live New York listings were verified and imported;
their five official websites have now been retrieved through the cloud proxy and
operator-reviewed analyses saved with retained source pages. Two phone discrepancies
(Tribeca and Trifecta) are flagged in evidence/summary. Original listing fields are
preserved. All five analyses remain provisional; no internal operational gaps are confirmed.
Automated website fetching now works through the HTTPS DNS fallback: dns.google
access is verified. All five pilot sites returned HTTP 201 from the live analysis
API with fetch_website=true, and saved analyses were read back successfully.
Optional WEBSITE_DNS_OVER_HTTPS and WEBSITE_FOLLOW_REDIRECTS default to false.
HTTPS DNS must check public A/AAAA answers; redirects must validate every destination.
Retain hostname/public-IP checks and verify new sites live; these five successful
checks do not establish universal website coverage or booking functionality.
Paid discovery is optional, not required for the MVP.
Keep the existing Google Places adapter. Use an OpenAI-compatible API for optional
summaries and Supabase for shared persistence; SQLite is the local development fallback.
CSV import must support preview, mapping, validation, provenance, stable Place IDs,
and duplicate skipping. Preserve existing records and report invalid rows.
Do not describe fixture data as live leads or claim the scraper works on Google
Maps until a live collection succeeds. Respect the environment's network policy.
Preserve the mock search behavior and health contract. Mark demo data clearly.
Do not claim an integration works live without a successful live check.
Credential-dependent checks must remain distinct from simulated provider tests.
Human click-to-call may use Twilio; keep calls disabled by default, require API
authentication, explicit per-call confirmation, and persistent idempotency tracking.
Do not actually contact businesses while developing or testing the backend.
The user has now authorized the first browser workspace and its backend connection.
Serve local HTML/CSS/JavaScript from FastAPI, with no separate frontend runtime.
Show sources, evidence dates, coverage, unknowns, and demo labels explicitly.
Static booking-link presence or absence must leave booking friction unknown.
Confirm the actual customer journey before awarding friction points or coverage.
Real collection must never fall back to mock data; preview before importing.
Discovery jobs run on a single API worker and retain status across restarts.
Qualification now has two independent stages. Prospect score is C+V normalized
to 100; public coverage is assessed C+V weight / 40. Initial review readiness
requires score >=40, coverage >=40%, and a recorded supported contact route.
A phone/email strong or partial assessment, or an inquiry form assessed strong,
can support a route; a detected, untested form alone cannot. These are starting
heuristics, not calibrated sales probabilities or verification of reachability.
Preserve the existing need formula and its 70% overall coverage gate. A public-ready
prospect does not establish internal need. Show business-confirmed gaps separately
from observed public friction and unknowns. Derive qualification from the latest
saved evidence without rewriting historical analysis snapshots. Exclude demos and
do-not-contact records from default prospect ranking. Block outreach drafts for
do-not-contact leads; discovery drafts ask about processes without inventing gaps.
AI calling, external workflow execution, billing, and complex user
authentication are separate future integrations; do not claim JSON generation alone executes workflows.
Current deployment work uses a portable Docker image with the same pinned browser
artifact and Python 3.12. Run the collector directly inside that container, without
requiring host Docker access. Preserve the existing Docker collector for development.
Production startup must require a strong shared access token and explicit app hosts.
Never embed secrets, local databases, or research artifacts in a release image.
Public publication requires a chosen hosting account; local container tests do not
establish a public deployment. Keep individual accounts distinct from shared MVP access.
Earlier portable packaging and hardening passed 94 Python tests and 13 production container/UI
checks passed, including one real Maps listing collected with TLS verification,
retained source checksums, and restart persistence. Read deploy/README.md and
backend/VERIFICATION.md before deployment. The release defaults to production,
one worker, bundled local collection, and persistent /data owned by UID/GID 10001.
No real listing was imported during isolated deployment verification. The development
database retains five real CSV leads and two demo records; real internal needs
remain unconfirmed. Public hosting, individual accounts, live dialer credentials,
and workflow execution still need their separate implementation or configuration.

Read backend/STATUS.md before adding features; three research stages work, contact
and build are partial, sandbox automation runs, and external execution/client
delivery remain incomplete.
The current fixture browser suite passes 14 checks; four read-only cohort checks
pass. Preserve repeat-save provenance and Place-ID CSV identities; mixed import/save
checks share a process-local lock, not cross-worker uniqueness. Default opportunities
exclude demo and do-not-contact records. Both outreach and new workflow drafts
require the latest analysis; opt-outs block both. Historical readback remains.
New automatic evidence has origin=automatic; operator UI edits use origin=operator.
Legacy unspecified origins must remain unspecified. Website refresh recomputes
tagged automatic observations and preserves operator/legacy dates for review.
Listing contact dates must not reset on each analysis. Phone syntax is not reachability.
Keep SQLite connections closed and Supabase batches bounded by response-size limits.
Use backend/backup.py for consistent SQLite-plus-scraper recovery to a new directory;
never overwrite primary data. The actual drill recovered 25 records/64 hashed files
without changing original rows. Archive research outside SCRAPE_OUTPUT_DIR separately;
keep private off-host copies. This helper is manual and SQLite only.
Repeated VFS Docker builds can exhaust the cloud disk. Inspect free space and only
remove identified obsolete app images/caches; preserve current images and all data.

The user has authorized the first durable workflow runner. Read backend/EXECUTION.md.
Version 0.5.0 executes only exact generated message graphs in sandbox mode using
SQLite, one worker/replica, and a local outbox. No network/message/call actions occur.
Explicit request message/timing is required; no invented recipient, consent, or
schedule. Retain execution_supported=false for external/client execution and expose
workflow_runner_modes=[sandbox] separately. Supabase runner routes return 503;
calendar and arbitrary graphs are unsupported. Existing research routes still work.
Run/outbox keys persist idempotency; identical events reuse runs, changed inputs
conflict. Atomic local outbox reservation makes interrupted-step replay safe.
Keep retries bounded, due times persistent, cancellation/history readable, and
current analysis/archive/business opt-out guards checked during execution.
Only synthetic events/text belong in development execution checks. Succeeded means
sandbox_recorded with sent=false, never actual delivery. External adapters need
their own idempotency, secure credentials, current consent and reconciliation.
The current Python suite passes 107 tests, including 13 execution regressions.
Do not run production execution verification against the primary research database.

## Historical reminder milestone — v0.6.0

This section supersedes earlier v0.5 sandbox-only scope and check counts.
Read backend/HACKATHON.md, backend/STATUS.md and the top of backend/VERIFICATION.md.
Current tests: 131 Python; nine API/container plus ten production browser checks;
five isolated Automation lab checks and four read-only real-cohort checks.
No business was contacted and no live email was verified. All 25 primary rows
remain unchanged, with five real unconfirmed leads/two demos; primary execution
collections remain empty. Creating the fictional demo is an explicit user action.

The browser Automation lab schedules sandbox reminders, inspects history/unsent
previews and cancels appointments. The demo scaffold uses a clearly mocked
business and synthetic operational evidence; never copy it onto real prospects.
Appointments are durable manually/API-supplied events, not calendar bookings or
availability. Pending writes/enqueues recover on startup and worker cycles.
Persist cancellation before stopping a run; check appointment cancellation/expiry,
latest analysis, archive, business opt-out and stored customer opt-out on execution.
Idempotent repeats reuse appointment/run IDs; changed inputs conflict.

Email mode is opt-in: ENABLE_EMAIL_DELIVERY, APP_API_TOKEN, RESEND_API_KEY and
verified RESEND_FROM_EMAIL. Default is false. Mock businesses cannot send email.
Require explicit recipient/subject/message/event/timing and literal confirm_send=true.
Reserve an outbox before submission with a stable provider idempotency key.
Provider acceptance means submitted, not sent/delivered. Timeouts, ambiguous errors
and crashes around submission must never automatically resend; use read-only
provider reconciliation matching ID, recipient, sender and subject. Preserve
historical failed run status while exposing current outbox delivery evidence.

Resend callbacks verify signed raw bytes, five-minute freshness, bounded headers
and 64 KB body. RESEND_WEBHOOK_SECRET must be the actual direct-runtime secret,
not a proxy placeholder. No bearer token on callbacks; signature is authorization.
Persist minimal event/hash data; dedupe, reconcile early events and prevent status
rollback. Bounce/complaint/suppression records customer opt-out. Later input consent
cannot override it; no opt-in reset API exists. Do not contact real businesses in tests.

SQLite and one worker/replica remain required. General external/client execution
flags stay false; capabilities expose supported sandbox/email modes separately.
Supabase execution remains 503; arbitrary graphs/native calendar/n8n/SMS/AI calling,
public hosting, individual accounts and client handoff remain incomplete.
Live email needs secure credentials, a verified sender, public HTTPS callback host,
and a consented isolated provider check before any live operation claim.

## Shared-workspace API contracts introduced in v0.7.0

This section supersedes older scope/counts. Read backend/MVP.md and the current
STATUS/VERIFICATION sections. The user explicitly authorized completing its backend.
Historical v0.7 checks: 158 Python tests (27 new), eleven API/container plus ten production
browser checks, two local client demos, four read-only real-cohort checks, and
29-record fixture recovery. All 25 primary research rows remain unchanged and
primary new execution/client collections are empty. No live messages/calls occurred.

SQLite shared-workspace MVP now includes contact/audit history, manual activities
and tasks, reviewed client workflow activation, managed runs/appointments,
client/deployment pause/archive, authenticated handoff and operations monitoring.
Use one worker/replica. Related local state/history writes are atomic transactions.
These new APIs return explicit 503 on Supabase; preserve existing research support.
Activity/task/contact entries cannot create operational evidence or claim delivery.
General external engine flags remain false; specific local activation is supported.

Before client activation require explicit recorded business authorization and
IANA timezone. Deployment activation requires same-business/current supported
workflow, successful sandbox proof, unblocked active client and current preflight.
Email additionally requires business-confirmed workflow scope, non-mock business,
configured sender/access and valid callback secret/public origin. Presence does
not prove live provider operation. Keep stable proof IDs in validation fingerprints;
changed client/evidence/sender requires validation again. Only managed endpoints
apply client deployment scope; low-level operator contracts remain available.
Check deployment/client state during waiting work and before actions. Persist
pause/archive/audit together; serialize state changes with execution. Stopped
runs never silently resume, and submitted messages cannot be recalled.

Twilio outcome callbacks validate its exact configured public HTTPS URL/form HMAC,
account/SID/from/to and monotonic sequences. APP_PUBLIC_URL is now an implemented
optional runtime setting, with origin/host validation. TWILIO_AUTH_TOKEN must be
actual runtime material for HMAC; proxy placeholders cannot compute signatures.
Callback completion describes the sales-agent leg, not prospect answering. Uncertain
calls reconcile by explicit authenticated GET/match only, never automatic redial.
Old attempts missing reserved metadata stay readable but cannot be auto-matched.
No AI calling or recording is implemented. Mock/opt-out and literal confirmation
guards remain mandatory. Never contact real businesses in tests.

backend/client_demo.py explicitly writes fictional data to a local SQLite API,
performs reviewed sandbox activation and managed reminders/handoff, and sends
nothing. Do not run it on primary data during verification. The release bundles
it for isolated production verification. Version 0.8 connects client onboarding,
manual tasks, contact history and operations in the browser; see backend/WORKSPACE.md.
Public hosting, live
provider verification, individual accounts/roles, native calendar/availability,
SMS, automated prospect campaigns, arbitrary workflows/n8n and billing remain
outside this pilot. Do not describe the full production platform as complete.

## Browser client workspace contracts introduced in v0.8.0

The browser supports reviewed client activation, sandbox setup validation and
activation, client/setup pause, managed reminders and secret-free handoff downloads.
Show fresh readiness separately from saved validation. Proof links select the
correct workflow in standalone sandbox mode; managed reminders bind to an eligible
active deployment and its workflow. No live-send/AI-call controls were added.
Keep fictional setup explicit, demos excluded by default, and real needs unknown
until supported business confirmation. Manual tasks/history cannot create evidence.
Render user/provider values with textContent. Preserve mutation keys and pending
inputs after lost responses so retries cannot duplicate records. Guard all responses
with the current access session; locking clears private data and prevents a delayed
response from repopulating it. Never persist the token in browser storage.
Check storage capabilities before loading new client/task/operations endpoints;
unsupported Supabase execution must not break research. Use isolated fixtures only.
Historical v0.8 checks: 158 Python tests, 29 packaged checks (11 API/container + 18 browser),
including eight client browser checks; four read-only real-cohort checks also pass.
Primary logical rows remain unchanged: 25 records, seven businesses, five real
unconfirmed leads, and no primary client/task/execution records. See the current
backend/VERIFICATION.md for retained evidence and exact release image.

## Backend reliability contracts introduced in v0.9.0

The user asked to complete the hackathon backend and fix faults without expanding
the deadline. The current shared-workspace SQLite MVP is implemented across all
seven pilot stages and connected to the browser. Read backend/HANDOFF.md for
actual feature behavior, live prerequisites and limits; do not invent integrations.
Historical v0.9 verification: 170 Python tests, 30 packaged checks (11 API/container +
19 browser, including nine client checks), four read-only real-cohort checks.
Twelve new regressions reproduced previous faults and pass after the fixes.
Primary 25 logical rows/seven businesses/five real unconfirmed leads are unchanged;
primary client/task/execution/permission collections remain empty.

Customer opt-outs block known recipient addresses within their business even
when contact IDs/case change; retain legacy contact-only opt-outs and restart
behavior. Use atomic related permission writes, no implicit re-opt-in, and do
not assume unknown new IDs/addresses identify an opted-out person. Delivery
callbacks/reconciliation and manual opt-outs remain serialized by the runner lock.
Local dialer validation runs before durable call reservation. Missing configuration
or invalid numbers must not consume a retry key; provider uncertainty still forbids
redial. Contact state updates acquire runner then dialer then CRM guards. Evidence
network fetching remains outside the runner guard, but its timestamped commit
and workflow archiving share the action guard. Never reverse these lock orders.
Already submitted provider actions cannot be recalled.
Operations checks active deployment readiness/fingerprints and reports stale or
missing-reference setups even without a new run. Preserve demo exclusion, bounded
alerts, secret-free fields and explicit review/validate/activate behavior. Propagate
storage failures; never silently reactivate a setup. New alert links go to Clients.
Read current VERIFICATION.md for image/evidence. Retain v0.8 rollback image;
obsolete v0.7 image/caches were removed, with data/base images preserved.
No new live scrape/email/call/public hosting was performed. Credentials/hosting
remain required for actual provider verification, securely entered in settings.

## Current CRM interface — v0.10.0

The user has chosen a CRM interface inspired by GoHighLevel or HubSpot and
authorized selecting the fit. HubSpot is the chosen reference because lead
records, public qualification, manual tasks, client profiles and activity history
match this backend. Use its dark navigation, compact record tables, coral primary
actions, teal links, saved views and record details while retaining AIAutomation's
own identity. This is UI inspiration, not a HubSpot integration or a feature clone.
Global search operates on authenticated saved records and the current demo filter;
clear results/query and disable it on lock/reload. Preserve safe text rendering,
keyboard navigation, existing API contracts and all execution/consent guards.
Saved views/sorting must reflect actual qualification, not fabricated sales/revenue
metrics. The dashboard follow-up section uses recorded tasks. Keep short page
titles and consistent backend-linked navigation. Test desktop/mobile and current
research/client/reminder flows before handoff. Native n8n is still not implemented;
the user's n8n question did not authorize representing it as complete.
Current verification: 170 Python tests, 32 packaged checks (11 API/container +
21 browser), six read-only real-cohort checks. Original 25 logical rows are
unchanged. Read backend/CRM_DESIGN.md and current backend/VERIFICATION.md for
design and evidence. The previous v0.9 image is retained; obsolete v0.8 and
the intermediate UI build were removed with only their specifically identified
unused app caches to preserve VFS disk. No volumes or global caches were pruned.

## Development rules

- The user explicitly authorized uploading the current source to their GitHub
  repository and confirmed a Windows laptop. Use a separate branch for this
  upload and preserve their main branch. Publish source, examples and docs only;
  exclude local databases, credentials, scrape artifacts and build caches.
  Windows instructions are in WINDOWS-START-HERE.md with START-WINDOWS.bat.
  A new laptop starts with an empty database; clearly labeled fictional examples
  must be explicit user actions. Keep Windows dependency availability checks
  separate from executing the batch launcher on a real Windows laptop.
- Work on one requested feature at a time; keep changes small and scoped.
- Preserve existing files and API contracts; avoid unrelated refactors.
- Keep route handlers thin. Add services/, models/, and database/ only when needed.
- Use the simplest implementation and only necessary dependencies.
- Never hard-code or commit secrets. Add environment requirements when used.
- Run relevant checks after meaningful changes and keep the project runnable.
- GitHub push is not required. Do not make destructive Git changes.
- Use the existing isolated checkout; do not create worktrees unless requested.
- Explain major architecture changes before applying them.
- Update these durable instructions when the user changes scope or architecture.

## Business contract

Normalized business fields: name, website, phone, address, rating, review_count.
Preserve this contract when business search is implemented. Model missing data
explicitly and add a stable identity when real discovery requires it.

## Agreed scoring model

- N, automation need (0–40): manual inquiry follow-up, appointment reminders,
  consultation follow-up, and rebooking, 10 points each.
- C, ease of contact (0–20): public business email 8, phone 6, working inquiry form 6.
- V, business value (0–20): operational scale 10 and recurring-service potential 10.
  Scale: one practitioner 0; two or three 5; four or more or multiple locations 10.
  Recurrence: no documented repeat offering 0; one repeat treatment or package 5;
  multiple repeat treatments, memberships, or packages 10.
- D, digital weakness (0–20): booking friction 10, inquiry friction 5, intake friction 5.
- Award full points for strong evidence, half for partial evidence, zero without evidence.
  Record unknowns separately; zero does not prove there is no need.
- need_score = round(100 * (N + D) / 60).
- sales_score = round(100 * (C + V) / 40).
- total_score = N + C + V + D.
- N requires confirmed operational gaps; D uses observable customer-facing friction.
  Do not infer manual operations merely from a website or count the same evidence twice.
- Retain evidence and observation dates. Report coverage as assessed criterion
  maximum points / 100. Below 70% coverage, need review remains provisional.
  Public prospect ranking has its own coverage and readiness, as described above.
- Initial priorities: 80–100 high; 60–79 medium; 40–59 low;
  below 40 insufficient demonstrated opportunity. Calibrate against real outcomes.
