# Client workspace — v0.10.0

The browser now connects the existing client, task and monitoring APIs. No new
provider or credentials are required for the sandbox demo. All API values are
rendered as text. Client handoff downloads use authenticated requests and exclude
provider keys and the shared token.
The [CRM redesign](CRM_DESIGN.md) uses HubSpot as its UI reference, adds local
saved-record search and lead views, and retains the controls described below.

## Complete the demo in the browser

1. Start/unlock the workspace as described in the repository README. Open
   **Clients**, then **Create fictional client example**. The business and its
   reminder evidence are clearly marked fictional; real leads are unchanged.
2. Choose the fictional business in **Onboard a client**. Enter a fictional contact,
   IANA timezone such as Asia/Karachi, and a fictional authorization reference.
   Check the authorization statement and create its profile.
3. Create a **sandbox setup** using that client's reminder workflow. Validation
   lists missing checks. A client awaiting authorization review cannot activate
   a setup. Review the profile, check its confirmation and activate the client.
4. Use **Open sandbox lab for a proof**. It selects the correct workflow in
   standalone sandbox mode. Enter a future appointment and an earlier reminder
   time, check both confirmations, and schedule the reminder. After the due time,
   refresh history and inspect the succeeded run and **unsent** preview.
5. Return to **Clients**, validate the setup, review its saved checks and explicitly
   confirm activation. **Check readiness** retrieves current checks; saved
   validation has its own timestamp and can become stale.
6. **Schedule client reminder** opens the lab with that deployment selected and
   its workflow fixed. These reminders use the managed endpoint and inherit its
   client/pause/validation guards. Schedule one later in the future, pause the
   setup or client, then refresh history to inspect the stopped run.
7. Download the **client handoff** and view its timestamped client history. This
   artifact describes a local setup; it does not publish a server or create client
   login accounts. Already submitted messages cannot be recalled.

The browser creates/activates sandbox setups only. Existing email deployments can
be inspected and paused, but the browser has no live-send control. Live provider
verification and public hosting remain outstanding. Existing API contracts in
[MVP.md](MVP.md) are preserved.

## Tasks, contact history and operations

**Follow-up tasks** lets you choose a business, record a title/notes/due time, and
complete or cancel its manual task. Saving a task never contacts a business.
Past due times represent overdue work. Do-not-contact businesses are excluded
from new-task selection. Existing task/history records remain readable.

Open a lead to see **Contact activity**, including recorded stage/task history
and current call/run summaries. These records do not establish delivery or an
internal operational need. Evidence remains in the separate analysis flow.

**Operations** shows active client/setup/run counts, scheduler state and saved
issues/overdue work. It excludes fictional records by default. The **Include
fictional demo records** control explicitly enables them. Completing an overdue
task removes its alert on refresh. An empty issue list does not prove provider
connectivity or delivery. Recorded call outcomes describe the sales-agent leg.
Active setups are also checked against current client/workflow readiness and their
saved validation fingerprints. A blocked or stale setup appears even before a new
run is scheduled; **Review client setup** opens Clients. Pause it, resolve its
failed checks, then explicitly validate and activate again. Refresh does not
reactivate a client or setup.

## Guards and verification

Lock/reload clears the shared token from tab memory and clears client/task data.
An in-flight response from a previous access session cannot repopulate locked data.
Mutation inputs are checked against current workspace state; API authorization and
workflow guards remain authoritative. Failed-response retries keep stable event
keys and visible pending inputs, including a task accepted before a connection loss.
Read-only handoff downloads never submit provider actions.

The new client/task/operations views require SQLite capabilities. On Supabase,
they show an explicit unsupported-storage message while research stays usable.
This remains one worker/replica with shared access; new data is not automatically
migrated and no individual accounts or native calendar availability are provided.

Current results and retained screenshots are recorded in
[VERIFICATION.md](VERIFICATION.md). All development browser fixtures are fictional,
and no business was contacted or live email sent.
