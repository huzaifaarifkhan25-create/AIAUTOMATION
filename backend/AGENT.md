# AI Agent — v0.14.0

The **AI Agent** sidebar screen uses Gemini or OpenAI tool calling to work with
this app's saved records. Chat runs on the server. A closed registry of 34 tools
retrieves evidence and creates reviewable action proposals. The agent cannot
approve its own proposals. Approved actions use the existing backend services.

## Verify the live AI connection

After connecting, click **Verify AI Agent**. The check requires the provider to
call the read-only workspace tool and copy its actual count/token in a second
response. It creates no conversation, proposal or business write. The page shows
the time, checked provider/model and result. A failed check stays failed;
connection success alone does not establish verified tool calling.

The fixed native n8n integration adds three reads and four reviewed actions:
status, deployments, runs, fictional inquiry demo, deploy, process inquiry, pause.
See [N8N.md](N8N.md). All seven tools stay within the inquiry-to-task template.
The restored agent also reads saved AI estimates/drafts, incoming inquiries and
recorded outcome metrics. Inquiry list results omit customer text and email;
inspecting one inquiry reveals its customer text as untrusted data while still
withholding the recipient address. Customer text cannot authorize an action.

## Connect Gemini on your Windows laptop

1. Update the whole backend using [the Windows guide](../WINDOWS-START-HERE.md),
   keeping your existing `.local` folder and imported leads.
2. Start the app, refresh with **Ctrl+F5**, sign in with your operator account,
   and open **AI Agent**.
3. Create a key in [Google AI Studio](https://aistudio.google.com/apikey).
   Free-tier availability, supported models and quota depend on your project.
4. Keep **Gemini** and `gemini-3.5-flash-lite`. Paste the key into **Provider API key**,
   then click **Connect AI**. Never paste it into chat.
5. The server makes a real connection request. Success enables chat; rejected
   keys, unsupported models, quota and network failures show errors. There is
   no fabricated answer fallback.

The laptop key stays in server memory until restart or **Disconnect AI**. Our
code does not write it to SQLite, history, logs or browser storage. Reconnect
after restarting. The form is limited to signed-in operator accounts on loopback
clients in development; an API bearer alone cannot enter a private key. Account
CSRF and same-origin checks also protect this form even when a bearer is supplied.
production uses secure server environment configuration. This local connection
enables the Agent and the separate Gemini insight, pitch and human call-script
APIs together. Those APIs retain their sender/language requirements and factual
citation checks. Connecting OpenAI clears the temporary Gemini override.
Disconnecting clears temporary settings and returns to environment configuration,
if present; it cannot remove credentials supplied to the server's environment.
The optional legacy research-summary provider still uses environment settings.

Connection success tests access; `tool_roundtrip_verified` separately reports a
successful read-only count/token verification. A completed chat or successful
connection alone does not establish that every answer is grounded or correct.
Gemini structured retries use the same credential/model snapshot throughout one
request, and saved results name that model. Before saving a new outreach draft,
the draft APIs recheck opt-out, archive and current analysis under the action
guard. A research change requires regeneration; historical drafts stay readable.

Questions, relevant records and recent conversation context go to the selected
provider. Saved conversations/action history are shared by operators with the
workspace access. Individual operator accounts also share these conversations;
there are no private per-user chats. See [ACCOUNTS.md](ACCOUNTS.md).

## Try it with imported records

- “Show my saved med-spa leads. Which ones need more research?”
- Select **Business context**, then ask “Explain this business's score. What
  is known, and what still needs verification?”
- “Create a task for [exact business name] titled Verify its official website,
  due [your actual future date and time] in Asia/Karachi.”
- “Prepare an outreach draft for [business name].” This returns unsent text.
- “Show my pending tasks and current automation status.”

Use exact business names and explicit timing. The agent is instructed to ask
about missing or ambiguous details. It uses your browser's IANA timezone.
Expand tool results to inspect the actual data supporting an answer.

Writes appear under **Action review**. Check the business, text, permissions and
dates, tick the checkbox, then **Approve & run** or **Reject**. The card's
recorded status/result describes the backend outcome. Chat text is not proof an
action ran. An LLM can misunderstand a request or explain it incorrectly;
tool validation and review do not make natural-language claims infallible.

## Supported tools

| Area | Reads | Changes after review |
|---|---|---|
| Research | Search leads, inspect qualification/evidence, prepare unsent outreach | Analyze a saved lead; start real 1–10-listing collection when the collector is configured |
| CRM | List tasks, clients and client deployments | Create/complete/cancel tasks; add notes; pause clients/deployments |
| Workflows | Inspect saved drafts and graphs | Create a supported draft from the current qualifying analysis |
| Automation | Inspect recorded appointments/runs | Create a fictional demo; schedule unsent sandbox reminders; cancel appointments/runs |
| Operations | Counts, current alerts and discovery-job states | No autonomous live outbound action |
| Native n8n | Connection status, managed deployments and verified execution/task results | Create fictional inquiry demo; deploy the fixed template; process an inquiry; pause a native workflow |
| Incoming inquiries and outcomes | Recorded inquiry states, customer text on explicit inspection, task/execution references and outcome counts | No autonomous intake processing or live email submission |
| AI drafts | Saved estimates and unsent draft history | Sender/language-aware generation remains on the separate draft screens/APIs |

CSV upload/import, evidence confirmation, client authorization, deployment
validation/activation and live-channel setup use their existing screens. There
are no agent tools for arbitrary code/SQL/URLs, secrets, approvals, live emails,
calls or SMS. It can deploy only the fixed inquiry-to-task native n8n template. It cannot access calendar availability,
provision hosting or billing. An unconfigured scraper never substitutes dummy
leads. Referencing fictional records requires the explicit demo scope.

Analysis preserves operator/legacy evidence and recomputes automatic observations
when fetching. Workflow proposals bind to their analysis and fail if outdated.
The existing opt-out, archive, permission, timing, client/deployment and storage
guards still apply. Public fit cannot establish an internal operational need.

## Persistence, retries and limits

SQLite and one worker/replica are required. Unsupported Supabase agent routes
return 503 without breaking supported research. Conversation/message requests
use idempotency UUIDs. Lost responses can be retried with identical inputs/key.
Completed approvals return their existing result without re-executing. Failed,
rejected or expired actions need a new proposal. Proposals expire after 24 hours.

On restart, a running chat becomes interrupted; an executing action becomes
uncertain and is not replayed. Inspect its underlying record before requesting
another action. Task/note/reminder keys also use the durable action ID.
Chat and reviews serialize within the single worker. Each turn allows six
provider rounds, 15 tool events, five proposals and 150 seconds. Conversations
allow 50 turns; start a new one when full. The selector lists the latest 50
conversations; older histories remain available in SQLite/API by ID.

Logout clears workspace access. Account sessions survive reload; the optional
legacy preview session still locks on reload. Delayed responses cannot restore
revoked access. React escapes provider/user text. The
connection password is separate from chat. Known credentials/common key shapes
are rejected in chat; configured secrets are redacted from tool/model data.
This is not a universal sensitive-data classifier.

## Server configuration and API

For Gemini set `LLM_PROVIDER=gemini`, `LLM_MODEL=gemini-3.5-flash-lite` and secure
`GEMINI_API_KEY` (preferred) or `LLM_API_KEY`. Allow HTTPS to
`generativelanguage.googleapis.com`. OpenAI remains supported with
`LLM_PROVIDER=openai`, an appropriate model and `LLM_API_KEY` or `OPENAI_API_KEY`,
targeting `api.openai.com`. Never check in keys. The root `.env.example` is
documentation and is not automatically loaded; Compose reads its deployment
env file.

All `/agent` routes use workspace authentication when its token is configured:

- `GET /agent/status` reports configuration/capabilities without credentials.
- Local development only: `POST /agent/connection` with provider, model and
  `api_key`; `DELETE /agent/connection` clears it.
- `POST /agent/conversations` with UUID `idempotency_key`; `GET /agent/conversations`.
- `GET /agent/conversations/{id}` returns turns and action cards.
- `POST /agent/conversations/{id}/messages`: UUID `request_id`, `message`, optional
  `business_id`, literal `include_demo` and `timezone`.
- `POST /agent/actions/{id}/review`: `conversation_id`, `decision` of
  `approve`/`reject`, literal `confirm_action=true` to approve.

## Verification

Python tests use simulated provider responses with actual SQLite and backend
services. They cover provider errors, Gemini tool signatures, all read tools,
auth, review/retries, opt-outs, scope, stale workflows, task/client/cancellation
guards, sandbox scheduling, restart uncertainty and credential/timezone handling.

`frontend/tests/workspace-browser.cjs` exercises the integrated UI with an
isolated database and real local n8n, including truthful missing-provider
behavior. Backend Agent tests use simulated model transport; they are not a
product fallback. Separate production HTTP checks cover authenticated assets,
account sessions and revoked access. Exact results are in
[VERIFICATION.md](VERIFICATION.md).

Version 0.13 also passed live Gemini tool verification and a reviewed
demo/deploy/process/readback flow through real n8n. The simulated checks above
remain distinct from that live evidence; see the current top of
[VERIFICATION.md](VERIFICATION.md). Reconnect and repeat the live check on a new
laptop/server; prior cloud results do not establish its current provider access.
The v0.14 regression checks additionally cover account-only local setup, CSRF
despite bearer authentication, one Gemini connection enabling the native draft
provider without persistence, environment fallback, strict boolean-count
rejection, provider overload errors and scoped inquiry reads. These use isolated
fictional data and simulated provider transport. No exposed historical key is
used for verification of this restored build.
