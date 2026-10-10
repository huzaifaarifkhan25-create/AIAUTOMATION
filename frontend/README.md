# New AIAutomation workspace

This is an additive Next.js interface. The original FastAPI workspace remains at `/app/`. It uses the same saved businesses, evidence, tasks, discovery jobs and sandbox workflows. Its purple dashboard is styled from the owner's supplied reference, with AIAutomation branding and real backend values.

**Use port 3000 for this design.** `http://127.0.0.1:8000/app/` is the older fallback CRM; `http://127.0.0.1:3000/workflows` is the new workflow screen. Mock/demo workflows are hidden in the new workspace until **Show demos** is selected. Motion is subtle and respects reduced-motion preferences.

## Run locally

1. Start the existing FastAPI app on `http://127.0.0.1:8000` with `APP_API_TOKEN` set to a private shared value. Keep one worker.
2. In a separate shell, set `BACKEND_URL=http://127.0.0.1:8000`, the same `APP_API_TOKEN`, a private `DEMO_ACCESS_CODE` of at least 12 characters and a private `FRONTEND_SESSION_SECRET` of at least 32 characters. Set them in the shell or host settings; this app does not load `.env.example`.
3. Run `cd frontend`, `npm install`, then `npm run dev`. Open `http://localhost:3000`.

Do not use `NEXT_PUBLIC_` for any secret. The browser receives only an HttpOnly signed demo session; the server-side route handler adds the backend bearer token. The proxy exposes only the read and draft operations used by this interface. The access gate is shared pilot access, not individual accounts or a complete public security model.

A full browser reload, typed workspace URL, or new tab clears the preview session and returns to `/login`. Navigation inside the workspace keeps the session. Use the lock button to leave without reloading.

## Hosted workflow

Vercel can host this frontend with `frontend` as its Root Directory and the four server-side environment variables above. The FastAPI backend needs a separate Python host, persistent SQLite disk, one worker/replica, `APP_ENV=production`, a strong `APP_API_TOKEN`, and explicit `APP_ALLOWED_HOSTS`. Use a backend HTTPS URL for `BACKEND_URL` in production. See [portable deployment](../deploy/README.md) for existing backend requirements. A basic Python host without the bundled browser supports CSV preview/import, not live Maps collection. Run Edge locally, download its CSV, review categories, then import into the hosted backend.

Gemini drafts require `GEMINI_API_KEY` on the **backend** only. `GEMINI_MODEL` defaults to `gemini-3.5-flash`. The Google Stitch key configures Codex design tooling separately and has no role in browser runtime. No live Gemini or Stitch operation has been verified here. Calls and email stay disabled by default.

On Windows, stop the existing port-8000 backend and run `pwsh -File START-GEMINI-BACKEND.ps1` from the repository root. It prompts for a Gemini key without echoing or saving it, then starts the local backend. Restart this script whenever the backend is stopped; refresh the workspace to update AI availability. The key shown earlier for Stitch was not installed as a Gemini credential.

## Limits

AI insights have their own labelled estimate and never change evidence scoring. Workflow graphs are generated JSON, not external automation execution. Automation lab uses synthetic sandbox events and unsent previews. Review business category, provenance and contact permission before any real outreach. Public hosting, individual accounts, provider verification and hosted browser isolation remain separate work.
