# Current frontend, API and real automation deployment

The supported pilot is **one shared workspace, one API worker, one server**.
Accounts identify individual operators; they do not separate company data or
provide owner/admin roles. A public host/domain has not been provisioned by this
repository. This guide provides the concrete server configuration.

## Choose the server and domains

Use an x86-64 Linux container server with Docker Compose v2, persistent disk,
outbound HTTPS, and public ports 80/443. A starting budget for the bundled browser,
Next.js and optional n8n is 4 CPUs, 8 GB RAM and at least 30 GB free disk; measure
your own workload. Docker VFS needs considerably more build space than overlay2.
Provider email and hosting can cost money. Self-hosted n8n avoids an n8n Cloud
subscription but uses server resources.

Create DNS A/AAAA records for your actual app hostname. If self-hosting n8n here,
create a second hostname pointing to the same server. Only publish an AAAA record
if the server actually supports IPv6. Keep the DNS proxy/network configured to
preserve raw webhook bodies and signature headers. Caddy obtains and renews public
HTTPS certificates and retains them in its named volumes.

## Private configuration

On the server, copy `deploy/production.env.example` to `deploy/production.env`.
Restrict its permissions to the server operator (`chmod 600`). Fill:

| Variable | Where to obtain it |
|---|---|
| `APP_DOMAIN` | The exact app DNS hostname you own, without scheme or path |
| `ACME_EMAIL` | Your certificate contact email |
| `BACKUP_DIRECTORY` | A private absolute host directory, outside the app volumes |
| `APP_API_TOKEN` | Generate a long random private value; also the invite/access code when registering operators |
| `GEMINI_API_KEY` | [Google AI Studio → API keys](https://aistudio.google.com/apikey); create/select a project and create a key |
| `N8N_BASE_URL` | The actual public HTTPS n8n origin, without extra path |
| `N8N_API_KEY` | n8n owner account → Settings → n8n API → Create API key; requires workflow/credential creation, activation, read and execution-read permissions |
| `RESEND_API_KEY` | [Resend → API keys](https://resend.com/api-keys); create an API key with sending permission for your verified domain |
| `RESEND_FROM_EMAIL` | Sender on a domain verified in [Resend → Domains](https://resend.com/domains) |
| `RESEND_WEBHOOK_SECRET` | Resend webhook details after creating the app callback; use its actual signing secret at runtime |

Generate random values privately with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not paste these values into chat, Git, client JavaScript or `NEXT_PUBLIC_*`.
Cloud network-secret proxy placeholders cannot verify HMAC signatures locally;
signing secrets must be the original provider values in the private runtime.
The frontend container receives only `BACKEND_URL`; all provider keys remain in
the API. For local Windows setup, see `LOCAL-RUN.md`.

## Build and start

From the repository root on the server:

```bash
.venv/bin/python deploy/build.py
docker compose --env-file deploy/production.env -f deploy/compose.production.yaml build frontend
docker compose --env-file deploy/production.env -f deploy/compose.production.yaml config --quiet
docker compose --env-file deploy/production.env -f deploy/compose.production.yaml up -d
docker compose --env-file deploy/production.env -f deploy/compose.production.yaml ps
```

The first command needs the documented Python environment; see `README.md` in
this directory. The frontend image uses Next.js standalone output and a non-root
Node user. The backend uses non-root UID/GID 10001. Neither API nor frontend exposes
a host port; Caddy is the public ingress. Backend host checks admit the configured
public hostname and the private `app` service name. Account cookies are HttpOnly,
secure in production, and forwarded server-side without a privileged bearer fallback
for account requests. The public frontend and callbacks share one app origin.

Open the real HTTPS app URL. Register the first operator with the private access
code, then sign in. Give the access code only to operators who should see this
shared workspace. Keep one API replica/worker; the collector and scheduler are
in-process workers. Allow 330 seconds for graceful stop. Use the Next.js interface
publicly; the earlier `/app/` CRM remains available in the local backend setup.

### Optional n8n on this server

In the private configuration, set `N8N_DOMAIN` to your second actual hostname,
`N8N_ENCRYPTION_KEY` to a separate long random value, and
`CADDY_CONFIG_FILE=./Caddyfile.n8n`. Then:

```bash
docker compose --env-file deploy/production.env -f deploy/compose.production.yaml --profile n8n up -d
```

Open the n8n HTTPS URL, create its owner account, and generate the API key.
Set `N8N_BASE_URL=https://<your-n8n-hostname>` and `N8N_API_KEY` in the private
configuration, then recreate the app service with the same `up -d` command.
Do not change the encryption key after creating credentials. The engine is pinned
to official n8n 2.42.6 and stores workflows, executions and encrypted credentials
in `n8n-data`. Development permits loopback HTTP n8n; public deployment requires
the actual separate HTTPS origin. Arbitrary workflow editing is outside this
app's native supported template.

## Real intake and email setup

Create an inquiry source from the authenticated app. Its private source key is
shown once. Integrate your website's server with the returned `/intake/<source-id>`
path, sending the private `X-Inquiry-Key` header and documented JSON body. Keep
the key in the website's server environment, not in browser form code. Caddy routes
`/intake/*` directly to the API. Duplicate event IDs reuse the existing saved inquiry;
changed duplicate data is refused. Read `backend/INQUIRIES.md` for the exact contract.

For email, add Resend's required DNS records and wait for domain verification.
Create a Resend webhook for `https://<your-app-hostname>/webhooks/resend` and select
the supported email outcome events documented in `backend/HACKATHON.md`. Enter the
actual webhook signing secret into `RESEND_WEBHOOK_SECRET`. Caddy forwards the raw
body and headers; the API verifies signatures, timestamp freshness and deduplication.
Configure the verified sender, then opt in with `ENABLE_EMAIL_DELIVERY=true` and
recreate the app. Provider acceptance is **submitted**, not delivered; delivery
requires signed provider evidence. Use an explicitly owned test inbox and verified
consent before claiming live delivery. No provider keys or real email test have
been supplied with this repository build.

## Backups and restoration

Create `BACKUP_DIRECTORY` on the server, restricted to owner access and writable
by UID/GID 10001 (for example an operator-created directory owned by 10001:10001,
mode 0700). Run:

```bash
./deploy/backup-server.sh
```

This uses SQLite's consistent backup API, copies the scraper artifacts, checks
hashes/integrity, and creates a new backup. It refuses an active collector. It
does not delete old backups or send data off-host. Copy completed backups to
private off-host storage, monitor disk use and choose your own retention policy.
Archives stored outside the configured scraper root need a separate backup.

For daily server backups, replace the two `/opt/AIAUTOMATION` paths in
`aiautomation-backup.service` with the actual checkout path, install both unit files
under `/etc/systemd/system`, then `systemctl daemon-reload` and
`systemctl enable --now aiautomation-backup.timer`. The timer runs at 03:00 in the
server's timezone plus up to 15 minutes jitter, and catches missed runs. Check
`systemctl list-timers` and the service journal for failures. Installation requires
server administrator access; no timer is installed automatically by this build.

Restore into a **new** directory with `backend/backup.py restore`; it refuses an
existing target. The restored copy preserves users/passwords but clears sessions,
so operators must sign in again. Recovered scraper paths are updated to the final
absolute recovery location. Keep the original volume intact until checking records
and retained CSV downloads on a separate instance. Do not move that recovered
folder afterward. See `deploy/README.md` for the exact restoration commands.

The app backup does not back up another provider or the n8n engine. For the bundled
engine, stop only n8n for a short maintenance window, take a private full copy of
`n8n-data`, and restart it with the same profile. Preserve the private encryption
key with your credential recovery plan. Do not claim this separate engine recovery
is verified until you restore that copy onto an isolated server.

Updates preserve named volumes. Never use `docker compose down -v`, volume pruning,
or a global Docker prune to update this application. Set up server/ingress monitoring
and provider limits before increasing usage. A passing local runtime does not
establish public DNS, certificate issuance, live scraping or provider operation.

## Verification scope

The Compose configuration passes rendering and constraint checks for the default,
n8n, maintenance and combined profiles. A small network-disabled scratch export
checked both build contexts: required `COPY` sources are present, and private
environment files, data directories and installed dependencies are excluded.
This does not build either application image. An isolated Linux Next.js standalone
runtime and production-configured API passed ten HTTP checks covering packaged
assets, anonymous access, account registration, secure cookie attributes, data
access, cross-origin rejection and logout revocation. That check manually forwards
the secure cookie over loopback HTTP; it does not test a browser's public HTTPS
connection. Seven backup regressions cover restoration, artifact relocation,
integrity checks and revocation of sessions in restored copies.

The complete new Docker stack has not been built or started in this cloud, and
Windows launchers have been reviewed without running Windows. The existing
read-only backup-container check used the previous verified backend image. The
current source has separate backup tests. Public DNS, Caddy certificate issuance,
provider delivery and restoration onto a separate hosting server still require
checks on the chosen host. No public host or live email credentials were supplied.
