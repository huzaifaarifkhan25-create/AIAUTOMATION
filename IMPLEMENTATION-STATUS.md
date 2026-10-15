# Implementation status — v0.14.0, 2026-10-15

The authoritative current assessment is
[PROJECT-COMPLETION-REPORT.md](PROJECT-COMPLETION-REPORT.md); exact checks and
limits are at the top of [backend/VERIFICATION.md](backend/VERIFICATION.md).

The seven authorized areas are implemented: shared-workspace accounts, a fixed
native n8n workflow, reviewed AI Agent actions and verification, authenticated
inquiry intake, guarded Resend acknowledgement delivery, measured outcomes, and
persistent deployment/backup tooling. This is a scoped pilot, not unrestricted
automation or separate company accounts.

Use **START-APP-WINDOWS.bat** for the purple account-enabled UI on port 3000.
The old port-8000 `/app/` remains a shared-token fallback. Account sessions survive
reload; only the optional legacy preview access still locks on reload.

Actual local n8n execution and browser flows were checked with isolated fictional
data. Live Gemini and Resend, public HTTPS hosting and physical Windows launcher
execution are not established by those checks. Supply private credentials using
[the setup guide](docs/CREDENTIALS-SETUP.md), then verify the actual installation.
No real business was contacted during this build.
