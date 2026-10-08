# Workspace milestone verification

## HubSpot-inspired CRM workspace — v0.10.0, 2026-10-08

The workspace uses HubSpot as its layout reference: dark grouped navigation,
coral actions, teal record links, compact lead tables, saved views and a record
detail panel. Global search reads authenticated saved data, supports keyboard
navigation/no-match behavior, respects demo filtering and clears on lock/reload.
Lead views stay synchronized with filters; sort uses actual names and scores.
The overview follow-up section uses saved pending tasks. No HubSpot/GoHighLevel
provider connection, native n8n engine or new backend integration was added.

Current Python suite: **170 passing tests**. The packaged release passes **32
checks: eleven API/container and twenty-one browser** (seven research/CRM, five
Automation lab, nine client/task/operations). New production checks cover keyboard
search opening an authenticated record and saved views separating public fit from
confirmed need. Existing client activation, pause, reminder/cancellation, task retry,
history/handoff, auth/host/CSP/non-root and actual restart checks all pass. JavaScript
and CSP error lists are empty. An intermediate browser test had an ambiguous
partial heading after the page titles shortened; exact page-heading selectors
resolved it before the final passing run. No assertion was removed.

**Six read-only real-cohort browser checks** pass, including multiple-result search
keyboard wrapping/Escape and saved-view/alphabetical sorting against the actual
five retained prospects. Desktop/mobile screenshots were inspected. Original
needs remain unconfirmed. Primary readback preserves **25 unchanged logical rows**,
seven businesses and empty primary client/task/execution/permission collections;
the v0.10 scheduler is running. Logical SHA-256 remains
`bbc7a134d4bb3eb54e194f1bdd030b8e7f57f7a5d5f0cb9f51bfa6d065594604`.

Current tested image:
`sha256:82b9c935522d96ec9d2b6c4e71f49a46626431de87a7455494cc5d5eed24f16d`.
Evidence: `.local/crm-verification/python-tests.log`, `build.log`,
`production-checks.log`, `primary-before.json`, `primary-readback.json`,
`real-cohort/live-qualification-report.json` and screenshots, plus
`.local/deployment/deployment-1c893a7509b8/report.json` and browser screenshots.
The previous v0.9 image is retained for rollback. Obsolete v0.8 and the intermediate
UI build plus their identified unused app caches were removed for VFS disk space;
no data volumes or global caches were pruned. Owned production test containers,
volume and temporary token files were cleaned up. No new live scrape, provider
email/call or public deployment occurred. See [CRM_DESIGN.md](CRM_DESIGN.md) and
[HANDOFF.md](HANDOFF.md) for the current behavior and limits.
The following sections describe historical releases.

## Historical backend reliability and handoff — v0.9.0, 2026-10-08

Current Python suite: **170 passing tests**. Twelve new isolated regressions
reproduced faults in v0.8 (nine assertion failures and three missing-alert errors)
and now pass. They cover recipient opt-out alias/case/restart/legacy behavior,
signed bounce suppression, separate recipient handling, local dialer validation
without consuming a key, contact opt-out serialization with an in-progress call,
evidence/archive action guards stopping outdated waiting runs, and Operations
detecting stale/blocked/missing-reference active setups without exposing credentials.
Provider transports are simulated; no live messages/calls occur.

The packaged release passes **30 checks: eleven container/API and nineteen
browser**. Nine client browser checks include the new blocked-setup alert and
client-review link. Existing research, Automation lab, authenticated host/CSP/non-root
checks, actual container restart recovery, and the twice-repeated full fictional
client handoff all pass. JavaScript/CSP error lists are empty. Owned production
test containers, temporary tokens and volume were cleaned up.

Current tested image:
`sha256:008fba0b1288d26572ffdd1b8a15c1a4a5a070ee106edb63acad68606cc45f1b`.
Evidence: `.local/final-verification/reproduced-faults.log`, `python-tests.log`,
`build.log`, `production-checks.log`, and
`.local/deployment/deployment-8eb06b6c37ef/report.json` with browser screenshots.
Dependency validation reports no broken requirements. The previous v0.8 image
is retained for rollback; the obsolete v0.7 image and three identified unused
application caches were removed before building to recover VFS disk. No volumes
or global caches were pruned.

Four read-only real-cohort browser checks pass. The restarted v0.9 API has a running
scheduler and retains **25 unchanged logical rows**, seven businesses, five real
leads with unconfirmed needs, and empty primary client/deployment/task/appointment/
run/outbox/call/permission collections. Logical SHA-256 remains
`bbc7a134d4bb3eb54e194f1bdd030b8e7f57f7a5d5f0cb9f51bfa6d065594604`.
Evidence: `.local/final-verification/primary-before.json`, `primary-readback.json`,
`real-cohort.log` and `real-cohort/live-qualification-report.json`.

There was no new live scrape, actual email/call or public deployment. Required
live credentials and HTTPS callback hosting remain unavailable. The completed
shared-token/one-worker SQLite hackathon scope and remaining live requirements
are defined in [HANDOFF.md](HANDOFF.md). The following sections are historical.

## Historical browser client workspace — v0.8.0, 2026-10-08

The current Python suite passes **158 tests**. The packaged release passes
**29 checks: eleven container/API and eighteen browser**, with no JavaScript or
CSP errors. Eight client browser checks cover explicit fictional onboarding,
authorization/proof guards, reviewed sandbox activation, deployment-bound
reminders, pause, secret-free handoff, stable task retry after a lost response,
safe operator text, demo alert exclusion and task completion, desktop/mobile
layouts, and clearing delayed private responses after locking the workspace.
Navigation checks wait for each screen's heading before measuring or capturing it.
The existing research and Automation lab checks also pass; the client command-line
demo runs twice and its state survives an actual production container restart.
The client browser suite also passed eight checks against an isolated local fixture.

Current tested image:
`sha256:a0c23bf3b6396c664a1196dad9429740f5b88f76ba9b76d19c3f0ee372baeb93`.
Evidence: `.local/workspace-verification/python-tests.log`, `build.log`,
`production-checks.log`, `final-browser/client-browser-report.json`, and
`.local/deployment/deployment-7f23917704f2/report.json` with browser screenshots.
The earlier packaged run also passed 29 checks in
`.local/deployment/deployment-f5c28c577ab5/report.json`.
Temporary production containers, tokens and volumes were cleaned up; the isolated
fixture API was stopped. The previous v0.7 image is retained for rollback.

Four read-only real-cohort browser checks pass. Primary readback confirms **25
unchanged logical records**, seven businesses, five real leads with unconfirmed
internal needs, and empty primary clients/deployments/tasks/appointments/runs/
outbox/calls. Logical SHA-256 remains
`bbc7a134d4bb3eb54e194f1bdd030b8e7f57f7a5d5f0cb9f51bfa6d065594604`.
Evidence: `.local/workspace-verification/primary-before.json`,
`primary-readback.json`, and `real-cohort/live-qualification-report.json`.
No real business was contacted, no email/call was sent, and no new live scrape
was performed. Provider credentials, verified sender/caller, public HTTPS hosting
and live integration verification remain outstanding. This is the shared-token,
one-worker SQLite pilot described in [WORKSPACE.md](WORKSPACE.md) and [MVP.md](MVP.md).
The following sections describe historical releases.

## Historical shared-workspace backend completion — v0.7.0, 2026-10-08

Current Python suite: **158 passing tests**, including **27 new** CRM/client/dialer/
operations regressions. They verify contact/audit atomic rollback and history,
concurrent idempotency/conflicts, task due dates/terminal states/opt-outs,
Twilio exact-URL/form signatures and matching account/numbers/SIDs, replay/order
handling and read-only uncertainty reconciliation, authorization/timezone guards,
client/workflow ownership, real sandbox proof before activation, changed
sender/evidence blocking, managed scheduling, pause/archive and restart recovery,
secret-free handoff/alerts, authentication, demo exclusion and explicit Supabase
rejection without breaking research. Provider transports are simulated throughout.

The packaged v0.7 release passes **21 checks: eleven container/API and ten
browser**. It includes the existing authenticated research and Automation lab
browser checks, scheduled-run/cancellation persistence, plus the complete fictional
client onboarding → contact/task history → sandbox proof → reviewed activation →
managed appointment reminder → handoff/operations flow. The client demo runs twice,
reuses its client/deployment and retains its records across a real container
restart. JavaScript/CSP errors are empty. No business was contacted or email sent.
Owned test containers/volume/token files were removed after saving evidence.

Current image:
`sha256:878878072d3314547055f51de98fc68b8afb91f7e9a6c643f7cf085dbd1b4013`.
Reports: `.local/completion-verification/python-tests.log`, `build.log`,
`production-checks.log`, `client-demo-first.json`, `client-demo-second.json`,
`client-recovery-report.json`, and
`.local/deployment/deployment-3233e17d4233/report.json` with browser evidence.
No new live Maps scrape was requested; prior collector evidence remains historical.

The local client demo also ran twice against a separately started API with its own
SQLite fixture, reusing client/deployment and saving unsent previews. Its recovery
drill verified **29 logical records**, restored the active client/deployment,
two appointments and previews, passed current preflight, and preserved all original
fixture rows. The unchanged backup helper includes all new record kinds.

Four read-only real-cohort browser checks passed with no JavaScript errors.
The restarted v0.7 primary API retains exactly **25 original logical rows** and the
same logical SHA-256, seven businesses/five real prospects with unconfirmed needs,
and empty primary clients/deployments/tasks/appointments/runs/outbox/calls.
Reports: `.local/completion-verification/primary-before.json`,
`primary-readback.json`, and `real-cohort/live-qualification-report.json`.
No fictional client data was written to the primary database during verification.

Twilio's official Python request-validator source was retrieved to confirm its
HMAC contract. Runtime provider credentials, verified sender/caller and public
HTTPS callback host are absent; live provider operation remains unverified.
[Current scope/contracts](MVP.md) describe shared access and SQLite limitations.
The following sections are historical releases.

## Historical reminder demo, appointments and guarded email — v0.6.0, 2026-10-07

Current Python suite: **131 passing tests**. New coverage includes 15 email/provider
cases and nine appointment cases: defaults and confirmation/auth guards, request
contracts, acceptance vs delivery, signed/raw-body/freshness/duplicate callbacks,
early and out-of-order events, opt-outs, uncertain crash/timeout replay without
resending, read-only provider reconciliation, appointment concurrency and partial
commit recovery, persistent cancellation, expiration, and fictional demo reuse.
Provider requests use simulated transports; no live email has been verified.

The current packaged release passes **19 checks: nine container/API and ten
browser**. Five browser checks exercise the new Automation lab: explicit fictional
setup, scheduled execution/history/unsent preview, cancellation, safe text rendering,
and desktop/mobile behavior. Appointment cancellation and previews survive an
actual container restart. Existing production authentication/research/CSP checks
also pass. JavaScript and CSP errors are empty. An additional isolated Automation
lab fixture passed five checks. All test contacts/evidence are synthetic; no
business was contacted. Test containers, volumes and temporary tokens were removed.

Current tested image:
`sha256:5c9f7a0207757b41b3df67455de4e552c71469ad32e050b28e094ab6842d19a0`.
Evidence: `.local/hackathon-verification/python-tests.log`, `build.log`,
`production-checks.log`, `automation-report.json`, screenshots, and
`.local/deployment/deployment-1da1c92ed80a/report.json` with its `browser/` and
`automation-browser/` directories. This run did not rerun live Maps collection.

The restarted v0.6.0 development API passed four read-only real-cohort browser
checks with no JavaScript errors. All **25 original logical rows** (seven
businesses, five real and two demos) have the same logical hash. No primary
appointments/runs/outbox were created. Real internal needs remain unconfirmed.
Readback reports are `.local/hackathon-verification/primary-before.json`,
`primary-readback.json`, and `real-cohort/live-qualification-report.json`.

Email defaults disabled; runtime credentials, verified sender and public callback
host are absent. Official Resend SDK/webhook models and Standard Webhooks/Svix
source were inspected for API/signature contracts; this is not live provider proof.
General external/client execution remains incomplete. Manual appointment events
do not establish native calendar integration or availability. See
[HACKATHON.md](HACKATHON.md) for the working demo, setup and exact limitations.
The sections below are historical results from previous releases.

## Historical durable sandbox execution milestone — 2026-10-07

The current Python suite passes **107 tests**, including **13** new execution
tests. These exercise actual SQLite actions rather than pretend delivery:
step progress/history, scheduler timing, concurrent event idempotency, conflicting
keys, cancellation, consent/cancel flags, archived/opted-out/superseded guards,
bounded retries/backoff, malformed input and unsupported actions, auth protection,
Supabase rejection, lifecycle startup/shutdown, and backup/restore of run/outbox.
A crash injected after outbox creation but before progress saving recovers with
exactly one preview. A transient progress-write failure replays the same step
without skipping ahead or duplicating the preview. Provider diagnostic text is
not copied into run history.

The rebuilt production release passes **eight container/API checks and five
browser checks**, including two execution checks in addition to the prior normal
non-live container coverage. An isolated synthetic reminder is queued to run
20 seconds later, waits without an early preview, survives an actual container
restart, finishes, and retains exactly one unsent preview. Identical requests
reuse the run; changed inputs using the same key return 409. Browser checks have
zero JavaScript exceptions and CSP errors. The isolated volume/container/token
are removed after saving evidence.

Current image:
`sha256:afc55824f37e1fc26affedbcda6717191a62d214b793e70015cbe375ab2d22d7`.
Reports: `.local/execution-verification/python-tests.log`, `build.log`,
`production-checks.log`, and
`.local/deployment/deployment-7596469230c6/report.json` with its `browser/` directory.
This deployment verification did **not** run live Maps collection; that unchanged
collector's prior live evidence is recorded below. No business was contacted.

Four read-only cohort browser checks pass again, with zero JavaScript errors.
Evidence is in `.local/execution-verification/real-cohort/`. Primary startup and
the final development restart retained all **25 logical records**, including seven
businesses (five real and two demos), with an identical logical database hash.
All five real prospects keep unconfirmed internal needs; no primary runs/outbox
records were created. Readback evidence is `primary-before.json` and
`primary-readback.json` in `.local/execution-verification/`.
The Connections screen now accurately shows sandbox API availability while
keeping live delivery and calendar/n8n integration incomplete.

Supported execution is deliberately sandbox-only: saved previews/results, no
email/SMS/voice delivery or client calendar/database action. Existing external
execution flags remain false. The runner requires one SQLite worker/replica;
Supabase, arbitrary graphs, and calendar actions are explicitly unsupported.
See [EXECUTION.md](EXECUTION.md) for precise contracts and remaining work.
Historical results follow.

## Historical backend hardening audit — 2026-10-07

The current suite passes **94 Python tests**. New regressions cover repeat-save
provenance, mixed concurrent import/save identity, immutable listing dates,
automatic/operator evidence refresh, latest-analysis guards, opt-out blocking,
invalid-phone scoring, closed SQLite connections, bounded Supabase batches,
malformed Twilio submission IDs, and five backup/recovery cases.
Provider checks are simulations; no business calls or messages are made.
The fictional demo explicitly opts into demo ranking and passed twice against a
temporary SQLite API, confirming repeat runs without changing primary records.

The final fixture browser run passes **14 checks**, the read-only five-real-lead
cohort passes **four**, and the rebuilt production release passes **eight
container/API plus five browser checks**. Browser reports have no JavaScript
exceptions; production has no CSP violations. Fixture refresh intercepts its
request and checks evidence filtering without fetching an external website.

Current evidence (ignored local files):

- `.local/hardening-tests.log`
- `.local/audit-verification/fixture-report.json` and screenshots
- `.local/audit-verification/real-cohort/live-qualification-report.json`
- `.local/audit-verification/recovery-report.json`
- `.local/deployment/deployment-cc7868c8a27c/report.json`, `browser/`, `scrapes/`

Current tested release:
`sha256:221d532b87f648590c1483745585fb5db38cf2f87866f3c0ec7a105a02d38b2d`.
Its live job `f33278b2-fcb2-440f-a232-de3bcf4fae03` collected Dolce Medical Spa NYC,
Medical spa, 124 E 36th St, New York. Listing name/address/website/phone/rating,
Place ID and Maps URL came from captured live data; review count was unavailable.
TLS verification was enabled. CSV SHA-256:
`43b6f5acba76fb2c8e24d0da11ef66073bd84fa31633a25f637bab640d65c779`.
Job/download integrity survived restart. No real listing was imported in this
isolated release check; its test containers/volume/tokens were cleaned afterward.

The recovery drill used the primary database and scraper directory, verified
**25 records and 64 hashed files**, restored to a separate new directory, checked
readiness, all seven businesses, five real unconfirmed prospects, and a recovered
job CSV download. Original logical rows remained unchanged. Only restored job
paths changed to point at the recovered artifact directory. The helper refuses
existing destinations, active collection snapshots, changed source files, and
unsafe paths. This is manual SQLite recovery, not scheduled/off-host backup.

Repeated builds exhausted the cloud's VFS Docker disk before the final fixture
run. Removing only identified superseded app images and their unused cache entries
recovered about 12 GB. The final fixture rerun passed. Current image, pinned base
images, databases, source artifacts, and backups remain. Superseded image IDs
below are historical evidence and are no longer retained in the local daemon.

See [STATUS.md](STATUS.md) for stage completion and [deployment/recovery](../deploy/README.md)
for operational limits. Historical milestone results follow.

## Portable deployment milestone — 2026-10-07

At this milestone the Python suite passed **77 tests**, including six new production-access
and bundled-collector regression tests. The final image builds successfully with
verified TLS and signed Debian packages. Its live deployment runner passes eight
container/API checks plus five browser checks, with zero JavaScript exceptions
or CSP violations. These are current-instance container checks, not a public launch.

Final-image evidence is under ignored
`.local/deployment/deployment-7f388f1df0ff/report.json`, with desktop/mobile
screenshots and the browser report in `browser/`, and source artifacts in `scrapes/`.
The final tested image ID is
`sha256:5d7e3be69562354c932c142c2f2e295b8932fb92b55ec52f5c861758e9d564b8`.

Production refuses missing/short/invalid tokens or wildcard/invalid hostnames.
Unauthenticated and wrong-token data requests return 401. Invalid Host returns
400, production documentation returns 404, and the app shell remains public.
The image runs as UID/GID 10001, without a Docker CLI/socket or embedded database,
research artifacts, API token, or managed proxy credentials. The test runs with
a read-only filesystem, limited resources, and a writable named `/data` volume.
The health check works with a configured app hostname even if outbound proxy
settings cannot reach loopback.

An isolated synthetic lead is previewed, explicitly imported, analyzed, and given
synthetic contact notes. All three records survive a real container restart.
The UI accepts the configured token, rejects an incorrect token, keeps access out
of local/session storage, and locks on reload. Unknown needs keep workflow creation
blocked. Desktop and mobile rendering work under production CSP.

A real Google Maps pilot inside this same app container collected **Dolce Medical
Spa NYC**, categorized Medical spa, at 124 E 36th St, New York, NY 10016. Its name,
address, website, phone, rating, Place ID, and Maps URL came from the captured live
listing; unavailable review count remains blank. TLS verification is true in the
manifest, and the downloaded CSV matches SHA-256
`6fefe288df6ed89031442ac7e63a5fc5ffba1219c13761cc47017e0be44f112c`.
Job `fdfd7942-a3e0-446e-95be-f33139f13452` succeeded and its original CSV remained
downloadable after another container restart. No collected listing was imported,
no business was contacted, and no workflow executed. Only the synthetic test lead
entered the isolated test database, which was removed after saving the report.

The owned development API was also restarted and checked read-only. All seven
records remain: five real CSV leads and two labeled demo records. The default
prospect queue contains the five real leads, with unconfirmed internal needs.
Four real-cohort browser checks pass again with zero JavaScript exceptions.
Evidence is in `.local/deployment/development-restart-report.json` and
`.local/deployment/development-cohort/`. The new container pilot did not change
the primary development database or old analysis evidence.

Repeat deployment checks with `deploy/build.py` and `deploy/verify.py`; use
`--live` for the single-listing network check. See [deployment instructions](../deploy/README.md).
Publication still requires a chosen hosting account, HTTPS ingress, and persistent
storage. Individual accounts, provider-backed dialer validation, AI calling, and
workflow execution remain separate work. Historical milestone results follow.

## Two-stage qualification update — 2026-10-07

At this milestone the Python suite passed **71 tests**, including nine qualification tests.
The extended fixture browser run passes **13 checks**, and four additional
read-only browser checks pass against the existing five real businesses. Both
browser runs have zero JavaScript exceptions. Reports/screenshots are retained
under ignored `.local/qualification-verification/`: `fixture-report.json`,
`live-qualification-report.json`, `live-api-report.json`, `fixture-desktop.png`,
`live-prospects-desktop.png`, `live-prospects-mobile.png`, and `live-prospect-detail.png`.

Public prospect ranking is derived from the latest saved C+V evidence and does
not mutate old analysis snapshots. The existing five businesses are ready for
prospect review, with scores ZZ 85, Trifecta 65, Perfect 48, Dolce 40, Tribeca 40.
All still have unconfirmed internal needs. Their original source evidence and
phone discrepancies remain. The 70% overall need-coverage gate is unchanged;
prospect coverage uses its own 40-point denominator. The 40-score/40%-coverage
public thresholds are initial heuristics, not calibrated conversion probabilities.

Checks cover public readiness without fabricated needs, unknown versus assessed
zero, supported contact routes (untested forms alone are insufficient), business
confirmation, observed public friction, opt-out blocking in API/UI, latest-snapshot
ranking, stable pagination, default demo exclusion, protected endpoints, and
historical readback without writes. Browser checks also verify closing a lead
during a pending save does not reopen it, and old success messages do not appear
to confirm a new pending save. Discovery drafts ask about processes; only
recorded operational confirmation supports confirmed-need wording.

To repeat the read-only real-cohort browser check, use the Docker command below
with `backend/tests/browser_qualification.cjs` mounted as `/test.cjs` and run
`/test.cjs` without a mode argument. It requires the documented cohort on port
8000. To repeat fixture checks, use a new empty fixture database on port 8001;
`browser_workspace.cjs fixture` now executes the current 14-check suite.
The qualification update makes no scraper or official-website network calls,
and sends no outreach or calls. October 6 live scraping/fetch evidence follows.

## Original workspace milestone — 2026-10-06

Verified in the current cloud instance on 2026-10-06. This is a development
workspace, not a published deployment or proof that every future scrape will work.

## Evidence

| Check | Result | Evidence type |
|---|---|---|
| Python suite | 62 tests passed | Isolated databases; provider responses simulated |
| Browser fixture journeys | 9 checks passed; no JavaScript exceptions | Separate SQLite database on port 8001, synthetic businesses |
| Browser live journeys | 5 checks passed; no JavaScript exceptions | Current live SQLite records, official website, Google Maps pilot |
| Live collection through UI | One public listing collected; preview rendered; no automatic import | Saved job and retained CSV/HTML/text/screenshots/manifest |
| Website analysis through UI | Dolce official site fetched; HTTP 201; unknown internal need retained | Actual network response and saved analysis |
| Mobile layout | Overview and lead dialog fit a 390px viewport | Chromium screenshots and overflow assertions |
| Service restart | Workspace, five real leads, job, preview, and CSV hash retained | Actual stop/start with one worker; `restart-report.json` |

Reports and screenshots: ignored `.local/ui-verification/fixture-report.json`,
`live-report.json`, `fixture-desktop.png`, `live-desktop.png`, `live-lead.png`,
`live-pilot.png`, and `live-mobile.png`. They are local evidence, not committed data.
Live job `a4a319ab-f377-4d71-b6a7-51405fd44661` collected one listing for
`medical spas in New York NY`; its API result and original CSV hash were checked.
The existing five real imported businesses remained five; none was contacted.

Fixture browser checks cover wrong/correct token access, zero-state metrics,
CSV validation and explicit import, invalidated previews after settings changes,
safe rendering of hostile business names, unknown criteria, operational evidence
confirmation, persisted contact notes, outreach drafts, workflow export/archive,
demo filtering, stale-data labeling, connection recovery, and memory-only tokens.
Synthetic operational confirmations are test inputs, never evidence about real businesses.

## Scoring correction

Static HTML booking-link presence or absence now leaves booking friction unknown.
Neither proves the customer journey is usable or broken. The regression check
requires zero digital-friction points and zero assessed coverage from that
observation alone. Historical immutable analyses are retained; this correction
applies to new automatic observations. Explicit reviewed evidence still overrides
automatic observations. The five real businesses already recorded booking as unknown.

## Repeat verification

Run the Python suite from `backend/`:

```bash
../.venv/bin/python -m unittest discover -s tests -v
```

The browser runner uses Playwright already bundled in the pinned Docker image;
it adds no application dependency. For fixture mode, start a separate server on
port 8001 with a **new, empty, ignored database** and
`APP_API_TOKEN=ui-fixture-access-only`. Do not point it at the primary database.
From the repository root, for example:

```bash
mkdir -p .local/ui-verification
APP_DB_PATH="$(mktemp /workspace/AIAUTOMATION/.local/ui-verification/fixture-XXXXXX.sqlite3)" \
APP_API_TOKEN=ui-fixture-access-only \
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001
```

Then, in a separate shell:

```bash
docker run --rm --network host --cpus=2 --memory=2g --shm-size=512m \
  --env DISABLE_TELEMETRY=1 \
  --mount type=bind,source=/workspace/AIAUTOMATION/backend/tests/browser_workspace.cjs,target=/test.cjs,readonly \
  --mount type=bind,source=/workspace/AIAUTOMATION/.local/ui-verification,target=/out \
  --entrypoint /opt/ms-playwright-go/node \
  gosom/google-maps-scraper@sha256:e205c02913c5a69c16fc2094b8e5b194a2f655166d2c1126d50548d216e6b1b2 \
  /test.cjs fixture
```

Live mode (`/test.cjs live`) requires the documented five-business pilot on
port 8000 without a shared token. It creates one new real website-analysis
snapshot and one single-listing discovery job; it never imports the result,
submits forms, sends outreach, calls a business, or executes a workflow.
It is a cohort-specific check, not a general production smoke test.

## Limits that remain

- Shared API-token access only; no accounts, roles, billing, or published deployment.
- Free collection is a small visible-listing pilot; no full pagination, guarantees,
  distributed queue, or retries. One API worker is required. Abrupt host shutdown
  can leave a container to inspect; normal shutdown waits for collector cleanup.
- Evidence entries and source choices are operator assertions, not independent verification.
  The five real businesses remain provisional with unconfirmed internal processes.
- Static website checks do not test bookings or form submission. AI summaries,
  Google Places, Supabase, and Twilio have no new live verification here.
- Workflow exports are internal JSON definitions. They do not execute and are not
  native n8n exports. The frontend offers no outbound call or send action.
- Files and SQLite records are local; Supabase needs its schema update and credentials.
  Existing provider requirements remain optional for the free workspace path.
