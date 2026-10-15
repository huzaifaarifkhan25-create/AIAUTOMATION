# AIAutomation

A shared workspace for med-spa prospect research and a reviewed inquiry follow-up
automation. Find or import businesses, review evidence, prepare outreach, deploy
the supported n8n workflow, connect a form server, and track the resulting tasks
and email records. The purple Next.js interface is the primary UI; the older
FastAPI `/app/` CRM remains available.

The current implementation is **v0.14.0, 2026-10-15**. Read the
[completion report](PROJECT-COMPLETION-REPORT.md) for implemented features,
verification and remaining live-service requirements. Earlier documents describe
historical milestones; the current report and top of
[VERIFICATION.md](backend/VERIFICATION.md) take precedence.

## Start on Windows

1. Install Python 3.12 with the `py` launcher and Node.js 24 LTS.
2. Extract the whole project. When upgrading, follow the
   [Windows guide](WINDOWS-START-HERE.md) to preserve `.local` and private settings.
3. Double-click **START-APP-WINDOWS.bat**. Keep both terminal windows open.
4. After both servers start, open `http://127.0.0.1:3000` on that laptop and
   choose **Register**. Operators have individual logins but share all records.

No paid account or provider key is needed for accounts, CSV import, evidence,
tasks or sandbox demonstrations. Live AI needs Gemini. Native execution needs
n8n; automatic email additionally needs a verified Resend sender and callbacks.
See [credential setup](docs/CREDENTIALS-SETUP.md) for the exact steps.
On Windows, **SETUP-GEMINI-WINDOWS.bat** saves Gemini once in your private local
`.env`; future backend starts reuse it. No key is embedded in the download.

## Start on Linux

From the repository root, with Python 3.12 and Node.js 24:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
.venv/bin/python -m pip check
npm ci --prefix frontend --no-audit --no-fund
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
```

In another terminal:

```bash
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

The default database is `.local/backend.sqlite3`. Keep **one backend worker and
one replica**, using SQLite for accounts and execution. The backend fallback UI
is at `http://127.0.0.1:8000/app/`; that older screen retains shared-token access.
These are local addresses, not a public deployment.

To configure persistent local keys, copy `.env.example` to root `.env`, edit it
privately and start uvicorn with `--env-file .env`. The Windows backend launcher
does this automatically when `.env` exists. Provider values never belong in
`frontend/` or in Git. Root `.env.example` has local defaults; production uses
the separate [deployment configuration](deploy/PRODUCTION.md).

## Main flow

1. **Discover:** preview a CSV or a configured small browser pilot, review its
   categories and sources, then explicitly import. Failed real collection does
   not substitute demo leads. Maps can return irrelevant businesses.
2. **Research:** retain dated evidence and unknowns. Public fit and confirmed
   internal need are separate; a booking link alone proves neither friction
   nor manual operations. Scores are explicit rules, not sales probabilities.
3. **Prepare:** create tasks and unsent outreach, or use **AI Agent** to inspect
   saved records and propose supported actions. Review each proposed write.
4. **Automate:** obtain actual business confirmation, generate the current
   inquiry-follow-up workflow and deploy the fixed **Webhook → Set → Respond**
   n8n template. Verified execution creates a CRM task; this graph does not send.
5. **Connect intake:** activate a reviewed source under **Inquiries**. Your form's
   server submits permitted operational inquiries with its private source key.
   Task-only mode sends nothing. Explicit email mode uses the separate guarded
   Resend runner for the fixed acknowledgement.
6. **Measure:** inspect inquiry states, actual n8n execution references, task
   completion and confirmed email delivery under **Outcomes**. No estimated
   revenue, bookings or time savings are presented as measured results.

The supported native graph is fixed. Arbitrary n8n workflows, calendars, SMS,
AI calling, billing, private company tenants, roles and password recovery are
outside this build. The Agent has 34 fixed tools and cannot approve itself,
run arbitrary code or autonomously send live email. See
[Agent behavior](backend/AGENT.md), [accounts](backend/ACCOUNTS.md),
[n8n](backend/N8N.md) and [intake/outcomes](backend/INQUIRIES.md).

## Verify

```bash
cd backend
../.venv/bin/python -m unittest discover -s tests -v
cd ../frontend
node --test tests/*.test.mjs
npm run typecheck
npm run build
```

[VERIFICATION.md](backend/VERIFICATION.md) distinguishes isolated/provider-mocked
tests from actual local n8n and browser checks. Live Gemini, Resend delivery,
public HTTPS deployment and physical Windows launcher execution still require
their own checks on the configured installation.

## Deploy and recover

[Production deployment](deploy/PRODUCTION.md) supplies a current frontend/API/
Caddy Compose stack, optional n8n, persistent volumes and scheduled backup
instructions. [Local startup](deploy/LOCAL-RUN.md) covers Windows and private
environment values. The SQLite backup helper restores into a **new** directory
and revokes recovered sessions. Keep private off-host copies and back up n8n
separately; never delete data volumes while updating.

GitHub source and ZIP downloads contain no database, imported leads, credentials
or installed dependencies. A fresh installation starts empty. Optional Google
Stitch is design tooling, separate from the app's AI key; see
[Stitch setup](docs/STITCH-SETUP.md).
