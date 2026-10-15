# Connect real services privately

Accounts, CSV import, evidence, tasks and sandbox work require no external API
keys. The optional live services below are independent. Never send secret values
in a chat, commit them, or put provider keys in frontend environment variables.
Previously exposed keys should be revoked and replaced.

## 1. Gemini: live AI Agent and draft generation

1. Open **https://aistudio.google.com/apikey** and sign in to your Google account.
2. Choose **Create API key**, select or create an authorized project and copy the
   new value privately. Free-tier availability, model access and quota depend on
   the account/project; a billing plan is not assumed.
3. Start AIAutomation, register/sign in, then open **AI Agent**. On a local laptop,
   select Gemini, enter the private key in **Provider API key**, and choose
   **Connect AI**. The default is `gemini-3.5-flash-lite`; use an available
   tool-calling Gemini model if your project rejects it.
4. Click **Verify AI Agent**. A real provider must request a read-only workspace
   tool and return its actual token/count. Failure remains failure. Inspect
   provider/model/time and `tool_roundtrip_verified`, not just key presence.
5. Ask about saved records; inspect tool results. Writes require a separate
   **Approve & run** review. Verification does not guarantee every answer.

This connection also enables the separate AI insight/outreach draft APIs. A
session-only key stays in backend memory until restart/disconnection. For a
persistent Windows setup, run **SETUP-GEMINI-WINDOWS.bat** once and paste the new
key at its hidden prompt. It saves all four settings below in root private `.env`
without changing unrelated settings. Restart the backend once; later starts load
it automatically. The helper itself contains no credential, and `.env` is excluded
from GitHub/ZIP releases. This file contains plaintext settings; keep it private
and preserve it separately when updating. Existing process environment overrides
take precedence. You can also edit these entries privately instead:

```dotenv
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.5-flash-lite
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_API_KEY=YOUR_NEW_PRIVATE_KEY
```

Replace the last value; do not copy the placeholder as a real credential.
Use a different permitted model consistently if necessary. Production requires
server-side environment configuration; local key-entry forms are disabled there.
Codex/Kiro login, Stitch and the app's Gemini key are separate credentials.

## 2. n8n: actual workflow execution

You can self-host n8n locally without an n8n Cloud subscription. Install Docker
Desktop with Linux containers and run **START-N8N-WINDOWS.bat**. Then:

1. Open **http://127.0.0.1:5678** on your laptop and create the n8n owner account.
2. In n8n open **Settings → n8n API → Create API key**. Grant only the available
   permissions needed for workflows, execution readback and activation.
3. Sign in to AIAutomation. Under **Automations**, connect using base URL
   `http://127.0.0.1:5678` and that private API key. The form is local development
   only and keeps the connection in server memory.
4. For persistence, privately set `N8N_BASE_URL` and `N8N_API_KEY` in root `.env`
   and restart. For hosted n8n use its actual HTTPS origin and allow that hostname
   in the cloud network settings. Do not put a URL path or n8n editor route in it.
5. Create the fictional demo and deploy/process its task-only inquiry. Inspect
   the actual saved execution and task; pause the workflow when done.

The app supports only its fixed **Webhook → Set → Respond** graph. It verifies
that exact graph and saved execution, then commits a CRM follow-up task. No
n8n credentials, email node, arbitrary imported graph or campaign are allowed in
that template. Its acknowledgement is a draft; optional email runs separately.
An uncertain network result is not automatically replayed.

A real business workflow requires current business-confirmed follow-up evidence,
permission and a reviewed deployment. See [N8N.md](../backend/N8N.md).

## 3. Resend: actual acknowledgement email

You need a Resend account, a domain you control and a permitted test recipient.
A free allowance may be available, but domain registration/hosting can cost money.

1. Create an account at **https://resend.com**.
2. Under **Domains**, add your sending domain/subdomain and copy the displayed
   DNS records to your domain's DNS provider. Wait for verified status.
3. Under **API Keys**, create a private key with sending permission. Read-only
   provider reconciliation also needs permission to retrieve the submitted email.
4. Choose a plain verified sender address, for example `followup@your-domain`.
   Set `RESEND_FROM_EMAIL` to the actual address, without a display-name wrapper.
5. Deploy the app with public HTTPS as described below. Under Resend **Webhooks**,
   create `https://YOUR_APP_DOMAIN/webhooks/resend`, subscribe to sent, delivered,
   bounced, complained, failed and suppressed events, and copy its signing secret
   privately. The app verifies signed original request bytes and freshness.
6. Configure privately on the backend:

```dotenv
ENABLE_EMAIL_DELIVERY=true
RESEND_API_KEY=YOUR_PRIVATE_RESEND_KEY
RESEND_FROM_EMAIL=YOUR_VERIFIED_PLAIN_ADDRESS
RESEND_WEBHOOK_SECRET=YOUR_ACTUAL_WEBHOOK_SIGNING_SECRET
APP_PUBLIC_URL=https://YOUR_ACTUAL_APP_DOMAIN
```

A strong private `APP_API_TOKEN` is also required. These are placeholders to
replace, not working values. `RESEND_WEBHOOK_SECRET` must be the **actual direct
runtime value**, because the backend verifies its HMAC locally. A network-proxy
placeholder cannot perform that verification.

Activate an **email** inquiry source only after reviewing its exact subject,
acknowledgement, delay, authorized business and future-source permission. Incoming
contacts must have permission and no saved opt-out. Demo businesses cannot send.
Pausing cancels waiting work but cannot recall a submitted message.

The first real check must target only an address you own and explicitly consent
to contact, using non-clinical text. Inspect its engine execution, CRM task,
provider ID and signed delivery callback. **Submitted is not delivered.**
Read-only reconciliation can establish matched provider evidence when available;
ambiguous failures must not trigger a blind resend.

Email-mode intake intentionally requires public callbacks. A separate explicitly
confirmed, owned-recipient local runner test can work without public callbacks;
it does not prove the production intake/callback flow. See
[the local email check](../backend/INQUIRIES.md#local-owned-recipient-email-check-without-public-hosting).

## 4. Connect a real website/form

Under **Inquiries**, create a source for an active reviewed native deployment.
Save its one-time key in your **form server's** private settings. That server
POSTs JSON to the displayed `/intake/{source_id}` URL with `X-Inquiry-Key`.
Do not place the key in public JavaScript. The sender must retain a stable event
ID and reuse it with identical data when retrying one submission.

The sending server obtains actual customer consent before setting
`contact_permission: true`. This pilot handles general operational inquiries,
not patient/clinical records. It is not a replacement for a healthcare data
compliance system. See the exact schema and size limits in
[INQUIRIES.md](../backend/INQUIRIES.md). Key rotation invalidates the old key;
pausing blocks future processing. No automatic consent inference is implemented.

## 5. Public hosting and backups

Use a Docker-capable Linux host with persistent disk and a domain you control.
Follow [PRODUCTION.md](../deploy/PRODUCTION.md): frontend, one SQLite API worker,
Caddy HTTPS and optionally n8n. Generate private service/encryption values locally
and save them in the host's protected environment. Direct local values such as
`APP_API_TOKEN`, `RESEND_WEBHOOK_SECRET` and `N8N_ENCRYPTION_KEY` must never be
replaced with outbound network credential placeholders.

No hosting account or public domain was supplied for this build. Source and
configuration are prepared; public DNS/TLS, live provider delivery and off-host
restore need verification on the chosen host. Keep private backups of app data,
scrape evidence and n8n separately. Updating must preserve named volumes.

## Codex cloud settings

The existing environment draft declares `GEMINI_API_KEY` for
`generativelanguage.googleapis.com` and `RESEND_API_KEY` for `api.resend.com`.
Enter private values through the environment's secure settings, not chat. Secret
names and hostnames are requirements; saving them does not create a valid key.

Local signature checks use the actual raw direct runtime settings described
above. A hosted n8n destination cannot be added until its hostname is known.
After editing, **review/save the environment settings and publish the environment**
when required. Draft saving alone neither injects values nor applies network
access, restarts services or publicly deploys the app.
