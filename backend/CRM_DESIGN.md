# CRM workspace design — v0.10.0

HubSpot is the selected UI reference. Its record-oriented workspace fits our
existing business records, qualification, tasks, contact activity and client setup.
The interface keeps the AIAutomation identity and uses a dark navigation rail,
coral primary actions, teal record links, compact tables and a record detail panel.
This redesign does not connect the app to HubSpot or GoHighLevel.

## Connected controls

- **Overview:** saved lead/qualification/workflow counts, prospect queue and the
  next three recorded pending follow-up tasks. Empty tasks and zero confirmed needs
  remain explicit; no sales/revenue figures are invented.
- **Search your CRM:** find saved businesses by name, address or phone using the
  authenticated loaded data. It respects the demo toggle. Arrow keys navigate
  results, Enter opens a record, Escape clears the search. Lock/reload clears
  the query/results and disables search until the workspace loads again.
- **Leads & research:** All leads, Ready for review, Confirmed needs and Do not
  contact views share the existing filter state. Sort by review priority, business
  name or prospect score. Search/filter/view changes do not alter saved evidence.
- **Record details:** inspect source, dates, unknowns and recorded activity, update
  evidence/contact stage, and create supported drafts through the existing API.
- **Clients, tasks, automation and operations:** the same backend controls and
  confirmation/opt-out/proof/cancellation guards, styled consistently with the CRM.

On small screens navigation scrolls horizontally and wide record tables scroll
within their cards. Record details use a full-width panel. Assets are local;
there is no new frontend service, package, third-party script or font dependency.

All API values still use `textContent`. Authentication remains a shared token
kept only in tab memory, with session guards for delayed responses. Demos remain
excluded by default. Public readiness and confirmed internal need stay separate.
Provider credentials, public hosting and native n8n integration remain the
requirements described in [HANDOFF.md](HANDOFF.md).

Current verification and screenshots are in [VERIFICATION.md](VERIFICATION.md).
