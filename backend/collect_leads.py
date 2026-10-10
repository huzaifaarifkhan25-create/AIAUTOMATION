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
WINDOWS_PLAYWRIGHT = Path(__file__).resolve().parents[1] / ".local/browser-tools/node_modules/playwright-core"
BROWSER_ENV_KEYS = ("PATH", "LANG", "LC_ALL", "TZ", "TMPDIR", "HTTP_PROXY", "HTTPS_PROXY",
                    "ALL_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SystemRoot")


class CollectorUnavailable(RuntimeError):
    """A safe, operator-facing collector failure without provider output."""


COLLECTOR_ERRORS = {
    "browser_launch_failed": "The collector could not start Edge. Close other Edge windows using the pilot, then check the collector setup and try again. No leads were imported.",
    "browser_closed": "The collector's Edge page closed unexpectedly before the search finished. This can happen if the window is closed or Edge stops. Start a new pilot with a business type and city. No leads were imported.",
    "maps_navigation_failed": "The collector could not open the Maps search page. Check network access to Google Maps, then start a new pilot. No leads were imported.",
    "maps_place_page": "Maps opened a place or city page instead of business results. Search for a business type and city, then start a new pilot. No leads were imported.",
    "maps_results_unavailable": "Maps did not show readable listing cards within 30 seconds. Try a business type and city, then start a new pilot. No leads were imported.",
    "no_usable_listings": "The collector found Maps results but could not capture a complete listing. Try a more specific query or use CSV import. No leads were imported.",
}


def local_browser_paths():
    if NODE.is_file() and (NODE.parent / "package/index.js").is_file():
        return str(NODE), str(NODE.parent / "package"), ""
    if os.name == "nt":
        node = shutil.which("node")
        roots = [os.environ.get("PROGRAMFILES(X86)"), os.environ.get("PROGRAMFILES")]
        candidates = [Path(root) / "Microsoft/Edge/Application/msedge.exe" for root in roots if root]
        edge = next((path for path in candidates if path.is_file()), None)
        if node and WINDOWS_PLAYWRIGHT.joinpath("index.js").is_file() and edge:
            return node, str(WINDOWS_PLAYWRIGHT), str(edge)
    return None


def collector_status(runtime):
    """Check local prerequisites only; never pull an image or contact Maps."""
    if runtime == "local":
        ready = bool(local_browser_paths()) and (os.name == "nt" or bool(shutil.which("certutil")))
        return {"ready": ready, "code": "ready" if ready else "browser_missing",
                "message": ("Edge and the collector setup are available. This check has not searched Google Maps. Start a live pilot to try a search, then review its results before importing."
                            if ready and os.name == "nt" else
                            "Bundled browser is available. This check has not searched Google Maps. Start a live pilot to try a search."
                            if ready else "Local browser runtime is missing. CSV import is available.")}
    if not shutil.which("docker"):
        return {"ready": False, "code": "docker_missing",
                "message": "Docker is not installed on this server. Use CSV import or install the browser collector."}
    try:
        daemon = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"],
                                capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        daemon = None
    if daemon is None or daemon.returncode:
        return {"ready": False, "code": "docker_unavailable",
                "message": "Docker Desktop is not responding. Start or restart it, then check again. CSV import is available."}
    try:
        image = subprocess.run(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
                               capture_output=True, text=True, timeout=3, check=False)
    except (OSError, subprocess.TimeoutExpired):
        image = None
    if image is None:
        return {"ready": False, "code": "docker_unavailable",
                "message": "Docker Desktop is not responding. Start or restart it, then check again. CSV import is available."}
    if image.returncode:
        return {"ready": False, "code": "image_missing",
                "message": "The pinned browser image is not installed. Install it after checking Docker storage, or use CSV import."}
    return {"ready": True, "code": "ready",
            "message": "Browser image is available. This check has not searched Google Maps. Start a live pilot to try a search."}


def collector_configured(runtime):
    browser_available = (shutil.which("docker") if runtime == "docker" else
                         local_browser_paths())
    return bool(browser_available and (os.name == "nt" or shutil.which("certutil")))


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
            raise CollectorUnavailable("The 5-minute pilot limit was reached. Start a new pilot or use CSV import. No leads were imported.") from None
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def collect(query, output_root, limit=5, *, runtime="docker"):
    if not query.strip() or len(query) > 300 or "\n" in query or "\r" in query:
        raise ValueError("Provide one nonempty business/location query, at most 300 characters")
    if not isinstance(limit, int) or not 1 <= limit <= 10:
        raise ValueError("Pilot limit must be between 1 and 10")
    if runtime not in {"docker", "local"}:
        raise ValueError("Browser runtime must be docker or local")
    status = collector_status(runtime)
    if not status["ready"]:
        raise CollectorUnavailable(status["message"])
    # Do not use container networking to work around the cloud's proxy policy.
    try:
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            response = client.get("https://www.google.com/maps/search/", params={"api": "1", "query": query})
            if response.status_code >= 400:
                raise RuntimeError("Google Maps rejected the network preflight")
    except (httpx.HTTPError, RuntimeError):
        raise CollectorUnavailable("Google Maps is blocked or unavailable through the configured network; no scraper job was started") from None
    run_id = "medspa-scrape-" + uuid4().hex[:12]
    output = output_root.resolve() / run_id
    output.mkdir(parents=True, exist_ok=False)
    (output / "queries.txt").write_text(query.strip() + "\n", encoding="utf-8")
    # Trust only certificates already installed by this environment. Chromium
    # uses an NSS store; importing these preserves certificate verification.
    home = output / "home"
    home.mkdir()
    if os.name != "nt":
        database = home / ".pki/nssdb"
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
        node, package, executable = local_browser_paths()
        # The API may hold provider credentials. The browser needs only its
        # runtime paths and managed network configuration.
        environment = {key: os.environ[key] for key in BROWSER_ENV_KEYS if key in os.environ}
        environment.update(HOME=str(output / "home"), MAPS_OUTPUT_DIR=str(output), DISABLE_TELEMETRY="1")
        environment["MAPS_PLAYWRIGHT_PACKAGE"] = package
        if executable:
            environment.update(MAPS_BROWSER_EXECUTABLE=executable, MAPS_BROWSER_VISIBLE="1")
        result = run_local([node, str(script), str(limit)], environment)
    else:
        result = run_docker(output, run_id, script, limit)
    logs = result.stdout + result.stderr
    logs = re.sub(r"(?i)(https?|socks5h?)://[^/\s@]+@", r"\1://[redacted]@", logs)
    if result.returncode:
        print(logs[-4000:])
        match = re.search(r"(?m)^COLLECTOR_ERROR_CODE=([a-z_]+)$", logs)
        if match and match.group(1) in COLLECTOR_ERRORS:
            raise CollectorUnavailable(COLLECTOR_ERRORS[match.group(1)])
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
    status = collector_status("docker")
    if not status["ready"]:
        raise CollectorUnavailable(status["message"])
    command = [
        "docker", "run", "--rm", "--name", run_id,
        "--cpus=2", "--memory=2g", "--shm-size=512m",
        "--env", "DISABLE_TELEMETRY=1", "--env", "HOME=/out/home",
        "--env", "HTTP_PROXY", "--env", "HTTPS_PROXY", "--env", "ALL_PROXY", "--env", "NO_PROXY",
        "--mount", f"type=bind,source={output},target=/out",
    ]
    if hasattr(os, "getuid") and hasattr(os, "getgid"):
        command.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
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
    parser.add_argument("--runtime", choices=("docker", "local"), default=os.getenv("BROWSER_RUNTIME", "local" if os.name == "nt" else "docker"))
    args = parser.parse_args()
    try:
        collect(args.query, args.output_dir, args.limit, runtime=args.runtime)
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")
