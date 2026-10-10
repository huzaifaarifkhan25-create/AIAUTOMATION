# Backend status — 2026-10-08 (v0.10.0)

**Current local UI update (2026-10-09):** Discover & import uses the Calm Studio
med-spa theme, an authenticated readiness check and a Docker-free Windows Edge
collector. A live one-listing app job completed and displayed its preview in an
isolated database; its result was a tanning salon and was not imported. Preview
now shows source categories and requires an explicit category-review confirmation
before live-pilot import. The separate **Open Google Maps** link is for manual
inspection and does not save data. Windows collector
setup is documented in [WINDOWS-START-HERE.md](../WINDOWS-START-HERE.md).
The collector readiness panel now explains that setup readiness does not prove
Maps access; recognized future failures show safe, specific guidance. Three new
primary failed jobs and the historical generic New York job have no recoverable
per-job root-cause detail or importable CSV. No lead was imported from them.
Three subsequent Islamabad pilots succeeded with five listings each. Their
Spa/Massage spa categories require relevance review; the latest count and
preview action are now beside the search form, and a newly completed pilot
opens its preview automatically in the active Discover page. Import remains
explicit. The user requested no manual browser retest for this UI update.
Two later location-only queries failed without a CSV. The browser form now
turns a city-only entry into an explicit med-spa search, and future Maps
place/city redirects have a specific safe error. This new query behavior has
targeted simulated checks, not a live browser verification.
See [VERIFICATION.md](VERIFICATION.md) for exact checks. AI, email and calls
still require separate live credential checks; no real contact occurred.

The earlier 2026-10-09 Windows/UI pass is documented in
[VERIFICATION.md](VERIFICATION.md), [CRM_DESIGN.md](CRM_DESIGN.md) and
[LIVE_INTEGRATION_CHECKS.md](LIVE_INTEGRATION_CHECKS.md). That pass ran
175 Python tests and 29 isolated visible Edge fixture checks. It introduced
Tabler-inspired spacing/controls and phone Sections navigation. Windows
Docker-collector host compatibility was corrected, but the pinned image was
absent. A later pinned-image pull stalled without visible layer progress; no
app collector run was claimed. Provider credentials remain absent, with no
live email or call.

Local Windows hardening on 2026-10-09 repaired backup restore, limited browser
subprocess environment exposure, added a spreadsheet-viewing CSV and a production
entrypoint guard. See the newest [verification section](VERIFICATION.md). The
v0.10 packaged checks below remain historical; no new Docker build was verified.

The supported shared-workspace backend MVP is implemented across discovery,
analysis, ranking, contact records, workflow generation, local execution and client
handoff. Version 0.8 connects the client, manual task and operations screens to
the existing backend, including reviewed sandbox activation and managed reminders.
Version 0.9 fixes twelve reproduced reliability regressions before handoff.
Version 0.10 adds the [HubSpot-inspired CRM layout](CRM_DESIGN.md), saved-record
search, lead views/sorting and actual upcoming follow-up tasks on the overview.
Live provider operation
is not verified: email/calling credentials and public HTTPS callbacks are absent.
This remains a one-worker SQLite pilot with shared access, not the full multi-user
production platform. See [WORKSPACE.md](WORKSPACE.md) for the browser walkthrough
and [MVP.md](MVP.md) for exact contracts and the complete fictional client demo.

| Stage | Working now | Remaining work |
|---|---|---|
| Discover | Windows Edge or bundled browser collection, retained sources, CSV preview/import, duplicate checks | Only 1–10 visible listings per pilot; no pagination, coverage guarantee, or distributed queue |
| Analyze | Public HTML fetching, dated evidence, unknowns, deterministic scoring, immutable snapshots | No JavaScript booking/form testing; operator assertions need review; optional AI provider access remains unverified |
| Rank | Latest-evidence prospect and need stages; demos and opt-outs excluded by default | Initial thresholds need calibration against sales outcomes |
| Contact | Outreach drafts, atomic contact history, manual activity/tasks, guarded human dialer, signed agent-leg outcomes and read-only reconciliation | No automatic prospect email/SMS, AI calling, or live dialer validation; calls disabled |
| Build | Workflow JSON generation, export, archive | Reviewed local deployment/activation for supported message graphs; no native n8n/calendar/arbitrary graph engine |
| Automate | Durable SQLite runner, sandbox UI, appointment events/cancellation, opt-in email adapter, signed callbacks and reconciliation | Live email credentials/callback host and proof; calendar/consent integration, distributed queue |
| Deliver | Client onboarding/approval references, sandbox-test preflight, local activation/pause/archive, audit/handoff export and operations alerts | Public hosting, live provider checks, individual accounts/roles, external alerting/support |

SQLite persistence, shared-token protection, production container packaging, and
manual backup/recovery work. Public hosting is not provisioned. Run one API worker
and one replica. This is shared pilot access, without individual accounts or roles.
Supabase/Places/AI/Twilio/Resend adapters have simulated provider tests; live access is
not established by those tests. No real business has been contacted by testing.

## Problems corrected in this audit

- Customer email opt-outs also block known recipient addresses within that
  business, including case variants and changed contact IDs. Legacy contact-only
  records are honored without rewriting original data; no automatic opt-in reset.
- Missing dialer configuration and invalid numbers fail before reserving an
  external-call key. A genuinely uncertain provider attempt still cannot redial.
- Contact opt-out is serialized with dialer submission; evidence commits and
  workflow archiving share the runner action guard. An in-progress provider
  submission cannot be recalled; completed changes block subsequent actions.
- Operations checks active deployment readiness and saved validation fingerprints,
  showing stale/blocked setups even before a managed run is scheduled. The browser
  links these alerts to client review without silently reactivating anything.
- Repeated saves preserve original fields, source, collection date, and provenance;
  Place-ID CSV records are reused. Mixed imports/saves are serialized within the
  single-worker process.
- Website refresh recomputes tagged automatic evidence, retaining operator and
  legacy evidence with original dates. Listing phone dates no longer reset on each
  analysis. Legacy evidence origin remains unspecified.
- New outreach/workflow drafts require the latest analysis. Opt-outs block both;
  default opportunity ranking excludes opted-out and demo records.
- Invalid phone text earns no automatic contact points. Syntax plausibility does
  not establish reachability; imported values remain available for review.
- SQLite connections close on success/failure. Supabase response-size failures
  reduce page size. Listing still loads records into memory: indexed queries are
  needed before large-scale use.
- Twilio requires a valid provider call-ID shape. Uncertain submissions cannot
  retry with the same key. Signed callbacks and explicit read-only reconciliation
  track the sales-agent leg; their real-provider operation remains unverified.
- SQLite backup/recovery includes committed WAL data and scraper files, checks
  hashes/integrity, restores to a new directory, and rebases download paths.
  It does not schedule backups or upload them.
- Superseded app images and their specific unused caches were removed after the
  cloud's VFS Docker driver exhausted disk space. About 12 GB was recovered;
  the current release image, saved leads, source files, and backups were preserved.

## Evidence and remaining limits

The current suite passes 170 Python tests, including twelve reliability regressions,
27 CRM/client/dialer/
operations checks, 13 sandbox runner regressions, 15 email/callback cases and nine
appointment cases. The current release passes eleven container/API plus twenty-one
production browser checks (32 total),
including actual scheduled-run restart recovery and appointment UI/cancellation
persistence, nine client/task/operations browser checks, and the complete fictional
client demo twice. New client/CRM/
appointment state survives another actual container restart. The earlier five
isolated Automation lab browser checks also passed. Six read-only real-cohort browser
checks also pass; all 25 original logical records remain unchanged.
The hardening milestone passed 14 fixture browser checks, four read-only cohort
checks, and eight production container/API plus five production browser checks.
That release collected one real listing with verified TLS and
retained CSV integrity across restart, without importing it. The primary database
contains seven businesses: five real imported leads and two labeled demos.
All five real leads are ready for public prospect review; internal needs remain
unconfirmed. Evidence cannot substitute for an actual business conversation.

The earlier v0.7 client recovery drill verified all 29 fixture records, restored the client,
active deployment, two appointments and unsent previews, and passed current
preflight without changing its source rows. The earlier real-data recovery drill
verified 25 records and 64 hashed files, recovered
API readback and discovery downloads, and left the original database unchanged.
Reports and limitations are detailed in [VERIFICATION.md](VERIFICATION.md).
Keep backups privately off-host; copies on this disk do not protect against losing
the disk. Manual research outside the configured scraper directory needs its own
archive. See [deployment and recovery instructions](../deploy/README.md).

The next provider step is a consented, isolated live email test after secure
credentials, a verified sender, and public HTTPS callback hosting are configured.
No actual email has been sent here. Sandbox succeeds with a saved unsent preview;
email acceptance alone does not establish sending or delivery. Signed callbacks
track outcomes; uncertain submission is never automatically resent. Appointment
events are manual/API events, not a calendar booking/availability integration.
Business needs remain unconfirmed for all five real leads. General external/client
execution flags remain false; specific runner modes are separate. Supabase
execution is explicitly unsupported. See [HACKATHON.md](HACKATHON.md) and
[EXECUTION.md](EXECUTION.md).
