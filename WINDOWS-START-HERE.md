# Open AIAutomation on Windows — v0.14

## First installation

1. Download the complete source ZIP and choose **Extract All**. Do not run from
   inside the ZIP. Keep the project in a folder you can write to.
2. Install **Python 3.12 (64-bit)** from https://www.python.org/downloads/ and
   include the `py` launcher and pip. Install **Node.js 24 LTS** from
   https://nodejs.org. Reopen terminal windows after installation.
3. Double-click **START-APP-WINDOWS.bat**. It starts the backend and current
   purple frontend in two windows and installs their pinned dependencies.
4. Wait for backend **Application startup complete** and frontend **Ready**.
   Keep both windows open, then type **http://127.0.0.1:3000** in your browser.
5. Choose **Register**, use a password of at least 12 characters and confirm
   that accounts share one workspace. If a private `APP_API_TOKEN` is configured,
   enter it as the workspace invitation code. Registration needs no AI key.

Your account remains signed in after reload, until logout, expiration or
revocation. Operators share leads, conversations, tasks and automations; there
are no private company workspaces or roles. Password reset is not implemented.

`127.0.0.1` and `localhost` mean this laptop. These addresses work only after
starting its servers. Backend port is **8000**; current UI port is **3000**;
optional local n8n port is **5678**. The older **START-WINDOWS.bat** starts only
the backend and its `/app/` shared-token fallback, not the purple account UI.

## Keep your records when upgrading

Stop both old servers with Ctrl+C. Extract the new ZIP into a separate folder.
Copy the **entire `.local` folder** from the old installation to the new one,
and separately copy your private root `.env` and any `frontend/.env.local`.
Keep the original folder as a recovery copy. Never copy an empty download over
`.local`. The ZIP contains source only, so a genuinely new installation is empty.

Use the new folder's START-APP-WINDOWS.bat. It creates its own Python environment
and installs the locked frontend dependencies. Browser refresh **Ctrl+F5** loads
current code. An old static-folder-only logo update is insufficient for this
release: it adds backend, frontend, accounts and execution files.

## First safe demonstration

1. In **Discover**, preview your CSV, map business name and address, review the
   category/source and import. Failed live collection never supplies mock leads.
2. In **Tasks**, create a follow-up task, then complete or cancel it. These are
   manual work records, not proof of customer contact.
3. Open **AI Agent**. Without Gemini it should explain that setup is needed.
   Connect a fresh key privately and click **Verify AI Agent** before using it.
4. For native execution, install/start optional n8n as below, connect it under
   **Automations**, and create the explicitly fictional inquiry demo. Review
   and deploy it. Process a future-dated permitted inquiry; inspect the actual
   n8n execution reference and task. The acknowledgement is unsent.
5. Under **Inquiries**, enable the demo filter and create a task-only source for
   that demo deployment. Your form server can submit to its authenticated
   endpoint. **Outcomes** shows recorded events; demos are excluded by default.
6. Pause the source and native deployment when finished. Check that existing
   tasks persist after restarting the app. No demonstration step sends email.

For an actual business, record only true business-confirmed inquiry evidence.
Do not fabricate confirmation to unlock deployment. The existing sandbox reminder
lab and old client/operations screens remain available alongside native n8n.

## Private keys

To save Gemini once, double-click **SETUP-GEMINI-WINDOWS.bat**, paste a fresh API
key into its hidden prompt and press Enter. The helper saves it in this project's
ignored root `.env`, preserves non-AI settings and sets Gemini provider/model
values. Stop the existing backend with Ctrl+C and restart it once. Subsequent
starts load the key automatically; you do not need to reconnect on every restart.
The key is not included in GitHub or the ZIP. This is a local plaintext settings
file, so keep it private and copy it separately when upgrading. Saving does not
verify the key; use **AI Agent → Verify live AI** after startup.

Follow [CREDENTIALS-SETUP.md](docs/CREDENTIALS-SETUP.md) for Gemini, n8n and
Resend. Never paste API keys into chat. To retain settings after restart, copy
root `.env.example` to root **`.env`** (not `.env.txt`), edit it privately and
restart the backend. START-WINDOWS.bat loads this file explicitly. Provider keys
belong in that backend file, never `frontend/.env.local` or `NEXT_PUBLIC_*`.
The supplied defaults are local development settings, not production settings.

For a session-only key, sign in and use **AI Agent → Connect AI** or the local
n8n connection form. These loopback forms keep keys in server memory and require
reconnection after restart. The n8n account itself persists separately.

If an old key/model remains active, close the backend and remove stale
`GEMINI_API_KEY` / `LLM_*` overrides from the environment used to launch it.
Existing process environment variables take precedence over the `.env` file.

## Optional local n8n and real Maps collector

Native n8n needs **Docker Desktop**, running Linux containers. After installation,
run **START-N8N-WINDOWS.bat**, open **http://127.0.0.1:5678**, create its owner,
and use **Settings → n8n API → Create API key**. Enter that key privately in
AIAutomation's local n8n connection form with base URL `http://127.0.0.1:5678`.
No n8n Cloud subscription is required. Keep its data volume when updating.

Maps collection is separate and does not need n8n. After installing Node.js and
Microsoft Edge, run **SETUP-WINDOWS-COLLECTOR.bat** and restart the backend. The
example config uses `BROWSER_RUNTIME=local`. Start a 1–10-listing pilot, inspect
its saved CSV/source preview and explicitly import relevant results. Browser
readiness is not proof that a Google Maps search succeeded. CSV import works
without Edge or Docker. No new live Maps collection was run for this release.

## Troubleshooting

- **Python/Node missing:** finish the installations and reopen the launcher.
- **Cannot connect:** wait for both servers. Read the terminal error; another
  process may already use port 8000 or 3000. Stop only your old app instance.
- **Invalid APP_ENV or storage settings:** compare your private `.env` to the
  new `.env.example`; do not leave enum/path/model settings blank. Preserve keys.
- **Gemini quota/model/key error:** choose a model available to your AI Studio
  project and repeat the real verification. A successful sign-in does not enable AI.
- **Collector not configured:** use CSV or install the optional local collector;
  this message does not mean your imported data is fake.
- **Demo records hidden:** enable the fictional/demo filter for that screen.
- **Lost source key:** rotate it under Inquiries and update the sending server.
- **Uncertain execution/email:** inspect its recorded engine/provider result;
  do not repeatedly submit new events to force it through.

The launchers are source-reviewed. Linux HTTP, browser and backup checks do not
establish that these batch files were executed on a physical Windows laptop.
Live Gemini, email and public hosting need separate checks on your installation.
