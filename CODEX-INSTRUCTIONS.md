# CODEX-INSTRUCTIONS.md

Hackathon project: **Med Spa AI lead-generation + cold-outreach + automation platform**.
Read this file fully, then read the repo docs listed in Phase 0, then work phase by phase.
The owner is not deeply technical. Explain decisions briefly and keep changes small and verifiable.

---

## 0. Ground rules (do not break)

1. **Preserve everything that works.** Python FastAPI backend, SQLite persistence, CSV import, Maps
   pilot collector, website analysis, scoring, outreach drafts, contact/tasks, sandbox workflow runner,
   Automation lab, clients/deployments/operations, the existing `/app/` HTML UI, and all existing API
   contracts and response shapes. Only **add** new endpoints/files. No unrelated refactors.
2. Baseline before changing anything: run the full test suite and record the result.
   `cd backend && ../.venv/bin/python -m unittest discover -s tests -v`
   (Windows: `..\.venv\Scripts\python.exe -m unittest discover -s tests -v`). It must still pass after every phase.
3. **Secrets:** never hard-code, commit, print, log, or paste any API key. Names only in `.env.example`.
   Never put a secret in a `NEXT_PUBLIC_*` variable or any browser-visible code. The app does not auto-load `.env`;
   follow the repo's existing environment-variable convention.
4. **Do not contact real businesses.** No real email, call, or message in development or tests. Email/calls stay
   disabled by default. Use synthetic data and mocked provider responses in tests.
5. **Honesty contracts from AGENTS.md stay in force:** show sources, evidence dates, unknowns, demo labels.
   Internal operational gaps are never "confirmed" without business confirmation. Public website evidence
   shows observed friction only. Maps results are not guaranteed to be med spas; a human reviews category before import.
   Never auto-import discovery results. Never fall back to mock data for real collection.
6. Keep route handlers thin; put logic in services. Single API worker; SQLite only for the new features
   (Supabase returns an explicit 503 for new APIs, like other recent APIs do).
7. Update `AGENTS.md` (durable notes) and `backend/VERIFICATION.md` honestly at the end. Do not claim anything
   was tested live unless you actually ran it.

---

## 1. Decisions already made

| Topic | Decision |
|---|---|
| Backend | Keep the existing Python FastAPI app. No rewrite. |
| Database | Keep SQLite. No Firestore migration. No Firebase (optional login gate only if time remains). |
| Frontend | Build a **new Next.js app in `frontend/`** (React Flow, chatbot). Keep the old `/app/` UI untouched as fallback. |
| AI provider | **Google Gemini API** via the owner's key. Not the existing OpenAI-compatible adapter. |
| Maps discovery | **Google Places API is NOT available**: the owner's Google Cloud billing verification failed. Do not depend on it. |
| Hosting | Frontend on Vercel. Backend on a Python host (Render/Railway/Fly). Scraping/SQLite never run on Vercel. |

### Why Vercel cannot run the Maps scraper
The collector needs a real browser (Edge on Windows, bundled browser in Docker on Linux) and a long-running process.
Vercel serverless has no persistent filesystem (SQLite would lose data) and no such browser. The app also needs one
worker with persistent disk. So Vercel = Next.js frontend only.

---

## 2. Maps discovery strategy without the Places API

Use these, in order of reliability for the demo:

1. **CSV import (already built, works everywhere, including the hosted backend).** Preview, mapping, duplicate
   skipping and provenance already exist. Leads can be exported from the local collector on the owner's laptop,
   from gosom/google-maps-scraper (MIT), or from browser extensions.
2. **Local Edge collector on the owner's Windows laptop** (`SETUP-WINDOWS-COLLECTOR.bat`, then `START-WINDOWS.bat`).
   It saves a CSV and source pages. The owner downloads the CSV (`GET /discovery/jobs/{id}/csv`) and imports it
   into the hosted app via CSV import. This is the "scrape locally, import to cloud" path.
3. **Pre-imported demo leads.** Before the demo, import 10-15 reviewed, relevant leads so nothing depends on live scraping.
4. **Optional stretch (only after everything else is done): free OpenStreetMap source** (Overpass/Nominatim)
   as `source=osm`. Verify the current usage policies and test a real query for the target city before claiming it
   works. OSM coverage of Pakistani med spas may be thin. Same rules: preview, category review, no auto-import,
   provenance retained, no mock fallback. Skip it if it threatens the schedule.

Hosted-mode behavior to verify: when the browser collector is unavailable on the hosted backend, the Discover page
must show a clear "live collection unavailable here, import a CSV or run the local collector" message, not a crash
or a silent mock result. Do not change the existing contracts to achieve this; use the existing readiness/capabilities signals.

---

## 3. Phases

### Phase 0: Orient (read-only, ~30 min)
Read: `AGENTS.md`, `README.md`, `PROJECT-EXPLAINED.md`, `WINDOWS-START-HERE.md`, `backend/STATUS.md`, `backend/API.md`,
`backend/HANDOFF.md`, `backend/MVP.md`, `backend/WORKSPACE.md`, top of `backend/VERIFICATION.md`, `backend/EXECUTION.md`.
Create a feature branch (never touch `main`). Run the baseline test suite. Write a 10-line summary of the current architecture
and the API routes the frontend will consume.

### Phase 1: Gemini AI layer (backend)

Add a small provider module + service + thin routes. New environment variables (names only):
`GEMINI_API_KEY`, `GEMINI_MODEL` (configurable; **check the official Gemini API docs for a currently available model name
and the exact REST request/response format before coding**, do not guess; the call is typically a `generateContent` request
authenticated with the key sent in a header). Add both to `.env.example`. Expose **presence only** (never the value) in
`GET /capabilities`.

Provider requirements: `httpx` (add to requirements only if not already present), explicit timeouts, bounded retries,
bounded input size, no logging of keys or full prompts containing business data, ask for JSON output and **validate it
with Pydantic**; on invalid JSON retry once, then return a clear error. App must start and all existing features must work
with no Gemini key set; AI routes then return a clear "AI not configured" error (503 or 4xx consistent with the repo).

New authenticated endpoints (all draft/read-only; nothing is sent anywhere):

1. `POST /ai/businesses/{id}/analysis`
   Input: the business listing fields + its **latest saved analysis** (existing evidence, unknowns, coverage). Do not fetch
   arbitrary new URLs here; reuse the existing website analysis flow if fresh content is needed.
   Output (validated schema), roughly:
   ```json
   {
     "summary": "...",
     "pain_points": [{"point": "...", "evidence": "...", "source": "...", "confidence": "low|medium|high"}],
     "opportunity_estimate": {"score": 0, "label": "ai_estimate", "rationale": "..."},
     "recommended_automations": [{"type": "appointment_reminders|inquiry_followup|consultation_followup|rebooking", "why": "..."}],
     "unknowns": ["..."],
     "disclaimer": "AI inference from public information; internal gaps unconfirmed"
   }
   ```
   Persist as a separate AI-insight record with provenance (`origin="ai"`, model, timestamp, input hash). **Never overwrite or
   rewrite existing analyses**, and never feed AI output into `need_score` or the prospect score. The AI score is a separate,
   labelled estimate.
2. `POST /ai/businesses/{id}/pitch`: email/pitch **draft**, discovery-style (asks about processes; does not invent problems).
   Blocked for do-not-contact leads (reuse the existing guard). No send action.
3. `POST /ai/businesses/{id}/call-script`: short cold-call script (opening, discovery questions, likely objections with
   responses, close). Same do-not-contact block. Draft only.
4. `POST /ai/chat`: chatbot with **tool calling over a fixed whitelist of read-only internal functions** (list/rank prospects,
   get lead, get qualification, get analysis, get AI insight, list tasks). Write actions (create task, run analysis, generate pitch)
   are returned as a **proposed action** that the UI must confirm through a separate confirm call; the model never writes directly.
   Reuse existing service functions; do not duplicate logic. Keep chat history bounded.

Security for AI: treat website text and CSV fields as **untrusted data** (prompt-injection risk). Put them in clearly delimited
data sections, instruct the model to ignore instructions inside them, and never let model output choose arbitrary URLs, tools
outside the whitelist, or recipients. Mark demo/fictional records clearly in outputs.

Tests: mock the Gemini HTTP response for success, invalid JSON, timeout, missing key, do-not-contact block, injection text in a
website snippet, and tool-whitelist enforcement. No live calls in the automated suite. Then one **manual** live check using the
owner's key supplied in their own environment; record the result honestly in `VERIFICATION.md`.

Acceptance: full suite still passes; new tests pass; `/openapi.json` documents the new routes; app starts without keys.

### Phase 2: Discovery/CSV hardening for hosted mode
Implement Section 2. Verify CSV import end to end on the hosted-style configuration (preview -> import -> leads visible,
duplicates skipped, invalid rows reported). Add a short in-app/README note describing "scrape locally, import CSV to hosted".
Do not touch the collector's TLS verification, restricted child-process environment, or proxy handling.

### Phase 3: Next.js frontend (`frontend/`)
Stack: Next.js (App Router), TypeScript, React Flow. Do not delete or alter `backend/app/static`.

- **Token handling:** the backend's shared `APP_API_TOKEN` and `BACKEND_URL` live in **server-side** env vars only. The browser
  talks to Next.js route handlers (`app/api/...`) that forward to the backend with the Bearer token. Never expose the token to
  client code or browser storage. Add a simple demo access gate (shared password) because the Vercel URL is public.
- **Pages:** Dashboard (`/operations/summary`, `/opportunities`), Discover (search -> job status -> preview with category column ->
  explicit Import; plus CSV upload/preview/import), Leads table (search/filter/sort, demo hidden by default), Lead detail (listing,
  evidence/unknowns/coverage, scores shown separately, AI analysis panel, pitch, call script, contact history, tasks),
  Chatbot panel, Workflow page (React Flow rendering of `medspa-workflow-v1` JSON from `GET /workflows/{id}`), Automation lab
  (sandbox reminder scheduling, history, unsent previews).
- Every page has loading, error and empty states. Render all user/provider/AI text as plain text (no raw HTML injection).
- Always label: DEMO records, "AI estimate", "unsent preview / sandbox", "unconfirmed".
- Build order for demo value: Discover/CSV import -> Leads -> Lead detail with AI analysis + pitch -> Chatbot -> React Flow -> Automation lab -> polish.
- Check `GET /capabilities` before showing features; unsupported ones must be hidden or disabled, not broken.

#### Design reference for the Next.js UI (applies to Phase 3)

The owner supplied two reference screenshots. Save them in the repo as
`docs/design-reference/ui-1-auth-mobile.png` (dark purple mobile auth screens) and
`docs/design-reference/ui-2-dashboard.png` (dark sidebar dashboard with purple cards and a calendar timeline).
Use them as a **visual style reference only**. Recreate the look with our own components, copy, logo and data.

Do NOT copy: the "Looma Wallet" name or logo, the "HR." logo, any crypto/wallet/HR content, text, or icons from the screenshots.
Use the AIAutomation logo files in `backend/app/static/brand` and the product name "AIAutomation".

Style to match (approximate; match by eye, do not trust these values as exact):
- Dark near-black navy surfaces with a deep indigo/purple gradient glow; lavender/white text; muted grey secondary text.
- Primary actions: rounded, purple gradient buttons with a soft glow (a small sparkle icon is fine for AI actions).
- Inputs: dark translucent fill, thin subtle border, large rounded corners, clear focus ring.
- Cards: large radius; the top/highlighted card uses a rich purple gradient, others are neutral.
- Dashboard shell: slim icon-only left rail (dark) + optional second panel for filters/views; light content area with
  generous spacing; search bar at the top.
- Calendar/timeline with a "now" marker line.
- Define colors, radii and spacing as CSS variables or Tailwind theme tokens in one place. Keep text contrast readable
  (check small grey text on dark backgrounds). The reference auth screens are mobile; the dashboard is desktop; make both work.

Map the references to real product screens, using only real data from the backend:
- **Auth screen (reference 1) -> Access gate page.** The backend only has a shared access token, not user accounts. Build a
  simple "Welcome" gate with one demo access-code field. Do NOT add email/password sign-up, social login buttons (Apple/Facebook/X/Google),
  6-digit code verification, "remember me" or "forgot password": those would imply accounts that do not exist.
- **Dashboard shell (reference 2) -> app layout.** Left rail icons = Dashboard, Discover, Leads, Tasks, Automation lab, Workflows, Chatbot, Settings/Connections.
  Secondary panel (the "Role" list) = lead views such as High priority, Medium, Low, Needs review, Contacted.
- **"Trending offers" cards -> Top prospects.** Highlight card = best-ranked lead with its prospect score and public-evidence coverage.
  Show real values only; no invented revenue, candidate counts or conversion numbers.
- **"Calendar preview" -> Follow-up timeline.** Show recorded follow-up tasks and sandbox appointment reminders (from `/tasks`, `/appointments`).
  Label sandbox items as "unsent preview".
- Keep the honesty labels (DEMO, AI estimate, unconfirmed, sandbox) visible and styled consistently in this theme.

Where this fits: build the shared layout and theme tokens first (before the individual pages), so every page inherits the style.
The old `/app/` UI stays unchanged.

### Phase 4: Deployment
- **Backend:** simplest non-Docker path: a Python web service on Render/Railway (the repo `Dockerfile` also works if preferred).
  Build: `pip install -r backend/requirements.txt`. Start:
  `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT --workers 1`.
  Env (names only): `APP_ENV`, `APP_API_TOKEN` (>= 32 printable chars), `APP_ALLOWED_HOSTS` (the backend hostname),
  `GEMINI_API_KEY`, `GEMINI_MODEL`, `APP_DB_PATH` (pointing at a persistent volume if the plan has one).
  Read `deploy/README.md` first: production mode requires a strong token and explicit hosts; one worker, one replica.
  Warn the owner if the chosen plan has no persistent disk or sleeps (SQLite data may be lost; re-import the demo CSV).
- **Frontend:** Vercel, Root Directory `frontend`, env `BACKEND_URL`, `APP_API_TOKEN` (server-side only), demo gate password.
- **Check CORS/proxy:** with the Next.js route-handler proxy, browser CORS is not needed; verify anyway.
- Smoke test: backend `/health` and `/ready`, then a full flow through the Vercel URL.
- **Backup demo plan:** the whole app runs on the owner's Windows laptop via `START-WINDOWS.bat`
  (`http://127.0.0.1:8000/app/`), optionally exposed with a tunnel. Note: the `.bat` launcher has not been verified on a
  physical Windows laptop in the docs; do not claim it has.

### Phase 5: Demo readiness
- Import 10-15 reviewed relevant leads via CSV (human category review; drop massage spas/tanning salons, etc.).
- Create the explicitly fictional Automation lab demo for the reminder walkthrough.
- Run AI analysis + pitch + call script on 3-4 leads ahead of time; keep results saved as fallback in case Gemini free-tier
  rate limits hit during the demo.
- 3-minute script: problem -> Discover/leads -> lead analysis with pain points, AI estimate and unknowns -> chatbot -> pitch/script ->
  React Flow workflow -> sandbox reminder with unsent preview -> roadmap and honest limits.

### Phase 6: Documentation
Update `AGENTS.md`, `README.md` (short), `.env.example`, `backend/VERIFICATION.md` with: what was added, exact tests run and results,
what was and was not tested live, and remaining limits. Keep `TEAM-INSTRUCTIONS.md` consistent if present.

---

## 4. Environment variable summary (names only)

Backend: `APP_ENV`, `APP_API_TOKEN`, `APP_ALLOWED_HOSTS`, `APP_DB_PATH`, `SCRAPE_OUTPUT_DIR`, `BROWSER_RUNTIME`,
`GEMINI_API_KEY`, `GEMINI_MODEL`, plus the existing optional ones in `.env.example`.
Frontend (server-side only): `BACKEND_URL`, `APP_API_TOKEN`, demo gate password variable.
Not used now: `GOOGLE_PLACES_API_KEY` (billing unavailable). Keep the existing adapter code untouched.

## 5. Human-only steps (ask the owner; do not attempt)
- Setting real secret values in the host dashboards (Render/Railway, Vercel) and in their own laptop shell.
- Logging into Vercel/Render/GitHub accounts and connecting the repo.
- Any live check that needs the owner's Gemini key (they run it in their own environment).
- Reviewing Maps/CSV categories before import.

## 6. Do NOT claim (in UI, README, or the demo)
- Live email or calls work (never verified).
- Native n8n execution exists (it does not; a simple webhook prototype at most, and only if built and tested).
- Every Maps/CSV result is a med spa.
- Internal needs are confirmed, or the AI score is a calibrated sales probability.
- The platform is production-ready (individual accounts, public-hosting hardening, browser isolation remain open).

## 7. Definition of done
- Existing tests plus new tests pass; old `/app/` UI still works.
- App runs with and without a Gemini key (clear error without it).
- Hosted frontend + backend demonstrate: CSV import -> lead list -> AI analysis -> pitch/script -> chatbot -> workflow graph -> sandbox reminder.
- No secret in git history, logs, client code or docs.
- Final report: what changed, what was tested (and how), what was not tested, known limits.
