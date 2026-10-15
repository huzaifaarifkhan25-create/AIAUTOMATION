# Backend status — v0.14.0, 2026-10-15

The seven authorized functional areas are integrated: shared-workspace accounts,
a fixed native n8n workflow, reviewed AI Agent tools and verification,
authenticated inquiry intake, guarded Resend delivery, measured outcomes and
persistent deployment/backup tooling. The source is on
`codex/complete-automation`; main and the former preview are preserved.

See the [current completion report](../PROJECT-COMPLETION-REPORT.md) for the
feature table and live-service prerequisites, and
[verification](VERIFICATION.md) for exact evidence. Historical v0.10 descriptions
of accounts/native execution being absent no longer describe this build.

## Supported behavior

- Prospect research keeps sources, unknowns and explicit scores. Business-confirmed
  operational need is separate from public fit. A booking link alone cannot prove
  friction. Existing imports and outreach contracts are retained.
- Individual operator accounts and conversations share one workspace. Secure
  sessions, CSRF, invitations and revocation are supported; roles, private tenants
  and password recovery are not.
- Agent has 34 fixed tools and requires separate approval of proposed writes.
  Verification checks a real read-only provider/tool roundtrip. Missing credentials
  do not produce fake responses. Live outbound send is not an Agent tool.
- Native n8n is limited to Webhook → Set → Respond. The app verifies the graph and
  saved execution before committing an idempotent task. Paused, opted-out,
  archived or stale work cannot commit a new task. Uncertain runs are not replayed.
- Inquiry sources authenticate independently with one-time hashed keys. Key
  rotation/pause and final source/recipient guards apply during concurrent work.
- Optional email uses fixed source-level authorization plus recipient permission;
  opt-outs, current evidence/sender and pause are checked before submission.
  Signed callbacks and matched read-only reconciliation establish delivery.
  An accepted intake request or provider submission is not delivered email.
- Outcomes count real saved events, exclude demos by default and separate
  provider failures from safely stopped/cancelled work.
- SQLite and exactly one worker/replica are required for accounts and execution.
  Unsupported Supabase paths return 503. Backups restore into a new directory
  and revoke recovered sessions. n8n needs a separate backup.

## Verification and limits

The final full Python suite discovered 309 tests: 307 passed and two Windows-only
checks skipped. Frontend unit, typecheck, production build, 12 browser checks,
19 account-bridge HTTP checks and 10 production standalone checks passed.
Actual local n8n execution and task creation passed using fictional isolated data.
The primary database retains the same 25 logical records and integrity `ok`.

No fresh live Gemini, Resend delivery, public HTTPS hosting, full new Docker stack
or physical Windows launcher execution was verified. These need credentials,
a chosen host or the relevant machine. The implementation does not include
arbitrary workflow editing, native calendars, billing, SMS or dialer expansion.
