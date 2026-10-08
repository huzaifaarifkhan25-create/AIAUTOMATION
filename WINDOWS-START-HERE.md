# Open AIAUTOMATION on your Windows laptop

These steps run the actual CRM and backend on your laptop. You need Windows,
Python 3.12 and an internet connection for the first dependency installation.
Opening the CRM requires no Node.js, Docker or paid provider account.

1. Download the project ZIP from this GitHub branch: use **Code → Download ZIP**.
2. Right-click the downloaded ZIP, select **Extract All**, and open the extracted
   project folder. Do not run the app from inside the ZIP.
3. Install [Python 3.12 for Windows](https://www.python.org/downloads/release/python-31210/).
   Choose **Windows installer (64-bit)** for a usual Intel/AMD laptop. Include the
   Python launcher (`py`) and pip; the standard installer includes them.
4. Double-click **START-WINDOWS.bat**. The first launch installs dependencies;
   subsequent launches check the same pinned dependencies. Keep this window open.
5. Wait for **Application startup complete**. On this same laptop, type
   `http://127.0.0.1:8000/app/` in your browser's address bar.

This address works on your laptop after you start its local app. It is not a
public link to the cloud workspace. Stop the app with **Ctrl+C** in its window.
Run **START-WINDOWS.bat** again to reopen it; your local records are retained.

## First test: see the CRM and an explicitly fictional example

The download has no database, credentials or copied cloud leads. Your first
launch therefore shows an empty CRM. An empty workspace is expected.

1. Open **Automation lab** in the navigation.
2. Click **Create fictional reminder demo**. This enables the demo filter and
   creates a clearly labeled fictional business and reminder workflow.
3. Open **Overview**, then **Leads & research**. Find the demo business, search
   its name, open its details and try the lead views and sorting.
4. Open **Follow-up tasks**. Choose that demo business, enter a task and save it.
   Find the saved task and mark it complete.
5. Return to **Automation lab**. Enter a future appointment and an earlier
   reminder time that is still in the future. Check the required confirmations,
   schedule the reminder and refresh its history after the reminder is due.
   Expect a succeeded sandbox run and an **unsent preview**; no message is sent.
6. Stop and restart the app. Confirm your demo lead and task remain saved. Enable
   **Include fictional demo records/leads** again when needed; demos are hidden
   by default after a reload.

The other controls for clients, tasks and monitoring are described in
[the workspace walkthrough](backend/WORKSPACE.md). Real data can be imported
through **Discover & import** with CSV preview before saving.

## Troubleshooting

- **Python is missing:** finish the Python 3.12 installation with the launcher
  enabled, then run the batch file again.
- **Setup fails:** read the error in the window. Dependency installation needs
  internet access. Send the error text for help, keeping any credentials private.
- **Browser cannot connect:** wait for startup to complete and keep the app window
  open. If another copy is using port 8000, close it before starting this one.
- **Demo disappeared:** enable the fictional-data filter; your saved records are
  still in `.local/backend.sqlite3`.
- **Real collection is unavailable:** Maps collection requires the separate
  Docker/browser setup in [SCRAPING.md](backend/SCRAPING.md). CSV imports and the
  CRM do not need Docker.

Calls and email are disabled by default. This local walkthrough exercises the
sandbox; live providers, public hosting, native n8n and individual user accounts
remain separate features or setup steps. See [HANDOFF.md](backend/HANDOFF.md).

The cross-platform backend and CRM were previously verified in the cloud. Windows
dependency downloads for Python 3.12 (64-bit Windows) were checked successfully;
the batch launcher has not been
executed on a physical Windows laptop here.
