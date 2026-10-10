# CRM workspace design — v0.10.0

## Calm Studio refinement — 2026-10-09

The current UI uses warm white surfaces, soft slate navigation, coral actions
and teal links. Atomic CRM is the selected GitHub reference because it focuses
on lead/contact records, stages, tasks, notes and activity history. We use its
record-first flow as a design guide while keeping this app's med-spa research,
qualification and consent controls. The navigation is shorter and avoids a
second scrollbar at desktop sizes. Discover & import explains Collect → Preview
→ Import, separates automated collection from manual Google Maps search and CSV.
The design remains original HTML/CSS/JavaScript and keeps the existing API,
keyboard navigation, mobile Sections menu, safe text rendering and AIAutomation
branding. No React frontend or repository components were added. References:
[Atomic CRM on GitHub](https://github.com/marmelab/atomic-crm) and
[Twenty CRM](https://github.com/twentyhq/twenty).

Motion stays brief and limited to page changes, notices, hover feedback and
busy indicators. It runs only when the browser does not request reduced motion;
there is no animated background or decorative glow.

## Tabler-inspired visual pass — 2026-10-09

The record structure remains HubSpot-inspired. The latest visual pass uses the
spacing, clear card boundaries, table density and responsive admin patterns of
[Tabler](https://github.com/tabler/tabler) as a reference. It uses our own CSS,
markup, coral/navy A identity and backend controls; no Tabler package, chart,
frontend runtime or copied component was added. The palette, type hierarchy,
navigation targets, cards, tables, forms and empty states were adjusted together.
On phones the Sections menu is the main navigation; it replaces the crowded
horizontal strip. Lead-row controls now have at least 38 px height.

Visible Edge fixture flows passed 15 research, five Automation lab and nine
client/task/operations checks. An 18-screen desktop/phone visual sweep found no
JavaScript errors, broken images or document overflow. A focused retest measured
lead-row buttons at 38–41 px at both widths. See
[VERIFICATION.md](VERIFICATION.md) and
[LIVE_INTEGRATION_CHECKS.md](LIVE_INTEGRATION_CHECKS.md).

HubSpot is the selected UI reference. Its record-oriented workspace fits our
existing business records, qualification, tasks, contact activity and client setup.
The interface keeps the AIAutomation identity and uses a dark navigation rail,
coral primary actions, teal record links, compact tables and a record detail panel.
This redesign does not connect the app to HubSpot or GoHighLevel.

The user supplied the interwoven A/network symbol in coral/navy and monochrome
navy. Transparent PNG assets prepared from those references replace the old
letter tile and favicon. Use the color symbol on a light tile in the dark sidebar
and the navy symbol on the light shared-access card. Retain the text wordmark,
decorative-image accessibility, and local same-origin assets.

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

On small screens a Sections menu exposes all nine destinations, and wide record
tables scroll within their cards.
Record details use a full-width panel. Assets are local;
there is no new frontend service, package, third-party script or font dependency.

All API values still use `textContent`. Authentication remains a shared token
kept only in tab memory, with session guards for delayed responses. Demos remain
excluded by default. Public readiness and confirmed internal need stay separate.
Provider credentials, public hosting and native n8n integration remain the
requirements described in [HANDOFF.md](HANDOFF.md).

Current verification and screenshots are in [VERIFICATION.md](VERIFICATION.md).

## Readability and mobile polish — 2026-10-09

The existing CRM layout now uses a restrained coral/teal glow for active controls,
slightly larger labels and form text, and softer card and background lighting.
Wide tables show swipe cues. The Automation lab's required
consent checkboxes sit beside their labels, and the mobile Lock/refresh controls
have 40 px touch targets. These are presentation and usability changes; workflow,
permission, and delivery behavior are unchanged.

The visible-browser pass added a compact Overview header, a consistent set of
local line icons, gentler card surfaces, larger secondary touch targets and
loading feedback on busy actions. Page entrance motion is brief and disabled by
the operating system's reduced-motion preference. No external font or image
service was introduced.

The latest control pass improved secondary text and form readability, added clearer
spacing in nested client setup panels, and corrected the mobile lead dialog's
viewport fit. Changing sections from a lead detail now closes that dialog so it
cannot block the destination. The mobile Sections menu shows the current section
and closes on selection, Escape or outside click. See
[UI_CONTROL_AUDIT.md](UI_CONTROL_AUDIT.md) for the visible Edge control matrix.
