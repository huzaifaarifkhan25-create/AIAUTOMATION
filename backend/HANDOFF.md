# Backend handoff — v0.10.0

The 2026-10-09 local hardening pass is described at the top of
[VERIFICATION.md](VERIFICATION.md). Its source changes have not been packaged or
checked with a live provider; the v0.10 release counts below are historical.

The hackathon backend MVP is implemented and verified for a shared operator
workspace with SQLite and one worker/replica. It supports the complete pilot flow:
discover → analyze → rank → record contact → generate workflows → execute sandbox
reminders → onboard/manage clients and export a handoff. The browser connects
these APIs. Live provider operation and public hosting still require configuration
and verification; completing this code does not establish either.
The browser uses the [HubSpot-inspired CRM layout](CRM_DESIGN.md), with saved-record
search, lead views/sorting and actual pending follow-up tasks on the overview.

| Capability | Actual behavior | Verification and limit |
|---|---|---|
| Free discovery | Collect real visible Google Maps listings or import scraper CSV, preview before saving, retain sources/provenance | Prior live collection succeeded; pilot is 1–10 visible listings without pagination. No new live scrape in this release |
| Research | Fetch allowed public HTML, retain dated evidence, score transparently, show unknowns and source discrepancies | Five real leads retained. Public fit never establishes an internal operational need; no booking/form execution |
| Ranking | Separate public prospect readiness from confirmed need and observed friction | Rules are tested heuristics, not conversion probabilities. Demos/opt-outs excluded by default |
| Contact | Outreach drafts, recorded stage/history, manual follow-up tasks | Saving a draft/task sends nothing. Human Twilio adapter is simulated in tests; no AI voice |
| Workflow generation | Current-analysis message graphs, JSON export/archive | Generated graphs have a real local runner; arbitrary graphs/calendar/n8n execution remains unsupported |
| Automation | Durable timing, steps, bounded storage retry, cancellation, restart recovery and unsent sandbox previews | Sandbox behavior is verified. Guarded Resend submission/callback/reconciliation is simulated, without actual email |
| Client delivery | Authorization/timezone, proof-based validation, reviewed local activation, managed reminders, pause/archive, audit/handoff | Activates this application's supported local runner. Does not create a separate client account or provision hosting |
| Operations | Current counts, task/run/provider issues and blocked/stale active setups, explicit demo filtering | Read-only bounded alerts; no external notifications. An empty list does not prove provider availability |
| Persistence/deployment | SQLite transactions, backup/recovery tooling, authenticated non-root release image and restart persistence | One worker and replica. Supabase research adapter is simulated; its runner/client/CRM features explicitly return 503 |

## Faults fixed before handoff

Twelve new isolated regressions failed against v0.8 and pass with the fixes:

- Opt-outs block known email addresses within that business despite contact-ID
  changes or case variants, including after restart and for legacy contact-only
  records. Manual opt-out and signed bounce/suppression evidence preserve this
  restriction. Different addresses are not automatically treated as the same
  person. An ID with no known address cannot identify a future unrelated ID/address;
  the caller must supply the actual permission and stable contact identity.
- Missing/invalid local dialer configuration does not reserve a call attempt or
  consume its key. Once a provider attempt is genuinely uncertain, the existing
  no-redial rule remains mandatory; reconcile by provider GET.
- Contact changes share the dialer/runner guards. New evidence commits and
  workflow archiving share the runner action guard. A completed change blocks
  subsequent actions; an action already submitted cannot be recalled.
- Operations flags active deployments when the client is inactive, evidence or
  configuration invalidates validation, or a saved reference is missing. Alerts
  preserve demo filtering and link to client review. Storage errors are reported
  as errors. Operators must pause, fix, revalidate and explicitly activate.

The current suite passes **170 Python tests**, **32 packaged checks** (eleven
API/container and twenty-one browser), and **six read-only real-cohort browser
checks**. Original primary data remains unchanged: 25 records, seven businesses,
five real leads with unconfirmed internal needs, and no primary client/task/
execution records. Provider tests use fictional data and simulated transports;
no real business was contacted. Exact evidence is in [VERIFICATION.md](VERIFICATION.md).

## Run and demonstrate

Use the repository README startup command, preserving the existing database and
website settings. Follow [WORKSPACE.md](WORKSPACE.md) for the full browser demo.
For command-line verification, run `backend/client_demo.py` against an isolated
SQLite API; it explicitly writes fictional records and creates unsent previews.
Run the Python suite from `backend/`. Run `deploy/build.py` then `deploy/verify.py`
from the repository root for isolated packaged verification.

## Requirements for actual email, calls and hosting

No live credentials or public host were available for this release. Configure
values securely in environment/hosting settings; never paste secrets into chat.

| Path | Required setup | What still needs a real check |
|---|---|---|
| Hosted workspace | Persistent `/data`, one worker/replica, strong `APP_API_TOKEN`, explicit `APP_ALLOWED_HOSTS`, HTTPS ingress | Authenticated readiness, persistent restart/restore and scraper/website egress on the chosen host |
| Managed email | `ENABLE_EMAIL_DELIVERY=true`, `RESEND_API_KEY`, verified `RESEND_FROM_EMAIL`, actual runtime `RESEND_WEBHOOK_SECRET`, `APP_PUBLIC_URL`; confirmed client scope/recipient consent and sandbox proof | An isolated consenting test recipient, provider acceptance and valid signed delivery callback. Acceptance alone is not delivery |
| Human dialing | `ENABLE_OUTBOUND_CALLS=true`, valid Twilio account/key, verified caller number, `SALES_AGENT_NUMBER`, shared auth; public origin and actual runtime auth token for signed outcomes | A consented isolated agent/prospect test and matching signed sales-agent-leg outcome. Agent completion does not prove prospect answering |

Email/calling remain disabled by default. Configure the actual callback origin,
not an invented URL. Neither a proxy placeholder nor a saved secret requirement
provides local HMAC material. A chosen accessible hosting account is required
before public deployment. See [deploy/README.md](../deploy/README.md),
[MVP.md](MVP.md) and [HACKATHON.md](HACKATHON.md) for the full contracts.

Individual user accounts/roles, native calendar availability, SMS/AI calling,
automated prospect campaigns, arbitrary workflow engines, billing, distributed
workers and automatic off-host backups remain outside this pilot. These are
distinct product milestones, not features claimed by this handoff.
