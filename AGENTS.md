# Med Spa Automation Platform

## Current caller/email work — Level 0 and Level 1, 2026-10-09

Read `CALLER-EMAIL-INSTRUCTIONS.md` and `backend/LEVEL1-OUTREACH.md` before further outreach changes. The user authorized Levels 0 and 1 only; do not begin real email sending (Level 2) or Twilio click-to-call (Level 3) until they confirm. Level 1 now saves structured, unsent email and human call-script drafts in `ai_insights`, accepts sender/language input, checks cited public facts, and uses a rule-based email fallback on unavailable/invalid Gemini output. The Next.js lead detail has draft panels, copy/download/`mailto:`/`tel:` and operator-confirmed manual activity logging. The provider routes remain blocked in its proxy. Keep do-not-contact, mock, archive and evidence guards.

The supplied Gemini key was entered only into a hidden local backend prompt, not stored in source. A synthetic read-only provider call returned HTTP 403, so Gemini operation remains unverified and AI call scripts cannot currently be generated. The owner needs a fresh authorized Gemini API key entered locally and must review three to four actual med-spa leads before real-lead draft acceptance. Existing five CSV rows are massage/spa listings without real analysis. No real business was contacted by this work; preserve primary SQLite records. The Python suite passed 199 tests and the frontend build/typecheck plus isolated HTTP smoke passed. A read-only primary check returned integrity `ok` and 31 logical rows after other app activity during this turn; do not treat that as an unchanged-row claim. See the top of `backend/VERIFICATION.md` for exact limits. Rotate the key that appeared in chat.

## Additive Next.js/Gemini/Stitch milestone — 2026-10-09

The later visual clarification keeps `/app/` as the old fallback; the new purple interface is on port 3000. Current local data: five CSV businesses and one mock; three workflows are all mock and no real prospect is review-ready. The Next.js dashboard must hide unanalysed zero-score listings from Top prospects; workflows/tasks hide demos by default. Subtle CSS motion and reduced-motion support were added. Frontend build, isolated proxy/CSV smoke, read-only desktop/mobile screenshots, and primary SQLite integrity passed after this UI-only pass. The full manual control sweep and live provider checks remain open. Read `IMPLEMENTATION-STATUS.md` and the top of `backend/VERIFICATION.md` before claiming completion.

`CODEX-INSTRUCTIONS.md` authorizes an additive Next.js workspace in `frontend/`, separate Gemini draft/insight APIs and key-free Google Stitch MCP setup. Preserve the existing `/app/` UI, FastAPI routes, primary SQLite rows and collector. `GEMINI_API_KEY` is backend-only; `STITCH_API_KEY` is private Codex design tooling. The screenshot containing a Stitch key was not saved; rotate that exposed key before use. New AI insights live in `ai_insights`, carry origin/model/time/input hash, and do not alter scoring evidence. AI chat may call only fixed read-only functions; a task or draft proposal needs a separate user confirmation. The Next.js proxy holds `APP_API_TOKEN` server-side and exposes only selected routes; access is shared pilot access, not individual accounts. Final verification passed 190 Python tests, a Next.js production build and an isolated HTTP proxy/CSV smoke; no manual Edge/UI run occurred. Live Gemini, Stitch, Vercel/hosted deployment, email and calls remain unverified. A read-only primary SQLite check returned integrity `ok` and 28 logical rows, with no primary writes by this work. See `frontend/README.md` and the top of `backend/VERIFICATION.md`. The checkout has no `.git`, so no feature branch could be created here.

## Current local discovery/UI milestone — 2026-10-09

The current Windows UI uses a Calm Studio visual pass and Atomic CRM as the
lead-workflow reference. Windows defaults to the local Edge collector when its
optional Node/playwright-core setup is installed; this avoids requiring Docker.
The manual **Open Google Maps** link opens a query and saves nothing. The **Start
live pilot** flow collects up to ten results into a retained CSV/source preview;
never import automatically. Keep TLS verification, managed proxy routing, and
the restricted child-process environment. A one-listing local Edge collector
run and an isolated in-app run both succeeded with a verified result preview;
the in-app fixture database remained empty. The Docker runtime remains optional.
CSV import remains available. The historical generic New York job error does
not reveal its exact cause. The previous full Python suite passed 179 tests;
targeted collector/workspace checks passed after this change. See the newest
backend/VERIFICATION.md section. Preserve primary SQLite rows.

The latest one-listing query returned a tanning salon. It was not imported.
Retain/display source categories in CSV preview and require explicit category
review before importing live-pilot results. A human must still verify relevance;
do not promise that Maps results are all med spas.

After three later primary pilot jobs failed without importable output, the user
asked for an explanation and no further manual website/browser testing. The
readiness check now explicitly means local Edge setup only, not a successful
Maps search. Future recognized collector failures store safe specific messages;
old generic job errors cannot reveal their exact cause. Do not claim those jobs
were diagnosed individually. Targeted simulated checks passed 24 tests; no
browser was opened for that change. See current VERIFICATION.md.

Read-only inspection after the user's latest screenshot found three subsequent
successful Islamabad pilots, each with five captured listings and retained CSV
and source pages. Their visible categories are Spa/Massage spa, so relevance is
unverified and no automatic import is allowed. The Discover page now surfaces
the latest count beside the search form and auto-opens a preview for a pilot
started in the active page. Category is an explicit preview column. The user
again asked to avoid manual Edge/website testing; do not claim that this latest
UI change was browser-tested. PROJECT-EXPLAINED.md is the requested
purpose/usage/limits guide. Preserve existing primary rows.

The user's next screenshot showed newer location-only searches (`New york` and
`Islamabad pakistan`) failing without CSV while three specific Islamabad med-spa
queries had succeeded. The form now expands city-only text to `medical spas in
<city>` and shows the resulting query. The collector detects Maps place/city
pages and reports a safe specific failure. Browser-closed messaging avoids
assuming the user closed Edge. The project guide is now 294 words. Targeted
simulated checks passed 24 tests; no Edge/manual website retest was authorized.
Do not claim the newest UI logic succeeded live until it is tested live.

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

## CRM interface — v0.10.0, refined 2026-10-09

The user supplied a coral/navy interwoven A logo and an all-navy variant.
Prepared transparent PNGs are in backend/app/static/brand. Use the color mark
for the sidebar and favicon, and navy for the shared-access card. Laptop updates
must preserve .local/backend.sqlite3 and imported leads; the Windows guide
describes replacing only the static folder for branding changes.

Atomic CRM is the current GitHub UX reference because its open CRM flow centers
on lead/contact records, pipeline stages, tasks, notes and activity. HubSpot was
an earlier reference. Keep AIAutomation's original warm med-spa UI and backend;
do not add the reference repo's React stack or copy its components. Preserve
compact record tables, coral actions, teal links, saved views and record details.
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

The Next.js shared preview now locks on every full workspace document load, including reload and new-tab access; in-app navigation stays active. Keep the server-side page/API cookie checks and clear the cookie in `frontend/proxy.ts` on document navigation. This is local shared access, not individual accounts.

The 2026-10-09 Windows/UI pass uses Tabler as a visual reference while retaining
the HubSpot-inspired record structure and AIAutomation identity. The source
passes 175 Python tests and 29 isolated visible Edge fixture checks after
Windows Docker-collector compatibility fixes and mobile Sections navigation.
Read backend/LIVE_INTEGRATION_CHECKS.md: two real Maps searches and one public
website fetch succeeded, but the pinned Docker collector image is absent and
C: initially had about 153 MB free. A later exact-image pull stalled with no
visible layer progress and was interrupted; the app collector was not run or
imported. AI,
Resend and Twilio endpoints were reachable without credentials, but live
operations remain unverified and disabled. Do not claim provider success from
HTTP 401 reachability. No business was contacted.

The 2026-10-09 visible Edge control audit passed 99 overlapping assertions across
all nine sections and nested safe actions. Final fixture suites pass 29 checks:
15 research/CRM, five Automation lab, and nine client/task/operations. The mobile
Sections menu exposes all routes, and hash navigation closes the lead dialog.
See backend/UI_CONTROL_AUDIT.md and the top of backend/VERIFICATION.md. These
isolated fictional checks do not verify live collection or provider actions.

The 2026-10-09 Windows hardening pass repaired SQLite-plus-scraper backup recovery
across Windows path forms without changing the primary schema or records. The local
browser subprocess now receives only runtime/proxy environment variables; raw CSV
remains the import/provenance source and a separate spreadsheet-viewing download
neutralizes formula-like cells. The portable container entrypoint requires
APP_ENV=production. The complete Python suite passed 172 tests before that final
entrypoint guard; its new isolated test passed. Docker/browser packaging was not
rerun because the Linux Docker engine was unavailable. Read the newest
backend/VERIFICATION.md section before claiming release verification. Browser
isolation, proxy destination enforcement, ingress throttling and individual roles
remain open public-hosting work; do not describe them as solved by this pass.

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
