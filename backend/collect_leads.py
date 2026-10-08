"""Run a small live browser pilot through the managed cloud network."""
import argparse
import json
import os
import re
import socket
import subprocess
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from app.errors import AppError
from app.services.csv_import import parse_csv

IMAGE = "gosom/google-maps-scraper@sha256:e205c02913c5a69c16fc2094b8e5b194a2f655166d2c1126d50548d216e6b1b2"
NODE = Path("/opt/ms-playwright-go/node")


def collector_configured(runtime):
    return bool(shutil.which("certutil") and (
        shutil.which("docker") if runtime == "docker" else
        NODE.is_file() and (NODE.parent / "package/index.js").is_file()))


def run_local(command, environment):
    # SIGTERM lets the Node runner close Chromium before a forced process kill.
    with subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
        try:
            stdout, stderr = process.communicate(timeout=300)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
            raise RuntimeError("Scraper exceeded the 5-minute pilot limit; no leads were automatically imported") from None
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def collect(query, output_root, limit=5, *, runtime="docker"):
    if not query.strip() or len(query) > 300 or "\n" in query or "\r" in query:
        raise ValueError("Provide one nonempty business/location query, at most 300 characters")
    if not isinstance(limit, int) or not 1 <= limit <= 10:
        raise ValueError("Pilot limit must be between 1 and 10")
    if runtime not in {"docker", "local"}:
        raise ValueError("Browser runtime must be docker or local")
    # Do not use container networking to work around the cloud's proxy policy.
    try:
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.get("https://www.google.com/maps/search/", params={"api": "1", "query": query})
            if response.status_code >= 400:
                raise RuntimeError("Google Maps rejected the network preflight")
    except (httpx.HTTPError, RuntimeError):
        raise RuntimeError("Google Maps is blocked or unavailable through the configured network; no scraper job was started") from None
    run_id = "medspa-scrape-" + uuid4().hex[:12]
    output = output_root.resolve() / run_id
    output.mkdir(parents=True, exist_ok=False)
    (output / "queries.txt").write_text(query.strip() + "\n", encoding="utf-8")
    # Trust only certificates already installed by this environment. Chromium
    # uses an NSS store; importing these preserves certificate verification.
    database = output / "home/.pki/nssdb"
    database.mkdir(parents=True)
    subprocess.run(["certutil", "-N", "-d", "sql:" + str(database), "--empty-password"],
                   check=True, capture_output=True)
    for certificate in sorted(Path("/usr/local/share/ca-certificates").glob("*.crt")):
        subprocess.run(["certutil", "-A", "-d", "sql:" + str(database), "-n", certificate.stem,
                        "-t", "C,,", "-i", str(certificate)], check=True, capture_output=True)
    # Browser proxy configuration reads inherited variables inside the container;
    # credential values never become host command arguments or saved files.
    script = Path(__file__).with_name("maps_browser.cjs").resolve()
    if runtime == "local":
        environment = {**os.environ, "HOME": str(output / "home"), "MAPS_OUTPUT_DIR": str(output), "DISABLE_TELEMETRY": "1"}
        result = run_local([str(NODE), str(script), str(limit)], environment)
    else:
        result = run_docker(output, run_id, script, limit)
    logs = result.stdout + result.stderr
    logs = re.sub(r"(?i)(https?|socks5h?)://[^/\s@]+@", r"\1://[redacted]@", logs)
    if result.returncode:
        print(logs[-4000:])
        raise RuntimeError("Scraper failed; no leads were automatically imported")
    path = output / "results.csv"
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError("Scraper produced no CSV; live collection has not been validated")
    try:
        _, _, rows = parse_csv(path.read_bytes(), {})
    except AppError:
        raise RuntimeError("Scraper output cannot be parsed as business CSV; inspect the output before importing") from None
    if not any(row.status == "valid" for row, _ in rows):
        raise RuntimeError("Scraper CSV contains no valid business rows; live collection has not been validated")
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(browser_image=IMAGE, browser_runtime=runtime)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Scraper finished. Preview the CSV before importing: {path}")
    print("A file alone does not prove correct med spa results; inspect relevance and completeness.")
    return path


def run_docker(output, run_id, script, limit):
    command = [
        "docker", "run", "--rm", "--name", run_id,
        "--cpus=2", "--memory=2g", "--shm-size=512m",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--env", "DISABLE_TELEMETRY=1", "--env", "HOME=/out/home",
        "--env", "HTTP_PROXY", "--env", "HTTPS_PROXY", "--env", "ALL_PROXY", "--env", "NO_PROXY",
        "--mount", f"type=bind,source={output},target=/out",
    ]
    proxy_value = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or os.environ.get("ALL_PROXY")
    if proxy_value:
        # Share the host route to the existing egress sidecar, and retain the
        # exact managed proxy in Chromium. This does not enable direct egress.
        proxy_host = urlsplit(proxy_value).hostname
        if not proxy_host:
            raise RuntimeError("The configured proxy has no usable hostname")
        command.extend(["--network", "host", "--add-host", proxy_host + ":" + socket.gethostbyname(proxy_host)])
    command.extend(["--mount", f"type=bind,source={script},target=/collector.cjs,readonly",
                    "--entrypoint", "/opt/ms-playwright-go/node", IMAGE, "/collector.cjs", str(limit)])
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Scraper exceeded the 5-minute pilot limit; inspect any partial output before importing") from None
    finally:
        subprocess.run(["docker", "rm", "-f", run_id], capture_output=True, check=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True, help='Example: "med spas in Islamabad Pakistan"')
    parser.add_argument("--limit", type=int, default=5, help="Live pilot size, from 1 to 10 listings")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[1] / ".local/scrapes")
    parser.add_argument("--runtime", choices=("docker", "local"), default=os.getenv("BROWSER_RUNTIME", "docker"))
    args = parser.parse_args()
    try:
        collect(args.query, args.output_dir, args.limit, runtime=args.runtime)
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")
