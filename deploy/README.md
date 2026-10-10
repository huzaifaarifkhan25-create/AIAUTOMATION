# Portable deployment

The Docker image contains the API, browser workspace, Python 3.12, and the pinned
Playwright/Chromium runtime. The collector runs directly inside the app container.
It needs no Docker socket, provider key, or additional scraper container. Development
keeps the existing Docker collector by default. Collection remains a bounded,
1–10 visible-listing pilot with no pagination or guaranteed coverage.

## Build and verify

From the repository root, with Docker running:

```bash
.venv/bin/python deploy/build.py
.venv/bin/python deploy/verify.py
# Optional network check: collects one real listing without importing it.
.venv/bin/python deploy/verify.py --live
```

The build helper retains managed proxy routing and certificate verification.
Optional proxy settings and CA bundles enter through BuildKit secret mounts,
not image environment variables or build arguments. Debian signatures and TLS
remain enabled. Both base images are pinned by digest; Python dependencies are
pinned in `backend/requirements.txt`. Build dependencies are installed as signed
Debian packages, whose versions can change with security updates.

Verification uses an isolated named volume, a temporary random token, and a
loopback-only port 8002. It leaves the primary development database unchanged.
It checks missing-token startup failure, authentication, allowed hosts, production
headers, non-root operation, CSV preview/import, evidence, restart persistence,
and desktop/mobile UI behavior. It also verifies sandbox event idempotency,
scheduled waits, one unsent outbox preview, and recovery after an actual container
restart. The Automation lab additionally verifies appointment scheduling, history,
unsent previews, cancellation, and persistence across another container restart.
Current default verification passes eleven API/container and twenty-one browser checks
(32 total), including CRM search/saved-view checks, nine client/task/operations browser checks and the
complete fictional client demo twice and its records
surviving a container restart.
The client browser checks cover reviewed sandbox activation, deployment-bound
reminders/pause, secret-free handoff, lost-response task retry, safe text rendering,
demo alert filtering, blocked active setup alerts and review links, desktop/mobile
layouts and clearing delayed data after lock.
Email provider tests are simulated; deployment checks send no messages. `--live` checks real collection,
source-artifact retention, CSV integrity, no automatic import, and job persistence.
Reports and screenshots remain under ignored `.local/deployment/`; test containers,
temporary tokens, and test volumes are removed. A local test is not publication.

Check free disk before repeated builds. The cloud's VFS Docker driver copies
whole layers and can use much more physical space than `docker system df` shows.
Inspect `df -h`, `docker info`, and build cache before rebuilding. Only remove
identified superseded images/caches owned by this app; preserve the current image,
base images, data volumes, and backups. Never use volume pruning to fix build space.

## Hosting requirements

Use a container host with a persistent disk, HTTPS ingress, outbound access to
Google Maps and the approved business sites, and enough resources for Chromium.
The tested limits are two CPUs, 2 GB memory, and 512 MB shared memory. Do not assume
a small free hosting tier supports this workload. Scraping has no per-record
provider charge; server resources can still cost money.

Run exactly one replica with one API worker. Collection state is stored, but the
collector is an in-process task, not a distributed queue. Normal shutdown waits
for the bounded collection to finish; allow 330 seconds before forced termination.
After an abrupt restart, unfinished jobs become interrupted and need human review.

Configure these **on the hosting service**, using secure settings for secrets:

| Setting | Value |
|---|---|
| `APP_ENV` | `production` (image default) |
| `APP_API_TOKEN` | Random shared token; at least 32 printable non-space characters |
| `APP_ALLOWED_HOSTS` | Exact app hostname(s), comma-separated; no wildcard, scheme, or port |
| `PORT` | Hosting-assigned port, or `8000` |
| Persistent disk | Mounted at `/data`, writable by UID/GID `10001:10001` |
| `APP_DB_PATH` | `/data/backend.sqlite3` (image default) |
| `SCRAPE_OUTPUT_DIR` | `/data/scrapes` (image default) |
| `BROWSER_RUNTIME` | `local` (image default) |
| `ENABLE_OUTBOUND_CALLS` | `false` |
| `ENABLE_EMAIL_DELIVERY` | `false` until provider setup |
| `APP_PUBLIC_URL` | Optional actual HTTPS app origin for signed provider callbacks |

Store the token privately; the app checks length/character restrictions, not its
randomness. A cryptographically generated token, such as `secrets.token_urlsafe(48)`,
is appropriate. Rotate it in hosting settings and restart the app if shared access
changes. This is one shared workspace, with no individual accounts or roles.
Set ingress rate limits for failed authentication, collection and website analysis
before exposing the pilot publicly. The application does not implement per-user
quotas or roles.

Route public requests through HTTPS. The container listens on its assigned port
over internal HTTP. Preserve the app hostname in the ingress Host header; include
any provider health-check hostname in the allowlist when required. The image's
internal health check supplies the first configured hostname. `/health` is public
and only checks process responsiveness; `/ready` checks storage and requires the
token. API documentation is disabled in production. The app shell is public,
while all data routes require authentication. Production responses include CSP,
frame restrictions, and cache restrictions on API responses.

The development cloud's managed proxy and its private trust roots are specific
to that cloud. On another host use that host's supported networking and trust
settings; do not copy cloud proxy credentials. For an approved intercepting proxy,
install its public CA through supported host configuration for both Python and
Chromium. Never disable TLS verification. A deployment-host live test is required
before claiming its scraper or website fetching works.

The local browser subprocess now receives only runtime and proxy variables, not
API or provider credentials. Chromium still runs without its own sandbox in the
API container and shares that container's filesystem access. Isolate the browser
in a separate low-privilege worker before using collection with untrusted browsing
at larger scale. The website fetcher validates allowed public DNS answers, but a
proxy resolves the hostname again for the connection. Configure the hosting
egress/proxy policy to reject private and local destinations; the application
cannot prove the proxy's final destination from inside this container.

Website research needs exact `WEBSITE_ALLOWED_HOSTS`, separate from app allowed
hosts. HTTPS DNS fallback and redirects remain opt-in. Optional AI, Places,
Supabase, and Twilio need their respective provider configuration and live checks.
Workflow exports remain internal JSON; running supported reminders requires an
explicit event. Optional Resend reminders need api.resend.com, a verified sender,
API key, ENABLE_EMAIL_DELIVERY=true, and an actual direct-runtime signing secret.
Register the deployed HTTPS /webhooks/resend URL with the provider and preserve
its signed raw body/headers through ingress. Live email is unverified. See
[the reminder setup guide](../backend/HACKATHON.md). No business contacts occur
in deployment verification.

## Compose on a server

Build the image first. Copy `deploy/.env.example` to `deploy/.env` on the server,
enter a random token and the actual app hostname, and restrict the file to its
owner. Never commit it. Then, from the repository root:

```bash
docker compose -f deploy/compose.yaml up -d
docker compose -f deploy/compose.yaml ps
```

This binds to loopback only. Configure the server's HTTPS reverse proxy to send
requests to port 8000 and preserve Host. A managed host can instead use the same
image, settings, resource limits, and `/data` disk without Compose. With a managed
host, give the disk the runtime user's ownership before starting the container;
the Compose named volume inherits the image's ownership when first created.

Updates retain the named volume. Keep SQLite-consistent backups and all scraper
source artifacts on durable storage, and test restoration before storing important
production data. `docker compose down` keeps the volume; **do not use `down -v`**
unless intentionally deleting every saved record and source artifact.

## Backup and recovery

For SQLite, the release bundles `/app/backend/backup.py`. From the development
repository, with no collection running and the source paths configured:

```bash
.venv/bin/python backend/backup.py create --output-dir .local/backups
.venv/bin/python backend/backup.py verify .local/backups/backup-EXAMPLE
.venv/bin/python backend/backup.py restore .local/backups/backup-EXAMPLE --destination .local/recovered-NEW
```

Replace EXAMPLE with the returned backup directory. The helper reads APP_DB_PATH
and SCRAPE_OUTPUT_DIR for creation, uses SQLite's backup API including committed
WAL data, copies scraper files, and checks hashes/SQLite integrity. Keep the output
outside SCRAPE_OUTPUT_DIR. Queued/running jobs block backup; wait for them to finish.
Use a private backup directory and store a separate copy on private off-host
storage. The helper does not schedule backups or upload them. Research archives
outside SCRAPE_OUTPUT_DIR need a separate backup. Supabase requires its provider's
backup/recovery tools; this helper is SQLite only.

Recovery refuses an existing destination and rewrites saved discovery result paths
to the new recovered scraper root. Start a separate instance with APP_DB_PATH and
SCRAPE_OUTPUT_DIR set to those recovered paths, then verify records and CSV downloads.
The backup manifest hashes the original files; restored DB bytes change when job
paths are relocated. Leave the original instance/data intact until review finishes.
For a container recovery, perform restoration at its final absolute paths; mount
them there and ensure UID/GID 10001 can access the DB, directories, and files.
Do not rename/move recovered artifacts afterward without updating the saved paths.
Passing restoration tests locally does not establish a hosting provider's recovery.

CRM/client/operations APIs now support the shared-workspace pilot. Local workflow
activation does not provision another server or create client accounts.
See [MVP.md](../backend/MVP.md) for approval, preflight, pause and handoff behavior.
Human dialer outcomes additionally need the actual TWILIO_AUTH_TOKEN at runtime
for local signature verification and the registered public callback origin.

Public hosting is not provisioned by these files. Choosing a hosting account,
configuring HTTPS and storage, and testing its actual network are the remaining
publication steps.
