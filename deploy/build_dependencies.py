"""Install signed Debian packages and pinned Python packages with verified TLS.

BuildKit optionally mounts a JSON proxy environment and trusted CA bundle. Those
values are never copied into image layers, command arguments, or unredacted logs.
"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


def main():
    environment = dict(os.environ)
    proxy = Path("/run/secrets/build_proxy")
    if proxy.exists():
        values = json.loads(proxy.read_text())
        for name, value in values.items():
            if name in {"HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"} and isinstance(value, str):
                environment[name] = value
                environment[name.lower()] = value
    ca = Path("/run/secrets/build_ca")
    apt_options = []
    if ca.exists():
        environment["PIP_CERT"] = str(ca)
        environment["SSL_CERT_FILE"] = str(ca)
        apt_options = ["-o", f"Acquire::https::CaInfo={ca}"]
    environment["DEBIAN_FRONTEND"] = "noninteractive"
    # Official Debian archive metadata and package signatures stay mandatory.
    for source in Path("/etc/apt/sources.list.d").glob("*.sources"):
        source.write_text(source.read_text().replace("http://deb.debian.org", "https://deb.debian.org"))
    commands = [
        ["apt-get", *apt_options, "-o", "APT::Update::Error-Mode=any", "update"],
        ["apt-get", *apt_options, "install", "--no-install-recommends", "-y", "libnss3-tools", "libreadline8t64", "libgdbm6t64"],
        ["python3", "-m", "pip", "install", "--no-cache-dir", "-r", "/tmp/requirements.txt"],
        ["python3", "-m", "pip", "check"],
        ["python3", "-c", "import ssl,sqlite3,bz2,lzma,ctypes,readline,dbm.gnu; print('Python runtime imports verified')"],
    ]
    for command in commands:
        result = subprocess.run(command, env=environment, text=True, capture_output=True, check=False)
        output = result.stdout + result.stderr
        for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
            value = environment.get(name)
            if value:
                output = output.replace(value, "[build proxy]")
        output = re.sub(r"(?i)(https?|socks5h?)://[^/\s@]+@", r"\1://[redacted]@", output)
        print(output, flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)
    shutil.rmtree("/var/lib/apt/lists")


if __name__ == "__main__":
    main()
