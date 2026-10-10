# Outreach drafts: Level 0 audit and Level 1 handoff

Date: 2026-10-09. Scope: `CALLER-EMAIL-INSTRUCTIONS.md` Levels 0 and 1 only.

## Level 0 gaps found before implementation

- The pitch and call-script API routes existed, but needed a saved analysis, accepted no sender/language input, and returned small unstructured drafts.
- The lead detail page showed raw JSON and disabled generation without an analysis. It had no copy, text download, `mailto:`, `tel:`, or manual contact-log flow.
- The rule-based outreach route existed, but the UI had no fallback when Gemini was absent or rejected a request.
- Resend email and Twilio human calling were guarded backend integrations. The Next.js proxy blocked the call route. Neither provider was enabled or verified for live operation.

## Level 1 implemented

- Email and call-script schemas validate language, sender fields, short content, and required sections. Gemini JSON gets one validation retry. Personalization citations must exactly match saved listing/analysis facts and dates; unmatched facts cause a safe rule-based email fallback. No-analysis drafts are generic and say internal processes are unknown.
- Drafts save to `ai_insights` with input hash, model/origin, timestamp, `status=draft`, `sent=false`, analysis ID when available, and DEMO label for mock records. Do-not-contact and archived records are blocked before generation.
- The lead detail page has separate email and call panels, English/Urdu/Roman Urdu, sender input, Generate/Regenerate, copy, `.txt` download, encoded `mailto:`, validated public `tel:`, sources/unknowns, and a manual activity form that requires the operator to confirm they actually used their own tool. Opening a link records nothing automatically. Activities do not create scoring evidence or prove delivery.
- The Next.js proxy allows only the existing manual activities POST route for contact logging. Provider send and call routes remain unexposed.
- `.env.example` keeps only variable names. Sender details are request input. The Gemini key is held in the local backend process environment by `START-GEMINI-BACKEND.ps1`, not saved in source or browser storage.

## Current limits and owner actions

- The supplied key was loaded for a synthetic read-only request. Google returned HTTP 403: this key or project lacks Gemini access. A key being present does **not** prove provider operation. Email therefore uses the unsent rule fallback; AI call scripts cannot run with this key. Check the key/project in Google AI Studio, create a fresh Gemini API auth key with access if needed, and enter it at the helper's hidden prompt after restarting the backend. Because the key was shared in chat, rotate it.
- The five real saved CSV listings have massage/spa categories and no saved real analysis. None has been confirmed as a medical spa. The requested 3–4 real, category-reviewed AI drafts were **not** created; doing so would misrepresent the records and send real business data to a provider. Identify reviewed med-spa leads before that acceptance check.
- Human review is still required. Validation checks structure, known citations and selected safety properties; it cannot prove every sentence is true or that contact is lawful. No email or call was sent, and no real business was contacted in verification.
- Levels 2 and 3 have not been started. Resend sending, Twilio dialing, live delivery/call checks, and public callback setup need the owner's separate confirmation.
