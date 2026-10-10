# Workspace milestone verification

## Caller/email Level 0 and Level 1 — 2026-10-09

Read `CALLER-EMAIL-INSTRUCTIONS.md`, `CODEX-INSTRUCTIONS.md`, and the repository instructions. The pre-code API/UI gap audit and the Level 1 handoff are in [LEVEL1-OUTREACH.md](LEVEL1-OUTREACH.md). Level 1 now has structured, saved, unsent email and call-script drafts; request-supplied sender profile; English, Urdu and Roman Urdu; source/date citation checks; no-analysis generic drafts; do-not-contact/archived generation guards; and a rule-based email fallback when Gemini is absent, rejects access, or returns invalid output. The lead detail page has separate panels, copy/download/encoded `mailto:` and validated `tel:` actions, and a manual activity form. Its links and draft actions are disabled for a known do-not-contact lead. The Next.js proxy still blocks provider call/send routes.

Verification: the complete Python suite passed **199 tests** on Windows after the final backend changes. Focused AI/outreach tests passed **17** checks, including mocked provider response, invalid JSON retry, three languages, word limits, citation rejection, no-analysis drafts, do-not-contact, prompt-injection delimiter, no-key fallback, provider-denial fallback and manual log provenance. The frontend production build and TypeScript check passed; two Node link-encoding tests passed. The isolated production HTTP smoke passed login/reload lock, authenticated proxy, CSV import, unsent email fallback, manual activity, saved draft readback and a blocked call route. All automated tests use fictional records or mocked provider responses; none contacts a business. The primary SQLite database was not used for these tests or changed by this implementation. A later read-only primary check returned `integrity_check=ok` and 31 logical rows; other app activity occurred while this work was in progress, so this is not a before/after row-equivalence claim.

The supplied credential was entered through the local hidden terminal prompt and `GET /capabilities` reported `gemini_configured=true`. Synthetic, read-only `POST /ai/chat` checks reached Google but returned HTTP **403**. This verifies that the key is loaded, **not** that Gemini is usable; the key/project access must be corrected. No live AI draft or script was claimed. The existing real CSV rows have massage/spa categories and no real analysis, so the requested three to four category-reviewed real med-spa drafts were not created. No Resend email, Twilio call, provider callback or other real contact occurred. Levels 2 and 3 were not started. The key shared in chat should be rotated. The UI was not manually opened or clicked in this milestone.

## Gemini setup explanation and AI screen — 2026-10-09

The earlier image supplied a Google Stitch design-tool key, while the running backend had no `GEMINI_API_KEY` in process/user environment and `/capabilities` returned `gemini_configured=false`. The AI page now explains that separation and offers a private Windows helper that prompts for a Gemini key without saving it. The same change made the sticky top bar opaque so page text no longer shows through it. `npm run typecheck`, `npm run build`, and `frontend/scripts/smoke.ps1` passed; an isolated headless Edge view of the AI setup screen found no page errors, horizontal overflow or browser key-entry field. The helper parsed and correctly refused to start a second backend on port 8000. No real key was entered, no Gemini API call was made, and the assistant remains unavailable until a Gemini credential is supplied privately and the backend restarted.

## Next.js access lock and project status check — 2026-10-09

The current source passed `python -m unittest discover -s tests -q` from `backend/` (**190 tests**), `npm run typecheck`, `npm run build`, and the isolated `frontend/scripts/smoke.ps1` production HTTP flow. The smoke covers access, full-document reload redirect/cookie clearing, authenticated proxy, CSV preview/import, invalid rows, duplicates and a blocked call route. A live local HTTP check returned 200 for backend health, frontend login/workflows and authenticated capabilities; Gemini, email and calls reported disabled, while SQLite and sandbox mode were available. A read-only primary SQLite check returned `integrity_check=ok` and 28 logical rows; no primary fixture writes occurred. These checks did not exercise live Gemini, Stitch, Maps collection, email, calls, deployment, or every new UI control. The current work and remaining items are summarized in [PROJECT-COMPLETION-REPORT.md](../PROJECT-COMPLETION-REPORT.md).

## New interface visual clarification and polish — 2026-10-09

The user's screenshot showed `127.0.0.1:8000/app/#workflows`, the preserved FastAPI fallback rather than the Next.js UI at `127.0.0.1:3000/workflows`. A read-only API check found five CSV businesses, one mock business, four analyses and three workflows; all three workflows belong to the mock business, with zero review-ready real prospects. The new UI now hides demo workflows/tasks by default, labels the optional demo graph, and does not rank unanalysed zero-score listings as top prospects. The design pass added consistent SVG navigation, purple workflow empty state, restrained ambient/card motion, loading feedback and reduced-motion support; `devIndicators` is disabled for local preview.

`npm run build` passed after these frontend-only edits. The isolated `frontend/scripts/smoke.ps1` passed access/proxy, CSV preview/import, duplicate/invalid rows and blocked call route. Read-only headless Edge screenshots of the port-3000 desktop dashboard, desktop workflows and mobile workflows reported no page errors and no mobile horizontal overflow. No manual control sweep or live Gemini/Stitch request occurred. Primary SQLite remained `integrity_check=ok` with 28 logical rows after the checks. See [implementation status](../IMPLEMENTATION-STATUS.md) for phase-by-phase remaining work.

## Additive Next.js, Gemini drafts and Stitch config — 2026-10-09

Read `CODEX-INSTRUCTIONS.md` and the existing architecture/deployment docs before changes. Baseline Python suite: 182 tests passed. Added a separate Gemini service and authenticated `/ai/*` draft/read routes, with Pydantic output validation, bounded HTTP retries/timeouts, a fixed read-only chat tool whitelist, explicit proposal confirmation, and separate provenance-tagged `ai_insights` records. Existing analysis snapshots and scores are unchanged by AI output. The app starts without a Gemini key; AI requests then return a clear configuration error. `GET /capabilities` exposes key presence only. Unit tests use synthetic data and mocked provider responses, including success, invalid JSON, timeout, do-not-contact, prompt-injection delimiter and tool whitelist cases.

Added `frontend/` as an optional Next.js/React Flow workspace. It has an HttpOnly signed shared demo gate, server-side bearer proxy with a narrow route/method allowlist, CSV preview/import, discovery status, leads/evidence, tasks, AI drafts/chat, workflow graph and sandbox reminder forms/history. The original `/app/` remains available. The owner-supplied purple dashboard screenshot is retained as `docs/design-reference/ui-2-dashboard.png`; the screenshot containing a key was not copied. The `.codex/config.toml` Stitch MCP entry contains only the `STITCH_API_KEY` environment-variable name.

Final verification: `python -m unittest discover -s backend/tests -q` passed **190 tests** in 181.103 seconds; `npm run build` passed for Next.js 16.4.0; and `frontend/scripts/smoke.ps1` passed access-gate/proxy, isolated CSV preview/import, duplicate and invalid-row checks, plus blocking a call route. The smoke script uses a temporary SQLite file, synthetic access values and no business contact. No manual Edge/browser UI test was run, as requested. A read-only primary SQLite check returned `integrity_check=ok` and 28 logical rows; no primary writes were made by this work.

No live Gemini or Stitch call was made because those keys were not configured in the environment. The key exposed in the user screenshot should be rotated before use. No Vercel/Python host account was connected and no public site was deployed. The new shared gate is for an isolated pilot, not individual authentication or a complete public-hosting security review. Maps collection, email delivery and calls were not reverified live in this milestone. This checkout has no `.git`, so the requested feature branch could not be created here. See `frontend/README.md` and `docs/STITCH-SETUP.md` for private setup and remaining owner actions.

## Location-only Maps query correction — 2026-10-09

Read-only inspection found two newer failed pilots: `New york` and `Islamabad
pakistan`. Both retained only a query file, with no listing CSV or source page.
The former saved `maps_results_unavailable`; the latter saved `browser_closed`.
The user's screenshot shows Maps presenting New York as a city place page, which
explains why a business-results collector can wait without seeing listing cards.
The exact reason Edge closed during the Islamabad attempt remains unproven.
Three earlier `medical spas in Islamabad, Pakistan` jobs succeeded with five
captured listings each, so per-listing collection was not removed.

The browser form now expands a city-only entry to `medical spas in <city>` and
shows the actual query before collection. The collector reports a distinct safe
error if Maps opens a single place/city page, including after a delayed redirect.
The Edge-closed message no longer assumes the operator closed the window.
Twenty-four targeted deployment/workspace tests passed with simulated failures;
Node and Python syntax checks passed. No live browser run or manual website test
was performed for this change. The app restarted with no active pilot; its
collector-status API returned `ready`. Primary SQLite integrity remained `ok`
at 27 logical rows before and after restart, with no changes made to those rows
by this work.

## Islamabad pilot result visibility — 2026-10-09

Read-only inspection found three primary pilot jobs for "medical spas in
Islamabad, Pakistan" with status `succeeded` and five captured listings each.
Their retained manifests, source pages and CSV files exist. The latest manifest
contains categories `Massage spa` and `Spa`; these are search results, not
verified medical spas. The collector opens each listing in its owned Edge
window and closes that window when done. The previous UI put its count and
preview action in the activity list below the search form, making success easy
to miss.

The Discover page now shows the latest captured count beside the form and a
direct preview button. A pilot started in the current page automatically opens
its preview when polling sees it finish successfully; import remains a separate
human action. Preview has a visible category column. This is a frontend change
using existing job counts and preview API; no primary data was changed. The
user asked not to open or manually test the website, so verification is limited
to read-only source inspection and JavaScript syntax. A read-only SQLite check
returned integrity `ok` with 20 logical rows after the user's runs; this change
made no primary data writes. [Project explained](../PROJECT-EXPLAINED.md)
is a 287-word overview of purpose, usage and limits.

## Maps pilot failure messages — 2026-10-09

The primary database shows three new failed live jobs for broad/location-only
queries, plus an older failed New York job. Their saved error is generic; none
has an importable result path. The three new jobs created only query files,
without a CSV or source page. One server log shows the collector waiting for
Maps listing links when its browser page closed, but the log cannot reliably
identify the exact cause of each historical job. No primary lead was imported.

The readiness panel now states that it checks Edge and collector setup only;
it has not tested a Maps search. Recognized future failures have bounded,
operator-facing messages for browser launch/closure, Maps navigation, unreadable
result cards and unusable listings. Unknown failures retain a generic message;
raw provider errors and proxy details are not stored in the job. Older generic
rows now explain that their exact cause cannot be recovered. The existing
pilot remains a real browser search, with no mock fallback or automatic import.

No website was opened or clicked for this change. Targeted deployment/workspace
tests passed 24 checks with simulated collector failures; Node syntax checks
passed. The app was restarted without an active pilot; its collector-status API
returned the new setup-only wording. Primary SQLite integrity remained `ok`
with 17 logical rows before and after restart.

## Windows Edge Maps alternative — 2026-10-09

Windows now defaults to the installed Microsoft Edge browser and a pinned
`playwright-core` package in ignored `.local/browser-tools`. Docker remains an
optional runtime. The browser process receives network/runtime variables and
`SystemRoot`; app tokens and provider credentials are excluded. TLS validation
and managed proxy routing stay enabled. **Open Google Maps** opens the typed
search in a separate tab for manual inspection; it does not save or scrape.
**Start live pilot** performs the automated small-sample collection, retains
the source pages and CSV, then requires the existing Preview → Import action.

Live checks succeeded on this Windows laptop: one listing through the collector
CLI and one listing from the app button. The app job completed, its UI preview
showed one valid row, and the isolated app database still had zero businesses
before import. The source HTML was retained, TLS was verified, and the CSV hash
matched its manifest. No business was contacted. Manual Maps navigation passed
the isolated browser fixture. The research UI suite now passes 17 checks; the
Automation and Client suites have five and nine checks respectively. The full
Python suite's previous 179-test result predates the final local-runtime test;
22 targeted deployment/workspace tests passed after it. No full-site regression
run was repeated for this small, scoped change.

The live result was categorized as a tanning salon, exposing a relevance false
positive for the med-spa query. It was not imported. CSV preview now retains the
source category in provenance and displays it as a row warning; live-pilot
imports also require an explicit checkbox confirming the categories were reviewed.
The targeted CSV import suite passed 16 tests after this safeguard, and the
workspace JavaScript and collector/Python modules passed syntax compilation.
The category checkbox itself was not rerun in the browser, per the request to
avoid another website test. Human category review remains necessary; this small
sample does not establish discovery quality or broad Maps coverage.

## Calm Studio discovery pass — 2026-10-09

The local Windows source now shows an authenticated collector-readiness check
before enabling **Start live pilot**. The check has bounded Docker calls and
never pulls an image. Collection also checks prerequisites before contacting
Maps or creating an output directory. Known prerequisite and network failures
are saved as safe, actionable job messages; older generic failures cannot be
reconstructed from their stored rows. The current laptop returned
`docker_unavailable`; the pinned image is also absent, so no app collector run
or live import was claimed.

The workspace has a warm **Calm Studio** visual pass with compact navigation,
clear Collect → Preview → Import steps, a visible collector status, and a
responsive CSV path. It uses original CSS and the existing AIAutomation assets;
no frontend dependency was added. The discovery page was inspected in visible
Edge at 390, 1440 and 1900 px. Isolated visible Edge fixtures passed **30
checks** (16 research, five Automation lab, nine clients/tasks/operations).
An 18-screen desktop/phone sweep found zero JavaScript errors, broken images,
document overflow or visible buttons below 32 px. All browser writes used
separate fictional SQLite databases; no primary business was contacted.

The final full Python suite passed **179 tests** after the collector preflight
change; targeted deployment, CSV and workspace tests also passed 37 checks.
The Docker image and live provider integrations remain unverified.

## Windows provider checks and Tabler-inspired UI — 2026-10-09

The current source passed **175 Python tests** after two Windows Docker-collector
compatibility fixes. The updated UI passed **29 visible Edge fixture checks**:
15 research/CRM, five Automation lab and nine client/task/operations. The
client browser suite now uses the mobile Sections menu when testing phone
navigation. An 18-screen desktop/phone sweep found zero JavaScript errors,
broken images or document overflow. The only sub-32 px visible controls in
the sweep were lead-name buttons; they were enlarged and retested at 38–41 px.

The design uses [Tabler](https://github.com/tabler/tabler) as a visual reference
for spacing, cards, tables and forms while retaining the app's existing CRM
structure, branding and backend contracts. No frontend dependency was added.

[Live integration checks](LIVE_INTEGRATION_CHECKS.md) record a real public
website fetch, HTTPS reachability of Google Maps/OpenAI/Resend/Twilio, and two
visible Maps searches. One medical-spa listing was inspected without import.
Missing provider credentials keep AI/email/calls unverified. The pinned Docker
collector image was absent. After C: free space rose from roughly 153 MB to
3.2 GB, an exact-image pull was attempted; it made no visible layer progress
and was interrupted when the daemon stopped responding promptly. No app
collector run occurred. No business was contacted, and the primary
database was not used for fixture writes.

## Visible control audit and mobile navigation — 2026-10-09

The current source passed **29 isolated visible Edge fixture checks**: 15
research/CRM, five Automation lab and nine client/task/operations. The research
suite now checks the lead-to-Tasks path and the mobile Sections menu. A separate
visible Edge control audit passed **99 overlapping assertions** across the nine
screens, nested client setup, lead details, downloads, keyboard navigation and
mobile controls. Its [control matrix](UI_CONTROL_AUDIT.md) records each exercised
control and guarded live action. An 18-screen desktop/phone sweep found no
JavaScript errors, document overflow, broken images or narrow mobile buttons.

The audit reproduced a lead dialog that remained open after its **Manage
follow-up tasks** link changed the route. Hash navigation now closes the dialog;
the exact click path passed in visible Edge. Mobile now has a Sections menu with
all nine destinations, current-page feedback and keyboard/outside-click closing.
The lead dialog also fills the phone viewport without horizontal shift.

All fixture records were fictional and lived in separate SQLite databases. No
real collection, external website fetch, AI request, email or call was triggered.
Those credential/network paths remain separate from these UI checks. Browser
logs, screenshots and scripts are retained under ignored
`.local/control-audit-2026-10-09` and `.local/visible-ui-audit-2026-10-09`.

## Visible Edge interaction and graphics pass — 2026-10-09

The final UI was exercised in **visible** Edge windows against isolated fictional
SQLite data. The research, Automation lab and client browser suites passed all
**28 checks** after the graphics changes. A separate visible tour opened all nine
sections. Additional visible checks covered pilot preview, raw/spreadsheet CSV
downloads, saved-evidence download, manual task cancellation, a loading spinner
during a delayed refresh, and reduced-motion behavior. An 18-screen desktop/phone
visual sweep found no JavaScript errors, broken images, document overflow or
undersized mobile buttons. Source JavaScript syntax also passed. Logs, screenshots
and test-only browser scripts are under ignored `.local/visible-ui-audit-2026-10-09`.
All business and customer data in these tests was fictional; no scrape, email or
call occurred. The primary database was not used for the visible tests. Live
provider actions and public hosting still require their separate verification.

## Browser usability audit and UI polish — 2026-10-09

After the restrained glow, readability and mobile navigation changes, **28
isolated Edge fixture browser checks** passed again: 14 research/CRM, five
Automation lab, and nine client/task/operations. JavaScript and CSP error lists
are empty. A separate browser agent navigated all nine screens at 1440 px and
390 px, found no broken images or document overflow, and passed eight additional
safe controls with fictional records: client history, readiness, handoff download,
lead dialog, saved views/search, global search, reminder step history and
operations refresh. The agent confirmed the visible mobile swipe cues, inline
consent checkboxes and 40 px Lock/refresh targets. Screenshots and reports are in
ignored `.local/ui-audit-2026-10-09/visual`; the fixture suite logs are in the
same audit folder. No real collection or provider action occurred, and the
primary database was not used. The local preview on port 8000 remained running.

## Local button and workflow audit — 2026-10-09

The current source passed **29 isolated Edge browser checks**: 14 research/CRM,
five Automation lab, nine client/task/operations, and one direct mobile check of
pilot preview plus both CSV download buttons. The spreadsheet download prefixes
the synthetic phone cell as text; the original raw CSV remains unchanged. The
browser reports contain no JavaScript or CSP errors. Fictional fixtures ran in
separate SQLite databases under ignored `.local/ui-audit-2026-10-09`; no real
business was contacted and the primary research database was not used. The audit
found no reproducible button defect, so no UI behavior was changed. Docker's Linux
engine was unavailable; these are local Edge checks, not packaged-image or live
provider verification. Reports and logs are retained in that ignored audit folder.
The complete Python suite also passed **173 tests** on Python 3.13.

## Windows recovery and security hardening — 2026-10-09

The local Windows review reproduced one failing backup restore test in the prior
170-test suite. Windows short/long path forms and manifest path separators caused
the failure. Backup copies now canonicalize discovery paths, use portable manifest
names, and restore older Windows manifest names. Six isolated backup tests pass,
including recovery after the original scraper folder is removed.

The bundled local collector subprocess now receives an allowlist of runtime and
proxy variables instead of the API's full environment. A fixture test confirms
that API/email credentials are absent while HTTPS proxy routing remains present.
Successful pilot jobs now offer a separate spreadsheet-viewing CSV with common
formula-leading cells prefixed as text; the original hashed CSV and import behavior
are unchanged.
The container entrypoint rejects APP_ENV=development before binding publicly.

The complete Python suite passed **172 tests** on this Windows machine with
Python 3.13. The entrypoint guard was added afterward and its isolated startup
test passed; it brings the source suite to 173 tests, but the complete 173-test
suite was not rerun. JavaScript syntax and Python compilation checks passed.
Docker Desktop's Linux engine was unavailable, so no new packaged/browser or
live provider checks were run. The running loopback preview returned healthy and
ready, and the new route was registered. Read-only SQLite integrity was `ok`
with 14 local records both before and after the preview restart. No real lead was
collected or contacted during this verification.

Residual deployment limits: Chromium still uses `--no-sandbox` in the shared app
container, and the proxy resolves website hostnames after the API's public-IP
validation. Public hosting needs isolated browser execution, private-destination
blocking at egress, ingress rate limits, and individual accounts/roles for separate
clients. The current source change does not establish those controls or a public
deployment.

## User logo update — 2026-10-08

Transparent assets prepared from the user's coral/navy and navy A references
replace the letter tile, favicon and shared-access card branding. This source
update is published on the Windows preview branch; the previously packaged
v0.10 image below predates this logo change and was not rebuilt for it.

The existing public-shell/API-auth test passed. All six existing real-cohort
browser checks passed against an isolated copy of the retained research database.
Ad hoc browser inspection verified PNG loading, favicon responses, sidebar fit
and absence of horizontal page overflow at widths 1600, 960 and 390; JavaScript
errors were empty. The navy access-card logo was inspected with a simulated 401
readiness response. No new provider action or primary-data mutation occurred.
Reports/screenshots are retained under ignored `.local/logo-verification`.
Windows instructions include a static-only update that preserves local leads.

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
