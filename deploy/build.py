"""Build the portable image, retaining managed routing without persisting secrets."""
import json
import os
import socket
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


def main():
    root = Path(__file__).resolve().parents[1]
    local = root / ".local/deployment"
    local.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="build-", dir=local) as folder:
        proxy = Path(folder) / "proxy.json"
        values = {name: os.environ[name] for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY") if os.environ.get(name)}
        proxy.write_text(json.dumps(values))
        proxy.chmod(0o600)
        command = ["docker", "build", "--tag", "aiautomation:local", "--network", "host",
                   "--secret", f"id=build_proxy,src={proxy}"]
        ca = Path(os.environ.get("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt"))
        if ca.is_file():
            command.extend(["--secret", f"id=build_ca,src={ca}"])
        # Existing cloud sidecar hostname can require an explicit host entry.
        for host in sorted({urlsplit(values[name]).hostname for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY") if values.get(name)} - {None}):
            command.extend(["--add-host", f"{host}:{socket.gethostbyname(host)}"])
        command.append(str(root))
        raise SystemExit(subprocess.call(command))


if __name__ == "__main__":
    main()
