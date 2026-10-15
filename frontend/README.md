# AIAutomation purple workspace

The Next.js interface uses the same backend records as the older `/app/` CRM, preserving the owner's purple theme and existing multilingual email/call-script panels. Open **http://127.0.0.1:3000** for this interface; port **8000** is the backend.

## Start on Windows

Use `START-APP-WINDOWS.bat` in the repository root. It opens the backend and frontend in separate terminal windows. See [local setup](../deploy/LOCAL-RUN.md) for prerequisites and troubleshooting. Keep `.local` when updating the code, because it contains your local database.

For manual startup:

1. Start FastAPI on port 8000 with a persistent SQLite database and exactly one worker.
2. In a separate terminal, set server-only `BACKEND_URL=http://127.0.0.1:8000`.
3. Run `cd frontend`, `npm ci`, and `npm run dev`. Open port 3000.
4. Register the first operator account. If the backend has `APP_API_TOKEN` configured, registration requires that workspace invitation code.

Individual account sessions survive reload and use backend authentication and CSRF checks. Logout revokes the session. All operators share one workspace; separate company databases, roles and password recovery are not implemented. Optional legacy access-code mode remains available only when its four server variables are configured; it still locks on a full-page reload.

Do not prefix credentials with `NEXT_PUBLIC_`. The proxy forwards authenticated backend session cookies through server code. Credentials never belong in chat messages.

## Functional pages

- **Discover:** live collector status/jobs and CSV preview/import with explicit column mapping, source labels and duplicate validation.
- **Leads:** evidence, direct business confirmation, rules analysis, current workflow drafts, contact/task history, and the existing sender/language panels for unsent pitches and human call scripts.
- **Tasks:** create manual tasks and mark saved pending tasks complete or cancelled.
- **AI Agent:** persistent conversations, scoped saved-record tools, exact proposals requiring review, and a live read-only tool round-trip verification. Missing provider credentials produce a setup state, not fake replies.
- **Automations:** configure/check n8n, create explicitly fictional demos, deploy the supported inquiry template, run a permitted manual inquiry, inspect actual execution/task evidence, and pause managed deployments. Manual acknowledgement drafts stay unsent.
- **Inquiries:** authorize fixed source settings, receive a one-time intake key for your form server, pause sources, rotate keys, and inspect inquiry/task/email state. Email mode authorizes future fixed acknowledgements through the enabled backend delivery adapter. Never embed the intake key in a public browser form.
- **Outcomes:** actual connected-source event counts, task completion/overdue state, processing timestamps and distinct provider submission versus confirmed email delivery. Fictional records are excluded by default.
- **Workflow drafts / Automation lab:** retained generated graph review and local sandbox reminder execution. These screens do not claim to deploy arbitrary n8n graphs.

## Credentials and delivery

Use [provider setup](../backend/AGENT.md), [n8n setup](../backend/N8N.md), and [inquiry intake](../backend/INQUIRIES.md). Gemini generation defaults to `gemini-3.5-flash-lite`. Connect Gemini in the local AI Agent form or configure it privately on the backend; a local session connection also enables the backend's Gemini draft service. Live verification checks a specific read-only tool exchange, not every future answer.

Real email requires opt-in backend settings, Resend credentials, a verified sender, signed provider callbacks, a public backend URL, and a real non-demo source with recipient permission. A provider submission is not delivery. Fictional demo sources cannot send email. Do not test against real people without their permission.

The managed n8n template is bounded to inquiry follow-up. The backend rejects unsupported/changed graphs, verifies engine output and saved execution data, and creates a deduplicated task. Public inquiry intake uses its own source token rather than the operator login session. Integration belongs in your website/form's server handler; this build does not automatically modify a customer's website.

## Hosted deployment

[The deployment guide](../deploy/README.md) includes a frontend container, persistent backend storage and recovery commands. Set `BACKEND_URL` to the internal backend origin for server-to-server calls. Register an operator and configure the public backend origin/allowed hosts/private provider settings. Use HTTPS at the public edge and keep one backend worker/replica. A host without browser runtime still supports CSV import.

## Checks

`npm run typecheck` and `npm run build` check the interface. `node --test tests/*.test.mjs` checks outreach-link encoding and CSV header mapping. `tests/workspace-browser.cjs` exercises an isolated backend/frontend fixture; it requires Playwright and a browser. This is separate from real provider verification. Test records must not be added to your live `.local` database.
