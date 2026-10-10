# Windows live integration check — 2026-10-09

This check used public read-only requests and isolated fictional test records. It
did not import a live listing, send an email, or place a call. The primary SQLite
database was not used for fixture writes.

| Integration | Live observation | Actual app capability on this laptop |
|---|---|---|
| Google Maps | HTTPS preflight returned 200. Visible Edge loaded two searches with seven listing links each. The first query returned a **massage spa**, showing why category review matters; one initial listing-heading wait timed out, then a retry loaded. A more specific “medical spas in New York NY” query returned an HTTP 200 **medical spa** listing with matching name, address, and website. | The pinned Docker collector image is absent. Docker Desktop initially left only about 153 MB free on C:. Later, free space rose to about 3.2 GB, so an exact pinned-image pull was attempted. It transferred no visible layers and made the daemon unresponsive; the pull was interrupted. The app collector was not run and no live record was imported. |
| Public website fetch | The real `Gateway.analyze_website` fetched `https://example.com/` through HTTPS with public-host validation and returned a title. | The app supports allowed-host fetching. Individual business sites still require their own live checks and allowlist entries. |
| OpenAI-compatible summary | The public API endpoint returned 401 without a key, confirming reachability only. | `LLM_API_KEY` is absent; no live summary request was made. Structured-response and safety behavior passed simulated integration tests. |
| Resend email | The public API endpoint returned 401 without a key, confirming reachability only. | Email is disabled; API key, verified sender, webhook secret, and public HTTPS origin are absent. No message was submitted. Guard, idempotency, callback, and reconciliation tests use fictional data and simulated responses. |
| Twilio human call | The public API endpoint returned 401 without credentials, confirming reachability only. | Calling is disabled; account, auth token, caller number, sales-agent number, and public callback origin are absent. No call was placed. Confirmation, opt-out, idempotency, and callback tests use fictional data and simulated responses. |

The Windows Docker collector source now creates its output home without invoking
Linux NSS `certutil` on the Windows host and omits Unix UID flags on Windows.
Linux/container behavior, managed proxy routing, and TLS verification remain in
place. Windows-specific fixture tests passed; an actual pinned-image run remains
unverified on this laptop until Docker can pull and run the image. No global
Docker cleanup or data pruning was performed.

To complete real provider verification, configure credentials in private runtime
settings, a verified sender/caller, an actual public HTTPS callback origin, and
consenting test recipient/phone numbers. Use an isolated database and explicit
confirmation. Provider acceptance alone does not prove email delivery, and a
Twilio sales-agent-leg result does not prove a prospect answered.
