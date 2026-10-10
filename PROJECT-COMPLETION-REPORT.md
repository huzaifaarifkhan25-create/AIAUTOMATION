# AIAutomation: completed work and remaining work

Updated **2026-10-09** after reviewing [CODEX-INSTRUCTIONS.md](CODEX-INSTRUCTIONS.md), [AGENTS.md](AGENTS.md), the current source, [backend status](backend/STATUS.md), and [backend handoff](backend/HANDOFF.md). This report describes the local checkout and today's checks. Historical verification is in [backend/VERIFICATION.md](backend/VERIFICATION.md).

## What this project does

AIAutomation is a med-spa prospect research and client automation pilot. An operator collects a small sample of public listings or imports a CSV, reviews source and category, analyzes public website evidence, ranks prospects using explicit rules, prepares outreach drafts, records follow-up work, builds supported workflow JSON, and rehearses reminders in a **sandbox**. The backend also has reviewed local client activation and handoff tools. Public evidence can suggest an opportunity; it cannot confirm a business's internal problems, consent, or sales likelihood. Saving a draft or sandbox preview does not contact a business.

## Which website to open

- **New purple Next.js workspace:** <http://127.0.0.1:3000/login>. Its workflow page is <http://127.0.0.1:3000/workflows> after sign-in.
- **Original FastAPI CRM:** <http://127.0.0.1:8000/app/>. It remains the fallback and still exposes some client and operations screens not rebuilt in Next.js.
- A full reload, typed workspace URL, or new tab returns the new interface to login and clears its browser cookie. In-app navigation keeps the session. This is shared pilot access, **not individual user accounts**. The current local access code was supplied in chat; production needs private, strong environment values.

## Instruction phases: current status

| Phase in `CODEX-INSTRUCTIONS.md` | Status | Evidence and limit |
|---|---|---|
| 0. Orient and preserve | **Done locally** | Existing FastAPI/SQLite contracts, collector, CSV, research, sandbox, clients and old `/app/` were retained. This checkout has no `.git`, so no feature branch or push was possible here. |
| 1. Gemini AI layer | **Code complete; live provider unverified** | Authenticated analysis, pitch, call-script, insight-read and chat routes; Pydantic validation, bounded provider calls, fixed read-only chat tools, separate AI provenance and explicit UI confirmation of proposed writes. AI does not alter evidence scores. Mocked tests passed. `GEMINI_API_KEY` is absent locally, so no real Gemini request was run. The AI screen now explains the separate Stitch/Gemini setup; `START-GEMINI-BACKEND.ps1` prompts privately for a Gemini key. |
| 2. Hosted-style discovery/CSV | **Local path verified; host unverified** | Preview, explicit import, invalid-row reporting and duplicate skipping passed against an isolated SQLite API. The interface explains local collection plus CSV import when its browser collector is unavailable. No hosted service or new live Maps scrape was tested today. |
| 3. New Next.js interface | **Built; acceptance review remains** | Dashboard, Discover, leads/evidence, tasks, Gemini drafts/chat, React Flow workflow viewer, sandbox lab, access gate, responsive purple UI, loading/empty states, server-side backend proxy, and reduced-motion styling exist. Demo workflows are hidden by default. A production build and HTTP smoke passed. A full manual click-through of every new UI control was not run in this report. |
| 4. Deployment | **Not done** | Deployment requirements are documented, but no Vercel or Python hosting account, public HTTPS URL, persistent hosted SQLite disk, or hosted end-to-end check exists. |
| 5. Demo readiness | **Not done** | The requested 10–15 category-reviewed med spas and 3–4 real-lead AI drafts are not ready. The current five CSV businesses have not been analyzed in this local database. A fictional sandbox demo exists, but is not proof of real outreach. |
| 6. Documentation | **Done for local implementation** | README, environment examples, frontend setup, Stitch setup, architecture notes, verification history, durable instructions and this report describe setup and limits. Hosting results must be added if deployment happens. |

## Features working in code

| Area | Current behavior |
|---|---|
| Discovery | Local Edge/bundled-browser pilot supports small Google Maps samples and retains CSV/source pages; CSV import supports mapping, validation, provenance, duplicate checks and review before saving. Prior local live samples succeeded, but Maps results can be irrelevant or fail. The **Open Google Maps** link is manual inspection only. Google Places API is not needed for the demo. |
| Research and ranking | Public website fetching, dated evidence, unknowns, separate prospect/need qualification, and rule-based scores. Internal operational gaps require business confirmation. |
| Contact preparation | Outreach drafts, manual contact history/tasks, do-not-contact guards and opt-out handling. Sending and dialing remain disabled by default and were not used today. |
| Workflow and automation | Supported message workflow JSON, React Flow viewing, durable SQLite sandbox runner, unsent outbox previews, reminder history and cancellation. External arbitrary graphs, native n8n and native calendar booking are not implemented. |
| Client workspace | Existing backend and old CRM support reviewed client setup, local activation, pause/archive, operations checks and handoff. The new Next.js interface does not yet reproduce every client/operations screen. |
| Access/security | Next.js keeps the backend token on the server, uses an HttpOnly signed preview cookie, limits proxied routes/methods, checks request origin, blocks its call route, and locks on full page reload. Backend execution/contact consent guards remain. Public hosting still needs individual roles, ingress throttling and a dedicated security review. |

## Saved local data observed today

Read-only SQLite inspection returned `integrity_check=ok` and **28 logical records**: six businesses (**five CSV**, **one fictional mock**), four analyses, three workflows, ten discovery jobs (**four succeeded**, **six failed**), and one each of a contact, activity, appointment, workflow run and outbox item. **All four analyses, three workflows and the saved appointment/run/outbox item belong to the fictional demo business.** The five CSV businesses therefore have no saved local analysis or real-business workflow draft. Search results previously included `Spa`/`Massage spa` categories, so they are **not verified medical spas**. No new primary record was imported or changed by this report's checks.

## Tests run for this report

| Check | Result | Scope |
|---|---|---|
| `python -m unittest discover -s tests -q` from `backend/` | **190 tests passed** | Existing backend plus mocked Gemini/provider and isolated database behavior. The first attempt from the repository root failed at import setup (`No module named app`); rerunning from the documented `backend/` directory passed. |
| `npm run typecheck` | **Passed** | Current Next.js/TypeScript source. |
| `npm run build` | **Passed** | Optimized Next.js production build, including the reload-lock proxy. |
| `pwsh -NoProfile -File frontend/scripts/smoke.ps1` | **Passed** | Temporary SQLite API and production frontend: access, reload lock, authenticated proxy, CSV preview/import, invalid rows, duplicates and blocked call route. Fictional data only. |
| Local read-only HTTP checks | **Passed** | Port 8000 `/health`, port 3000 login/workflows, authenticated capabilities. Capabilities report SQLite and sandbox mode; Gemini, email and calls are disabled. |
| Primary SQLite read-only check | **Passed** | Integrity `ok`; record counts above. No fixture writes to the primary database. |

Earlier visible Edge fixture/control audits for the **old FastAPI UI** and read-only screenshots for the **new Next.js UI** are recorded in [backend/VERIFICATION.md](backend/VERIFICATION.md). They are not a fresh manual test of every new button. No live Gemini, Stitch, Resend, Twilio, hosted deployment, actual outreach, or new Maps collection was tested for this report.

After the report was created, the AI setup screen passed an isolated headless Edge check: no page errors or horizontal overflow, an opaque top bar, and no browser key-entry field. The updated frontend production build, TypeScript check and isolated HTTP smoke passed. The Gemini helper script parsed correctly and refused to start while port 8000 was already occupied. It has **not** been run with a real Gemini key.

## Remaining work, in useful order

1. **Review the leads.** Check each saved listing's category, source and website. Import 10–15 relevant med spas only after human review; a successful Maps job is not proof of relevance.
2. **Create real-lead research.** Fetch and review permitted public websites, save dated evidence, confirm unknowns, and inspect prospect readiness. Do not mark internal need confirmed from public pages.
3. **Enable Gemini privately if wanted.** Set `GEMINI_API_KEY` on the backend, make one synthetic non-contact live provider check, then prepare 3–4 reviewed AI drafts. The Google Stitch design-tool key is separate; the key shown in the earlier screenshot should be rotated before use. Never place either key in the repository or browser code.
4. **Complete the new UI acceptance pass.** Check every important desktop/mobile control and nested action in an isolated fixture, then have the owner approve visual design and copy. Add missing client/operations pages to Next.js only if those are needed for the new-interface demo; the old CRM already provides them.
5. **Deploy and verify separately.** Choose Vercel for `frontend/` and a Python host with HTTPS, persistent storage, one API worker and strong server-side tokens. Test hosted CSV import, restart persistence and the complete demo flow on the actual hosts. A standard Python host without a bundled browser should use local collection followed by CSV import.
6. **Plan production safeguards.** Add individual accounts/roles, ingress throttling, browser isolation, off-host backups and a security review before public customer use. Live email/calls need secure credentials, verified callbacks, explicit consent and separate isolated provider checks. Native calendar, AI calling, SMS, billing and arbitrary external workflow execution remain future integrations.

The next practical step is **category review and public analysis of real med-spa leads**. That creates meaningful prospect rankings and workflow drafts. Current sandbox success proves local recording only; it does not prove a message was delivered.
