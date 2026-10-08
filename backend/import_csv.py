"""Preview/import a scraper CSV through the running backend."""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx


def run(args):
    parsed = urlsplit(args.base_url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise ValueError("Provide an HTTP/HTTPS backend URL without credentials")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Use HTTPS for a remote backend")
    path = Path(args.file)
    if path.stat().st_size > 2_000_000:
        raise ValueError("CSV must be at most 2 MB")
    headers = {"Content-Type": "text/csv"}
    if os.getenv("APP_API_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["APP_API_TOKEN"]
    params = {"source": args.source, "file_name": path.name, "dry_run": not args.commit}
    if args.column_map:
        params["column_map"] = args.column_map
    if args.collected_at:
        params["collected_at"] = args.collected_at
    with httpx.Client(base_url=args.base_url, timeout=120, follow_redirects=False) as client:
        response = client.post("/businesses/import-csv", content=path.read_bytes(), headers=headers, params=params)
        if response.status_code != 200:
            print(response.text)
            response.raise_for_status()
        report = response.json()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        if report["invalid_rows"]:
            return 1
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Preview CSV first; use --commit to save valid unique rows")
    parser.add_argument("file")
    parser.add_argument("--source", choices=["gosom", "instant_data_scraper", "web_scraper", "csv"], default="csv")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--column-map", help='JSON mapping such as {"name":"Title","address":"Address"}')
    parser.add_argument("--collected-at", help="Timezone-aware ISO timestamp; defaults to upload time")
    parser.add_argument("--commit", action="store_true", help="Save rows; otherwise preview only")
    raise SystemExit(run(parser.parse_args()))
