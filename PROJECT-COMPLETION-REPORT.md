# Current build and remaining live setup

Updated **2026-10-15 — v0.14.0**. This report describes the integrated source on
`codex/complete-automation`, based on GitHub preview commit `b43b2f2`, while
preserving the previous v0.13 work on a local recovery branch. It supersedes older
feature-gap and reload-lock descriptions. Main and the existing preview branch
are preserved.

## What is implemented

| Area | Current behavior | Verification and remaining limit |
|---|---|---|
| Individual accounts | Register/sign in/out, salted password hashes, persistent revocable sessions, CSRF/origin checks and invitation code when configured. Next.js forwards the actual operator session. | 15 backend account tests, 19 isolated HTTP bridge checks and production/browser account flows passed. All operators share one workspace. No roles, private tenants, email verification or password recovery. |
| Native n8n | Deploys one fixed Webhook → Set → Respond inquiry graph; verifies the graph and successful saved execution before creating one idempotent CRM task. Pause blocks later task commits, including processed-run retries. | 22 backend native tests plus real official local n8n 2.42.6 and browser execution passed. Arbitrary graphs, native calendars and n8n email nodes are not supported. |
| AI Agent | 34 fixed tools, durable shared conversations, grounded reads, reviewed proposals, idempotent approvals and a strict read-only provider/tool verification. Local Gemini connection also enables existing AI draft APIs. | 46 Agent tests use simulated provider transport. Missing-provider UI is checked; no fresh live Gemini check in this build because no valid key is injected. Agent cannot self-approve, run arbitrary code or send live email. |
| Real inquiry intake | Source-scoped `/intake/{id}` with one-time hashed key, rotation, pause, bounded JSON and stable event IDs. Binds an approved deployment/template/delay. Actual native proof precedes the task. | 19 inquiry tests and real local n8n intake checks passed: wrong key rejected, duplicate reuses task, changed event conflicts, pause blocks, demos excluded. Public HTTPS ingress requires hosting. It does not automatically modify a customer's website. |
| Guarded email | Explicit source-level approval can send its fixed acknowledgement through Resend. Recipient permission, opt-outs, source/deployment/evidence/sender guards, idempotency, signed callbacks and read-only reconciliation remain enforced. | 15 delivery tests and source/lifecycle tests passed with simulated provider responses. No real email was sent. Live operation needs a key, verified sender, signing secret, public callback host and an owned consenting test address. |
| Measured outcomes | Counts actual received inquiries, verified tasks and their completion/overdue state; separates provider submission, delivery, failures and safely stopped work. Measures intake-to-task time. | Seven outcome tests and browser demo-filter/count checks passed. No inferred revenue, bookings, customer-response time or time savings. |
| Persistent operation | Current Next.js standalone/API/Caddy Compose configuration, optional n8n, persistent SQLite/scrapes, non-root runtime, backup/restore helper, backup timer and Windows launchers. | Production standalone passed 10 HTTP checks; four Compose profiles and both actual scratch build-context exports passed. Seven backup regressions passed. Full new application containers, public DNS/TLS and physical Windows launcher execution remain unverified. |

Existing CSV/discovery, website evidence, explicit scoring, multilingual unsent
outreach, tasks, sandbox reminders, client operations and the older `/app/` UI
were retained. The purple UI gained **AI Agent**, **Automations**, **Inquiries**
and **Outcomes** pages with the same visual theme. Older fallback access remains
shared-token based; account login is in the purple UI on port 3000.

## What makes the automation real

A form server submits an authenticated operational inquiry. The app reserves the
event, executes the fixed workflow through an actual n8n server, reads matching
successful execution evidence, then commits a deduplicated follow-up task. The
acknowledgement is unsent unless a separate reviewed email source has been enabled.
That email uses the backend's Resend adapter rather than an unrestricted n8n node.
Delivery is confirmed only by signed callback or matched provider reconciliation.

The local integration proof used native execution **10** and intake execution
**12**, each producing one fictional task with identical retries reusing it.
The browser acceptance pass exercised another real execution through the complete
UI. These are working local engine results with fictional data, not proof of
customer benefit or public hosting. All test workflows were paused afterward.

## Verification of this source

- Python full suite: **309 discovered, 307 passed, two Windows-only skips**.
- Frontend: **four unit tests**, typecheck and production build passed.
- Final production browser acceptance: **12 checks passed**, including mobile
  views, custom CSV mapping, task actions, actual n8n intake, demo-filtered
  outcomes, pause and revoked logout. No JavaScript errors.
- Account identity bridge: **19 HTTP checks**; account writes forwarded Cookie
  and CSRF without substituting the owner bearer, and revoked cookies did not
  fall back to owner access.
- Latest standalone output: **10 production HTTP checks** for assets, accounts,
  secure cookies, cross-origin rejection and revocation.
- Four Compose profile configurations and both actual Docker scratch context
  exports passed. This is not a full application-image build or TLS deployment.
- Linux env-file startup and the copied local `.env.example` passed. Windows
  batch files were source-reviewed; they were not run on Windows here.
- Primary SQLite read-only integrity was `ok`; all **25 logical records** retain
  their pre-build hash. Primary account/session/rate-limit tables remain empty.

Exact scope, retained local report paths and excluded checks are recorded at the
top of [backend/VERIFICATION.md](backend/VERIFICATION.md). Private fixture
artifacts, data, credentials, dependencies and build caches are excluded from
GitHub source downloads. No real business/customer was contacted.

## Remaining work before calling it live

1. **Connect a new Gemini key**, then run the real Agent tool verification on
   the actual installation. Review generated text and approved action results.
2. **Connect your n8n instance.** The app integration is verified locally; a new
   laptop/host must repeat its own deploy/process/pause check.
3. **For email**, verify a Resend sender/domain and configure its private API and
   signing keys, direct runtime settings and public callback URL. Test only an
   owned consenting recipient and inspect confirmed provider evidence.
4. **Choose a persistent host/domain**, build/start the configured containers and
   verify DNS/TLS, public ingress, restart persistence, limits and off-host restore.
5. **Validate the service with a real authorized med spa.** Public prospects do
   not prove a follow-up gap; record actual business confirmation and permission.
   Keep clinical/patient records outside this general-inquiry pilot.

No API keys are required to inspect the UI, register, import CSVs or use manual
and sandbox features. [CREDENTIALS-SETUP.md](docs/CREDENTIALS-SETUP.md) explains
where each key comes from and exactly where to enter it privately.
[WINDOWS-START-HERE.md](WINDOWS-START-HERE.md) explains installation and upgrades.
[deploy/PRODUCTION.md](deploy/PRODUCTION.md) covers hosting and recovery.

The implementation is a scoped single-workspace pilot. It is not a claim that an
unconfigured server is fully live or ready for unrestricted customer use. Dialer
expansion, arbitrary workflow flexibility, calendars, SMS, billing, private
company tenancy and role administration remain outside this build.
