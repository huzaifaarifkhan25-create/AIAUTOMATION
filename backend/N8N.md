# Native inquiry follow-up automation

The supported graph runs on a real n8n server:
**Webhook → Prepare follow-up (Set) → Return task instruction (Respond)**.
The app checks the graph before invoking it, reads the saved successful execution,
then commits an idempotent CRM follow-up task. The n8n graph prepares an
acknowledgement draft; it contains no email, delivery, code or arbitrary HTTP node.
Actual optional email delivery belongs to the app's separate guarded delivery
runner, after an intake source has been explicitly approved.

## Windows setup

1. Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   with Linux containers.
2. Double-click `START-N8N-WINDOWS.bat`. The first launch downloads official n8n
   2.42.6, pinned to its verified manifest digest. Later launches reuse the container.
3. Open **http://127.0.0.1:5678** and create a local n8n owner account.
4. Open **Settings → n8n API → Create an API key**. If scopes are offered, allow
   workflow list/read/create/activate/deactivate, credential create, and execution
   read. A paid n8n cloud account is not required for this local setup.
5. Start AIAutomation and sign in. In **Automations**, connect using the local URL
   and key. The private key form is restricted to signed-in loopback development
   sessions; API bearer authentication alone does not permit key entry.
6. Create the explicitly fictional inquiry example, deploy its reviewed template,
   and process an inquiry with a future follow-up time and confirmed permission.
7. Check the saved **execution ID** and **task ID** in the app. In n8n, inspect
   the saved execution. Pause deactivates the remote workflow.

Docker retains workflows and account data in `aiautomation-n8n-data`. Keep that
volume when updating the app. Local connection forms keep keys only in server
memory; reconnect after restart. The Windows launcher cannot run on the Linux
development machine; live integration checks use the same official npm version.

## Hosted configuration

Set `N8N_BASE_URL` to the public HTTPS n8n origin and `N8N_API_KEY` as a server
secret. Allow that hostname through the hosting environment's network settings.
Redirects are refused. Origins containing credentials, paths, queries or fragments
are refused, as are HTTPS targets resolving to private or non-public IP addresses.
Plain HTTP loopback connections are development-only. Use SQLite and one app
worker/replica for this bounded integration.

Keep keys out of chat, Git, frontend variables and browser storage. A deployment
belongs to the original origin/key pair; reconnect that pair to inspect or pause
it. Rotating the key requires reviewing a replacement deployment rather than
silently reusing old webhook authentication.

## Supported API and durable behavior

- `GET /n8n/status`: configuration/readiness metadata; no key.
- `POST` or `DELETE /n8n/connection`: session-only local setup/disconnection.
- `GET /n8n/template`: native JSON with placeholder path and no credential binding.
- `POST /n8n/demo`: explicitly fictional business, confirmation and workflow.
- `GET /n8n/deployments`, `GET /n8n/runs`: safe saved result views.
- `POST /n8n/deployments`: UUID `request_id`, saved `workflow_id`, and literal
  `confirm_deployment=true`.
- `POST /n8n/deployments/{id}/pause`: deactivate without needing current research.
- `POST /n8n/deployments/{id}/inquiries`: UUID `request_id`, `contact_reference`,
  `inquiry`, `acknowledgement`, aware future `followup_at`, and literal
  `contact_permission=true` plus `confirm_run=true`.

Deployment requires a current inquiry-follow-up draft and recorded
**business-confirmed inquiry-follow-up need**, including strong or partial
confirmation. A public-friction observation or AI estimate cannot authorize it.
Mock examples remain marked synthetic and never become evidence about real leads.
Archive, stale analysis and business opt-out block new processing. Those guards
are checked again under the execution lock before task commit, after network I/O.
The deployment must still be active, including when retrying only the local
task commit after a previously verified execution. Pausing prevents that commit.
Pause remains available when research becomes stale or a business opts out.

Each deployed webhook uses a Header Auth credential derived from the app's private
n8n key and deployment ID. Neither the token nor credential data is returned to
the UI. The app verifies the active remote graph's exact supported node types,
parameters, connections and credential ID before triggering it. It checks the
graph snapshot of the saved execution again before committing a task. External
workflow edits are unsupported; detected edits block processing or leave the
execution uncertain for review, rather than asserting that an edited graph was safe.

Success requires matching inquiry output, the expected workflow/execution IDs,
a successful saved execution, matching saved output and a persisted CRM task.
The n8n result always carries `delivery_status=unsent_draft`; later delivery status
must be read from the app's separate email outbox. Identical run requests reuse
the same task. Changed inputs under the same request ID conflict.

Deployment/run reservations are written before external mutations. An interrupted
or ambiguous submission remains **uncertain** and is never automatically replayed.
A verified execution that could not commit a task remains **processed**; repeating
the same request can safely attempt only the local idempotent task commit. Activation
can precede webhook registration; the app retries only n8n's explicit “not registered”
response with a bounded short wait, rather than retrying ambiguous executions.

The reviewed AI Agent can inspect status/history and propose deployment,
processing or pause. Provider/tool verification confirms a read-only roundtrip;
it does not establish that every future answer is correct.

There is no arbitrary workflow editor, native booking/calendar integration, SMS
or AI calling in this feature. Provider-backed behavior must be distinguished from
simulated tests and separately recorded live evidence.

## Current verification

On 15 October 2026, 22 native integration tests passed against the integrated
backend. They use a simulated provider to check auth/CSRF, graph edits, opt-outs,
stale evidence, idempotency, uncertainty/recovery and ordered pause behavior.
A separate isolated check against official n8n 2.42.6 completed real execution
`10`, verified its saved three-node graph/output and committed one fictional CRM
task (`922029bd-de1f-5bf6-9ca6-01d1ba5398f0`). Repeating the request reused the task;
remote pause was confirmed afterward. No customer email was sent. The private
runtime evidence is `.local/complete-automation/n8n/live-proof.json` and is excluded
from release archives. External-edit rejection has simulated-provider coverage;
the limited live API key deliberately has no workflow-update permission.
