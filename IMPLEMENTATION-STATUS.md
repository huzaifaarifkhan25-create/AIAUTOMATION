# AIAutomation implementation status

For the current phase-by-phase assessment and fresh test results, read [PROJECT-COMPLETION-REPORT.md](PROJECT-COMPLETION-REPORT.md).

Updated 2026-10-09 against [CODEX-INSTRUCTIONS.md](CODEX-INSTRUCTIONS.md).

## Open the correct interface

The screenshot at `http://127.0.0.1:8000/app/#workflows` shows the **original FastAPI CRM**. It is retained as a fallback. The new purple Next.js workspace is at **[http://127.0.0.1:3000](http://127.0.0.1:3000)**; its workflow page is **[http://127.0.0.1:3000/workflows](http://127.0.0.1:3000/workflows)**. The local preview code is supplied when the frontend is started. Port 3000 needs both the frontend and the port-8000 backend running.

## Completed

| Instruction phase | What is implemented and verified |
|---|---|
| 0 — Orientation | Existing FastAPI, SQLite, Maps pilot, CSV import, `/app/`, research, tasks, clients and sandbox contracts were reviewed and preserved. Baseline: 182 Python tests. This checkout has no `.git`, so a feature branch could not be created here. |
| 1 — Gemini layer | Authenticated analysis, pitch, call-script and chat routes; bounded provider calls, validated JSON, do-not-contact guard, fixed read-only chat tools, explicit action proposals, separate AI insight provenance and scores. Eight new isolated tests passed. No real Gemini request was made because `GEMINI_API_KEY` is absent. |
| 2 — Hosted CSV path | CSV preview → explicit import → saved records, duplicate skipping and invalid-row reporting passed an isolated end-to-end HTTP smoke. Live hosted Maps collection is not claimed. |
| 3 — New frontend | Next.js/TypeScript/React Flow workspace with access gate, server-side backend proxy, dashboard, Discover/CSV, leads and evidence, tasks, AI panels/chat, workflow graph and sandbox lab. The dark rail, indigo sidebar, purple highlight cards and timeline use the supplied dashboard screenshot as visual direction. Responsive styles, subtle motion, loading states and reduced-motion support are included. The original `/app/` remains. |
| 6 — Documentation | `.env.example`, [frontend setup](frontend/README.md), [Stitch setup](docs/STITCH-SETUP.md), `AGENTS.md`, `README.md` and [verification history](backend/VERIFICATION.md) were updated. |

The final backend suite passed **190 Python tests** before this frontend-only polish. The Next.js production build and isolated access/proxy/CSV smoke passed afterward. Read-only headless checks of the new desktop dashboard, desktop workflow page and mobile workflow page found no JavaScript page errors or mobile horizontal overflow. No business was contacted, and no manual Edge click-through of all controls was performed in this pass.

## Current saved data

The local backend currently reports **five CSV businesses and one fictional demo business**. The CSV listings need category review: prior previews include massage/spa listings, which must not be presented as verified medical spas. There are **zero review-ready real prospects** and **no real-business workflow drafts**. Three saved workflows belong to the fictional demo; the new UI hides them by default and offers an explicit **Show demos** control. AI estimates do not affect evidence-based ranking.

## Remaining from the instructions

1. **Private keys and live checks:** rotate the Stitch key exposed in the screenshot, set the replacement privately as `STITCH_API_KEY`, restart Codex and verify the MCP connection. Set `GEMINI_API_KEY` privately on the backend and run one synthetic, non-contact live request. Google [Stitch MCP](https://docs.cloud.google.com/mcp/supported-products) is design tooling; the [Gemini API](https://ai.google.dev/api/generate-content) powers app drafts. Neither live connection is verified here.
2. **Demo data:** a human must review categories and import 10–15 relevant med spas. Then save supported analyses, prepare 3–4 AI drafts and explicitly create the fictional sandbox reminder demo. The current massage/spa rows are not a ready med-spa cohort.
3. **Hosting:** connect a Vercel account for `frontend/` and a Python host with persistent SQLite storage, one worker/replica and HTTPS. No public deployment or public link exists yet. A basic hosted Python runtime without the bundled browser should use local collection → CSV export → hosted import.
4. **Production safeguards:** individual accounts/roles, ingress throttling, browser isolation and a public-hosting security review remain. Email and calls stay disabled without separate consented provider verification. Native n8n, calendar availability and arbitrary external workflow execution are not implemented.
5. **UI acceptance:** the new desktop/mobile pages have a read-only visual check and build/smoke verification. A full manual control walkthrough and owner review of the visual design remain. The screenshot containing a secret was deliberately not saved as an auth reference.

The next meaningful product step is **human category review of real med-spa leads**, followed by supported public analysis. A workflow appears for a real business only after its latest analysis supports a specific automation type; its JSON graph is a reviewed draft, not a live external execution.
