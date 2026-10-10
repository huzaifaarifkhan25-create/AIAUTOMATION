# Current architecture for the new workspace

1. FastAPI remains the backend and serves the original `/app/` CRM.
2. SQLite holds local businesses, analyses, tasks, workflows, jobs and client state.
3. The local Edge or bundled Docker browser collects a bounded Maps pilot.
4. The collector saves source pages and CSV; a human previews before import.
5. CSV import validates provenance, stable identity and duplicate rows.
6. Rules-based analysis and qualification remain the only scoring evidence.
7. New Gemini routes create separate AI insights and unsent drafts.
8. New Next.js route handlers forward authenticated calls to FastAPI.
9. The browser receives an HttpOnly demo session, never the backend bearer token.
10. Dashboard and lead pages consume `/capabilities`, `/businesses`, `/prospects`, `/analyses`, `/tasks`, `/appointments`, `/discovery/jobs`, `/workflows` and `/ai/*`.
