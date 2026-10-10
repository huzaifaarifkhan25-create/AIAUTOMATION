# Free scraping and CSV import

The cloud workflow uses our small Playwright browser collector in maps_browser.cjs,
launched by collect_leads.py. It needs no provider API key or per-record fee.
It uses the installed browser from a pinned
[gosom/google-maps-scraper](https://github.com/gosom/google-maps-scraper) image;
it does not run gosom's scraping engine. That engine rejected the cloud's
unauthenticated proxy. The original browser cache also required write permissions.
Our collector supports the managed proxy directly and preserves TLS verification
using existing environment trust certificates in a local browser NSS store.

Gosom's verified v1.18.1 license is MIT, and its own CLI/API remains a possible
external CSV source. Its live scraping engine has not been validated here.
Our backend integrates through CSV and its own saved browser-pilot jobs. Automatic
vendor scraper REST API adapters are not implemented.
Hosting can cost money. Free software does not guarantee unlimited Google access,
complete results, or accurate categories.

## Comparison

| Tool | Fit |
|---|---|
| Local browser pilot | Verified five live medical-spa listings; 1–10 listing pilot, no pagination |
| gosom/google-maps-scraper | Free self-hosted CLI/API; cloud proxy incompatible in the tested image |
| Instant Data Scraper | Browser/manual export fallback; generated headers can be mapped |
| Web Scraper extension | Custom directory scraping; API belongs to its separate Cloud product |
| Omkar Google Maps Extractor | Repository advertises a limited free allowance; not selected over the MIT core |

Sources: [gosom release README](https://github.com/gosom/google-maps-scraper/tree/v1.18.1),
[license](https://github.com/gosom/google-maps-scraper/blob/v1.18.1/LICENSE),
[CSV implementation](https://github.com/gosom/google-maps-scraper/blob/v1.18.1/gmaps/entry.go),
[Web Scraper Cloud client](https://www.npmjs.com/package/@webscraperio/api-client-nodejs),
[Omkar repository](https://github.com/omkarcloud/google-maps-scraper).
There is no comparative live accuracy benchmark. Extension pricing/limits and
Maps behavior are not independently verified here because vendor sites are restricted.

## Installed browser runtime

On Windows, the app now defaults to `BROWSER_RUNTIME=local`. The optional
`SETUP-WINDOWS-COLLECTOR.bat` installs pinned `playwright-core` into ignored
`.local/browser-tools` and uses the installed Microsoft Edge browser and Node.
This needs no Docker image. The child browser receives only its runtime,
working directory and network variables plus Windows `SystemRoot`, not app
tokens or provider keys. Browser certificate verification remains enabled.
A one-listing New York pilot succeeded on 2026-10-09 with its source page,
manifest and matching CSV hash; it was not imported. The app shows live
readiness before enabling Start, but network access and listing quality still
require a result preview on every run. The **Open Google Maps** link is a
manual option when neither automated collector is ready.

Linux development's default Docker runtime requires a running Docker daemon and
certutil (libnss3-tools) on Linux. On Windows the Docker collector uses the
container/browser trust store and does not invoke Windows' unrelated `certutil`.
The release image bundles certutil, Node, and Chromium
and uses BROWSER_RUNTIME=local, running the collector inside the app container.
It needs no Docker CLI or socket. SCRAPE_OUTPUT_DIR sets the API job artifact
directory; the release default is `/data/scrapes`. See
[deploy/README.md](../deploy/README.md) for build and live container verification.
The image is pinned by digest:

```bash
docker pull gosom/google-maps-scraper@sha256:e205c02913c5a69c16fc2094b8e5b194a2f655166d2c1126d50548d216e6b1b2
docker run --rm --network none -e DISABLE_TELEMETRY=1 gosom/google-maps-scraper@sha256:e205c02913c5a69c16fc2094b8e5b194a2f655166d2c1126d50548d216e6b1b2 -version
```

On the checked Windows laptop Docker Desktop started, but the pinned image was
absent and C: initially had about 153 MB free. After free space rose to about
3.2 GB, an exact pinned-image pull was attempted. It transferred no visible
layers, the daemon stopped responding promptly, and the pull was interrupted.
No app collector run occurred. A separate visible Edge check reached Google
Maps and a medical-spa listing, but this does not verify the bundled collector.
See [LIVE_INTEGRATION_CHECKS.md](LIVE_INTEGRATION_CHECKS.md).

Download, checksum verification through Docker, CLI help, and version
v1.18.1-549e4b5 were verified. Google Maps access now works. On 2026-10-06,
the local browser collector loaded Maps and collected five medical-spa listings
for "medical spas in New York NY". All five had names, addresses, websites,
phones, ratings, and Place IDs. All five matched captured listing text and were
imported into SQLite with source=csv and original values. Review counts were
unavailable in Google's limited view and remain null.

Pilot artifacts are under ignored .local/scrapes/medspa-scrape-ce210a755731/:
results.csv, queries.txt, manifest.json (query, dates, image digest, CSV SHA-256),
search HTML/screenshot, and HTML/text/screenshots for each listing. The pilot
does not prove directory completeness, future scraping reliability, or phone
reachability. Initial independent official-site checks returned proxy access
denials, recorded in website-checks.json. Subsequent official-site research and
live automatic API analysis succeeded for all five. Current verification is in
.local/research/automatic-fetch-49b94d993015/verification.md, with full live
responses in report.json. No fixture was used as live data.

Run from the repository root:

```bash
.venv/bin/python backend/collect_leads.py --query 'medical spas in New York NY' --limit 5
```

Change the city as needed; New York is a validation territory, not a product restriction.
The helper checks managed
network access first and inherits proxy routing into the browser. It does not
bypass a blocked preflight. With a proxy it shares the host route to the existing
egress sidecar and resolves that sidecar hostname inside the container. Browser
traffic still uses the managed proxy. It collects at most 1–10 visible listings,
with a five-minute limit and a unique output folder under ignored .local/scrapes/. It removes
only its own container, never imports automatically, and does not contact businesses.
On timeout, inspect any partial CSV. Inspect successful output for med spa relevance
and usable contact details. Browser/TLS failures need supported trust configuration,
not disabled verification or CAPTCHA bypassing.

Hosts saved for review: www.google.com, maps.google.com, consent.google.com,
www.gstatic.com, maps.gstatic.com, fonts.gstatic.com, fonts.googleapis.com,
lh3.googleusercontent.com. Add others only when an observed request requires them.
After the five official-site requests were denied, these observed hosts were also
saved in the draft: dolcemedicalspas.com, www.tribecamedspa.com,
www.perfectmedspa.com, www.zzmedspa.com, trifectamedspanyc.com. These sites and
dns.google now work through the managed proxy. All five passed automatic analysis
with HTTPS DNS enabled. Review/save the reusable settings and publish the
environment to retain the prepared setup for future sessions.

## Preview and import CSV

Start the backend, then run from the repository root:

```bash
.venv/bin/python backend/import_csv.py results.csv --source csv --collected-at '2026-10-06T17:04:42.101Z'
.venv/bin/python backend/import_csv.py results.csv --source csv --collected-at '2026-10-06T17:04:42.101Z' --commit
```

Replace the timestamp with the current run's manifest started_at. The first command
only previews. Use --commit after inspecting the report. Category and per-row date
columns remain in the raw CSV/manifest and are ignored by this import contract.
Use source=gosom for an actual gosom CLI export.
Other source labels: instant_data_scraper, web_scraper. APP_API_TOKEN is used
when configured and is not printed. Remote backend URLs require HTTPS.
No paid provider key is needed for this path.

Fictional example, preview only:

```bash
.venv/bin/python backend/import_csv.py backend/examples/gosom-demo.csv --source gosom
```

For extension-generated headers, supply an exact mapping matching your file:

```bash
.venv/bin/python backend/import_csv.py results.csv --source instant_data_scraper --column-map '{"name":"qBF1Pd","address":"W4Efsd","website":"Website"}'
```

Raw upload endpoint, also documented in Swagger UI:

```bash
curl --fail-with-body -X POST 'http://127.0.0.1:8000/businesses/import-csv?source=gosom&dry_run=true' \
  -H 'Content-Type: text/csv' --data-binary @results.csv
```

Set dry_run=false to save. Authenticated deployments need the configured bearer
header. These local addresses are development validation routes, not published previews.

## Rules and limitations

The browser workspace at `/app/` can launch the same live collector and preview
its results. `POST /discovery/jobs` accepts `query` and `limit` (1–10), returns
HTTP 202, and does not import leads. Poll `GET /discovery/jobs/{id}` for queued,
running, succeeded, failed, or interrupted status. Only a successful job can be
previewed with `POST /discovery/jobs/{id}/preview`; saving requires a separate
`POST /discovery/jobs/{id}/import`. `GET /discovery/jobs/{id}/csv` downloads the
original output for re-import and provenance. `GET /discovery/jobs/{id}/spreadsheet.csv`
downloads a separate viewing copy that prefixes common formula-leading cells as
text and replaces embedded tabs/newlines with spaces. Spreadsheet applications
can interpret CSV differently, so review the file before opening it. Its values
can differ from the raw source; use the original CSV for re-import. These routes
use the same bearer authentication as other data routes.
The service checks the retained CSV against its original SHA-256 before preview,
download, or import. Missing/modified output is rejected. Repeated imports skip duplicates.
The query, collection time, count, and hash are retained on the job; internal file
paths are excluded from API responses. Failed collection never falls back to demo data.
Run one API worker; an active pilot blocks a second job. This is an MVP background
task, not a distributed/durable worker queue. Startup marks unfinished saved jobs
interrupted and does not automatically retry them. Normal shutdown waits for cleanup;
after abrupt host failure, inspect owned pilot containers before resuming collection.

- UTF-8 CSV (BOM supported), comma/semicolon/tab separators; at most 2 MB, 2,000 nonempty rows, 80 columns.
- Name and address are required. Optional targets: website, phone, rating, review_count, place_id, listing_url.
- Common headers (title, Business Name, Full Address, site, review_rating, Reviews) are recognized. Ambiguous columns require column_map.
- Generic URL is not automatically a website; it could be a Maps listing. Missing details stay null.
- Bare website domains receive HTTPS. Maps listing URLs belong in listing_url. Phone formatting/country prefixes are preserved; none are invented.
- Decimal-comma ratings and grouped integer counts work. Abbreviated counts such as 1.2K stay unknown with a warning and the original retained.
- Preview saves no business records. Commit saves valid unique rows and reports invalid ones.
- Malformed syntax, missing/ambiguous headers, and exceeded limits are rejected before writes.
- Existing records are skipped, not overwritten. Place ID detects duplicates when available; normalized name/address is the fallback. Repeat import is safe.
- Saved provenance includes source, collection date, filename, Place ID, listing URL, mapping, and original mapped values. Unmapped columns are reported but not stored.
- collected_at defaults to upload time, not a verified scrape date. Supply a timezone-aware ISO timestamp when known; future dates are rejected.
- A storage failure reports how many rows were saved. Retry the file to skip those records and continue. Import is not a cross-provider transaction.
- Duplicate detection scans saved records in this MVP; larger datasets need indexing.
- The report contains total_rows, valid_rows (unique candidates), imported_rows, duplicate_rows, invalid_rows, and row errors/warnings.
- The CLI exits nonzero if rows are invalid, even if other valid rows were committed.
- Import does not verify that a business is real, is a med spa, or needs automation.

Earlier cloud drafts list Google Places/LLM/Twilio credential requirements. The
free CSV workflow does not use them. Remove unused requirements in environment
settings for a free-only setup; the draft tool cannot remove existing requirements.
